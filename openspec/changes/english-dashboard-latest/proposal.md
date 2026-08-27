# English Dashboard Latest Date — Proposal

## Acceptance criteria

Add `study_log.latest_date` to the dashboard metrics: the latest distinct study date
(from the `study_log` table, ISO `YYYY-MM-DD`). `test_metrics.py` asserts it equals the
max date in the `study_log` table, and `dashboard.html` renders a "Last study" card.

## Acceptance commands

- python3 projects/english/dashboard/metrics.py --data /Users/theoyuan/projects/personal/life-ops/projects/english
- python3 projects/english/dashboard/test_metrics.py --data /Users/theoyuan/projects/personal/life-ops/projects/english

## Acceptance test paths

- projects/english/dashboard/test_metrics.py

## Gate surface

- projects/english/dashboard/*
- the machine-local english data (read-only)

## Declared dependencies

- Python 3 standard library

## Deadline

2026-09-30T23:59:59Z

## Out of scope

- mock_test / vocabulary / daily_goal population or rendering
- theming, auth, deployment
