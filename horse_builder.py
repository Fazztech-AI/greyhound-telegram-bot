from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from horse_client import get_horse_races
from horse_scorer import score_horse_races


MELBOURNE = ZoneInfo("Australia/Melbourne")

MAX_SCAN_RACES = 25
MAX_ITEMS_PER_SECTION = 5


def _format_start_time(start_time: str | None) -> str:
    if not start_time:
        return "Unknown time"

    try:
        parsed = datetime.fromisoformat(
            start_time.replace("Z", "+00:00")
        )
        local_time = parsed.astimezone(MELBOURNE)

        return local_time.strftime("%I:%M %p").lstrip("0")

    except (TypeError, ValueError):
        return "Unknown time"


def _race_heading(race: dict[str, Any]) -> str:
    venue = race.get("venue") or "Unknown Venue"
    race_number = race.get("race_number") or "?"
    start_time = _format_start_time(race.get("start_time"))

    return f"{venue} R{race_number} — {start_time}"


def _safe_price(value: Any) -> str:
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return "Unavailable"


def _normalised_runner_names(
    race: dict[str, Any],
) -> set[str]:
    names: set[str] = set()

    for runner in race.get("runners") or []:
        name = str(
            runner.get("normalised_name")
            or runner.get("name")
            or ""
        ).strip().lower()

        if name:
            names.add(name)

    return names


def _race_market_coverage(race: dict[str, Any]) -> int:
    total = 0

    for runner in race.get("runners") or []:
        total += int(runner.get("bookmaker_count") or 0)

    return total


