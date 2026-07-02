import os
import requests
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
BETFAIR_USERNAME = os.getenv("BETFAIR_USERNAME")
BETFAIR_PASSWORD = os.getenv("BETFAIR_PASSWORD")
BETFAIR_APP_KEY = os.getenv("BETFAIR_APP_KEY")

LOGIN_URL = "https://identitysso.betfair.com.au/api/login"
BETTING_URL = "https://api-au.betfair.com/exchange/betting/json-rpc/v1"

def safe_json(response):
    try:
        return response.json()
    except Exception:
        raise RuntimeError(
            f"Non-JSON response from Betfair.\n"
            f"HTTP {response.status_code}\n"
            f"Body preview:\n{response.text[:500]}"
        )

def betfair_login():
    response = requests.post(
        LOGIN_URL,
        data=f"username={BETFAIR_USERNAME}&password={BETFAIR_PASSWORD}",
        headers={
            "X-Application": BETFAIR_APP_KEY,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=20,
    )

    data = safe_json(response)

    if data.get("status") != "SUCCESS":
        raise RuntimeError(f"Login failed:\n{data}")

    return data["token"]

def betfair_call(session_token, method, params):
    payload = {
        "jsonrpc": "2.0",
        "method": f"SportsAPING/v1.0/{method}",
        "params": params,
        "id": 1,
    }

    response = requests.post(
        BETTING_URL,
        json=payload,
        headers={
            "X-Application": BETFAIR_APP_KEY,
            "X-Authentication": session_token,
            "Content-Type": "application/json",
        },
        timeout=20,
    )

    data = safe_json(response)

    if "error" in data:
        raise RuntimeError(f"API error:\n{data['error']}")

    return data["result"]

def get_greyhound_markets():
    session = betfair_login()

    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)

    return betfair_call(
        session,
        "listMarketCatalogue",
        {
            "filter": {
                "eventTypeIds": ["4339"],
                "marketCountries": ["AU"],
                "marketStartTime": {
                    "from": now.isoformat(),
                    "to": tomorrow.isoformat(),
                },
                "marketTypeCodes": ["WIN"],
            },
            "maxResults": "10",
            "marketProjection": ["EVENT", "RUNNER_DESCRIPTION", "MARKET_START_TIME"],
            "sort": "FIRST_TO_START",
        },
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🐕 Betfair Greyhound Scanner online.\n\nType /scan.")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Connecting to Betfair...")

    try:
        markets = get_greyhound_markets()

        if not markets:
            await update.message.reply_text("No AU greyhound WIN markets found.")
            return

        msg = "🐕 Betfair Greyhound Markets\n\n"

        for market in markets:
            event = market.get("event", {})
            venue = event.get("venue", "Unknown")
            name = market.get("marketName", "Unknown")
            start = market.get("marketStartTime", "")

            runners = market.get("runners", [])
            dogs = [r.get("runnerName", "Unknown") for r in runners[:4]]

            msg += f"• {venue} — {name}\n"
            msg += f"Start: {start}\n"
            msg += f"Dogs: {', '.join(dogs)}...\n\n"

        await update.message.reply_text(msg[:4000])

    except Exception as e:
        await update.message.reply_text(f"Betfair scanner error:\n{e}")

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    print("🤖 Betfair Greyhound Scanner Started")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.run_polling()

if __name__ == "__main__":
    main()
