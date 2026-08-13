---
description: "人生运营 Bootup Skill — 个人项目 portfolio 全貌，开始任何跨项目任务前必读"
---

# Bootup: 个人学习项目 Portfolio

> 在开始任何涉及多个个人项目的任务前，先加载本 Skill 了解全貌。

## 项目总览

单一 `life-ops` monorepo（由原 6 个独立仓库合并），`projects/` 下按领域划分，`ops/` 做跨项目汇总。

| 项目 | 状态 | 数据源 | 自动化 |
|------|------|--------|--------|
| projects/workout | 运行中 | 训记 App → train.db | 预告/摘要 → Discord 频道 |
| projects/english | 运行中 | study_log.db + 听写快照 | 听写打卡 → Discord 频道 |
| projects/finance | 基础 | finance_plan.db | study-log CLI |
| projects/gmail | 运行中 | Gmail API → JSON 摘要 | 08:03 日摘要 → 聚合 |
| projects/article | 运行中 | topics.txt → 文章 | 07:30 日报 → Discord DM |
| ops/ | 运行中 | 各项目 db + reveal 日志 | 日报/巡检 → Discord 私信 |

## 数据层

- **训练**：`projects/workout/.agents/db/train.db`
  - 表：trains(datestr,title,duration_s) / movements / sets
  - 标题含 P1-推/拉/腿 标识分化
- **英语**：`projects/english/.agents/db/english_learning.db`
  - 表：study_log(date,duration_min,activity,detail) / vocabulary / mock_test / daily_goal
  - 听写快照：`projects/english/tmp/daily-dictation/<date>.json`
- **理财**：`projects/finance/.agents/db/finance_plan.db`
  - 表：study_log(date,duration_min,activity,detail)
- **邮件**：`projects/gmail/tmp/emails.json`
  - 由 fetch-emails.cjs 生成，结构：stats, categories, important[{sender,subject,body}], others
- **调度**：`~/.config/reveille/executions/*.json`（任务执行状态）

## 目录速查

- 领域工具/数据/自动化：`projects/<name>/`
- 知识库（GitHub Pages）：`docs/<name>/knowledge/`
- 共享脚手架：`shared/`
- 运营层脚本：`ops/`
- 审计数据：`audit/`
- 领域技能：根 `.agents/skills/`

## 约定

- **数据以实际记录为准**，不要编造；脚本提供什么就用什么
- 点评结合各项目 profile（`projects/<name>/.agents/profile.md`）
- 文档写入 `$AGENT_DOCS_DIR/projects/<project>/docs/`
- 报告发送：频道用 `学习星球/<频道名>`，私信用用户名 `f1andre8472`
