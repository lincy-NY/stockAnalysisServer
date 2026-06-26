#!/usr/bin/env python3
"""
B2点选股筛选脚本（MySQL版）
策略：砖型图动量拐点(XG=1) + 收盘价高于多空线

砖型图公式：
  VAR1A = (HHV(HIGH,4)-CLOSE)/(HHV(HIGH,4)-LLV(LOW,4))*100-90
  VAR2A = SMA(VAR1A,4,1)+100
  VAR3A = (CLOSE-LLV(LOW,4))/(HHV(HIGH,4)-LLV(LOW,4))*100
  VAR4A = SMA(VAR3A,6,1)
  VAR5A = SMA(VAR4A,6,1)+100
  砖型图 = VAR5A-VAR2A, 当>4时显示

XG信号：前一天砖型图≤4或无变化，当天砖型图开始增长 → 动量由弱转强拐点

支持指定日期: python3 run_b2_screen_mysql.py 2026-04-21
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import pymysql
from mysql_config import DB_CONFIG
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def sma(data, period, weight=1):
    """通达信SMA递归公式: SMA(X,N,M) = (M*X + (N-M)*PREV) / N
    其中 M=weight, N=period"""
    vals = data.values if hasattr(data, 'values') else np.array(data, dtype=float)
    result = np.full(len(vals), np.nan)
    # 找到第一个非NaN的位置作为起点
    start = 0
    while start < len(vals) and np.isnan(vals[start]):
        start += 1
    if start >= len(vals):
        return pd.Series(result, index=data.index if hasattr(data, 'index') else None)
    result[start] = vals[start]
    for i in range(start + 1, len(vals)):
        if np.isnan(vals[i]):
            result[i] = result[i-1]
        else:
            result[i] = (weight * vals[i] + (period - weight) * result[i-1]) / period
    return pd.Series(result, index=data.index if hasattr(data, 'index') else None)


def get_stock_data(conn, ts_code, target_date=None):
    """从MySQL获取股票数据"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    if target_date:
        cursor.execute("""
            SELECT ts_code, trade_date, open, high, low, close, pre_close,
                   vol, amount, short_line, big_line, kdj_j
            FROM stock_daily
            WHERE ts_code = %s AND trade_date <= %s
            ORDER BY trade_date DESC
            LIMIT 150
        """, (ts_code, target_date))
    else:
        cursor.execute("""
            SELECT ts_code, trade_date, open, high, low, close, pre_close,
                   vol, amount, short_line, big_line, kdj_j
            FROM stock_daily
            WHERE ts_code = %s
            ORDER BY trade_date DESC
            LIMIT 150
        """, (ts_code,))

    rows = cursor.fetchall()
    if not rows or len(rows) < 20:
        return None

    df = pd.DataFrame(rows)
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d').astype(int)
    for col in ['open', 'high', 'low', 'close', 'pre_close', 'vol', 'amount', 'short_line', 'big_line', 'kdj_j']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def calc_brick_indicator(df):
    """计算砖型图动量指标，返回 (brick_series, xg_series)"""
    df = df.sort_values('trade_date', ascending=True).reset_index(drop=True)

    high = df['high']
    low = df['low']
    close = df['close']

    # VAR1A = (HHV(HIGH,4)-CLOSE)/(HHV(HIGH,4)-LLV(LOW,4))*100-90
    hhv4 = high.rolling(4).max()
    llv4 = low.rolling(4).min()
    range4 = hhv4 - llv4
    var1a = (hhv4 - close) / range4 * 100 - 90

    # VAR2A = SMA(VAR1A,4,1)+100
    var2a = sma(var1a, 4, 1) + 100

    # VAR3A = (CLOSE-LLV(LOW,4))/(HHV(HIGH,4)-LLV(LOW,4))*100
    var3a = (close - llv4) / range4 * 100

    # VAR4A = SMA(VAR3A,6,1)
    var4a = sma(var3a, 6, 1)

    # VAR5A = SMA(VAR4A,6,1)+100
    var5a = sma(var4a, 6, 1) + 100

    # 砖型图 = VAR5A-VAR2A, 当>4时取值
    var6a = var5a - var2a
    brick = np.where(var6a > 4, var6a - 4, 0)

    df['brick'] = brick
    df['var6a'] = var6a

    # AA = REF(砖型图,1)<砖型图 (砖型图在涨 = 红柱)
    brick_series = pd.Series(brick, index=df.index)
    brick_prev = brick_series.shift(1)
    df['AA'] = brick_prev < brick_series

    # BB = REF(砖型图,1)>砖型图 (砖型图在跌 = 绿柱)
    df['BB'] = brick_prev > brick_series

    # CC = REF(AA,1)=0 && AA=1 (从非涨转为涨 = 动量拐点)
    AA_prev = df['AA'].shift(1).fillna(False)
    df['CC'] = (~AA_prev) & df['AA']

    # XG = CC>0
    df['XG'] = df['CC']

    return df


