# Audit System Changelog

## 2026-08-04
- Added `task_health.py` with `--snapshot` (saves daily health snapshot incl. per-repo git SHA)
- Added `audit.py` query tool (list / trend / show / incidents)
- Added `sched/task_health.sh` agent-driven investigation + fix + incident record + git commit
- Added `audit/` structure (snapshots + incidents + README)
