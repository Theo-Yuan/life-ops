---
status: resolved
detected: 2026-08-04T23:35:46
resolved: 2026-08-04T23:55:00
tasks: workout-summary
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-04T23:35:46
- **涉及任务**: workout-summary (任务 ID: 7vV2yQE3)
- **失败日期**: 2026-08-02、2026-08-03
- **状态**: resolved

## 根因分析

`pick_train()` 函数未处理 `trains` 为空列表的场景。

8/2 和 8/3 是休息日，`query_train.py --json` 返回 `trains: []`。原始代码中：
1. `main()` 仅检查 `if not data`（但 data 始终是长度为 1 的 list，不会触发）
2. `generate_summary()` 直接 `pick_train(trains)`，无空值检查
3. `pick_train()` 的 for 循环找不到 `duration_s > 0` 的训练，fallthrough 到 `max(trains, key=...)` —— 此时 `trains` 为空列表，`max([])` 抛出 `ValueError: max() iterable argument is empty`

调用链：`main() → generate_summary() → pick_train()` 三层均缺少空值传播。

## 修复动作

**仓库**: workout_plan  
**Commit**: `d389664`  
**文件**: `.agents/sched/workout_summary.py`

修改内容：
- `pick_train()`: 返回类型 `dict` → `dict | None`，增加 `if not trains: return None` 守卫
- `generate_summary()`: 返回类型 `str` → `str | None`，增加 trains 和 train 的空值检查
- `_summary_data()`: 增加 `if not train` 检查，返回 error 字典
- `main()`: 增加 `if not summary` 检查，打印 "No training data" 并正常退出

## 验证结果

- `python3 workout_summary.py` → exit 0（当日有训练数据时正常生成摘要并发送 Discord）
- 空 trains 场景模拟 → `pick_train()` 返回 `None`，不会触发 `max()` 异常
- 8/4 定时执行成功（exit 0）

## 分类

**非代码缺陷，属边界条件处理缺失**。8/2、8/3 均为休息日无训练数据，属正常业务场景，脚本应优雅退出而非崩溃。修复后休息日将输出 "No training data for YYYY-MM-DD" 并正常退出。
