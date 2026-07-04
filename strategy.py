"""
Greyhound AI v2
Strategy Engine

Turns scores and race trust into actual betting strategies.
"""

from race_trust import (
    race_trust_score,
    final_recommendation,
)

from same_race import (
    race_is_top4_candidate,
    multi_anchor_strength,
)


def strong_single(pick):
    trust, _, _ = race_trust_score(pick)

    return (
        pick["score"] >= 75
        and pick["margin"] >= 10
        and trust >= 70
    )


def elite_single(pick):
    trust, _, _ = race_trust_score(pick)

    return (
        pick["score"] >= 88
        and pick["margin"] >= 18
        and trust >= 80
    )


def multi_anchor(pick):
    trust, _, _ = race_trust_score(pick)

    return (
        pick["score"] >= 60
        and trust >= 60
    )


def safe_multi_leg(pick):
    trust, _, _ = race_trust_score(pick)

    return (
        pick["score"] >= 70
        and trust >= 65
    )


def value_runner(pick):
    """
    Placeholder until live odds are added.
    """

    trust, _, _ = race_trust_score(pick)

    return (
        pick["score"] >= 65
        and trust >= 70
    )


def avoid_race(pick):
    trust, _, _ = race_trust_score(pick)

    return (
        trust < 50
        or pick["margin"] < 5
        or pick["score"] < 50
    )


def confidence_stars(pick):
    score = pick["score"]

    if score >= 90:
        return "⭐⭐⭐⭐⭐"

    if score >= 80:
        return "⭐⭐⭐⭐"

    if score >= 70:
        return "⭐⭐⭐"

    if score >= 60:
        return "⭐⭐"

    return "⭐"


def betting_plan(pick):
    """
    Returns a dictionary describing how the model
    thinks this runner should be used.
    """

    trust, trust_label, warnings = race_trust_score(pick)

    return {
        "score": pick["score"],
        "margin": pick["margin"],
        "trust": trust,
        "trust_label": trust_label,
        "stars": confidence_stars(pick),
        "single": strong_single(pick),
        "elite_single": elite_single(pick),
        "multi_anchor": multi_anchor(pick),
        "safe_multi": safe_multi_leg(pick),
        "top4": race_is_top4_candidate(pick),
        "value": value_runner(pick),
        "avoid": avoid_race(pick),
        "recommendation": final_recommendation(pick),
        "anchor_strength": multi_anchor_strength(pick),
        "warnings": warnings,
    }


def best_singles(ranked, limit=5):
    return [
        pick
        for pick in ranked
        if strong_single(pick)
    ][:limit]


def elite_singles(ranked, limit=3):
    return [
        pick
        for pick in ranked
        if elite_single(pick)
    ][:limit]


def multi_anchors(ranked, limit=6):
    return [
        pick
        for pick in ranked
        if multi_anchor(pick)
    ][:limit]


def safe_multis(ranked, limit=4):
    return [
        pick
        for pick in ranked
        if safe_multi_leg(pick)
    ][:limit]


def same_race_candidates(ranked, limit=5):
    return [
        pick
        for pick in ranked
        if race_is_top4_candidate(pick)
    ][:limit]


def races_to_avoid(ranked, limit=8):
    return [
        pick
        for pick in ranked
        if avoid_race(pick)
    ][:limit]


def daily_summary(ranked):
    """
    Returns everything needed by formatter.py
    """

    return {
        "elite": elite_singles(ranked),
        "singles": best_singles(ranked),
        "anchors": multi_anchors(ranked),
        "safe_multis": safe_multis(ranked),
        "top4": same_race_candidates(ranked),
        "avoid": races_to_avoid(ranked),
    }
