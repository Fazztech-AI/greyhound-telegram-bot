"""
Greyhound AI v2
formatter.py

Formats Telegram output.
"""

from race_trust import race_trust_score
from same_race import (
    same_race_summary,
    recommended_same_race_bet,
)


def format_runner(runner):
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
        f"{pick['track']} "
        f"R{race_no} ({authority}) — "
        f"Box {box} {dog} — "
        f"{distance}m — {start}"
    )


def format_pick(pick, plan):
    trust, trust_label, warnings = race_trust_score(pick)

    msg = ""
    msg += f"{format_leg(pick)}\n"
    msg += f"Model Score: {pick['score']}/100\n"
    msg += f"Race Trust: {trust}/100 {trust_label}\n"
    msg += f"Recommendation: {plan['recommendation']}\n"
    msg += f"Confidence: {plan['stars']}\n"

    if warnings:
        msg += "\nWarnings:\n"
        for warning in warnings:
            msg += f"• {warning}\n"

    return msg


def format_section(title, picks, planner):

    msg = f"{title}\n\n"

    if not picks:
        msg += "None today.\n\n"
        return msg

    for i, pick in enumerate(picks, start=1):

        msg += f"{i}.\n"
        msg += format_pick(
            pick,
            planner(pick),
        )
        msg += "\n"

    return msg


def format_same_race_section(picks):

    msg = "🏁 SAME RACE MULTIS\n\n"

    if not picks:
        msg += "No Same Race opportunities today.\n\n"
        return msg

    for pick in picks:

        bet = recommended_same_race_bet(pick)

        msg += format_leg(pick) + "\n"

        if bet:

            msg += f"Market: {bet['market']}\n"
            msg += f"Strength: {bet['strength']}\n"
            msg += "Selections:\n"

            for runner in bet["runners"]:
                msg += f"• {format_runner(runner)}\n"

        msg += same_race_summary(pick)
        msg += "\n\n"

    return msg


def format_daily_plan(summary, planner, target_date):

    msg = ""
    msg += "🐕 GREYHOUND AI DAILY PLAN\n"
    msg += f"{target_date}\n\n"

    msg += (
        "Model finds the strongest runners.\n"
        "You decide whether the odds justify a single or multi.\n\n"
    )

    msg += format_section(
        "🔥 STRONG SINGLES",
        summary["singles"],
        planner,
    )

    msg += format_section(
        "⭐ ELITE SINGLES",
        summary["elite"],
        planner,
    )

    msg += format_section(
        "🧱 MULTI ANCHORS",
        summary["anchors"],
        planner,
    )

    msg += format_same_race_section(
        summary["top4"]
    )

    msg += format_section(
        "🚫 RACES TO AVOID",
        summary["avoid"],
        planner,
    )

    msg += (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Greyhound AI v2"
    )

    return msg[:4000]


def format_track_list(track_dict, target_date):

    msg = f"🐕 Tracks racing {target_date}\n\n"

    for track in sorted(track_dict):
        msg += (
            f"• {track} "
            f"({track_dict[track]} races)\n"
        )

    return msg[:4000]


def format_race_breakdown(pick):

    trust, label, warnings = race_trust_score(pick)

    msg = ""
    msg += (
        f"🐕 {pick['track']} "
        f"Race {pick['race'].get('raceNumber')}\n\n"
    )

    msg += (
        f"Distance: "
        f"{pick['race'].get('distance')}m\n"
    )

    msg += (
        f"Model Score: "
        f"{pick['score']}/100\n"
    )

    msg += (
        f"Race Trust: "
        f"{trust}/100 {label}\n\n"
    )

    msg += "🏆 Full Rankings\n\n"

    for i, item in enumerate(
        pick["full_rankings"],
        start=1,
    ):

        score, runner, pros, warn = item

        msg += (
            f"{i}. "
            f"{format_runner(runner)} "
            f"({score}/100)\n"
        )

        if pros:
            msg += f"   ✔ {pros[0]}\n"

        if warn:
            msg += f"   ⚠ {warn[0]}\n"

        msg += "\n"

    if warnings:

        msg += "General Warnings\n"

        for warning in warnings:
            msg += f"• {warning}\n"

    return msg[:4000]
