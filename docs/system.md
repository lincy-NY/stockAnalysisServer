# 选股系统网站 — 系统文档

> 版本：2.0 | 更新：2026-04-27
> URL: http://211.159.224.52
> 管理员：admin / admin123

---

## 一、架构总览

```
前端 (Vue3 + Element Plus)  →  nginx  →  后端 (FastAPI)  →  MySQL
/var/www/stock-web               :8000          stock 库
```

- **后端**：`/root/.openclaw/workspace/stock_web/backend/`
  - `main.py` — API 路由（FastAPI + Uvicorn）
  - `database.py` — 数据库操作层
  - `auth.py` — JWT 认证
  - `config.py` — MySQL 连接配置
- **前端**：`/root/.openclaw/workspace/stock_web/frontend/`
  - Vue3 + Element Plus，构建后部署到 nginx
- **服务**：`stock-web.service`（systemd），监听 `127.0.0.1:8000`

---

## 二、数据库表（当前）

### 选股结果表

| 表名 | 说明 | 策略 |
|------|------|------|
| `stock_screen_results` | 日线选股（统一表，strategy 字段区分） | b0=346, b1=20, b2=349 |
| `stock_b0_weekly` | B0 周线选股（独立表） | 10 条 |
| `stock_b1_weekly` | B1 周线选股（独立表） | 120 条 |
| `stock_b0_daily` | B0 日线旧表（未使用） | 210 条 |
| `stock_b1_daily` | B1 日线旧表（未使用） | 9 条 |

**stock_screen_results 字段：**
id | strategy | screen_date | ts_code | trade_date | close | low_price | big_line | short_line | kdj_j | brick_value | dist_pct | dist_short | vol | amount | is_track | created_at

### 追踪表

| 表名 | 说明 | 条数 |
|------|------|------|
| `stock_b1_daily_track` | 日线追踪（统一表，strategy 字段区分，含 b0=702, b1=27） | 729 |
| `stock_b1_weekly_track` | 周线追踪（统一表，b1=120） | 120 |

**追踪表字段（stock_b1_daily_track）：**
id | relate_id | strategy | track_date | close | low | short_line | big_line | target_price | s1(DATE) | s2(DATE) | s3(DATE) | sm1(DATE) | created_at

> 注：s1/s2/s3 已改为 DATE 类型（记录触发日期），sm1 是新增的 MACD 反转信号

### 数据表

| 表名 | 说明 | 记录数 |
|------|------|--------|
| `stock_daily` | 日线数据（含技术指标+MACD） | 223万+ |
| `stock_weekly` | 周线数据（含技术指标） | 327万+ |
| `stock_info` | 股票基本信息 | 4593 |

**stock_daily 关键指标字段：**
close, short_line (EMA双10), big_line (四线均值), kdj_j, brick_value, macd_dif, macd_dea, macd_bar

---

## 三、后端 API 接口

### 3.1 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/login` | 登录，返回 JWT token |
| GET | `/api/me` | 获取当前用户信息 |

### 3.2 仪表盘

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats` | 今日各策略选股数量、追踪中数量、信号触发数量 |

### 3.3 选股结果

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/screen/{strategy}/{period}` | strategy=b0/b1/b2, period=daily/weekly, screen_date=? | 获取选股结果（日线从统一表，周线从独立表） |
| GET | `/api/screen/{strategy}/{period}/dates` | limit=30 | 获取有选股记录的日期列表 |

**当前限制：**
- B2 仅支持 daily
- B3 未接入
- 周线从旧表读取（stock_b0_weekly / stock_b1_weekly）

### 3.4 追踪

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/tracking/{strategy}/{period}` | strategy=b0/b1, period=daily/weekly | 获取追踪中股票列表 |
| GET | `/api/tracking/{strategy}/{period}/{relate_id}` | | 获取单只追踪历史 |

**当前限制：**
- 追踪接口仅支持 b0/b1，不含 b2/b3
- 信号显示为 0/1（前端代码还未适配 DATE 类型）

### 3.5 K线

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/stock/{ts_code}/kline` | period=daily/weekly, days=120 | K线+技术指标（不含 MACD） |
| GET | `/api/stock/{ts_code}/info` | | 股票基本信息 |

