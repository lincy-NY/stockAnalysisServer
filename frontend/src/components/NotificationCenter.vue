<template>
  <div class="notification-center">
    <el-badge :value="unreadCount" :hidden="unreadCount === 0" type="danger" :max="99">
      <el-button circle @click="toggleDropdown" :icon="Bell" />
    </el-badge>
    
    <div v-if="dropdownVisible" class="dropdown">
      <div class="dropdown-header">
        <span>消息通知</span>
        <el-button
          v-if="unreadCount > 0"
          text
          type="primary"
          size="small"
          @click="markAllRead"
        >
          全部标为已读
        </el-button>
      </div>
      
      <div v-loading="loading" class="dropdown-content">
        <div v-if="alerts.length === 0" class="empty">
          暂无未读消息
        </div>
        
        <div v-else class="alert-list">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="alert-item"
          >
            <div class="alert-title">
              {{ alert.stock_name }} 触发卖点
            </div>
            <div class="alert-info">
              类型：{{ alertTypeMap[alert.alert_type] }}（{{ alertTypeDescMap[alert.alert_type] }}）
            </div>
            <div class="alert-info">
              日期：{{ alert.alert_date }}  价格：{{ alert.alert_price }}元
            </div>
            <div class="alert-actions">
              <el-button text type="primary" size="small" @click="viewDetail(alert)">
                查看详情
              </el-button>
              <el-button text size="small" @click="markRead(alert.id)">
                已读
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getUnreadCount, getUnreadAlerts, markAlertRead, markAllAlertsRead } from '@/utils/api'

const emit = defineEmits(['viewPosition'])

const dropdownVisible = ref(false)
const loading = ref(false)
const unreadCount = ref(0)
const alerts = ref([])

const alertTypeMap = {
  s1: 's1',
  s2: 's2',
  s3: 's3',
  sm1: 'sm1'
}

const alertTypeDescMap = {
  s1: '跌破目标价',
  s2: '跌破多空线',
  s3: '短期线低于多空线',
  sm1: 'MACD绿柱'
}

let refreshInterval = null

const loadUnreadCount = async () => {
  try {
    const res = await getUnreadCount()
    unreadCount.value = res.count
  } catch (error) {
    console.error('加载未读数量失败:', error)
  }
}

const loadUnreadAlerts = async () => {
  loading.value = true
  try {
    const res = await getUnreadAlerts()
    alerts.value = res.items
  } catch (error) {
    console.error('加载未读消息失败:', error)
  } finally {
    loading.value = false
  }
}

const toggleDropdown = async () => {
  dropdownVisible.value = !dropdownVisible.value
  if (dropdownVisible.value) {
    await loadUnreadAlerts()
  }
}

const markRead = async (alertId) => {
  try {
    await markAlertRead(alertId)
    alerts.value = alerts.value.filter(a => a.id !== alertId)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    ElMessage.success('已标记为已读')
  } catch (error) {
    ElMessage.error('标记失败')
  }
}

const markAllRead = async () => {
  try {
    const res = await markAllAlertsRead()
    alerts.value = []
    unreadCount.value = 0
    ElMessage.success(`已全部标记为已读（${res.count}条）`)
  } catch (error) {
    ElMessage.error('标记失败')
  }
}

const viewDetail = (alert) => {
  dropdownVisible.value = false
  emit('viewPosition', alert.position_id)
}

// 点击外部关闭
const handleClickOutside = (e) => {
  const center = document.querySelector('.notification-center')
  if (center && !center.contains(e.target)) {
    dropdownVisible.value = false
  }
}

onMounted(() => {
  loadUnreadCount()
  document.addEventListener('click', handleClickOutside)
  
  // 每分钟刷新一次未读数量
  refreshInterval = setInterval(loadUnreadCount, 60000)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.notification-center {
  position: relative;
  display: inline-block;
}

.dropdown {
  position: absolute;
  right: 0;
  top: 40px;
  width: 400px;
  max-height: 500px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 1000;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  font-weight: 600;
}

.dropdown-content {
  max-height: 400px;
  overflow-y: auto;
}

.empty {
  padding: 40px;
  text-align: center;
  color: #999;
}

.alert-list {
  padding: 8px 0;
}

.alert-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.alert-item:last-child {
  border-bottom: none;
}

.alert-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: #333;
}

.alert-info {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.alert-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>