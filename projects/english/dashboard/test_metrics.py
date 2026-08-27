#!/usr/bin/env python3
"""Verify metrics.json matches the source data and structural anchors hold.

Recomputes the same derived values from the SQLite study_log and the
daily-dictation JSONs, then asserts metrics.json matches. Prints a terse
OK or FAIL; exits 0 on pass, 1 on fail.

Usage:
    python3 test_metrics.py --data <DATA>
"""
import argparse
import glob
import json
import os
import sqlite3
import sys
from datetime import date

DB_REL = os.path.join(".agents", "db", "english_learning.db")
DICT_REL = os.path.join("tmp", "daily-dictation", "*.json")


def recompute_study_log(data_dir):
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
    streak_days = recompute_streak_days({r[0] for r in rows})
    by_activity = {}
    for _date, minutes, activity in rows:
        agg = by_activity.setdefault(activity, {"count": 0, "minutes": 0})
        agg["count"] += 1
        agg["minutes"] += minutes

    return {
        "rows": len(rows),
        "total_minutes": total_minutes,
        "distinct_days": distinct_days,
        "streak_days": streak_days,
        "by_activity": by_activity,
    }


def recompute_streak_days(dates):
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


def recompute_dictation(data_dir):
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
    parser = argparse.ArgumentParser(description="Verify metrics.json consistency.")
    parser.add_argument("--data", required=True, help="Path to the english data dir")
    args = parser.parse_args()

    metrics_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "metrics.json"
    )
    if not os.path.exists(metrics_path):
        print("FAIL: metrics.json not found (run metrics.py first)")
        return 1

    with open(metrics_path, "r", encoding="utf-8") as fh:
        metrics = json.load(fh)

    expected_study = recompute_study_log(args.data)
    expected_dict = recompute_dictation(args.data)

    failures = []

    # Consistency: study_log
    sl = metrics.get("study_log", {})
    if sl.get("rows") != expected_study["rows"]:
        failures.append(
            f"study_log.rows {sl.get('rows')} != {expected_study['rows']}"
        )
    if sl.get("total_minutes") != expected_study["total_minutes"]:
        failures.append(
            f"study_log.total_minutes {sl.get('total_minutes')} != "
            f"{expected_study['total_minutes']}"
        )
    if sl.get("distinct_days") != expected_study["distinct_days"]:
        failures.append(
            f"study_log.distinct_days {sl.get('distinct_days')} != "
            f"{expected_study['distinct_days']}"
        )
    sd = sl.get("streak_days")
    if not isinstance(sd, int) or sd <= 0:
        failures.append(f"study_log.streak_days {sd} not a positive int")
    elif sd > expected_study["distinct_days"]:
        failures.append(
            f"study_log.streak_days {sd} > distinct_days "
            f"{expected_study['distinct_days']}"
        )
    elif sd != expected_study["streak_days"]:
        failures.append(
            f"study_log.streak_days {sd} != brute-force "
            f"{expected_study['streak_days']}"
        )
    if sl.get("by_activity") != expected_study["by_activity"]:
        failures.append("study_log.by_activity mismatch")

    # Consistency: dictation
    dc = metrics.get("dictation", {})
    for key in (
        "file_count",
        "sum_active_time_hours",
        "sum_lesson_completions",
        "max_active_days",
        "max_last_7d_hours",
        "max_last_30d_hours",
    ):
        if dc.get(key) != expected_dict[key]:
            failures.append(f"dictation.{key} {dc.get(key)} != {expected_dict[key]}")
    if dc.get("recent_lessons") != expected_dict["recent_lessons"]:
        failures.append("dictation.recent_lessons mismatch")

    # Structural anchors
    if sl.get("rows", 0) < 100:
        failures.append(f"study_log.rows {sl.get('rows')} < 100")
    if sl.get("total_minutes", 0) <= 0:
        failures.append("study_log.total_minutes not > 0")
    if not sl.get("by_activity"):
        failures.append("study_log.by_activity is empty")
    if dc.get("file_count") != 30:
        failures.append(f"dictation.file_count {dc.get('file_count')} != 30")
    if dc.get("sum_active_time_hours", 0) <= 0:
        failures.append("dictation.sum_active_time_hours not > 0")

    if failures:
        print("FAIL")
        for f in failures:
            print("  - " + f)
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
