"""
TelegramtoCSV Telegram Bot — free tier interface.

Uses python-telegram-bot v22+ with HTTP long-polling (reliable, no
MTProto session quirks). The scraper itself still uses Pyrogram with
the worker pool — that part is unchanged.
"""

import asyncio
import logging
import os
import re
import time
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from app import app, db
from models import Order
from scraper_engine import process_scraping


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("tgcsv-bot")
logging.getLogger("httpx").setLevel(logging.WARNING)


# --- Rate limit: 1 free export / hour, per user ---
FREE_COOLDOWN_SEC = 3600
_user_last_order: dict[int, float] = {}


CHANNEL_LINK_RE = re.compile(
    r"(?:https?://)?(?:t(?:elegram)?\.me/(?:s/)?|@)([A-Za-z][A-Za-z0-9_]{3,31})",
    re.IGNORECASE,
)


WELCOME = (
    "👋 *Hi! I export public Telegram channels into CSV files.*\n\n"
    "Send me a public channel link — for example:\n"
    "• `https://t.me/durov`\n"
    "• `@durov`\n\n"
    "I'll fetch the last {limit} messages and DM you the CSV (zipped).\n\n"
    "*Free tier:* {limit} messages, 1 export per hour.\n"
    "*Unlimited:* whole archive for ${price:.2f} USDT — on the website.\n\n"
    "🔗 telegramtocsv.com"
)

HELP = (
    "*How to use this bot*\n\n"
    "1. Send me a Telegram channel link or @username\n"
    "2. I fetch the last {limit} messages (free tier)\n"
    "3. You get a CSV inside a ZIP\n\n"
    "*Limits*\n"
    "• 1 free export per hour per user\n"
    "• Public channels only (no private chats/groups)\n\n"
    "*Need more?*\n"
    "Whole-archive exports cost ${price:.2f} USDT (TRC20). Use the website:\n"
    "🔗 telegramtocsv.com\n\n"
    "Questions: riven2430@gmail.com"
)

UPSELL = (
    "\n\n💡 *Need the whole archive, not just the last {limit}?*\n"
    "Unlimited export for *${price:.2f} USDT*: telegramtocsv.com"
)


