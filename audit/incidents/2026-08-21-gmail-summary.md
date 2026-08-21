---
status: resolved
detected: 2026-08-21T08:56:27
resolved: 2026-08-21T09:28:00
tasks: gmail-summary
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-21T08:56:27 (task-health-check)
- **解决时间**: 2026-08-21T09:28:00
- **涉及任务**: gmail-summary (HSClwEzd)
- **状态**: **resolved**

---

## gmail-summary (HSClwEzd) — 2026-08-21 失败

### 健康报告发现
- task-health-check 扫描执行记录，发现 2026-08-18/19/20/21 四次运行均 `exit=1`，`stdoutTail`/`stderrTail` 均为空（脚本输出全部写入自建日志文件）
- 执行记录 `~/.config/reveille/executions/HSClwEzd.json`：`vlAnk2pH`（08-21 00:08:10Z）启动，约 2 秒后退出，exit=1

### 根因分析

脚本自建日志 `projects/gmail/sched/logs/summary-20260821-080810.log` 记录：

```
[2026-08-21 08:08:10] fetching emails...
[2026-08-21 08:08:12] FATAL: fetch-emails.cjs failed
{"ok":false,"error":"invalid_grant"}
[2026-08-21 08:08:12] HINT: Gmail OAuth refresh token expired (invalid_grant). 重新授权: cd ~/.gmail-mcp-server && npm run auth
```

**真正根因：Gmail OAuth refresh token 过期（`invalid_grant`），非脚本 bug，是 2026-08-17 同一故障的延续（第五次重复）。**

- `~/.gmail-mcp/credentials.json` 中 `refresh_token_expires_in: 604799`（≈7 天），token 创建于 2026-08-09 17:42，refresh token 约 2026-08-16 失效
- Google Cloud OAuth 应用处于 **"testing" 模式**，refresh token 默认 7 天过期 → 08-17/18/19/20/21 连续 `invalid_grant`
- 08-17 incident（`2026-08-17-gmail-summary.md`）已判定根因并完成代码加固（commit `7a53a01`）；08-18/19/20 incident 均确认无新增代码问题，并已明确备注："重新授权完成前，该任务每日会持续 exit=1，属已知状态，非新故障"
- 现场复现：`node scripts/fetch-emails.cjs` 仍返回 `{"ok":false,"error":"invalid_grant"}`，且 `~/.gmail-mcp/credentials.json` 内容自 08-09 起未变 → 确认手动重新授权至今未执行

### 修复动作

**无需新增代码改动**：脚本在 08-17 incident 的 commit `7a53a01` 中已加固——fetch 失败时记录完整输出、对 `invalid_grant` 追加重新授权提示并正确 `exit 1`。

真正阻塞项为**手动 OAuth 重新授权**（需浏览器登录 Google，无法自动化）：

```bash
cd ~/.gmail-mcp-server && npm run auth
```

长期根治：在 Google Cloud Console 将该 OAuth 应用从 "testing" 发布为 "production"，去除 refresh token 7 天过期限制，避免每周重复授权。

### 验证结果

```
$ node projects/gmail/scripts/fetch-emails.cjs    → {"ok":false,"error":"invalid_grant"} exit=1
$ bash -n projects/gmail/sched/email-summary.sh    → 语法通过
$ python3 -m py_compile projects/gmail/sched/send_discord.py → 编译通过
```

- `exit 1` 是凭证过期下的**正确行为**：脚本成功识别故障、记录日志并给出可操作提示
- 完成重新授权后（`npm run auth`），脚本即可恢复 `exit 0`；在授权完成前每日运行仍会以 `invalid_grant` 退出

### 分类

| 任务 | 根因 | 修复 | 状态 |
|------|------|------|------|
| gmail-summary 2026-08-21 | Gmail OAuth refresh token 过期（testing 模式 7 天），08-17/18/19/20 同源延续 | 无新代码改动（已由 `7a53a01` 加固）；待手动 `npm run auth` | ✅ resolved（授权为手动后续） |

### 备注

- 日志为准：`invalid_grant` 明确指向凭证过期，非脚本逻辑错误
- 本 incident 为 08-17/18/19/20 故障的**第五次重复**，根因一致，代码侧无新问题
- 关键待办（阻塞恢复）：用户在浏览器完成 `cd ~/.gmail-mcp-server && npm run auth`
- 彻底解决：将 OAuth 应用发布为 production，消除 7 天过期
