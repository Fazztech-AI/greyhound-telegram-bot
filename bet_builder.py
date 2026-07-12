import re
from datetime import datetime
from zoneinfo import ZoneInfo
from database import save_pick, pick_exists
from learning_history import save_learning_runner
from model_weights import weighted_confidence

from topaz_client import get_all_races_for_date, get_runners_for_races_parallel
from scorer import (
    score_runner,
    confidence_label,
    dominance_label,
    race_risk_label,
    suggested_bet_type,
)
from learning import load_settings
from utils import normalise, melbourne_today

MELBOURNE_TZ = ZoneInfo("Australia/Melbourne")


def melbourne_now():
    return datetime.now(MELBOURNE_TZ)


def parse_race_start(race):
    raw = race.get("raceStart")
    if not raw:
        return None

    try:
        raw = str(raw).replace("Z", "+00:00")
        return datetime.fromisoformat(raw).astimezone(MELBOURNE_TZ)
    except Exception:
        return None

def race_is_on_target_date(race, target_date):
    start = parse_race_start(race)
    if not start:
        return True

    return start.date() == target_date


def race_has_started(race, target_date):
    if target_date != melbourne_today():
        return False

    start = parse_race_start(race)
    if not start:
        return False

    return start <= melbourne_now()


def race_is_resulted_or_invalid(race):
    return (
        race.get("isRaceResultEntered") is True
        or race.get("raceResultEntered") is True
        or race.get("abandoned") is True
        or race.get("isAbandoned") is True
    )


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


def active_runners_only(runners):
    scratched_values = {
        "true",
        "yes",
        "y",
        "1",
        "scratched",
        "late scratching",
        "late scratched",
        "withdrawn",
        "withdrawal",
    }

    active = []

    for r in runners:
        dog_name = str(r.get("dogName", "")).upper()

        if "SPEEDY ZIPPER" in dog_name:
            print("DEBUG SPEEDY ZIPPER RUNNER DATA:", r)

        scratch_fields = [
            r.get("scratched"),
            r.get("isScratched"),
            r.get("isLateScratching"),
            r.get("lateScratching"),
            r.get("scratchingType"),
            r.get("scratchingReason"),
            r.get("status"),
            r.get("runnerStatus"),
            r.get("raceRunStatus"),
            r.get("runStatus"),
        ]

        is_scratched = False

        for value in scratch_fields:
            if value is True:
                is_scratched = True
                break

            if value is None:
                continue

            if str(value).strip().lower() in scratched_values:
                is_scratched = True
                break

        if not is_scratched:
            active.append(r)

    return active

