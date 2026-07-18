from __future__ import annotations

import math
import re
from statistics import mean, median
from typing import Any


# Fixed-odds bookmakers used to calculate the main market consensus.
# Betfair Exchange is analysed separately because exchange prices can be
# noticeably different from bookmaker prices.
FIXED_ODDS_BOOKMAKERS = {
    "sportsbet",
    "tab",
    "tabtouch",
    "neds",
    "ladbrokes_au",
    "pointsbetau",
    "playup",
    "unibet",
    "betright",
    "betr_au",
    "palmerbet",
}

EXCHANGE_BOOKMAKER = "betfair_ex_au"

MAX_BOOKMAKER_COVERAGE = 10


def _safe_float(value: Any) -> float | None:
    """Convert a value to a positive float, or return None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number) or number <= 1.0:
        return None

    return number


def _normalise_name(name: Any) -> str:
    """
    Normalise a runner name so minor feed differences do not create
    duplicate horses.

    Example:
        Spirit Of Luna
        Spirit Of Luna (Nz)

    Both become:
        spirit of luna
    """
    text = str(name or "").strip().lower()
    text = re.sub(r"\s*\([a-z]{2,3}\)\s*$", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _percentage_spread(prices: list[float]) -> float:
    """
    Return the percentage difference between the lowest and highest price,
    measured against the median price.
    """
    if len(prices) < 2:
        return 1.0

    middle = median(prices)

    if middle <= 0:
        return 1.0

    return (max(prices) - min(prices)) / middle


def _win_price_score(average_win_price: float | None) -> float:
    """
    Score the market's assessed win chance out of 40.

    This is based on price strength, not independent horse-form analysis.
    """
    if average_win_price is None:
        return 0.0

    implied_probability = 1.0 / average_win_price

    # A horse priced around $1.50 receives close to maximum points.
    # Scores reduce smoothly as odds increase.
    score = implied_probability * 60.0

    return _clamp(score, 0.0, 40.0)


def _place_price_score(average_place_price: float | None) -> float:
    """Score place-market strength out of 30."""
    if average_place_price is None:
        return 0.0

    if average_place_price <= 1.20:
        return 30.0
    if average_place_price <= 1.35:
        return 28.0
    if average_place_price <= 1.50:
        return 26.0
    if average_place_price <= 1.70:
        return 23.0
    if average_place_price <= 1.90:
        return 20.0
    if average_place_price <= 2.20:
        return 17.0
    if average_place_price <= 2.60:
        return 13.0
    if average_place_price <= 3.00:
        return 9.0
    if average_place_price <= 4.00:
        return 5.0

    return 1.0


def _agreement_score(win_prices: list[float]) -> float:
    """Score bookmaker agreement out of 20."""
    if len(win_prices) < 2:
        return 2.0

    spread = _percentage_spread(win_prices)

    if spread <= 0.05:
        return 20.0
    if spread <= 0.10:
        return 18.0
    if spread <= 0.15:
        return 16.0
    if spread <= 0.20:
        return 14.0
    if spread <= 0.30:
        return 11.0
    if spread <= 0.40:
        return 8.0
    if spread <= 0.60:
        return 5.0

    return 2.0


def _coverage_score(bookmaker_count: int) -> float:
    """Score bookmaker coverage out of 10."""
    if bookmaker_count <= 0:
        return 0.0

    return _clamp(
        bookmaker_count / MAX_BOOKMAKER_COVERAGE * 10.0,
        0.0,
        10.0,
    )


def _confidence_label(score: float) -> str:
    if score >= 82:
        return "Strong"
    if score >= 72:
        return "Playable"
    if score >= 62:
        return "Caution"
    return "Low"


def _extract_price_data(
    bookmakers: list[dict[str, Any]],
) -> dict[str, Any]:
    fixed_win_prices: list[float] = []
    fixed_place_prices: list[float] = []

    sportsbet_win: float | None = None
    sportsbet_place: float | None = None
    exchange_win: float | None = None
    exchange_lay: float | None = None

    bookmaker_keys: set[str] = set()

    for bookmaker in bookmakers:
        key = str(bookmaker.get("key") or "").strip().lower()

        if not key:
            continue

        bookmaker_keys.add(key)

        win_price = _safe_float(bookmaker.get("win_price"))
        place_price = _safe_float(bookmaker.get("place_price"))
        lay_price = _safe_float(bookmaker.get("lay_price"))

        if key == "sportsbet":
            sportsbet_win = win_price
            sportsbet_place = place_price

        if key == EXCHANGE_BOOKMAKER:
            exchange_win = win_price
            exchange_lay = lay_price
            continue

        if key in FIXED_ODDS_BOOKMAKERS:
            if win_price is not None:
                fixed_win_prices.append(win_price)

            if place_price is not None:
                fixed_place_prices.append(place_price)

    return {
        "fixed_win_prices": fixed_win_prices,
        "fixed_place_prices": fixed_place_prices,
        "sportsbet_win": sportsbet_win,
        "sportsbet_place": sportsbet_place,
        "exchange_win": exchange_win,
        "exchange_lay": exchange_lay,
        "bookmaker_count": len(bookmaker_keys),
    }


def _exchange_warning(
    average_win_price: float | None,
    exchange_win_price: float | None,
) -> str | None:
    """
    Flag when the Betfair Exchange price is materially longer than the
    fixed-odds consensus.
    """
    if average_win_price is None or exchange_win_price is None:
        return None

    difference = (
        exchange_win_price - average_win_price
    ) / average_win_price

    if difference >= 0.50:
        return "Exchange price is much longer than bookmaker consensus"

    if difference >= 0.25:
        return "Exchange price is longer than bookmaker consensus"

    return None


def _sportsbet_value_percentage(
    sportsbet_price: float | None,
    consensus_price: float | None,
) -> float | None:
    """
    Compare Sportsbet's price with the median fixed-odds price.

    A positive result means Sportsbet is offering a longer price.
    This is price-shopping value, not proof the horse is profitable.
    """
    if sportsbet_price is None or consensus_price is None:
        return None

    if consensus_price <= 0:
        return None

    return (
        (sportsbet_price - consensus_price)
        / consensus_price
        * 100.0
    )


def score_horse_runner(
    runner: dict[str, Any],
) -> dict[str, Any]:
    """
    Score one runner out of 100 using the available betting market.

    Components:
        Win-market strength:       40 points
        Place-market strength:     30 points
        Market agreement:          20 points
        Bookmaker coverage:        10 points
    """
    name = str(runner.get("name") or "Unknown Runner").strip()
    number = runner.get("number")
    bookmakers = runner.get("bookmakers") or []

    price_data = _extract_price_data(bookmakers)

    fixed_win_prices = price_data["fixed_win_prices"]
    fixed_place_prices = price_data["fixed_place_prices"]

    average_win_price = (
        mean(fixed_win_prices)
        if fixed_win_prices
        else None
    )

    median_win_price = (
        median(fixed_win_prices)
        if fixed_win_prices
        else None
    )

    average_place_price = (
        mean(fixed_place_prices)
        if fixed_place_prices
        else None
    )

    median_place_price = (
        median(fixed_place_prices)
        if fixed_place_prices
        else None
    )

    win_score = _win_price_score(average_win_price)
    place_score = _place_price_score(average_place_price)
    agreement_score = _agreement_score(fixed_win_prices)
    coverage_score = _coverage_score(
        price_data["bookmaker_count"]
    )

    raw_score = (
        win_score
        + place_score
        + agreement_score
        + coverage_score
    )

    warnings: list[str] = []

    if len(fixed_win_prices) < 3:
        warnings.append("Limited bookmaker coverage")

    if not fixed_place_prices:
        warnings.append("No fixed-odds place market available")

    market_spread = _percentage_spread(fixed_win_prices)

    if market_spread > 0.40:
        warnings.append("Bookmakers disagree significantly")

    exchange_warning = _exchange_warning(
        average_win_price,
        price_data["exchange_win"],
    )

    if exchange_warning:
        warnings.append(exchange_warning)

    # Apply modest deductions for poor or incomplete data.
    penalty = 0.0

    if len(fixed_win_prices) < 3:
        penalty += 5.0

    if not fixed_place_prices:
        penalty += 5.0

    if market_spread > 0.60:
        penalty += 5.0

    score = round(
        _clamp(raw_score - penalty, 0.0, 100.0),
        1,
    )

    sportsbet_value = _sportsbet_value_percentage(
        price_data["sportsbet_win"],
        median_win_price,
    )

    return {
        "name": name,
        "normalised_name": _normalise_name(name),
        "number": number,
        "score": score,
        "confidence": _confidence_label(score),
        "win_score": round(win_score, 1),
        "place_score": round(place_score, 1),
        "agreement_score": round(agreement_score, 1),
        "coverage_score": round(coverage_score, 1),
        "average_win_price": (
            round(average_win_price, 2)
            if average_win_price is not None
            else None
        ),
        "median_win_price": (
            round(median_win_price, 2)
            if median_win_price is not None
            else None
        ),
        "average_place_price": (
            round(average_place_price, 2)
            if average_place_price is not None
            else None
        ),
        "median_place_price": (
            round(median_place_price, 2)
            if median_place_price is not None
            else None
        ),
        "sportsbet_win": price_data["sportsbet_win"],
        "sportsbet_place": price_data["sportsbet_place"],
        "exchange_win": price_data["exchange_win"],
        "exchange_lay": price_data["exchange_lay"],
        "sportsbet_value_percentage": (
            round(sportsbet_value, 1)
            if sportsbet_value is not None
            else None
        ),
        "bookmaker_count": price_data["bookmaker_count"],
        "market_spread_percentage": round(
            market_spread * 100.0,
            1,
        ),
        "warnings": warnings,
    }


def _merge_duplicate_runners(
    runners: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge duplicated runners appearing under slightly different names or
    separate bookmaker feeds.

    PuntersEdge can return examples such as:
        Crazy Town
        Crazy Town (Nz)

    Their bookmaker lists are combined before scoring.
    """
    merged: dict[str, dict[str, Any]] = {}

    for runner in runners:
        name = str(runner.get("name") or "").strip()
        normalised_name = _normalise_name(name)

        if not normalised_name:
            continue

        if normalised_name not in merged:
            merged[normalised_name] = {
                "name": name,
                "number": runner.get("number"),
                "bookmakers": [],
            }

        existing_bookmakers = merged[normalised_name]["bookmakers"]
        known_keys = {
            str(bookmaker.get("key") or "").lower()
            for bookmaker in existing_bookmakers
        }

        for bookmaker in runner.get("bookmakers") or []:
            key = str(bookmaker.get("key") or "").lower()

            if key and key not in known_keys:
                existing_bookmakers.append(bookmaker)
                known_keys.add(key)

    return list(merged.values())


