import os
import re
from datetime import date, timedelta, datetime

import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from topaz import TopazAPI

BOT_TOKEN = os.getenv("BOT_TOKEN")
TOPAZ_API_KEY = os.getenv("TOPAZ_API_KEY")

AUTHORITY_CODES = ["NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]


def make_topaz():
    return TopazAPI(TOPAZ_API_KEY)


def is_valid(value):
    return value is not None and not pd.isna(value)


def parse_date_from_text(text):
    text = text.lower().strip()

    if "tomorrow" in text:
        return date.today() + timedelta(days=1)

    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return datetime.strptime(match.group(0), "%Y-%m-%d").date()

    return date.today()


def get_all_races_for_date(target_date):
    topaz = make_topaz()
    from_date = target_date.isoformat()
    to_date = (target_date + timedelta(days=1)).isoformat()

    all_races = []

    for code in AUTHORITY_CODES:
        try:
            races = topaz.get_races(
                from_date=from_date,
                to_date=to_date,
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
    return [int(ch) for ch in last5 if ch.isdigit()]


def confidence_label(score):
    if score >= 75:
        return "🔥 Strong"
    if score >= 60:
        return "✅ Solid"
    if score >= 45:
        return "⚠️ Usable"
    return "🧊 Low"


def dominance_label(margin):
    if margin >= 20:
        return f"Dominant +{margin}"
    if margin >= 10:
        return f"Strong +{margin}"
    if margin >= 5:
        return f"Decent +{margin}"
    return f"Tight +{margin}"


def race_risk_label(score, margin, field_size):
    if score >= 70 and margin >= 10 and field_size <= 8:
        return "🟢 Clean race"
    if score >= 55 and margin >= 5:
        return "🟡 Competitive but playable"
    return "🔴 Messy / low confidence"


def suggested_bet_type(score, margin):
    if score >= 75 and margin >= 15:
        return "Win / Place"
    if score >= 60 and margin >= 8:
        return "Place / Top 2 style"
    if score >= 45:
        return "Tiny place only"
    return "Skip unless tiny API-keeper bet"


def score_runner(runner, field):
    score = 0
    pros = []
    warnings = []

    if runner.get("scratched") is True or runner.get("isLateScratching") is True:
        return 0, [], ["Scratched"]

    rating = runner.get("rating")
    if is_valid(rating) and rating > 0:
        score += min(20, float(rating) / 5)
        pros.append(f"Rating {rating}")

    avg_speed = runner.get("averageSpeed")
    field_speeds = [
        r.get("averageSpeed") for r in field
        if is_valid(r.get("averageSpeed")) and r.get("averageSpeed") > 0
    ]

    if is_valid(avg_speed) and avg_speed > 0 and field_speeds:
        best_speed = max(field_speeds)
        if avg_speed == best_speed:
            score += 20
            pros.append("Best average speed")
        else:
            score += max(0, 15 * (avg_speed / best_speed))

    best_finish_td = runner.get("bestFinishTrackAndDistance")
    if is_valid(best_finish_td):
        try:
            best_finish_td = int(best_finish_td)
            if best_finish_td == 1:
                score += 15
                pros.append("Won track/distance")
            elif best_finish_td <= 3:
                score += 10
                pros.append("Placed track/distance")
        except Exception:
            pass

    last5 = parse_last5(runner.get("last5"))
    if last5:
        top3 = sum(1 for pos in last5 if pos <= 3)
        wins = sum(1 for pos in last5 if pos == 1)

        score += top3 * 4
        score += wins * 3

        if top3 >= 4:
            pros.append("Very consistent last 5")
        elif top3 >= 3:
            pros.append("Good recent form")
        elif wins >= 1:
            pros.append("Recent winner")
    else:
        score -= 5
        warnings.append("Limited last-5 form")

    box = runner.get("boxNumber") or runner.get("rugNumber")
    try:
        box = int(box)
        if box in [1, 2]:
            score += 12
            pros.append("Good inside box")
        elif box in [3, 4]:
            score += 7
        elif box in [5, 6]:
            score += 3
        elif box in [7, 8]:
            score += 4
    except Exception:
        warnings.append("No box data")

    total_form_count = runner.get("totalFormCount")
    if is_valid(total_form_count):
        try:
            total_form_count = int(total_form_count)
            if total_form_count == 0:
                score -= 8
                warnings.append("No exposed form")
            elif total_form_count >= 10:
                score += 8
                pros.append("Experienced runner")
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
                    pros.append("Market liked recently")
                elif start_price <= 5:
                    score += 8
        except Exception:
            pass

    score = round(max(0, min(score, 100)), 1)

    if not pros:
        pros.append("Top ranked by available data")

    return score, pros[:5], warnings[:4]


def get_track_name(race, runners):
    if runners:
        track = runners[0].get("track")
        if track:
            return str(track)

    name = str(race.get("name", ""))
    match = re.search(r"@([A-Z]+)", name)
    if match:
        return match.group(1)

    return "Unknown Track"


def track_matches(track_name, search):
    return search.lower() in track_name.lower()


def scan_ranked(target_date=None, track_search=None):
    if target_date is None:
        target_date = date.today()

    races = get_all_races_for_date(target_date)
    ranked = []

    for race in races:
        runners = get_runners_for_race(race.get("raceId"))

        active = [
            r for r in runners
            if r.get("scratched") is not True and r.get("isLateScratching") is not True
        ]

        if len(active) < 4:
            continue

        track = get_track_name(race, active)

        if track_search and not track_matches(track, track_search):
            continue

        scored = []
        for runner in active:
            score, pros, warnings = score_runner(runner, active)
            scored.append((score, runner, pros, warnings))

        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_runner, pros, warnings = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0
        margin = round(best_score - second_score, 1)

        ranked.append({
            "score": best_score,
            "margin": margin,
            "race": race,
            "runner": best_runner,
            "runners": active,
            "pros": pros,
            "warnings": warnings,
            "track": track,
            "field_size": len(active),
        })

    ranked.sort(key=lambda x: (x["score"], x["margin"]), reverse=True)
    return ranked


def format_leg(pick):
    race = pick["race"]
    runner = pick["runner"]

    race_no = race.get("raceNumber", "?")
    authority = race.get("authority", "?")
    distance = race.get("distance", "?")
    start = race.get("startTime", "")
    dog = runner.get("dogName", "Unknown Dog")
    box = runner.get("boxNumber") or runner.get("rugNumber") or "?"

    return f"{pick['track']} R{race_no} ({authority}) — Box {box} {dog} — {distance}m — {start}"


def format_pick(pick, index):
    runner = pick["runner"]
    trainer = runner.get("trainerName", "Unknown Trainer")

    pros_text = "\n".join([f"✔ {p}" for p in pick["pros"]])
    warnings_text = "\n".join([f"⚠ {w}" for w in pick["warnings"]]) if pick["warnings"] else "None"

    risk = race_risk_label(pick["score"], pick["margin"], pick["field_size"])
    bet_type = suggested_bet_type(pick["score"], pick["margin"])

    return (
        f"{index}. {confidence_label(pick['score'])} — {pick['score']}/100\n"
        f"{format_leg(pick)}\n"
        f"Trainer: {trainer}\n"
        f"Dominance: {dominance_label(pick['margin'])}\n"
        f"Race risk: {risk}\n"
        f"Suggested bet: {bet_type}\n\n"
        f"Pros:\n{pros_text}\n"
        f"Warnings:\n{warnings_text}\n"
    )


def build_message(target_date=None, track_search=None):
    if target_date is None:
        target_date = date.today()

    ranked = scan_ranked(target_date, track_search)

    if not ranked:
        if track_search:
            return f"No races found for '{track_search}' on {target_date}."
        return f"No race/runner data found for {target_date}."

    title = f"🐕 Smart Greyhound Bets — {target_date}"
    if track_search:
        title += f"\nTrack search: {track_search}"

    msg = title + "\n\n"
    msg += "Topaz model only. Check live odds and scratchings before betting.\n\n"

    msg += "✅ Best Singles / Place-Style Picks\n\n"
    for i, pick in enumerate(ranked[:5], start=1):
        msg += format_pick(pick, i) + "\n"

    msg += "🔒 Suggested 2-Leg Safer Multi\n"
    for i, pick in enumerate(ranked[:2], start=1):
        msg += f"Leg {i}: {format_leg(pick)} — {pick['score']}/100\n"
    msg += "\n"

    if len(ranked) >= 3:
        msg += "⚡ Suggested 3-Leg Higher Risk Multi\n"
        for i, pick in enumerate(ranked[:3], start=1):
            msg += f"Leg {i}: {format_leg(pick)} — {pick['score']}/100\n"
        msg += "\n"

    msg += "🧾 4 API-Keeper Markets\n"
    for i, pick in enumerate(ranked[:4], start=1):
        msg += f"{i}. {format_leg(pick)} — {confidence_label(pick['score'])}\n"

    msg += "\nStake idea: tiny stakes until results are tracked."

    return msg[:4000]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐕 Greyhound Scanner online.\n\n"
        "/scan\n"
        "/track Geelong\n"
        "/track The Meadows tomorrow\n\n"
        "Or just type a track name."
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning and rating races...")
    try:
        await update.message.reply_text(build_message())
    except Exception as e:
        await update.message.reply_text(f"Scanner error:\n{e}")


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()

    if not text:
        await update.message.reply_text("Example: /track Geelong or /track The Meadows tomorrow")
        return

    target_date = parse_date_from_text(text)
    clean_track = text.replace("tomorrow", "").replace(target_date.isoformat(), "").strip()

    await update.message.reply_text(f"🔍 Scanning {clean_track} for {target_date}...")

    try:
        await update.message.reply_text(build_message(target_date, clean_track))
    except Exception as e:
        await update.message.reply_text(f"Track scanner error:\n{e}")


async def natural_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    target_date = parse_date_from_text(text)
    clean_track = text.replace("tomorrow", "").replace(target_date.isoformat(), "").strip()

    await update.message.reply_text(f"🔍 Checking {clean_track} for {target_date}...")

    try:
        await update.message.reply_text(build_message(target_date, clean_track))
    except Exception as e:
        await update.message.reply_text(f"Message scanner error:\n{e}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    if not TOPAZ_API_KEY:
        raise RuntimeError("TOPAZ_API_KEY missing")

    print("🚀 TOPAZ BET TYPE VERSION STARTED")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("track", track_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, natural_message))

    app.run_polling()


if __name__ == "__main__":
    main()
