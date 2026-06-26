#!/usr/bin/env python3
"""
B1点选股筛选脚本（MySQL版）
从MySQL读取数据，输出符合条件的股票
支持指定日期: python3 run_b1_screen_mysql.py 2026-04-21
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import pymysql
from mysql_config import DB_CONFIG, get_db_connection
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def get_stock_data(conn, ts_code, table='stock_daily', target_date=None):
    """从MySQL获取股票数据"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    if target_date:
        cursor.execute(f"""
            SELECT ts_code, trade_date, open, high, low, close, pre_close,
                   vol, amount, short_line, big_line, kdj_j
            FROM {table}
            WHERE ts_code = %s AND trade_date <= %s
            ORDER BY trade_date DESC
            LIMIT 150
        """, (ts_code, target_date))
    else:
        cursor.execute(f"""
            SELECT ts_code, trade_date, open, high, low, close, pre_close,
                   vol, amount, short_line, big_line, kdj_j
            FROM {table}
            WHERE ts_code = %s
            ORDER BY trade_date DESC
            LIMIT 150
        """, (ts_code,))

    rows = cursor.fetchall()
    if not rows:
        return None

    df = pd.DataFrame(rows)
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d').astype(int)

    for col in ['open', 'high', 'low', 'close', 'pre_close', 'vol', 'amount', 'short_line', 'big_line', 'kdj_j']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def _get_60d_stats(df, idx, lookback=60):
    """获取近N日的统计量：最高价、均量、均振幅"""
    prev = df.iloc[idx-lookback:idx]
    if len(prev) < lookback:
        return None, None, None
    high_n = prev['high'].max()
    avg_vol = prev['vol'].mean()
    avg_amp = ((prev['high'] - prev['low']) / prev['open']).mean()
    return high_n, avg_vol, avg_amp


def is_suspicious_volume_candle(df, idx, lookback=60):
    """
    检查单根K线是否为可疑放量K线（三类）：

    类型A - 高位放量长上影阴线（冲高回落，主力拉高出货）:
      1. close 在近N日 high 的 90% 以上（相对高点）
      2. vol ≥ 近N日均量 × 1.5（放量）
      3. 上影线 ≥ 当日振幅 × 50%（长上影）
      4. 阴线（close < open）

    类型B - 高位放量长上下影K线（多空激烈博弈）:
      1. close 在近N日 high 的 90% 以上
      2. vol ≥ 近N日均量 × 1.5
      3. 下影线 ≥ 当日振幅 × 50%（长下影）
      4. 振幅 ≥ 近N日均振幅 × 1.5（当天波动异常大）

    类型C - 放量大跌（不看位置）:
      1. vol ≥ 近N日均量 × 2.0
      2. 跌幅 ≥ 3%
    """
    if idx < lookback:
        return False

    row = df.iloc[idx]
    high_n, avg_vol, avg_amp = _get_60d_stats(df, idx, lookback)

    if pd.isna(avg_vol) or avg_vol == 0 or pd.isna(avg_amp) or avg_amp == 0:
        return False

    close = row['close']
    open_p = row['open']
    high = row['high']
    low = row['low']
    vol = row['vol']
    amp = (high - low) / open_p

    # 基础计算
    near_top = close >= high_n * 0.90          # 相对高点
    high_vol_15 = vol >= avg_vol * 1.5         # 放量(1.5倍)
    high_vol_20 = vol >= avg_vol * 2.0         # 大幅放量(2倍)
    is_bearish = close < open_p                # 阴线
    body = abs(close - open_p)
    upper_shadow = high - max(open_p, close)   # 上影线
    lower_shadow = min(open_p, close) - low    # 下影线
    large_amp = amp >= avg_amp * 1.5           # 振幅异常
    drop_pct = (open_p - close) / open_p       # 跌幅

    # 类型A：高位 + 放量 + 长上影 + 阴线
    if near_top and high_vol_15 and is_bearish:
        if amp > 0 and upper_shadow / amp >= 0.5:
            return True

    # 类型B：高位 + 放量 + 长下影 + 大振幅
    if near_top and high_vol_15 and large_amp:
        if amp > 0 and lower_shadow / amp >= 0.5:
            return True

    # 类型C：放量大跌
    if high_vol_20 and drop_pct >= 0.03:
        return True

    return False


def has_suspicious_volume_in_period(df, days=60):
    """检查近N日内是否有可疑放量K线"""
    start_idx = max(0, len(df) - days)
    for idx in range(start_idx, len(df)):
        if is_suspicious_volume_candle(df, idx, lookback=60):
            return True
    return False


