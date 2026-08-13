.PHONY: report health audit study-log check

# 聚合日报 → Discord（agent 主导）
report:
	bash ops/report.sh

# 定时任务巡检（最近 N 天，默认 3）
health:
	bash ops/task_health.sh $(or $(DAYS),3)

# 审计快照/故障历史
audit:
	python3 ops/audit.py list

# 学习记录 CLI（指定 DB 与子命令）
# 用法: make study-log DB=projects/english/.agents/db/english_learning.db ARGS="week"
study-log:
	python3 shared/study_log/study-log.py --db $(DB) $(ARGS)

# 本地全量语法检查（与 CI 一致）
check:
	@echo "== py_compile =="; find . -name '*.py' -not -path '*/__pycache__/*' -print0 | xargs -0 -n1 python3 -m py_compile
	@echo "== bash -n =="; find . -name '*.sh' -type f -print0 | xargs -0 -n1 bash -n
	@echo "== node --check =="; find . -name '*.cjs' -type f -print0 | xargs -0 -n1 node --check
	@echo "== done =="
