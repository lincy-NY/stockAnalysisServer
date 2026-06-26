import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

api.interceptors.request.use(config => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      window.location.href = '/login'
    } else {
      ElMessage.error(error.response?.data?.detail || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default api

// ==================== 交易管理 ====================

export const buyStock = (data) => api.post('/position/buy', data)

export const addPosition = (data) => api.post('/position/add', data)

export const createPositionDirect = (data) => api.post('/position/add', data)

export const getPositionList = (params) => api.get('/position/list', { params })

export const getPositionDetail = (positionId) => api.get(`/position/${positionId}`)

export const sellStock = (data) => api.post('/position/sell', data)

export const getTradeList = (params) => api.get('/trade/list', { params })

export const getUnreadCount = () => api.get('/alert/unread-count')

export const getUnreadAlerts = () => api.get('/alert/unread')

export const markAlertRead = (alertId) => api.put(`/alert/${alertId}/read`)

export const markAllAlertsRead = () => api.put('/alert/read-all')

export const getPositionStats = () => api.get('/position/stats')
