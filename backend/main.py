"""
选股系统后端 API - 统一表架构
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from datetime import date
import pymysql

from config import DB_CONFIG

from auth import verify_password, create_access_token, get_current_user
from database import (
    get_dashboard_stats, get_screen_results, get_screen_dates,
    get_tracking_list, get_track_history, get_stock_kline,
    get_stock_info, get_signal_stats, query_all, query_one,
    get_signal_triggers, get_recent_signal_stats, get_stock_screen_history
)
from scheduler import init_scheduler, scheduler, TASKS, execute_task

app = FastAPI(
    title='选股系统 API',
    description='B0/B1/B2选股策略结果展示',
    version='2.0.0'
)

# 初始化定时任务调度器
init_scheduler(app)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# ============ 请求模型 ============

class LoginRequest(BaseModel):
    username: str
    password: str


# ============ 认证接口 ============

@app.post('/api/login')
def login(req: LoginRequest):
    """用户登录"""
    if not verify_password(req.password, req.username):
        raise HTTPException(status_code=401, detail='用户名或密码错误')
    
    token = create_access_token(req.username)
    return {
        'token': token,
        'username': req.username,
        'name': '管理员'
    }


@app.get('/api/me')
def get_me(username: str = Depends(get_current_user)):
    """获取当前用户信息"""
    return {'username': username, 'name': '管理员'}


# ============ 仪表盘接口 ============

@app.get('/api/dashboard/stats')
def dashboard_stats(username: str = Depends(get_current_user)):
    """获取仪表盘统计"""
    stats = get_dashboard_stats()
    return {
        'today': {
            'b0_daily': stats.get('b0_daily_count', 0),
            'b1_daily': stats.get('b1_daily_count', 0),
            'b2_daily': stats.get('b2_daily_count', 0),
            'b0_weekly': stats.get('b0_weekly_count', 0),
            'b1_weekly': stats.get('b1_weekly_count', 0)
        },
        'tracking': {
            'b0': stats.get('b0_tracking', 0),
            'b1': stats.get('b1_tracking', 0)
        },
        'signals': {
            'b0': stats.get('b0_signals', 0),
            'b1': stats.get('b1_signals', 0)
        }
    }


@app.get('/api/dashboard/signal-recent')
def dashboard_signal_recent(days: int = 2, username: str = Depends(get_current_user)):
    """获取近N天信号触发统计"""
    data = get_recent_signal_stats(days)
    return {'days': days, 'data': data}


# ============ 选股结果接口 ============

@app.get('/api/screen/{strategy}/{period}')
def screen_list(
    strategy: str, 
    period: str, 
    screen_date: Optional[str] = None,
    username: str = Depends(get_current_user)
):
    """
    获取选股结果 - 统一接口
    strategy: b0, b1, b2
    period: daily, weekly
    """
    if strategy not in ['b0', 'b1', 'b2'] or period not in ['daily', 'weekly']:
        raise HTTPException(status_code=400, detail='无效的策略或周期参数')
    
    if strategy == 'b2' and period != 'daily':
        raise HTTPException(status_code=400, detail='B2策略仅支持日线')
    
    results = get_screen_results(strategy, period, screen_date)
    
    for r in results:
        if r.get('trade_date'):
            r['trade_date'] = str(r['trade_date'])
        if r.get('screen_date'):
            r['screen_date'] = str(r['screen_date'])
    
    return {
        'strategy': strategy,
        'period': period,
        'screen_date': screen_date,
        'count': len(results),
        'data': results
    }


@app.get('/api/screen/{strategy}/{period}/dates')
def screen_dates(
    strategy: str, 
    period: str, 
    limit: int = 30,
    username: str = Depends(get_current_user)
):
    """获取有选股记录的日期列表"""
    if strategy not in ['b0', 'b1', 'b2'] or period not in ['daily', 'weekly']:
        raise HTTPException(status_code=400, detail='无效的策略或周期参数')
    
    if strategy == 'b2' and period != 'daily':
        raise HTTPException(status_code=400, detail='B2策略仅支持日线')
    
    dates = get_screen_dates(strategy, period, limit)
    return {'dates': dates}


@app.get('/api/screen/{strategy}/{period}/export')
def screen_export(
    strategy: str, 
    period: str,
    screen_date: Optional[str] = None,
    min_amount: Optional[float] = None,
    username: str = Depends(get_current_user)
):
    """
    导出选股结果 - txt格式（股票代码列表）
    strategy: b0, b1, b2
    period: daily, weekly
    screen_date: 选股日期（不指定则取最新）
    min_amount: 最小成交额过滤（单位：千元）
    """
    if strategy not in ['b0', 'b1', 'b2'] or period not in ['daily', 'weekly']:
        raise HTTPException(status_code=400, detail='无效的策略或周期参数')
    
    if strategy == 'b2' and period != 'daily':
        raise HTTPException(status_code=400, detail='B2策略仅支持日线')
    
    # 构建查询
    table = 'stock_select_daily' if period == 'daily' else 'stock_select_weekly'
    kdj_cols = ', kdj_j' if strategy == 'b1' and period == 'daily' else ''
    
    # 确定日期
    if screen_date:
        date_condition = f"AND s.screen_date = '{screen_date}'"
    else:
        date_condition = f"AND s.screen_date = (SELECT MAX(screen_date) FROM {table} WHERE strategy='{strategy}')"
    
    # 成交额过滤
    amount_condition = ''
    if min_amount and min_amount > 0:
        amount_condition = f'AND s.amount >= {min_amount}'
    
    sql = f"""
        SELECT DISTINCT s.ts_code
        FROM {table} s
        WHERE s.strategy = '{strategy}'
          {date_condition}
          {amount_condition}
        ORDER BY s.ts_code
    """
    
    results = query_all(sql)
    
    # 生成txt内容（每行一个股票代码）
    codes = '\n'.join([r['ts_code'] for r in results])
    
    # 生成文件名
    filename = f"{strategy}_{period}_{'latest' if not screen_date else screen_date}.txt"
    
    return Response(
        content=codes,
        media_type='text/plain',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


# ============ 追踪接口 ============

@app.get('/api/tracking/{strategy}/{period}')
def tracking_list(
    strategy: str, 
    period: str,
    username: str = Depends(get_current_user)
):
    """获取追踪中的股票列表"""
    if strategy not in ['b0', 'b1'] or period not in ['daily', 'weekly']:
        raise HTTPException(status_code=400, detail='无效的策略或周期参数')
    
    results = get_tracking_list(strategy, period)
    
    for r in results:
        if r.get('trade_date'):
            r['trade_date'] = str(r['trade_date'])
        if r.get('screen_date'):
            r['screen_date'] = str(r['screen_date'])
        if r.get('track_date'):
            r['track_date'] = str(r['track_date'])
    
    return {
        'strategy': strategy,
        'period': period,
        'count': len(results),
        'data': results
    }


@app.get('/api/tracking/{strategy}/{period}/{relate_id}')
def track_detail(
    strategy: str,
    period: str,
    relate_id: int,
    username: str = Depends(get_current_user)
):
    """获取单只股票的追踪历史"""
    if strategy not in ['b0', 'b1'] or period not in ['daily', 'weekly']:
        raise HTTPException(status_code=400, detail='无效的策略或周期参数')
    
    history = get_track_history(strategy, period, relate_id)
    
    for h in history:
        if h.get('track_date'):
            h['track_date'] = str(h['track_date'])
    
    return {
        'relate_id': relate_id,
        'count': len(history),
        'data': history
    }


# ============ K线接口 ============

@app.get('/api/stock/{ts_code}/kline')
def stock_kline(
    ts_code: str,
    period: str = 'daily',
    days: int = 120,
    username: str = Depends(get_current_user)
):
    """获取股票K线数据"""
    kline = get_stock_kline(ts_code, period, days)
    
    for k in kline:
        if k.get('trade_date'):
            k['trade_date'] = str(k['trade_date'])
    
    return {
        'ts_code': ts_code,
        'period': period,
        'count': len(kline),
        'data': kline
    }


@app.get('/api/stock/{ts_code}/info')
def stock_info(ts_code: str, username: str = Depends(get_current_user)):
    """获取股票基本信息"""
    info = get_stock_info(ts_code)
    if not info:
        return {
            'ts_code': ts_code,
            'name': ts_code.split('.')[0]
        }
    return info


@app.get('/api/stock/{ts_code}/screen-history')
def stock_screen_history(ts_code: str, username: str = Depends(get_current_user)):
    """获取指定股票的所有选股历史"""
    history = get_stock_screen_history(ts_code)
    for h in history:
        if h.get('screen_date'):
            h['screen_date'] = str(h['screen_date'])
        if h.get('created_at'):
            h['created_at'] = str(h['created_at'])
    return {
        'ts_code': ts_code,
        'count': len(history),
        'data': history
    }


# ============ 历史统计接口 ============

@app.get('/api/stats/signals')
def signal_stats(days: int = 30, username: str = Depends(get_current_user)):
    """获取信号触发统计"""
    stats = get_signal_stats(days)
    for s in stats:
        if s.get('screen_date'):
            s['screen_date'] = str(s['screen_date'])
    return {
        'days': days,
        'data': stats
    }


# ============ 信号触发接口 ============

@app.get('/api/signals/triggers')
def signal_triggers(
    signal_type: Optional[str] = None,
    strategy: Optional[str] = None,
    signal_date: Optional[str] = None,
    username: str = Depends(get_current_user)
):
    """查询信号触发详情"""
    if signal_type and signal_type not in ['s1', 's2', 's3', 'sm1']:
        raise HTTPException(status_code=400, detail='无效的信号类型')
    if strategy and strategy not in ['b0', 'b1']:
        raise HTTPException(status_code=400, detail='无效的策略类型')

    results = get_signal_triggers(signal_type, strategy, signal_date)
    for r in results:
        if r.get('screen_date'):
            r['screen_date'] = str(r['screen_date'])
        if r.get('signal_date'):
            r['signal_date'] = str(r['signal_date'])
    return {'count': len(results), 'data': results}


@app.get('/api/signals/dates')
def signal_dates(limit: int = 30, username: str = Depends(get_current_user)):
    """获取有信号触发的日期列表"""
    results = query_all("""
        SELECT DISTINCT td.track_date as signal_date
        FROM stock_track_daily td
        WHERE td.s1 IS NOT NULL OR td.s2 IS NOT NULL OR td.s3 IS NOT NULL OR td.sm1 IS NOT NULL
        UNION
        SELECT DISTINCT td.track_date as signal_date
        FROM stock_track_weekly td
        WHERE td.s1 IS NOT NULL OR td.s2 IS NOT NULL OR td.s3 IS NOT NULL OR td.sm1 IS NOT NULL
        ORDER BY signal_date DESC
        LIMIT %s
    """, (limit,))
    return {'dates': [str(r['signal_date']) for r in results]}


# ============ 搜索接口 ============

@app.get('/api/stock/search')
def stock_search(q: str = '', limit: int = 20, username: str = Depends(get_current_user)):
    """搜索股票（按代码或名称）"""
    if not q or len(q.strip()) == 0:
        return {'data': []}
    q = q.strip()
    results = query_all("""
        SELECT ts_code, symbol, name, area, industry
        FROM stock_info
        WHERE symbol LIKE %s OR name LIKE %s
        ORDER BY symbol
        LIMIT %s
    """, (f'%{q}%', f'%{q}%', limit))
    return {'data': results, 'count': len(results)}


# ============ 全量股票接口 ============

@app.get('/api/stock/all')
def stock_all(limit: int = 6000, username: str = Depends(get_current_user)):
    """获取全部股票列表，按代码排序"""
    results = query_all("""
        SELECT ts_code, symbol, name, area, industry
        FROM stock_info
        ORDER BY symbol
        LIMIT %s
    """, (limit,))
    return {'data': results, 'count': len(results)}


# ============ 全量股票接口 ============

@app.get('/api/stocks/all')
def stocks_all(limit: int = 6000, username: str = Depends(get_current_user)):
    """获取全部股票列表，按代码排序"""
    results = query_all("""
        SELECT ts_code, symbol, name, area, industry
        FROM stock_info
        ORDER BY symbol
        LIMIT %s
    """, (limit,))
    return {'data': results, 'count': len(results)}


# ============ 定时任务接口 ============

@app.get('/api/tasks')
def task_list(username: str = Depends(get_current_user)):
    """获取所有定时任务状态"""
    result = []
    for tid, task in TASKS.items():
        job = scheduler.get_job(tid) if scheduler else None
        # 查最近一次执行记录
        last = query_one(
            'SELECT status, created_at, duration_sec FROM task_log WHERE task_id=%s ORDER BY created_at DESC LIMIT 1',
            (tid,)
        )
        result.append({
            'id': tid,
            'name': task['name'],
            'schedule': task['schedule'],
            'next_run': str(job.next_run_time) if job and job.next_run_time else None,
            'last_status': last['status'] if last else None,
            'last_run': str(last['created_at']) if last else None,
            'last_duration': last['duration_sec'] if last else None,
        })
    return {'data': result}


@app.post('/api/tasks/{task_id}/run')
def task_run(task_id: str, username: str = Depends(get_current_user)):
    """手动触发任务"""
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail='任务不存在')
    ok, output = execute_task(task_id)
    return {'success': ok, 'output': output[:2000]}


@app.get('/api/tasks/logs')
def task_logs(task_id: str = None, limit: int = 50, username: str = Depends(get_current_user)):
    """获取任务执行日志"""
    if task_id:
        rows = query_all(
            'SELECT * FROM task_log WHERE task_id=%s ORDER BY created_at DESC LIMIT %s',
            (task_id, limit)
        )
    else:
        rows = query_all(
            'SELECT * FROM task_log ORDER BY created_at DESC LIMIT %s',
            (limit,)
        )
    for r in rows:
        if r.get('created_at'):
            r['created_at'] = str(r['created_at'])
        if r.get('output'):
            r['output'] = r['output'][:500]
    return {'data': rows}


@app.delete('/api/tasks/logs')
def task_logs_clear(task_id: str = None, username: str = Depends(get_current_user)):
    """清空任务日志"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    if task_id:
        cursor.execute('DELETE FROM task_log WHERE task_id=%s', (task_id,))
    else:
        cursor.execute('DELETE FROM task_log')
    conn.commit()
    conn.close()
    return {'success': True}


# ============ 健康检查 ============

@app.get('/api/health')
def health():
    """健康检查"""
    return {'status': 'ok'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
