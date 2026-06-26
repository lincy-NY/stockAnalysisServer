#!/usr/bin/env python3
"""
周线B1点选股筛选脚本（MySQL版）
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import pymysql
from mysql_config import DB_CONFIG
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def get_stock_data(conn, ts_code):
    """从MySQL获取周线数据"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT ts_code, trade_date, open, high, low, close, pre_close,
               vol, amount, short_line, big_line, kdj_j
        FROM stock_weekly
        WHERE ts_code = %s
        ORDER BY trade_date DESC
        LIMIT 150
    """, (ts_code,))
    
    rows = cursor.fetchall()
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d').astype(int)
    
    # 转换数值列为float
    for col in ['open', 'high', 'low', 'close', 'pre_close', 'vol', 'amount', 'short_line', 'big_line', 'kdj_j']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def is_top_huge_volume_bearish(df, idx, lookback=30, volume_threshold=2.0, top_pct=0.95):
    """判断是否为顶部放巨量阴线（周线用更短的lookback）"""
    if idx < lookback:
        return False
    row = df.iloc[idx]
    if row['close'] >= row['open']:
        return False
    high_n = df.iloc[idx-lookback:idx+1]['high'].max()
    if row['close'] < high_n * top_pct:
        return False
    avg_vol = df.iloc[idx-lookback:idx]['vol'].mean()
    if pd.isna(avg_vol) or avg_vol == 0:
        return False
    if row['vol'] < avg_vol * volume_threshold:
        return False
    return True


def has_top_huge_volume_in_period(df, days=30):
    """检查指定周数内是否有顶部放巨量阴线"""
    start_idx = max(0, len(df) - days)
    for idx in range(start_idx, len(df)):
        if is_top_huge_volume_bearish(df, idx):
            return True
    return False


def is_shrinking_decline(df, weeks=3):
    """判断是否为缩量下跌（周线用更短的周期）"""
    if len(df) < weeks + 3:
        return False
    recent = df.head(weeks)
    current_vol = recent.iloc[0]['vol']
    prev_avg_vol = df.iloc[weeks:weeks+3]['vol'].mean()
    if pd.isna(prev_avg_vol) or prev_avg_vol == 0:
        return False
    vol_shrinking = current_vol < prev_avg_vol * 0.8
    price_declining = recent.iloc[0]['close'] < recent.iloc[-1]['close']
    bearish_count = (recent['close'] < recent['open']).sum()
    mostly_bearish = bearish_count >= weeks * 0.5
    return vol_shrinking and price_declining and mostly_bearish


def screen_stock(conn, ts_code):
    """筛选单只股票"""
    df = get_stock_data(conn, ts_code)
    if df is None or len(df) < 60:
        return None
    
    latest = df.iloc[0]
    
    # B1条件检查
    if pd.isna(latest['kdj_j']) or latest['kdj_j'] >= 10:
        return None
    if pd.isna(latest['short_line']) or latest['close'] >= latest['short_line']:
        return None
    if pd.isna(latest['big_line']) or latest['close'] <= latest['big_line']:
        return None
    if has_top_huge_volume_in_period(df, days=30):
        return None
    if not is_shrinking_decline(df, weeks=3):
        return None
    
    dist_short = (latest['short_line'] - latest['close']) / latest['close'] * 100
    dist_big = (latest['close'] - latest['big_line']) / latest['close'] * 100
    
    return {
        'code': latest['ts_code'],
        'date': int(latest['trade_date']),
        'close': latest['close'],
        'low': latest['low'],
        'kdj_j': latest['kdj_j'],
        'short_line': latest['short_line'],
        'big_line': latest['big_line'],
        'vol': latest['vol'],
        'amount': latest['amount'],
        'dist_short': round(dist_short, 2),
        'dist_big': round(dist_big, 2)
    }


def enrich_results(conn, results):
    """批量查询行业和估值数据，附加到筛选结果"""
    if not results:
        return results
    codes = [r['code'] for r in results]
    placeholders = ','.join(['%s'] * len(codes))
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(f"SELECT ts_code, industry FROM stock_info WHERE ts_code IN ({placeholders})", codes)
    industry_map = {r['ts_code']: r['industry'] for r in cursor.fetchall()}
    cursor.execute(f"""
        SELECT ts_code, pe_ttm, pb, dv_ratio AS dv, total_mv
        FROM stock_daily_basic
        WHERE ts_code IN ({placeholders})
          AND trade_date = (SELECT MAX(trade_date) FROM stock_daily_basic WHERE ts_code IN ({placeholders}))
    """, codes + codes)
    basic_map = {r['ts_code']: r for r in cursor.fetchall()}
    cursor.close()
    for r in results:
        code = r['code']
        r['industry'] = industry_map.get(code, '')
        b = basic_map.get(code, {})
        r['pe_ttm'] = b.get('pe_ttm')
        r['pb'] = b.get('pb')
        r['dv'] = b.get('dv')
        mv = b.get('total_mv')
        r['total_mv_yi'] = round(mv / 10000, 0) if mv else None
    return results


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
    print(f"周线B1点选股筛选(MySQL) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    
    results = sorted(results, key=lambda x: x['kdj_j'])
    
    if results:
        print(f"\n✅ 共找到 {len(results)} 只符合条件的周线B1点股票:\n")
        print(f"{'序号':<4} {'代码':<12} {'收盘价':>8} {'J值':>8} {'距短期%':>8} {'距多空%':>8}")
        print("-" * 52)
        
        for i, r in enumerate(results[:30], 1):
            print(f"{i:<4} {r['code']:<12} {r['close']:>8.2f} {r['kdj_j']:>8.2f} "
                  f"{r['dist_short']:>7.2f}% {r['dist_big']:>7.2f}%")
        
        if len(results) > 30:
            print(f"... 还有 {len(results) - 30} 只")
        
        # 保存结果到MySQL
        today = datetime.now().strftime('%Y-%m-%d')
        today_fmt = datetime.now().strftime('%Y%m%d')
        
        cursor = conn.cursor()
        for r in results:
            trade_date = str(r['date'])
            trade_date_fmt = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            
            sql = '''
                INSERT IGNORE INTO stock_select_weekly
                (strategy, screen_date, ts_code, trade_date, close, low_price, kdj_j, short_line, big_line, dist_pct, dist_short, vol, amount)
                VALUES ('b1', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (
                today, r['code'], trade_date_fmt,
                r['close'], r['low'], r['kdj_j'], r['short_line'], r['big_line'],
                r['dist_short'], r['dist_big'], r['vol'], r['amount']
            ))
        conn.commit()
        cursor.close()
        print(f"\n💾 结果已保存到数据库表 stock_select_weekly")

        # 批量附加行业和估值数据
        results = enrich_results(conn, results)

        # 保存Excel文件
        output_file = OUTPUT_DIR / f'b1_weekly_result_{today_fmt}.xlsx'
        df_result = pd.DataFrame(results)
        export_cols = ['code', 'industry', 'close', 'kdj_j', 'pe_ttm', 'pb', 'dv', 'total_mv_yi',
                       'dist_short', 'dist_big', 'vol', 'amount', 'short_line', 'big_line', 'low']
        df_result = df_result[[c for c in export_cols if c in df_result.columns]]
        df_result.to_excel(output_file, index=False, sheet_name='B1周线选股')
        print(f"📁 完整结果已保存至: {output_file}")
        print(f"\n附件：")
        print(f"<qqmedia>{output_file}</qqmedia>")
    else:
        print("\n❌ 未找到符合条件的股票")
    
    conn.close()
    return results


if __name__ == '__main__':
    main()
