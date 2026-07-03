import os
from datetime import date, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from topaz import TopazAPI

BOT_TOKEN = os.getenv("BOT_TOKEN")
TOPAZ_API_KEY = os.getenv("TOPAZ_API_KEY")

AUTHORITY_CODES = ["NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]


def get_today_races():
    topaz = TopazAPI(TOPAZ_API_KEY)

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    all_races = []

    for code in AUTHORITY_CODES:
        try:
            races = topaz.get_races(
                from_date=today,
                to_date=tomorrow,
                owning_authority_code=code,
            )

            if races is not None and len(races) > 0:
                for _, race in races.iterrows():
                    all_races.append(
                        {
                            "authority": code,
                            "race_id": race.get("raceId"),
                            "track": race.get("trackName") or race.get("venueName") or "Unknown",
                            "race_number": race.get("raceNumber", "?"),
                            "distance": race.get("distance", "?"),
                            "start_time": race.get("startTime") or race.get("raceStartTime") or "",
                        }
                    )
        except Exception as e:
            print(f"Topaz error for {code}: {e}")

    return all_races


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Inspecting first Topaz race...")

    try:
        races = get_today_races()

        if not races:
            await update.message.reply_text("No races.")
            return

        import json

        await update.message.reply_text(
            json.dumps(races[0], indent=2)[:4000]
        )

    except Exception as e:
        await update.message.reply_text(str(e))

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    if not TOPAZ_API_KEY:
        raise RuntimeError("TOPAZ_API_KEY missing")

    print("🚀 TOPAZ VERSION 1 STARTED")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.run_polling()


if __name__ == "__main__":
    main()
