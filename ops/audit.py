#!/usr/bin/env python3
"""
Audit Tool — 查询定时任务巡检的审计快照历史。

功能:
  - 列出所有快照日期
  - 汇总最近 N 天各任务健康趋势
  - 查询某天快照详情（含 git 版本）
  - 列出所有故障 incident 记录

数据源:
  audit/snapshots/task-health-YYYY-MM-DD.json  (巡检快照)
  audit/incidents/*.md                         (故障记录)

用法:
    python3 scripts/audit.py list
    python3 scripts/audit.py trend --days 14
    python3 scripts/audit.py show 2026-08-04
    python3 scripts/audit.py incidents
"""
import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent.parent / "audit"
SNAPSHOT_DIR = AUDIT_DIR / "snapshots"
INCIDENT_DIR = AUDIT_DIR / "incidents"


def _snapshots() -> list:
    return sorted(SNAPSHOT_DIR.glob("task-health-*.json"))


def cmd_list(_args):
    snaps = _snapshots()
    if not snaps:
        print("(无快照)")
        return
    print(f"{'日期':12} 状态")
    for p in snaps:
        try:
            d = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        flag = "🔴 有失败" if d["any_failure"] else "✅ 健康"
        print(f"{p.stem[-10:]:12} {flag}")


def cmd_trend(args):
    snaps = _snapshots()[-args.days:] if args.days else _snapshots()
    all_names = set()
    by_day = []
    for p in snaps:
        try:
            d = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        day = {t["name"]: t["failed"] for t in d["tasks"]}
        all_names.update(day.keys())
        by_day.append((p.stem[-10:], day))
    if not all_names:
        print("(无快照)")
        return
    names = sorted(all_names)
    print(f"{'日期':12} " + "  ".join(f"{n[:10]:>12}" for n in names))
    for date, day in by_day:
        cells = []
        for n in names:
            f = day.get(n, "-")
            cells.append(f"{f:>12}")
        print(f"{date:12} " + "  ".join(cells))
    print("\n数值 = 当天失败次数")


def cmd_show(args):
    path = SNAPSHOT_DIR / f"task-health-{args.date}.json"
    if not path.exists():
        print(f"快照不存在: {path}")
        return
    d = json.loads(path.read_text())
    print(f"=== {args.date} 巡检快照 ===")
    for t in d["tasks"]:
        status = "✅" if t["healthy"] else "🔴"
        print(f"  {status} {t['name']}: {t['success']}/{t['runs']} 成功"
              + (f" ({t['failed']} 失败)" if t["failed"] else ""))
        for f in t.get("failures", []):
            print(f"      ✗ {f['date']} exit={f['exit_code']}: "
                  f"{(f.get('stderr_tail') or '')[:100]}")
    print("  版本:")
    for name, v in d.get("versions", {}).items():
        dirty = f" (+{len(v['dirty'])} 未提交)" if v.get("dirty") else ""
        print(f"    {name}: {v['sha']}{dirty}")


def cmd_incidents(_args):
    files = sorted(INCIDENT_DIR.glob("*.md")) if INCIDENT_DIR.exists() else []
    if not files:
        print("(无故障记录)")
        return
    for f in files:
        text = f.read_text()
        title = text.splitlines()[0] if text.splitlines() else f.name
        print(f"• {f.stem}")
        print(f"    {title}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list", help="列出所有快照")
    p_list.set_defaults(fn=cmd_list)

    p_trend = sub.add_parser("trend", help="健康趋势")
    p_trend.add_argument("--days", type=int, default=None)
    p_trend.set_defaults(fn=cmd_trend)

    p_show = sub.add_parser("show", help="查看某天快照")
    p_show.add_argument("date", help="YYYY-MM-DD")
    p_show.set_defaults(fn=cmd_show)

    p_inc = sub.add_parser("incidents", help="列出故障记录")
    p_inc.set_defaults(fn=cmd_incidents)

    args = parser.parse_args()
    if not hasattr(args, "fn"):
        parser.print_help()
        return
    args.fn(args)


if __name__ == "__main__":
    main()
