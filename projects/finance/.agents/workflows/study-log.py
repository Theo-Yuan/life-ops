"""
学习记录 — 记录每日理财学习内容。

用法：
    python study-log.py log --activity 概念学习 --duration 30 --detail "复利公式与 72 法则"
    python study-log.py today
    python study-log.py week
    python study-log.py stats

活动分类建议：概念学习 / 案例分析 / 实操演练 / 复盘检验
"""
import sqlite3
import os
import argparse
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "finance_plan.db")


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
    print(f"✓ 已记录：{duration} 分钟 {activity} — {detail}")


def show_today():
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT activity, duration_min, detail FROM study_log WHERE date = ? ORDER BY id",
        (today,),
    ).fetchall()
    conn.close()
    if not rows:
        print("今日无学习记录。")
        return
    total = sum(row[1] for row in rows)
    print(f"📚 今日（{today}）：共 {total} 分钟")
    for activity, duration, detail in rows:
        print(f"  • {activity}：{duration} 分钟 — {detail}")


def show_week():
    conn = get_conn()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT date, SUM(duration_min) FROM study_log WHERE date >= ? GROUP BY date ORDER BY date",
        (week_ago,),
    ).fetchall()
    conn.close()
    print("📊 近 7 天：")
    total = 0
    for date, mins in rows:
        print(f"  {date}：{mins} 分钟")
        total += mins
    print(f"  ─────────\n  总计：{total} 分钟（日均 {total/7:.0f} 分钟）")


def show_stats():
    conn = get_conn()
    rows = conn.execute(
        "SELECT activity, SUM(duration_min), COUNT(*) FROM study_log GROUP BY activity ORDER BY SUM(duration_min) DESC"
    ).fetchall()
    conn.close()
    print("📈 累计统计：")
    for activity, total_min, count in rows:
        print(f"  • {activity}：共 {total_min} 分钟（{count} 次）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="理财学习记录")
    subparsers = parser.add_subparsers(dest="command")

    log_parser = subparsers.add_parser("log", help="记录一次学习")
    log_parser.add_argument("--activity", required=True)
    log_parser.add_argument("--duration", type=int, required=True)
    log_parser.add_argument("--detail", default="")
    log_parser.add_argument("--notes", default="")

    subparsers.add_parser("today", help="查看今日学习")
    subparsers.add_parser("week", help="查看近一周")
    subparsers.add_parser("stats", help="查看累计统计")

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
