import asyncio
import json
import os

from pyrogram import Client

import config


async def convert_sessions():
    """One-off helper: turns each .session file in sessions/ into a Pyrogram
    session string and writes them all to session_strings.json."""
    session_strings = {}

    if not os.path.exists("sessions"):
        print("❌ 'sessions' folder not found.")
        return

    session_files = [f for f in os.listdir("sessions") if f.endswith(".session")]
    if not session_files:
        print("❌ No .session files found.")
        return

    print(f"🔍 Found {len(session_files)} session files")

    for f in session_files:
        session_name = f.replace(".session", "")
        session_path = os.path.join("sessions", f)

        if os.path.getsize(session_path) < 100:
            print(f"⚠️  {session_name}: file too small (likely empty)")
            continue

        app = None
        try:
            print(f"🔄 Converting {session_name}...")
            app = Client(
                session_name,
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                workdir="sessions",
            )
            await app.start()
            string = await app.export_session_string()
            session_strings[session_name] = string

            me = await app.get_me()
            label = f"@{me.username}" if me.username else me.first_name
            print(f"✅ {session_name}: {label}")

            await app.stop()
            await asyncio.sleep(3)
        except Exception as e:
            print(f"❌ {session_name}: {str(e)[:100]}")
            if app:
                try:
                    await app.stop()
                except Exception:
                    pass

    if session_strings:
        with open("session_strings.json", "w") as f:
            json.dump(session_strings, f, indent=2)
        print(f"\n🎉 {len(session_strings)} sessions converted and saved.")
    else:
        print("\n⚠️  No sessions converted.")

    return session_strings


if __name__ == "__main__":
    if not config.API_ID or not config.API_HASH:
        raise SystemExit("TG_API_ID / TG_API_HASH not set in .env.")
    asyncio.run(convert_sessions())
