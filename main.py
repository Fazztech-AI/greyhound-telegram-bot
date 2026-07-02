import os
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

    meetings = []

    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True)
        href = link["href"]

        if not text:
            continue

        if "/form-guides/" in href and len(text) < 40:
            if href.startswith("/"):
                href = "https://www.thegreyhoundrecorder.com.au" + href

            meetings.append({
                "name": text,
                "url": href
            })

    # remove duplicates
    unique = {}
    for meeting in meetings:
        unique[meeting["name"]] = meeting["url"]

    return unique

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Greyhound Scanner Bot is online!\n\nType /scan to scan today’s meetings."
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scanning meeting links...")

    try:
        meetings = get_meetings()

        if not meetings:
            await update.message.reply_text("No meeting links found.")
            return

        msg = "🐕 Today’s Greyhound Meetings\n\n"

        for name, url in list(meetings.items())[:20]:
            msg += f"• {name}\n{url}\n\n"

        msg += "Next step: open each meeting and pull Race 1, Race 2, Race 3 etc."

        await update.message.reply_text(msg[:4000])

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