def score_horse_race(
    race: dict[str, Any],
) -> dict[str, Any]:
    """Score and rank every runner in a race."""

    raw_runners = race.get("runners") or []

    active_runners = []

    for runner in raw_runners:
        status = str(runner.get("status") or "").lower()

        if runner.get("scratched") is True:
            continue

        if status in {
            "scratched",
            "scratch",
            "late scratching",
            "withdrawn",
            "removed",
        }:
            continue

        active_runners.append(runner)

    runners = _merge_duplicate_runners(active_runners)

    scored_runners = [
        score_horse_runner(runner)
        for runner in runners
    ]

    scored_runners.sort(
        key=lambda runner: (
            runner["score"],
            -(runner["median_win_price"] or 9999),
        ),
        reverse=True,
    )

    favourite = scored_runners[0] if scored_runners else None
    second = (
        scored_runners[1]
        if len(scored_runners) >= 2
        else None
    )

    score_edge = 0.0

    if favourite and second:
        score_edge = round(
            favourite["score"] - second["score"],
            1,
        )

    race_trust = _calculate_race_trust(
        scored_runners,
        score_edge,
    )

    return {
        "race_id": race.get("race_id"),
        "source_id": race.get("source_id"),
        "venue": race.get("venue") or "Unknown Venue",
        "race_number": race.get("race_number"),
        "start_time": race.get("start_time"),
        "country": race.get("country"),
        "category": race.get("category"),
        "runner_count": len(scored_runners),
        "score_edge": score_edge,
        "race_trust": race_trust,
        "runners": scored_runners,
    }


