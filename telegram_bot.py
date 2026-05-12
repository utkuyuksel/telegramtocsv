"""
TelegramtoCSV Telegram Bot — full-flow free tier interface.

Users send a public channel link to the bot. Bot calls the same
scraper engine the website uses (sharing the worker pool), exports
the last FREE_MESSAGE_LIMIT messages, and DMs the CSV (zipped) back.

Free tier only — paid orders go through the website (USDT TXID flow).

Runs as a separate process; the Flask web app (gunicorn) keeps running.
"""

import asyncio
import logging
import os
import re
import time
from datetime import datetime

from pyrogram import Client, filters, idle
from pyrogram.types import BotCommand, Message

import config
from app import app, db
from models import Order
from scraper_engine import process_scraping


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("tgcsv-bot")


# --- Rate limit ---
# One free export per user per hour. Resets on failure.
FREE_COOLDOWN_SEC = 3600
_user_last_order: dict[int, float] = {}


# Capture both https://t.me/<name>, http://t.me/<name>, t.me/<name>, @<name>
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


bot = Client(
    "telegramtocsv_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    workdir=os.path.dirname(os.path.abspath(__file__)),
)


@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    await message.reply_text(
        WELCOME.format(limit=config.FREE_MESSAGE_LIMIT, price=config.PAID_PRICE_USDT),
        disable_web_page_preview=True,
    )


@bot.on_message(filters.command("help") & filters.private)
async def help_handler(client, message: Message):
    await message.reply_text(
        HELP.format(limit=config.FREE_MESSAGE_LIMIT, price=config.PAID_PRICE_USDT),
        disable_web_page_preview=True,
    )


@bot.on_message(filters.command("paid") & filters.private)
async def paid_handler(client, message: Message):
    caption = (
        f"💎 *Unlimited export* — the whole channel archive.\n\n"
        f"Price: *${config.PAID_PRICE_USDT:.2f} USDT* (TRC20 / TRON network)\n"
        f"Wallet:\n`{config.WALLET_ADDRESS}`\n\n"
        f"*How to pay:*\n"
        f"1. Open [telegramtocsv.com](https://telegramtocsv.com)\n"
        f"2. Paste channel link → choose *Unlimited*\n"
        f"3. Send the USDT, paste your TXID → done\n\n"
        f"_Payment verification runs on the website (instant on-chain check)._"
    )
    qr_url = f"https://telegramtocsv.com/qr/wallet.png?v={config.WALLET_ADDRESS[:8]}"
    try:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=qr_url,
            caption=caption,
        )
    except Exception:
        # Fallback if URL fetch fails — just send the text
        await message.reply_text(caption, disable_web_page_preview=True)


@bot.on_message(filters.command("contact") & filters.private)
async def contact_handler(client, message: Message):
    await message.reply_text(
        "📧 *Contact*\n\n"
        "Email: riven2430@gmail.com\n"
        "Website: telegramtocsv.com\n\n"
        "Bug reports, feature requests, partnerships — all welcome. "
        "We read every message.",
        disable_web_page_preview=True,
    )


@bot.on_message(
    filters.text & filters.private & ~filters.command(["start", "help"])
)
async def channel_handler(client, message: Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    match = CHANNEL_LINK_RE.search(text)
    if not match:
        await message.reply_text(
            "❌ That doesn't look like a Telegram channel link.\n\n"
            "Send something like: `https://t.me/durov` or `@durov`",
            disable_web_page_preview=True,
        )
        return

    channel_name = match.group(1).lstrip("@")
    channel_link = f"https://t.me/{channel_name}"

    # --- Rate limit ---
    now = time.time()
    last = _user_last_order.get(user_id, 0)
    if now - last < FREE_COOLDOWN_SEC:
        remaining = int((FREE_COOLDOWN_SEC - (now - last)) / 60) + 1
        await message.reply_text(
            f"⏳ *Free tier cooldown.* You've used your free export this hour.\n\n"
            f"Try again in ~{remaining} min, or get unlimited (no cooldown) at telegramtocsv.com",
            disable_web_page_preview=True,
        )
        return
    _user_last_order[user_id] = now

    # --- Create DB order (tagged as bot source) ---
    username_tag = (
        message.from_user.username
        or message.from_user.first_name
        or "unknown"
    )[:64]
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

    log.info("Bot order #%s started for user %s (channel: %s)", order_id, user_id, channel_name)

    status_msg = await message.reply_text(f"🔍 Fetching `{channel_name}`… 5%")

    last_percent = [5]
    loop = asyncio.get_running_loop()

    def update_progress(percent: int, msg: str):
        # Debounce: only edit when 15%+ jump or special milestones, and update DB
        try:
            with app.app_context():
                o = db.session.get(Order, order_id)
                if o:
                    o.progress = percent
                    o.status_message = msg
                    db.session.commit()
        except Exception:
            pass
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
            # Don't burn the user's hourly slot on a server-side failure
            _user_last_order.pop(user_id, None)
            return

        # --- Send file ---
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
        await client.send_document(
            chat_id=message.chat.id,
            document=result_path,
            caption=caption,
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
                f"❌ Something went wrong while exporting `{channel_name}`.\n\n"
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


BOT_COMMANDS = [
    BotCommand("start", "Start using the bot"),
    BotCommand("help", "How to use this bot"),
    BotCommand("paid", "Get the unlimited plan"),
    BotCommand("contact", "Get in touch"),
]


async def main():
    await bot.start()
    try:
        await bot.set_bot_commands(BOT_COMMANDS)
        log.info("Slash commands registered: %s", [c.command for c in BOT_COMMANDS])
    except Exception:
        log.exception("Failed to register slash commands (continuing anyway)")
    log.info("TelegramtoCSV bot is ready.")
    await idle()
    await bot.stop()


if __name__ == "__main__":
    if not config.BOT_TOKEN:
        raise SystemExit("TG_BOT_TOKEN is not set in .env — bot cannot start.")
    log.info("TelegramtoCSV bot starting...")
    asyncio.run(main())
