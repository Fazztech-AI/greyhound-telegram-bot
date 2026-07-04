"""
Greyhound AI v2
same_race.py

Same Race Multi & Top 4 logic.
"""

TOP4_MIN_GAP = 6
TOP4_STRONG_GAP = 10


def field_type(field_size):
    if field_size >= 8:
        return "FULL"

    if field_size == 7:
        return "SEVEN"

    if field_size == 6:
        return "SIX"

    if field_size == 5:
        return "FIVE"

    return "SMALL"


def gap_between(scored, first_index, second_index):
    if len(scored) <= second_index:
        return 0

    return round(
        scored[first_index][0] - scored[second_index][0],
        1,
    )


def top_three_runners(pick):
    return [
        item[1]
        for item in pick["full_rankings"][:3]
    ]


def top_four_runners(pick):
    return [
        item[1]
        for item in pick["full_rankings"][:4]
    ]


def same_race_top4_angle(pick):
    """
    Looks for a strong Same Race Top 4 opportunity.

    Works best with six-runner fields.
    """

    scored = pick["full_rankings"]
    field_size = pick["field_size"]

    if field_size != 6:
        return None

    if len(scored) < 6:
        return None

    top3 = scored[:3]

    gap3to4 = gap_between(scored, 2, 3)
    gap3to5 = gap_between(scored, 2, 4)
    gap4to5 = gap_between(scored, 3, 4)

    if gap3to5 < TOP4_MIN_GAP:
        return None

    if gap3to5 >= TOP4_STRONG_GAP:
        strength = "🟢 Excellent"

    else:
        strength = "🟡 Good"

    return {
        "strength": strength,
        "top3": top3,
        "gap3to4": gap3to4,
        "gap3to5": gap3to5,
        "gap4to5": gap4to5,
    }


def same_race_multi_angle(pick):
    """
    Suggests which Same Race market
    best suits the field size.
    """

    field = field_type(
        pick["field_size"]
    )

    if field == "SMALL":
        return None

    if field == "FIVE":
        return {
            "market": "Top 3",
            "legs": 2,
        }

    if field == "SIX":
        return {
            "market": "Top 4",
            "legs": 3,
        }

    if field == "SEVEN":
        return {
            "market": "Top 4",
            "legs": 3,
        }

    return {
        "market": "Top 4",
        "legs": 3,
    }


def race_is_top4_candidate(pick):
    return same_race_top4_angle(pick) is not None


def multi_anchor_strength(pick):
    score = pick["score"]
    margin = pick["margin"]

    if score >= 90 and margin >= 20:
        return "⭐⭐⭐⭐⭐"

    if score >= 80 and margin >= 15:
        return "⭐⭐⭐⭐"

    if score >= 70 and margin >= 10:
        return "⭐⭐⭐"

    if score >= 60:
        return "⭐⭐"

    return "⭐"


def same_race_summary(pick):
    angle = same_race_top4_angle(pick)

    if angle:
        return (
            f"🏁 Top 4 Angle • "
            f"{angle['strength']} • "
            f"Gap {angle['gap3to5']} pts"
        )

    multi = same_race_multi_angle(pick)

    if multi:
        return (
            f"🏁 {multi['market']} "
            f"({multi['legs']} selections)"
        )

    return "No Same Race opportunity"


def recommended_same_race_bet(pick):
    """
    Always returns RUNNER DICTIONARIES.
    Never tuples.
    """

    angle = same_race_top4_angle(pick)

    if angle:

        runners = [
            item[1]
            for item in angle["top3"]
        ]

        return {
            "market": "Same Race Top 4",
            "strength": angle["strength"],
            "runners": runners,
        }

    multi = same_race_multi_angle(pick)

    if multi:

        runners = [
            item[1]
            for item in pick["full_rankings"][: multi["legs"]]
        ]

        return {
            "market": multi["market"],
            "strength": "Standard",
            "runners": runners,
        }

    return None
