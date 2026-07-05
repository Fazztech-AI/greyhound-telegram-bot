from telegram.ext import Application, CommandHandler, MessageHandler, filters
from zoneinfo import ZoneInfo
from config import BOT_TOKEN, TOPAZ_API_KEY
from commands import (
    start,
    scan,
    tracks_command,
    track_command,
    race_command,
    natural_message,
    history_command,
    stats_command,
    record_command,
)
from database import initialise_database

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")
    if not TOPAZ_API_KEY:
        raise RuntimeError("TOPAZ_API_KEY missing")

    print("🚀 GREYHOUND AI V1.0 STARTED")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("tracks", tracks_command))
    app.add_handler(CommandHandler("track", track_command))
    app.add_handler(CommandHandler("race", race_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_message))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("stats", stats_command))  
    app.add_handler(CommandHandler("record", record_command))

    app.run_polling()

if __name__ == "__main__":
    main()
