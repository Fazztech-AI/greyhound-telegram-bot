import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
FORM_GUIDE_URL = "https://www.thegreyhoundrecorder.com.au/form-guides/"

def get_meetings():
    headers = {"User-Agent": "Mozilla/5.0 GreyhoundScannerBot/1.0"}
    response = requests.get(FORM_GUIDE_URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    tracks = [
        "Sandown", "The Meadows", "Ballarat", "Bendigo", "Geelong",
        "Warragul", "Shepparton", "Traralgon", "Healesville",
        "Horsham", "Sale", "Warrnambool", "Angle Park", "Albion Park",
        "Wentworth Park", "Richmond", "Dapto", "Gosford",
        "Cannington", "Mandurah", "Hobart", "Launceston", "Darwin",
        "Ipswich", "Maitland", "Grafton", "Casino", "Dubbo",
        "Gawler", "Murray Bridge", "Northam", "Townsville"
    ]

    found = []
    for track in tracks:
        if re.search(rf"\b{re.escape(track)}\b", text, re.IGNORECASE):
            found.append(track)

    return sorted(set(found))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Greyhound Scanner Bot is online!\n\nType /scan to scan today’s meetings."
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning live greyhound meetings...")

    try:
        meetings = get_meetings()

        if not meetings:
            await update.message.reply_text(
                "No meetings found from this source. We may need another data source."
            )
            return

        msg = "🐕 Today’s Greyhound Meetings\n\n"
        for meeting in meetings:
            msg += f"• {meeting}\n"

        msg += "\nNext step: pull races from each meeting."
        await update.message.reply_text(msg)

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
