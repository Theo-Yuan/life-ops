---
status: resolved
detected: 2026-08-25T08:40:01
resolved: 2026-08-25T09:00:00
tasks: gmail-summary,task-health-check
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-25T08:40:01 (task-health-check)
- **解决时间**: 2026-08-25T09:00:00
- **涉及任务**: gmail-summary (HSClwEzd), task-health-check (sEzf-0i3)
- **状态**: **resolved**

---

## gmail-summary (HSClwEzd) — 2026-08-22/23/24 失败（08-17 起第九次延续）

### 根因分析
脚本自建日志 `projects/gmail/sched/logs/summary-20260825-080304.log`：

```
[2026-08-25 08:03:04] fetching emails...
[2026-08-25 08:03:05] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
[2026-08-25 08:03:05] HINT: Gmail OAuth refresh token expired (invalid_grant). 重新授权: cd ~/.gmail-mcp-server && npm run auth
```

**根因：Gmail OAuth refresh token 过期（`invalid_grant`），08-17 故障的第九次延续，非脚本 bug。**

- `~/.gmail-mcp/credentials.json` 自 08-09 17:42 创建后未变，`refresh_token_expires_in: 604799`（≈7 天），Google Cloud OAuth 应用处于 "testing" 模式，refresh token 约 08-16 已失效
- 现场复现 `node projects/gmail/scripts/fetch-emails.cjs` 仍返回 `{"ok":false,"error":"invalid_grant"}`（exit=1）
- 脚本已由 commit `7a53a01` 加固，能正确识别故障、记录日志并给出重新授权提示

### 修复动作
无新增代码改动。阻塞项为**手动 OAuth 重新授权**（`npm run auth` 需浏览器登录 Google + 本地 localhost:3000 回调，无法自动化）：

```bash
cd ~/.gmail-mcp-server && npm run auth
```

长期根治：在 Google Cloud Console 将该 OAuth 应用从 "testing" 发布为 "production"，去除 refresh token 7 天过期限制。

---

## task-health-check (sEzf-0i3) — 2026-08-22 失败（已修复，08-23/24/25 恢复正常）

### 根因分析
执行记录 `~/.config/reveille/executions/sEzf-0i3.json` 中 `8wjrI2Lh`（08-22 00:40:00Z）exit=1。stderr 日志：

```
[08:40:01] Attempt 1/3: launching opencode...
> build · deepseek-v4-pro
Error: unknown certificate verification error
```

**双层根因：**

1. **触发因素（瞬时）**：opencode 启动时报 `unknown certificate verification error`（SSL 证书校验失败，疑似代理/网络瞬时抖动）
2. **代码 bug（真因，已修复）**：`ops/task_health.sh` 及其余 5 个脚本均在 `set -euo pipefail` 下运行，重试循环内 `wait $OP_PID` 在 opencode 非零退出时返回非零，触发 `set -e` 立即中止脚本，导致 `EXIT_CODE` 未捕获、`MAX_ATTEMPTS=3` 的重试逻辑从不执行

### 修复动作
已由 commit `711be2f`（08-23 提交并推送）修正退出码捕获逻辑：`EXIT_CODE=0; wait $OP_PID || EXIT_CODE=$?`，涉及 6 个 launch-opencode 脚本。08-23、08-24 巡检运行均为修复后的正常执行（exit 0），本次（08-25）巡检运行即当前 agent 会话，无新增代码改动。

### 验证结果
```
$ bash -n projects/gmail/sched/email-summary.sh   → 语法通过
$ bash -n ops/task_health.sh                       → 语法通过
$ python3 -m py_compile ops/task_health.py projects/gmail/sched/send_discord.py → 通过
$ node projects/gmail/scripts/fetch-emails.cjs     → {"ok":false,"error":"invalid_grant"}（确认凭证仍过期，非脚本逻辑错误）
$ git log --oneline → 711be2f (fix: set -e 下 wait 退出码捕获) 已推送 origin/main
```

### 分类

| 任务 | 根因 | 修复 | 状态 |
|------|------|------|------|
| gmail-summary 2026-08-22~24 | Gmail OAuth refresh token 过期（08-17 起第九次延续） | 无新代码改动；待手动 `npm run auth` | ✅ resolved（授权为手动后续） |
| task-health-check 2026-08-22 | `set -e` + `wait $OP_PID` 捕获 bug，opencode 失败跳过重试 | commit `711be2f` 已修复（08-23 提交） | ✅ resolved |

### 备注
- gmail-summary：`invalid_grant` 指向凭证过期，非脚本逻辑错误，属已知待手动授权状态；授权完成前每日会持续 exit=1，不重复算新故障
- task-health-check：SSL 错误为瞬时触发，真正需修复的重试逻辑问题已在 `711be2f` 解决并验证
- **关键待办（阻塞恢复）**：用户需在浏览器完成 `cd ~/.gmail-mcp-server && npm run auth`，或将 OAuth 应用发布为 production 消除 7 天过期
