<template>
  <div class="tracking-page">
    <el-card>
      <!-- 筛选条件 -->
      <el-form inline class="filter-form">
        <el-form-item label="策略">
          <el-select v-model="filters.strategy" @change="loadData">
            <el-option label="B0 (金叉)" value="b0" />
            <el-option label="B1 (超卖)" value="b1" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期">
          <el-select v-model="filters.period" @change="loadData">
            <el-option label="日线" value="daily" />
            <el-option label="周线" value="weekly" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading">
        <el-table-column prop="ts_code" label="代码" width="110" fixed>
          <template #default="{ row }">
            <a :href="getEastmoneyUrl(row.ts_code)" target="_blank" class="code-link">{{ row.ts_code }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="stock_name" label="名称" width="100">
          <template #default="{ row }">
            <a :href="getEastmoneyUrl(row.ts_code)" target="_blank" class="name-link">{{ row.stock_name || '-' }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="screen_date" label="选股日期" width="110" />
        <el-table-column prop="close" label="选股收盘价" width="100">
          <template #default="{ row }">{{ Number(row.close).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="low_price" label="选股最低价" width="100">
          <template #default="{ row }">{{ Number(row.low_price).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="track_close" label="最新收盘" width="100">
          <template #default="{ row }">
            {{ row.track_close ? Number(row.track_close).toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="涨跌幅" width="100">
          <template #default="{ row }">
            <span v-if="row.track_close && row.close" 
                  :class="getChangeClass(row.track_close, row.close)">
              {{ getChange(row.track_close, row.close) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="track_date" label="最新追踪" width="110" />
        <el-table-column label="信号" width="150">
          <template #default="{ row }">
            <span>
              <el-tag v-if="row.s1 === 1" type="danger" size="small" class="signal-tag">S1</el-tag>
              <el-tag v-if="row.s2 === 1" type="warning" size="small" class="signal-tag">S2</el-tag>
              <el-tag v-if="row.s3 === 1" type="info" size="small" class="signal-tag">S3</el-tag>
              <span v-if="!row.s1 && !row.s2 && !row.s3" class="no-signal">-</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="showDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="total-info">
        共 {{ tableData.length }} 条追踪中
      </div>
    </el-card>

    <!-- 追踪详情弹窗 -->
    <el-dialog v-model="detailVisible" title="追踪历史" width="800px">
      <el-table :data="trackHistory" max-height="400">
        <el-table-column prop="track_date" label="追踪日期" width="120" />
        <el-table-column prop="close" label="收盘价" width="100">
          <template #default="{ row }">{{ Number(row.close).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="low" label="最低价" width="100">
          <template #default="{ row }">{{ Number(row.low).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="short_line" label="短期线" width="100">
          <template #default="{ row }">{{ Number(row.short_line).toFixed(3) }}</template>
        </el-table-column>
        <el-table-column prop="big_line" label="多空线" width="100">
          <template #default="{ row }">{{ Number(row.big_line).toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="信号" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.s1 === 1" type="danger" size="small" class="signal-tag">S1</el-tag>
            <el-tag v-if="row.s2 === 1" type="warning" size="small" class="signal-tag">S2</el-tag>
            <el-tag v-if="row.s3 === 1" type="info" size="small" class="signal-tag">S3</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '../utils/api'

const loading = ref(false)
const tableData = ref([])
const detailVisible = ref(false)
const trackHistory = ref([])
const filters = reactive({
  strategy: 'b0',
  period: 'daily'
})

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const res = await api.get(`/tracking/${filters.strategy}/${filters.period}`)
    tableData.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function showDetail(row) {
  detailVisible.value = true
  const res = await api.get(`/tracking/${filters.strategy}/${filters.period}/${row.id}`)
  trackHistory.value = res.data || []
}

function getEastmoneyUrl(tsCode) {
  const [code, market] = tsCode.split('.')
  const marketCode = market === 'SH' ? 'SH' : 'SZ'
  return `https://quote.eastmoney.com/${marketCode}${code}.html`
}

function getChange(current, base) {
  const change = ((current - base) / base * 100).toFixed(2)
  return change > 0 ? `+${change}%` : `${change}%`
}

function getChangeClass(current, base) {
  const change = (current - base) / base * 100
  return change > 0 ? 'up' : change < 0 ? 'down' : ''
}
</script>

<style scoped>
.filter-form {
  margin-bottom: 16px;
}
.total-info {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
}
.signal-tag {
  margin-right: 4px;
}
.no-signal {
  color: #c0c4cc;
}
.up {
  color: #f56c6c;
}
.down {
  color: #67c23a;
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
</style>
