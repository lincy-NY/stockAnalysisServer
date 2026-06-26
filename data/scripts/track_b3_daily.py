#!/usr/bin/env python3
"""
B3日线追踪脚本
- 查出近250日内is_track=1的B3选股结果（从stock_select_daily）
- 计算信号s2/s3/sm1，触发时记录日期
- 触发任一信号或超过250天则结束追踪
"""

import pymysql
from datetime import datetime, timedelta
from mysql_config import DB_CONFIG

TRACK_DAYS = 250


def get_pending_tracks(conn):
    """获取待追踪的B3选股记录"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT r.id, r.ts_code, r.close as buy_close, r.big_line, r.screen_date
        FROM stock_select_daily r
        WHERE r.strategy = 'b3'
          AND r.is_track = 1
          AND r.screen_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY r.screen_date DESC
    """, (TRACK_DAYS,))
    return cursor.fetchall()


def get_existing_signals(conn, relate_id):
    """获取已触发的信号日期"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT s1, s2, s3, sm1 FROM stock_b1_daily_track
        WHERE relate_id = %s
        ORDER BY track_date DESC
        LIMIT 1
    """, (relate_id,))
    return cursor.fetchone()


def get_latest_data(conn, ts_code):
    """获取最新日线数据"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT trade_date, close, low, short_line, big_line, macd_dif, macd_bar
        FROM stock_daily WHERE ts_code = %s
        ORDER BY trade_date DESC LIMIT 1
    """, (ts_code,))
    return cursor.fetchone()


def main():
    print("=" * 60)
    print(f"B3日线追踪 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    conn = pymysql.connect(**DB_CONFIG)
    tracks = get_pending_tracks(conn)
    print(f"待追踪: {len(tracks)} 条")

    tracked, ended = 0, 0

    for t in tracks:
        relate_id = t['id']
        ts_code = t['ts_code']
        old_big_line = float(t['big_line']) if t['big_line'] else 0

        latest = get_latest_data(conn, ts_code)
        if not latest:
            continue

        track_date = latest['trade_date']
        close = float(latest['close'])
        short_line = float(latest['short_line']) if latest['short_line'] else 0
        big_line = float(latest['big_line']) if latest['big_line'] else 0
        macd_dif = float(latest['macd_dif']) if latest['macd_dif'] else 0
        macd_bar = float(latest['macd_bar']) if latest['macd_bar'] else 0

        # 获取已触发的信号
        existing = get_existing_signals(conn, relate_id)
        prev_s2 = existing['s2'] if existing else None
        prev_s3 = existing['s3'] if existing else None
        prev_sm1 = existing['sm1'] if existing else None

        # 计算信号（仅在首次触发时记录日期）
        s2 = track_date if (not prev_s2 and close < big_line) else prev_s2
        s3 = track_date if (not prev_s3 and short_line < big_line) else prev_s3
        sm1 = track_date if (not prev_sm1 and macd_bar < 0 and macd_dif < 0) else prev_sm1

        # 追踪窗口到期
        screen_date = t['screen_date']
        if hasattr(screen_date, 'strftime'):
            days_elapsed = (datetime.now().date() - screen_date).days
        else:
            days_elapsed = (datetime.now().date() - datetime.strptime(str(screen_date), '%Y-%m-%d').date()).days

        should_end = (s2 or s3 or sm1) is not None or days_elapsed >= TRACK_DAYS

        # 插入追踪记录
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stock_b1_daily_track
            (relate_id, track_date, close, low, short_line, big_line, target_price, s1, s2, s3, sm1)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (relate_id, track_date, close,
              float(latest['low']) if latest['low'] else 0,
              short_line, big_line, 0,
              None, s2, s3, sm1))
        conn.commit()
        tracked += 1

        if should_end:
            cursor.execute("UPDATE stock_select_daily SET is_track=2 WHERE id=%s", (relate_id,))
            conn.commit()
            ended += 1
            signals = []
            if s2: signals.append(f's2({s2})')
            if s3: signals.append(f's3({s3})')
            if sm1: signals.append(f'sm1({sm1})')
            reason = ','.join(signals) if signals else '到期'
            print(f"  ⚠️ {ts_code} {reason}，结束追踪")

    conn.close()
    print(f"\n追踪完成: 处理{tracked}条，结束{ended}条")
    print("=" * 60)


if __name__ == '__main__':
    main()
