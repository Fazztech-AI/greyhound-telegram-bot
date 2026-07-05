from database import get_history, get_statistics


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
