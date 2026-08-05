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

# --- Admin ---
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

# --- Pricing / Hybrid model ---
FREE_MESSAGE_LIMIT = _int("FREE_MESSAGE_LIMIT", 500)

# Paid tier is a FLAT one-time price for the whole channel of ANY size — no
# per-message pricing, no cap. The message count is still fetched up front to
# validate the channel before payment, but the price is always this flat value.
PAID_PRICE_USDT = 4.00  # fixed flat price; NOT read from env (ignores any stale PAID_PRICE_USDT)
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS", "")

# --- Multi-network USDT payment config ---
# Per-network: wallet, USDT token contract, token DECIMALS (load-bearing — BSC
# USDT is 18 decimals, ETH/TRON are 6; the verifier computes amounts in raw
# integer units per network so this is never hardcoded), verifier kind, and
# keyless public JSON-RPC endpoints for the EVM chains (no API key required).
USDT_NETWORKS = {
    "TRC20": {
        "label": "USDT · TRON (TRC20)",
        "short": "TRON (TRC20)",
        "wallet": os.environ.get("WALLET_TRC20", os.environ.get("WALLET_ADDRESS", "")),
        "contract": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "decimals": 6,
        "kind": "tron",
        "rpc": None,  # Tron uses the Tronscan HTTP API, not JSON-RPC
        "min_confirmations": 1,
        "fee_note": "cheapest",
    },
    "BEP20": {
        "label": "USDT · BNB Smart Chain (BEP20)",
        "short": "BSC (BEP20)",
        "wallet": os.environ.get("WALLET_BEP20", "0x13283FE0f73dB30239f4a616853fc568a95634Ab"),
        "contract": "0x55d398326f99059fF775485246999027B3197955",
        "decimals": 18,  # <-- BSC USDT is 18 decimals (the money-bug guard)
        "kind": "evm",
        "rpc": [
            os.environ.get("BSC_RPC_URL", "https://bsc-dataseed.bnbchain.org"),
            "https://bsc.publicnode.com",
            "https://bsc-dataseed1.defibit.io",
        ],
        "min_confirmations": _int("BSC_MIN_CONF", 2),
        "fee_note": "low fee",
    },
    "ERC20": {
        "label": "USDT · Ethereum (ERC20)",
        "short": "Ethereum (ERC20)",
        "wallet": os.environ.get("WALLET_ERC20", "0x13283FE0f73dB30239f4a616853fc568a95634Ab"),
        "contract": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "decimals": 6,
        "kind": "evm",
        "rpc": [
            os.environ.get("ETH_RPC_URL", "https://ethereum.publicnode.com"),
            "https://eth.llamarpc.com",
            "https://eth.drpc.org",
        ],
        "min_confirmations": _int("ETH_MIN_CONF", 3),
        "fee_note": "high gas",
    },
}
DEFAULT_NETWORK = os.environ.get("DEFAULT_NETWORK", "TRC20")

def price_for(message_count):
    """Flat one-time price for a paid export (whole channel, any size).
    Returns (price, billable_count) — billable = full count, no cap."""
    return round(PAID_PRICE_USDT, 2), int(message_count or 0)

# --- Limits ---
DAILY_IP_LIMIT = _int("DAILY_IP_LIMIT", 100)
FILE_RETENTION_HOURS = _int("FILE_RETENTION_HOURS", 1)

# --- Paths ---
DOWNLOADS_DIR = "downloads"
SESSION_FILE = "session_strings.json"
DEAD_SESSION_FILE = "dead_sessions.json"
