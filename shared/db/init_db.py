"""Initialize a study database. Run once to create tables.

用法:
    python init_db.py --db <path.db> --schema <schema.sql>
"""
import sqlite3
import argparse


def init_db(db_path, schema_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    with open(schema_path, "r") as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"数据库已初始化：{db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="初始化学习数据库")
    parser.add_argument("--db", required=True, help="SQLite 数据库路径")
    parser.add_argument("--schema", required=True, help="schema.sql 路径")
    args = parser.parse_args()
    init_db(args.db, args.schema)
