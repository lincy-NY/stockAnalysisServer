"""
数据库操作模块 - 统一表架构（4张表）
- stock_select_daily: 日线选股
- stock_select_weekly: 周线选股
- stock_track_daily: 日线追踪
- stock_track_weekly: 周线追踪
"""
import pymysql
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from config import DB_CONFIG


@contextmanager
def get_db():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def query_one(sql, params=None):
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql, params)
        return cursor.fetchone()


def query_all(sql, params=None):
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql, params)
        return cursor.fetchall()


# ============ 统计相关 ============

def get_dashboard_stats():
    today = date.today().strftime('%Y-%m-%d')
    base = query_one("""
        SELECT
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b0' AND screen_date = %s) as b0_daily_count,
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b0' AND screen_date >= DATE_SUB(%s, INTERVAL 7 DAY)) as b0_weekly_count,
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b1' AND screen_date = %s) as b1_daily_count,
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b1' AND screen_date >= DATE_SUB(%s, INTERVAL 7 DAY)) as b1_weekly_count,
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b2' AND screen_date = %s) as b2_daily_count,
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b0' AND is_track = 1) as b0_tracking,
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b1' AND is_track = 1) as b1_tracking,
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b0' AND screen_date = %s) as b0_signals,
            (SELECT COUNT(*) FROM stock_select_daily WHERE strategy='b1' AND screen_date = %s) as b1_signals
    """, (today, today, today, today, today, today, today))
    return base


# ============ 选股结果 ============

def get_screen_results(strategy, period, screen_date=None):
    if period == 'daily':
        return _get_daily_results(strategy, screen_date)
    else:
        return _get_weekly_results(strategy, screen_date)


def _get_daily_results(strategy, screen_date=None):
    if screen_date:
        sql = """
            SELECT s.id, s.screen_date, s.ts_code, s.trade_date, s.close, s.low_price,
                   s.big_line, s.short_line, s.kdj_j, s.brick_value,
                   s.dist_pct, s.dist_short, s.vol, s.amount, s.is_track, s.created_at,
                   i.name as stock_name
            FROM stock_select_daily s
            LEFT JOIN stock_info i ON s.ts_code = i.ts_code
            WHERE s.strategy = %s AND s.screen_date = %s
            ORDER BY s.close DESC
        """
        return query_all(sql, (strategy, screen_date))
    else:
        sql = """
            SELECT s.id, s.screen_date, s.ts_code, s.trade_date, s.close, s.low_price,
                   s.big_line, s.short_line, s.kdj_j, s.brick_value,
                   s.dist_pct, s.dist_short, s.vol, s.amount, s.is_track, s.created_at,
                   i.name as stock_name
            FROM stock_select_daily s
            LEFT JOIN stock_info i ON s.ts_code = i.ts_code
            WHERE s.strategy = %s
              AND s.screen_date = (SELECT MAX(screen_date) FROM stock_select_daily WHERE strategy = %s)
            ORDER BY s.close DESC
        """
        return query_all(sql, (strategy, strategy))


def _get_weekly_results(strategy, screen_date=None):
    kdj_col = 's.kdj_j,' if strategy == 'b1' else ''
    if screen_date:
        sql = f"""
            SELECT s.id, s.screen_date, s.ts_code, s.trade_date, s.close, s.low_price,
                   s.short_line, s.big_line, {kdj_col} s.vol, s.amount, s.is_track, s.created_at,
                   i.name as stock_name
            FROM stock_select_weekly s
            LEFT JOIN stock_info i ON s.ts_code = i.ts_code
            WHERE s.strategy = %s AND s.screen_date = %s
            ORDER BY s.close DESC
        """
        return query_all(sql, (strategy, screen_date))
    else:
        sql = f"""
            SELECT s.id, s.screen_date, s.ts_code, s.trade_date, s.close, s.low_price,
                   s.short_line, s.big_line, {kdj_col} s.vol, s.amount, s.is_track, s.created_at,
                   i.name as stock_name
            FROM stock_select_weekly s
            LEFT JOIN stock_info i ON s.ts_code = i.ts_code
            WHERE s.strategy = %s
              AND s.screen_date = (SELECT MAX(screen_date) FROM stock_select_weekly WHERE strategy = %s)
            ORDER BY s.close DESC
        """
        return query_all(sql, (strategy, strategy))


def get_screen_dates(strategy, period, limit=500):
    table = 'stock_select_daily' if period == 'daily' else 'stock_select_weekly'
    results = query_all(f"""
        SELECT DISTINCT screen_date FROM {table}
        WHERE strategy = %s
        ORDER BY screen_date DESC LIMIT %s
    """, (strategy, limit))
    return [str(r['screen_date']) for r in results]


