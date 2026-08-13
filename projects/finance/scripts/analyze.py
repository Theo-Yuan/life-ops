#!/usr/bin/env python3
"""
⚠️ PHASE 2 — 当前项目处于「学习阶段」，此脚本暂不活跃。
   等你掌握了理财投资的基础知识后，再启用数据追踪功能。
   参考 README.md 中的项目定位。

数据分析脚本 — 从 SQLite 读取数据生成财务分析报告。

用法:
    python scripts/analyze.py                        # 完整财务报告
    python scripts/analyze.py --overview             # 资产概览
    python scripts/analyze.py --spending             # 支出分析
    python scripts/analyze.py --budget               # 预算执行
    python scripts/analyze.py --portfolio            # 投资组合
    python scripts/analyze.py --net-worth            # 净值趋势
    python scripts/analyze.py --returns              # 收益分析
    python scripts/analyze.py --advice               # 仅建议
"""

import argparse
import os
import sqlite3
from typing import Optional
from datetime import datetime
from pathlib import Path


DB_PATH = os.getenv("DB_PATH", ".agents/db/finance.db")


def get_connection() -> Optional[sqlite3.Connection]:
    if not Path(DB_PATH).exists():
        print(f"[!] 数据库不存在: {DB_PATH}")
        print("    请先运行 python scripts/sync.py 初始化数据库")
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def report_overview(conn: sqlite3.Connection):
    print("=" * 50)
    print("📊 资产概览")
    print("=" * 50)

    accounts = conn.execute(
        "SELECT type, COUNT(*) as cnt FROM accounts WHERE closed_date IS NULL GROUP BY type"
    ).fetchall()
    if accounts:
        print("\n账户分布:")
        for a in accounts:
            print(f"  {a['type']}: {a['cnt']} 个")
    else:
        print("\n  暂无账户数据")

    latest_snapshot = conn.execute(
        "SELECT * FROM net_worth_snapshots ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if latest_snapshot:
        print(f"\n最新净值 ({latest_snapshot['date']}):")
        print(f"  总资产: {latest_snapshot['total_assets']:,.2f}")
        print(f"  总负债: {latest_snapshot['total_liabilities']:,.2f}")
        print(f"  净资产: {latest_snapshot['net_worth']:,.2f}")
    else:
        print("\n  暂无净值数据（运行 sync.py --snapshot 生成）")


def report_spending(conn: sqlite3.Connection):
    print("\n" + "=" * 50)
    print("💳 支出分析")
    print("=" * 50)

    this_month = datetime.now().strftime("%Y-%m")
    rows = conn.execute(
        """
        SELECT category, SUM(amount) as total, COUNT(*) as cnt
        FROM transactions
        WHERE type = 'expense' AND strftime('%Y-%m', date) = ?
        GROUP BY category
        ORDER BY total ASC
        """,
        (this_month,),
    ).fetchall()

    if rows:
        total = sum(abs(r["total"]) for r in rows)
        print(f"\n本月 ({this_month}) 支出: {total:,.2f} 元\n")
        for r in rows:
            pct = abs(r["total"]) / total * 100 if total > 0 else 0
            bar = "█" * int(pct / 5)
            print(f"  {r['category']:15s} {abs(r['total']):>10.2f} ({pct:5.1f}%) {bar}")
    else:
        print(f"\n  本月 ({this_month}) 暂无支出记录")


def report_budget(conn: sqlite3.Connection):
    print("\n" + "=" * 50)
    print("🎯 预算执行")
    print("=" * 50)

    this_month = datetime.now().strftime("%Y%m")
    budgets = conn.execute(
        "SELECT * FROM budgets WHERE month = ? OR (period = 'yearly' AND year = ?)",
        (int(this_month), datetime.now().year),
    ).fetchall()

    if not budgets:
        print("\n  暂无预算数据")
        print("  设置预算: sync.py --set-budget <category> <amount> --period monthly")
        return

    for b in budgets:
        spent = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE type='expense' AND category = ? AND strftime('%Y-%m', date) = ?",
            (b["category"], this_month[:4] + "-" + this_month[4:]),
        ).fetchone()
        spent_amt = abs(spent["total"])
        pct = spent_amt / b["amount"] * 100 if b["amount"] > 0 else 0
        status = "✓" if pct <= 100 else "⚠️"
        print(f"  {b['category']:15s} 预算 {b['amount']:>8.2f}  已用 {spent_amt:>8.2f} ({pct:5.1f}%) {status}")


