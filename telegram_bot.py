import os

from pyrogram import Client, filters

import config
from app import app, db
from models import Order


bot = Client(
    "my_bot_session",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)


@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "👋 **Welcome to TG to CSV Bot!**\n\n"
            "To download a file, please start the process on our website:\n"
            "👉 https://telegramtocsv.com\n\n"
            "If you have a payment issue, contact support."
        )
        return

    token = message.command[1]
    await message.reply_text("🔍 Checking your order...")

    with app.app_context():
        order = db.session.query(Order).filter_by(token=token).first()

        if not order:
            await message.reply_text(
                "❌ **Invalid or expired token.**\nPlease create a new order on the website."
            )
            return

        if order.status != "completed":
            await message.reply_text(
                f"⏳ **Order is not ready yet.**\nCurrent status: {order.status}\nPlease wait for completion on the website."
            )
            return

        if not order.file_path or not os.path.exists(order.file_path):
            await message.reply_text(
                "❌ **File not found on server.**\nIt might have been deleted (files are kept for 1 hour)."
            )
            return

        try:
            await message.reply_text("✅ **File found!** Uploading now...")
            caption = (
                f"📂 **Channel:** {order.channel_link}\n"
                f"📦 **Plan:** {order.tier.upper()}\n"
                f"📅 **Date:** {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                "🚀 *Powered by TelegramToCSV*"
            )
            await client.send_document(
                chat_id=message.chat.id,
                document=order.file_path,
                caption=caption,
            )
        except Exception as e:
            await message.reply_text(f"❌ Upload error: {e}")


if __name__ == "__main__":
    if not config.BOT_TOKEN:
        raise SystemExit("TG_BOT_TOKEN is not set in .env — bot cannot start.")
    print("🤖 Bot starting...")
    bot.run()
