#!/usr/bin/env python3
"""
股票周线数据更新（MySQL版）- 批量+多线程模式
- 按交易日批量获取全市场周线数据
- 多线程并行计算技术指标
- 数据先落库，再并行算指标
"""

import os
import sys
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import pymysql
from mysql_config import DB_CONFIG

TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '7f67a9fe52856eda6d9ea19c2e492a2ca52266657ff55aaa3d399919')
WEEKS_TO_FETCH = 4
LOOKBACK_WEEKS = 60  # 指标计算回看周数（MA114需要至少114周）
INDICATOR_WORKERS = 8


def init_tushare():
    ts.set_token(TUSHARE_TOKEN)
    return ts.pro_api()


def to_mysql_val(val):
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return None
    return float(val)


def get_recent_week_endings():
    """获取最近N周的周五日期（周线数据的trade_date）"""
    today = datetime.now()
    # 往前退到最近的周五
    d = today
    while d.weekday() != 4:  # 4=Friday
        d -= timedelta(days=1)
    # 收集最近N个周五
    fridays = []
    for _ in range(WEEKS_TO_FETCH):
        fridays.append(d.strftime('%Y%m%d'))
        d -= timedelta(weeks=1)
    fridays.sort()
    return fridays


def fetch_and_save(pro):
    """按交易日批量获取全市场周线数据并落库"""
    week_dates = get_recent_week_endings()
    print(f"待获取周数: {len(week_dates)} 周")
    print(f"日期: {week_dates}")

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    updated_codes = set()

    for trade_date in week_dates:
        print(f"  获取 {trade_date}...", end=" ", flush=True)
        try:
            df = pro.weekly(trade_date=trade_date,
                            fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount')
        except Exception as e:
            print(f"错误: {e}")
            continue

        if df is None or len(df) == 0:
            print("无数据")
            continue

        print(f"{len(df)} 条", end=" → ", flush=True)

        rows = []
        for _, row in df.iterrows():
            td = str(int(row['trade_date'])) if isinstance(row['trade_date'], float) else str(row['trade_date'])
            fmt = f"{td[:4]}-{td[4:6]}-{td[6:]}" if len(td) == 8 else td
            rows.append((
                row['ts_code'], fmt,
                to_mysql_val(row['open']), to_mysql_val(row['high']),
                to_mysql_val(row['low']), to_mysql_val(row['close']),
                to_mysql_val(row['pre_close']), to_mysql_val(row['change']),
                to_mysql_val(row['pct_chg']), to_mysql_val(row['vol']),
                to_mysql_val(row['amount']), None, None, None, None, None, None, None
            ))
            updated_codes.add(row['ts_code'])

        sql = """INSERT INTO stock_weekly
            (ts_code, trade_date, open, high, low, close, pre_close,
             change_val, pct_chg, vol, amount, short_line, big_line, kdj_j, brick_value, macd_dif, macd_dea, macd_bar)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
             open=VALUES(open), high=VALUES(high), low=VALUES(low), close=VALUES(close),
             pre_close=VALUES(pre_close), change_val=VALUES(change_val), pct_chg=VALUES(pct_chg),
             vol=VALUES(vol), amount=VALUES(amount)
        """
        for i in range(0, len(rows), 2000):
            cursor.executemany(sql, rows[i:i+2000])
        conn.commit()
        print(f"已落库 {len(rows)} 条")

    conn.close()
    return list(updated_codes)


def calc_one_stock(ts_code):
    """计算单只股票的周线技术指标（线程安全）"""
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cur.execute("""
            SELECT trade_date, open, high, low, close, short_line
            FROM stock_weekly WHERE ts_code=%s
            ORDER BY trade_date DESC LIMIT %s
        """, (ts_code, LOOKBACK_WEEKS))
        rows = cur.fetchall()

        if len(rows) < 28:
            return

        df = pd.DataFrame(rows)
        df = df.sort_values('trade_date', ascending=True).reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # short_line = EMA(EMA(Close, 10), 10)
        df['short_line'] = df['close'].ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()

        # big_line = (MA14 + MA28 + MA57 + MA114) / 4
        df['big_line'] = (df['close'].rolling(14).mean() +
                          df['close'].rolling(28).mean() +
                          df['close'].rolling(57).mean() +
                          df['close'].rolling(114).mean()) / 4

        # KDJ
        low_n = df['low'].rolling(9).min()
        high_n = df['high'].rolling(9).max()
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        k_vals, d_vals = [], []
        pk, pd_ = 50.0, 50.0
        for i in range(len(df)):
            if pd.isna(rsv.iloc[i]):
                k_vals.append(np.nan)
                d_vals.append(np.nan)
            else:
                k = pk * 2 / 3 + rsv.iloc[i] / 3
                d = pd_ * 2 / 3 + k / 3
                k_vals.append(k)
                d_vals.append(d)
                pk, pd_ = k, d
        df['kdj_j'] = 3 * pd.Series(k_vals) - 2 * pd.Series(d_vals)

        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd_dif'] = ema12 - ema26
        df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
        df['macd_bar'] = (df['macd_dif'] - df['macd_dea']) * 2

        # 只更新指标为NULL的行
        upd_cur = conn.cursor()
        for _, row in df.iterrows():
            if pd.isna(row.get('short_line')):
                continue
            upd_cur.execute("""
                UPDATE stock_weekly SET short_line=%s, big_line=%s, kdj_j=%s,
                    macd_dif=%s, macd_dea=%s, macd_bar=%s
                WHERE ts_code=%s AND trade_date=%s AND short_line IS NULL
            """, (
                to_mysql_val(row['short_line']),
                to_mysql_val(row['big_line']),
                to_mysql_val(row['kdj_j']),
                to_mysql_val(row.get('macd_dif')),
                to_mysql_val(row.get('macd_dea')),
                to_mysql_val(row.get('macd_bar')),
                ts_code, row['trade_date']
            ))
        conn.commit()
    finally:
        conn.close()


def calc_indicators_parallel(ts_codes):
    """多线程并行计算技术指标"""
    total = len(ts_codes)
    print(f"需计算指标: {total} 只股票（{INDICATOR_WORKERS}线程并行）")

    done = 0
    with ThreadPoolExecutor(max_workers=INDICATOR_WORKERS) as executor:
        futures = {executor.submit(calc_one_stock, code): code for code in ts_codes}
        for future in as_completed(futures):
            done += 1
            if done % 500 == 0:
                print(f"  进度: {done}/{total}")
            try:
                future.result()
            except Exception:
                pass


def main():
    print("=" * 60)
    print(f"股票周线数据更新 - 批量+多线程模式")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    pro = init_tushare()

    # 步骤1: 批量获取+落库
    print("\n【步骤1】按日期批量获取全市场周线数据...")
    updated_codes = fetch_and_save(pro)
    print(f"\n  本次更新 {len(updated_codes)} 只股票")

    # 步骤2: 多线程计算指标
    print(f"\n【步骤2】多线程计算技术指标（{INDICATOR_WORKERS}线程）...")
    calc_indicators_parallel(updated_codes)

    print()
    print("=" * 60)
    print(f"完成！更新 {len(updated_codes)} 只股票")
    print("=" * 60)


if __name__ == '__main__':
    main()
