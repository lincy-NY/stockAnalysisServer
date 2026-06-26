<template>
  <div class="position-page">
    <el-card>
      <!-- 筛选条件 -->
      <el-form inline class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="filters.status" @change="loadData" clearable placeholder="全部" style="width: 140px">
            <el-option label="持仓中" value="holding" />
            <el-option label="已卖出" value="sold" />
            <el-option label="部分卖出" value="partial_sold" />
          </el-select>
        </el-form-item>
        <el-form-item label="策略">
          <el-select v-model="filters.strategy" @change="loadData" clearable placeholder="全部" style="width: 120px">
            <el-option label="B0" value="b0" />
            <el-option label="B1" value="b1" />
            <el-option label="B2" value="b2" />
            <el-option label="B3" value="b3" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">刷新</el-button>
        </el-form-item>
      </el-form>

      <!-- 统计信息 -->
      <el-row :gutter="16" class="stats-row">
        <el-col :span="6">
          <el-statistic title="持仓数量" :value="stats.holding_count" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="总市值" :value="stats.total_value" precision="2" suffix="元" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="总盈亏" :value="stats.total_profit_loss" precision="2" suffix="元" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="盈亏比例" :value="stats.profit_loss_pct" precision="2" suffix="%" />
        </el-col>
      </el-row>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" style="margin-top: 20px">
        <el-table-column prop="ts_code" label="代码" width="110">
          <template #default="{ row }">
            <a :href="getEastmoneyUrl(row.ts_code)" target="_blank" class="code-link">{{ row.ts_code }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="stock_name" label="名称" width="100" />
        <el-table-column prop="strategy" label="策略" width="70" />
        <el-table-column prop="buy_date" label="买入日期" width="110" />
        <el-table-column prop="buy_price" label="买入价" width="90">
          <template #default="{ row }">{{ row.buy_price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="buy_amount" label="持仓数" width="80" />
        <el-table-column prop="buy_total" label="买入总额" width="100">
          <template #default="{ row }">{{ row.buy_total?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="current_price" label="现价" width="90">
          <template #default="{ row }">{{ row.current_price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="current_value" label="市值" width="100">
          <template #default="{ row }">{{ row.current_value?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="profit_loss" label="盈亏" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.profit_loss >= 0 ? '#f56c6c' : '#67c23a' }">
              {{ (row.profit_loss >= 0 ? '+' : '') + row.profit_loss?.toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_loss_pct" label="盈亏%" width="90">
          <template #default="{ row }">
            <span :style="{ color: row.profit_loss_pct >= 0 ? '#f56c6c' : '#67c23a' }">
              {{ (row.profit_loss_pct >= 0 ? '+' : '') + row.profit_loss_pct?.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'holding'" type="success" size="small">持仓中</el-tag>
            <el-tag v-else-if="row.status === 'sold'" type="info" size="small">已卖出</el-tag>
            <el-tag v-else type="warning" size="small">部分卖出</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'holding'" type="primary" link size="small" @click="openSellDialog(row)">
              卖出
            </el-button>
            <el-button type="default" link size="small" @click="goToStock(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 卖出弹窗 -->
    <el-dialog v-model="sellDialogVisible" title="卖出股票" width="500px">
      <el-form :model="sellForm" :rules="sellRules" ref="sellFormRef" label-width="100px">
        <el-form-item label="股票代码">
          <el-input v-model="sellForm.ts_code" disabled />
        </el-form-item>
        <el-form-item label="持仓数量">
          <el-input v-model="sellForm.max_amount" disabled>
            <template #append>股</template>
          </el-input>
        </el-form-item>
        <el-form-item label="当前价格">
          <el-input v-model="sellForm.current_price" disabled>
            <template #append>元</template>
          </el-input>
        </el-form-item>
        <el-form-item label="卖出日期" prop="sell_date">
          <el-date-picker
            v-model="sellForm.sell_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="卖出数量" prop="sell_amount">
          <el-input-number v-model="sellForm.sell_amount" :min="100" :max="sellForm.max_amount" :step="100" style="width: 100%">
            <template #append>股</template>
          </el-input-number>
        </el-form-item>
        <el-form-item label="卖出均价" prop="sell_price">
          <el-input-number v-model="sellForm.sell_price" :min="0.01" :precision="2" style="width: 100%">
            <template #append>元</template>
          </el-input-number>
        </el-form-item>
        <el-form-item label="预计盈亏">
          <el-input :value="expectedProfit" disabled>
            <template #append>元</template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sellDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSell" :loading="sellLoading">确认卖出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getPositionList, sellStock } from '../utils/api'

const router = useRouter()

const loading = ref(false)
const tableData = ref([])
const stats = ref({
  holding_count: 0,
  total_value: 0,
  total_profit_loss: 0,
  profit_loss_pct: 0
})

const filters = reactive({
  status: 'holding',
  strategy: ''
})

// 卖出弹窗
const sellDialogVisible = ref(false)
const sellLoading = ref(false)
const sellFormRef = ref(null)

const sellForm = reactive({
  position_id: null,
  ts_code: '',
  max_amount: 0,
  current_price: 0,
  sell_date: new Date().toISOString().split('T')[0],
  sell_amount: 100,
  sell_price: 0
})

const sellRules = {
  sell_date: [{ required: true, message: '请选择卖出日期', trigger: 'change' }],
  sell_amount: [{ required: true, message: '请输入卖出数量', trigger: 'blur' }],
  sell_price: [{ required: true, message: '请输入卖出均价', trigger: 'blur' }]
}

const expectedProfit = computed(() => {
  return ((sellForm.sell_price - sellForm.current_price) * sellForm.sell_amount).toFixed(2)
})

onMounted(() => {
  loadData()
  loadStats()
})

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.strategy) params.strategy = filters.strategy
    
    const response = await getPositionList(params)
    tableData.value = response.items || []
  } catch (error) {
    console.error('加载持仓数据失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await getPositionStats()
    stats.value = response
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

function openSellDialog(row) {
  sellForm.position_id = row.id
  sellForm.ts_code = row.ts_code
  sellForm.max_amount = row.buy_amount
  sellForm.current_price = row.current_price || row.buy_price
  sellForm.sell_date = new Date().toISOString().split('T')[0]
  sellForm.sell_amount = 100
  sellForm.sell_price = row.current_price || row.buy_price
  sellDialogVisible.value = true
}

async function handleSell() {
  try {
    await sellFormRef.value.validate()
    
    sellLoading.value = true
    const response = await sellStock({
      position_id: sellForm.position_id,
      sell_date: sellForm.sell_date,
      sell_price: sellForm.sell_price,
      sell_amount: sellForm.sell_amount
    })
    
    ElMessage.success(`卖出成功，盈亏：${response.profit_loss >= 0 ? '+' : ''}${response.profit_loss.toFixed(2)}元`)
    sellDialogVisible.value = false
    loadData()
    loadStats()
  } catch (error) {
    if (error.response) {
      ElMessage.error(error.response.data.detail || '卖出失败')
    }
  } finally {
    sellLoading.value = false
  }
}

function goToStock(row) {
  router.push(`/stock/${row.ts_code}`)
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
.stats-row {
  margin: 20px 0;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.code-link {
  color: #409eff;
  text-decoration: none;
}
.code-link:hover {
  text-decoration: underline;
}
</style>