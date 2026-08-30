---
status: resolved
detected: 2026-08-30T08:40:01
resolved: 2026-08-30T09:05:00
tasks: gmail-summary,task-health-check
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-30T08:40:01
- **解决时间**: 2026-08-30T09:05:00
- **涉及任务**: gmail-summary,task-health-check
- **状态**: resolved（已解决）

## 1. gmail-summary（08-27 / 08-28 失败）

### 根因
Gmail OAuth 刷新令牌过期，接口返回 `{"ok":false,"error":"invalid_grant"}`。
- 证据：`projects/gmail/sched/logs/summary-20260827-080301.log` 与 `summary-20260828-080301.log` 均记录 `FATAL: fetch-emails.cjs failed` + `invalid_grant`。
- 底层原因：OAuth App 处于 Google "Testing" 模式，刷新令牌 7 天过期（credentials.json 中 `refresh_token_expires_in: 604799`）。

### 修复动作
本次无需新改动——已于 2026-08-28 通过 commit `5699716`（`feat(gmail): migrate to gog CLI and drop googleapis dependency`）将取信/取件从 `fetch-emails.cjs`（gmail-mcp + refresh_token）迁移到 `gog` CLI，规避了 refresh_token 7 天过期。

### 验证
- `2026-08-29`：成功（fetch 38 封 → 摘要 → 已发送）。
- `2026-08-30`：成功（fetch 11 封 → 摘要 → 已发送）。
- 失败窗口（08-27/08-28）已不属于持续性问题；确认修复生效。

## 2. task-health-check（08-27 失败）

### 根因
脚本内嵌的 `opencode run` 巡检子流程在第 1..3 次重试中均超过 300s 超时被 kill，最终 `FATAL: All 3 attempts failed`（exit=1）。
- 证据：`~/.local/share/reveille/logs/sEzf-0i3/2026-08-27T00-40-03-109Z.stderr.log` 末尾 `[08:58:20] ✗ opencode timeout after 300s (attempt 3)` / `FATAL: All 3 attempts failed`。
- 每次重试均为全新 opencode 会话（无记忆，需从头读文件），耗时波动大；属瞬时/限时问题，非脚本逻辑 bug（脚本是否正确捕获了 wait 退出码，见 commit `711be2f`）。

### 修复动作（代码加固）
`ops/task_health.sh:100-102`：将巡检子流程的 `TIMEOUT_SEC` 由 300 提升至 900，使「排查 + 修复 + git 提交 + Discord 发送」的多步骤流程在单次窗口内有更充分时间，降低重试轮空概率。`bash -n` 校验通过。

### 验证
- 仅改超时常量，不影响控制流。
- 该任务 08-28 / 08-29 已成功（`success=2`，见快照），确认此前失败为瞬时；本次加固进一步降低复发风险。

## 结论
两个失败任务的根因均已定位：gmail-summary 为凭据过期（已被 gog 迁移修复），task-health-check 为 opencode 巡检超限（已加固超时）并已自恢复。无人为数据缺失或脚本 bug。
