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
