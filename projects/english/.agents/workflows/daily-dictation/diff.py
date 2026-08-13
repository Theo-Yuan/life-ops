"""
diff.py — Compare two DailyDictation snapshots, detect changes.

Usage:
    python diff.py snapshots/2026-07-26.json snapshots/2026-07-27.json
    python diff.py --auto  # auto-find yesterday vs today
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SNAPSHOTS_DIR = PROJECT_ROOT / "tmp" / "daily-dictation"


def load_snapshot(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def find_snapshots(date_str: str) -> Path | None:
    """Find snapshot file for a given date."""
    path = SNAPSHOTS_DIR / f"{date_str}.json"
    return path if path.exists() else None


def diff_snapshots(yesterday: dict, today: dict) -> dict:
    """Compare two snapshots and return detected changes."""
    ys = yesterday.get("stats", {})
    ts = today.get("stats", {})

    # Today's daily activity (minutes for today)
    today_date = today["date"]
    today_minutes = 0
    for entry in today.get("daily_activity", []):
        if entry.get("date") == today_date:
            today_minutes = entry.get("minutes", 0)
            break

    # Lesson completion delta
    prev_completions = ys.get("lesson_completions", 0)
    curr_completions = ts.get("lesson_completions", 0)
    new_completions = max(0, curr_completions - prev_completions)

    # Active time delta
    prev_time = ys.get("active_time_hours", 0)
    curr_time = ts.get("active_time_hours", 0)
    time_delta_hours = round(curr_time - prev_time, 1)
    time_delta_minutes = round(time_delta_hours * 60)

    # New lessons: in today's recent_lessons but not in yesterday's
    prev_lesson_paths = {l["path"] for l in ys.get("recent_lessons", [])}
    curr_lessons = ts.get("recent_lessons", [])

    # Find new lessons (new paths or increased completions)
    new_lessons = []
    increased_completion_lessons = []
    for lesson in curr_lessons:
        path = lesson["path"]
        if path not in prev_lesson_paths:
            new_lessons.append(lesson)
        else:
            # Check if completions increased
            prev_lesson = next(
                (l for l in ys.get("recent_lessons", []) if l["path"] == path),
                None
            )
            if prev_lesson and lesson["completions"] > prev_lesson["completions"]:
                increased_completion_lessons.append({
                    **lesson,
                    "prev_completions": prev_lesson["completions"],
                })

    # Active days delta
    active_days_delta = ts.get("active_days", 0) - ys.get("active_days", 0)

    # Last 7d delta
    last7d_delta = round(
        ts.get("last_7d_hours", 0) - ys.get("last_7d_hours", 0), 1
    )

    return {
        "date": today_date,
        "today_minutes_api": today_minutes,
        "new_lesson_completions": new_completions,
        "time_spent_minutes": time_delta_minutes,
        "time_spent_hours": time_delta_hours,
        "new_recent_lessons": new_lessons,
        "increased_completion_lessons": increased_completion_lessons,
        "active_days_delta": active_days_delta,
        "last_7d_hours_delta": last7d_delta,
        "prev_stats": {
            "lesson_completions": prev_completions,
            "active_time_hours": prev_time,
            "active_days": ys.get("active_days", 0),
        },
        "curr_stats": {
            "lesson_completions": curr_completions,
            "active_time_hours": curr_time,
            "active_days": ts.get("active_days", 0),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Diff DailyDictation snapshots")
    parser.add_argument("yesterday", nargs="?", help="Path to yesterday's snapshot")
    parser.add_argument("today", nargs="?", help="Path to today's snapshot")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-find yesterday vs today snapshots")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON (for piping to record.py)")
    args = parser.parse_args()

    if args.auto:
        today_str = datetime.now().strftime("%Y-%m-%d")
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_path = find_snapshots(yesterday_str)
        today_path = find_snapshots(today_str)
    elif args.yesterday and args.today:
        yesterday_path = Path(args.yesterday)
        today_path = Path(args.today)
    else:
        print("Usage: diff.py <yesterday.json> <today.json>  OR  diff.py --auto",
              file=sys.stderr)
        sys.exit(1)

    if not yesterday_path or not yesterday_path.exists():
        print(f"Yesterday snapshot not found: {yesterday_path}", file=sys.stderr)
        sys.exit(1)
    if not today_path or not today_path.exists():
        print(f"Today snapshot not found: {today_path}", file=sys.stderr)
        sys.exit(1)

    yesterday = load_snapshot(yesterday_path)
    today = load_snapshot(today_path)
    diff = diff_snapshots(yesterday, today)

    if args.json:
        print(json.dumps(diff, indent=2, ensure_ascii=False))
    else:
        print(f"=== DailyDictation Diff: {diff['date']} ===")
        print(f"  Time spent: {diff['time_spent_minutes']} min "
              f"(API: {diff['today_minutes_api']} min)")
        print(f"  New completions: {diff['new_lesson_completions']}")
        print(f"  Active days: +{diff['active_days_delta']}")
        if diff["new_recent_lessons"]:
            print(f"  New lessons:")
            for l in diff["new_recent_lessons"]:
                print(f"    - [{l['category']}] {l['title']}")
        if diff["increased_completion_lessons"]:
            print(f"  Re-done lessons:")
            for l in diff["increased_completion_lessons"]:
                print(f"    - [{l['category']}] {l['title']} "
                      f"({l['prev_completions']}→{l['completions']})")
        if diff["new_lesson_completions"] == 0 and diff["time_spent_minutes"] == 0:
            print("  ⚠️  No activity detected today.")
        else:
            print("  ✅ Activity detected!")


if __name__ == "__main__":
    main()
