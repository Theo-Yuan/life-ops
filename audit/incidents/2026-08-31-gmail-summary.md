---
status: resolved
detected: 2026-08-31T08:40:04
resolved: 2026-08-31T08:55:00
tasks: gmail-summary
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-31T08:40:04
- **解决时间**: 2026-08-31T08:55:00
- **涉及任务**: gmail-summary (HSClwEzd)
- **状态**: **resolved**（08-28 失败已由 commit `5699716` 根治；本次顺带修复了持续存在于每次运行 stderr 的 heredoc 命令替换噪声）

---

## gmail-summary (HSClwEzd) — 2026-08-28 失败（exit=1）

### 根因分析
巡检快照 `audit/snapshots/task-health-2026-08-31.json` 将 gmail-summary 标记为 3/4 成功、1 次失败（2026-08-28 exit=1）。此前 incidents（08-28/08-29/08-30）已完整定位该失败：

**根因：Gmail OAuth refresh token 过期（`invalid_grant`），非脚本逻辑 bug。** 迁移前依赖 `fetch-emails.cjs`（googleapis + `~/.gmail-mcp-server`，OAuth app 处于 Google "testing" 模式，refresh token 约 7 天过期），08-17 起反复触发。脚本自建日志 `projects/gmail/sched/logs/summary-20260828-080301.log` 记录：

```
[2026-08-28 08:03:01] fetching emails...
[2026-08-28 08:03:02] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
```

### 修复动作
- **08-28 失败（已先行根治）**：commit `5699716` **feat(gmail): migrate to gog CLI and drop googleapis dependency** 于 08-28 部署，将抓取迁移到 `gog-fetch.cjs`（gog CLI 统一凭证管理），彻底移除 7 天过期的 refresh token 依赖。08-29/08-30/08-31 均 exit=0。
- **本次新增修复（commit `9a770bd`）**：`projects/gmail/sched/email-summary.sh` 中 `<<PROMPT_EOF` 未加引号的 heredoc 内含有两行三反引号 markdown 代码围栏 `\`\`\``。Bash 会将**未引用 heredoc** 中的反引号当作命令替换，把格式示例块（emoji/金额等）当作 shell 命令执行，导致成功运行的 stderr 也持续输出 `email-summary.sh: line N: 📊: command not found` 之类噪声。已将两处围栏转义为 `\`\`\``，使 bash 将其视为字面量，同时保留 `$EMAILS_PATH`/`$DIGEST` 的变量展开。

### 验证结果
- `bash -n projects/gmail/sched/email-summary.sh` → 语法通过。
- 端到端 stub 运行（真实 node/gog-fetch 路径注入 `{"ok":true,"total":3}`，`opencode` 打桩）：`exit=0`，stderr 为空，`command not found` 计数 = 0。
- 真实 `node projects/gmail/scripts/gog-fetch.cjs` → `{"ok":true,"total":7,"unread":6}`（exit=0）。
- 08-29/08-30/08-31 真实执行 exit=0（摘要已通过 Discord 送达 f1andre8472）。

---

## 分类

| 项 | 根因 | 修复 | 状态 |
|----|------|------|------|
| gmail-summary 2026-08-28 exit=1 | 旧路径 Gmail OAuth refresh token 过期（`invalid_grant`） | commit `5699716` gog CLI 迁移已根治 | ✅ resolved |
| gmail-summary 每次成功运行 stderr 噪声 | 未引用 heredoc 内 markdown 围栏反引号被 bash 当作命令替换 | commit `9a770bd` 转义围栏 | ✅ resolved |

### 备注
- 本次巡检脚本（`ops/task_health.py`）无改动；快照 `task-health-2026-08-31.json` 已保存于 `audit/snapshots/`（随本 incident 一并提交）。
- 巡检窗口为 `--days 3`（cutoff 2026-08-28），故 08-28（已修复前的最后一次失败）仍在窗口内被标记；该失败非持续性，后续巡检不再复现。
- `tmp/` 为 gitignored 工作产物，未列入提交。
