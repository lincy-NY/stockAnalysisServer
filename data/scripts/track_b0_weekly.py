#!/usr/bin/env python3
"""
B0周线选股追踪脚本（统一表版）
"""

import pymysql
from datetime import datetime
from mysql_config import DB_CONFIG


def get_pending_signals(conn):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT id, ts_code, screen_date
        FROM stock_select_weekly
        WHERE strategy = 'b0' AND is_track = 1
          AND screen_date >= DATE_SUB(CURDATE(), INTERVAL 45 DAY)
        ORDER BY screen_date DESC
    """)
    return cursor.fetchall()


def get_latest_weekly_data(conn, ts_code):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT trade_date, close, low, short_line, big_line
        FROM stock_weekly
        WHERE ts_code = %s
        ORDER BY trade_date DESC
        LIMIT 1
    """, (ts_code,))
    return cursor.fetchone()


def get_prev_signals(conn, relate_id):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT s1, s2
        FROM stock_track_weekly
        WHERE relate_id = %s
        ORDER BY track_date DESC
        LIMIT 1
    """, (relate_id,))
    return cursor.fetchone()


def update_track_record(conn, relate_id, ts_code):
    latest = get_latest_weekly_data(conn, ts_code)
    if not latest:
        return None

    track_date = latest['trade_date']
    close = float(latest['close'])
    low = float(latest['low'])
    short_line = float(latest['short_line']) if latest['short_line'] else 0
    big_line = float(latest['big_line']) if latest['big_line'] else 0

    prev = get_prev_signals(conn, relate_id)
    prev_s1 = prev['s1'] if prev else None
    prev_s2 = prev['s2'] if prev else None

    s1 = prev_s1 or (track_date if close < big_line else None)
    s2 = prev_s2 or (track_date if short_line < big_line else None)

    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO stock_track_weekly
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
        's1': s1,
        's2': s2
    }


def end_tracking(conn, relate_id):
    cursor = conn.cursor()
    cursor.execute("UPDATE stock_select_weekly SET is_track = 2 WHERE id = %s", (relate_id,))
    conn.commit()


def main():
    print(f"B0周线追踪 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
                print(f"  {ts_code} 触发s2，结束追踪")

    conn.close()
    print(f"完成: 处理{tracked}条，结束{ended}条")


if __name__ == '__main__':
    main()
