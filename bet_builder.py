import re

from topaz_client import (
    get_all_races_for_date,
    get_runners_for_races_parallel,
)
from scorer import (
    score_runner,
    confidence_label,
    dominance_label,
    race_risk_label,
    suggested_bet_type,
)
from utils import normalise, melbourne_today


def get_track_name(race, runners=None):
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
    return normalise(search) in normalise(track_name)


def build_meeting_track_map(races):
    meeting_first_race = {}

    for race in races:
        meeting_id = race.get("meetingId")
        if meeting_id not in meeting_first_race:
            meeting_first_race[meeting_id] = race

    first_race_ids = [r.get("raceId") for r in meeting_first_race.values()]
    runners_by_race = get_runners_for_races_parallel(first_race_ids, max_workers=8)

    track_map = {}

    for meeting_id, race in meeting_first_race.items():
        runners = runners_by_race.get(race.get("raceId"), [])
        track_map[meeting_id] = get_track_name(race, runners)

    return track_map


def scan_ranked(target_date=None, track_search=None):
    if target_date is None:
        target_date = melbourne_today()

    races = get_all_races_for_date(target_date)
    meeting_track_map = build_meeting_track_map(races)

    if track_search:
        races = [
            race for race in races
            if track_matches(
                meeting_track_map.get(race.get("meetingId"), "Unknown Track"),
                track_search,
            )
        ]

    race_ids = [race.get("raceId") for race in races]
    runners_by_race = get_runners_for_races_parallel(race_ids, max_workers=8)

    ranked = []

    for race in races:
        runners = runners_by_race.get(race.get("raceId"), [])

        active = [
            r for r in runners
            if r.get("scratched") is not True
            and r.get("isLateScratching") is not True
        ]

        if len(active) < 4:
            continue

        track = get_track_name(race, active)
        if track == "Unknown Track":
            track = meeting_track_map.get(race.get("meetingId"), "Unknown Track")

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
            "full_rankings": scored,
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


def format_runner_short(runner):
    box = runner.get("boxNumber") or runner.get("rugNumber") or "?"
    dog = runner.get("dogName", "Unknown Dog")
    return f"Box {box} {dog}"


def single_suitability(pick):
    if pick["score"] >= 75 and pick["margin"] >= 15:
        return "⭐⭐⭐⭐⭐"
    if pick["score"] >= 65 and pick["margin"] >= 10:
        return "⭐⭐⭐⭐"
    if pick["score"] >= 55 and pick["margin"] >= 5:
        return "⭐⭐⭐"
    return "⭐⭐"


def multi_suitability(pick):
    if pick["score"] >= 70 and pick["margin"] >= 10:
        return "⭐⭐⭐⭐⭐"
    if pick["score"] >= 60 and pick["margin"] >= 5:
        return "⭐⭐⭐⭐"
    if pick["score"] >= 50:
        return "⭐⭐⭐"
    return "⭐⭐"


def is_anchor_single(pick):
    return pick["score"] >= 60 and pick["margin"] >= 5


def is_safe_multi_leg(pick):
    return pick["score"] >= 55


def is_multi_anchor(pick):
    return pick["score"] >= 70 and pick["margin"] >= 10


def is_race_to_avoid(pick):
    return pick["margin"] < 5 or pick["score"] < 50


def get_same_race_top4_angle(pick):
    scored = pick["full_rankings"]
    active_count = pick["field_size"]

    if active_count != 6:
        return None

    if len(scored) < 6:
        return None

    top3 = scored[:3]
    fourth = scored[3]
    fifth = scored[4]
    sixth = scored[5]

    top3_scores = [item[0] for item in top3]
    third_score = top3_scores[-1]
    fifth_score = fifth[0]
    sixth_score = sixth[0]

    gap_to_danger = round(third_score - fifth_score, 1)
    bottom_gap = round(third_score - max(fifth_score, sixth_score), 1)

    if gap_to_danger < 4:
        risk = "⚠️ Risky — top 3 are not far enough ahead"
    elif gap_to_danger >= 10:
        risk = "🟢 Strong Top 4 setup"
    else:
        risk = "🟡 Playable Top 4 setup"

    return {
        "top3": top3,
        "gap_to_danger": gap_to_danger,
        "bottom_gap": bottom_gap,
        "risk": risk,
    }


