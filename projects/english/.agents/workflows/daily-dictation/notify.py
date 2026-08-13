import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SNAPSHOTS_DIR = PROJECT_ROOT / "tmp" / "daily-dictation"
CHANNEL_ID = "1466302720515379307"


def get_bot_token() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "discord-bot-token",
         "-a", "opencode", "-w"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        print(f"Error reading bot token from Keychain: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def send_discord_message(token: str, content: str):
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    body = json.dumps({"content": content}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bot {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "DailyDictation-Bot/1.0")
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            print(f"Discord API error: {resp.status}", file=sys.stderr)
            sys.exit(1)


def build_report(date_str: str) -> str:
    snap_path = SNAPSHOTS_DIR / f"{date_str}.json"
    if not snap_path.exists():
        print(f"Snapshot not found: {snap_path}", file=sys.stderr)
        sys.exit(1)

    with open(snap_path) as f:
        snap = json.load(f)

    stats = snap["stats"]
    completions = stats.get("lesson_completions", 0)
    time_hours = stats.get("active_time_hours", 0)
    active_days = stats.get("active_days", 0)
    last_7d = stats.get("last_7d_hours", 0)
    last_30d = stats.get("last_30d_hours", 0)

    api_minutes = 0
    for entry in snap.get("daily_activity", []):
        if entry.get("date") == date_str:
            api_minutes = entry.get("minutes", 0)
            break

    recent = stats.get("recent_lessons", [])[:3]
    recent_names = " · ".join(l["title"] for l in recent)

    weekday_cn = ["一", "二", "三", "四", "五", "六", "日"]
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = weekday_cn[dt.weekday()]

    lines = [
        f"📖 每日听写打卡 {date_str} 周{weekday}",
        f"▸ 今日 {api_minutes}min · 总完成 {completions} 课 · 累计 {time_hours}h（{active_days} 天）",
        f"▸ 近 7 天 {last_7d}h · 近 30 天 {last_30d}h",
    ]
    if recent_names:
        lines.append(f"▸ 最近练习: {recent_names}")

    return "\n".join(lines)


def _merged_daily_activity() -> dict:
    """合并所有 snapshot 的 daily_activity，保留每个日期的最新分钟数。"""
    merged: dict[str, int] = {}
    for snap_path in sorted(SNAPSHOTS_DIR.glob("*.json")):
        try:
            with open(snap_path) as f:
                snap = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        for entry in snap.get("daily_activity", []):
            d = entry.get("date")
            if d:
                minutes = entry.get("minutes", 0)
                merged[d] = max(merged.get(d, 0), minutes)
    return merged


def compute_trends(date_str: str) -> dict:
    """从可用 snapshot 计算近 7/30 天听写分钟数与连续打卡天数。"""
    merged = _merged_daily_activity()
    dt = datetime.strptime(date_str, "%Y-%m-%d")

    def window(days: int) -> list[dict]:
        out = []
        for i in range(days - 1, -1, -1):
            d = (dt - timedelta(days=i)).strftime("%Y-%m-%d")
            out.append({"date": d, "minutes": merged.get(d, 0)})
        return out

    last_7d = window(7)
    last_30d = window(30)

    streak = 0
    cur = dt
    while merged.get(cur.strftime("%Y-%m-%d"), 0) > 0:
        streak += 1
        cur -= timedelta(days=1)

    return {
        "last_7d_minutes": sum(e["minutes"] for e in last_7d),
        "last_30d_minutes": sum(e["minutes"] for e in last_30d),
        "last_7d": last_7d,
        "last_30d": last_30d,
        "streak_days": streak,
    }


def collect_data(date_str: str) -> dict:
    """Agent 决策数据：当日听写 + 趋势 + profile，供 agent 生成个性化打卡消息。"""
    snap_path = SNAPSHOTS_DIR / f"{date_str}.json"
    if not snap_path.exists():
        print(f"Snapshot not found: {snap_path}", file=sys.stderr)
        sys.exit(1)

    with open(snap_path) as f:
        snap = json.load(f)

    stats = snap["stats"]
    api_minutes = 0
    for entry in snap.get("daily_activity", []):
        if entry.get("date") == date_str:
            api_minutes = entry.get("minutes", 0)
            break

    profile_text = ""
    profile_path = PROJECT_ROOT / ".agents" / "profile.md"
    if profile_path.exists():
        profile_text = profile_path.read_text()

    return {
        "date": date_str,
        "stats": {
            "api_minutes": api_minutes,
            "lesson_completions": stats.get("lesson_completions", 0),
            "active_time_hours": stats.get("active_time_hours", 0),
            "active_days": stats.get("active_days", 0),
            "last_7d_hours": stats.get("last_7d_hours", 0),
            "last_30d_hours": stats.get("last_30d_hours", 0),
        },
        "recent_lessons": stats.get("recent_lessons", [])[:3],
        "trends": compute_trends(date_str),
        "profile": profile_text,
        "note": "数据由脚本提供，请勿编造；参考 .agents/profile.md 中的 IELTS 6.5 目标与弱项（听力、词组搭配）做个性化点评。",
    }


def main():
    args = sys.argv[1:]
    if "--data" in args:
        idx = args.index("--data")
        date_str = args[idx + 1] if idx + 1 < len(args) else datetime.now().strftime("%Y-%m-%d")
        print(json.dumps(collect_data(date_str), ensure_ascii=False))
        return

    date_str = args[0] if args else datetime.now().strftime("%Y-%m-%d")
    token = get_bot_token()
    report = build_report(date_str)
    send_discord_message(token, report)
    print(f"Sent to Discord: {len(report)} chars")


if __name__ == "__main__":
    main()
