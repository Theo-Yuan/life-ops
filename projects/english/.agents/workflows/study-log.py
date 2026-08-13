"""
Study Log — Record daily study sessions.

Usage:
    python study-log.py log --activity listening --duration 30 --detail "BBC 6 Minute English"
    python study-log.py today
    python study-log.py week
    python study-log.py stats
"""
import sqlite3
import os
import argparse
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "english_learning.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def log_study(activity, duration, detail, notes=""):
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO study_log (date, duration_min, activity, detail, notes) VALUES (?, ?, ?, ?, ?)",
        (today, duration, activity, detail, notes),
    )
    conn.commit()
    conn.close()
    print(f"✓ Logged: {duration}min {activity} — {detail}")


def show_today():
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT activity, duration_min, detail FROM study_log WHERE date = ? ORDER BY id",
        (today,),
    ).fetchall()
    conn.close()
    if not rows:
        print("No study recorded today.")
        return
    total = sum(row[1] for row in rows)
    print(f"📚 Today ({today}): {total}min total")
    for activity, duration, detail in rows:
        print(f"  • {activity}: {duration}min — {detail}")


def show_week():
    conn = get_conn()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT date, SUM(duration_min) FROM study_log WHERE date >= ? GROUP BY date ORDER BY date",
        (week_ago,),
    ).fetchall()
    conn.close()
    print("📊 Past 7 days:")
    total = 0
    for date, mins in rows:
        print(f"  {date}: {mins}min")
        total += mins
    print(f"  ─────────\n  Total: {total}min ({total/7:.0f}min/day)")


def show_stats():
    conn = get_conn()
    rows = conn.execute(
        "SELECT activity, SUM(duration_min), COUNT(*) FROM study_log GROUP BY activity ORDER BY SUM(duration_min) DESC"
    ).fetchall()
    conn.close()
    print("📈 Study Stats (All Time):")
    for activity, total_min, count in rows:
        print(f"  • {activity}: {total_min}min ({count} sessions)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="English Study Log")
    subparsers = parser.add_subparsers(dest="command")

    log_parser = subparsers.add_parser("log", help="Log study session")
    log_parser.add_argument("--activity", required=True)
    log_parser.add_argument("--duration", type=int, required=True)
    log_parser.add_argument("--detail", default="")
    log_parser.add_argument("--notes", default="")

    subparsers.add_parser("today", help="Show today's study")
    subparsers.add_parser("week", help="Show past week")
    subparsers.add_parser("stats", help="Show all-time stats")

    args = parser.parse_args()

    if args.command == "log":
        log_study(args.activity, args.duration, args.detail, args.notes)
    elif args.command == "today":
        show_today()
    elif args.command == "week":
        show_week()
    elif args.command == "stats":
        show_stats()
    else:
        parser.print_help()