def format_same_race_top4(pick):
    angle = get_same_race_top4_angle(pick)

    if not angle:
        return ""

    msg = "🏁 SAME RACE TOP 4 ANGLE\n"
    msg += f"Active runners: {pick['field_size']}\n"
    msg += f"Setup: {angle['risk']}\n"
    msg += "Idea: use model top 3 to finish Top 4 in the same race.\n\n"

    msg += "Use these 3:\n"
    for i, item in enumerate(angle["top3"], start=1):
        score, runner, pros, warnings = item
        msg += f"{i}. {format_runner_short(runner)} — {score}/100\n"

    msg += f"\nGap from 3rd pick to danger: {angle['gap_to_danger']} pts\n"
    msg += "Warning: check Sportsbet/TAB market rules after scratchings. If no third dividend or market changes, reassess.\n"

    return msg


def format_short_pick(pick, index=None):
    prefix = f"{index}. " if index is not None else ""
    label = confidence_label(pick["score"], pick["margin"])
    return f"{prefix}{format_leg(pick)} — {label} — {pick['score']}/100"


def format_detailed_pick(pick, index=None):
    runner = pick["runner"]
    trainer = runner.get("trainerName", "Unknown Trainer")

    pros_text = "\n".join([f"✔ {p}" for p in pick["pros"]])
    warnings_text = (
        "\n".join([f"⚠ {w}" for w in pick["warnings"]])
        if pick["warnings"]
        else "None"
    )

    label = confidence_label(pick["score"], pick["margin"])
    dominance = dominance_label(pick["margin"])
    risk = race_risk_label(pick["score"], pick["margin"], pick["field_size"])
    bet_type = suggested_bet_type(pick["score"], pick["margin"])
    top4_text = format_same_race_top4(pick)

    prefix = f"{index}. " if index is not None else ""

    msg = (
        f"{prefix}{label} — {pick['score']}/100\n"
        f"{format_leg(pick)}\n"
        f"Trainer: {trainer}\n"
        f"Dominance: {dominance}\n"
        f"Race risk: {risk}\n"
        f"Single suitability: {single_suitability(pick)}\n"
        f"Multi suitability: {multi_suitability(pick)}\n"
        f"Suggested single: {bet_type}\n"
        f"Multi use: {'Anchor leg candidate' if is_safe_multi_leg(pick) else 'Not ideal'}\n\n"
        f"Pros:\n{pros_text}\n"
        f"Warnings:\n{warnings_text}\n"
    )

    if top4_text:
        msg += "\n" + top4_text

    return msg


