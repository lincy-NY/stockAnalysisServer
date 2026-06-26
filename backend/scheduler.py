"""
APScheduler 定时任务调度器
替代 OpenClaw cron，零 token 消耗
"""
import subprocess
import sys
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pymysql
from config import DB_CONFIG

STOCK_DATA_DIR = '/root/.openclaw/workspace/stock_data'
PYTHON = sys.executable

TASKS = {
    'b1_daily': {
        'name': 'B1日线选股',
        'schedule': '周一至五 17:00',
        'cron': {'day_of_week': 'mon-fri', 'hour': 17, 'minute': 0},
        'scripts': [
            ('update_stock_daily_mysql.py', '更新日线数据'),
            ('update_daily_basic_mysql.py', '更新估值指标'),
            ('update_brick_last_5days.py', '更新砖型图'),
            ('run_b1_screen_mysql.py', 'B1日线筛选'),
            ('track_b1_daily.py', '日线追踪更新'),
        ],
    },
    'b1_weekly': {
        'name': 'B1周线选股',
        'schedule': '周六 08:00',
        'cron': {'day_of_week': 'sat', 'hour': 8, 'minute': 0},
        'scripts': [
            ('update_stock_weekly_mysql.py', '更新周线数据'),
            ('update_daily_basic_mysql.py', '更新估值指标'),
            ('run_b1_screen_weekly_mysql.py', 'B1周线筛选'),
            ('track_b1_weekly.py', '周线追踪更新'),
        ],
    },
}

scheduler = None


def _log(task_id, status, output='', duration=0):
    """写入任务执行日志"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO task_log (task_id, task_name, status, output, duration_sec)
        VALUES (%s, %s, %s, %s, %s)
    """, (task_id, TASKS[task_id]['name'], status, output[:65535], duration))
    conn.commit()
    conn.close()


def _is_trading_day():
    """通过 tushare 判断今天是否交易日"""
    try:
        from datetime import date
        today = date.today().strftime('%Y%m%d')
        result = subprocess.run(
            [PYTHON, '-c', f"""
import tushare as ts
ts.set_token('7f67a9fe52856eda6d9ea19c2e492a2ca52266657ff55aaa3d399919')
pro = ts.pro_api()
df = pro.trade_cal(exchange='SSE', start_date='{today}', end_date='{today}', fields='cal_date,is_open')
print('YES' if df is not None and len(df) > 0 and df.iloc[0]['is_open'] == 1 else 'NO')
"""],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip() == 'YES'
    except Exception:
        return True  # 出错时默认执行


def _run_script(name):
    """运行单个 Python 脚本，返回 (success, output)"""
    path = os.path.join(STOCK_DATA_DIR, name)
    result = subprocess.run(
        [PYTHON, path],
        capture_output=True, text=True,
        timeout=600, cwd=STOCK_DATA_DIR
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output


def execute_task(task_id):
    """执行任务的完整流程"""
    task = TASKS.get(task_id)
    if not task:
        return False, '未知任务'

    start = datetime.now()

    # 日线任务判断交易日
    if task_id == 'b1_daily' and not _is_trading_day():
        msg = '今日非交易日，跳过执行'
        _log(task_id, 'skipped', msg, 0)
        return True, msg

    all_output = []
    try:
        for script, desc in task['scripts']:
            all_output.append(f'[{desc}]')
            ok, out = _run_script(script)
            all_output.append(out)
            if not ok:
                raise Exception(f'{desc}失败')

        elapsed = (datetime.now() - start).seconds
        full_output = '\n'.join(all_output)
        _log(task_id, 'success', full_output, elapsed)
        return True, full_output

    except Exception as e:
        elapsed = (datetime.now() - start).seconds
        full_output = '\n'.join(all_output) + f'\n错误: {e}'
        _log(task_id, 'failed', full_output, elapsed)
        return False, full_output


def init_scheduler(app):
    """初始化调度器并注册到 FastAPI"""
    global scheduler
    scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

    for task_id, task in TASKS.items():
        if 'cron' in task:
            scheduler.add_job(
                execute_task,
                trigger=CronTrigger(**task['cron'], timezone='Asia/Shanghai'),
                id=task_id,
                name=task['name'],
                kwargs={'task_id': task_id},
                misfire_grace_time=3600,
            )

    @app.on_event('startup')
    def start_scheduler():
        scheduler.start()

    @app.on_event('shutdown')
    def shutdown_scheduler():
        scheduler.shutdown()


def ensure_table():
    """确保 task_log 表存在"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id VARCHAR(32) NOT NULL,
            task_name VARCHAR(64),
            status ENUM('running','success','failed','skipped') DEFAULT 'running',
            output TEXT,
            duration_sec INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            KEY idx_task_id (task_id, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    conn.close()


# 启动时建表
ensure_table()
