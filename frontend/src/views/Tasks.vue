<template>
  <div class="tasks">
    <div class="header-row">
      <h2>定时任务</h2>
      <el-button type="primary" size="small" @click="fetchTasks" :loading="loading">
        刷新状态
      </el-button>
    </div>

    <div class="task-cards">
      <el-card v-for="task in tasks" :key="task.id" class="task-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="task-name">{{ task.name }}</span>
            <el-tag :type="statusTag(task)" size="small">{{ statusText(task) }}</el-tag>
          </div>
        </template>
        <div class="task-info">
          <div class="info-row">
            <span class="label">调度：</span>
            <span>{{ task.schedule }}</span>
          </div>
          <div class="info-row">
            <span class="label">下次执行：</span>
            <span>{{ formatTime(task.next_run) }}</span>
          </div>
          <div class="info-row" v-if="task.last_run">
            <span class="label">上次执行：</span>
            <span>{{ formatTime(task.last_run) }}</span>
          </div>
          <div class="info-row" v-if="task.last_duration != null">
            <span class="label">耗时：</span>
            <span>{{ task.last_duration }}秒</span>
          </div>
        </div>
        <div class="task-actions">
          <el-button
            type="primary"
            size="small"
            :loading="runningId === task.id"
            @click="runTask(task.id)"
          >
            {{ runningId === task.id ? '执行中...' : '手动执行' }}
          </el-button>
          <el-button size="small" @click="viewLogs(task.id)">执行日志</el-button>
        </div>
      </el-card>
    </div>

    <!-- 执行日志弹窗 -->
    <el-dialog v-model="logDialog" title="执行日志" width="700px" destroy-on-close>
      <el-table :data="logs" style="width: 100%" max-height="400" size="small">
        <el-table-column prop="task_name" label="任务" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : row.status === 'skipped' ? 'info' : 'warning'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160" />
        <el-table-column prop="duration_sec" label="耗时(秒)" width="90" />
        <el-table-column label="输出">
          <template #default="{ row }">
            <el-popover placement="left" :width="500" trigger="click">
              <template #reference>
                <el-button type="primary" link size="small">查看</el-button>
              </template>
              <pre class="log-output">{{ row.output }}</pre>
            </el-popover>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button size="small" type="danger" plain @click="clearLogs">清空日志</el-button>
      </template>
    </el-dialog>

    <!-- 执行结果弹窗 -->
    <el-dialog v-model="resultDialog" title="执行结果" width="600px" destroy-on-close>
      <pre class="log-output">{{ resultOutput }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'

const tasks = ref([])
const logs = ref([])
const loading = ref(false)
const runningId = ref(null)
const logDialog = ref(false)
const resultDialog = ref(false)
const resultOutput = ref('')

async function fetchTasks() {
  loading.value = true
  try {
    const { data } = await api.get('/tasks')
    tasks.value = data
  } catch (e) {
    ElMessage.error('获取任务列表失败')
  }
  loading.value = false
}

async function runTask(taskId) {
  runningId.value = taskId
  try {
    const { data } = await api.post(`/tasks/${taskId}/run`)
    resultOutput.value = data.output || '执行完成'
    resultDialog.value = true
    if (data.success) {
      ElMessage.success('执行成功')
    } else {
      ElMessage.warning('执行失败，查看详情')
    }
    await fetchTasks()
  } catch (e) {
    ElMessage.error('执行请求失败')
  }
  runningId.value = null
}

async function viewLogs(taskId) {
  try {
    const { data } = await api.get('/tasks/logs', { params: { task_id: taskId, limit: 30 } })
    logs.value = data
    logDialog.value = true
  } catch (e) {
    ElMessage.error('获取日志失败')
  }
}

async function clearLogs() {
  try {
    await ElMessageBox.confirm('确定清空所有执行日志？', '确认')
    await api.delete('/tasks/logs')
    logs.value = []
    ElMessage.success('已清空')
  } catch {}
}

function statusTag(task) {
  if (!task.last_status) return 'info'
  if (task.last_status === 'success') return 'success'
  if (task.last_status === 'failed') return 'danger'
  if (task.last_status === 'skipped') return 'info'
  return 'warning'
}

function statusText(task) {
  if (!task.last_status) return '未执行'
  const map = { success: '成功', failed: '失败', skipped: '已跳过', running: '执行中' }
  return map[task.last_status] || task.last_status
}

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

onMounted(fetchTasks)
</script>

<style scoped>
.tasks {
  padding: 0;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-row h2 {
  margin: 0;
  font-size: 18px;
}
.task-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.task-name {
  font-weight: 600;
  font-size: 15px;
}
.task-info {
  margin-bottom: 12px;
}
.info-row {
  display: flex;
  margin-bottom: 6px;
  font-size: 13px;
  color: #606266;
}
.info-row .label {
  color: #909399;
  width: 80px;
  flex-shrink: 0;
}
.task-actions {
  display: flex;
  gap: 8px;
}
.log-output {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
