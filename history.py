from database import (
    get_history,
    get_statistics,
    get_recommendation_stats,
    get_score_band_stats,
    get_track_stats,
    get_box_stats,
)

def build_history_message(limit=25):
    rows = get_history(limit)

    if not rows:
        return "📒 No betting history recorded yet."

    msg = "📒 GREYHOUND BET HISTORY\n\n"

    for row in rows:
        msg += (
            f"#{row['id']} {row['race_date']} {row['track']} R{row['race_number']}\n"
            f"🐕 Box {row['box']} {row['dog']}\n"
            f"Result: {row['result']}\n"
            f"Score: {row['score']}/100\n"
            f"Margin: {row['margin']}\n"
            f"Race Trust: {row['race_trust']}\n"
            f"Field Edge: {row['field_edge']}\n"
            f"Recommendation: {row['recommendation']}\n\n"
        )

    return msg[:4000]


def build_statistics_message():
    stats = get_statistics()

    return (
        "📊 BOT PERFORMANCE\n\n"
        f"Selections: {stats['total']}\n"
        f"Wins: {stats['wins']}\n"
        f"Places: {stats['places']}\n"
        f"Losses: {stats['losses']}\n"
        f"Pending: {stats['pending']}\n\n"
        f"Win Strike Rate: {stats['strike_rate']}%"
    )

def build_recommendation_stats_message():
    rows = get_recommendation_stats()

    if not rows:
        return "📊 No recommendation stats yet."

    msg = "📊 PERFORMANCE BY RECOMMENDATION\n\n"

    for row in rows:
        total = row["total"]
        wins = row["wins"] or 0
        places = row["places"] or 0
        losses = row["losses"] or 0
        pending = row["pending"] or 0

        completed = wins + places + losses
        win_rate = round((wins / completed) * 100, 1) if completed else 0
        place_rate = round(((wins + places) / completed) * 100, 1) if completed else 0

        msg += (
            f"{row['recommendation']}\n"
            f"Total: {total}\n"
            f"Completed: {completed}\n"
            f"Wins: {wins} ({win_rate}%)\n"
            f"Win/Place: {wins + places} ({place_rate}%)\n"
            f"Losses: {losses}\n"
            f"Pending: {pending}\n\n"
        )

    return msg[:4000]

def build_score_band_stats_message():
    rows = get_score_band_stats()

    if not rows:
        return "📊 No score-band stats yet."

    msg = "📊 PERFORMANCE BY SCORE BAND\n\n"

    for row in rows:
        total = row["total"]
        wins = row["wins"] or 0
        places = row["places"] or 0
        losses = row["losses"] or 0
        pending = row["pending"] or 0

        completed = wins + places + losses
        win_rate = round((wins / completed) * 100, 1) if completed else 0
        place_rate = round(((wins + places) / completed) * 100, 1) if completed else 0

        msg += (
            f"Score {row['score_band']}\n"
            f"Total: {total}\n"
            f"Completed: {completed}\n"
            f"Wins: {wins} ({win_rate}%)\n"
            f"Win/Place: {wins + places} ({place_rate}%)\n"
            f"Losses: {losses}\n"
            f"Pending: {pending}\n\n"
        )

    return msg[:4000]

def build_track_stats_message():
    rows = get_track_stats()

    if not rows:
        return "📊 No track stats yet. Debug: get_track_stats returned 0 rows."

    msg = "📊 PERFORMANCE BY TRACK\n\n"

    for row in rows:
        total = row["total"]
        wins = row["wins"] or 0
        places = row["places"] or 0
        losses = row["losses"] or 0
        pending = row["pending"] or 0

        completed = wins + places + losses
        win_rate = round((wins / completed) * 100, 1) if completed else 0
        place_rate = round(((wins + places) / completed) * 100, 1) if completed else 0

        msg += (
            f"{row['track']}\n"
            f"Total: {total}\n"
            f"Completed: {completed}\n"
            f"Wins: {wins} ({win_rate}%)\n"
            f"Win/Place: {wins + places} ({place_rate}%)\n"
            f"Losses: {losses}\n"
            f"Pending: {pending}\n\n"
        )

    return msg[:4000]

def build_box_stats_message():
    rows = get_box_stats()

    if not rows:
        return "📊 No box stats yet. Debug: get_box_stats returned 0 rows."

    msg = "📊 PERFORMANCE BY BOX\n\n"

    for row in rows:
        total = row["total"]
        wins = row["wins"] or 0
        places = row["places"] or 0
        losses = row["losses"] or 0
        pending = row["pending"] or 0

        completed = wins + places + losses
        win_rate = round((wins / completed) * 100, 1) if completed else 0
        place_rate = round(((wins + places) / completed) * 100, 1) if completed else 0

        msg += (
            f"Box {row['box']}\n"
            f"Total: {total}\n"
            f"Completed: {completed}\n"
            f"Wins: {wins} ({win_rate}%)\n"
            f"Win/Place: {wins + places} ({place_rate}%)\n"
            f"Losses: {losses}\n"
            f"Pending: {pending}\n\n"
        )

    return msg[:4000]
