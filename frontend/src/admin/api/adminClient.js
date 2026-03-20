import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'

const api = axios.create({ baseURL: BASE })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('admin_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_email')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const login = (email, password) =>
  api.post('/admin/auth/login', { email, password }).then(r => r.data)

export const getOverview = () =>
  api.get('/admin/analytics/overview').then(r => r.data)

export const getSiteConfigs = () =>
  api.get('/admin/configs').then(r => r.data)

export const createConfig = data =>
  api.post('/admin/configs', data).then(r => r.data)

export const autoDetectConfig = (url, name) =>
  api.post('/admin/configs/auto-detect', { url, name }).then(r => r.data)

export const updateConfig = (name, data) =>
  api.put(`/admin/configs/${name}`, data).then(r => r.data)

export const deleteConfig = name =>
  api.delete(`/admin/configs/${name}`).then(r => r.data)

export const toggleConfig = name =>
  api.post(`/admin/configs/${name}/toggle`).then(r => r.data)

export const startScrape = site_name =>
  api.post(`/admin/scraper/start/${site_name}`).then(r => r.data)

export const startAll = () =>
  api.post('/admin/scraper/start-all').then(r => r.data)

export const getJobStatus = () =>
  api.get('/admin/scraper/status').then(r => r.data)

export const getJobHistory = params =>
  api.get('/admin/scraper/jobs', { params }).then(r => r.data)

export const getMachines = params =>
  api.get('/admin/machines', { params }).then(r => r.data)

export const deleteMachine = id =>
  api.delete(`/admin/machines/${id}`).then(r => r.data)

export const deleteBySite = site_name =>
  api.delete('/admin/machines/bulk', { params: { site_name } }).then(r => r.data)

export const clearAllMachines = () =>
  api.delete('/admin/machines/clear-all').then(r => r.data)

export const getClickAnalytics = params =>
  api.get('/admin/analytics/clicks', { params }).then(r => r.data)

export const getSearchAnalytics = params =>
  api.get('/admin/analytics/searches', { params }).then(r => r.data)
