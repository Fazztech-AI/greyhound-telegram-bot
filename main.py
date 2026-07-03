import os
import json
from datetime import date, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from topaz import TopazAPI

BOT_TOKEN = os.getenv("BOT_TOKEN")
TOPAZ_API_KEY = os.getenv("TOPAZ_API_KEY")

AUTHORITY_CODES = ["NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]


def fetch_races_debug():
    topaz = TopazAPI(TOPAZ_API_KEY)

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    for code in AUTHORITY_CODES:
        try:
            races = topaz.get_races(
                from_date=today,
                to_date=tomorrow,
                owning_authority_code=code,
            )

            if races is not None and len(races) > 0:
                first_row = races.iloc[0].to_dict()

                return {
                    "authority": code,
                    "columns": list(races.columns),
                    "first_race": first_row,
                }

        except Exception as e:
            print(f"Error for {code}: {e}")

    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Topaz Greyhound Scanner online.\n\nType /scan."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Inspecting Topaz race data...")

    try:
        result = fetch_races_debug()

        if not result:
            await update.message.reply_text("No Topaz races found today.")
            return

        msg = (
            "🐕 TOPAZ DEBUG RESULT\n\n"
            f"Authority: {result['authority']}\n\n"
            "Columns:\n"
            f"{result['columns']}\n\n"
            "First race:\n"
            f"{json.dumps(result['first_race'], indent=2, default=str)}"
        )

        await update.message.reply_text(msg[:4000])

    except Exception as e:
        await update.message.reply_text(f"Topaz error:\n{e}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    if not TOPAZ_API_KEY:
        raise RuntimeError("TOPAZ_API_KEY missing")

    print("🚀 TOPAZ DEBUG VERSION STARTED")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.run_polling()


if __name__ == "__main__":
    main()
