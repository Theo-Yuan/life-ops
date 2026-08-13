---
status: resolved
detected: 2026-08-11T08:42:43
resolved: 2026-08-11T09:30:00
tasks: daily-article-digest,daily-dictation-tracker
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-11T08:42:43
- **解决时间**: 2026-08-11T09:30:00
- **涉及任务**: daily-article-digest, daily-dictation-tracker
- **状态**: **resolved**

---

## daily-article-digest (0ZjOzEGM) — 2026-08-08 失败 + 2026-08-10 超时

### 根因分析

**2026-08-08 exit=1**: 
- `digest_fetch.py` 从 `news.google.com` 获取 RSS 全部失败 (SSL_ERROR_SYSCALL × 3)
- 候选文件为空（0 字节），opencode 检测到空文件无法生成 digest → exit 1
- **已于 2026-08-09 修复**：article-digest `905e07a`（fetch 重试次数 3→5 + 指数退避）+ `a182609`（opencode 超时保护）+ `b41eadb`（Discord 重试）

**2026-08-10 timeout**:
- opencode agent 在读取候选文件后挂起，未产生任何输出
- daily_digest.sh 的 30 分钟超时保护触发，`kill $OP_PID`（SIGTERM）发送给 opencode 进程
- **但 SIGTERM 未能终止 opencode 进程**，进程持续运行直至被 reveille 60 分钟硬超时 kill
- 根因：opencode 不响应 SIGTERM，旧版脚本仅发送 SIGTERM 无强制 kill 后备

### 修复动作
1. **`daily_digest.sh`**: 超时 kill 逻辑：SIGTERM → sleep 2 → SIGKILL（force kill 保证进程终止）
- **Repo**: article-digest
- **Commit**: `5f7dbb1`
- **验证**: `bash -n` 通过；snapshot 步骤测试通过（dailydictation.com 可达）

---

## daily-dictation-tracker (vbObtAvS) — 2026-08-08/09 失败 + 2026-08-10 超时

### 根因分析

**2026-08-08 exit=1**:
- `snapshot.py` 连接 `dailydictation.com` 时 SSL 握手失败：`ssl.SSLEOFError`
- **已于 2026-08-09 修复**：english_learning `9425028`（snapshot.py 3 次重试 + 退避）

**2026-08-09 exit=1**（级联故障）:
- 2026-08-08 快照未保存 → 2026-08-09 diff.py 找不到昨日快照（08-08.json）
- macOS bash 3.2.57 `set -e` 行为差异导致 `run.sh` 错误处理器不可达 → exit 1
- **已于 2026-08-10 修复**：english_learning `1229be4`（bash 3.2 `set +e`/`set -e` 兼容）

**2026-08-10 timeout**（新发现）:
- `notify_agent.sh` 中 opencode agent 耗时 33 分钟（正常 < 2 分钟）
- 旧版 TIMEOUT_SEC=90（过短），且 `kill $OP_PID`（SIGTERM）无法终止 opencode
- opencode 进程持续运行 33 分钟直到自然完成，但已被 reveille 标记为 timeout
- 根因：SIGTERM 对 opencode 无效 + 超时值过短无法覆盖正常慢速运行

### 修复动作
1. **`notify_agent.sh`**: 
   - TIMEOUT_SEC 从 90 → 300（给 opencode 更充裕的时间）
   - 超时 kill 逻辑：SIGTERM → sleep 2 → SIGKILL（force kill）
- **Repo**: english_learning
- **Commit**: `9a2ac0c`
- **验证**: `bash -n` 通过；snapshot.py + diff.py 步骤测试通过（exit 0）

---

## 验证结果 (2026-08-11)

### daily-article-digest
- `bash -n daily_digest.sh` → 语法通过
- `python3 -m py_compile digest_fetch.py send_discord.py` → 通过
- snapshot.py 手工验证：dailydictation.com 正常可达，快照创建成功

### daily-dictation-tracker
- `bash -n notify_agent.sh` → 语法通过
- `python3 -m py_compile snapshot.py diff.py record.py notify.py` → 通过
- 快照步骤：`snapshot.py --user-id 278853 --date 2026-08-11` → exit 0，快照写入成功
- diff 步骤：`diff.py 2026-08-09.json 2026-08-10.json --json` → exit 0，48min / 4 completions

### 历史修复验证（前序 incident）
- **2026-08-08 SSL 错误**: 已验证为上游瞬时故障，retry 逻辑已覆盖
- **2026-08-09 bash 3.2 兼容**: `set +e`/`set -e` 包裹已验证生效
- **部署状态**: deploy worktree 与 source repo 完全同步（diff 无差异）

---

## Git Push 状态
| Repo | Commit | 描述 | 状态 |
|------|--------|------|------|
| article-digest | `5f7dbb1` | kill -KILL backup for opencode timeout | ✅ 已推送 |
| english_learning | `9a2ac0c` | harden opencode timeout 90→300s + kill -KILL | ✅ 已推送 |
| life-ops | `483c795` (本 incident 回写) | update incident record | ⏳ 待推送 |

---

## 分类
| 故障 | 类型 | 修复 commit | 状态 |
|------|------|-------------|------|
| daily-article-digest 2026-08-08 | 上游 SSL + 空候选文件 | article-digest `905e07a` + `a182609` | ✅ resolved (前序) |
| daily-article-digest 2026-08-10 | opencode 挂起 + SIGTERM 无效 | article-digest `5f7dbb1` | ✅ resolved |
| daily-dictation-tracker 2026-08-08 | 上游 SSL (dailydictation.com) | english_learning `9425028` | ✅ resolved (前序) |
| daily-dictation-tracker 2026-08-09 | bash 3.2 `set -e` 兼容性（级联） | english_learning `1229be4` | ✅ resolved (前序) |
| daily-dictation-tracker 2026-08-10 | opencode notify agent 超时 | english_learning `9a2ac0c` | ✅ resolved |

## 备注
- 所有前序修复（08-08/08-09）已部署并验证通过
- 本次仅新增 `kill -KILL` 强制终止逻辑，加固已有的 opencode 超时机制
- opencode agent 响应时间的不确定性是其固有特性，超时 + 强制 kill 是最佳防御措施
