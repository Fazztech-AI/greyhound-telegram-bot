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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Topaz Greyhound Scanner online.\n\nType /scan."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning Topaz races...")

    try:
        races = get_today_races()

        if not races:
            await update.message.reply_text(
                "No races found from Topaz today, or your key does not have access to this endpoint."
            )
            return

        msg = "🐕 Today's Topaz Races\n\n"

        for race in races[:25]:
            msg += (
                f"• {race['track']} R{race['race_number']} "
                f"({race['authority']}) — {race['distance']}m\n"
                f"  ID: {race['race_id']}\n"
            )

        msg += "\nNext step: pull runners for each race."

        await update.message.reply_text(msg[:4000])

    except Exception as e:
        await update.message.reply_text(f"Topaz scanner error:\n{e}")


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
