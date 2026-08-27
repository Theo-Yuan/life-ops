# English Learning Dashboard — Proposal

## Acceptance criteria

A static web dashboard at `projects/english/dashboard/` that surfaces the real
life-ops english learning data:

1. A metrics generator reads the machine-local data and emits `metrics.json`:
   - `study_log`: total sessions, total minutes, distinct days, and per-activity
     session count + minutes (read from the `study_log` table of the SQLite DB).
   - `dictation`: file count, sum of `active_time_hours`, sum of `lesson_completions`,
     max `active_days`, max `last_7d_hours`, max `last_30d_hours` (aggregated across
     every `tmp/daily-dictation/*.json`).
   - `recent_lessons`: the titles from the latest dictation file.
2. `dashboard.html` renders the metrics with Chart.js (from the CDN): a study-activity
   bar (minutes per day) + a per-activity breakdown, dictation stat cards, and the
   recent-lessons list. It fetches `metrics.json` (no backend).
3. `test_metrics.py` recomputes the same derived values from the data and asserts
   `metrics.json` matches (consistency) and that the structural anchors hold
   (`study_log.rows >= 100`, `study_log.total_minutes > 0`, non-empty activities,
   `dictation.file_count == 30`).

## Acceptance commands

- python3 projects/english/dashboard/metrics.py --data /Users/theoyuan/projects/personal/life-ops/projects/english
- python3 projects/english/dashboard/test_metrics.py --data /Users/theoyuan/projects/personal/life-ops/projects/english

## Acceptance test paths

- `projects/english/dashboard/test_metrics.py`

## Gate surface

- `projects/english/dashboard/*`
- the machine-local english data (`projects/english/.agents/db/english_learning.db` and
  `projects/english/tmp/daily-dictation/*.json`) — gitignored, read-only

## Declared dependencies

- Python 3 standard library (`sqlite3`, `json`, `glob`, `argparse`)
- Chart.js via CDN (no bundled JS; no npm build)

## Deadline

2026-09-30T23:59:59Z

## Out of scope

- Populating or rendering `mock_test`, `vocabulary`, or `daily_goal` (tables exist but
  are empty-ready here)
- Any backend server beyond `python3 -m http.server` for local preview
- Authentication, deployment, or theming beyond default Chart.js styling
