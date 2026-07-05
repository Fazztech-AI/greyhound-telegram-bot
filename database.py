import sqlite3
from pathlib import Path

DB_FILE = Path("greyhound_history.db")


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table, column, column_type):
    existing = conn.execute(f"PRAGMA table_info({table})").fetchall()
    columns = [row["name"] for row in existing]

    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def initialise_database():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        race_id TEXT,
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
        finish_position INTEGER,
        starting_price REAL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_column(conn, "bets", "race_id", "TEXT")
    ensure_column(conn, "bets", "finish_position", "INTEGER")

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
    race_id=None,
):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO bets (
            race_id,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            race_id,
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


def pick_exists(race_date, track, race_number, dog, recommendation):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT id
        FROM bets
        WHERE race_date=?
        AND track=?
        AND race_number=?
        AND dog=?
        AND recommendation=?
        LIMIT 1
        """,
        (race_date, track, race_number, dog, recommendation),
    ).fetchone()

    conn.close()
    return row is not None


def update_result(bet_id, result, starting_price=None):
    conn = get_connection()

    conn.execute(
        """
        UPDATE bets
        SET result=?, starting_price=?
        WHERE id=?
        """,
        (result, starting_price, bet_id),
    )

    conn.commit()
    conn.close()


def update_pick_result(
    pick_id,
    result,
    finish_position=None,
    starting_price=None,
):
    conn = get_connection()

    conn.execute(
        """
        UPDATE bets
        SET
            result=?,
            finish_position=?,
            starting_price=?
        WHERE id=?
        """,
        (result, finish_position, starting_price, pick_id),
    )

    conn.commit()
    conn.close()


def get_pending_picks():
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM bets
        WHERE result='Pending'
    """).fetchall()

    conn.close()
    return rows


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

    total = conn.execute("SELECT COUNT(*) FROM bets").fetchone()[0]
    wins = conn.execute("SELECT COUNT(*) FROM bets WHERE result='Won'").fetchone()[0]
    places = conn.execute("SELECT COUNT(*) FROM bets WHERE result='Placed'").fetchone()[0]
    losses = conn.execute("SELECT COUNT(*) FROM bets WHERE result='Lost'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM bets WHERE result='Pending'").fetchone()[0]

    conn.close()

    strike_rate = round((wins / total) * 100, 1) if total else 0

    return {
        "total": total,
        "wins": wins,
        "places": places,
        "losses": losses,
        "pending": pending,
        "strike_rate": strike_rate,
    }