def scan_ranked(target_date=None, track_search=None):
    if target_date is None:
        target_date = melbourne_today()

    races = get_all_races_for_date(target_date)
    meeting_track_map = build_meeting_track_map(races)

    filtered_races = []

    for race in races:
        if race_is_resulted_or_invalid(race):
            continue

        if not race_is_on_target_date(race, target_date):
            continue

        if race_has_started(race, target_date):
            continue

        if track_search:
            track = meeting_track_map.get(race.get("meetingId"), "Unknown Track")
            if not track_matches(track, track_search):
                continue

        filtered_races.append(race)

    race_ids = [race.get("raceId") for race in filtered_races]
    runners_by_race = get_runners_for_races_parallel(race_ids, max_workers=8)

    ranked = []

    for race in filtered_races:
        runners = runners_by_race.get(race.get("raceId"), [])
        active = active_runners_only(runners)

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

        temp_pick = {
            "score": best_score,
            "margin": margin,
            "runner": best_runner,
            "runners": active,
            "field_size": len(active),
            "full_rankings": scored,
        }

        trust_for_weight, _, _ = race_trust_score(temp_pick)
        edge_for_weight, _ = field_dominance_index(temp_pick)

        weighted_score = weighted_confidence(
            best_score,
            trust_for_weight,
            edge_for_weight,
            margin,
        )

        ranked.append({
            "score": best_score,
            "weighted_score": weighted_score,
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

    ranked.sort(
    key=lambda x: (
        x["score"],
        x["margin"],
    ),
    reverse=True,
    )

    return ranked
    

def format_runner_short(runner):
    box = runner.get("boxNumber") or runner.get("rugNumber") or "?"
    dog = runner.get("dogName", "Unknown Dog")
    return f"Box {box} {dog}"


def format_leg(pick):
    race = pick["race"]
    runner = pick["runner"]

    race_no = race.get("raceNumber", "?")
    authority = race.get("authority", "?")
    distance = race.get("distance", "?")
    start = race.get("startTime", "")
    box = runner.get("boxNumber") or runner.get("rugNumber") or "?"
    dog = runner.get("dogName", "Unknown Dog")

    return (
        f"{pick['track']} R{race_no} ({authority}) — "
        f"Box {box} {dog} — {distance}m — {start}"
    )


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

    if pick["field_size"] != 6 or len(scored) < 6:
        return None

    top3 = scored[:3]

    first_score = top3[0][0]
    second_score = top3[1][0]
    third_score = top3[2][0]

    fourth_score = scored[3][0]
    fifth_score = scored[4][0]

    gap_to_danger = round(third_score - fifth_score, 1)

    # Every included runner must be genuinely competitive.
    if first_score < 60:
        return None

    if second_score < 55:
        return None

    if third_score < 52:
        return None

    # The third selection must have a meaningful advantage
    # over the runners most likely to knock it out of the Top 4.
    if gap_to_danger < 8:
        return None

    # Avoid races where rankings below the favourite are tightly bunched.
    if third_score - fourth_score < 2:
        return None

    risk = (
        "🟢 Strong Top 4 setup"
        if gap_to_danger >= 12 and third_score >= 58
        else "🟡 Playable Top 4 setup"
    )

    return {
        "top3": top3,
        "gap_to_danger": gap_to_danger,
        "risk": risk,
    }

def format_same_race_top4(pick):
    angle = get_same_race_top4_angle(pick)
    if not angle:
        return ""

    msg = "🏁 SAME RACE TOP 4 ANGLE\n"
    msg += f"Active runners: {pick['field_size']}\n"
    msg += f"Setup: {angle['risk']}\n"
    msg += "Use model top 3 to finish Top 4.\n\n"

    for i, item in enumerate(angle["top3"], start=1):
        score, runner, pros, warnings = item
        msg += f"{i}. {format_runner_short(runner)} — {score}/100\n"

    msg += f"\nGap to danger: {angle['gap_to_danger']} pts\n"
    msg += "Warning: re-check scratchings and market rules before betting.\n"

    return msg


def race_trust_score(pick):
    score = 50
    warnings = []

    margin = pick["margin"]
    field_size = pick["field_size"]
    scored = pick["full_rankings"]

    if margin >= 20:
        score += 25
    elif margin >= 10:
        score += 15
    elif margin >= 5:
        score += 5
    else:
        score -= 20
        warnings.append("Tight race")

    if field_size >= 7:
        score += 10
    elif field_size == 6:
        score += 5
    elif field_size <= 5:
        score -= 10
        warnings.append("Small field")

    no_form_count = 0
    weak_form_count = 0

    for item in scored:
        runner = item[1]
        form_count = runner.get("totalFormCount")

        try:
            form_count = int(form_count)
            if form_count == 0:
                no_form_count += 1
            elif form_count < 5:
                weak_form_count += 1
        except Exception:
            weak_form_count += 1

    if no_form_count >= 2:
        score -= 20
        warnings.append("Multiple no-form runners")
    elif no_form_count == 1:
        score -= 8
        warnings.append("One no-form runner")

    if weak_form_count >= 3:
        score -= 10
        warnings.append("Weak exposed form")

    if pick["score"] >= 75:
        score += 10
    elif pick["score"] < 50:
        score -= 10

    score = max(0, min(100, round(score, 1)))

    if score >= 80:
        label = "🟢 High trust"
    elif score >= 65:
        label = "🟡 Playable"
    elif score >= 50:
        label = "🟠 Caution"
    else:
        label = "🔴 Low trust"

    return score, label, warnings


def field_dominance_index(pick):
    scored = pick["full_rankings"]

    if len(scored) < 4:
        return 0, "🔴 Weak field read"

    top_score = scored[0][0]
    rest_scores = [item[0] for item in scored[1:]]

    avg_rest = sum(rest_scores) / len(rest_scores)
    dominance = round(top_score - avg_rest, 1)

    if dominance >= 20:
        label = "🟢 Dominates field"
    elif dominance >= 12:
        label = "🟡 Clear field edge"
    elif dominance >= 7:
        label = "🟠 Some field edge"
    else:
        label = "🔴 Bunched field"

    return dominance, label
    
    
def final_recommendation(pick):
    trust, trust_label, warnings = race_trust_score(pick)

    if pick["score"] >= 75 and pick["margin"] >= 15 and trust >= 75:
        return "✅ Strong single candidate / multi anchor"

    if pick["score"] >= 65 and pick["margin"] >= 8 and trust >= 65:
        return "✅ Single candidate if odds are worth it"

    if pick["score"] >= 60 and trust >= 60:
        return "🧱 Multi anchor candidate"

    if trust < 50:
        return "🚫 Avoid / race too messy"

    return "⚠️ Small stake only"

def format_short_pick(pick, index=None):
    prefix = f"{index}. " if index is not None else ""

    label = confidence_label(pick["score"], pick["margin"])

    trust, trust_label, warnings = race_trust_score(pick)
    field_dom, field_label = field_dominance_index(pick)

    place_score = place_confidence_score(pick)
    place_label = place_confidence_label(place_score)

    return (
        f"{prefix}{format_leg(pick)} — {label} — {pick['score']}/100\n"
        f"Race trust: {trust}/100 {trust_label}\n"
        f"Field edge: {field_dom} pts {field_label}\n"
        f"Place confidence: {place_score}/100 {place_label}"
    )

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
    trust, trust_label, trust_warnings = race_trust_score(pick)
    recommendation = final_recommendation(pick)
    risk = race_risk_label(pick["score"], pick["margin"], pick["field_size"])
    bet_type = suggested_bet_type(pick["score"], pick["margin"])

    prefix = f"{index}. " if index is not None else ""

    msg = (
        f"{prefix}{label} — {pick['score']}/100\n"
        f"{format_leg(pick)}\n"
        f"Trainer: {trainer}\n"
        f"Active runners: {pick['field_size']}\n"
        f"Dominance: {dominance}\n"
        f"Race trust: {trust}/100 {trust_label}\n"
        f"Final recommendation: {recommendation}\n"
        f"Race risk: {risk}\n"
        f"Suggested single: {bet_type}\n"
        f"Multi use: {'Anchor leg candidate' if is_safe_multi_leg(pick) else 'Not ideal'}\n\n"
        f"Pros:\n{pros_text}\n"
        f"Warnings:\n{warnings_text}\n"
    )

    top4 = format_same_race_top4(pick)
    if top4:
        msg += "\n" + top4

    return msg


def save_pick_to_history(pick, recommendation):
    trust, _, _ = race_trust_score(pick)
    field_edge, _ = field_dominance_index(pick)

    race = pick["race"]
    runner = pick["runner"]

    race_date = str(race.get("raceDate") or melbourne_today())
    track = pick["track"]
    race_number = race.get("raceNumber")
    dog = runner.get("dogName")
    box = runner.get("boxNumber") or runner.get("rugNumber")

    if pick_exists(race_date, track, race_number, dog):
        return

    save_pick(
        race_id=race.get("raceId"),
        race_date=race_date,
        track=track,
        race_number=race_number,
        dog=dog,
        box=box,
        score=pick["score"],
        margin=pick["margin"],
        race_trust=trust,
        field_edge=field_edge,
        recommendation=recommendation,
    )
    
def save_learning_from_scan(ranked):
    """
    Save the top 4 analysed runners from every scanned race.

    This records what the AI believed BEFORE the race.
    """

    for pick in ranked:

        race = pick["race"]
        scored = pick["full_rankings"]

        field_size = len(pick["runners"])

        for score, runner, pros, warnings in scored[:4]:

            margin = round(score - scored[1][0], 1) if len(scored) > 1 else 0

            learning_pick = {
                "score": score,
                "margin": margin,
                "runner": runner,
                "runners": pick["runners"],
                "field_size": field_size,
                "full_rankings": scored,
            }

            race_trust, _, _ = race_trust_score(learning_pick)
            field_edge, _ = field_dominance_index(learning_pick)

            recommendation = final_recommendation(learning_pick)

            save_learning_runner(
                race_id=race.get("raceId"),
                race_date=str(race.get("raceDate") or melbourne_today()),
                track=pick["track"],
                race_number=race.get("raceNumber"),
                dog=runner.get("dogName"),
                box=runner.get("boxNumber") or runner.get("rugNumber"),
                score=score,
                margin=margin,
                race_trust=race_trust,
                field_edge=field_edge,
                recommendation=recommendation,
                field_size=field_size,
            )
            
def place_confidence_score(pick):
    score = 50

    race_trust, _, _ = race_trust_score(pick)
    field_edge, _ = field_dominance_index(pick)

    if pick["score"] >= 70:
        score += 15
    elif pick["score"] >= 60:
        score += 8

    if race_trust >= 70:
        score += 15
    elif race_trust >= 60:
        score += 8

    if field_edge >= 15:
        score += 15
    elif field_edge >= 10:
        score += 8

    if pick["field_size"] <= 6:
        score += 8

    if pick["margin"] >= 5:
        score += 7
    elif pick["margin"] >= 3:
        score += 3

    return min(100, round(score, 1))

def place_confidence_label(score):
    if score >= 90:
        return "⭐⭐⭐⭐⭐ Elite"
    elif score >= 80:
        return "⭐⭐⭐⭐ Excellent"
    elif score >= 70:
        return "⭐⭐⭐ Strong"
    elif score >= 60:
        return "⭐⭐ Good"
    else:
        return "⭐ Speculative"
    
def build_daily_betting_plan(ranked, target_date, track_search=None):
    thresholds = load_settings()

    title = f"🐕 DAILY BETTING PLAN — {target_date}"
    if track_search:
        title += f"\nTrack search: {track_search}"

    msg = title + "\n\n"
    msg += "Bot role: find strong runners. You decide single vs multi based on Sportsbet/TAB odds.\n"
    msg += "Singles: use only when price is worth it.\n"
    msg += "Place chances only show for 8-runner races where 3rd dividend is available.\n"
    msg += "Finished races and scratched runners are filtered out.\n\n"

    strong_singles = [
        p for p in ranked
        if p["score"] >= thresholds["strong_single_score"]
        and p["margin"] >= thresholds["strong_single_margin"]
        and race_trust_score(p)[0] >= thresholds["strong_single_trust"]
        and field_dominance_index(p)[0] >= thresholds["strong_single_edge"]
    ][:6]

    multi_anchors = [
        p for p in ranked
        if p["score"] >= thresholds["multi_anchor_score"]
        and p["margin"] >= thresholds["multi_anchor_margin"]
        and race_trust_score(p)[0] >= thresholds["multi_anchor_trust"]
        and field_dominance_index(p)[0] >= thresholds["multi_anchor_edge"]
    ][:6]

    place_anchors = [
        p for p in ranked
        if p["field_size"] >= 8
        and place_confidence_score(p) >= thresholds["place_confidence"]
    ][:6]

    top4_angles = [
        p for p in ranked
        if get_same_race_top4_angle(p) is not None
        and race_trust_score(p)[0] >= 60
    ][:5]

    avoid_races = [
        p for p in ranked
        if p["margin"] < 5
        or p["score"] < 50
        or race_trust_score(p)[0] < 50
        or field_dominance_index(p)[0] < 5
    ][:8]

    used_runners = set()

    def runner_key(pick):
        race = pick["race"]
        runner = pick["runner"]
        return (
            str(race.get("raceId")),
            str(runner.get("dogName")),
            str(runner.get("boxNumber") or runner.get("rugNumber")),
        )

    def unique_category(picks):
        clean = []

        for pick in picks:
            key = runner_key(pick)

            if key in used_runners:
                continue

            used_runners.add(key)
            clean.append(pick)

        return clean

    strong_singles = unique_category(strong_singles)
    multi_anchors = unique_category(multi_anchors)
    place_anchors = unique_category(place_anchors)
    top4_angles = unique_category(top4_angles)

    msg += "🔥 STRONG SINGLE CANDIDATES\n"
    msg += "Check these for win/place odds. Best used when the price is worth it.\n\n"

    if strong_singles:
        for i, pick in enumerate(strong_singles, start=1):
            save_pick_to_history(pick, "Strong Single")
            msg += format_short_pick(pick, i) + "\n"
    else:
        msg += "No strong single candidates found.\n"

    msg += "\n━━━━━━━━━━━━━━\n\n"

    msg += "🧱 MULTI ANCHORS\n"
    msg += "High-confidence runners that may be too short as singles but useful in multis.\n\n"

    if multi_anchors:
        for i, pick in enumerate(multi_anchors, start=1):
            save_pick_to_history(pick, "Multi Anchor")
            msg += format_short_pick(pick, i) + "\n"
    else:
        msg += "No strong multi anchors found.\n"

    msg += "\n━━━━━━━━━━━━━━\n\n"

    msg += "🛡 HIGH PLACE CHANCES\n"
    msg += "Only shown for 8-runner races where 3rd dividend is available.\n\n"

    if place_anchors:
        for i, pick in enumerate(place_anchors, start=1):
            save_pick_to_history(pick, "High Place")
            msg += format_short_pick(pick, i) + "\n"
    else:
        msg += "No strong 8-runner place candidates found.\n"

    msg += "\n━━━━━━━━━━━━━━\n\n"

    msg += "🏁 SAME RACE TOP 4 ANGLES\n"
    msg += "Best for 6-runner races. Use model top 3 to finish Top 4.\n\n"

    if top4_angles:
        for i, pick in enumerate(top4_angles, start=1):
            save_pick_to_history(pick, "Top 4 Angle")
            angle = get_same_race_top4_angle(pick)
            msg += f"{i}. {format_leg(pick)}\n"
            msg += f"Setup: {angle['risk']}\n"
            msg += "Use: "
            msg += ", ".join(format_runner_short(item[1]) for item in angle["top3"])
            msg += f"\nGap to danger: {angle['gap_to_danger']} pts\n\n"
    else:
        msg += "No strong 6-runner Top 4 setups found.\n"

    msg += "━━━━━━━━━━━━━━\n\n"

    msg += "🚫 AVOID / MESSY RACES\n"
    msg += "Low edge or weak model confidence. Be careful with these.\n\n"

    if avoid_races:
        for i, pick in enumerate(avoid_races, start=1):
            msg += f"{i}. {format_leg(pick)} — {dominance_label(pick['margin'])}\n"
    else:
        msg += "No obvious messy races from the top-ranked list.\n"

    msg += "\nUse /race Track RaceNumber for a full race breakdown."

    return msg[:4000]

def build_best_bets_message(target_date=None, track_search=None):
    if target_date is None:
        target_date = melbourne_today()

    ranked = scan_ranked(target_date, track_search)
    save_learning_from_scan(ranked)

    if not ranked:
        if track_search:
            return f"No upcoming races found for '{track_search}' on {target_date}."
        return f"No upcoming race/runner data found for {target_date}."

    return build_daily_betting_plan(ranked, target_date, track_search)

def build_tracks_message(target_date=None):
    if target_date is None:
        target_date = melbourne_today()

    races = get_all_races_for_date(target_date)

    races = [
        r for r in races
        if not race_is_resulted_or_invalid(r)
        and race_is_on_target_date(r, target_date)
        and not race_has_started(r, target_date)
    ]

    if not races:
        return f"No upcoming tracks found for {target_date}."

    meeting_track_map = build_meeting_track_map(races)
    tracks = {}

    for race in races:
        track = meeting_track_map.get(race.get("meetingId"), "Unknown Track")
        tracks.setdefault(track, 0)
        tracks[track] += 1

    msg = f"🐕 Upcoming tracks on {target_date}\n\n"

    for track, count in sorted(tracks.items()):
        msg += f"• {track} — {count} upcoming races\n"

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
        return f"No upcoming race found for {track_search} R{race_number} on {target_date}."

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

    top4 = format_same_race_top4(pick)
    if top4:
        msg += top4

    return msg[:4000]
