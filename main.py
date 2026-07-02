import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

RACECARDS_URL = "https://www.thedogs.com.au/racing/racecards"

def get_today_meetings():
    headers = {
        "User-Agent": "Mozilla/5.0 GreyhoundScannerBot/1.0"
    }

    response = requests.get(RACECARDS_URL, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    possible_tracks = [
        "Sandown",
        "The Meadows",
        "Ballarat",
        "Bendigo",
        "Geelong",
        "Warragul",
        "Shepparton",
        "Traralgon",
        "Healesville",
        "Horsham",
        "Sale",
        "Warrnambool",
        "Angle Park",
        "Albion Park",
        "Wentworth Park",
        "Richmond",
        "Dapto",
        "Gosford",
        "Cannington",
        "Mandurah",
        "Hobart",
        "Launceston",
        "Darwin",
    ]

    found = []

    for track in possible_tracks:
        if re.search(rf"\b{re.escape(track)}\b", text, re.IGNORECASE):
            found.append(track)

    return sorted(set(found))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Greyhound Scanner Bot is online!\n\nType /scan to scan today’s meetings."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning today’s greyhound meetings...")

    try:
        meetings = get_today_meetings()

        if not meetings:
            await update.message.reply_text(
                "No meetings found yet. The racecard page may have changed or there may be no listed meetings."
            )
            return

        message = "🐕 Today’s Greyhound Meetings\n\n"
        for meeting in meetings:
            message += f"• {meeting}\n"

        message += "\nNext step: we’ll pull races and dogs from each meeting."

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"Scanner error:\n{e}")


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    print("🤖 Greyhound Scanner Bot Started")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.run_polling()


if __name__ == "__main__":
    main()
