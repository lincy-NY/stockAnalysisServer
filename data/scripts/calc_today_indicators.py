#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量更新今日指标（short_line, big_line, kdj_j, brick_value）
只处理当日新增数据，不重算历史
"""
import pandas as pd
import numpy as np
import pymysql
from mysql_config import DB_CONFIG
import sys

def sma(data, period, weight=1):
    """通达信SMA递归公式"""
    result = np.zeros(len(data))
    vals = data.values
    result[0] = vals[0]
    for i in range(1, len(vals)):
        result[i] = (weight * vals[i] + (period - weight) * result[i-1]) / period
    return pd.Series(result, index=data.index)

def calc_indicators(df):
    """计算全部指标"""
    h, l, c = df['high'], df['low'], df['close']

    # short_line = EMA(EMA(CLOSE,10),10)
    short_line = c.ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()

    # big_line = (MA14+MA28+MA57+MA114)/4
    big_line = (c.rolling(14).mean() + c.rolling(28).mean() +
                c.rolling(57).mean() + c.rolling(114).mean()) / 4

    # KDJ J值
    llv9 = l.rolling(9).min()
    hhv9 = h.rolling(9).max()
    rsv = (c - llv9) / (hhv9 - llv9).replace(0, np.nan) * 100
    rsv = rsv.fillna(50)
    k = pd.Series(50.0, index=c.index)
    d = pd.Series(50.0, index=c.index)
    for i in range(1, len(c)):
        k.iloc[i] = 2/3 * k.iloc[i-1] + 1/3 * rsv.iloc[i]
        d.iloc[i] = 2/3 * d.iloc[i-1] + 1/3 * k.iloc[i]
    kdj_j = 3 * k - 2 * d

    # 砖型图
    hhv4 = h.rolling(4).max()
    llv4 = l.rolling(4).min()
    denom = (hhv4 - llv4).replace(0, np.nan)
    var1a = ((hhv4 - c) / denom * 100 - 90).fillna(0)
    var2a = sma(var1a, 4, 1) + 100
    var3a = ((c - llv4) / denom * 100).fillna(0)
    var4a = sma(var3a, 6, 1)
    var5a = sma(var4a, 6, 1) + 100
    brick_value = np.where(var5a - var2a > 4, var5a - var2a - 4, 0)

    return {
        'short_line': short_line,
        'big_line': big_line,
        'kdj_j': kdj_j,
        'brick_value': pd.Series(brick_value, index=df.index)
    }

def v(val):
    if pd.isna(val) or np.isinf(val):
        return None
    return float(val)

def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else None

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 确定需要更新的日期
    if target_date:
        check_date = target_date
    else:
        cursor.execute("SELECT MAX(trade_date) FROM stock_daily")
        check_date = str(cursor.fetchone()[0])

    # 找出今天指标为NULL的股票
    cursor.execute("""
        SELECT DISTINCT ts_code FROM stock_daily
        WHERE trade_date = %s AND (short_line IS NULL OR brick_value IS NULL)
    """, (check_date,))
    stocks = [r[0] for r in cursor.fetchall()]

    if not stocks:
        print(f"✅ {check_date} 所有指标已计算完毕")
        conn.close()
        return

    print(f"📊 {check_date} 需更新 {len(stocks)} 只股票的指标")

    for i, ts_code in enumerate(stocks):
        df = pd.read_sql(
            "SELECT trade_date, high, low, close FROM stock_daily WHERE ts_code=%s AND trade_date <= %s ORDER BY trade_date DESC LIMIT 120",
            conn, params=[ts_code, check_date])
        df = df.sort_values('trade_date').reset_index(drop=True)

        if len(df) < 60:
            continue

        indicators = calc_indicators(df)

        # 只更新最后一天（今天）
        last_idx = len(df) - 1
        last_date = df.iloc[last_idx]['trade_date']

        cursor.execute("""
            UPDATE stock_daily SET short_line=%s, big_line=%s, kdj_j=%s, brick_value=%s
            WHERE ts_code=%s AND trade_date=%s
        """, (
            v(indicators['short_line'].iloc[last_idx]),
            v(indicators['big_line'].iloc[last_idx]),
            v(indicators['kdj_j'].iloc[last_idx]),
            v(indicators['brick_value'].iloc[last_idx]),
            ts_code, last_date
        ))

        if (i + 1) % 500 == 0:
            conn.commit()
            print(f"  [{i+1}/{len(stocks)}]")

    conn.commit()
    print(f"✅ 完成！更新了 {len(stocks)} 只股票的今日指标")
    conn.close()

if __name__ == "__main__":
    main()
