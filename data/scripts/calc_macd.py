#!/usr/bin/env python3
"""
MACD指标计算 - 全量版
DIF = EMA(Close, 12) - EMA(Close, 26)
DEA = EMA(DIF, 9)
MACD = (DIF - DEA) * 2
"""

import os, sys
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pymysql
import time
from mysql_config import DB_CONFIG

WORKERS = 8
TABLE = 'stock_daily'  # 改为 stock_weekly 则算周线


def to_mysql_val(val):
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return None
    return float(val)


def calc_one_stock(ts_code):
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute(f"SELECT COUNT(*) as cnt FROM {TABLE} WHERE ts_code=%s AND macd_dif IS NULL", (ts_code,))
        if cur.fetchone()['cnt'] == 0:
            return 0

        cur.execute(f"SELECT trade_date, close FROM {TABLE} WHERE ts_code=%s ORDER BY trade_date ASC", (ts_code,))
        rows = cur.fetchall()
        if len(rows) < 34:
            return 0

        df = pd.DataFrame(rows)
        df['close'] = pd.to_numeric(df['close'], errors='coerce')

        # MACD计算
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd_dif'] = ema12 - ema26
        df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
        df['macd_bar'] = (df['macd_dif'] - df['macd_dea']) * 2

        upd = conn.cursor()
        updated = 0
        for _, row in df.iterrows():
            if pd.isna(row['macd_dif']) or pd.isna(row['macd_dea']) or pd.isna(row['macd_bar']):
                continue
            upd.execute(f"""
                UPDATE {TABLE} SET macd_dif=%s, macd_dea=%s, macd_bar=%s
                WHERE ts_code=%s AND trade_date=%s AND macd_dif IS NULL
            """, (to_mysql_val(row['macd_dif']), to_mysql_val(row['macd_dea']),
                  to_mysql_val(row['macd_bar']), ts_code, row['trade_date']))
            if upd.rowcount > 0:
                updated += upd.rowcount
        conn.commit()
        return updated
    except Exception:
        conn.rollback()
        return 0
    finally:
        conn.close()


def main():
    print(f"MACD全量计算 - {TABLE}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(f"SELECT DISTINCT ts_code FROM {TABLE} WHERE macd_dif IS NULL")
    ts_codes = [r[0] for r in cur.fetchall()]
    conn.close()

    print(f"需计算: {len(ts_codes)} 只股票")
    if not ts_codes:
        print("无需计算！")
        return

    start = time.time()
    total_updated = 0
    done = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(calc_one_stock, c): c for c in ts_codes}
        for f in as_completed(futures):
            done += 1
            try:
                total_updated += f.result()
            except Exception:
                pass
            if done % 500 == 0 or done == len(ts_codes):
                elapsed = time.time() - start
                print(f"进度: {done}/{len(ts_codes)} | 已更新 {total_updated} 行 | {elapsed:.0f}s")
                sys.stdout.flush()

    print(f"\n完成！更新 {total_updated} 行，耗时 {time.time()-start:.0f}秒")


if __name__ == '__main__':
    main()
