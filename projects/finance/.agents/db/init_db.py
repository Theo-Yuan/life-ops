"""
Initialize the Finance Plan Database.
Run once to create tables.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "finance_plan.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    with open(SCHEMA_PATH, "r") as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"数据库已初始化：{DB_PATH}")


if __name__ == "__main__":
    init_db()
