# 🧠 个人财富增长助手

> AI Agent 驱动的理财投资学习系统 — 先懂再投，构建你的财富认知体系

📖 **知识库网站**: [Theo-Yuan.github.io/finance_plan](https://Theo-Yuan.github.io/finance_plan)（Docsify 发布）

---

## 项目定位

```
阶段一（当前）:  📚 学习理财投资知识 → 建立认知体系
阶段二（未来）:  📊 构建个人财务模型 → 数据驱动成长
```

**先学习，后建模。** 这个项目首先是一位理财导师，教你建立正确的财富观念和投资方法论。知识库通过 GitHub Pages 发布，随时随地可访问。

## 项目结构

```
finance_plan/
├── knowledge/                  ★ 核心：财富知识库（GH Pages 发布）
│   ├── 00-快速导航.md          ─ 索引/入口
│   ├── 01-核心概念.md          ─ FIRE、复利、资产配置、风险
│   ├── 02-实践方法.md          ─ 定投、再平衡、保险、税务
│   ├── 03-学习路径.md          ─ 从入门到精通课程大纲
│   ├── 04-评估体系.md          ─ 知识检验与阶段测验
│   ├── 99-来源文献.md          ─ 书籍/论文/文章来源
│   └── _inbox/                 ─ 原始收集暂存区
├── .agents/                    ─ Agent 配置（私有）
│   ├── skills/
│   │   └── financial-tutor.md  ─ 理财导师教学法
│   ├── db/                     ─ 学习记录数据库（SQLite）
│   │   ├── schema.sql          ─ 表结构定义
│   │   └── init_db.py          ─ 初始化数据库
│   ├── workflows/              ─ 工作流脚本
│   │   └── study-log.py        ─ 学习记录 CLI
│   └── profile.md              ─ 用户画像（gitignored）
├── index.html                  ─ Docsify 入口
├── _sidebar.md                 ─ 网站导航
├── .nojekyll                   ─ 禁用 Jekyll
├── scripts/                    ─ [Phase 2] 数据管道
└── README.md
```

## 知识库内容

| 模块 | 适合谁 | 内容 |
|------|--------|------|
| 核心概念 | 初学者 | FIRE、复利、资产配置、风险、72 法则 |
| 实践方法 | 有基础 | 定投策略、再平衡、保险配置、税务优化 |
| 学习路径 | 所有人 | 12 课系统课程，从入门到精通 |
| 评估体系 | 学习者 | 阶段测验 + 知识检验 |

## 快速开始

```bash
# 1. 建立学习画像
cp .agents/profile.example.md .agents/profile.md
# 填写学习目标、当前知识水平

# 2. 开始学习
# 直接对话 AI Agent，或访问知识库网站
```

## 使用

### 学习记录

```bash
# 初始化数据库（首次）
python3 .agents/db/init_db.py

# 记录一次学习
python3 .agents/workflows/study-log.py log --activity 概念学习 --duration 30 --detail "复利公式与 72 法则"

# 查看今日 / 近 7 天 / 累计统计
python3 .agents/workflows/study-log.py today
python3 .agents/workflows/study-log.py week
python3 .agents/workflows/study-log.py stats
```

活动分类建议：`概念学习` / `案例分析` / `实操演练` / `复盘检验`

## 学习路径

参见 [knowledge/03-学习路径.md](knowledge/03-学习路径.md)

```
初级（第 1-6 课）→ 基础认知：复利、风险、指数基金、定投
中级（第 7-12 课）→ 核心方法：再平衡、保险、FIRE、税务
高级（专题）        → 实战优化：资产配置进阶、个股分析、投资哲学
```

## 设计原则

- **学习优先** — 先建立认知，再动手操作
- **隐私优先** — 所有个人数据本地存储
- **来源可追溯** — 每条知识标注来源，支持深入学习
