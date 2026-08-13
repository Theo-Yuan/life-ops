---
status: resolved
detected: 2026-08-08T08:53:36
resolved: 2026-08-08T10:00:00
tasks: daily-article-digest
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-08T08:53:36
- **涉及任务**: daily-article-digest
- **状态**: resolved

## 故障概述

2026-08-08 巡检检测到 daily-article-digest 仍有运行中的僵尸进程（PID 94032，自 07:39 启动）。根因与 2026-08-07 incident 完全一致：`daily_digest.sh` 缺少 opencode 超时保护，agent 卡住后无限挂起。

## 根因分析
同 [2026-08-07-daily-article-digest.md](./2026-08-07-daily-article-digest.md) — `daily_digest.sh` 中 `opencode run` 无超时/重试机制，当 opencode 响应异常时脚本挂起。

## 修复动作
- 已通过 commit `a182609` 修复（article-digest 仓）
- `daily_digest.sh` 添加 1800s 超时 + 2 次重试循环
- 今日僵尸进程（PID 94032）已手动 kill

## 验证结果
- `bash -n daily_digest.sh` → 通过
- 相关 Python 脚本 `py_compile` → 全部通过

## 分类
| 故障 | 类型 | 修复状态 |
|------|------|----------|
| 2026-08-08 opencode 持续挂起 | opencode 无超时保护（同 08-07） | ✅ a182609 |
