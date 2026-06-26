<template>
  <div class="detail-layout">
    <div class="sidebar">
      <div class="sidebar-header">选股列表</div>
      <div class="sidebar-filters">
        <el-select v-model="sideStrategy" size="small" style="width:70px" @change="onSideFilterChange">
          <el-option label="全部" value="all" />
          <el-option v-for="s in availableStrategies" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="sidePeriod" size="small" style="width:70px" @change="onSideFilterChange">
          <el-option label="日线" value="daily" />
          <el-option label="周线" value="weekly" />
        </el-select>
        <el-date-picker
          v-if="sideStrategy !== 'all'"
          v-model="sideDate"
          type="date"
          placeholder="选择日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          clearable
          size="small"
          style="width:140px"
          @change="loadSideList"
        />
      </div>
      <div class="sidebar-list" ref="sidebarListRef">
        <div v-for="item in sideList" :key="item.ts_code" class="sidebar-item"
          :class="{ active: item.ts_code === code }"
          :ref="el => { if (item.ts_code === code) activeItemRef = el }"
          @click="switchStock(item.ts_code)">
          <div class="item-code">{{ item.symbol || item.ts_code }}</div>
          <div class="item-name">{{ item.stock_name || item.name || '' }}</div>
          <div class="item-price" v-if="sideStrategy !== 'all'">
            <span>{{ item.close != null ? Number(item.close).toFixed(2) : '' }}</span>
            <span class="item-j">J:{{ item.kdj_j != null ? Number(item.kdj_j).toFixed(1) : '' }}</span>
          </div>
        </div>
        <div v-if="!sideList.length" class="empty">暂无数据</div>
      </div>
    </div>
    <div class="main-content">
      <el-page-header @back="$router.back()">
        <template #content>
          <span class="stock-title">
            <a :href="getEastmoneyUrl(code)" target="_blank" class="name-link">{{ stockInfo.name || code }}</a>
            <a :href="getEastmoneyUrl(code)" target="_blank" class="stock-code code-link">{{ code }}</a>
            <el-link :href="getEastmoneyUrl(code)" target="_blank" type="primary" :underline="false" class="external-link"><el-icon><TopRight /></el-icon></el-link>
          </span>
        </template>
        <template #extra>
          <el-select v-model="klineDays" size="small" style="width:110px;margin-right:12px" @change="onPeriodChange">
            <el-option label="120天" :value="120" />
            <el-option label="250天(1年)" :value="250" />
            <el-option label="500天(2年)" :value="500" />
          </el-select>
          <el-radio-group v-model="klinePeriod" size="small" @change="onPeriodChange">
            <el-radio-button label="daily">日线</el-radio-button>
            <el-radio-button label="weekly">周线</el-radio-button>
          </el-radio-group>
        </template>
      </el-page-header>
      <el-card class="info-card">
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="最新价"><span :class="priceClass">{{ latestClose }}</span></el-descriptions-item>
          <el-descriptions-item label="短期线">{{ latestShortLine }}</el-descriptions-item>
          <el-descriptions-item label="多空线">{{ latestBigLine }}</el-descriptions-item>
          <el-descriptions-item label="J值">{{ latestKdj }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
      <el-card class="chart-card">
        <div ref="chartRef" class="chart"></div>
      </el-card>
      <el-card header="选股记录" class="history-card">
        <el-table :data="screenHistory" size="small" row-key="id" @expand-change="onExpand">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-track" v-loading="row._loading">
                <el-table :data="row._tracks || []" size="small" v-if="row._tracks && row._tracks.length">
                  <el-table-column prop="track_date" label="追踪日期" width="110" />
                  <el-table-column prop="close" label="收盘价" width="90"><template #default="{ row: t }">{{ Number(t.close).toFixed(2) }}</template></el-table-column>
                  <el-table-column prop="s1" label="S1" width="60"><template #default="{ row: t }">{{ t.s1 ? '✓' : '' }}</template></el-table-column>
                  <el-table-column prop="s2" label="S2" width="60"><template #default="{ row: t }">{{ t.s2 ? '✓' : '' }}</template></el-table-column>
                  <el-table-column prop="s3" label="S3" width="60"><template #default="{ row: t }">{{ t.s3 ? '✓' : '' }}</template></el-table-column>
                </el-table>
                <div v-if="row._tracks && !row._tracks.length" class="empty">暂无追踪数据</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="策略" width="60"><template #default="{ row }"><el-tag size="small" :type="row.strategy === 'b1' ? 'danger' : row.strategy === 'b0' ? 'warning' : 'success'">{{ row.strategy?.toUpperCase() }}</el-tag></template></el-table-column>
          <el-table-column label="周期" width="60"><template #default="{ row }">{{ row.period === 'weekly' ? '周线' : '日线' }}</template></el-table-column>
          <el-table-column prop="screen_date" label="选股日期" width="110" />
          <el-table-column prop="close" label="选股收盘价" width="110"><template #default="{ row }">{{ Number(row.close).toFixed(2) }}</template></el-table-column>
          <el-table-column prop="is_track" label="状态" width="80"><template #default="{ row }"><el-tag :type="row.is_track === 1 ? 'success' : 'info'" size="small">{{ row.is_track === 1 ? '追踪中' : '已结束' }}</el-tag></template></el-table-column>
        </el-table>
        <div v-if="!screenHistory.length" class="empty">暂无选股记录</div>
      </el-card>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { TopRight } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import api from '../utils/api'

const route = useRoute()
const router = useRouter()
const code = ref(route.params.code)
const stockInfo = ref({})
const klineData = ref([])
const screenHistory = ref([])
const chartRef = ref()
let chart = null
const klinePeriod = ref('daily')
const klineDays = ref(125)
const sideStrategy = ref('all')
const sidePeriod = ref('daily')
const sideDate = ref('')
const sideList = ref([])
const sidebarListRef = ref(null)
const activeItemRef = ref(null)

const availableStrategies = computed(() => {
  if (sidePeriod.value === 'weekly') return [{ label: 'B1', value: 'b1' }]
  return [
    { label: 'B1', value: 'b1' },
    { label: 'B0', value: 'b0' },
    { label: 'B2', value: 'b2' }
  ]
})

const latestClose = computed(() => klineData.value.length > 0 ? Number(klineData.value[0].close).toFixed(2) : '-')
const latestShortLine = computed(() => klineData.value.length > 0 && klineData.value[0].short_line ? Number(klineData.value[0].short_line).toFixed(3) : '-')
const latestBigLine = computed(() => klineData.value.length > 0 && klineData.value[0].big_line ? Number(klineData.value[0].big_line).toFixed(3) : '-')
const latestKdj = computed(() => klineData.value.length > 0 && klineData.value[0].kdj_j !== null ? Number(klineData.value[0].kdj_j).toFixed(2) : '-')
const priceClass = computed(() => {
  if (klineData.value.length > 0) {
    return Number(klineData.value[0].close) > Number(klineData.value[0].big_line) ? 'up' : 'down'
  }
  return ''
})

function buildSwitchQuery() {
  const q = {}
  if (sideStrategy.value) q.strategy = sideStrategy.value
  if (sidePeriod.value) q.period = sidePeriod.value
  if (sideDate.value) q.date = sideDate.value
  return q
}

watch(() => route.params.code, (newCode) => {
  if (newCode && newCode !== code.value) {
    code.value = newCode
    loadAll()
    loadSideList()
    scrollActiveIntoView()
  }
})

onMounted(() => {
  if (route.query.strategy) sideStrategy.value = route.query.strategy
  if (route.query.period) { sidePeriod.value = route.query.period; klinePeriod.value = route.query.period }
  if (route.query.date) sideDate.value = route.query.date
  loadAll()
  loadSideList()
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => { if (chart) chart.dispose(); window.removeEventListener('keydown', onKeyDown) })

function onKeyDown(e) {
  if (!sideList.value.length) return
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return
  e.preventDefault()
  const idx = sideList.value.findIndex(i => i.ts_code === code.value)
  if (idx === -1) return
  let nextIdx = e.key === 'ArrowUp'
    ? (idx > 0 ? idx - 1 : sideList.value.length - 1)
    : (idx < sideList.value.length - 1 ? idx + 1 : 0)
  const nextStock = sideList.value[nextIdx]
  if (nextStock) router.replace({ path: `/stock/${nextStock.ts_code}`, query: buildSwitchQuery() })
}

function scrollActiveIntoView() {
  nextTick(() => { if (activeItemRef.value) activeItemRef.value.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) })
}

async function loadAll() {
  await Promise.all([loadStockInfo(), loadKline(), loadScreenHistory()])
  nextTick(() => renderChart())
}

async function loadStockInfo() { stockInfo.value = {}; try { stockInfo.value = await api.get(`/stock/${code.value}/info`) } catch (e) {} }

async function loadKline() {
  klineData.value = []
  const res = await api.get(`/stock/${code.value}/kline?period=${klinePeriod.value}&days=${klineDays.value}`)
  klineData.value = (res.data || []).reverse()
}

async function loadScreenHistory() {
  try {
    const res = await api.get(`/stock/${code.value}/screen-history`)
    screenHistory.value = (res.data || []).map(s => ({ ...s, _tracks: null, _loading: false }))
  } catch (e) {
    screenHistory.value = []
  }
}

async function loadSideList() {
  if (sideStrategy.value === 'all') {
    const res = await api.get('/stocks/all')
    sideList.value = res.data || []
  } else {
    const params = sideDate.value ? `?screen_date=${sideDate.value}` : ''
    const res = await api.get(`/screen/${sideStrategy.value}/${sidePeriod.value}${params}`)
    const data = (res.data || []).filter(i => i.amount >= 100000)
    sideList.value = data.sort((a, b) => (a.kdj_j || 0) - (b.kdj_j || 0))
  }
  scrollActiveIntoView()
}

async function onSideFilterChange() {
  if (sideStrategy.value === 'all') { sideDate.value = ''; await loadSideList(); return }
  if (sidePeriod.value === 'weekly' && !['b1'].includes(sideStrategy.value)) sideStrategy.value = 'b1'
  sideDate.value = ''
  await loadSideList()
}

function onPeriodChange() {
  klineData.value = []
  loadKline().then(() => nextTick(() => renderChart()))
}

function switchStock(tsCode) { router.replace({ path: `/stock/${tsCode}`, query: buildSwitchQuery() }) }

function getEastmoneyUrl(tsCode) {
  const [c, m] = tsCode.split('.')
  return `https://quote.eastmoney.com/${m === 'SH' ? 'SH' : 'SZ'}${c}.html`
}

async function onExpand(row, expandedRows) {
  if (!expandedRows.includes(row) || row._tracks !== null) return
  row._loading = true
  try { row._tracks = (await api.get(`/tracking/${row.strategy}/${row.period}/${row.id}`)).data || [] }
  catch (e) { row._tracks = [] }
  row._loading = false
}

function formatAmount(v) { if (!v) return '-'; v = Number(v); return v > 100000 ? (v/100000).toFixed(2)+'亿' : v > 1000 ? (v/1000).toFixed(2)+'万' : v.toFixed(0)+'千' }
function formatVol(v) { if (!v) return '-'; v = Number(v); return v > 100000000 ? (v/100000000).toFixed(2)+'亿' : v > 10000 ? (v/10000).toFixed(2)+'万' : v.toFixed(0) }

function renderChart() {
  if (!chartRef.value || klineData.value.length === 0) return
  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)
  const isDaily = klinePeriod.value === 'daily'
  const dates = klineData.value.map(d => d.trade_date)
  const ohlc = klineData.value.map(d => [d.open, d.close, d.low, d.high])
  const volumes = klineData.value.map(d => d.vol)
  const shortLines = klineData.value.map(d => d.short_line)
  const bigLines = klineData.value.map(d => d.big_line)
  const kdjVals = klineData.value.map(d => d.kdj_j)
  const brickGridIdx = isDaily ? 1 : -1
  const volGridIdx = isDaily ? 2 : 1
  const kdjGridIdx = isDaily ? 3 : 2
  const gridCount = isDaily ? 4 : 3
  const grids = [], xAxes = [], yAxes = []
  const gTop = ['8%','40%','58%','76%']
  const gHeight = ['28%','14%','14%','16%']
  for (let i = 0; i < gridCount; i++) {
    grids.push({ left: '10%', right: '8%', top: gTop[i], height: gHeight[i] })
    xAxes.push({ type: 'category', data: dates, gridIndex: i, axisLabel: { show: i === gridCount-2 }, axisLine: { lineStyle: { color: '#555' } }, splitLine: { show: false } })
    yAxes.push({ scale: true, gridIndex: i, splitLine: { lineStyle: { color: '#333' } }, axisLine: { lineStyle: { color: '#555' } } })
  }
  const allXIdx = Array.from({length: gridCount}, (_, i) => i)
  const series = [
    { name: 'K线', type: 'candlestick', data: ohlc, barWidth: '70%', itemStyle: { color: '#ef5350', color0: '#26a69a', borderColor: '#ef5350', borderColor0: '#26a69a' } },
    { name: '短期线', type: 'line', data: shortLines, smooth: true, lineStyle: { width: 1, color: '#ffffff' }, symbol: 'none' },
    { name: '多空线', type: 'line', data: bigLines, smooth: true, lineStyle: { width: 1, color: '#ffd600' }, symbol: 'none' },
  ]
  if (isDaily) {
    series.push({ name: '砖型图', type: 'custom', xAxisIndex: brickGridIdx, yAxisIndex: brickGridIdx, barWidth: '70%',
      renderItem: (params, api) => {
        const idx = params.dataIndex
        if (idx === 0) return null
        const prev = klineData.value[idx-1]?.brick_value
        const curr = klineData.value[idx]?.brick_value
        if (prev == null || curr == null) return null
        if (prev === 0 && curr === 0) return null
        if (curr === 0 && prev > 0) return null
        const x = api.coord([idx, 0])[0]
        const prevY = api.coord([0, prev])[1]
        const currY = api.coord([0, curr])[1]
        const w = params.coordSys.width
        const cnt = klineData.value.length
        const width = Math.max(6, (w/cnt)*0.8) // 增加宽度至与K线一致
        return { type: 'rect', shape: { x: x-width/2, y: Math.min(prevY,currY), width, height: Math.abs(prevY-currY) || 2 }, style: { fill: prev < curr ? '#ef5350' : '#26a69a' } }
      },
      data: klineData.value.map(d => d.brick_value ?? null), z: 10
    })
  }
  series.push(
    { name: '成交量', type: 'bar', xAxisIndex: volGridIdx, yAxisIndex: volGridIdx, data: volumes,
      itemStyle: { color: p => klineData.value[p.dataIndex]?.close >= klineData.value[p.dataIndex]?.open ? '#ef5350' : '#26a69a' } },
    { name: 'KDJ J', type: 'line', xAxisIndex: kdjGridIdx, yAxisIndex: kdjGridIdx, data: kdjVals,
      smooth: true, lineStyle: { width: 1.5, color: '#ce93d8' }, symbol: 'none', markLine: { silent: true, lineStyle: { color: '#444', type: 'dashed' }, data: [{ yAxis: 100 }, { yAxis: 0 }] } }
  )
  chart.setOption({
    backgroundColor: '#1a1a2e',
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, backgroundColor: 'rgba(30,30,46,0.95)', borderColor: '#555', textStyle: { color: '#ddd' },
      formatter(params) {
        const idx = params[0]?.dataIndex; if (idx == null) return ''
        const d = klineData.value[idx]; if (!d) return ''
        let h = `<div style="font-size:12px;line-height:1.6"><b style="color:#fff">${d.trade_date}</b><br/>`
        h += `开:<span style="color:#ef5350">${Number(d.open).toFixed(2)}</span> 收:<span style="color:#26a69a">${Number(d.close).toFixed(2)}</span><br/>`
        h += `高:${Number(d.high).toFixed(2)} 低:${Number(d.low).toFixed(2)}<br/>`
        h += `成交量:${formatVol(d.vol)}<br/>成交额:${formatAmount(d.amount)}<br/>`
        if (d.short_line) h += `<span style="color:#fff">短期线:${Number(d.short_line).toFixed(3)}</span><br/>`
        if (d.big_line) h += `<span style="color:#ffd600">多空线:${Number(d.big_line).toFixed(3)}</span><br/>`
        if (d.kdj_j != null) h += `<span style="color:#ce93d8">KDJ J:${Number(d.kdj_j).toFixed(2)}</span><br/>`
        if (d.brick_value) h += `砖型图:${Number(d.brick_value).toFixed(2)}<br/>`
        h += `</div>`; return h
      }
    },
    legend: { data: ['K线','成交量','短期线','多空线','KDJ J'], textStyle: { color: '#aaa' } },
    grid: grids, xAxis: xAxes, yAxis: yAxes,
    dataZoom: [{ type: 'inside', xAxisIndex: allXIdx, start: 50, end: 100 }, { show: true, xAxisIndex: allXIdx, type: 'slider', bottom: '1%' }],
    series
  })
  window.addEventListener('resize', () => chart?.resize())
}
</script>
<style scoped>
.detail-layout { display: flex; gap: 16px; min-height: calc(100vh - 120px); }
.sidebar { width: 220px; flex-shrink: 0; background: #fff; border-radius: 4px; display: flex; flex-direction: column; overflow: hidden; height: calc(100vh - 140px); }
.sidebar-header { padding: 12px 16px; font-weight: bold; font-size: 14px; border-bottom: 1px solid #ebeef5; }
.sidebar-filters { padding: 8px 12px; display: flex; gap: 6px; border-bottom: 1px solid #ebeef5; }
.sidebar-list { flex: 1; overflow-y: auto; min-height: 0; }
.sidebar-item { padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #f5f7fa; transition: background 0.15s; }
.sidebar-item:hover { background: #f5f7fa; }
.sidebar-item.active { background: #ecf5ff; border-left: 3px solid #409eff; }
.item-code { font-size: 13px; font-weight: bold; color: #303133; }
.item-name { font-size: 11px; color: #909399; margin-top: 2px; }
.item-price { font-size: 12px; color: #606266; margin-top: 4px; display: flex; justify-content: space-between; }
.item-j { color: #e6a23c; font-size: 11px; }
.main-content { flex: 1; min-width: 0; }
.stock-title { font-size: 18px; font-weight: bold; }
.stock-code { font-size: 14px; margin-left: 8px; font-weight: normal; }
.code-link { color: #409eff; text-decoration: none; }
.code-link:hover { text-decoration: underline; }
.name-link { color: #303133; text-decoration: none; }
.name-link:hover { color: #409eff; }
.external-link { margin-left: 8px; vertical-align: middle; }
.info-card { margin-top: 20px; }
.up { color: #f56c6c; font-weight: bold; }
.down { color: #67c23a; font-weight: bold; }
.chart-card { margin-top: 16px; }
.chart { height: 600px; }
.history-card { margin-top: 16px; }
.empty { text-align: center; color: #909399; padding: 20px; }
.expand-track { padding: 0 20px; }
</style>
