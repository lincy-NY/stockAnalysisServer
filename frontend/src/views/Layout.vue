<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">
        <span>📊</span> 选股系统
      </div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/">
          <el-icon><DataLine /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/screen">
          <el-icon><Search /></el-icon>
          <span>选股结果</span>
        </el-menu-item>
        <el-menu-item index="/signals">
          <el-icon><Bell /></el-icon>
          <span>信号触发</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><Timer /></el-icon>
          <span>定时任务</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>{{ title }}</span>
        <div class="header-right">
          <div class="search-trigger" @click="searchRef?.open()">
            <el-icon><Search /></el-icon>
            <span class="search-placeholder">搜索股票...</span>
            <span class="search-hint">按任意键搜索</span>
          </div>
          <NotificationCenter />
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              {{ userStore.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
    <GlobalSearch ref="searchRef" />
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import GlobalSearch from '../components/GlobalSearch.vue'
import NotificationCenter from '../components/NotificationCenter.vue'

const searchRef = ref(null)

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const title = computed(() => {
  const titles = {
    '/': '仪表盘',
    '/screen': '选股结果',
    '/signals': '信号触发'
  }
  return titles[route.path] || '选股系统'
})

function handleCommand(cmd) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}
.aside {
  background: #304156;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #3a4a5e;
}
.el-menu {
  border-right: none;
  background: transparent;
}
:deep(.el-menu-item) {
  color: #bfcbd9;
}
:deep(.el-menu-item:hover),
:deep(.el-menu-item.is-active) {
  background: #263445;
  color: #409eff;
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.search-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 20px;
  cursor: pointer;
  color: #909399;
  font-size: 13px;
  transition: all 0.2s;
}
.search-trigger:hover {
  border-color: #409eff;
  color: #409eff;
}
.search-placeholder {
  color: #c0c4cc;
}
.search-hint {
  font-size: 11px;
  background: #ebeef5;
  padding: 1px 6px;
  border-radius: 3px;
  color: #909399;
}
.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
}
.main {
  background: #f5f7fa;
  padding: 20px;
}
</style>
