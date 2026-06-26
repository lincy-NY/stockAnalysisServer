<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="4">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.today.b0_daily }}</div>
            <div class="stat-label">B0日线</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.today.b1_daily }}</div>
            <div class="stat-label">B1日线</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.today.b2_daily }}</div>
            <div class="stat-label">B2日线</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value primary">{{ stats.tracking.b0 + stats.tracking.b1 }}</div>
            <div class="stat-label">追踪中</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value warning">{{ recentSignals }}</div>
            <div class="stat-label">近两日信号</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.today.b0_weekly + stats.today.b1_weekly }}</div>
            <div class="stat-label">周线选股</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 选股结果概览 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card header="B0日线选股（金叉信号）">
          <el-table :data="b0Daily" height="300" @row-dblclick="goToStock">
            <el-table-column prop="ts_code" label="代码" width="110">
              <template #default="{ row }">
                <a :href="getEastmoneyUrl(row.ts_code)" target="_blank" class="code-link">{{ row.ts_code }}</a>
              </template>
            </el-table-column>
            <el-table-column prop="stock_name" label="名称" width="120">
              <template #default="{ row }">
                <span class="name-link" @click="goToStock(row)">{{ row.stock_name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="close" label="收盘价" width="90">
              <template #default="{ row }">{{ Number(row.close).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="short_line" label="短期线">
              <template #default="{ row }">{{ Number(row.short_line).toFixed(3) }}</template>
            </el-table-column>
            <el-table-column prop="big_line" label="多空线">
              <template #default="{ row }">{{ Number(row.big_line).toFixed(3) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="B1日线选股（超卖反弹）">
          <el-table :data="b1Daily" height="300" @row-dblclick="goToStock">
            <el-table-column prop="ts_code" label="代码" width="110">
              <template #default="{ row }">
                <a :href="getEastmoneyUrl(row.ts_code)" target="_blank" class="code-link">{{ row.ts_code }}</a>
              </template>
            </el-table-column>
            <el-table-column prop="stock_name" label="名称" width="120">
              <template #default="{ row }">
                <span class="name-link" @click="goToStock(row)">{{ row.stock_name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="close" label="收盘价" width="90">
              <template #default="{ row }">{{ Number(row.close).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="kdj_j" label="J值">
              <template #default="{ row }">{{ Number(row.kdj_j || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="is_track" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_track === 1 ? 'success' : 'info'" size="small">
                  {{ row.is_track === 1 ? '追踪' : '结束' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="B2日线选股（砖型图动量拐点）">
          <el-table :data="b2Daily" height="300" @row-dblclick="goToStock">
            <el-table-column prop="ts_code" label="代码" width="110">
              <template #default="{ row }">
                <a :href="getEastmoneyUrl(row.ts_code)" target="_blank" class="code-link">{{ row.ts_code }}</a>
              </template>
            </el-table-column>
            <el-table-column prop="stock_name" label="名称" width="120">
              <template #default="{ row }">
                <span class="name-link" @click="goToStock(row)">{{ row.stock_name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="close" label="收盘价" width="90">
              <template #default="{ row }">{{ Number(row.close).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="brick_value" label="砖型图">
              <template #default="{ row }">{{ Number(row.brick_value || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="dist_pct" label="距多空%">
              <template #default="{ row }">{{ Number(row.dist_pct || 0).toFixed(2) }}%</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../utils/api'

const router = useRouter()
const stats = ref({
  today: { b0_daily: 0, b1_daily: 0, b2_daily: 0, b0_weekly: 0, b1_weekly: 0 },
  tracking: { b0: 0, b1: 0 },
  signals: { b0: 0, b1: 0 }
})
const recentSignals = ref(0)
const b0Daily = ref([])
const b1Daily = ref([])
const b2Daily = ref([])

onMounted(async () => {
  const [statsRes, b0Res, b1Res, b2Res, signalRes] = await Promise.all([
    api.get('/dashboard/stats'),
    api.get('/screen/b0/daily'),
    api.get('/screen/b1/daily'),
    api.get('/screen/b2/daily'),
    api.get('/dashboard/signal-recent')
  ])
  stats.value = statsRes
  b0Daily.value = b0Res.data?.slice(0, 10) || []
  b1Daily.value = b1Res.data?.slice(0, 10) || []
  b2Daily.value = b2Res.data?.slice(0, 10) || []
  // 计算近两日信号总数
  const sd = signalRes.data || {}
  let total = 0
  for (const item of [...(sd.daily || []), ...(sd.weekly || [])]) {
    total += (item.s1_count || 0) + (item.s2_count || 0) + (item.s3_count || 0) + (item.sm1_count || 0)
  }
  recentSignals.value = total
})

function goToStock(row) {
  router.push(`/stock/${row.ts_code}`)
}

function getEastmoneyUrl(tsCode) {
  // ts_code格式: 002371.SZ -> https://quote.eastmoney.com/SZ002371.html
  const [code, market] = tsCode.split('.')
  const marketCode = market === 'SH' ? 'SH' : 'SZ'
  return `https://quote.eastmoney.com/${marketCode}${code}.html`
}
</script>

<style scoped>
.stat-cards {
  margin-bottom: 20px;
}
.stat-item {
  text-align: center;
  padding: 10px 0;
}
.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}
.stat-value.primary {
  color: #409eff;
}
.stat-value.warning {
  color: #e6a23c;
}
.stat-label {
  margin-top: 8px;
  color: #909399;
}
.code-link {
  color: #409eff;
  text-decoration: none;
}
.code-link:hover {
  text-decoration: underline;
}
.name-link {
  color: #606266;
  text-decoration: none;
}
.name-link:hover {
  color: #409eff;
}
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
