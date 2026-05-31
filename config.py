import math
import os
from pathlib import Path


def _load_env_file():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# --- Telegram API ---
API_ID = _int("TG_API_ID", 0)
API_HASH = os.environ.get("TG_API_HASH", "")
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")

# --- Flask ---
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())
DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///database.db")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = _int("PORT", 8000)

# --- AdSense ---
ADSENSE_PUB_ID = os.environ.get("ADSENSE_PUB_ID", "pub-XXXXXXXXXXXXXXXX")

# --- Admin ---
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

# --- Pricing / Hybrid model ---
FREE_MESSAGE_LIMIT = _int("FREE_MESSAGE_LIMIT", 500)

# Paid tier is priced "by size": the user gets an exact quote (from the channel's
# message count) BEFORE paying. Price scales per 1,000 messages with a minimum.
# The WHOLE channel is exported — there is no message cap.
PAID_PRICE_PER_1K_USDT = _float("PAID_PRICE_PER_1K_USDT", 0.50)
PAID_MIN_PRICE_USDT = _float("PAID_MIN_PRICE_USDT", 3.00)
# Optional price ceiling: if > 0, no single export ever costs more than this, no
# matter how large the channel ("full archive of any channel, max $X"). 0 = off.
PAID_MAX_PRICE_USDT = _float("PAID_MAX_PRICE_USDT", 15.00)
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS", "")

# Back-compat: templates and the bot still read a single "from" price.
PAID_PRICE_USDT = PAID_MIN_PRICE_USDT


def price_for(message_count):
    """By-size quote for a paid export (whole channel, no message cap).
    Returns (price, billable_count)."""
    billable = int(message_count or 0)
    units = math.ceil(billable / 1000) if billable > 0 else 0
    price = max(PAID_MIN_PRICE_USDT, units * PAID_PRICE_PER_1K_USDT)
    if PAID_MAX_PRICE_USDT > 0:
        price = min(price, PAID_MAX_PRICE_USDT)
    return round(price, 2), billable

# --- Limits ---
DAILY_IP_LIMIT = _int("DAILY_IP_LIMIT", 100)
FILE_RETENTION_HOURS = _int("FILE_RETENTION_HOURS", 1)

# --- Paths ---
DOWNLOADS_DIR = "downloads"
SESSION_FILE = "session_strings.json"
DEAD_SESSION_FILE = "dead_sessions.json"
