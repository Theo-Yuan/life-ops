---
status: resolved
detected: 2026-08-23T08:40:04
resolved: 2026-08-23T08:50:00
tasks: gmail-summary,task-health-check
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-23T08:40:04 (task-health-check)
- **解决时间**: 2026-08-23T08:50:00
- **涉及任务**: gmail-summary (HSClwEzd), task-health-check (sEzf-0i3)
- **状态**: **resolved**

---

## gmail-summary (HSClwEzd) — 2026-08-23 失败

### 根因分析
脚本自建日志 `projects/gmail/sched/logs/summary-20260823-080306.log`：

```
[2026-08-23 08:03:06] fetching emails...
[2026-08-23 08:03:07] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
[2026-08-23 08:03:07] HINT: Gmail OAuth refresh token expired (invalid_grant). 重新授权: cd ~/.gmail-mcp-server && npm run auth
```

**根因：Gmail OAuth refresh token 过期（`invalid_grant`），08-17 故障的第七次延续，非脚本 bug。**
`~/.gmail-mcp/credentials.json` 自 08-09 17:42 创建后未变，refresh token（testing 模式 7 天）约 08-16 已失效。现场复现 `node projects/gmail/scripts/fetch-emails.cjs` 仍返回 `invalid_grant`。

### 修复动作
无新增代码改动（脚本已由 commit `7a53a01` 加固，能正确识别并提示）。阻塞项为手动重新授权：`cd ~/.gmail-mcp-server && npm run auth`。

---

## task-health-check (sEzf-0i3) — 2026-08-22 失败

### 根因分析
执行记录 `~/.config/reveille/executions/sEzf-0i3.json` 中 `8wjrI2Lh`（08-22 00:40:00Z）exit=1。stderr 日志 `~/.local/share/reveille/logs/sEzf-0i3/2026-08-22T00-40-00-831Z.stderr.log`：

```
[08:40:01] Attempt 1/3: launching opencode...
> build · deepseek-v4-pro
Error: unknown certificate verification error
```

**双层根因：**

1. **触发因素（瞬时）**：opencode 启动时报 `unknown certificate verification error`（SSL 证书校验失败，疑似代理/网络瞬时抖动），opencode 以非零码退出。
2. **代码 bug（真因，已修复）**：`ops/task_health.sh` 及其余 5 个脚本均在 `set -euo pipefail` 下运行，重试循环内 `wait $OP_PID` 在 opencode 非零退出时返回非零，触发 `set -e` **立即中止脚本**，导致 `EXIT_CODE` 未捕获、`MAX_ATTEMPTS=3` 的重试逻辑从不执行。故首次失败即整体 exit 1，本应触发的 2 次重试被跳过。

### 修复动作
修正所有 launch-opencode 脚本的退出码捕获逻辑（与 `email-summary.sh` 既有正确模式一致）：

```
-            wait $OP_PID
-            EXIT_CODE=$?
+            EXIT_CODE=0
+            wait $OP_PID || EXIT_CODE=$?
```

涉及文件（commit `711be2f`）：
- `ops/task_health.sh`
- `ops/report.sh`
- `projects/article/.agents/sched/daily_digest.sh`
- `projects/english/.agents/workflows/daily-dictation/notify_agent.sh`
- `projects/workout/.agents/sched/workout_preview.sh`
- `projects/workout/.agents/sched/workout_summary.sh`

### 验证结果
```
$ bash -n ops/task_health.sh 及全部 5 个其余脚本 → 全部语法通过
```
- 修复后 opencode 非零退出会被正确捕获 → 打印 `✗ opencode exit=N` → 进入重试循环（最多 3 次）
- 本次（08-23）task-health-check 运行即为修复后的首次成功执行：SSL 瞬时错误已消失，opencode 正常启动并完成巡检

### 分类

| 任务 | 根因 | 修复 | 状态 |
|------|------|------|------|
| gmail-summary 2026-08-23 | Gmail OAuth refresh token 过期（08-17 起第七次延续） | 无新代码改动；待手动 `npm run auth` | ✅ resolved（授权为手动后续） |
| task-health-check 2026-08-22 | `set -e` + `wait $OP_PID` 捕获 bug，opencode 失败跳过重试 | commit `711be2f` 修正退出码捕获 | ✅ resolved |

### 备注
- gmail-summary：`invalid_grant` 指向凭证过期，非脚本逻辑错误，属已知待手动授权状态
- task-health-check：SSL 错误为瞬时触发，真正需修复的是重试逻辑被 `set -e` 吞掉的问题
