#!/usr/bin/env python3
"""
Daily Life Ops Report — 聚合各学习项目数据 + 定时任务执行状态。

数据源:
  projects/workout   .agents/db/train.db        (训练记录)
  projects/english .agents/db/english_learning.db + tmp/daily-dictation/ (学习记录+听写)
  reveille       ~/.config/reveille/executions/*.json (定时任务执行状态)

注：finance / article 摘要已暂停（见 README）；gmail 摘要已恢复。

用法:
    python3 scripts/aggregate.py            # 输出今日报告 JSON (stdout)
    python3 scripts/aggregate.py --days 7   # 最近 7 天
"""
import argparse
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

PROJECTS = Path(__file__).resolve().parent.parent / "projects"
REVEILLE_DIR = Path.home() / ".config" / "reveille" / "executions"

TASK_NAMES = {
    "7vV2yQE3": "训练摘要 workout-summary",
    "CF8hidn2": "训练预告 workout-preview",
    "vbObtAvS": "听写打卡 daily-dictation",
    "HSClwEzd": "邮件摘要 gmail-summary",
    "BB9Lv5p2": "聚合日报 life-ops-report",
    "sEzf-0i3": "任务巡检 task-health-check",
}


def _db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _workout(today: str):
    db = PROJECTS / "workout" / ".agents" / "db" / "train.db"
    if not db.exists():
        return {"error": "train.db not found"}
    conn = _db(db)
    rows = conn.execute(
        "SELECT datestr, title, duration_s FROM trains "
        "WHERE duration_s IS NOT NULL AND duration_s > 0 "
        "ORDER BY datestr DESC LIMIT 8"
    ).fetchall()
    conn.close()
    trains = [
        {"date": r["datestr"], "title": r["title"],
         "duration_min": (r["duration_s"] or 0) // 60}
        for r in rows
    ]
    today_train = next((t for t in trains if t["date"] == today), None)
    return {"today": today_train, "recent": trains}


def _english(today: str):
    db = PROJECTS / "english" / ".agents" / "db" / "english_learning.db"
    snap_dir = PROJECTS / "english" / "tmp" / "daily-dictation"
    if not db.exists():
        return {"error": "english_learning.db not found"}
    conn = _db(db)

    # 手动学习记录（非 daily-dictation 自动记录，duration_min 有真实值）
    manual_rows = conn.execute(
        "SELECT date, SUM(duration_min) AS minutes, COUNT(*) AS entries "
        "FROM study_log WHERE notes NOT LIKE '%daily-dictation-auto%' "
        "GROUP BY date"
    ).fetchall()
    manual = {r["date"]: {"minutes": r["minutes"] or 0, "entries": r["entries"]}
              for r in manual_rows}

    # 听写分钟数：读 snapshot 的 daily_activity（权威数据）
    # record.py 写 study_log 时 duration_min 固定为 0，真实时长在 snapshot 里
    dictation_min = {}
    if snap_dir.exists():
        for snap_file in sorted(snap_dir.glob("*.json")):
            try:
                snap = json.loads(snap_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            for entry in snap.get("daily_activity", []):
                entry_date = entry.get("date")
                minutes = entry.get("minutes") or 0
                if entry_date:
                    dictation_min[entry_date] = max(dictation_min.get(entry_date, 0), minutes)

    def day_stats(d):
        dm = dictation_min.get(d, 0)
        mn = manual.get(d, {}).get("minutes", 0)
        me = manual.get(d, {}).get("entries", 0)
        total = dm + mn
        if dm == 0 and mn == 0:
            return None
        return {"date": d, "minutes": total,
                "dictation_min": dm, "manual_min": mn, "entries": me}

    week_rows = conn.execute(
        "SELECT DISTINCT date FROM study_log WHERE date >= ?",
        ((date.today() - timedelta(days=7)).isoformat(),),
    ).fetchall()
    conn.close()
    week_dates = {r["date"] for r in week_rows} | set(dictation_min) | set(manual)
    week = []
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    for d in sorted(week_dates):
        if d >= cutoff:
            stats = day_stats(d)
            if stats:
                week.append(stats)
    return {
        "today": day_stats(today),
        "week": week,
        "dictation_min": dictation_min,
    }


def _gmail(today: str):
    summary = PROJECTS / "gmail" / "tmp" / "emails.json"
    if not summary.exists():
        return {"error": "emails.json not found"}
    try:
        data = json.loads(summary.read_text())
    except (json.JSONDecodeError, OSError):
        return {"error": "emails.json parse error"}
    return {
        "date": data.get("date", today),
        "total": data["stats"]["total"],
        "unread": data["stats"]["unread"],
        "categories": data.get("categories", []),
        "important": [{"from": e["sender"], "subject": e["subject"]} for e in data.get("important", [])[:10]],
        "topSenders": data.get("topSenders", []),
    }


def _tasks(days: int):
    """读取 reveille 执行记录，汇总最近 N 天每个任务的状态。"""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    results = {tid: [] for tid in TASK_NAMES}
    for task_id in TASK_NAMES:
        f = REVEILLE_DIR / f"{task_id}.json"
        if not f.exists():
            continue
        try:
            execs = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for e in execs:
            started = e.get("startedAt", "")[:10]
            if started >= cutoff:
                results[task_id].append({
                    "date": started,
                    "status": e.get("status"),
                    "exit_code": e.get("exitCode"),
                    "duration_s": None,
                })
    return [{"task": TASK_NAMES[tid], "runs": runs} for tid, runs in results.items()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1,
                        help="任务执行统计天数 (默认 1)")
    args = parser.parse_args()
    today = date.today().isoformat()

    report = {
        "date": today,
        "workout": _workout(today),
        "english_learning": _english(today),
        "gmail": _gmail(today),
        "tasks": _tasks(args.days),
        "note": "数据以脚本读取为准，不要编造。结合各项目目标给个性化点评。",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
