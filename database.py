import sqlite3
from pathlib import Path

DB_FILE = Path("greyhound_history.db")


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_database():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        race_date TEXT,
        track TEXT,
        race_number INTEGER,

        dog TEXT,
        box INTEGER,

        score REAL,
        margin REAL,
        race_trust REAL,
        field_edge REAL,

        recommendation TEXT,

        result TEXT DEFAULT 'Pending',

        starting_price REAL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_pick(
    race_date,
    track,
    race_number,
    dog,
    box,
    score,
    margin,
    race_trust,
    field_edge,
    recommendation,
):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO bets (
            race_date,
            track,
            race_number,
            dog,
            box,
            score,
            margin,
            race_trust,
            field_edge,
            recommendation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            race_date,
            track,
            race_number,
            dog,
            box,
            score,
            margin,
            race_trust,
            field_edge,
            recommendation,
        ),
    )

    conn.commit()
    conn.close()


def update_result(bet_id, result, starting_price=None):
    conn = get_connection()

    conn.execute(
        """
        UPDATE bets
        SET
            result=?,
            starting_price=?
        WHERE id=?
        """,
        (
            result,
            starting_price,
            bet_id,
        ),
    )

    conn.commit()
    conn.close()


def get_history(limit=100):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM bets
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return rows


def get_statistics():
    conn = get_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM bets"
    ).fetchone()[0]

    wins = conn.execute(
        "SELECT COUNT(*) FROM bets WHERE result='Won'"
    ).fetchone()[0]

    places = conn.execute(
        "SELECT COUNT(*) FROM bets WHERE result='Placed'"
    ).fetchone()[0]

    losses = conn.execute(
        "SELECT COUNT(*) FROM bets WHERE result='Lost'"
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM bets WHERE result='Pending'"
    ).fetchone()[0]

    conn.close()

    strike_rate = 0

    if total:
        strike_rate = round((wins / total) * 100, 1)

    return {
        "total": total,
        "wins": wins,
        "places": places,
        "losses": losses,
        "pending": pending,
        "strike_rate": strike_rate,
    }
