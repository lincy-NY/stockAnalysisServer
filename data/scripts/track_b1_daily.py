#!/usr/bin/env python3
"""
B1日线选股追踪脚本（统一表版）
- 从stock_select_daily查出待追踪的B1选股
- 信号s1/s2/s3记录触发日期
- s3触发或45天到期则结束追踪
"""

import pymysql
from datetime import datetime, timedelta
from mysql_config import DB_CONFIG

TRACK_DAYS = 45


def get_pending_tracks(conn):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT r.id, r.ts_code, r.low_price, r.big_line, r.screen_date
        FROM stock_select_daily r
        WHERE r.strategy = 'b1' AND r.is_track = 1
          AND r.screen_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY r.screen_date DESC
    """, (TRACK_DAYS,))
    return cursor.fetchall()


def get_existing_signals(conn, relate_id):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT s1, s2, s3, sm1 FROM stock_track_daily
        WHERE relate_id = %s ORDER BY track_date DESC LIMIT 1
    """, (relate_id,))
    return cursor.fetchone()


def get_latest_data(conn, ts_code):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT trade_date, close, low, short_line, big_line
        FROM stock_daily WHERE ts_code = %s
        ORDER BY trade_date DESC LIMIT 1
    """, (ts_code,))
    return cursor.fetchone()


def main():
    print(f"B1日线追踪 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = pymysql.connect(**DB_CONFIG)
    tracks = get_pending_tracks(conn)
    print(f"待追踪: {len(tracks)} 条")

    tracked, ended = 0, 0

    for t in tracks:
        relate_id = t['id']
        ts_code = t['ts_code']
        low_price = float(t['low_price']) if t['low_price'] else 0
        old_big_line = float(t['big_line']) if t['big_line'] else 0

        latest = get_latest_data(conn, ts_code)
        if not latest:
            continue

        track_date = latest['trade_date']
        close = float(latest['close'])
        short_line = float(latest['short_line']) if latest['short_line'] else 0
        big_line = float(latest['big_line']) if latest['big_line'] else 0

        # 获取已触发信号
        existing = get_existing_signals(conn, relate_id)
        prev_s1 = existing['s1'] if existing else None
        prev_s2 = existing['s2'] if existing else None
        prev_s3 = existing['s3'] if existing else None
        prev_sm1 = existing['sm1'] if existing else None

        # 目标价 = 选股最低价 - 1%
        target_price = low_price * 0.99

        # 信号（首次触发记录日期）
        s1 = track_date if (not prev_s1 and close < target_price) else prev_s1
        s2 = track_date if (not prev_s2 and close < big_line) else prev_s2
        s3 = track_date if (not prev_s3 and short_line < big_line) else prev_s3

        # 到期检查
        screen_date = t['screen_date']
        if hasattr(screen_date, 'strftime'):
            days_elapsed = (datetime.now().date() - screen_date).days
        else:
            days_elapsed = (datetime.now().date() - datetime.strptime(str(screen_date), '%Y-%m-%d').date()).days

        should_end = s3 is not None or days_elapsed >= TRACK_DAYS

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stock_track_daily
            (relate_id, track_date, close, low, short_line, big_line, target_price, s1, s2, s3)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (relate_id, track_date, close, float(latest['low']) if latest['low'] else 0,
              short_line, big_line, target_price, s1, s2, s3))
        conn.commit()
        tracked += 1

        if should_end:
            cursor.execute("UPDATE stock_select_daily SET is_track=2 WHERE id=%s", (relate_id,))
            conn.commit()
            ended += 1
            signals = []
            if s1: signals.append(f's1({s1})')
            if s2: signals.append(f's2({s2})')
            if s3: signals.append(f's3({s3})')
            reason = ','.join(signals) if signals else '到期'
            print(f"  {ts_code} {reason}，结束追踪")

    conn.close()
    print(f"完成: 处理{tracked}条，结束{ended}条")


if __name__ == '__main__':
    main()
