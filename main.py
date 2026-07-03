import os
import math
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


def is_valid(value):
    return value is not None and not pd.isna(value)


def get_all_today_races():
    topaz = make_topaz()
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    races_out = []

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
                r = race.to_dict()
                r["authority"] = code
                races_out.append(r)

        except Exception as e:
            print(f"Race load error {code}: {e}")

    return races_out


def get_runners_for_race(race_id):
    topaz = make_topaz()

    try:
        runners = topaz.get_race_runs(race_id)

        if runners is None or len(runners) == 0:
            return []

        return runners.to_dict("records")

    except Exception as e:
        print(f"Runner load error {race_id}: {e}")
        return []


def parse_last5(last5):
    if not isinstance(last5, str):
        return []

    nums = []
    for ch in last5:
        if ch.isdigit():
            nums.append(int(ch))

    return nums


def score_runner(runner, field):
    score = 0
    reasons = []

    if runner.get("scratched") is True:
        return 0, ["Scratched"]

    rating = runner.get("rating")
    if is_valid(rating) and rating > 0:
        score += min(20, rating / 5)
        reasons.append(f"Rating {rating}")

    avg_speed = runner.get("averageSpeed")
    field_speeds = [
        r.get("averageSpeed") for r in field
        if is_valid(r.get("averageSpeed")) and r.get("averageSpeed") > 0
    ]

    if is_valid(avg_speed) and avg_speed > 0 and field_speeds:
        best_speed = max(field_speeds)
        if avg_speed == best_speed:
            score += 20
            reasons.append("Best average speed")
        else:
            score += max(0, 15 * (avg_speed / best_speed))

    best_time = runner.get("bestTime")
    field_times = [
        r.get("bestTime") for r in field
        if is_valid(r.get("bestTime")) and isinstance(r.get("bestTime"), (int, float)) and r.get("bestTime") > 0
    ]

    if is_valid(best_time) and isinstance(best_time, (int, float)) and best_time > 0 and field_times:
        fastest_time = min(field_times)
        if best_time == fastest_time:
            score += 20
            reasons.append("Fastest best time")
        else:
            score += max(0, 15 * (fastest_time / best_time))

    last5 = parse_last5(runner.get("last5"))
    if last5:
        top3 = sum(1 for pos in last5 if pos <= 3)
        wins = sum(1 for pos in last5 if pos == 1)

        score += top3 * 3
        score += wins * 2

        if top3 >= 4:
            reasons.append("Very consistent recent form")
        elif top3 >= 3:
            reasons.append("Good recent form")

    box = runner.get("boxNumber") or runner.get("rugNumber")
    if box in [1, 2]:
        score += 10
        reasons.append("Good inside box")
    elif box in [3, 4, 5]:
        score += 5
    elif box in [7, 8]:
        score += 3

    total_form_count = runner.get("totalFormCount")
    if is_valid(total_form_count):
        if total_form_count == 0:
            score -= 15
            reasons.append("Limited exposed form")
        elif total_form_count >= 5:
            score += 5

    return round(max(0, min(score, 100)), 1), reasons


def scan_best_bets(limit=8):
    races = get_all_today_races()
    picks = []

    for race in races:
        race_id = race.get("raceId")
        runners = get_runners_for_race(race_id)

        if len(runners) < 4:
            continue

        active_runners = [r for r in runners if r.get("scratched") is not True]

        if len(active_runners) < 4:
            continue

        scored = []

        for runner in active_runners:
            score, reasons = score_runner(runner, active_runners)
            scored.append((score, runner, reasons))

        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_runner, reasons = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0

        margin = best_score - second_score

        if best_score >= 55 and margin >= 5:
            picks.append({
                "score": best_score,
                "margin": round(margin, 1),
                "race": race,
                "runner": best_runner,
                "reasons": reasons,
            })

    picks.sort(key=lambda x: x["score"], reverse=True)
    return picks[:limit]


def format_pick(pick, index):
    race = pick["race"]
    runner = pick["runner"]

    track = runner.get("track") or "Unknown Track"
    race_no = race.get("raceNumber", "?")
    authority = race.get("authority", "?")
    distance = race.get("distance", "?")
    start = race.get("startTime", "")
    dog = runner.get("dogName", "Unknown Dog")
    box = runner.get("boxNumber") or runner.get("rugNumber") or "?"
    trainer = runner.get("trainerName", "Unknown Trainer")

    reasons = pick["reasons"][:4]
    reason_text = "\n".join([f"✔ {r}" for r in reasons]) if reasons else "✔ Top ranked by model"

    return (
        f"{index}. ⭐ {pick['score']}/100\n"
        f"{track} R{race_no} ({authority}) — {distance}m — {start}\n"
        f"Dog: Box {box} {dog}\n"
        f"Trainer: {trainer}\n"
        f"Edge over 2nd: {pick['margin']} pts\n"
        f"{reason_text}\n"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Greyhound Scanner online.\n\n"
        "Type /scan for today's model picks."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning all races and scoring runners...")

    try:
        picks = scan_best_bets()

        if not picks:
            await update.message.reply_text(
                "No high-probability picks found yet.\n\n"
                "This is good — the bot should skip messy days/races."
            )
            return

        msg = "🐕 Today's Top Model Picks\n\n"

        for i, pick in enumerate(picks, start=1):
            msg += format_pick(pick, i) + "\n"

        msg += (
            "Note: This is Version 1 scoring using Topaz form data only. "
            "Verify odds and scratchings before betting."
        )

        await update.message.reply_text(msg[:4000])

    except Exception as e:
        await update.message.reply_text(f"Scanner error:\n{e}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    if not TOPAZ_API_KEY:
        raise RuntimeError("TOPAZ_API_KEY missing")

    print("🚀 TOPAZ SCORING VERSION STARTED")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.run_polling()


if __name__ == "__main__":
    main()
