-- 交易管理系统数据表
-- 创建时间：2026-06-26

-- 持仓表
CREATE TABLE IF NOT EXISTS stock_position (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ts_code VARCHAR(12) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) COMMENT '股票名称',
    strategy VARCHAR(10) COMMENT '选股策略(b0/b1/b2/b3)',
    screen_date DATE COMMENT '选股日期',
    buy_date DATE NOT NULL COMMENT '买入日期',
    buy_price DECIMAL(10,3) NOT NULL COMMENT '买入均价',
    buy_amount INT NOT NULL COMMENT '买入数量(股)',
    buy_total DECIMAL(12,2) COMMENT '买入总金额',
    current_price DECIMAL(10,3) COMMENT '当前价格',
    current_value DECIMAL(12,2) COMMENT '当前市值',
    profit_loss DECIMAL(12,2) COMMENT '盈亏金额',
    profit_loss_pct DECIMAL(5,2) COMMENT '盈亏百分比',
    status ENUM('holding','sold','partial_sold') DEFAULT 'holding' COMMENT '持仓状态',
    is_alert TINYINT DEFAULT 0 COMMENT '是否触发卖点提示',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_ts_code (ts_code),
    KEY idx_status (status),
    KEY idx_buy_date (buy_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓表';

-- 交易记录表
CREATE TABLE IF NOT EXISTS stock_trade (
    id INT AUTO_INCREMENT PRIMARY KEY,
    position_id INT NOT NULL COMMENT '持仓ID',
    ts_code VARCHAR(12) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) COMMENT '股票名称',
    trade_type ENUM('buy','sell','sell_partial') NOT NULL COMMENT '交易类型',
    trade_date DATE NOT NULL COMMENT '交易日期',
    trade_price DECIMAL(10,3) NOT NULL COMMENT '成交价',
    trade_amount INT NOT NULL COMMENT '成交数量(股)',
    trade_total DECIMAL(12,2) NOT NULL COMMENT '成交总金额',
    profit_loss DECIMAL(12,2) COMMENT '盈亏金额',
    notes TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_position (position_id),
    KEY idx_ts_code (ts_code),
    KEY idx_trade_date (trade_date),
    FOREIGN KEY (position_id) REFERENCES stock_position(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易记录表';

-- 卖点提示表
CREATE TABLE IF NOT EXISTS stock_alert (
    id INT AUTO_INCREMENT PRIMARY KEY,
    position_id INT NOT NULL COMMENT '持仓ID',
    ts_code VARCHAR(12) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) COMMENT '股票名称',
    alert_type VARCHAR(20) NOT NULL COMMENT '提示类型(s1/s2/s3/sm1)',
    alert_date DATE NOT NULL COMMENT '触发日期',
    alert_price DECIMAL(10,3) COMMENT '触发价格',
    trigger_desc TEXT COMMENT '触发描述',
    status ENUM('unread','read') DEFAULT 'unread' COMMENT '阅读状态',
    read_at TIMESTAMP NULL COMMENT '已读时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_position (position_id),
    KEY idx_status (status),
    KEY idx_alert_date (alert_date),
    FOREIGN KEY (position_id) REFERENCES stock_position(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='卖点提示表';