def _calculate_race_trust(
    runners: list[dict[str, Any]],
    score_edge: float,
) -> dict[str, Any]:
    """Calculate an overall market-based race trust score."""
    if len(runners) < 3:
        return {
            "score": 30.0,
            "label": "Low",
            "warnings": ["Too few priced runners"],
        }

    top_runner = runners[0]

    score = 40.0

    # Stronger leading runner.
    score += min(top_runner["score"] * 0.35, 30.0)

    # Separation between the top two runners.
    score += min(score_edge * 1.5, 15.0)

    # Broad bookmaker coverage.
    score += min(
        top_runner["bookmaker_count"],
        10,
    )

    warnings: list[str] = []

    if score_edge < 3:
        warnings.append("Very little separation between top runners")
        score -= 8

    if top_runner["market_spread_percentage"] > 35:
        warnings.append("Top runner has unstable market pricing")
        score -= 8

    if len(runners) >= 14:
        warnings.append("Large field")
        score -= 5

    final_score = round(
        _clamp(score, 0.0, 100.0),
        1,
    )

    if final_score >= 75:
        label = "High"
    elif final_score >= 62:
        label = "Playable"
    elif final_score >= 50:
        label = "Caution"
    else:
        label = "Low"

    return {
        "score": final_score,
        "label": label,
        "warnings": warnings,
    }


def score_horse_races(
    races: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Score a list of PuntersEdge horse races."""
    scored_races = [
        score_horse_race(race)
        for race in races
        if str(race.get("category") or "").lower() == "horse"
    ]

    scored_races.sort(
        key=lambda race: (
            race["race_trust"]["score"],
            race["runners"][0]["score"]
            if race["runners"]
            else 0,
        ),
        reverse=True,
    )

    return scored_races
