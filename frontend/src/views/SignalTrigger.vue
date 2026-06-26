<template>
  <div class="signal-page">
    <el-card>
      <!-- 筛选条件 -->
      <el-form inline class="filter-form">
        <el-form-item label="触发日期">
          <el-date-picker
            v-model="filters.signal_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            clearable
            @change="loadData"
          />
        </el-form-item>
        <el-form-item label="选股类型">
          <el-select v-model="filters.strategy" placeholder="全部" clearable @change="loadData">
            <el-option label="B0 (金叉)" value="b0" />
            <el-option label="B1 (超卖)" value="b1" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发类型">
          <el-select v-model="filters.signal_type" placeholder="全部" clearable @change="loadData">
            <el-option label="S1 (跌破目标价)" value="s1" />
            <el-option label="S2 (跌破多空线)" value="s2" />
            <el-option label="S3 (趋势转空)" value="s3" />
            <el-option label="SM1" value="sm1" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" @row-dblclick="goToStock" stripe>
        <el-table-column prop="ts_code" label="代码" width="110" fixed>
          <template #default="{ row }">
            <a :href="getEastmoneyUrl(row.ts_code)" target="_blank" class="code-link">{{ row.ts_code }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="stock_name" label="名称" width="100">
          <template #default="{ row }">
            <span class="name-link" @click="goToStock(row)">{{ row.stock_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="screen_date" label="选股日期" width="110" />
        <el-table-column prop="strategy" label="选股类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getStrategyType(row.strategy)" size="small">
              {{ getStrategyLabel(row.strategy) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="signal_type" label="触发类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getSignalTypeColor(row.signal_type)" size="small">
              {{ row.signal_type.toUpperCase() }}
            </el-tag>
            <span class="signal-desc">{{ getSignalDesc(row.signal_type) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="signal_date" label="触发日期" width="110" sortable />
      </el-table>

      <div class="total-info">
        共 {{ tableData.length }} 条信号触发
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../utils/api'

const router = useRouter()
const loading = ref(false)
const tableData = ref([])

const filters = reactive({
  signal_date: null,
  strategy: null,
  signal_type: null
})

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.signal_date) params.signal_date = filters.signal_date
    if (filters.strategy) params.strategy = filters.strategy
    if (filters.signal_type) params.signal_type = filters.signal_type

    const res = await api.get('/signals/triggers', params)
    tableData.value = res.data || []
  } finally {
    loading.value = false
  }
}

function goToStock(row) {
  router.push(`/stock/${row.ts_code}`)
}

function getEastmoneyUrl(tsCode) {
  const [code, market] = tsCode.split('.')
  return `https://quote.eastmoney.com/${market}${code}.html`
}

function getStrategyLabel(strategy) {
  const labels = { b0: 'B0 金叉', b1: 'B1 超卖', b2: 'B2 砖型' }
  return labels[strategy] || strategy
}

function getStrategyType(strategy) {
  const types = { b0: 'success', b1: 'warning', b2: '' }
  return types[strategy] || 'info'
}

function getSignalTypeColor(signalType) {
  const types = { s1: 'danger', s2: 'warning', s3: 'info', sm1: '' }
  return types[signalType] || 'info'
}

function getSignalDesc(signalType) {
  const descs = {
    s1: '跌破目标价',
    s2: '跌破多空线',
    s3: '趋势转空',
    sm1: ''
  }
  return descs[signalType] || ''
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
.signal-desc {
  margin-left: 6px;
  color: #909399;
  font-size: 12px;
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
  cursor: pointer;
}
.name-link:hover {
  color: #409eff;
}
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
