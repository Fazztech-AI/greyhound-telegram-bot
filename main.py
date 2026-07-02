import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

SPORTSBET_URL = "https://www.sportsbet.com.au/racing-schedule/greyhound/today"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Sportsbet Greyhound Scanner\n\n"
        "Type /scan to test Sportsbet access."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Testing Sportsbet connection...")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            SPORTSBET_URL,
            headers=headers,
            timeout=20
        )

        message = (
            "✅ Sportsbet Test Complete\n\n"
            f"Status Code: {response.status_code}\n"
            f"Final URL:\n{response.url}\n\n"
            "First 500 characters:\n\n"
            f"{response.text[:500]}"
        )

        await update.message.reply_text(message[:4000])

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error\n\n{str(e)}"
        )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    print("🚀 SPORTSBET VERSION 1 STARTED")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))

    app.run_polling()


if __name__ == "__main__":
    main()
