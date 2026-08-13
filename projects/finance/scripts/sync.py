#!/usr/bin/env python3
"""
⚠️ PHASE 2 — 当前项目处于「学习阶段」，此脚本暂不活跃。
   等你掌握了理财投资的基础知识后，再启用数据追踪功能。
   参考 README.md 中的项目定位。

数据同步脚本 — 从各数据源拉取财务数据到本地 SQLite。

用法:
    python scripts/sync.py                          # 全量同步
    python scripts/sync.py --snapshot               # 生成净值快照
    python scripts/sync.py --csv <file> --platform alipay   # 导入支付宝CSV
    python scripts/sync.py --add-expense <params>   # 手动录入支出
    python scripts/sync.py --add-income <params>    # 手动录入收入
    python scripts/sync.py --add-holding <params>   # 添加持仓
    python scripts/sync.py --add-trade <params>     # 添加交易记录
    python scripts/sync.py --set-budget <params>    # 设置预算
"""

import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = os.getenv("DB_PATH", ".agents/db/finance.db")


def get_connection() -> sqlite3.Connection:
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            currency TEXT DEFAULT 'CNY',
            institution TEXT,
            tags TEXT,
            opened_date TEXT,
            closed_date TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'CNY',
            description TEXT,
            tags TEXT,
            counterparty TEXT,
            reconciled INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );

        CREATE TABLE IF NOT EXISTS net_worth_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_assets REAL NOT NULL,
            total_liabilities REAL NOT NULL,
            net_worth REAL NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(date)
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            period TEXT NOT NULL,
            amount REAL NOT NULL,
            month INTEGER,
            year INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            currency TEXT DEFAULT 'CNY',
            shares REAL NOT NULL,
            cost_basis REAL NOT NULL,
            account_id INTEGER,
            opened_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );

        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holding_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            shares REAL NOT NULL,
            price REAL NOT NULL,
            fees REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (holding_id) REFERENCES holdings(id)
        );

        CREATE TABLE IF NOT EXISTS market_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            price REAL NOT NULL,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(symbol, date)
        );
    """)
    conn.commit()


def cmd_snapshot(conn: sqlite3.Connection):
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type IN ('cash','deposit','investment','crypto','property') THEN 1 ELSE 0 END), 0) as accts,
            0 as total_assets,
            0 as total_liabilities
        FROM accounts WHERE closed_date IS NULL
    """).fetchone()
    print(f"[TODO] 净值快照: {today}")
    print("    请先在 accounts 表中填入账户余额，或通过 --csv 导入")


def cmd_import_csv(conn: sqlite3.Connection, filepath: str, platform: str):
    print(f"[TODO] 导入 {platform} CSV: {filepath}")
    print("    解析逻辑待实现 — 不同平台（支付宝/微信/银行）格式不同")


def main():
    parser = argparse.ArgumentParser(description="财务数据同步工具")
    parser.add_argument("--snapshot", action="store_true", help="生成净值快照")
    parser.add_argument("--csv", type=str, help="导入 CSV 文件")
    parser.add_argument("--platform", type=str, choices=["alipay", "wechat", "eastmoney"], help="CSV 来源平台")
    parser.add_argument("--add-expense", nargs=3, metavar=("CATEGORY", "AMOUNT", "NOTE"), help="手动录入支出")
    parser.add_argument("--add-income", nargs=3, metavar=("CATEGORY", "AMOUNT", "NOTE"), help="手动录入收入")

    args = parser.parse_args()

    conn = get_connection()
    init_db(conn)

    if args.snapshot:
        cmd_snapshot(conn)
    elif args.csv:
        cmd_import_csv(conn, args.csv, args.platform or "unknown")
    elif args.add_expense:
        category, amount, note = args.add_expense
        conn.execute(
            "INSERT INTO transactions (date, type, category, amount, description) VALUES (?, 'expense', ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d"), category, -abs(float(amount)), note),
        )
        conn.commit()
        print(f"[✓] 已记录支出: {category} {-abs(float(amount))}元 — {note}")
    elif args.add_income:
        category, amount, note = args.add_income
        conn.execute(
            "INSERT INTO transactions (date, type, category, amount, description) VALUES (?, 'income', ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d"), category, abs(float(amount)), note),
        )
        conn.commit()
        print(f"[✓] 已记录收入: {category} {abs(float(amount))}元 — {note}")
    else:
        print("同步工具已就绪。使用 --help 查看用法。")
        print(f"数据库路径: {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    main()
