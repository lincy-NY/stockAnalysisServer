# 股票量化选股系统

基于技术指标的量化选股分析系统，支持 B0/B1/B2/B3 多策略选股与追踪。

## 系统架构

- **后端**: Python FastAPI
- **前端**: Vue3 + Vite
- **数据库**: MySQL 8.0
- **定时任务**: APScheduler (Web端配置)

## 目录结构

```
stock_analysis_system/
├── docs/                # 文档
│   ├── strategies/      # 策略说明
│   └── system.md        # 系统文档
├── backend/             # 后端代码 (FastAPI)
├── frontend/            # 前端代码 (Vue3)
├── data/scripts/        # 数据处理脚本
└── config/              # 配置文件
```

## 核心功能

1. **数据更新**: 日线/周线数据自动更新
2. **技术指标计算**: 短期线、多空线、KDJ、MACD、砖型图
3. **选股策略**:
   - B0: 短期线金叉多空线
   - B1: KDJ超卖 + 股价回调至多空线上方
   - B2: 阳包阴形态
   - B3: MACD趋势启动
4. **结果追踪**: 自动追踪选股后的表现
5. **定时任务**: 日线17:00、周线周六08:00自动执行

## 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 数据更新

```bash
cd data/scripts
python update_stock_daily_mysql.py
python update_stock_weekly_mysql.py
```

### 选股执行

```bash
# 日线选股
python run_b0_screen_mysql.py
python run_b1_screen_mysql.py
python run_b2_screen_mysql.py
python run_b3_screen_mysql.py

# 周线选股
python run_b0_screen_weekly_mysql.py
python run_b1_screen_weekly_mysql.py

# 追踪
python track_b0_daily.py
python track_b1_daily.py
python track_b3_daily.py
```

## 数据库配置

数据库配置在 `backend/config.py` 中修改。

## 技术指标说明

- **short_line**: EMA(EMA(Close, 10), 10)
- **big_line**: (MA14 + MA28 + MA57 + MA114) / 4
- **KDJ**: 标准KDJ公式
- **MACD**: 标准MACD公式
- **砖型图**: 固定涨跌幅的OHLC简化

## 定时任务

系统通过 Web 端 APScheduler 配置定时任务：
- 日线数据更新 + 选股: 每周一至五 17:00
- 周线数据更新 + 选股: 每周六 08:00

## 系统访问

- 演示地址: http://211.159.224.52
- 默认账号: admin / admin123