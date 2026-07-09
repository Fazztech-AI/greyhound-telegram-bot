from pathlib import Path
import sqlite3

DB = Path("learning_history.db")


def get_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_learning():
    conn = get_connection()

    conn.execute("""
CREATE TABLE IF NOT EXISTS learning (

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

    field_size INTEGER,

    finish_position INTEGER,
    result TEXT,

    learnt INTEGER DEFAULT 0,

    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

def save_learning_runner(
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
    field_size,
):
    if learning_runner_exists(race_id, dog):
        return

    conn = get_connection()

    conn.execute("""
        INSERT INTO learning (
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
            field_size
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
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
        field_size,
    ))

    conn.commit()
    conn.close()

def learning_runner_exists(race_id, dog):
    conn = get_connection()

    row = conn.execute("""
        SELECT id
        FROM learning
        WHERE race_id=?
        AND dog=?
        LIMIT 1
    """, (
        race_id,
        dog,
    )).fetchone()

    conn.close()
    return row is not None

def update_learning_result(race_id, dog, finish_position, result):
    conn = get_connection()

    conn.execute("""
        UPDATE learning
        SET
            finish_position=?,
            result=?
        WHERE race_id=?
        AND dog=?
    """, (
        finish_position,
        result,
        race_id,
        dog,
    ))

    conn.commit()
    conn.close()

def get_learning_summary():
    conn = get_connection()

    row = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN result='Won' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN result='Placed' THEN 1 ELSE 0 END) AS places,
            SUM(CASE WHEN result='Lost' THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN result IS NULL THEN 1 ELSE 0 END) AS pending
        FROM learning
    """).fetchone()

    conn.close()
    return row

def get_top_rank_learning():
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            race_id,
            MAX(CASE WHEN result='Won' THEN dog END) AS winner,
            MAX(CASE WHEN result='Won' THEN score END) AS winner_score,
            MAX(score) AS top_score
        FROM learning
        WHERE result IS NOT NULL
        GROUP BY race_id
    """).fetchall()

    total = 0
    top_wins = 0
    close_misses = 0

    for row in rows:
        if row["winner"] is None:
            continue

        total += 1

        if row["winner_score"] == row["top_score"]:
            top_wins += 1
        elif row["top_score"] - row["winner_score"] <= 5:
            close_misses += 1

    conn.close()

    return {
        "total": total,
        "top_wins": top_wins,
        "close_misses": close_misses,
        "top_win_rate": round((top_wins / total) * 100, 1) if total else 0,
    }
