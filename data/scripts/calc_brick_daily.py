#!/usr/bin/env python3
"""
增量计算最近几天的brick_value
只计算指定日期范围内的数据，避免全量计算
"""

import pandas as pd
import numpy as np
import pymysql
from datetime import datetime, timedelta
from mysql_config import DB_CONFIG

DAYS_TO_CALC = 5  # 计算最近N天的数据


def sma(data, period, weight=1):
    """通达信SMA递归公式: SMA(X,N,M) = (M*X + (N-M)*Y') / N"""
    result = np.zeros(len(data))
    vals = data.values
    result[0] = vals[0]
    for i in range(1, len(vals)):
        result[i] = (weight * vals[i] + (period - weight) * result[i-1]) / period
    return pd.Series(result, index=data.index)


def calculate_brick_value(df):
    """计算砖型图指标"""
    # VAR2A = SMA(CLOSE,6,1)
    var2a = sma(df['close'], 6, 1)

    # VAR3A = SMA(VAR2A,6,1)
    var3a = sma(var2a, 6, 1)

    # VAR4A = SMA(VAR3A,6,1)
    var4a = sma(var3a, 6, 1)

    # VAR5A = SMA(VAR4A,6,1)+100
    var5a = sma(var4a, 6, 1) + 100

    # 砖型图 = VAR5A-VAR2A, 当>4时取值
    var6a = var5a - var2a
    brick = np.where(var6a > 4, var6a - 4, 0)

    return brick


def main():
    """主函数"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 计算日期范围
    today = datetime.now()
    dates = []
    for i in range(DAYS_TO_CALC):
        d = today - timedelta(days=i)
        dates.append(d.strftime('%Y-%m-%d'))

    dates_str = "', '".join(dates)
    print(f"📊 计算 {DAYS_TO_CALC} 天的brick_value: {dates_str}")

    # 获取需要更新的股票代码（这些股票在指定日期范围内有brick_value为NULL的记录）
    query = f"""
        SELECT DISTINCT ts_code
        FROM stock_daily
        WHERE trade_date IN ('{dates_str}')
          AND brick_value IS NULL
    """
    cursor.execute(query)
    stocks = [row[0] for row in cursor.fetchall()]

    total_stocks = len(stocks)
    print(f"需处理 {total_stocks} 只股票")

    if total_stocks == 0:
        print("✅ 无需处理！")
        conn.close()
        return

    # 获取每个股票的历史数据（需要足够的历史数据来计算SMA）
    processed = 0
    updated = 0

    for ts_code in stocks:
        # 查询该股票的所有历史数据（按日期排序）
        query = """
            SELECT trade_date, close
            FROM stock_daily
            WHERE ts_code = %s
            ORDER BY trade_date ASC
        """
        df = pd.read_sql(query, conn, params=[ts_code])

        if len(df) < 20:  # 至少需要20天数据
            continue

        # 计算brick_value
        brick = calculate_brick_value(df)

        # 只更新指定日期范围内brick_value为NULL的记录
        upd_cursor = conn.cursor()
        for i, (_, row) in enumerate(df.iterrows()):
            trade_date = row['trade_date'].strftime('%Y-%m-%d') if hasattr(row['trade_date'], 'strftime') else str(row['trade_date'])

            # 只更新指定日期范围内的记录
            if trade_date not in dates:
                continue

            # 检查是否需要更新（brick_value为NULL）
            check_query = """
                SELECT brick_value FROM stock_daily
                WHERE ts_code = %s AND trade_date = %s
            """
            upd_cursor.execute(check_query, (ts_code, trade_date))
            result = upd_cursor.fetchone()

            if result and result[0] is None:
                update_query = """
                    UPDATE stock_daily
                    SET brick_value = %s
                    WHERE ts_code = %s AND trade_date = %s
                """
                upd_cursor.execute(update_query, (float(brick[i]) if not pd.isna(brick[i]) else None, ts_code, trade_date))
                updated += 1

        processed += 1

        # 每100只股票提交一次
        if processed % 100 == 0:
            conn.commit()
            print(f"进度: {processed}/{total_stocks} | 已更新 {updated} 条")

    # 提交所有更改
    conn.commit()
    conn.close()

    print(f"✅ 完成！处理了 {processed} 只股票，更新了 {updated} 条brick_value记录")


if __name__ == "__main__":
    main()