### 3.6 其他

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/stats/signals` | days=30 | 信号触发统计（s1/s2/s3 计数） |
| GET | `/api/stock/search` | q=, limit=20 | 搜索股票（代码/名称） |
| GET | `/api/stock/all` | limit=6000 | 全部股票列表 |
| GET | `/api/stocks/all` | limit=6000 | 同上（重复接口） |
| GET | `/api/health` | | 健康检查 |

---

## 四、前端页面

### 4.1 登录页 (`/login`)
- 用户名+密码表单
- JWT token 存储在 localStorage

### 4.2 仪表盘 (`/`)
- 6 个统计卡片：B0日线、B1日线、B2日线、追踪中、信号触发、周线选股
- 3 个选股概览表格（各显示最新 10 条）：
  - B0（金叉信号）：代码、名称、收盘价、短期线、多空线
  - B1（超卖反弹）：代码、名称、收盘价、J值、状态
  - B2（砖型图）：代码、名称、收盘价、砖型图值、距多空%
- 点击代码 → 东方财富，点击名称 → 股票详情页

### 4.3 选股结果页 (`/screen`)
- 筛选条件：策略(b0/b1/b2) + 周期(daily/weekly) + 日期 + 成交额过滤
- 表格：代码、名称、选股/交易日期、短期线、多空线、J值(仅B1)、砖型图(仅B2)、距多空%、距短期%、成交量、成交额、状态、操作
- 分页：10/20/50/100

### 4.4 追踪页 (`/tracking`)
- 筛选：策略(b0/b1) + 周期(daily/weekly)
- 表格：代码、名称、选股日期、选股收盘价、最低价、最新收盘、涨跌幅、最新追踪日期、信号(S1/S2/S3)
- 点击"详情"弹出追踪历史对话框
- **当前问题**：信号列显示逻辑检查 `row.s1 === 1`，但数据库已改为 DATE 类型

### 4.5 股票详情页 (`/stock/:code`)
- 顶部：股票基本信息（代码、名称）
- K线图（ECharts）：
  - 主图：K线 + short_line + big_line
  - 下方：砖型图指标
  - 日期范围：120天 / 250天(1年) / 500天(2年)
- 选股历史表格（从 stock_screen_results）
- 追踪历史表格（从 track 表）
- **当前问题**：K线 API 未返回 MACD 数据，详情页无 MACD 图表

---

## 五、定时任务

| 任务 | ID | 时间 | 说明 |
|------|----|------|------|
| 10 分钟检查 | — | */10 * * * * | 检查 work.md，空则 HEARTBEAT_OK |
| B1 日线选股 | 91d7e002... | 周一-五 17:00 | run_b1_screen_mysql.py |
| B1 周线选股 | 49125d03... | 周六 08:00 | run_b1_screen_weekly_mysql.py |
| B1 日线追踪 | — | 周一-五 17:30 | track_b1_daily.py |

---

## 六、已知问题清单

1. **追踪页信号显示**：检查 `row.s1 === 1` 但字段已改为 DATE，需改为 `row.s1 != null`
2. **Dashboard 统计**：`get_dashboard_stats()` 查询 `s1 = 1` 但字段已改为 DATE
3. **K线无 MACD**：`get_stock_kline()` 未查 macd_dif/macd_dea/macd_bar
4. **B3 未接入**：前端/后端/定时任务均不支持 B3 策略
5. **选股表分散**：日线用统一表，周线用旧表，结构不一致
6. **追踪表分散**：B0/B1 共用一张表（strategy 区分），周线也是，但名称叫 `stock_b1_*_track` 容易混淆
7. **/api/stocks/all 重复**：与 /api/stock/all 功能完全相同

---

## 七、改版方向（待确认）

将以上问题统一解决：
- 4 张新表：stock_select_daily / stock_select_weekly / stock_track_daily / stock_track_weekly
- 所有策略共用选股表和追踪表，通过 strategy 字段区分
- 前端/后端/定时任务统一适配新表结构
