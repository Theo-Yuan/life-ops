# English Learning — IELTS 6.5 + Work Abroad

英语学习项目，目标为 **雅思总分 6.5（单科不低于 6.0）** + **出国工作英语能力**。

🌐 **知识库（GitHub Pages）**: [theo-yuan.github.io/english_learning](https://theo-yuan.github.io/english_learning/)

## 快速开始

```bash
# 1. 初始化数据库
python .agents/db/init_db.py

# 2. 复制并填写个人档案
cp .agents/profile.example.md .agents/profile.md
# 编辑 .agents/profile.md 填写当前英语水平和目标

# 3. 开始学习
python .agents/workflows/study-log.py log --activity listening --duration 30 --detail "Cambridge 13 Test 1"
```

## 项目结构

```
.agents/
├── skills/           # Agent Skill 文件
│   ├── _shared/      # 鉴权等共享文件
│   ├── ielts-skill.md
│   ├── vocabulary-skill.md
│   └── speaking-skill.md
├── db/              # 数据库
│   ├── schema.sql
│   ├── init_db.py
│   └── english_learning.db (gitignored)
├── workflows/       # 工具脚本
│   └── study-log.py
├── profile.md       # 用户画像 (gitignored)
└── profile.example.md
knowledge/           # 英语学习知识库
├── _inbox/          # 原始收集暂存区
├── 00-快速导航.md
├── 01-IELTS备考指南.md
├── 02-学习方法和计划.md
├── 03-核心语法和写作.md
├── 04-听力与发音.md
├── 05-工作英语.md
├── 06-资源推荐.md
├── 07-中国人学英语：从应试到实战.md
├── 99-来源文献.md
└── WORKFLOW.md
tmp/                 # 临时文件
```

## 目标

| 目标 | 状态 |
|------|------|
| IELTS 总分 6.5+ | 🎯 目标 |
| 听力 6.5+ | 🎯 |
| 阅读 6.5+ | 🎯 |
| 写作 6.0+ | 🎯 |
| 口语 6.0+ | 🎯 |
| 日常英语工作沟通 | 🎯 |

## 使用

学习记录:
```bash
# 记录今天的学习
python .agents/workflows/study-log.py log --activity reading --duration 45 --detail "Cambridge 13 Test 2"

# 查看今日学习
python .agents/workflows/study-log.py today

# 查看本周统计
python .agents/workflows/study-log.py week

# 查看全部统计
python .agents/workflows/study-log.py stats
```

每日听写打卡（DailyDictation）:

```bash
# 每日流水线：快照 → diff → 入库 → agent 生成打卡消息并发送到 Discord
bash .agents/workflows/daily-dictation/run.sh --user-id 597155

# 只跑 agent 通知（读 .agents/profile.md 生成个性化中文打卡消息）
bash .agents/workflows/daily-dictation/notify_agent.sh
```

> 通知采用 agent 驱动：`notify.py --data <date>` 只输出原始 JSON（当日 + 趋势 + profile），
> 由 opencode agent 结合 `profile.md`（IELTS 6.5 目标、听力/词组弱项）生成个性化打卡消息。
> `notify.py <date>` 的旧模板直发模式仍可用。
