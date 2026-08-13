---
status: resolved
detected: 2026-08-10T08:40:01
resolved: 2026-08-10T09:30:00
tasks: daily-article-digest,daily-dictation-tracker
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-10T08:40:01
- **解决时间**: 2026-08-10T09:30:00
- **涉及任务**: daily-article-digest, daily-dictation-tracker
- **状态**: **resolved**

---

## daily-article-digest (0ZjOzEGM) — 2026-08-08 失败

### 根因分析
- 2026-08-08 执行时 opencode 在文章筛选阶段挂起（无超时保护），最终超时退出
- 旧版 `daily_digest.sh` 无 opencode 超时保护，agent 卡住后无限挂起
- 旧版 `digest_fetch.py` 重试次数不足，news.google.com SSL 瞬断时直接失败
- 日志（`digest-20260808-073918.log`）显示 opencode 开始读取候选文件后即无后续输出

### 修复动作（已于 08-09 前完成）
1. **`digest_fetch.py`**: 重试次数 3→5，退避策略改为指数 (5s/10s/20s/40s/80s)
2. **`daily_digest.sh`**: 添加 1800s 超时 + 2 次重试循环；候选文件为空时 exit 0
3. **`send_discord.py`**: 增加 3 次指数退避重试
- **Repo**: article-digest
- **Commits**: `905e07a`（fetch 韧性）、`a182609`（opencode 超时）、`b41eadb`（Discord 重试）
- **验证**: 2026-08-09 运行成功（exit 0，log 完整）

---

## daily-dictation-tracker (vbObtAvS) — 2026-08-08 失败

### 根因分析
- `snapshot.py` 的 `fetch_text()` 无重试逻辑
- 连接 `dailydictation.com` 时 SSL 握手失败: `ssl.SSLEOFError: [SSL: UNEXPECTED_EOF_WHILE_READING]`
- 单次网络异常即导致整个脚本崩溃 → `run.sh` 因 `set -e` 退出 1
- 当日未保存 08-08 快照，触发次日（08-09）的级联故障

### 修复动作
1. **`snapshot.py`**: `fetch_text()` 增加 3 次重试 + 线性退避 (2s/4s/6s)
- **Repo**: english_learning
- **Commit**: `9425028`（snapshot.py 重试）
- **验证**: 08-09 快照步骤成功执行（149 lessons, 37.2h）

---

## daily-dictation-tracker (vbObtAvS) — 2026-08-09 失败（级联故障）

### 根因分析
- **直接原因**: `diff.py --auto` 需要昨日快照（08-08.json），但 08-08 快照由于 SSL 错误未保存
- **真正根因**: macOS bash 3.2.57 的 `set -e` 行为差异：命令替换 `$()` 在变量赋值中失败时，bash 3.2 会直接退出脚本，**不等待后续错误处理**
- run.sh 第 53 行 `DIFF_JSON=$(python3 diff.py --auto --json 2>&1)` 中 diff.py 失败 → bash 3.2 立即 kill 进程 → `if [ $? -ne 0 ]` 错误处理器永远不可达 → exit 1
- 此为 bash 版本兼容性 bug（bash 4.4+ 已修复此行为）

### 修复动作
1. **`run.sh`**: 将 diff.py 调用包裹在 `set +e` / `set -e` 中，捕获退出码后再判断
   - `set +e` → 执行 diff.py → `set -e` → 检查 `$?`
- **Repo**: english_learning
- **Commit**: `1229be4`（bash 3.2 兼容）
- **验证**:
  - `bash -n` 语法检查通过
  - 模拟缺失昨日快照场景：diff.py exit 1 → 错误处理器正确捕获 → exit 0（graceful）
  - 快照步骤验证通过（retry 逻辑生效，dailydictation.com 可正常访问）

---

## ✅ 验证结果 (2026-08-10 复核)
- **daily-article-digest**: 2026-08-09 自动运行成功（exit 0）。候选文件 fetch + opencode 超时保护 + Discord 发送全部正常。
- **daily-dictation-tracker**: `reveille run vbObtAvS`（2026-08-10 08:47 UTC）exit 0。
  - snapshot → diff → record → Discord 四步全部通过
  - snapshot 重试正常、diff 正常对比 08-09 基线、Discord 通知成功
  - bash 3.2 `set +e`/`set -e` 兼容方案生效

## Git Push 状态
| Repo | Commits | 状态 |
|------|---------|------|
| article-digest | `905e07a`, `a182609`, `b41eadb` | ✅ 已推送 |
| english_learning | `9425028`, `1229be4` | ✅ 已推送 |
| life-ops | `3adde26` (本 incident) + `aca84f0` (08-09 incident) | ✅ 已推送 |

## 分类
| 故障 | 类型 | 修复 commit | 状态 |
|------|------|-------------|------|
| daily-article-digest 2026-08-08 | opencode 超时/上游 SSL | article-digest `a182609` + `905e07a` | ✅ resolved |
| daily-dictation-tracker 2026-08-08 | 上游 SSL (dailydictation.com) | english_learning `9425028` | ✅ resolved |
| daily-dictation-tracker 2026-08-09 | bash 3.2 `set -e` 兼容性（级联） | english_learning `1229be4` | ✅ resolved |
