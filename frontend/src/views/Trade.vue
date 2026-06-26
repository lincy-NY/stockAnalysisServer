<template>
  <div class="trade-page">
    <el-card>
      <!-- 筛选条件 -->
      <el-form inline class="filter-form">
        <el-form-item label="股票代码">
          <el-input v-model="filters.ts_code" placeholder="输入代码" clearable style="width: 140px" @change="loadData" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading">
        <el-table-column prop="ts_code" label="代码" width="110">
          <template #default="{ row }">
            <a :href="getEastmoneyUrl(row.ts_code)" target="_blank" class="code-link">{{ row.ts_code }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="stock_name" label="名称" width="100" />
        <el-table-column prop="trade_type" label="类型" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.trade_type === 'buy'" type="success" size="small">买入</el-tag>
            <el-tag v-else-if="row.trade_type === 'sell'" type="danger" size="small">卖出</el-tag>
            <el-tag v-else type="warning" size="small">部分卖出</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trade_date" label="交易日期" width="110" />
        <el-table-column prop="trade_price" label="成交价" width="90">
          <template #default="{ row }">{{ row.trade_price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="trade_amount" label="成交数量" width="100">
          <template #default="{ row }">{{ row.trade_amount }}股</template>
        </el-table-column>
        <el-table-column prop="trade_total" label="成交金额" width="110">
          <template #default="{ row }">{{ row.trade_total?.toFixed(2) }}元</template>
        </el-table-column>
        <el-table-column prop="profit_loss" label="盈亏" width="100">
          <template #default="{ row }">
            <span v-if="row.profit_loss !== null" :style="{ color: row.profit_loss >= 0 ? '#f56c6c' : '#67c23a' }">
              {{ (row.profit_loss >= 0 ? '+' : '') + row.profit_loss.toFixed(2) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadData"
          @size-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getTradeList } from '../utils/api'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const filters = reactive({
  ts_code: ''
})

const currentPage = ref(1)
const pageSize = ref(20)

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (filters.ts_code) params.ts_code = filters.ts_code
    
    const response = await getTradeList(params)
    tableData.value = response.items || []
    total.value = response.total || 0
  } catch (error) {
    console.error('加载交易记录失败:', error)
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.ts_code = ''
  currentPage.value = 1
  loadData()
}

function formatTime(time) {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getEastmoneyUrl(tsCode) {
  const [code, market] = tsCode.split('.')
  const marketCode = market === 'SH' ? 'SH' : 'SZ'
  return `https://quote.eastmoney.com/${marketCode}${code}.html`
}
</script>

<style scoped>
.filter-form {
  margin-bottom: 16px;
}
.code-link {
  color: #409eff;
  text-decoration: none;
}
.code-link:hover {
  text-decoration: underline;
}
.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>