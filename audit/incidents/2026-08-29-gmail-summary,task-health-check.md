---
status: resolved
detected: 2026-08-29T08:40:06
resolved: 2026-08-29T08:44:00
tasks: gmail-summary,task-health-check
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-29T08:40:06 (task-health-check)
- **解决时间**: 2026-08-29T08:44:00
- **涉及任务**: gmail-summary (HSClwEzd), task-health-check (sEzf-0i3)
- **状态**: **resolved**（故障已由此前 commit 根治；本次为健康确认跑）

---

## gmail-summary (HSClwEzd) — 2026-08-26/27/28 失败，08-29 已恢复

### 根因分析
脚本自建日志 `projects/gmail/sched/logs/summary-*.log`（错误写入该日志而非 stderr，故 reveal stderr 记录为空）：

```
[2026-08-26 08:03:02] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
[2026-08-27 08:03:02] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
[2026-08-28 08:03:02] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
```

**根因：旧 OAuth 路径的 Gmail refresh token 过期（`invalid_grant`）。** 依赖 `~/.gmail-mcp-server` (googleapis, testing 模式，refresh token 约 7 天过期)，为 08-17 起反复出现的凭证过期问题延续，非脚本逻辑 bug。

### 修复动作（已落地，非本次新增）
commit `5699716` **feat(gmail): migrate to gog CLI and drop googleapis dependency** 于 08-28 部署，将抓取从 `fetch-emails.cjs`（googleapis + OAuth refresh token）迁移到 `gog-fetch.cjs`（gog CLI 统一凭证管理），彻底移除 7 天过期的 refresh token 依赖。本次无新增代码改动。

另：08-29 08:03 执行记录 `jgc1UJEY` (exit=0) 的 stderr 出现 `email-summary.sh: line 42: 📊: command not found` 等噪声——对应当前文件为 mid-migration 的草稿版；当前 on-disk 脚本已核实 `bash -n` 通过、heredoc 正确闭合（`sed -n '41,88p'` 复现无误），该噪声不影响结果，无需修复。

### 验证结果
```
$ bash -n projects/gmail/sched/email-summary.sh        → 语法通过
$ node projects/gmail/scripts/gog-fetch.cjs           → {"ok":true,"total":37,"unread":17}（exit=0）
$ 08-29 08:03 实际执行 exit=0：fetched 38 emails → opencode 生成 digest → send_discord 送达 f1andre8472 (577385627562016792)
```

---

## task-health-check (sEzf-0i3) — 2026-08-27 失败（退出 1，opencode 全部超时）

### 根因分析
执行记录 `~/.config/reveille/executions/sEzf-0i3.json` 中 `D5_6O-48`（08-27 00:40:03Z）exit=1。stderr 日志末尾：

```
[08:58:20] ✗ opencode timeout after 300s (attempt 3)
[08:58:20] FATAL: All 3 attempts failed
```

**根因：非脚本 bug，为修复 agent 在 300s 窗口内未能收敛。** 当日巡检 agent 反复复现/重查 gmail-summary 的 `invalid_grant`（需手动浏览器授权，agent 无法自行完成），3 次 `opencode run` 全部超时，重试耗尽后 wrapper（`ops/task_health.sh`）按设计以 exit=1 退出。wrapper 的退出码捕获逻辑已在 commit `711be2f` 修复；本次超时为守护机制正常工作，而非执行失败。

### 验证结果
```
$ bash -n ops/task_health.sh   → 语法通过
$ 08-28 巡检 exit=0；08-29 巡检=本次（running/成功）
```

---

## 分类

| 任务 | 根因 | 修复 | 状态 |
|------|------|------|------|
| gmail-summary 2026-08-26~28 | 旧路径 Gmail OAuth refresh token 过期（`invalid_grant`） | commit `5699716` gog CLI 迁移已根治；08-29 成功 | ✅ resolved |
| task-health-check 2026-08-27 | 巡检 agent 处理 gmail 凭证到期未收敛，3 次 opencode 超时 | 无新增代码改动（wrapper 逻辑正确，`711be2f`） | ✅ resolved |

### 备注
- gmail-summary 的功能恢复已由 gog CLI 迁移完成，后续无需再依赖手动 `npm run auth`。
- task-health-check 08-27 失败系 gmail 未修复期 agent 超时；gmail 已根治后不再因同因触发。
- 本次无代码改动，仅回写 incident 记录，提交 `audit/`（snapshot + incident）。
