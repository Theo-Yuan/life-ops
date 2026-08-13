"""
snapshot.py — Take a snapshot of DailyDictation profile + API data.

Usage:
    python snapshot.py --user-id 278853
    python snapshot.py --user-id 278853 --date 2026-07-27

Env:
    DD_USER_ID — fallback if --user-id not given
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SNAPSHOTS_DIR = PROJECT_ROOT / "tmp" / "daily-dictation"
PROFILE_URL = "https://dailydictation.com/profile/{user_id}"
API_URL = "https://dailydictation.com/api/user-dates/{user_id}?from={date_from}&to={date_to}"


def fetch_text(url: str, attempts: int = 3) -> str:
    last_err = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DailyDictation-Tracker/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(2 * (i + 1))
    raise Exception(f"fetch_text failed after {attempts} attempts: {last_err}")


def parse_profile(html: str) -> dict:
    stats = {}

    patterns = {
        "lesson_completions": r"Lesson completions:\s*</span>\s*<strong>(\d+)</strong>",
        "translations": r"Translations contributed:\s*</span>\s*<strong>(\d+)</strong>",
        "active_days": r"Active days:\s*</span>\s*<strong>([\d.]+)\s*days?</strong>",
        "active_time_hours": r"Active time:\s*</span>\s*<strong>([\d.]+)\s*hours?</strong>",
        "last_7d_hours": r"Last 7 days:\s*</span>\s*<strong>([\d.]+)\s*hours?</strong>",
        "last_30d_hours": r"Last 30 days:\s*</span>\s*<strong>([\d.]+)\s*hours?</strong>",
        "last_active": r"Last active:\s*</span>\s*<strong>([^<]+)</strong>",
        "join_date": r"Join date:\s*</span>\s*<strong>([^<]+)</strong>",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, html)
        if m:
            val = m.group(1).strip()
            try:
                stats[key] = float(val) if "." in val else int(val)
            except ValueError:
                stats[key] = val

    lesson_blocks = re.findall(
        r'<li class="list-group-item">(.*?)</li>', html, re.DOTALL
    )
    recent_lessons = []
    for block in lesson_blocks:
        link_m = re.search(r'<a href="/exercises/([^"]+)">([^<]+)</a>', block)
        star_m = re.search(r'title="Completions:\s*(\d+)"', block)
        if link_m:
            path = link_m.group(1).strip()
            title = link_m.group(2).strip()
            category = path.split("/")[0]
            recent_lessons.append({
                "title": title,
                "category": category,
                "path": path,
                "completions": int(star_m.group(1)) if star_m else 0,
            })

    stats["recent_lessons"] = recent_lessons
    return stats


def fetch_daily_activity(user_id: int, days_back: int = 90) -> list[dict]:
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = API_URL.format(user_id=user_id, date_from=date_from, date_to=date_to)
    return json.loads(fetch_text(url))


def main():
    parser = argparse.ArgumentParser(description="DailyDictation snapshot")
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--date", default=None)
    args = parser.parse_args()

    user_id = args.user_id or int(os.environ.get("DD_USER_ID", 0))
    if not user_id:
        print("Error: --user-id required or set DD_USER_ID env var", file=sys.stderr)
        sys.exit(1)

    snap_date = args.date or datetime.now().strftime("%Y-%m-%d")

    profile_html = fetch_text(PROFILE_URL.format(user_id=user_id))
    stats = parse_profile(profile_html)
    daily_activity = fetch_daily_activity(user_id)

    snapshot = {
        "date": snap_date,
        "user_id": user_id,
        "fetched_at": datetime.now().isoformat(),
        "stats": stats,
        "daily_activity": daily_activity,
    }

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SNAPSHOTS_DIR / f"{snap_date}.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"Snapshot saved: {out_path}")
    print(f"  Lesson completions: {stats.get('lesson_completions', '?')}")
    print(f"  Active time: {stats.get('active_time_hours', '?')}h")
    print(f"  Recent lessons: {len(stats.get('recent_lessons', []))}")


if __name__ == "__main__":
    main()
