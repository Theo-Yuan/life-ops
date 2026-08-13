"""
record.py — Write DailyDictation diff into the study_log database.

Usage:
    python diff.py --auto --json | python record.py
    python record.py --diff diff_output.json
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / ".agents" / "db" / "english_learning.db"


def get_conn():
    return sqlite3.connect(str(DB_PATH))


def record_entry(conn, date: str, duration_min: int, detail: str, notes: str = ""):
    """Insert a study_log entry."""
    conn.execute(
        "INSERT INTO study_log (date, duration_min, activity, detail, notes) "
        "VALUES (?, ?, 'listening', ?, ?)",
        (date, duration_min, detail, notes),
    )


def record_from_diff(diff: dict, topic: str = ""):
    """Record all detected activity from a diff into study_log."""
    conn = get_conn()
    date = diff["date"]

    # Check if already recorded for today
    existing = conn.execute(
        "SELECT id FROM study_log WHERE date = ? AND notes LIKE '%daily-dictation-auto%'",
        (date,),
    ).fetchall()
    if existing:
        print(f"Skipping: {len(existing)} auto entries already exist for {date}")
        conn.close()
        return

    new_lessons = diff.get("new_recent_lessons", [])
    increased = diff.get("increased_completion_lessons", [])
    all_changed = new_lessons + increased
    api_minutes = diff.get("today_minutes_api", 0)
    time_spent = diff.get("time_spent_minutes", 0)

    # 优先用 API 单日分钟数（精确），time_spent 是两天快照差值，隔天会虚高
    effective_minutes = api_minutes or time_spent

    if not all_changed and effective_minutes == 0:
        print(f"No activity detected for {date}, nothing to record.")
        conn.close()
        return

    # 逐条课程明细（duration 记 0，避免与聚合时长重复计数）
    for lesson in all_changed:
        cat = lesson.get("category", "unknown")
        title = lesson.get("title", "unknown")
        completions = lesson.get("completions", 1)
        prev_comp = lesson.get("prev_completions")

        if prev_comp is not None:
            detail = f"DailyDictation [{cat}]: {title} (completion #{prev_comp + 1}→{completions})"
        else:
            detail = f"DailyDictation [{cat}]: {title}"

        if topic:
            detail += f" — topic: {topic}"

        record_entry(conn, date, 0, detail, "source: daily-dictation-auto")

    # 聚合时长记录：始终写入，保证 study_log 能正确反映当天听写时长
    if effective_minutes > 0:
        detail = "DailyDictation: listening practice"
        if topic:
            detail += f" — topic: {topic}"
        record_entry(conn, date, effective_minutes, detail,
                     "source: daily-dictation-auto (aggregate)")

    conn.commit()
    count = len(all_changed) + (1 if effective_minutes > 0 else 0)
    print(f"Recorded {count} entries for {date}" +
          (f" ({effective_minutes} min)" if effective_minutes > 0 else ""))

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Record DailyDictation diff to study_log")
    parser.add_argument("--diff", help="Path to diff JSON file")
    parser.add_argument("--topic", default="",
                        help="Current study topic (e.g., 'IELTS Listening')")
    args = parser.parse_args()

    if args.diff:
        with open(args.diff) as f:
            diff = json.load(f)
    else:
        # Read from stdin (pipe from diff.py)
        raw = sys.stdin.read()
        if not raw.strip():
            print("Error: no diff data provided via stdin or --diff", file=sys.stderr)
            sys.exit(1)
        diff = json.loads(raw)

    record_from_diff(diff, args.topic)


if __name__ == "__main__":
    main()