# ============== Handlers ==============


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME.format(limit=config.FREE_MESSAGE_LIMIT, price=config.PAID_PRICE_USDT),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP.format(limit=config.FREE_MESSAGE_LIMIT, price=config.PAID_PRICE_USDT),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def paid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        f"💎 *Unlimited export* — the whole channel archive\\.\n\n"
        f"Price: *${config.PAID_PRICE_USDT:.2f} USDT* \\(TRC20 / TRON network\\)\n"
        f"Wallet:\n`{config.WALLET_ADDRESS}`\n\n"
        f"*How to pay:*\n"
        f"1\\. Open [telegramtocsv\\.com](https://telegramtocsv.com)\n"
        f"2\\. Paste channel link → choose *Unlimited*\n"
        f"3\\. Send the USDT, paste your TXID → done\n\n"
        f"_Payment verification runs on the website \\(instant on\\-chain check\\)\\._"
    )
    qr_url = f"https://telegramtocsv.com/qr/wallet.png?v={config.WALLET_ADDRESS[:8]}"
    try:
        await update.message.reply_photo(
            photo=qr_url,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception:
        # Fallback to plain text without markdown if photo or MD fails
        fallback = (
            f"Unlimited export — the whole channel archive.\n\n"
            f"Price: ${config.PAID_PRICE_USDT:.2f} USDT (TRC20)\n"
            f"Wallet: {config.WALLET_ADDRESS}\n\n"
            f"Pay at https://telegramtocsv.com — paste channel link, "
            f"choose Unlimited, send USDT, paste TXID."
        )
        await update.message.reply_text(fallback, disable_web_page_preview=True)


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📧 *Contact*\n\n"
        "Email: riven2430@gmail.com\n"
        "Website: telegramtocsv.com\n\n"
        "Bug reports, feature requests, partnerships — all welcome\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = (update.message.text or "").strip()

    m = CHANNEL_LINK_RE.search(text)
    if not m:
        await update.message.reply_text(
            "❌ That doesn't look like a Telegram channel link.\n\n"
            "Send something like: https://t.me/durov or @durov",
            disable_web_page_preview=True,
        )
        return

    channel_name = m.group(1).lstrip("@")
    channel_link = f"https://t.me/{channel_name}"

    # Rate limit
    now = time.time()
    last = _user_last_order.get(user_id, 0)
    if now - last < FREE_COOLDOWN_SEC:
        remaining = int((FREE_COOLDOWN_SEC - (now - last)) / 60) + 1
        await update.message.reply_text(
            f"⏳ Free tier cooldown. You've used your free export this hour.\n\n"
            f"Try again in ~{remaining} min, or get unlimited (no cooldown) at telegramtocsv.com",
            disable_web_page_preview=True,
        )
        return
    _user_last_order[user_id] = now

    # Create DB order
    username_tag = (user.username or user.first_name or "unknown")[:64]
    with app.app_context():
        order = Order(
            channel_link=channel_link,
            tier="free",
            currency="USDT",
            amount=0,
            ip_address=f"bot:{user_id}",
            user_agent=f"TelegramBot/{username_tag}",
            status="processing",
            progress=5,
            status_message="Started via bot",
        )
        db.session.add(order)
        db.session.commit()
        order_id = order.id
        order_token = order.token

    log.info(
        "Bot order #%s started for user %s (@%s, channel: %s)",
        order_id, user_id, username_tag, channel_name,
    )

    status_msg = await update.message.reply_text(f"🔍 Fetching {channel_name}… 5%")

    last_percent = [5]
    loop = asyncio.get_running_loop()

    def update_progress(percent: int, msg: str):
        # Update DB regardless
        try:
            with app.app_context():
                o = db.session.get(Order, order_id)
                if o:
                    o.progress = percent
                    o.status_message = msg
                    db.session.commit()
        except Exception:
            pass
        # Debounce status message edits
        if percent - last_percent[0] >= 15 or percent in (50, 95, 100):
            last_percent[0] = percent
            try:
                asyncio.run_coroutine_threadsafe(
                    status_msg.edit_text(f"⏳ {msg} ({percent}%)"), loop
                )
            except Exception:
                pass

    def record_worker(worker_name: str):
        try:
            with app.app_context():
                o = db.session.get(Order, order_id)
                if o:
                    o.worker_used = worker_name
                    db.session.commit()
        except Exception:
            pass

    try:
        result_path, message_count = await process_scraping(
            channel_link,
            order_token,
            limit=config.FREE_MESSAGE_LIMIT,
            progress_callback=update_progress,
            worker_callback=record_worker,
        )

        if not result_path or not os.path.exists(result_path):
            await status_msg.edit_text(
                "❌ Couldn't fetch this channel.\n\n"
                "It may be private, empty, or unreachable. Try another public channel."
            )
            with app.app_context():
                o = db.session.get(Order, order_id)
                if o:
                    o.status = "failed"
                    o.status_message = "Channel inaccessible from bot"
                    db.session.commit()
            _user_last_order.pop(user_id, None)
            return

        await status_msg.edit_text(f"✅ Got {message_count} messages. Uploading…")

        caption = (
            f"📂 *{channel_name}* — {message_count} messages\n"
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"📦 Free tier (last {config.FREE_MESSAGE_LIMIT})"
            + UPSELL.format(
                limit=config.FREE_MESSAGE_LIMIT,
                price=config.PAID_PRICE_USDT,
            )
        )
        with open(result_path, "rb") as fp:
            await update.message.reply_document(
                document=fp,
                filename=os.path.basename(result_path),
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
        try:
            await status_msg.delete()
        except Exception:
            pass

        with app.app_context():
            o = db.session.get(Order, order_id)
            if o:
                o.status = "completed"
                o.progress = 100
                o.status_message = "Delivered via bot"
                o.file_path = result_path
                o.message_count = message_count
                o.completed_at = datetime.utcnow()
                db.session.commit()
        log.info("Bot order #%s completed (%s messages)", order_id, message_count)

    except Exception as e:
        log.exception("Bot scrape failed for user %s", user_id)
        try:
            await status_msg.edit_text(
                f"❌ Something went wrong while exporting {channel_name}.\n\n"
                "Please try a different channel or try again later."
            )
        except Exception:
            pass
        with app.app_context():
            o = db.session.get(Order, order_id)
            if o:
                o.status = "failed"
                o.status_message = f"Bot error: {str(e)[:200]}"
                db.session.commit()
        _user_last_order.pop(user_id, None)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error("Unhandled exception in handler", exc_info=context.error)


# ============== Bootstrap ==============


def main():
    if not config.BOT_TOKEN:
        raise SystemExit("TG_BOT_TOKEN is not set in .env — bot cannot start.")
    log.info("TelegramtoCSV bot starting (python-telegram-bot, HTTP long-polling)...")

    application: Application = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("paid", paid_handler))
    application.add_handler(CommandHandler("contact", contact_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, channel_handler)
    )
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    main()
