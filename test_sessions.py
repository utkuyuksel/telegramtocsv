import asyncio
import os

from pyrogram import Client

import config


async def test_session(session_name):
    try:
        print(f"\n🔍 Testing: {session_name}")
        app = Client(
            session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            workdir="sessions",
        )
        async with app:
            me = await app.get_me()
            print(f"✅ OK: @{me.username} ({me.first_name})")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_all_sessions():
    print("🧪 Session test starting...")
    if not os.path.exists("sessions"):
        print("❌ 'sessions' folder not found.")
        return 0

    valid = 0
    files = [f for f in os.listdir("sessions") if f.endswith(".session")]
    for f in files:
        if await test_session(f.replace(".session", "")):
            valid += 1
    print(f"\n📊 Result: {valid}/{len(files)} valid sessions")
    return valid


if __name__ == "__main__":
    if not config.API_ID or not config.API_HASH:
        raise SystemExit("TG_API_ID / TG_API_HASH not set in .env.")
    asyncio.run(test_all_sessions())
