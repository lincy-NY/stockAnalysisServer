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


# ============ 交易管理 ============

def create_position(ts_code, stock_name, strategy, screen_date, buy_date, buy_price, buy_amount):
    """创建持仓（买入）"""
    buy_total = round(buy_price * buy_amount, 2)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 插入持仓记录
        cursor.execute("""
            INSERT INTO stock_position
            (ts_code, stock_name, strategy, screen_date, buy_date, buy_price, buy_amount, buy_total, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'holding')
        """, (ts_code, stock_name, strategy, screen_date, buy_date, buy_price, buy_amount, buy_total))
        position_id = cursor.lastrowid
        
        # 插入交易记录
        cursor.execute("""
            INSERT INTO stock_trade
            (position_id, ts_code, stock_name, trade_type, trade_date, trade_price, trade_amount, trade_total)
            VALUES (%s, %s, %s, 'buy', %s, %s, %s, %s)
        """, (position_id, ts_code, stock_name, buy_date, buy_price, buy_amount, buy_total))
        
        conn.commit()
        return position_id


def create_position_direct(ts_code, stock_name, buy_date, buy_price, buy_amount, notes=''):
    """直接创建持仓（不关联选股结果）"""
    buy_total = round(buy_price * buy_amount, 2)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 获取股票名称（如果没有提供）
        if not stock_name:
            stock = query_one("SELECT name FROM stock_info WHERE ts_code = %s", (ts_code,))
            if stock:
                stock_name = stock['name']
        
        # 插入持仓记录
        cursor.execute("""
            INSERT INTO stock_position
            (ts_code, stock_name, strategy, buy_date, buy_price, buy_amount, buy_total, status)
            VALUES (%s, %s, NULL, %s, %s, %s, %s, 'holding')
        """, (ts_code, stock_name, buy_date, buy_price, buy_amount, buy_total))
        position_id = cursor.lastrowid
        
        # 插入交易记录
        cursor.execute("""
            INSERT INTO stock_trade
            (position_id, ts_code, stock_name, trade_type, trade_date, trade_price, trade_amount, trade_total, notes)
            VALUES (%s, %s, %s, 'buy', %s, %s, %s, %s, %s)
        """, (position_id, ts_code, stock_name, buy_date, buy_price, buy_amount, buy_total, notes))
        
        conn.commit()
        return position_id


