# Life Ops — 个人项目总运营仓（monorepo）

集中管理个人学习项目的**领域工具 + 知识库 + 自动化**：训练（workout）、英语（english）、理财（finance）、邮件（gmail）、文章日报（article），以及跨项目的聚合/调度/巡检（ops）。

> 由原 6 个独立仓库（workout_plan / english_learning / finance_plan / gmail-organizer / article-digest / life-ops）合并而来。设计文档见 `theo-docs/MRG-Designs/Life Ops Monorepo/Design.md`。

## 目录结构

```
life-ops/
├── projects/        # 领域：工具 / 数据 / 自动化
│   ├── workout/     # 训练（训记 API + train.db + sched）
│   ├── english/     # 英语（study-log + 听写打卡）
│   ├── finance/     # 理财（study-log + 认知知识）
│   ├── gmail/       # Gmail 自动分类 + 日摘要（Node）
│   └── article/     # 每日文章推送
├── docs/            # 知识库（GitHub Pages 三分区：workout/english/finance）
├── shared/          # 共享脚手架（study-log / db / tools）
├── ops/             # 运营层（聚合日报 / 任务巡检 / 审计）
├── audit/           # 审计数据（巡检快照 + 故障记录）
└── .agents/skills/  # 全部领域技能（合并于根）
```

## 快速开始

```bash
# 聚合日报 → Discord 私信
just report

# 定时任务巡检（最近 3 天）
just health

# 审计快照历史
just audit

# 学习记录（指定 DB）
just study-log db=projects/english/.agents/db/english_learning.db args=week

# 本地语法检查（与 CI 一致）
just check
```

## 知识库（GitHub Pages）

单站三分区：`theo-yuan.github.io/life-ops/workout/`、`/english/`、`/finance/`。

## 定时任务（reveille）

| 任务 | 调度 | 脚本 |
|---|---|---|
| workout-preview | 07:00 | `projects/workout/.agents/sched/workout_preview.sh` |
| workout-summary | 22:00 | `projects/workout/.agents/sched/workout_summary.sh` |
| daily-dictation-tracker | 23:33 | `projects/english/.agents/workflows/daily-dictation/run.sh` |
| gmail-summary | 08:03 | `projects/gmail/sched/email-summary.sh` |
| life-ops-report | 23:35 | `ops/report.sh` |
| task-health-check | 08:40 | `ops/task_health.sh` |
| ~~daily-article-digest~~（暂停） | 07:30 | `projects/article/.agents/sched/daily_digest.sh` |

> 每日新闻（文章日报）已通过 `reveille disable` 暂停（未删除，可随时 `reveille enable 0ZjOzEGM` 恢复）。聚合日报 `ops/report.sh` 汇总 workout + english + gmail。

## 约定

- 数据以实际记录为准，不要编造；脚本提供什么就用什么。
- 个人档案在各项目 `projects/<name>/.agents/profile.md`（gitignored）。
- 领域技能统一在根 `.agents/skills/`，知识库在 `docs/<name>/knowledge/`。
- 报告发送：频道用 `YOUR_SERVER/<频道名>`，私信用用户名 `YOUR_DISCORD_USERNAME`。
