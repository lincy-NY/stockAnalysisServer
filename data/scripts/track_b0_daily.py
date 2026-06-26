#!/usr/bin/env python3
"""
B0日线选股追踪脚本（统一表版）
追踪信号：
- s1: 跌破多空线（触发日期）
- s2: 短期线低于多空线（结束追踪，触发日期）
"""

import pymysql
from datetime import datetime
from mysql_config import DB_CONFIG


def get_pending_signals(conn):
    """获取近45日内待追踪的选股记录"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT id, ts_code, big_line, screen_date
        FROM stock_select_daily
        WHERE strategy = 'b0' AND is_track = 1
          AND screen_date >= DATE_SUB(CURDATE(), INTERVAL 45 DAY)
        ORDER BY screen_date DESC
    """)
    return cursor.fetchall()


def get_latest_daily_data(conn, ts_code):
    """获取股票最新交易数据"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT trade_date, close, low, short_line, big_line
        FROM stock_daily
        WHERE ts_code = %s
        ORDER BY trade_date DESC
        LIMIT 1
    """, (ts_code,))
    return cursor.fetchone()


def get_prev_signals(conn, relate_id):
    """获取上一次追踪记录的信号状态"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT s1, s2
        FROM stock_track_daily
        WHERE relate_id = %s
        ORDER BY track_date DESC
        LIMIT 1
    """, (relate_id,))
    return cursor.fetchone()


def update_track_record(conn, relate_id, ts_code):
    """更新追踪记录"""
    latest = get_latest_daily_data(conn, ts_code)
    if not latest:
        return None

    track_date = latest['trade_date']
    close = float(latest['close'])
    low = float(latest['low'])
    short_line = float(latest['short_line']) if latest['short_line'] else 0
    big_line = float(latest['big_line']) if latest['big_line'] else 0

    # 获取之前的信号状态
    prev = get_prev_signals(conn, relate_id)
    prev_s1 = prev['s1'] if prev else None
    prev_s2 = prev['s2'] if prev else None

    # 信号计算（只记录首次触发日期）
    s1 = prev_s1 or (track_date if close < big_line else None)
    s2 = prev_s2 or (track_date if short_line < big_line else None)

    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO stock_track_daily
            (relate_id, track_date, close, low, short_line, big_line, s1, s2)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (relate_id, track_date, close, low, short_line, big_line, s1, s2))
        conn.commit()
    except Exception as e:
        print(f"  插入追踪记录失败: {e}")
        return None

    return {
        'relate_id': relate_id,
        'ts_code': ts_code,
        'track_date': track_date,
        'close': close,
        's1': s1,
        's2': s2
    }


def end_tracking(conn, relate_id):
    """结束追踪"""
    cursor = conn.cursor()
    cursor.execute("UPDATE stock_select_daily SET is_track = 2 WHERE id = %s", (relate_id,))
    conn.commit()


def main():
    print("=" * 60)
    print(f"B0日线追踪更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    conn = pymysql.connect(**DB_CONFIG)

    signals = get_pending_signals(conn)
    print(f"待追踪记录: {len(signals)} 条")

    if not signals:
        print("无待追踪记录")
        conn.close()
        return

    tracked = 0
    ended = 0

    for sig in signals:
        relate_id = sig['id']
        ts_code = sig['ts_code']

        result = update_track_record(conn, relate_id, ts_code)
        if result:
            tracked += 1

            if result['s2']:
                end_tracking(conn, relate_id)
                ended += 1
                print(f"  {ts_code} 触发s2（短期线跌破多空线），结束追踪")

    conn.close()

    print()
    print(f"追踪完成: {tracked} 条，结束: {ended} 条")
    print("=" * 60)


if __name__ == '__main__':
    main()