# ============ 追踪相关 ============

def get_tracking_list(strategy, period):
    track_table = 'stock_track_daily' if period == 'daily' else 'stock_track_weekly'
    select_table = 'stock_select_daily' if period == 'daily' else 'stock_select_weekly'
    s3_col = ', t.s3' if strategy == 'b1' else ''

    sql = f"""
        SELECT
            s.id, s.screen_date, s.ts_code, s.trade_date, s.close, s.low_price,
            s.short_line, s.big_line, s.kdj_j, s.brick_value,
            s.dist_pct, s.dist_short, s.vol, s.amount, s.is_track,
            t.track_date, t.close as track_close, t.s1, t.s2,
            i.name as stock_name {s3_col}
        FROM {select_table} s
        LEFT JOIN {track_table} t ON s.id = t.relate_id
            AND t.track_date = (SELECT MAX(track_date) FROM {track_table} WHERE relate_id = s.id)
        LEFT JOIN stock_info i ON s.ts_code = i.ts_code
        WHERE s.strategy = %s AND s.is_track = 1
          AND s.screen_date >= DATE_SUB(CURDATE(), INTERVAL 45 DAY)
        ORDER BY s.screen_date DESC
    """
    return query_all(sql, (strategy,))


def get_track_history(strategy, period, relate_id):
    track_table = 'stock_track_daily' if period == 'daily' else 'stock_track_weekly'
    s3_col = ', s3, sm1' if strategy == 'b1' else ', s3, sm1'

    sql = f"""
        SELECT id, relate_id, track_date, close, low, short_line, big_line, target_price, s1, s2 {s3_col}
        FROM {track_table}
        WHERE relate_id = %s
        ORDER BY track_date DESC
    """
    return query_all(sql, (relate_id,))


# ============ K线数据 ============

def get_stock_kline(ts_code, period='daily', days=120):
    table = f'stock_{period}'
    sql = f"""
        SELECT trade_date, open, high, low, close, vol, amount,
               short_line, big_line, kdj_j, brick_value
        FROM {table}
        WHERE ts_code = %s
        ORDER BY trade_date DESC
        LIMIT %s
    """
    return query_all(sql, (ts_code, days))


def get_stock_info(ts_code):
    return query_one("""
        SELECT ts_code, symbol, name, area, industry, list_date
        FROM stock_info WHERE ts_code = %s
    """, (ts_code,))


# ============ 历史统计 ============

def get_signal_stats(days=30):
    sql = """
        SELECT
            track_date,
            SUM(CASE WHEN s1 IS NOT NULL THEN 1 ELSE 0 END) as s1_count,
            SUM(CASE WHEN s2 IS NOT NULL THEN 1 ELSE 0 END) as s2_count,
            SUM(CASE WHEN s3 IS NOT NULL THEN 1 ELSE 0 END) as s3_count,
            COUNT(*) as total
        FROM (
            SELECT td.track_date, td.s1, td.s2, NULL as s3
            FROM stock_track_daily td
            JOIN stock_select_daily sd ON td.relate_id = sd.id
            WHERE sd.strategy = 'b0' AND td.track_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            UNION ALL
            SELECT td.track_date, td.s1, td.s2, td.s3
            FROM stock_track_daily td
            JOIN stock_select_daily sd ON td.relate_id = sd.id
            WHERE sd.strategy = 'b1' AND td.track_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ) t
        GROUP BY track_date
        ORDER BY track_date DESC
    """
    return query_all(sql, (days, days))


