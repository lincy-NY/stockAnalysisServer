#!/usr/bin/env python3
"""
MySQL 数据库配置
"""

import pymysql
from contextlib import contextmanager

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '82728231lcy123L',
    'database': 'stock',
    'charset': 'utf8mb4'
}


@contextmanager
def get_db_connection():
    """获取数据库连接"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def get_db_cursor(conn):
    """获取数据库游标"""
    return conn.cursor(pymysql.cursors.DictCursor)


def init_database():
    """初始化数据库表结构"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 创建股票信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                ts_code VARCHAR(12) PRIMARY KEY COMMENT '股票代码',
                symbol VARCHAR(6) NOT NULL COMMENT '股票代码(不带后缀)',
                name VARCHAR(20) COMMENT '股票名称',
                area VARCHAR(20) COMMENT '地区',
                industry VARCHAR(20) COMMENT '行业',
                list_date DATE COMMENT '上市日期',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基本信息表'
        ''')
        
        # 创建日线数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_daily (
                ts_code VARCHAR(12) NOT NULL COMMENT '股票代码',
                trade_date DATE NOT NULL COMMENT '交易日期',
                open DECIMAL(10,3) COMMENT '开盘价',
                high DECIMAL(10,3) COMMENT '最高价',
                low DECIMAL(10,3) COMMENT '最低价',
                close DECIMAL(10,3) COMMENT '收盘价',
                pre_close DECIMAL(10,3) COMMENT '前收盘价',
                change_val DECIMAL(10,4) COMMENT '涨跌额',
                pct_chg DECIMAL(8,4) COMMENT '涨跌幅%',
                vol DECIMAL(20,2) COMMENT '成交量(手)',
                amount DECIMAL(20,2) COMMENT '成交额(千元)',
                short_line DECIMAL(12,6) COMMENT '短期趋势线',
                big_line DECIMAL(12,6) COMMENT '多空线',
                kdj_j DECIMAL(10,4) COMMENT 'KDJ-J值',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (ts_code, trade_date),
                INDEX idx_trade_date (trade_date),
                INDEX idx_ts_code (ts_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日线数据表'
        ''')
        
        # 创建周线数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_weekly (
                ts_code VARCHAR(12) NOT NULL COMMENT '股票代码',
                trade_date DATE NOT NULL COMMENT '交易日期',
                open DECIMAL(10,3) COMMENT '开盘价',
                high DECIMAL(10,3) COMMENT '最高价',
                low DECIMAL(10,3) COMMENT '最低价',
                close DECIMAL(10,3) COMMENT '收盘价',
                pre_close DECIMAL(10,3) COMMENT '前收盘价',
                change_val DECIMAL(10,4) COMMENT '涨跌额',
                pct_chg DECIMAL(8,4) COMMENT '涨跌幅%',
                vol DECIMAL(20,2) COMMENT '成交量(手)',
                amount DECIMAL(20,2) COMMENT '成交额(千元)',
                short_line DECIMAL(12,6) COMMENT '短期趋势线',
                big_line DECIMAL(12,6) COMMENT '多空线',
                kdj_j DECIMAL(10,4) COMMENT 'KDJ-J值',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (ts_code, trade_date),
                INDEX idx_trade_date (trade_date),
                INDEX idx_ts_code (ts_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票周线数据表'
        ''')
        
        conn.commit()
        print("✓ 数据库表结构创建完成")


if __name__ == '__main__':
    init_database()
