import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'screen', name: 'Screen', component: () => import('../views/Screen.vue') },
      { path: 'signals', name: 'SignalTrigger', component: () => import('../views/SignalTrigger.vue') },
      { path: 'tasks', name: 'Tasks', component: () => import('../views/Tasks.vue') },
      { path: 'position', name: 'Position', component: () => import('../views/Position.vue') },
      { path: 'trade', name: 'Trade', component: () => import('../views/Trade.vue') },
      { path: 'stock/:code', name: 'StockDetail', component: () => import('../views/StockDetail.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth !== false && !userStore.token) {
    next('/login')
  } else {
    next()
  }
})

export default router