def get_position_list(status=None, strategy=None):
    """获取持仓列表"""
    sql = """
        SELECT id, ts_code, stock_name, strategy, screen_date, buy_date,
               buy_price, buy_amount, buy_total, current_price, current_value,
               profit_loss, profit_loss_pct, status, is_alert, created_at, updated_at
        FROM stock_position
        WHERE 1=1
    """
    params = []
    
    if status:
        sql += " AND status = %s"
        params.append(status)
    if strategy:
        sql += " AND strategy = %s"
        params.append(strategy)
    
    sql += " ORDER BY updated_at DESC"
    
    positions = query_all(sql, tuple(params))
    
    # 更新当前价格和盈亏
    for pos in positions:
        latest = query_one("""
            SELECT close FROM stock_daily
            WHERE ts_code = %s ORDER BY trade_date DESC LIMIT 1
        """, (pos['ts_code'],))
        
        if latest:
            current_price = float(latest['close'])
            current_value = round(current_price * pos['buy_amount'], 2)
            profit_loss = round(current_value - pos['buy_total'], 2)
            profit_loss_pct = round((profit_loss / pos['buy_total']) * 100, 2) if pos['buy_total'] > 0 else 0
            
            # 更新数据库
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE stock_position
                    SET current_price = %s, current_value = %s, profit_loss = %s, profit_loss_pct = %s
                    WHERE id = %s
                """, (current_price, current_value, profit_loss, profit_loss_pct, pos['id']))
                conn.commit()
            
            pos['current_price'] = current_price
            pos['current_value'] = current_value
            pos['profit_loss'] = profit_loss
            pos['profit_loss_pct'] = profit_loss_pct
    
    return positions


def get_position_detail(position_id):
    """获取持仓详情"""
    position = query_one("""
        SELECT * FROM stock_position WHERE id = %s
    """, (position_id,))
    
    if not position:
        return None
    
    # 获取交易记录
    trades = query_all("""
        SELECT * FROM stock_trade WHERE position_id = %s ORDER BY trade_date DESC
    """, (position_id,))
    
    # 获取提示记录
    alerts = query_all("""
        SELECT * FROM stock_alert WHERE position_id = %s ORDER BY created_at DESC
    """, (position_id,))
    
    return {
        'position': position,
        'trades': trades,
        'alerts': alerts
    }


def sell_position(position_id, sell_date, sell_price, sell_amount):
    """卖出持仓"""
    position = query_one("""
        SELECT * FROM stock_position WHERE id = %s
    """, (position_id,))
    
    if not position:
        raise ValueError('持仓不存在')
    
    if position['status'] != 'holding':
        raise ValueError('持仓状态不正确')
    
    if sell_amount > position['buy_amount']:
        raise ValueError('卖出数量超过持仓数量')
    
    sell_total = round(sell_price * sell_amount, 2)
    profit_loss = round(sell_total - (position['buy_price'] * sell_amount), 2)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 插入交易记录
        trade_type = 'sell' if sell_amount == position['buy_amount'] else 'sell_partial'
        cursor.execute("""
            INSERT INTO stock_trade
            (position_id, ts_code, stock_name, trade_type, trade_date, trade_price, trade_amount, trade_total, profit_loss)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (position_id, position['ts_code'], position['stock_name'], trade_type, sell_date, sell_price, sell_amount, sell_total, profit_loss))
        
        # 更新持仓状态
        new_status = 'sold' if sell_amount == position['buy_amount'] else 'partial_sold'
        cursor.execute("""
            UPDATE stock_position SET status = %s WHERE id = %s
        """, (new_status, position_id))
        
        conn.commit()
    
    return profit_loss


def get_unread_alert_count():
    """获取未读消息数量"""
    result = query_one("""
        SELECT COUNT(*) as count FROM stock_alert WHERE status = 'unread'
    """)
    return result['count']


def get_unread_alerts():
    """获取未读消息列表"""
    sql = """
        SELECT id, position_id, ts_code, stock_name, alert_type,
               alert_date, alert_price, trigger_desc, status, created_at
        FROM stock_alert
        WHERE status = 'unread'
        ORDER BY created_at DESC
        LIMIT 50
    """
    return query_all(sql)


def mark_alert_read(alert_id):
    """标记消息为已读"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE stock_alert SET status = 'read', read_at = NOW() WHERE id = %s
        """, (alert_id,))
        conn.commit()


def mark_all_alerts_read():
    """全部标记为已读"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE stock_alert SET status = 'read', read_at = NOW() WHERE status = 'unread'
        """)
        affected = cursor.rowcount
        conn.commit()
        return affected


def get_position_stats():
    """获取持仓统计"""
    positions = get_position_list(status='holding')
    
    if not positions:
        return {
            'holding_count': 0,
            'total_value': 0,
            'total_profit_loss': 0,
            'profit_loss_pct': 0,
            'unread_alerts': 0
        }
    
    total_value = sum(p['current_value'] for p in positions)
    total_profit_loss = sum(p['profit_loss'] for p in positions)
    total_cost = sum(p['buy_total'] for p in positions)
    profit_loss_pct = round((total_profit_loss / total_cost) * 100, 2) if total_cost > 0 else 0
    unread_alerts = get_unread_alert_count()
    
    return {
        'holding_count': len(positions),
        'total_value': round(total_value, 2),
        'total_profit_loss': round(total_profit_loss, 2),
        'profit_loss_pct': profit_loss_pct,
        'unread_alerts': unread_alerts
    }
