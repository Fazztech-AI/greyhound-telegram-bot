import re
from datetime import date
from topaz_client import get_all_races_for_date, get_runners_for_race, get_runners_for_races_parallel
from scorer import score_runner, confidence_label, dominance_label, race_risk_label, suggested_bet_type
from utils import normalise

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
    """Find track names by checking only one race per meeting, not every race."""
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
        target_date = date.today()

    races = get_all_races_for_date(target_date)

    # Fast track filtering: identify matching meetings first, then only fetch those races.
    meeting_track_map = build_meeting_track_map(races)

    if track_search:
        races = [
            race for race in races
            if track_matches(meeting_track_map.get(race.get("meetingId"), "Unknown Track"), track_search)
        ]

    race_ids = [race.get("raceId") for race in races]
    runners_by_race = get_runners_for_races_parallel(race_ids, max_workers=8)

    ranked = []
    for race in races:
        race_id = race.get("raceId")
        runners = runners_by_race.get(race_id, [])

        active = [
            r for r in runners
            if r.get("scratched") is not True and r.get("isLateScratching") is not True
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

        ranked.append({
            "score": best_score,
            "margin": round(best_score - second_score, 1),
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

def format_pick(pick, index):
    runner = pick["runner"]
    trainer = runner.get("trainerName", "Unknown Trainer")
    pros_text = "\n".join([f"✔ {p}" for p in pick["pros"]])
    warnings_text = "\n".join([f"⚠ {w}" for w in pick["warnings"]]) if pick["warnings"] else "None"

    return (
        f"{index}. {confidence_label(pick['score'])} — {pick['score']}/100\n"
        f"{format_leg(pick)}\n"
        f"Trainer: {trainer}\n"
        f"Dominance: {dominance_label(pick['margin'])}\n"
        f"Race risk: {race_risk_label(pick['score'], pick['margin'], pick['field_size'])}\n"
        f"Suggested bet: {suggested_bet_type(pick['score'], pick['margin'])}\n\n"
        f"Pros:\n{pros_text}\n"
        f"Warnings:\n{warnings_text}\n"
    )

def build_best_bets_message(target_date=None, track_search=None):
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
    return msg

def build_tracks_message(target_date=None):
    if target_date is None:
        target_date = date.today()

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
        target_date = date.today()

    ranked = scan_ranked(target_date, track_search)
    race_picks = [p for p in ranked if str(p["race"].get("raceNumber", "")) == str(race_number)]

    if not race_picks:
        return f"No race found for {track_search} R{race_number} on {target_date}."

    pick = race_picks[0]
    scored = pick["full_rankings"]

    msg = f"🐕 Full Race Ranking — {pick['track']} R{race_number}\n"
    msg += f"Date: {target_date}\n"
    msg += f"Distance: {pick['race'].get('distance', '?')}m\n\n"

    for i, item in enumerate(scored, start=1):
        score, runner, pros, warnings = item
        box = runner.get("boxNumber") or runner.get("rugNumber") or "?"
        dog = runner.get("dogName", "Unknown Dog")
        trainer = runner.get("trainerName", "Unknown Trainer")
        msg += f"{i}. Box {box} {dog} — {score}/100 {confidence_label(score)}\n"
        msg += f"Trainer: {trainer}\n"
        if pros:
            msg += f"✔ {pros[0]}\n"
        if warnings:
            msg += f"⚠ {warnings[0]}\n"
        msg += "\n"

    msg += f"Suggested bet: {suggested_bet_type(pick['score'], pick['margin'])}\n"
    msg += f"Race risk: {race_risk_label(pick['score'], pick['margin'], pick['field_size'])}"
    return msg
