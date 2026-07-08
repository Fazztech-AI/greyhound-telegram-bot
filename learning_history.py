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

        predicted_dog TEXT,
        winning_dog TEXT,

        predicted_score REAL,
        winning_score REAL,

        predicted_trust REAL,
        winning_trust REAL,

        predicted_edge REAL,
        winning_edge REAL,

        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
