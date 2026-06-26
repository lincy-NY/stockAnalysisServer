<template>
  <div class="screen-page">
    <el-card>
      <!-- 筛选条件 -->
      <el-form inline class="filter-form">
        <el-form-item label="策略">
          <el-select v-model="filters.strategy" @change="onStrategyChange" style="width: 140px">
            <el-option label="B0 (金叉)" value="b0" />
            <el-option label="B1 (超卖)" value="b1" />
            <el-option label="B2 (砖型图)" value="b2" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期">
          <el-select v-model="filters.period" @change="onPeriodChange" style="width: 120px">
            <el-option label="日线" value="daily" />
            <el-option label="周线" value="weekly" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="filters.date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 160px"
            @change="loadData"
          />
        </el-form-item>
        <el-form-item label="成交额">
          <el-select v-model="filters.amountFilter" @change="filterData" clearable placeholder="全部" style="width: 150px">
            <el-option label="全部" value="" />
            <el-option label="≥1亿" value="100000" />
            <el-option label="≥5亿" value="500000" />
            <el-option label="≥10亿" value="1000000" />
            <el-option label="≥20亿" value="2000000" />
            <el-option label="≥50亿" value="5000000" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="exportData" :loading="exportLoading" style="margin-bottom: 16px">
        导出TXT
      </el-button>

      <!-- 数据表格 -->
      <el-table :data="paginatedData" v-loading="loading" @row-dblclick="goToStock" row-class-name="clickable-row">
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
        <el-table-column prop="trade_date" label="交易日期" width="110" />
        <el-table-column prop="short_line" label="短期线" width="90">
          <template #default="{ row }">{{ Number(row.short_line).toFixed(3) }}</template>
        </el-table-column>
        <el-table-column prop="big_line" label="多空线" width="90">
          <template #default="{ row }">{{ Number(row.big_line).toFixed(3) }}</template>
        </el-table-column>
        <el-table-column prop="kdj_j" label="J值" width="80" v-if="filters.strategy === 'b1'">
          <template #default="{ row }">{{ row.kdj_j != null ? Number(row.kdj_j).toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="brick_value" label="砖型图" width="90" v-if="filters.strategy === 'b2'">
          <template #default="{ row }">{{ row.brick_value != null ? Number(row.brick_value).toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="dist_pct" label="距多空%" width="100" v-if="filters.strategy !== 'b0'">
          <template #default="{ row }">{{ row.dist_pct != null ? Number(row.dist_pct).toFixed(2) + '%' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="dist_short" label="距短期%" width="100" v-if="filters.strategy !== 'b0'">
          <template #default="{ row }">{{ row.dist_short != null ? Number(row.dist_short).toFixed(2) + '%' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="vol" label="成交量" width="100">
          <template #default="{ row }">{{ formatVol(row.vol) }}</template>
        </el-table-column>
        <el-table-column prop="amount" label="成交额" width="100">
          <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="is_track" label="状态" width="70">
          <template #default="{ row }">
            <el-tag :type="row.is_track === 1 ? 'success' : 'info'" size="small">
              {{ row.is_track === 1 ? '追踪' : '结束' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="goToStock(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredData.length"
          layout="total, sizes, prev, pager, next"
          background
        />
      </div>

      <div class="total-info">
        共 {{ filteredData.length }} 条记录（总计 {{ tableData.length }} 条）
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../utils/api'
import axios from 'axios'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const exportLoading = ref(false)
const tableData = ref([])
const filters = reactive({
  strategy: route.query.strategy || 'b1',
  period: route.query.period || 'daily',
  date: '',
  amountFilter: '100000'
})
const currentPage = ref(1)
const pageSize = ref(20)

const filteredData = computed(() => {
  if (!filters.amountFilter) {
    return tableData.value
  }
  const minAmount = Number(filters.amountFilter)
  return tableData.value.filter(row => {
    const amount = Number(row.amount) || 0
    return amount >= minAmount
  })
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredData.value.slice(start, start + pageSize.value)
})

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const params = filters.date ? `?screen_date=${filters.date}` : ''
    const res = await api.get(`/screen/${filters.strategy}/${filters.period}${params}`)
    tableData.value = res.data || []
    currentPage.value = 1
  } finally {
    loading.value = false
  }
}

async function onStrategyChange() {
  filters.date = ''
  currentPage.value = 1
  // B2仅支持日线
  if (filters.strategy === 'b2') {
    filters.period = 'daily'
  }
  await loadData()
}

function onPeriodChange() {
  currentPage.value = 1
  // 周线仅支持B1
  if (filters.period === 'weekly' && filters.strategy !== 'b1') {
    filters.strategy = 'b1'
  }
  loadData()
}

function filterData() {
  // 筛选已通过computed自动完成
}

function formatVol(vol) {
  if (!vol) return '-'
  const v = Number(vol)
  if (v > 100000000) return (v / 100000000).toFixed(2) + '亿'
  if (v > 10000) return (v / 10000).toFixed(2) + '万'
  return v.toFixed(0)
}

function formatAmount(amount) {
  if (!amount) return '-'
  const v = Number(amount)
  // amount单位是千元
  if (v > 100000) return (v / 100000).toFixed(2) + '亿'
  if (v > 1000) return (v / 1000).toFixed(2) + '万'
  return v.toFixed(0) + '千'
}

function getEastmoneyUrl(tsCode) {
  const [code, market] = tsCode.split('.')
  const marketCode = market === 'SH' ? 'SH' : 'SZ'
  return `https://quote.eastmoney.com/${marketCode}${code}.html`
}

function goToStock(row) {
  router.push({
    path: `/stock/${row.ts_code}`,
    query: {
      strategy: filters.strategy,
      period: filters.period,
      date: filters.date || undefined,
      from: 'screen'
    }
  })
}

async function exportData() {
  exportLoading.value = true
  try {
    const userStore = useUserStore()
    const params = new URLSearchParams()
    if (filters.date) params.append('screen_date', filters.date)
    if (filters.amountFilter) params.append('min_amount', filters.amountFilter)
    
    const url = `/screen/${filters.strategy}/${filters.period}/export?${params.toString()}`
    
    // 使用原始 axios 实例获取二进制数据
    const response = await axios.get(url, {
      baseURL: '/api',
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      },
      responseType: 'blob'
    })
    
    // 创建 Blob 并下载
    const blob = new Blob([response.data], { type: 'text/plain' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${filters.strategy}_${filters.period}_${filters.date || 'latest'}.txt`
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (error) {
    console.error('导出失败:', error)
  } finally {
    exportLoading.value = false
  }
}
</script>

<style scoped>
.filter-form {
  margin-bottom: 16px;
}
.filter-form :deep(.el-form-item) {
  margin-bottom: 12px;
}
.total-info {
  margin-top: 12px;
  color: #909399;
  font-size: 13px;
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
.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
