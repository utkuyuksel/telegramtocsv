#!/usr/bin/env bash
# Register the bot's slash menu via Telegram Bot HTTP API.
# Run once after setting up the bot, or after changing the command list.
# Requires TG_BOT_TOKEN from the project .env.

set -euo pipefail

if [[ -f "$(dirname "$0")/../.env" ]]; then
    # shellcheck disable=SC1091
    source <(grep '^TG_BOT_TOKEN=' "$(dirname "$0")/../.env")
fi

if [[ -z "${TG_BOT_TOKEN:-}" ]]; then
    echo "Error: TG_BOT_TOKEN not set (export it or put in .env)" >&2
    exit 1
fi

curl -sS -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/setMyCommands" \
    -H "Content-Type: application/json" \
    -d '{
        "commands": [
            {"command": "start",   "description": "Start using the bot"},
            {"command": "help",    "description": "How to use this bot"},
            {"command": "paid",    "description": "Get the unlimited plan"},
            {"command": "contact", "description": "Get in touch"}
        ]
    }' | python3 -m json.tool
