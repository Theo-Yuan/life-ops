"""
Initialize the English Learning Database.
Run once to create tables.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "english_learning.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    with open(SCHEMA_PATH, "r") as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
