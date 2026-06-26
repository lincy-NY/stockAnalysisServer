<template>
  <teleport to="body">
    <div v-if="visible" class="search-overlay" @click.self="close">
      <div class="search-modal">
        <div class="search-input-wrap">
          <el-icon class="search-icon"><Search /></el-icon>
          <input
            ref="inputRef"
            v-model="query"
            class="search-input"
            placeholder="输入股票代码或名称搜索..."
            @input="onSearch"
            @keydown.down.prevent="moveDown"
            @keydown.up.prevent="moveUp"
            @keydown.enter.prevent="selectCurrent"
            @keydown.escape="close"
          />
          <span class="search-hint">ESC关闭</span>
        </div>
        <div class="search-results" v-if="results.length > 0">
          <div
            v-for="(item, idx) in results"
            :key="item.ts_code"
            class="search-item"
            :class="{ active: idx === activeIndex }"
            @mouseenter="activeIndex = idx"
            @click="goDetail(item)"
          >
            <span class="stock-code">{{ item.symbol }}</span>
            <span class="stock-name">{{ item.name }}</span>
            <span class="stock-industry" v-if="item.industry">{{ item.industry }}</span>
          </div>
        </div>
        <div class="search-empty" v-else-if="query.length > 0 && !loading">
          未找到匹配的股票
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import api from '../utils/api'

const router = useRouter()
const visible = ref(false)
const query = ref('')
const results = ref([])
const activeIndex = ref(0)
const loading = ref(false)
const inputRef = ref(null)
let searchTimer = null

function open() {
  visible.value = true
  query.value = ''
  results.value = []
  activeIndex.value = 0
  nextTick(() => inputRef.value?.focus())
}

function close() {
  visible.value = false
  query.value = ''
  results.value = []
}

async function doSearch() {
  if (!query.value.trim()) {
    results.value = []
    return
  }
  loading.value = true
  try {
    const res = await api.get(`/stock/search?q=${encodeURIComponent(query.value.trim())}`)
    results.value = res.data || []
    activeIndex.value = 0
  } catch (e) {
    results.value = []
  }
  loading.value = false
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(doSearch, 200)
}

function moveDown() {
  if (activeIndex.value < results.value.length - 1) activeIndex.value++
}
function moveUp() {
  if (activeIndex.value > 0) activeIndex.value--
}
function selectCurrent() {
  if (results.value[activeIndex.value]) {
    goDetail(results.value[activeIndex.value])
  }
}

function goDetail(item) {
  close()
  router.push(`/stock/${item.ts_code}`)
}

// 全局键盘监听
function onGlobalKeydown(e) {
  // 已打开时不处理
  if (visible.value) return
  // 忽略修饰键、功能键、快捷键
  if (e.ctrlKey || e.altKey || e.metaKey) return
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return
  // 只响应字母和数字键
  if (e.key.length === 1 && /[a-zA-Z0-9]/.test(e.key)) {
    e.preventDefault()
    open()
    query.value = e.key
    onSearch()
  }
}

onMounted(() => {
  document.addEventListener('keydown', onGlobalKeydown)
})
onUnmounted(() => {
  document.removeEventListener('keydown', onGlobalKeydown)
})

// 暴露open方法供外部调用
defineExpose({ open })
</script>

<style scoped>
.search-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  z-index: 9999;
  display: flex;
  justify-content: center;
  padding-top: 100px;
}
.search-modal {
  width: 520px;
  max-height: 500px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  overflow: hidden;
  align-self: flex-start;
}
.search-input-wrap {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}
.search-icon {
  font-size: 20px;
  color: #909399;
  margin-right: 12px;
}
.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 16px;
  color: #303133;
}
.search-input::placeholder {
  color: #c0c4cc;
}
.search-hint {
  font-size: 12px;
  color: #c0c4cc;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}
.search-results {
  max-height: 400px;
  overflow-y: auto;
}
.search-item {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  cursor: pointer;
  transition: background 0.15s;
}
.search-item:hover,
.search-item.active {
  background: #f5f7fa;
}
.stock-code {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  width: 80px;
}
.stock-name {
  font-size: 14px;
  color: #303133;
  flex: 1;
}
.stock-industry {
  font-size: 12px;
  color: #909399;
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 4px;
}
.search-empty {
  padding: 30px 20px;
  text-align: center;
  color: #c0c4cc;
  font-size: 14px;
}
</style>