def is_shrinking_decline(df, days=5):
    """判断是否为缩量下跌"""
    if len(df) < days + 5:
        return False
    recent = df.head(days)
    current_vol = recent.iloc[0]['vol']
    prev_avg_vol = df.iloc[days:days+5]['vol'].mean()
    if pd.isna(prev_avg_vol) or prev_avg_vol == 0:
        return False
    vol_shrinking = current_vol < prev_avg_vol * 0.8
    price_declining = recent.iloc[0]['close'] < recent.iloc[-1]['close']
    bearish_count = (recent['close'] < recent['open']).sum()
    mostly_bearish = bearish_count >= days * 0.5
    return vol_shrinking and price_declining and mostly_bearish


def screen_stock(conn, ts_code, table='stock_daily', target_date=None):
    """筛选单只股票"""
    df = get_stock_data(conn, ts_code, table, target_date)
    if df is None or len(df) < 120:
        return None

    latest = df.iloc[0]

    # B1条件检查
    if pd.isna(latest['kdj_j']) or latest['kdj_j'] >= 10:
        return None
    if pd.isna(latest['short_line']) or latest['close'] >= latest['short_line']:
        return None
    if pd.isna(latest['big_line']) or latest['close'] <= latest['big_line']:
        return None
    if has_suspicious_volume_in_period(df, days=60):
        return None
    if not is_shrinking_decline(df, days=5):
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
    # 行业
    cursor.execute(f"SELECT ts_code, industry FROM stock_info WHERE ts_code IN ({placeholders})", codes)
    industry_map = {r['ts_code']: r['industry'] for r in cursor.fetchall()}
    # 最新估值
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
        r['total_mv_yi'] = round(mv / 10000, 0) if mv else None  # 万→亿
    return results


def get_all_stock_codes(conn):
    """获取所有有近期交易数据的股票代码（排除退市/长期停牌）"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT ts_code FROM stock_daily
        WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
        ORDER BY ts_code
    """)
    return [row[0] for row in cursor.fetchall()]


def main():
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    screen_date = target_date or datetime.now().strftime('%Y-%m-%d')

    print("=" * 60)
    print(f"B1点选股筛选(MySQL) - 目标日期: {screen_date}")
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

    results = sorted(results, key=lambda x: x['kdj_j'])

    if results:
        print(f"\n✅ 共找到 {len(results)} 只符合条件的B1点股票:\n")
        print(f"{'序号':<4} {'代码':<12} {'收盘价':>8} {'J值':>8} {'距短期%':>8} {'距多空%':>8}")
        print("-" * 52)

        for i, r in enumerate(results[:30], 1):
            print(f"{i:<4} {r['code']:<12} {r['close']:>8.2f} {r['kdj_j']:>8.2f} "
                  f"{r['dist_short']:>7.2f}% {r['dist_big']:>7.2f}%")

        if len(results) > 30:
            print(f"... 还有 {len(results) - 30} 只")

        today = screen_date
        today_fmt = screen_date.replace('-', '')

        cursor = conn.cursor()
        for r in results:
            trade_date = str(r['date'])
            trade_date_fmt = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            sql = '''
                INSERT IGNORE INTO stock_select_daily
                (strategy, screen_date, ts_code, trade_date, close, low_price, big_line, short_line, kdj_j, dist_pct, dist_short, vol, amount)
                VALUES ('b1', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (
                today, r['code'], trade_date_fmt,
                r['close'], r['low'], r['big_line'], r['short_line'], r['kdj_j'],
                r['dist_big'], r['dist_short'], r['vol'], r['amount']
            ))
        conn.commit()
        cursor.close()
        print(f"\n💾 结果已保存到统一表 stock_select_daily (b1)")

        # 批量附加行业和估值数据
        results = enrich_results(conn, results)

        output_file = OUTPUT_DIR / f'b1_result_{today_fmt}.xlsx'
        df_result = pd.DataFrame(results)
        export_cols = ['code', 'industry', 'close', 'kdj_j', 'pe_ttm', 'pb', 'dv', 'total_mv_yi',
                       'dist_short', 'dist_big', 'vol', 'amount', 'short_line', 'big_line', 'low']
        df_result = df_result[[c for c in export_cols if c in df_result.columns]]
        df_result.to_excel(output_file, index=False, sheet_name='B1日线选股')
        print(f"📁 完整结果已保存至: {output_file}")
        print(f"\n附件：")
        print(f"<qqmedia>{output_file}</qqmedia>")
    else:
        print("\n❌ 未找到符合条件的股票")

    conn.close()
    return results


if __name__ == '__main__':
    main()
