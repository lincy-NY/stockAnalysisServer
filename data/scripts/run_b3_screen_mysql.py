#!/usr/bin/env python3
"""
B3点选股筛选脚本
MACD趋势启动型：DIF上穿0轴 + 红柱 + 放量 + 趋势支持

条件：
1. DIF上穿0轴 — 当日macd_dif > 0 且前一日macd_dif <= 0
2. 红柱 — macd_bar > 0
3. 放量 — 当日成交量 > 前5日均量 × 1.5
4. 价格在多空线上方 — close > big_line
5. 趋势偏多 — short_line >= big_line
6. 流动性 — amount >= 1亿

用法: python3 run_b3_screen_mysql.py [日期]
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import pymysql
from mysql_config import DB_CONFIG
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def get_stock_data(conn, ts_code, target_date=None):
    """获取股票数据（含MACD），加载最近10天用于判断穿越"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    if target_date:
        cursor.execute("""
            SELECT ts_code, trade_date, open, high, low, close,
                   vol, amount, short_line, big_line, macd_dif, macd_dea, macd_bar
            FROM stock_daily
            WHERE ts_code = %s AND trade_date <= %s
            ORDER BY trade_date DESC
            LIMIT 10
        """, (ts_code, target_date))
    else:
        cursor.execute("""
            SELECT ts_code, trade_date, open, high, low, close,
                   vol, amount, short_line, big_line, macd_dif, macd_dea, macd_bar
            FROM stock_daily
            WHERE ts_code = %s
            ORDER BY trade_date DESC
            LIMIT 10
        """, (ts_code,))

    rows = cursor.fetchall()
    if not rows or len(rows) < 6:
        return None

    df = pd.DataFrame(rows)
    for col in ['open', 'high', 'low', 'close', 'vol', 'amount', 'short_line', 'big_line', 'macd_dif', 'macd_dea', 'macd_bar']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def screen_stock(conn, ts_code, target_date=None):
    """筛选单只股票"""
    df = get_stock_data(conn, ts_code, target_date)
    if df is None:
        return None

    latest = df.iloc[0]   # 当日
    prev = df.iloc[1]     # 前一日

    # 条件1: DIF上穿0轴
    if pd.isna(latest['macd_dif']) or pd.isna(prev['macd_dif']):
        return None
    if not (latest['macd_dif'] > 0 and prev['macd_dif'] <= 0):
        return None

    # 条件2: 红柱
    if pd.isna(latest['macd_bar']) or latest['macd_bar'] <= 0:
        return None

    # 条件3: 放量（前5日均量 × 1.5）
    if len(df) < 6:
        return None
    avg_vol_5 = df.iloc[1:6]['vol'].mean()
    if pd.isna(avg_vol_5) or avg_vol_5 == 0 or latest['vol'] <= avg_vol_5 * 1.5:
        return None

    # 条件4: 价格在多空线上方
    if pd.isna(latest['big_line']) or latest['close'] <= latest['big_line']:
        return None

    # 条件5: 趋势偏多
    if pd.isna(latest['short_line']) or latest['short_line'] < latest['big_line']:
        return None

    # 条件6: 流动性
    if pd.isna(latest['amount']) or latest['amount'] < 100000:
        return None

    dist_big = (latest['close'] - latest['big_line']) / latest['close'] * 100

    return {
        'code': latest['ts_code'],
        'date': latest['trade_date'],
        'close': latest['close'],
        'low': latest['low'],
        'short_line': latest['short_line'],
        'big_line': latest['big_line'],
        'macd_dif': latest['macd_dif'],
        'macd_dea': latest['macd_dea'],
        'macd_bar': latest['macd_bar'],
        'vol': latest['vol'],
        'amount': latest['amount'],
        'dist_big': round(dist_big, 2)
    }


def get_all_stock_codes(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT ts_code FROM stock_daily
        WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
        ORDER BY ts_code
    """)
    return [row[0] for row in cursor.fetchall()]


def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    screen_date = target_date or datetime.now().strftime('%Y-%m-%d')

    print("=" * 60)
    print(f"B3点选股筛选(MACD趋势启动型) - 目标日期: {screen_date}")
    print("=" * 60)

    conn = pymysql.connect(**DB_CONFIG)
    stock_codes = get_all_stock_codes(conn)
    total = len(stock_codes)
    print(f"扫描 {total} 只股票...", end=" ", flush=True)

    results = []
    for idx, ts_code in enumerate(stock_codes):
        result = screen_stock(conn, ts_code, target_date=target_date)
        if result:
            results.append(result)
        if (idx + 1) % 500 == 0:
            print(".", end="", flush=True)

    results = sorted(results, key=lambda x: x['macd_dif'])

    if results:
        print(f"\n✅ 共找到 {len(results)} 只B3点股票:\n")
        print(f"{'序号':<4} {'代码':<12} {'收盘价':>8} {'DIF':>8} {'DEA':>8} {'BAR':>8} {'放量比':>8}")
        print("-" * 60)
        for i, r in enumerate(results[:30], 1):
            print(f"{i:<4} {r['code']:<12} {r['close']:>8.2f} {r['macd_dif']:>8.4f} {r['macd_dea']:>8.4f} {r['macd_bar']:>8.4f}")
        if len(results) > 30:
            print(f"... 还有 {len(results) - 30} 只")

        cursor = conn.cursor()
        for r in results:
            trade_date = r['date']
            trade_date_fmt = trade_date.strftime('%Y-%m-%d') if hasattr(trade_date, 'strftime') else str(trade_date)
            sql = '''INSERT IGNORE INTO stock_select_daily
                (strategy, screen_date, ts_code, trade_date, close, low_price, big_line, short_line, kdj_j, dist_pct, dist_short, vol, amount)
                VALUES ('b3', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
            cursor.execute(sql, (
                screen_date, r['code'], trade_date_fmt,
                r['close'], r['low'], r['big_line'], r['short_line'], None,
                r['dist_big'], None, r['vol'], r['amount']
            ))
        conn.commit()
        cursor.close()
        print(f"\n💾 结果已保存到 stock_select_daily (b3)")

        output_file = OUTPUT_DIR / f'b3_result_{screen_date.replace("-", "")}.xlsx'
        pd.DataFrame(results).to_excel(output_file, index=False, sheet_name='B3日线选股')
        print(f"📁 {output_file}")
        print(f"<qqmedia>{output_file}</qqmedia>")
    else:
        print("\n❌ 未找到符合条件的股票")

    conn.close()


if __name__ == '__main__':
    main()
