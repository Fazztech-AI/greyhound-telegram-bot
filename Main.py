import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TZ = ZoneInfo("Australia/Melbourne")


def build_daily_greyhound_message() -> str:
    """
    Version 1 uses mock picks.
    Later we replace this with live Sportsbet/race data scanning.
    """

    picks = [
        {
            "race": "Sandown R3",
            "selection": "#1 Place",
            "reason": "Short market, inside box, strong recent placings",
        },
        {
            "race": "Ballarat R5",
            "selection": "#2 Top 2",
            "reason": "Consistent runner, low-risk market profile",
        },
        {
            "race": "Warragul R7",
            "selection": "#4 Head-to-head",
            "reason": "Clearer form line than opponent",
        },
    ]

    today = datetime.now(TZ).strftime("%A %d %B %Y")

    lines = [
        f"🐕 Greyhound Scanner — {today}",
        "",
        "Suggested multi idea:",
    ]

    for i, pick in enumerate(picks, start=1):
        lines.append("")
        lines.append(f"Leg {i}: {pick['race']} — {pick['selection']}")
        lines.append(f"Reason: {pick['reason']}")

    lines.extend([
        "",
        "Risk: Low/Medium",
        "Stake idea: $5 max",
        "",
        "Reminder: manually verify odds, scratchings, race conditions, and Sportsbet market before placing anything.",
    ])

    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Bot is working ✅\n\nYour CHAT_ID is:\n{chat_id}\n\nSave this in Railway as CHAT_ID."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_daily_greyhound_message())


async def send_daily_scan(app: Application):
    if not CHAT_ID:
        logging.warning("CHAT_ID not set")
        return

    await app.bot.send_message(
        chat_id=CHAT_ID,
        text=build_daily_greyhound_message(),
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))

    scheduler = AsyncIOScheduler(timezone=TZ)

    scheduler.add_job(
        send_daily_scan,
        "cron",
        hour=8,
        minute=0,
        args=[app],
    )

    scheduler.start()

    app.run_polling()


if __name__ == "__main__":
    main()