def screen_stock(conn, ts_code, target_date=None):
    """筛选单只股票"""
    df = get_stock_data(conn, ts_code, target_date)
    if df is None or len(df) < 20:
        return None

    # 计算砖型图指标
    df = calc_brick_indicator(df)

    # calc_brick_indicator 按日期升序排列，最后一行是最新的
    latest = df.iloc[-1]

    # 条件1: XG信号 = 1（动量拐点）
    if not latest['XG']:
        return None

    # 条件1.5: 红砖长度 > 绿砖长度（当天砖型图增量 > 前一天减量）
    brick_vals = df['brick'].values
    red_len = brick_vals[-1] - brick_vals[-2]           # 红砖长度：当天-昨天
    green_len = abs(brick_vals[-2] - brick_vals[-3])    # 绿砖长度：昨天-前天（取绝对值）
    if red_len <= green_len:
        return None

    # 条件2: 收盘价 > 多空线（多头趋势）
    if pd.isna(latest['big_line']) or latest['close'] <= latest['big_line']:
        return None

    # 条件3: 短期线 > 多空线（短期线在多空线上方，多头排列）
    if pd.isna(latest['short_line']) or latest['short_line'] <= latest['big_line']:
        return None

    dist_big = (latest['close'] - latest['big_line']) / latest['big_line'] * 100
    dist_short = (latest['close'] - latest['short_line']) / latest['short_line'] * 100

    return {
        'code': latest['ts_code'],
        'date': int(latest['trade_date']),
        'close': latest['close'],
        'low': latest['low'],
        'big_line': latest['big_line'],
        'short_line': latest['short_line'],
        'brick': round(latest['brick'], 2),
        'var6a': round(latest['var6a'], 2),
        'vol': latest['vol'],
        'amount': latest['amount'],
        'dist_big': round(dist_big, 2),
        'dist_short': round(dist_short, 2)
    }


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
    print(f"B2点选股筛选(MySQL) - 目标日期: {screen_date}")
    print(f"策略: 砖型图动量拐点(XG=1) + 收盘价>多空线")
    print("=" * 60)

    conn = pymysql.connect(**DB_CONFIG)

    stock_codes = get_all_stock_codes(conn)
    total = len(stock_codes)
    print(f"扫描 {total} 只股票...", end=" ", flush=True)

    results = []
    for idx, ts_code in enumerate(stock_codes):
        try:
            result = screen_stock(conn, ts_code, target_date=target_date)
            if result:
                results.append(result)
        except Exception:
            pass
        if (idx + 1) % 500 == 0:
            print(".", end="", flush=True)

    results = sorted(results, key=lambda x: x['brick'], reverse=True)

    if results:
        print(f"\n✅ 共找到 {len(results)} 只符合条件的B2点股票:\n")
        print(f"{'序号':<4} {'代码':<12} {'收盘价':>8} {'砖型图':>8} {'距多空%':>8} {'距短期%':>8}")
        print("-" * 52)

        for i, r in enumerate(results[:30], 1):
            print(f"{i:<4} {r['code']:<12} {r['close']:>8.2f} {r['brick']:>8.2f} "
                  f"{r['dist_big']:>7.2f}% {r['dist_short']:>7.2f}%")

        if len(results) > 30:
            print(f"... 还有 {len(results) - 30} 只")

        today_fmt = screen_date.replace('-', '')

        cursor = conn.cursor()
        for r in results:
            trade_date = str(r['date'])
            trade_date_fmt = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            sql = '''
                INSERT IGNORE INTO stock_select_daily
                (strategy, screen_date, ts_code, trade_date, close, low_price, big_line, short_line, brick_value, dist_pct, dist_short, vol, amount)
                VALUES ('b2', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (
                screen_date, r['code'], trade_date_fmt,
                r['close'], r['low'], r['big_line'], r['short_line'], r['brick'],
                r['dist_big'], r['dist_short'], r['vol'], r['amount']
            ))
        conn.commit()
        cursor.close()
        print(f"\n💾 结果已保存到统一表 stock_select_daily (b2)")

        output_file = OUTPUT_DIR / f'b2_result_{today_fmt}.xlsx'
        df_result = pd.DataFrame(results)
        df_result.to_excel(output_file, index=False, sheet_name='B2日线选股')
        print(f"📁 完整结果已保存至: {output_file}")
        print(f"\n附件：")
        print(f"<qqmedia>{output_file}</qqmedia>")
    else:
        print("\n❌ 未找到符合条件的股票")

    conn.close()
    return results


if __name__ == '__main__':
    main()
