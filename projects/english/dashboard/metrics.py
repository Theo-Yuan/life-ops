#!/usr/bin/env python3
"""Generate metrics.json from the machine-local english learning data.

Reads the SQLite study_log table and all daily-dictation JSON files, then writes
a metrics.json file in the same directory as this script.

Usage:
    python3 metrics.py --data <DATA>
"""
import argparse
import glob
import json
import os
import sqlite3
from datetime import date, datetime, timezone

DB_REL = os.path.join(".agents", "db", "english_learning.db")
DICT_REL = os.path.join("tmp", "daily-dictation", "*.json")


def load_study_log(data_dir):
    db_path = os.path.join(data_dir, DB_REL)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT date, duration_min, activity FROM study_log"
        ).fetchall()
    finally:
        conn.close()

    total_minutes = sum(r[1] for r in rows)
    distinct_days = len({r[0] for r in rows})
    latest_date = max((r[0] for r in rows), default=None)
    streak_days = compute_streak_days({r[0] for r in rows})
    by_activity = {}
    for _date, minutes, activity in rows:
        agg = by_activity.setdefault(activity, {"count": 0, "minutes": 0})
        agg["count"] += 1
        agg["minutes"] += minutes

    return {
        "rows": len(rows),
        "total_minutes": total_minutes,
        "distinct_days": distinct_days,
        "latest_date": latest_date,
        "streak_days": streak_days,
        "by_activity": by_activity,
    }


def compute_streak_days(dates):
    """Length of the longest run of consecutive calendar days ending at the max date."""
    if not dates:
        return 0
    ordered = sorted(date.fromisoformat(d) for d in dates)
    streak = 1
    for prev, cur in zip(ordered, ordered[1:]):
        if (cur - prev).days == 1:
            streak += 1
        else:
            streak = 1
    return streak


def load_dictation(data_dir):
    pattern = os.path.join(data_dir, DICT_REL)
    files = sorted(glob.glob(pattern))

    sum_active_time_hours = 0.0
    sum_lesson_completions = 0
    max_active_days = 0
    max_last_7d_hours = 0.0
    max_last_30d_hours = 0.0
    latest = None
    latest_date = None

    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        stats = data.get("stats", {})
        sum_active_time_hours += stats.get("active_time_hours", 0) or 0
        sum_lesson_completions += stats.get("lesson_completions", 0) or 0
        max_active_days = max(max_active_days, stats.get("active_days", 0) or 0)
        max_last_7d_hours = max(
            max_last_7d_hours, stats.get("last_7d_hours", 0) or 0
        )
        max_last_30d_hours = max(
            max_last_30d_hours, stats.get("last_30d_hours", 0) or 0
        )
        date = data.get("date", "")
        if latest_date is None or date > latest_date:
            latest_date = date
            latest = data

    recent_lessons = []
    if latest is not None:
        for lesson in latest.get("stats", {}).get("recent_lessons", []):
            recent_lessons.append(
                {
                    "title": lesson.get("title", ""),
                    "category": lesson.get("category", ""),
                    "completions": lesson.get("completions", 0),
                }
            )

    return {
        "file_count": len(files),
        "sum_active_time_hours": round(sum_active_time_hours, 2),
        "sum_lesson_completions": sum_lesson_completions,
        "max_active_days": max_active_days,
        "max_last_7d_hours": round(max_last_7d_hours, 2),
        "max_last_30d_hours": round(max_last_30d_hours, 2),
        "recent_lessons": recent_lessons,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate english dashboard metrics.")
    parser.add_argument("--data", required=True, help="Path to the english data dir")
    args = parser.parse_args()

    metrics = {
        "study_log": load_study_log(args.data),
        "dictation": load_dictation(args.data),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metrics.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
