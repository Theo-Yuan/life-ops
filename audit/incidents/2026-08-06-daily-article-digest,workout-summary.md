---
status: resolved
detected: 2026-08-06T08:49:22
resolved: 2026-08-06T13:00:00
tasks: daily-article-digest,workout-summary
---

# 定时任务故障 Incident

## 状态
- **检测时间**: 2026-08-06T08:49:22
- **涉及任务**: daily-article-digest (0ZjOzEGM), workout-summary (7vV2yQE3)
- **状态**: resolved

## daily-article-digest

### 根因分析

2026-08-05（实际运行 2026-08-06 07:45 CST）退出码 1。

opencode 成功生成了 digest 文件，但在 `send_discord.py` 发送到 Discord 时，HTTP 请求被服务端断开：
```
http.client.RemoteDisconnected: Remote end closed connection without response
```

脚本的 `api()` 函数无重试逻辑，连接异常直接崩溃，导致 digest 生成成功但未送达。

### 修复动作

**仓库**: article-digest（首次初始化 git）  
**Commit**: `b41eadb`  
**Remote**: `git@github.com:Theo-Yuan/article-digest.git`  
**文件**: `.agents/sched/send_discord.py`

修改内容：
- `api()` 函数增加 3 次指数退避重试（`RemoteDisconnected`、`TimeoutError`、`ConnectionError`、`OSError`）
- 同时处理 429 限频响应（读取 `Retry-After` 头后重试）
- 正确管理 `HTTPSConnection` 生命周期（conn.close() 移到 finally 块）

### 验证结果

- `python3 -m py_compile send_discord.py` → 编译通过
- 脚本功能与修复前一致，仅增加错误重试包装

## workout-summary

### 根因分析

2026-08-02、2026-08-03 两次失败，退出码 1。

```
ValueError: max() iterable argument is empty
  pick_train() → max(trains, key=...)  # trains 为空列表
```

8/2 和 8/3 是休息日，`query_train.py --json` 返回 `trains: []`。`pick_train()` 未处理空列表，`max([])` 抛出异常。

### 修复动作

**仓库**: workout_plan  
**Commit**: `d389664`（2026-08-04 已修复）  
**文件**: `.agents/sched/workout_summary.py`

- `pick_train()`: 增加 `if not trains: return None` 守卫
- `generate_summary()`: 返回类型 `str | None`，增加空值检查
- `main()`: 无数据时打印 "No training data" 正常退出

### 验证结果

- 8/4、8/5 定时执行均成功（exit 0）
- 空 trains 场景返回 `None` 而非崩溃

## 分类

| 任务 | 类型 | 修复状态 |
|------|------|----------|
| daily-article-digest | 瞬时故障（Discord API 连接中断）+ 代码缺重试 | ✅ 已修复 |
| workout-summary | 代码缺陷（边界条件未处理） | ✅ 已修复（8/4） |
