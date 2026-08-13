---
status: resolved
detected: 2026-08-07T08:55:20
resolved: 2026-08-08T10:00:00
tasks: daily-article-digest
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-07T08:55:20
- **涉及任务**: daily-article-digest
- **状态**: resolved

## 故障概述

daily-article-digest 连续出现两类故障：

### 1. 2026-08-05 exit=1（已有修复）
- **根因**: `send_discord.py` 无重试逻辑，Discord API 连接断开（`RemoteDisconnected`）导致脚本崩溃
- **修复**: commit `b41eadb`（article-digest），为 `api()` 函数增加 3 次指数退避重试
- **状态**: 已在 2026-08-06 incident 中记录并修复

### 2. 2026-08-06 timeout + 2026-08-07 持续运行中（本次修复）
- **根因**: `daily_digest.sh` 中 `opencode run` 无超时/重试机制。当 opencode agent 卡住（模型 API 响应异常等），脚本无限挂起，直至被 reveille 60 分钟硬超时或长期僵尸运行
- **日志证据**: digest-20260807-073641.log 显示 opencode 在 `Read /tmp/digest-cand-*.txt` 后停止输出，进程一直未退出
- **修复**: commit `a182609`（article-digest），`daily_digest.sh` 的 opencode 调用替换为超时+重试循环（1800s 超时，2 次尝试），与 `task_health.sh` / `report.sh` 模式一致
- **文件变更**: `.agents/sched/daily_digest.sh`

### 验证结果
- `bash -n daily_digest.sh` → 语法通过
- `python3 -m py_compile send_discord.py` → 编译通过
- `python3 -m py_compile digest_fetch.py` → 编译通过
- 超时后自动重试逻辑与同仓库 `task_health.sh` / `report.sh` 一致

## 分类
| 故障 | 类型 | 修复状态 |
|------|------|----------|
| 2026-08-05 exit=1 | Discord API 连接中断 + 代码缺重试 | ✅ b41eadb (Aug 6) |
| 2026-08-06 timeout + 2026-08-07 挂起 | opencode 无超时保护 | ✅ a182609 (Aug 8) |
