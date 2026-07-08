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

    predicted_dog TEXT,
    predicted_box INTEGER,

    winner_dog TEXT,
    winner_box INTEGER,

    predicted_score REAL,
    winner_score REAL,

    predicted_margin REAL,
    winner_margin REAL,

    predicted_trust REAL,
    winner_trust REAL,

    predicted_edge REAL,
    winner_edge REAL,

    field_size INTEGER,

    learnt INTEGER DEFAULT 0,

    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

    conn.commit()
    conn.close()
