-- Finance Plan Database Schema
-- SQLite

CREATE TABLE study_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    activity TEXT NOT NULL,  -- 概念学习 / 案例分析 / 实操演练 / 复盘检验
    detail TEXT,             -- 具体学习内容（如 "复利公式与 72 法则"）
    notes TEXT
);
