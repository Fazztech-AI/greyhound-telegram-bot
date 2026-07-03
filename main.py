import os
import json
from datetime import date, timedelta

import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from topaz import TopazAPI

BOT_TOKEN = os.getenv("BOT_TOKEN")
TOPAZ_API_KEY = os.getenv("TOPAZ_API_KEY")

AUTHORITY_CODES = ["NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]


def make_topaz():
    return TopazAPI(TOPAZ_API_KEY)


def get_value(row, keys, default="Unknown"):
    for key in keys:
        if key in row and pd.notna(row[key]) and row[key] != "":
            return row[key]
    return default


def get_all_today_races():
    topaz = make_topaz()
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

            if races is None or len(races) == 0:
                continue

            for _, race in races.iterrows():
                race_dict = race.to_dict()
                race_dict["authority"] = code
                all_races.append(race_dict)

        except Exception as e:
            print(f"Error loading {code}: {e}")

    return all_races


def get_runners_for_race(race_id):
    topaz = make_topaz()

    try:
        runners = topaz.get_race_runs(race_id)

        if runners is None or len(runners) == 0:
            return []

        return runners.to_dict("records")

    except Exception as e:
        print(f"Runner error for race {race_id}: {e}")
        return []


def format_race_line(race):
    name = get_value(race, ["name", "raceName"], "Unknown Race")
    race_no = get_value(race, ["raceNumber"], "?")
    distance = get_value(race, ["distance"], "?")
    authority = race.get("authority", "?")
    start_time = get_value(race, ["startTime"], "")

    return f"• {authority} R{race_no} — {distance}m — {start_time}\n  {name}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Topaz Greyhound Scanner online.\n\nType /scan."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning all Australian greyhound races...")

    try:
        races = get_all_today_races()

        if not races:
            await update.message.reply_text("No races found today.")
            return

        vic_count = len([r for r in races if r.get("authority") == "VIC"])

        msg = "🐕 Today's Races Loaded\n\n"
        msg += f"Total races: {len(races)}\n"
        msg += f"VIC races: {vic_count}\n\n"
        msg += "First 15 races:\n\n"

        for race in races[:15]:
            msg += format_race_line(race) + "\n\n"

        msg += "Now testing runners from first available race..."

        await update.message.reply_text(msg[:4000])

        first_race = races[0]
        race_id = first_race.get("raceId")
        runners = get_runners_for_race(race_id)

        if not runners:
            await update.message.reply_text(
                f"No runners found for raceId {race_id}."
            )
            return

        runner_msg = "🐕 First Race Runners\n\n"
        runner_msg += format_race_line(first_race) + "\n\n"

        for runner in runners[:8]:
            box = get_value(runner, ["boxNumber", "box", "rugNumber"], "?")
            dog = get_value(runner, ["dogName", "name", "runnerName"], "Unknown Dog")
            trainer = get_value(runner, ["trainerName", "trainer"], "Unknown Trainer")
            scratched = get_value(runner, ["isScratched", "scratched"], False)

            runner_msg += f"Box {box}: {dog}\n"
            runner_msg += f"Trainer: {trainer}\n"
            runner_msg += f"Scratched: {scratched}\n\n"

        await update.message.reply_text(runner_msg[:4000])

    except Exception as e:
        await update.message.reply_text(f"Topaz scanner error:\n{e}")


async def debug_runners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Debugging runner fields...")

    races = get_all_today_races()
    if not races:
        await update.message.reply_text("No races found.")
        return

    race_id = races[0].get("raceId")
    runners = get_runners_for_race(race_id)

    if not runners:
        await update.message.reply_text("No runners found.")
        return

    await update.message.reply_text(
        json.dumps(runners[0], indent=2, default=str)[:4000]
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    if not TOPAZ_API_KEY:
        raise RuntimeError("TOPAZ_API_KEY missing")

    print("🚀 TOPAZ RUNNER VERSION STARTED")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("debugrunners", debug_runners))

    app.run_polling()


if __name__ == "__main__":
    main()
