---
status: resolved
detected: 2026-08-27T08:40:03
resolved: 2026-08-27T00:00:00
tasks: gmail-summary
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-27T08:40:03 (task-health-check)
- **解决时间**: 2026-08-28T09:30:00（补记：当日 agent 超时未回写，今天补正）
- **涉及任务**: gmail-summary (HSClwEzd)
- **状态**: **resolved**

---

## gmail-summary (HSClwEzd) — 2026-08-27 失败（08-17 起延续）

### 根因分析
脚本自建日志 `projects/gmail/sched/logs/summary-20260827-080301.log`：

```
[2026-08-27 08:03:01] fetching emails...
[2026-08-27 08:03:02] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
```
**根因：Gmail OAuth refresh token 过期（`invalid_grant`），非脚本 bug，与 08-17 起每日失败同根因。**

### 修复动作
无新增代码改动。功能恢复阻塞于手动 OAuth 重新授权（`npm run auth`），不可无人值守自动化。

### 验证结果
见 `2026-08-28-gmail-summary,task-health-check.md`（同日 live 复现 `invalid_grant`，凭证确认失效）。