def report_portfolio(conn: sqlite3.Connection):
    print("\n" + "=" * 50)
    print("📈 投资组合")
    print("=" * 50)

    holdings = conn.execute(
        """
        SELECT h.*, a.name as account_name
        FROM holdings h
        LEFT JOIN accounts a ON h.account_id = a.id
        ORDER BY h.type, h.symbol
        """
    ).fetchall()

    if not holdings:
        print("\n  暂无持仓数据")
        return

    total_cost = 0
    for h in holdings:
        cost = h["shares"] * h["cost_basis"]
        total_cost += cost
        print(f"\n  {h['name']} ({h['symbol']})")
        print(f"    类型: {h['type']:10s}  数量: {h['shares']:>10.4f}")
        print(f"    成本价: {h['cost_basis']:>10.2f}  成本: {cost:>12.2f}")

    print(f"\n  总投资成本: {total_cost:,.2f} 元")
    print("  (当前市值需通过行情数据计算，运行 sync.py 导入价格)")


def report_net_worth(conn: sqlite3.Connection):
    print("\n" + "=" * 50)
    print("📈 净值趋势")
    print("=" * 50)

    snapshots = conn.execute(
        "SELECT * FROM net_worth_snapshots ORDER BY date ASC LIMIT 60"
    ).fetchall()

    if not snapshots:
        print("\n  暂无净值快照数据")
        print("  运行 sync.py --snapshot 定期生成净值快照")
        return

    print(f"\n  共 {len(snapshots)} 个快照")
    first = snapshots[0]
    last = snapshots[-1]
    growth = last["net_worth"] - first["net_worth"]
    growth_pct = (growth / first["net_worth"] * 100) if first["net_worth"] != 0 else 0
    print(f"  期间: {first['date']} → {last['date']}")
    print(f"  净资产: {first['net_worth']:,.2f} → {last['net_worth']:,.2f}")
    print(f"  增长: {growth:+,.2f} ({growth_pct:+.2f}%)")

    print("\n  最近 5 个快照:")
    for s in snapshots[-5:]:
        print(f"    {s['date']}  资产 {s['total_assets']:>12.2f}  负债 {s['total_liabilities']:>12.2f}  净值 {s['net_worth']:>12.2f}")


def main():
    parser = argparse.ArgumentParser(description="财务分析报告")
    parser.add_argument("--overview", action="store_true", help="资产概览")
    parser.add_argument("--spending", action="store_true", help="支出分析")
    parser.add_argument("--budget", action="store_true", help="预算执行")
    parser.add_argument("--portfolio", action="store_true", help="投资组合")
    parser.add_argument("--net-worth", action="store_true", help="净值趋势")
    parser.add_argument("--advice", action="store_true", help="仅显示建议")

    args = parser.parse_args()

    conn = get_connection()
    if conn is None:
        return

    has_args = any([args.overview, args.spending, args.budget, args.portfolio, args.net_worth, args.advice])

    if not has_args or args.overview:
        report_overview(conn)
    if not has_args or args.spending:
        report_spending(conn)
    if not has_args or args.budget:
        report_budget(conn)
    if not has_args or args.portfolio:
        report_portfolio(conn)
    if not has_args or args.net_worth:
        report_net_worth(conn)

    if not has_args or args.advice:
        print("\n" + "=" * 50)
        print("💡 建议")
        print("=" * 50)
        print("\n  1. 确保每周同步一次交易数据")
        print("  2. 每月生成净值快照，追踪长期趋势")
        print("  3. 定期检查预算执行情况，调整不合理预算")
        print("  4. 每季度做一次资产再平衡")
        print("\n  (个性化建议需结合 profile.md 和知识库生成)")

    conn.close()


if __name__ == "__main__":
    main()
