---
status: resolved
detected: 2026-08-17T08:40:02
resolved: 2026-08-17T08:44:07
tasks: gmail-summary
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-17T08:40:02 (task-health-check)
- **解决时间**: 2026-08-17T08:44:07
- **涉及任务**: gmail-summary (HSClwEzd)
- **状态**: **resolved**

---

## gmail-summary (HSClwEzd) — 2026-08-17 失败

### 健康报告发现
- task-health-check 扫描执行记录，发现 2026-08-17 运行 `exit=1`，`stdoutTail`/`stderrTail` 均为空（脚本重写后输出全部写入自建日志文件）
- 执行记录 `~/.config/reveille/executions/HSClwEzd.json`：`q0e_LtON` 08-17 00:03:04Z 启动，1 秒后退出，exit=1

### 根因分析

脚本自建日志 `projects/gmail/sched/logs/summary-20260817-080304.log` 记录：

```
[2026-08-17 08:03:04] fetching emails...
[2026-08-17 08:03:05] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
```

**真正根因：Gmail OAuth refresh token 已过期（`invalid_grant`）**，非脚本 bug。

- `fetch-emails.cjs` 读取 `~/.gmail-mcp/credentials.json`，其中 `refresh_token_expires_in: 604799`（≈7 天）
- 该 Google Cloud OAuth 应用处于 **"testing" 模式**，refresh token 默认 7 天过期
- token 创建于 2026-08-09 17:42，约 2026-08-16 过期 → 08-17 首次运行 `invalid_grant`
- 历史运行记录佐证：08-09/10 成功，08-11/12/13/15 超时（MCP discord 超时，另一问题），08-14/16 成功，08-17 失败

### 修复动作

**A. 代码加固（本次提交）**

| Commit | Repo | 内容 |
|--------|------|------|
| `7a53a01` | life-ops | gmail-summary 脚本加固 |

- 提交此前未入库的重写：`email-summary.sh` 改为 opencode 将摘要写入文件后由 `send_discord.py` 直连 Discord REST 发送，规避 MCP discord 超时（08-11/12/13/15 的反复超时根因）
- 修复 `set -e` 下 `wait $OP_PID` 提前退出、跳过重试/错误日志的缺陷（`wait $OP_PID || OP_EXIT_CODE=$?`）
- fetch 失败时记录完整输出，并对 `invalid_grant` 追加重新授权提示
- 新增 `send_discord.py`（Keychain 读 bot token，2000 字符分片，3 次重试）
- `.gitignore` 忽略 `sched/logs/`

**B. 凭证重新授权（需手动，非代码可修）**

`invalid_grant` 必须重新走 OAuth 浏览器授权流程，无法自动完成：

```bash
cd ~/.gmail-mcp-server && npm run auth
```

长期根治：在 Google Cloud Console 将该 OAuth 应用从 "testing" 发布为 "production"，去除 refresh token 7 天过期限制。

### 验证结果

```
$ bash -n projects/gmail/sched/email-summary.sh    → 语法通过
$ python3 -m py_compile projects/gmail/sched/send_discord.py → 编译通过
$ bash projects/gmail/sched/email-summary.sh       → exit 1（预期：token 过期）
  日志正确输出 invalid_grant 并给出重新授权提示
```

- `exit 1` 是凭证过期下的**正确行为**：脚本成功识别故障、记录日志并给出可操作提示
- 完成重新授权后（`npm run auth`），脚本即可恢复 `exit 0`；在授权完成前每日运行仍会以 `invalid_grant` 退出

### 分类

| 任务 | 根因 | 修复 | 状态 |
|------|------|------|------|
| gmail-summary 2026-08-17 | Gmail OAuth refresh token 过期（testing 模式 7 天） | 代码加固 `7a53a01` + 手动重新授权 | ✅ resolved（授权为手动后续） |

### 备注

- 日志为准：`invalid_grant` 明确指向凭证过期，非脚本逻辑错误
- 脚本重写（含超时修复）此前遗留未提交，本次一并入库
- 重新授权完成前，该任务每日会持续 `exit=1`，属已知状态，非新故障