def _deduplicate_scored_races(
    races: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Remove obvious duplicate race feeds.

    PuntersEdge can occasionally return the same underlying race under
    different venue labels or source feeds. When two races share the same
    start time and most runner names, keep the version with better coverage.
    """
    selected: list[dict[str, Any]] = []

    for candidate in races:
        candidate_names = _normalised_runner_names(candidate)
        candidate_time = candidate.get("start_time")

        duplicate_index: int | None = None

        for index, existing in enumerate(selected):
            if candidate_time != existing.get("start_time"):
                continue

            existing_names = _normalised_runner_names(existing)

            if not candidate_names or not existing_names:
                continue

            overlap = len(candidate_names & existing_names)
            smaller_field = min(
                len(candidate_names),
                len(existing_names),
            )

            if smaller_field and overlap / smaller_field >= 0.60:
                duplicate_index = index
                break

        if duplicate_index is None:
            selected.append(candidate)
            continue

        existing = selected[duplicate_index]

        if (
            _race_market_coverage(candidate)
            > _race_market_coverage(existing)
        ):
            selected[duplicate_index] = candidate

    return selected


def _runner_summary(
    race: dict[str, Any],
    runner: dict[str, Any],
    include_value: bool = False,
) -> str:
    barrier = runner.get("number")
    name = runner.get("name") or "Unknown Runner"

    lines = [
        _race_heading(race),
        f"#{number} {name}",
        f"Rating: {runner.get('score', 0):.1f}/100",
        f"Confidence: {runner.get('confidence', 'Unknown')}",
        (
            f"Race trust: "
            f"{race.get('race_trust', {}).get('score', 0):.1f}/100 "
            f"({race.get('race_trust', {}).get('label', 'Unknown')})"
        ),
        f"Top-runner edge: +{race.get('score_edge', 0):.1f}",
    ]

    sportsbet_win = runner.get("sportsbet_win")
    sportsbet_place = runner.get("sportsbet_place")

    if sportsbet_win is not None:
        lines.append(
            f"Sportsbet win: {_safe_price(sportsbet_win)}"
        )
    else:
        lines.append(
            "Sportsbet win: Unavailable"
        )

    if sportsbet_place is not None:
        lines.append(
            f"Sportsbet place: {_safe_price(sportsbet_place)}"
        )
    else:
        lines.append(
            "Sportsbet place: Unavailable"
        )

    average_win = runner.get("average_win_price")

    if average_win is not None:
        lines.append(
            f"Average bookmaker win: {_safe_price(average_win)}"
        )

    lines.append(
        f"Bookmaker agreement: "
        f"{runner.get('agreement_score', 0):.1f}/20"
    )
    lines.append(
        f"Bookmakers priced: {runner.get('bookmaker_count', 0)}"
    )

    if include_value:
        value = runner.get("sportsbet_value_percentage")

        if value is not None:
            prefix = "+" if value >= 0 else ""
            lines.append(
                f"Sportsbet vs median: {prefix}{value:.1f}%"
            )

    warnings = runner.get("warnings") or []

    for warning in warnings[:2]:
        lines.append(f"⚠️ {warning}")

    return "\n".join(lines)


def _qualifies_as_strong_win(
    race: dict[str, Any],
    runner: dict[str, Any],
) -> bool:
    win_price = runner.get("sportsbet_win")
    trust = race.get("race_trust", {}).get("label")
    score = float(runner.get("score") or 0)
    edge = float(race.get("score_edge") or 0)

    return (
        trust in {"High", "Playable"}
        and score >= 72
        and edge >= 3
        and win_price is not None
        and 1.50 <= float(win_price) <= 7.00
    )


def _qualifies_as_place(
    race: dict[str, Any],
    runner: dict[str, Any],
) -> bool:
    place_price = runner.get("sportsbet_place")
    trust = race.get("race_trust", {}).get("label")
    score = float(runner.get("score") or 0)

    return (
        trust in {"High", "Playable"}
        and score >= 68
        and place_price is not None
        and float(place_price) >= 1.50
    )


def _qualifies_as_multi_anchor(
    race: dict[str, Any],
    runner: dict[str, Any],
) -> bool:
    win_price = runner.get("sportsbet_win")
    trust_score = float(
        race.get("race_trust", {}).get("score") or 0
    )
    score = float(runner.get("score") or 0)
    edge = float(race.get("score_edge") or 0)

    return (
        trust_score >= 75
        and score >= 76
        and edge >= 5
        and win_price is not None
        and 1.20 <= float(win_price) <= 2.80
    )


def _qualifies_as_value(
    race: dict[str, Any],
    runner: dict[str, Any],
) -> bool:
    win_price = runner.get("sportsbet_win")
    value = runner.get("sportsbet_value_percentage")
    trust = race.get("race_trust", {}).get("label")
    score = float(runner.get("score") or 0)
    warnings = runner.get("warnings") or []

    exchange_warning = any(
        "Exchange price" in warning
        for warning in warnings
    )

    return (
        trust in {"High", "Playable", "Caution"}
        and score >= 60
        and win_price is not None
        and float(win_price) >= 2.00
        and value is not None
        and float(value) >= 7.0
        and not exchange_warning
    )


def _collect_recommendations(
    scored_races: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    strong_wins: list[dict[str, Any]] = []
    place_chances: list[dict[str, Any]] = []
    multi_anchors: list[dict[str, Any]] = []
    value_bets: list[dict[str, Any]] = []
    avoid_races: list[dict[str, Any]] = []

    for race in scored_races:
        runners = race.get("runners") or []

        if not runners:
            avoid_races.append(
                {
                    "race": race,
                    "reason": "No priced runners available",
                }
            )
            continue

        top_runner = runners[0]
        race_trust = race.get("race_trust", {})
        trust_label = race_trust.get("label", "Low")
        trust_score = float(race_trust.get("score") or 0)

        item = {
            "race": race,
            "runner": top_runner,
        }

        if _qualifies_as_strong_win(race, top_runner):
            strong_wins.append(item)

        if _qualifies_as_place(race, top_runner):
            place_chances.append(item)

        if _qualifies_as_multi_anchor(race, top_runner):
            multi_anchors.append(item)

        if _qualifies_as_value(race, top_runner):
            value_bets.append(item)

        if (
            trust_label == "Low"
            or trust_score < 50
            or float(race.get("score_edge") or 0) < 2
        ):
            reasons = race_trust.get("warnings") or []

            avoid_races.append(
                {
                    "race": race,
                    "reason": (
                        "; ".join(reasons)
                        if reasons
                        else "Open market with little separation"
                    ),
                }
            )

    strong_wins.sort(
        key=lambda item: (
            item["runner"]["score"],
            item["race"]["race_trust"]["score"],
        ),
        reverse=True,
    )

    place_chances.sort(
        key=lambda item: (
            item["runner"]["score"],
            item["race"]["race_trust"]["score"],
        ),
        reverse=True,
    )

    multi_anchors.sort(
        key=lambda item: (
            item["race"]["race_trust"]["score"],
            item["runner"]["score"],
        ),
        reverse=True,
    )

    value_bets.sort(
        key=lambda item: (
            item["runner"].get(
                "sportsbet_value_percentage"
            )
            or 0
        ),
        reverse=True,
    )

    return {
        "strong_wins": strong_wins,
        "place_chances": place_chances,
        "multi_anchors": multi_anchors,
        "value_bets": value_bets,
        "avoid_races": avoid_races,
    }


def _add_selection_section(
    lines: list[str],
    heading: str,
    selections: list[dict[str, Any]],
    empty_message: str,
    include_value: bool = False,
) -> None:
    lines.extend(
        [
            "",
            heading,
            "",
        ]
    )

    if not selections:
        lines.append(empty_message)
        return

    for index, item in enumerate(
        selections[:MAX_ITEMS_PER_SECTION],
        start=1,
    ):
        lines.append(
            f"{index}. "
            + _runner_summary(
                item["race"],
                item["runner"],
                include_value=include_value,
            )
        )
        lines.append("")


def build_horse_bets_message(
    limit: int = MAX_SCAN_RACES,
) -> str:
    raw_races = get_horse_races(limit=limit)

    if isinstance(raw_races, list):
        races = raw_races

    elif isinstance(raw_races, dict):
        races = (
            raw_races.get("races")
            or raw_races.get("data")
            or raw_races.get("results")
            or []
        )

    else:
        raise RuntimeError(
            "PuntersEdge returned an unexpected response type."
        )

    if not isinstance(races, list):
        raise RuntimeError(
            "PuntersEdge response did not contain a race list."
        )

    scored_races = score_horse_races(races)
    scored_races = _deduplicate_scored_races(scored_races)

    if not scored_races:
        return (
            "🐎 AUSTRALIAN HORSE SCANNER\n\n"
            "No upcoming Australian horse races were available."
        )

    recommendations = _collect_recommendations(
        scored_races
    )

    lines = [
        "🐎 AUSTRALIAN HORSE SCANNER",
        "",
        f"Races analysed: {len(scored_races)}",
        (
            "Ratings are based on bookmaker market strength, "
            "place prices, agreement and coverage."
        ),
        (
            "They are not guaranteed winning probabilities."
        ),
    ]

    _add_selection_section(
        lines,
        "🏆 STRONG WIN CHANCES",
        recommendations["strong_wins"],
        "No strong win selections currently qualified.",
    )

    _add_selection_section(
        lines,
        "🛡️ HIGH PLACE CHANCES",
        recommendations["place_chances"],
        (
            "No place selections at Sportsbet odds of "
            "$1.50 or higher currently qualified."
        ),
    )

    _add_selection_section(
        lines,
        "🔥 MULTI ANCHORS",
        recommendations["multi_anchors"],
        "No high-trust multi anchors currently qualified.",
    )

    _add_selection_section(
        lines,
        "💎 SPORTSBET VALUE",
        recommendations["value_bets"],
        (
            "No clear Sportsbet price advantages currently "
            "qualified."
        ),
        include_value=True,
    )

    lines.extend(
        [
            "",
            "⚠️ AVOID / MESSY RACES",
            "",
        ]
    )

    avoid_races = recommendations["avoid_races"]

    if avoid_races:
        for item in avoid_races[:6]:
            lines.append(
                f"• {_race_heading(item['race'])}: "
                f"{item['reason']}"
            )
    else:
        lines.append(
            "No major market-trust warnings detected."
        )

    lines.extend(
        [
            "",
            "Rules:",
            "• Minimum $1.50 for win/place singles.",
            (
                "• Shorter runners can still appear as "
                "multi anchors."
            ),
            (
                "• Value means Sportsbet is longer than the "
                "median bookmaker price, not that a bet is "
                "guaranteed profitable."
            ),
        ]
    )

    return "\n".join(lines)