def get_signal_triggers(signal_type=None, strategy=None, signal_date=None):
    """查询信号触发详情，每条信号一行"""
    where_clauses_daily = []
    where_clauses_weekly = []
    params_daily = []
    params_weekly = []

    if strategy:
        where_clauses_daily.append('sd.strategy = %s')
        where_clauses_weekly.append('sd.strategy = %s')
        params_daily.append(strategy)
        params_weekly.append(strategy)
    if signal_date:
        where_clauses_daily.append('td.%s = %s')
        where_clauses_weekly.append('td.%s = %s')

    where_daily = ' AND '.join(where_clauses_daily) if where_clauses_daily else '1=1'
    where_weekly = ' AND '.join(where_clauses_weekly) if where_clauses_weekly else '1=1'

    signal_types = [signal_type] if signal_type else ['s1', 's2', 's3', 'sm1']

    parts = []
    all_params = []
    for st in signal_types:
        wd = where_daily
        ww = where_weekly
        pd = list(params_daily)
        pw = list(params_weekly)
        if signal_date:
            wd = wd.replace('td.%s = %s', f'td.{st} = %s')
            ww = ww.replace('td.%s = %s', f'td.{st} = %s')
            pd.append(signal_date)
            pw.append(signal_date)

        parts.append(f"""
        SELECT sd.ts_code, i.name AS stock_name, sd.screen_date,
               sd.strategy, '{st}' AS signal_type, td.{st} AS signal_date
        FROM stock_track_daily td
        JOIN stock_select_daily sd ON td.relate_id = sd.id
        LEFT JOIN stock_info i ON sd.ts_code = i.ts_code
        WHERE td.{st} IS NOT NULL AND {wd}
        """)
        all_params.extend(pd)

        parts.append(f"""
        SELECT sd.ts_code, i.name AS stock_name, sd.screen_date,
               sd.strategy, '{st}' AS signal_type, td.{st} AS signal_date
        FROM stock_track_weekly td
        JOIN stock_select_weekly sd ON td.relate_id = sd.id
        LEFT JOIN stock_info i ON sd.ts_code = i.ts_code
        WHERE td.{st} IS NOT NULL AND {ww}
        """)
        all_params.extend(pw)

    sql = f"""
        SELECT * FROM (
            {' UNION ALL '.join(parts)}
        ) t
        ORDER BY signal_date DESC, ts_code
        LIMIT 500
    """

    return query_all(sql, tuple(all_params))


def get_recent_signal_stats(days=2):
    """获取近N天的信号触发统计"""
    daily = query_all("""
        SELECT sd.strategy,
            SUM(CASE WHEN td.s1 IS NOT NULL THEN 1 ELSE 0 END) as s1_count,
            SUM(CASE WHEN td.s2 IS NOT NULL THEN 1 ELSE 0 END) as s2_count,
            SUM(CASE WHEN td.s3 IS NOT NULL THEN 1 ELSE 0 END) as s3_count,
            SUM(CASE WHEN td.sm1 IS NOT NULL THEN 1 ELSE 0 END) as sm1_count
        FROM stock_track_daily td
        JOIN stock_select_daily sd ON td.relate_id = sd.id
        WHERE td.track_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY sd.strategy
    """, (days,))

    weekly = query_all("""
        SELECT sd.strategy,
            SUM(CASE WHEN td.s1 IS NOT NULL THEN 1 ELSE 0 END) as s1_count,
            SUM(CASE WHEN td.s2 IS NOT NULL THEN 1 ELSE 0 END) as s2_count,
            SUM(CASE WHEN td.s3 IS NOT NULL THEN 1 ELSE 0 END) as s3_count,
            SUM(CASE WHEN td.sm1 IS NOT NULL THEN 1 ELSE 0 END) as sm1_count
        FROM stock_track_weekly td
        JOIN stock_select_weekly sd ON td.relate_id = sd.id
        WHERE td.track_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY sd.strategy
    """, (days,))

    return {'daily': daily, 'weekly': weekly}


def get_stock_screen_history(ts_code):
    """查询指定股票的所有选股历史（跨策略跨周期）"""
    daily_sql = """
        SELECT s.id, s.strategy, s.screen_date, s.ts_code, s.trade_date, s.close, s.low_price,
               s.big_line, s.short_line, s.kdj_j, s.brick_value,
               s.dist_pct, s.dist_short, s.vol, s.amount, s.is_track, s.created_at,
               i.name as stock_name, 'daily' as period
        FROM stock_select_daily s
        LEFT JOIN stock_info i ON s.ts_code = i.ts_code
        WHERE s.ts_code = %s
        ORDER BY s.screen_date DESC, s.strategy
    """
    
    weekly_sql = """
        SELECT s.id, s.strategy, s.screen_date, s.ts_code, s.trade_date, s.close, s.low_price,
               s.short_line, s.big_line, s.kdj_j,
               s.vol, s.amount, s.is_track, s.created_at,
               i.name as stock_name, 'weekly' as period
        FROM stock_select_weekly s
        LEFT JOIN stock_info i ON s.ts_code = i.ts_code
        WHERE s.ts_code = %s
        ORDER BY s.screen_date DESC, s.strategy
    """
    
    daily_results = list(query_all(daily_sql, (ts_code,)))
    weekly_results = list(query_all(weekly_sql, (ts_code,)))
    
    return daily_results + weekly_results
