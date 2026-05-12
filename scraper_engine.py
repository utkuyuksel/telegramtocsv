import os
import csv
import json
import random
import asyncio
import traceback
import zipfile
from datetime import datetime

from pyrogram import Client
from pyrogram.errors import FloodWait

import config

DOWNLOADS_DIR = config.DOWNLOADS_DIR
SESSION_FILE = config.SESSION_FILE
DEAD_SESSION_FILE = config.DEAD_SESSION_FILE


def load_sessions():
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


SESSION_STRINGS = load_sessions()


def remove_bad_session(worker_name, error_reason="Unknown"):
    global SESSION_STRINGS
    try:
        if worker_name in SESSION_STRINGS:
            print(f"[SYSTEM] Dead session removed: {worker_name}")
            dead_entry = {
                "session_string": SESSION_STRINGS[worker_name],
                "died_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "reason": str(error_reason),
            }
            dead_sessions = {}
            if os.path.exists(DEAD_SESSION_FILE):
                try:
                    with open(DEAD_SESSION_FILE, "r") as f:
                        dead_sessions = json.load(f)
                except Exception:
                    pass

            dead_sessions[worker_name] = dead_entry
            with open(DEAD_SESSION_FILE, "w") as f:
                json.dump(dead_sessions, f, indent=2)

            del SESSION_STRINGS[worker_name]
            with open(SESSION_FILE, "w") as f:
                json.dump(SESSION_STRINGS, f, indent=2)
    except Exception:
        pass


class SessionManager:
    def __init__(self, worker_prefix=""):
        self.session_items = list(SESSION_STRINGS.items())
        if self.session_items:
            random.shuffle(self.session_items)

        self.worker_queue = self.session_items.copy()
        self.active_clients = {}
        self.worker_prefix = worker_prefix

    async def get_next_worker(self):
        if not self.worker_queue:
            global SESSION_STRINGS
            SESSION_STRINGS = load_sessions()
            if not SESSION_STRINGS:
                raise Exception("No active workers available! Please add accounts.")
            self.session_items = list(SESSION_STRINGS.items())
            self.worker_queue = self.session_items.copy()
            random.shuffle(self.worker_queue)

        worker_name, session_string = self.worker_queue.pop(0)

        if worker_name in self.active_clients:
            return self.active_clients[worker_name], worker_name

        return await self._start_worker(worker_name, session_string)

    async def _start_worker(self, worker_name, session_string):
        try:
            app = Client(
                name=f"{self.worker_prefix}_{worker_name}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=session_string,
                in_memory=True,
                sleep_threshold=0,
                no_updates=True,
            )
            await app.start()
            self.active_clients[worker_name] = app
            return app, worker_name
        except Exception as e:
            remove_bad_session(worker_name, error_reason=e)
            return await self.get_next_worker()

    async def rotate_worker(self, current_app, current_worker):
        try:
            await current_app.stop()
        except Exception:
            pass
        if current_worker in self.active_clients:
            del self.active_clients[current_worker]
        return await self.get_next_worker()

    async def cleanup(self):
        for _, app in self.active_clients.items():
            try:
                await app.stop()
            except Exception:
                pass
        self.active_clients.clear()


async def process_scraping(
    channel_link,
    order_token,
    limit=None,
    include_media=False,
    progress_callback=None,
    worker_callback=None,
):
    """
    Scrape a Telegram channel into a zipped CSV.

    limit: hard cap on messages (None = unlimited; free tier passes 500).
    worker_callback: called with (worker_name) when a worker is selected, so
                     the caller can persist which worker handled this order.
    Returns: (zip_path, processed_count) on success, or (None, 0) on failure.
    """
    try:
        manager = SessionManager(worker_prefix=f"[{order_token[:5]}]")
    except Exception:
        return None, 0

    app = None
    processed = 0

    try:
        channel_name = channel_link.split("/")[-1].replace("@", "").strip()

        if progress_callback:
            progress_callback(10, "Connecting to Telegram...")
        app, current_worker = await manager.get_next_worker()
        if worker_callback:
            worker_callback(current_worker)

        try:
            chat = await app.get_chat(channel_name)
            total_count = await app.get_chat_history_count(channel_name)
        except Exception as e:
            print(f"Channel not found: {e}")
            return None, 0

        if total_count == 0:
            return None, 0

        target_count = total_count if limit is None else min(limit, total_count)

        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        base_filename = f"{channel_name}_{order_token}"
        csv_path = os.path.join(DOWNLOADS_DIR, f"{base_filename}.csv")

        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Message ID", "Date", "Content", "Views", "Link"])

            offset_id = 0

            while processed < target_count:
                try:
                    messages = []
                    async for msg in app.get_chat_history(
                        channel_name, limit=100, offset_id=offset_id
                    ):
                        messages.append(msg)

                    if not messages:
                        break

                    for msg in messages:
                        if processed >= target_count:
                            break
                        processed += 1
                        try:
                            text = msg.text or msg.caption or "[Media/File]"
                            link = f"https://t.me/{channel_name}/{msg.id}"
                            date = (
                                msg.date.strftime("%Y-%m-%d %H:%M:%S")
                                if msg.date
                                else ""
                            )
                            views = msg.views or 0
                            writer.writerow([msg.id, date, text, views, link])
                            offset_id = msg.id
                        except Exception:
                            continue

                        if progress_callback and processed % 50 == 0:
                            percent = 10 + int((processed / target_count) * 80)
                            progress_callback(
                                percent,
                                f"Scraping: {processed}/{target_count} messages...",
                            )

                except FloodWait as e:
                    print(f"FloodWait: {e.value}s. Rotating worker...")
                    app, current_worker = await manager.rotate_worker(
                        app, current_worker
                    )
                    if worker_callback:
                        worker_callback(current_worker)
                except Exception:
                    app, current_worker = await manager.rotate_worker(
                        app, current_worker
                    )
                    if worker_callback:
                        worker_callback(current_worker)

        if progress_callback:
            progress_callback(95, "Compressing file...")

        zip_path = os.path.join(DOWNLOADS_DIR, f"{base_filename}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(csv_path, arcname=f"{channel_name}.csv")

        try:
            os.remove(csv_path)
        except Exception:
            pass

        if progress_callback:
            progress_callback(100, "Completed!")
        return zip_path, processed

    except Exception:
        traceback.print_exc()
        return None, processed
    finally:
        await manager.cleanup()
