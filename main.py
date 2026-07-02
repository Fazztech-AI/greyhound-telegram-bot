import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

SPORTSBET_URL = "https://www.sportsbet.com.au/racing-schedule/greyhound/today"

def test_sportsbet_access():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    response = requests.get(SPORTSBET_URL, headers=headers, timeout=20)

    return {
        "status": response.status_code,
        "url": response.url,
        "text_preview": response.text[:500],
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Greyhound Scanner Bot online.\n\nType /scan to test Sportsbet access."
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Testing Sportsbet access...")

    try:
        result = test_sportsbet_access()

        msg = (
            "Sportsbet Access Test\n\n"
            f"HTTP Status: {result['status']}\n"
            f"Final URL: {result['url']}\n\n"
            f"Preview:\n{result['text_preview']}"
        )

        await update.message.reply_text(msg[:4000])

    except Exception as e:
        await update.message.reply_text(f"Sportsbet test error:\n{e}")

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    print("🤖 Sportsbet Greyhound Scanner Started")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.run_polling()

if __name__ == "__main__":
    main()
