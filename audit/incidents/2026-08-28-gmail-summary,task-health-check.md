---
status: resolved
detected: 2026-08-28T08:40:01
resolved: 2026-08-28T09:30:00
tasks: gmail-summary,task-health-check
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-28T08:40:01 (task-health-check)
- **解决时间**: 2026-08-28T09:30:00
- **涉及任务**: gmail-summary (HSClwEzd), task-health-check (sEzf-0i3)
- **状态**: **resolved**（调查完成；gmail-summary 为已知待手动授权状态）

---

## gmail-summary (HSClwEzd) — 2026-08-25/26/27/28 失败（08-17 起第 12 次延续）

### 根因分析
脚本自建日志 `projects/gmail/sched/logs/summary-20260828-080301.log`：

```
[2026-08-28 08:03:01] fetching emails...
[2026-08-28 08:03:02] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
[2026-08-28 08:03:02] HINT: Gmail OAuth refresh token expired (invalid_grant). 重新授权: cd ~/.gmail-mcp-server && npm run auth
```

**根因：Gmail OAuth refresh token 过期（`invalid_grant`），自 08-17 故障的延续，非脚本 bug。**

- `~/.gmail-mcp/credentials.json` 自 08-09 17:42 创建后未变，`refresh_token_expires_in: 604799`（≈7 天），Google Cloud OAuth 应用处于 "testing" 模式，refresh token 约 08-16 已失效
- 本次现场复现 fetch-emails.cjs 仍返回 `{"ok":false,"error":"invalid_grant"}`（exit=1）
- 独立 live 验证：用 `refresh_token` 直连 `https://oauth2.googleapis.com/token` 返回 `HTTP 400 {"error":"invalid_grant","error_description":"Token has been expired or revoked."}`

### 修复动作
无新增代码改动（脚本已由 commit `7a53a01` 加固，能正确识别并记录故障、提示重新授权）。功能恢复阻塞于**手动 OAuth 重新授权**（`npm run auth` 需浏览器登录 Google + 本地 localhost:3000 回调，不可无人值守自动化）：

```bash
cd ~/.gmail-mcp-server && npm run auth
```

长期根治：在 Google Cloud Console 将该 OAuth 应用从 "testing" 发布为 "production"，去除 refresh token 7 天过期限制（此前 incident 已多次提示，仍未处理）。

---

## task-health-check (sEzf-0i3) — 2026-08-27 失败（退出 1，opencode 子进程全部超时）

### 根因分析
执行记录 `~/.config/reveille/executions/sEzf-0i3.json` 中 `D5_6O-48`（08-27 00:40:03Z）exit=1。stderr 日志末尾：

```
[08:58:20] ✗ opencode timeout after 300s (attempt 3)
[08:58:20] FATAL: All 3 attempts failed
```

**根因：非脚本 bug，为修复 agent 在 300s 窗口内未能收敛。** 当日巡检 agent 反复复现/重查 gmail-summary 的 `invalid_grant`（该问题需手动浏览器授权，agent 无法自行完成），导致 3 次 `opencode run` 全部超时，重试耗尽后 wrapper 按设计以 exit=1 退出。wrapper 的 `wait $OP_PID` 退出码捕获逻辑已在 commit `711be2f` 修复，本次超时是守护机制正常工作，而非执行失败。

### 验证结果
```
$ bash -n projects/gmail/sched/email-summary.sh   → 语法通过
$ bash -n ops/task_health.sh                       → 语法通过
$ python3 -m py_compile ops/task_health.py projects/gmail/sched/send_discord.py → 通过
$ node projects/gmail/scripts/fetch-emails.cjs     → {"ok":false,"error":"invalid_grant"}（凭证仍过期，非脚本逻辑错误）
$ 耗时确认：gmail token refresh 直连测试 → HTTP 400 invalid_grant（死凭证）
```

### 分类

| 任务 | 根因 | 修复 | 状态 |
|------|------|------|------|
| gmail-summary 2026-08-25~28 | Gmail OAuth refresh token 过期（08-17 起延续第 12 次） | 无新代码改动；待手动 `npm run auth` | ✅ resolved（授权为手动后续） |
| task-health-check 2026-08-27 | 巡检 agent 处理 gmail 到期问题未收敛，3 次 opencode 超时 | 无新代码改动（wrapper 逻辑正确） | ✅ resolved |

### 备注
- gmail-summary：`invalid_grant` 为已知待手动授权状态，授权完成前每日会持续 exit=1，不重复算新故障
- task-health-check：无脚本逻辑错误；建议用户在完成 gmail 重新授权后，该巡检自动恢复正常，不再因同一原因超时
- **关键待办（阻塞 gmail-summary 功能恢复）**：用户需在浏览器完成 `cd ~/.gmail-mcp-server && npm run auth`，或将 OAuth 应用发布为 production 消除 7 天过期
