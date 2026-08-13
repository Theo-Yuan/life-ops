# Audit — 定时任务巡检审计

本目录承载定时任务的**版本控制 + 审计日志**，用于事后追溯。

## 目录结构

| 路径 | 内容 |
|------|------|
| `snapshots/task-health-YYYY-MM-DD.json` | 每日巡检快照（含各任务健康状态 + 各仓 git SHA 版本） |
| `incidents/*.md` | 故障记录（检测→排查→修复→resolved 全流程） |
| `CHANGELOG.md` | 本系统变更日志 |

## 追溯流程

1. **巡检**（每日由 reveal 触发 `sched/task_health.sh`）
   - 读取全部 reveal 任务最近 N 天执行记录
   - 保存快照到 `snapshots/`，记录每个任务成功/失败数 + **各项目仓当前 git SHA**
2. **故障处理**
   - 发现失败 → 先写 incident 草稿（`status: open`），确保故障信息不丢失
   - opencode agent 排查根因 → 修复 → 验证 → **git commit + push 到受影响仓**
   - 回写 incident（根因/修复动作/commit SHA/验证）→ 状态改 `resolved`
   - 发送 DM 报告到用户
3. **查询**
   ```bash
   python3 scripts/audit.py list            # 所有快照日期
   python3 scripts/audit.py trend --days 14 # 健康趋势
   python3 scripts/audit.py show 2026-08-04 # 某天详情（含 git 版本）
   python3 scripts/audit.py incidents       # 故障记录列表
   ```

## 关键设计

- **快照含 git SHA**：`task_health.py` 记录各仓当前 commit，故障时可精确定位"哪个版本在跑"
- **incident 先于 agent 落盘**：即使 agent 修复失败，故障证据仍在
- **修复强制走 git**：所有代码修复和 incident 回写都必须提交推送，保证可追溯
- **running 状态不计入失败**：避免把进行中的任务误判为故障
