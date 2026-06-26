#!/bin/bash
# B1点每日定时任务
# 0. 判断是否交易日（非交易日跳过）
# 1. 更新当天数据
# 2. 执行筛选
# 3. 追踪更新
# 4. 发送结果

cd /root/.openclaw/workspace/stock_data

TASK_TIME=$(date '+%Y-%m-%d %H:%M:%S')

echo "============================================================"
echo "B1点每日任务 - $TASK_TIME"
echo "============================================================"

# 步骤0: 判断是否交易日
TODAY=$(date +%Y%m%d)
IS_TRADING=$(python3 -c "
import tushare as ts
import sys
try:
    ts.set_token('7f67a9fe52856eda6d9ea19c2e492a2ca52266657ff55aaa3d399919')
    pro = ts.pro_api()
    df = pro.trade_cal(exchange='SSE', start_date='$TODAY', end_date='$TODAY', fields='cal_date,is_open')
    if df is not None and len(df) > 0 and df.iloc[0]['is_open'] == 1:
        print('YES')
    else:
        print('NO')
except Exception as e:
    print('ERROR')
" 2>&1)

echo "今日($TODAY)是否交易日: $IS_TRADING"

if [ "$IS_TRADING" != "YES" ]; then
    echo "⏭ 今日非交易日，跳过执行"
    openclaw message send \
      --channel qqbot \
      --target "qqbot:c2c:5216D73CDD5404EDD8D06DF75F95885D" \
      --message "⏭ 今日($TODAY)非交易日，B1点每日任务已跳过" 2>&1 > /dev/null
    exit 0
fi

echo "✅ 今日为交易日，继续执行"

# 步骤1a: 发送开始通知
openclaw message send \
  --channel qqbot \
  --target "qqbot:c2c:5216D73CDD5404EDD8D06DF75F95885D" \
  --message "📊 B1点每日任务开始执行

⏰ 时间：$TASK_TIME
📋 任务：更新数据 → 筛选股票 → 推送结果

请稍候..." 2>&1 > /dev/null &

# 步骤1b: 更新股票数据
echo ""
echo "【步骤1a】更新股票数据(MySQL)..."
python3 update_stock_daily_mysql.py 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 日线数据更新失败"
    exit 1
fi

# 步骤1b: 更新估值指标(PE/PB/股息率/市值)
echo ""
echo "【步骤1b】更新估值指标(MySQL)..."
python3 update_daily_basic_mysql.py 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 估值数据更新失败"
    exit 1
fi

# 步骤1c: 更新砖型图指标
echo ""
echo "【步骤1c】更新砖型图指标(MySQL)..."
python3 update_brick_monthly.py 2>&1
if [ $? -ne 0 ]; then
    echo "⚠️ 砖型图更新失败（继续执行后续任务）"
fi

# 步骤2: 执行B1筛选
echo ""
echo "【步骤2】执行B1筛选(MySQL)..."
OUTPUT=$(python3 run_b1_screen_mysql.py 2>&1)
echo "$OUTPUT"

# 步骤3: 追踪更新
echo ""
echo "【步骤3】追踪更新..."
python3 track_b1_daily.py 2>&1

# 步骤4: 发送结果文件
TODAY=$(date +%Y%m%d)
RESULT_FILE="/root/.openclaw/workspace/stock_data/b1_result_${TODAY}.xlsx"

if [ -f "$RESULT_FILE" ]; then
    echo ""
    echo "【步骤4】发送结果文件..."
    
    # 统计符合条件的股票数量
    STOCK_COUNT=$(tail -n +2 "$RESULT_FILE" | wc -l)
    
    # 发送文本摘要
    openclaw message send \
      --channel qqbot \
      --target "qqbot:c2c:5216D73CDD5404EDD8D06DF75F95885D" \
      --message "📊 B1点筛选结果 ($TODAY)

✅ 共找到 $STOCK_COUNT 只符合条件的股票

详情请查看附件CSV文件" \
      --media "$RESULT_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ 结果文件已发送"
    else
        echo "❌ 发送失败"
    fi
else
    echo "❌ 未找到结果文件"
fi
