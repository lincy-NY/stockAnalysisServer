#!/usr/bin/env python3
"""
每日估值指标数据拉取（MySQL版）
从 tushare daily_basic 接口获取全市场数据：
PE/PB/股息率/总市值/流通市值/换手率/量比等
"""

import os
import sys
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pymysql
from mysql_config import DB_CONFIG

TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '7f67a9fe52856eda6d9ea19c2e492a2ca52266657ff55aaa3d399919')
DAYS_TO_FETCH = 3  # 回补天数


def to_mysql_val(val):
    """安全转换数值"""
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return None
    return float(val)


def fetch_daily_basic(pro, trade_date):
    """获取指定日期的全市场daily_basic数据"""
    fields = 'ts_code,trade_date,turnover_rate,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_mv,circ_mv'
    try:
        df = pro.daily_basic(trade_date=trade_date, fields=fields)
        return df
    except Exception as e:
        print(f"  API错误: {e}")
        return None


def save_to_mysql(conn, df, trade_date):
    """批量写入MySQL"""
    if df is None or len(df) == 0:
        return 0

    cursor = conn.cursor()
    rows = []
    for _, row in df.iterrows():
        rows.append((
            row['ts_code'],
            trade_date[:4] + '-' + trade_date[4:6] + '-' + trade_date[6:],
            to_mysql_val(row.get('pe')),
            to_mysql_val(row.get('pe_ttm')),
            to_mysql_val(row.get('pb')),
            to_mysql_val(row.get('ps')),
            to_mysql_val(row.get('ps_ttm')),
            to_mysql_val(row.get('dv_ratio')),
            to_mysql_val(row.get('dv_ttm')),
            to_mysql_val(row.get('total_mv')),
            to_mysql_val(row.get('circ_mv')),
            to_mysql_val(row.get('turnover_rate')),
            to_mysql_val(row.get('volume_ratio')),
        ))

    sql = """
        INSERT INTO stock_daily_basic
        (ts_code, trade_date, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm, total_mv, circ_mv, turnover_rate, volume_ratio)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            pe=VALUES(pe), pe_ttm=VALUES(pe_ttm),
            pb=VALUES(pb), ps=VALUES(ps), ps_ttm=VALUES(ps_ttm),
            dv_ratio=VALUES(dv_ratio), dv_ttm=VALUES(dv_ttm),
            total_mv=VALUES(total_mv), circ_mv=VALUES(circ_mv),
            turnover_rate=VALUES(turnover_rate), volume_ratio=VALUES(volume_ratio)
    """
    cursor.executemany(sql, rows)
    conn.commit()
    cursor.close()
    return len(rows)


def main():
    # 确定要获取的日期
    target_date = sys.argv[1] if len(sys.argv) > 1 else None

    if target_date:
        dates = [target_date.replace('-', '')]
    else:
        # 默认获取最近几天（含当天）
        today = datetime.now()
        dates = []
        d = today + timedelta(days=1)
        while len(dates) < DAYS_TO_FETCH:
            d = d - timedelta(days=1)
            if d.weekday() < 5:  # 跳过周末
                dates.append(d.strftime('%Y%m%d'))
        dates.sort()

    print("=" * 60)
    print(f"daily_basic 数据更新 - 待获取: {dates}")
    print("=" * 60)

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    conn = pymysql.connect(**DB_CONFIG)

    total = 0
    for trade_date in dates:
        print(f"\n获取 {trade_date}...", end=" ", flush=True)
        df = fetch_daily_basic(pro, trade_date)
        if df is not None and len(df) > 0:
            count = save_to_mysql(conn, df, trade_date)
            print(f"{count} 条 ✅")
            total += count
        else:
            print("无数据")

    conn.close()
    print(f"\n完成，共写入 {total} 条记录")


if __name__ == '__main__':
    main()
