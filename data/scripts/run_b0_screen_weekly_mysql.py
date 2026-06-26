#!/usr/bin/env python3
"""
B0点周线选股筛选脚本（MySQL版）
"""

import pandas as pd
import numpy as np
from datetime import datetime
import pymysql
from mysql_config import DB_CONFIG
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def get_stock_data(conn, ts_code):
    """从MySQL获取周线数据"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT ts_code, trade_date, open, high, low, close,
               vol, amount, short_line, big_line
        FROM stock_weekly
        WHERE ts_code = %s
        ORDER BY trade_date DESC
        LIMIT 10
    """, (ts_code,))
    
    rows = cursor.fetchall()
    if not rows or len(rows) < 2:
        return None
    
    df = pd.DataFrame(rows)
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d').astype(int)
    
    for col in ['open', 'high', 'low', 'close', 'vol', 'amount', 'short_line', 'big_line']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def screen_stock(conn, ts_code):
    """筛选单只股票"""
    df = get_stock_data(conn, ts_code)
    if df is None or len(df) < 2:
        return None
    
    df = df.sort_values('trade_date', ascending=True).reset_index(drop=True)
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 条件1: 收盘价 > big_line
    if pd.isna(latest['close']) or pd.isna(latest['big_line']):
        return None
    if latest['close'] <= latest['big_line']:
        return None
    
    # 条件2: 当日short_line上穿big_line
    if pd.isna(latest['short_line']) or pd.isna(prev['short_line']) or pd.isna(prev['big_line']):
        return None
    if not (latest['short_line'] > latest['big_line'] and prev['short_line'] <= prev['big_line']):
        return None
    
    return {
        'code': latest['ts_code'],
        'date': int(latest['trade_date']),
        'close': latest['close'],
        'low': latest['low'],
        'short_line': latest['short_line'],
        'big_line': latest['big_line'],
        'vol': latest['vol'],
        'amount': latest['amount']
    }


def get_all_stock_codes(conn):
    """获取所有有近期交易数据的股票代码（排除退市/长期停牌）"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT ts_code FROM stock_weekly
        WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 180 DAY)
        ORDER BY ts_code
    """)
    return [row[0] for row in cursor.fetchall()]


def main():
    print("=" * 60)
    print(f"B0点周线选股筛选(MySQL) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("条件: 收盘价>多空线 且 短期线上穿多空线")
    print("=" * 60)
    
    conn = pymysql.connect(**DB_CONFIG)
    
    stock_codes = get_all_stock_codes(conn)
    total = len(stock_codes)
    print(f"扫描 {total} 只股票...", end=" ", flush=True)
    
    results = []
    for idx, ts_code in enumerate(stock_codes):
        result = screen_stock(conn, ts_code)
        if result:
            results.append(result)
        
        if (idx + 1) % 500 == 0:
            print(".", end="", flush=True)
    
    print(" 完成!")
    
    results = sorted(results, key=lambda x: x['code'])
    
    if results:
        print(f"\n✅ 共找到 {len(results)} 只符合条件的B0点股票:\n")
        print(f"{'序号':<4} {'代码':<12} {'收盘价':>8} {'短期线':>10} {'多空线':>10}")
        print("-" * 48)
        
        for i, r in enumerate(results[:30], 1):
            print(f"{i:<4} {r['code']:<12} {r['close']:>8.2f} {r['short_line']:>10.3f} {r['big_line']:>10.3f}")
        
        if len(results) > 30:
            print(f"... 还有 {len(results) - 30} 只")
        
        today = datetime.now().strftime('%Y-%m-%d')
        today_fmt = datetime.now().strftime('%Y%m%d')
        
        cursor = conn.cursor()
        for r in results:
            trade_date = str(r['date'])
            trade_date_fmt = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            
            sql = '''
                INSERT IGNORE INTO stock_select_weekly
                (strategy, screen_date, ts_code, trade_date, close, low_price, short_line, big_line, vol, amount)
                VALUES ('b0', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (
                today, r['code'], trade_date_fmt,
                r['close'], r['low'], r['short_line'], r['big_line'], r['vol'], r['amount']
            ))
        conn.commit()
        print(f"\n💾 结果已保存到数据库表 stock_select_weekly")
        
        output_file = OUTPUT_DIR / f'b0_weekly_result_{today_fmt}.xlsx'
        df_result = pd.DataFrame(results)
        df_result.to_excel(output_file, index=False, sheet_name='B0周线选股')
        print(f"📁 完整结果已保存至: {output_file}")
        print(f"\n附件：")
        print(f"<qqmedia>{output_file}</qqmedia>")
    else:
        print("\n❌ 未找到符合条件的股票")
    
    conn.close()
    return results


if __name__ == '__main__':
    main()
