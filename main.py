from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import Application, CommandHandler, MessageHandler, filters

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
    update_command,
)
from database import initialise_database
from results_updater import update_results

MELBOURNE = ZoneInfo("Australia/Melbourne")


async def nightly_update(context):
    try:
        updated, skipped, reasons = update_results()

        print(
            f"🌙 Nightly results update complete. "
            f"Updated={updated}, Skipped={skipped}"
        )

        if reasons:
            for reason in reasons:
                print(reason)

    except Exception as e:
        print(f"Nightly update failed: {e}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")
    if not TOPAZ_API_KEY:
        raise RuntimeError("TOPAZ_API_KEY missing")

    print("🚀 GREYHOUND AI V1.0 STARTED")

    initialise_database()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("tracks", tracks_command))
    app.add_handler(CommandHandler("track", track_command))
    app.add_handler(CommandHandler("race", race_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("record", record_command))
    app.add_handler(CommandHandler("update", update_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_message))

    app.job_queue.run_daily(
        nightly_update,
        time=time(hour=0, minute=30, tzinfo=MELBOURNE),
        name="nightly_results_update",
    )

    app.run_polling()


if __name__ == "__main__":
    main()
