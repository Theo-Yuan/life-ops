# English Dashboard Study Streak — Proposal

## Acceptance criteria

Extend the english learning dashboard so its metrics include a study streak:

1. `metrics.py` adds `study_log.streak_days`: the length (in calendar days) of the
   longest run of consecutive distinct study days ending at the latest study date
   (read from the `study_log` table's `date` column).
2. `test_metrics.py` asserts `study_log.streak_days` is a positive integer, is <=
   `distinct_days`, and matches a brute-force computation over the study dates.
3. `dashboard.html` renders the streak as a stat card (no chart change).

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
