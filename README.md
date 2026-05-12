# TelegramtoCSV

Flask web app that exports the message history of a public Telegram channel to a downloadable CSV (zipped). Uses a pool of Pyrogram worker accounts for FloodWait rotation.

## Hybrid Monetization Model

- **Free tier** — last `FREE_MESSAGE_LIMIT` messages (default 500), ad-supported, daily IP rate limit.
- **Paid tier** — whole channel history, ad-free, `PAID_PRICE_USDT` USDT (TRC20) one-time. Payment is verified on-chain via Tronscan.

## Setup

1. Copy env and fill values:
   ```
   cp .env.example .env
   ```
   At minimum set: `TG_API_ID`, `TG_API_HASH`, `ADMIN_PASSWORD`, `WALLET_ADDRESS`, `FLASK_SECRET_KEY`.

2. Install deps:
   ```
   pip install -r requirements.txt
   ```

3. Add Pyrogram worker accounts. If you already have `.session` files in `sessions/`, convert them once:
   ```
   python convert_to_string.py
   ```
   …then they will be in `session_strings.json`. You can also add them via the Admin Panel.

4. Run:
   ```
   python app.py
   ```
   The site runs at `http://0.0.0.0:8000/`.

## Admin Panel

`/admin/login` — login with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`.

Pages:
- **Dashboard** — daily/weekly/monthly orders + revenue, worker count, success rate, recent activity.
- **Orders** — filter by status/tier, search by channel/token/IP, delete.
- **Workers** — per-worker stats (success/fail/messages handled, last used), add/remove workers, dead session archive.
- **Payments** — paid orders with TXID, manual verify button for stuck payments.

## File Layout

```
app.py                # Flask app factory, public routes, scraper runner thread
admin.py              # Admin blueprint (/admin/*)
config.py             # Env-based config loader
models.py             # SQLAlchemy Order model
scraper_engine.py     # Pyrogram worker pool + scraper
crypto_utils.py       # TRC20 USDT/TRX TXID verification
templates/
  index.html          # Public landing page (with tier selector + payment widget)
  privacy.html
  admin/              # Admin panel templates
convert_to_string.py  # One-off: .session files → session strings
manage_sessions.py    # CLI worker management (Admin Panel is preferred now)
telegram_bot.py       # Optional Telegram bot for delivering files via /start <token>
```

## Production Notes

- Put the app behind Cloudflare to hide the server IP from Telegram and get free DDoS / bot protection.
- Replace the AdSense placeholder in `app.py:ads_txt` with your real publisher ID once approved (AdSense is strict about scraper sites; consider Adsterra / PropellerAds as fallback).
- Files in `downloads/` are auto-deleted after `FILE_RETENTION_HOURS` (default 1 hour).
- `.env` and `session_strings.json` are in `.gitignore` — never commit them.