def build_daily_betting_plan(ranked, target_date, track_search=None):
    title = f"🐕 DAILY BETTING PLAN — {target_date}"
    if track_search:
        title += f"\nTrack search: {track_search}"

    msg = title + "\n\n"
    msg += "Singles rule: main singles only if live odds are $1.50+.\n"
    msg += "Multi rule: sub-$1.50 runners can still be used as safe anchor legs.\n"
    msg += "Topaz model only. Check live odds/scratchings before betting.\n\n"

    best_bet = ranked[0]
    anchor_singles = [p for p in ranked if is_anchor_single(p)][:5]
    safe_multi_legs = [p for p in ranked if is_safe_multi_leg(p)][:4]
    multi_anchors = [p for p in ranked if is_multi_anchor(p)][:5]
    top4_angles = [p for p in ranked if get_same_race_top4_angle(p) is not None][:5]
    avoid_races = [p for p in ranked if is_race_to_avoid(p)][:6]

    msg += "⭐ BEST BET OF THE DAY\n\n"
    msg += format_detailed_pick(best_bet) + "\n"

    msg += "━━━━━━━━━━━━━━\n\n"
    msg += "🔥 ANCHOR SINGLES\n"
    msg += "Use as singles only if live odds are $1.50+.\n\n"

    if anchor_singles:
        for i, pick in enumerate(anchor_singles, start=1):
            msg += format_short_pick(pick, i) + "\n"
    else:
        msg += "No strong single anchors found.\n"

    msg += "\n━━━━━━━━━━━━━━\n\n"
    msg += "🔒 SAFE MULTI\n"
    msg += "These are the cleanest multi-leg candidates.\n\n"

    if len(safe_multi_legs) >= 2:
        for i, pick in enumerate(safe_multi_legs[:3], start=1):
            msg += f"Leg {i}: {format_leg(pick)} — {multi_suitability(pick)}\n"
    else:
        msg += "No safe multi found.\n"

    msg += "\n━━━━━━━━━━━━━━\n\n"
    msg += "🏁 SAME RACE TOP 4 ANGLES\n"
    msg += "Best for 6-runner races. Pick model top 3 to finish Top 4.\n\n"

    if top4_angles:
        for i, pick in enumerate(top4_angles, start=1):
            angle = get_same_race_top4_angle(pick)
            msg += f"{i}. {format_leg(pick)}\n"
            msg += f"Setup: {angle['risk']}\n"
            msg += "Use: "
            msg += ", ".join([format_runner_short(item[1]) for item in angle["top3"]])
            msg += f"\nGap to danger: {angle['gap_to_danger']} pts\n\n"
    else:
        msg += "No strong 6-runner Top 4 setups found.\n"

    msg += "━━━━━━━━━━━━━━\n\n"
    msg += "🧱 MULTI ANCHORS\n"
    msg += "High-confidence runners that can still be useful even if under $1.50.\n\n"

    if multi_anchors:
        for i, pick in enumerate(multi_anchors, start=1):
            msg += format_short_pick(pick, i) + "\n"
    else:
        msg += "No dominant anchor legs found.\n"

    msg += "\n━━━━━━━━━━━━━━\n\n"
    msg += "🧾 4 API-KEEPER MARKETS\n"
    msg += "Tiny stakes only if needed for API activity.\n\n"

    for i, pick in enumerate(ranked[:4], start=1):
        label = confidence_label(pick["score"], pick["margin"])
        msg += f"{i}. {format_leg(pick)} — {label}\n"

    msg += "\nStake idea: tiny stakes only until results are tracked."

    return msg[:4000]


def build_best_bets_message(target_date=None, track_search=None):
    if target_date is None:
        target_date = melbourne_today()

    ranked = scan_ranked(target_date, track_search)

    if not ranked:
        if track_search:
            return f"No races found for '{track_search}' on {target_date}."
        return f"No race/runner data found for {target_date}."

    return build_daily_betting_plan(ranked, target_date, track_search)


def build_tracks_message(target_date=None):
    if target_date is None:
        target_date = melbourne_today()

    races = get_all_races_for_date(target_date)

    if not races:
        return f"No tracks found for {target_date}."

    meeting_track_map = build_meeting_track_map(races)
    tracks = {}

    for race in races:
        track = meeting_track_map.get(race.get("meetingId"), "Unknown Track")
        tracks.setdefault(track, 0)
        tracks[track] += 1

    msg = f"🐕 Tracks racing on {target_date}\n\n"

    for track, count in sorted(tracks.items()):
        msg += f"• {track} — {count} races\n"

    msg += "\nUse: /track Geelong or /race Geelong 5"

    return msg[:4000]


def build_race_message(track_search, race_number, target_date=None):
    if target_date is None:
        target_date = melbourne_today()

    ranked = scan_ranked(target_date, track_search)

    race_picks = [
        p for p in ranked
        if str(p["race"].get("raceNumber", "")) == str(race_number)
    ]

    if not race_picks:
        return f"No race found for {track_search} R{race_number} on {target_date}."

    pick = race_picks[0]
    scored = pick["full_rankings"]

    msg = f"🐕 FULL RACE RANKING — {pick['track']} R{race_number}\n"
    msg += f"Date: {target_date}\n"
    msg += f"Distance: {pick['race'].get('distance', '?')}m\n"
    msg += f"Active runners: {pick['field_size']}\n\n"

    for i, item in enumerate(scored, start=1):
        score, runner, pros, warnings = item
        label = confidence_label(score)

        msg += f"{i}. {format_runner_short(runner)} — {score}/100 {label}\n"

        if pros:
            msg += f"✔ {pros[0]}\n"

        if warnings:
            msg += f"⚠ {warnings[0]}\n"

        msg += "\n"

    msg += f"Suggested bet: {suggested_bet_type(pick['score'], pick['margin'])}\n"
    msg += f"Race risk: {race_risk_label(pick['score'], pick['margin'], pick['field_size'])}\n\n"

    top4_text = format_same_race_top4(pick)
    if top4_text:
        msg += top4_text

    return msg[:4000]
