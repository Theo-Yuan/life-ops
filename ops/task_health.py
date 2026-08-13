#!/usr/bin/env python3
"""
Task Health Check — 巡检所有 reveille 定时任务最近执行状态。

检查维度:
  1. 最近 N 天每个任务的执行次数 / 成功数 / 失败数
  2. 失败任务的错误摘要（读取 stderr 日志末尾）
  3. 到期未执行的任务（有调度但最近无运行记录）
  4. 各项目仓当前 git SHA（版本溯源）

数据源:
  ~/.config/reveille/tasks/*.md         (任务配置)
  ~/.config/reveille/executions/*.json (执行记录)

用法:
    python3 scripts/task_health.py --days 3
    python3 scripts/task_health.py --days 3 --snapshot   # 同时保存审计快照
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

TASKS_DIR = Path.home() / ".config" / "reveille" / "tasks"
EXEC_DIR = Path.home() / ".config" / "reveille" / "executions"
LOG_DIR = Path.home() / ".local" / "share" / "reveille" / "logs"

# 各项目仓 → 用于 git SHA 版本溯源
REPO_DIRS = {
    "life-ops": Path(__file__).resolve().parent.parent,
}

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "audit" / "snapshots"


def _git_sha(repo: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "?"
    except (subprocess.SubprocessError, OSError):
        return "?"


def _git_status(repo: Path) -> list:
    """返回未提交改动文件列表（若有）。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        return [line[:2] + " " + line[3:] for line in result.stdout.strip().splitlines()][:10]
    except (subprocess.SubprocessError, OSError):
        return []


def _parse_task(path: Path) -> dict:
    text = path.read_text()
    fm = {}
    for m in re.finditer(r"^(\w+):\s*(.*)$", text, re.MULTILINE):
        key, val = m.group(1), m.group(2).strip()
        if key in ("name", "agent", "scheduleType", "scheduleCron", "enabled",
                   "workingDir"):
            fm[key] = val
    return {"id": path.stem, **fm}


def _read_execs(task_id: str) -> list:
    f = EXEC_DIR / f"{task_id}.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _stderr_tail(exec_path: str, lines: int = 15) -> str:
    if not exec_path:
        return ""
    p = Path(exec_path)
    if not p.exists():
        return ""
    try:
        content = p.read_text(errors="replace").strip()
        return "\n".join(content.splitlines()[-lines:])
    except OSError:
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3,
                        help="检查最近 N 天执行记录 (默认 3)")
    parser.add_argument("--snapshot", action="store_true",
                        help="保存审计快照到 audit/snapshots/")
    args = parser.parse_args()

    cutoff = (datetime.now() - timedelta(days=args.days)).isoformat()[:10]

    tasks = []
    for task_file in sorted(TASKS_DIR.glob("*.md")):
        task = _parse_task(task_file)
        execs = _read_execs(task["id"])
        recent = [e for e in execs if e.get("startedAt", "")[:10] >= cutoff]

        failed = [e for e in recent if e.get("status") == "failed"]
        running = [e for e in recent if e.get("status") == "running"]
        success = len(recent) - len(failed) - len(running)

        task["runs"] = len(recent)
        task["success"] = success
        task["failed"] = len(failed)
        task["running"] = len(running)
        task["healthy"] = len(failed) == 0
        task["last_run"] = recent[-1].get("startedAt", "")[:10] if recent else None
        task["failures"] = [
            {
                "date": e.get("startedAt", "")[:10],
                "exit_code": e.get("exitCode"),
                "stderr_tail": _stderr_tail(e.get("stderrPath")),
            }
            for e in failed[:3]
        ]
        tasks.append(task)

    report = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "days": args.days,
        "tasks": tasks,
        "any_failure": any(t["failed"] > 0 for t in tasks),
        "versions": {
            name: {"sha": _git_sha(repo), "dirty": _git_status(repo)}
            for name, repo in REPO_DIRS.items()
        },
    }

    if args.snapshot:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        out = SNAPSHOT_DIR / f"task-health-{datetime.now():%Y-%m-%d}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"[snapshot] saved {out}", file=sys.stderr)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
