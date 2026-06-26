#!/bin/bash
# B1点每周定时任务
# 1. 更新周线数据
# 2. 执行筛选
# 3. 追踪更新
# 4. 发送结果

cd /root/.openclaw/workspace/stock_data

TASK_TIME=$(date '+%Y-%m-%d %H:%M:%S')

echo "============================================================"
echo "B1点每周任务 - $TASK_TIME"
echo "============================================================"

# 步骤0: 发送开始通知
openclaw message send \
  --channel qqbot \
  --target "qqbot:c2c:5216D73CDD5404EDD8D06DF75F95885D" \
  --message "📊 B1点每周任务开始执行

⏰ 时间：$TASK_TIME
📋 任务：更新周线数据 → 筛选股票 → 推送结果

请稍候..." 2>&1 > /dev/null &

# 步骤1a: 更新周线数据
echo ""
echo "【步骤1a】更新周线数据(MySQL)..."
python3 update_stock_weekly_mysql.py 2>&1
if [ $? -ne 0 ]; then
    echo "❌ 周线数据更新失败"
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

# 步骤2: 执行周线B1筛选
echo ""
echo "【步骤2】执行周线B1筛选(MySQL)..."
OUTPUT=$(python3 run_b1_screen_weekly_mysql.py 2>&1)
echo "$OUTPUT"

# 步骤3: 追踪更新
echo ""
echo "【步骤3】追踪更新..."
python3 track_b1_weekly.py 2>&1

# 步骤4: 发送结果文件
TODAY=$(date +%Y%m%d)
RESULT_FILE="/root/.openclaw/workspace/stock_data/b1_weekly_result_${TODAY}.xlsx"

if [ -f "$RESULT_FILE" ]; then
    echo ""
    echo "【步骤4】发送结果文件..."
    
    STOCK_COUNT=$(tail -n +2 "$RESULT_FILE" | wc -l)
    
    openclaw message send \
      --channel qqbot \
      --target "qqbot:c2c:5216D73CDD5404EDD8D06DF75F95885D" \
      --message "📊 B1点周线筛选结果 ($TODAY)

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
