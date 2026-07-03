import os
import re
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
                r = race.to_dict()
                r["authority"] = code
                all_races.append(r)

        except Exception as e:
            print(f"Race load error {code}: {e}")

    return all_races


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


def confidence_label(score):
    if score >= 70:
        return "🔥 Strong"
    if score >= 50:
        return "✅ Usable"
    if score >= 35:
        return "⚠️ Speculative"
    return "🧊 Low"


def score_runner(runner, field):
    score = 0
    reasons = []

    if runner.get("scratched") is True or runner.get("isLateScratching") is True:
        return 0, ["Scratched"]

    rating = runner.get("rating")
    if is_valid(rating) and rating > 0:
        pts = min(20, float(rating) / 5)
        score += pts
        reasons.append(f"Rating {rating}")

    avg_speed = runner.get("averageSpeed")
    field_speeds = [
        r.get("averageSpeed")
        for r in field
        if is_valid(r.get("averageSpeed")) and r.get("averageSpeed") > 0
    ]

    if is_valid(avg_speed) and avg_speed > 0 and field_speeds:
        best_speed = max(field_speeds)
        if avg_speed == best_speed:
            score += 20
            reasons.append("Best average speed")
        else:
            score += max(0, 15 * (avg_speed / best_speed))

    best_finish_td = runner.get("bestFinishTrackAndDistance")
    if is_valid(best_finish_td):
        try:
            best_finish_td = int(best_finish_td)
            if best_finish_td == 1:
                score += 15
                reasons.append("Has won track/distance")
            elif best_finish_td <= 3:
                score += 10
                reasons.append("Placed track/distance")
        except Exception:
            pass

    last5 = parse_last5(runner.get("last5"))
    if last5:
        top3 = sum(1 for pos in last5 if pos <= 3)
        wins = sum(1 for pos in last5 if pos == 1)

        score += top3 * 4
        score += wins * 3

        if top3 >= 4:
            reasons.append("Very consistent last 5")
        elif top3 >= 3:
            reasons.append("Good recent form")
        elif wins >= 1:
            reasons.append("Recent winner")
    else:
        score -= 5
        reasons.append("Limited last-5 form")

    box = runner.get("boxNumber") or runner.get("rugNumber")
    try:
        box = int(box)
        if box in [1, 2]:
            score += 12
            reasons.append("Good inside box")
        elif box in [3, 4]:
            score += 7
        elif box in [5, 6]:
            score += 3
        elif box in [7, 8]:
            score += 4
    except Exception:
        pass

    total_form_count = runner.get("totalFormCount")
    if is_valid(total_form_count):
        try:
            total_form_count = int(total_form_count)
            if total_form_count == 0:
                score -= 8
                reasons.append("No exposed form")
            elif total_form_count >= 10:
                score += 8
                reasons.append("Experienced runner")
            elif total_form_count >= 5:
                score += 5
        except Exception:
            pass

    start_price = runner.get("startPrice")
    if is_valid(start_price):
        try:
            start_price = float(start_price)
            if start_price > 1:
                if start_price <= 2.5:
                    score += 15
                    reasons.append("Market liked recently")
                elif start_price <= 5:
                    score += 8
        except Exception:
            pass

    score = round(max(0, min(score, 100)), 1)

    if not reasons:
        reasons.append("Top ranked by available data")

    return score, reasons[:5]


def get_track_from_name(race, runners):
    if runners:
        track = runners[0].get("track")
        if track:
            return track

    name = race.get("name", "")
    match = re.search(r"@([A-Z]+)", str(name))
    if match:
        return match.group(1)

    return "Unknown Track"


def scan_all_ranked():
    races = get_all_today_races()
    ranked = []

    for race in races:
        race_id = race.get("raceId")
        runners = get_runners_for_race(race_id)

        active = [
            r for r in runners
            if r.get("scratched") is not True and r.get("isLateScratching") is not True
        ]

        if len(active) < 4:
            continue

        scored = []

        for runner in active:
            score, reasons = score_runner(runner, active)
            scored.append((score, runner, reasons))

        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_runner, reasons = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0
        margin = round(best_score - second_score, 1)

        ranked.append({
            "score": best_score,
            "margin": margin,
            "race": race,
            "runner": best_runner,
            "runners": active,
            "reasons": reasons,
            "field_size": len(active),
        })

    ranked.sort(key=lambda x: (x["score"], x["margin"]), reverse=True)
    return ranked


def format_leg(pick):
    race = pick["race"]
    runner = pick["runner"]

    track = get_track_from_name(race, pick["runners"])
    race_no = race.get("raceNumber", "?")
    authority = race.get("authority", "?")
    distance = race.get("distance", "?")
    start = race.get("startTime", "")
    dog = runner.get("dogName", "Unknown Dog")
    box = runner.get("boxNumber") or runner.get("rugNumber") or "?"

    return f"{track} R{race_no} ({authority}) — Box {box} {dog} — {distance}m — {start}"


def format_pick(pick, index):
    runner = pick["runner"]
    trainer = runner.get("trainerName", "Unknown Trainer")
    reasons = "\n".join([f"✔ {r}" for r in pick["reasons"]])

    return (
        f"{index}. {confidence_label(pick['score'])} — {pick['score']}/100\n"
        f"{format_leg(pick)}\n"
        f"Trainer: {trainer}\n"
        f"Edge over 2nd: {pick['margin']} pts\n"
        f"{reasons}\n"
    )


def build_bet_message():
    ranked = scan_all_ranked()

    if not ranked:
        return "No race/runner data found from Topaz today."

    top10 = ranked[:10]

    safer_singles = [p for p in ranked if p["score"] >= 45][:5]
    if len(safer_singles) < 5:
        safer_singles = top10[:5]

    two_leg = top10[:2]
    three_leg = top10[:3]
    four_api_keeper = top10[:4]

    msg = "🐕 TODAY'S SMART GREYHOUND BETS\n\n"
    msg += "These are model-ranked suggestions from Topaz data only. Verify odds/scratchings before betting.\n\n"

    msg += "✅ Safer Singles / Place-Style Picks\n\n"
    for i, pick in enumerate(safer_singles, start=1):
        msg += format_pick(pick, i) + "\n"

    msg += "🔒 Suggested 2-Leg Safer Multi\n"
    for i, pick in enumerate(two_leg, start=1):
        msg += f"Leg {i}: {format_leg(pick)} ({pick['score']}/100)\n"
    msg += "\n"

    msg += "⚡ Suggested 3-Leg Higher Risk Multi\n"
    for i, pick in enumerate(three_leg, start=1):
        msg += f"Leg {i}: {format_leg(pick)} ({pick['score']}/100)\n"
    msg += "\n"

    msg += "🧾 4 Betfair API-Keeper Markets\n"
    for i, pick in enumerate(four_api_keeper, start=1):
        msg += f"{i}. {format_leg(pick)} ({confidence_label(pick['score'])})\n"

    msg += "\nStake idea: tiny stakes only until we track results."

    return msg[:4000]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Greyhound Scanner online.\n\nType /scan for smart bet suggestions."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning races, runners, form and building smart bets...")

    try:
        msg = build_bet_message()
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Scanner error:\n{e}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    if not TOPAZ_API_KEY:
        raise RuntimeError("TOPAZ_API_KEY missing")

    print("🚀 TOPAZ SMART BET VERSION STARTED")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.run_polling()


if __name__ == "__main__":
    main()
