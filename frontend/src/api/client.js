import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'

const api = axios.create({ baseURL: BASE })

export const searchMachines = (params) =>
  api.get('/api/v1/search/', { params }).then(r => r.data)

export const getMachine = (id) =>
  api.get(`/api/v1/search/machine/${id}`).then(r => r.data)

export const trackClick = (machineId) =>
  api.post('/api/v1/search/track-click', { machine_id: machineId }).then(r => r.data)

export const getSuggestions = (q) =>
  api.get('/api/v1/search/suggestions', { params: { q } }).then(r => r.data)

export const getFilters = () =>
  api.get('/api/v1/search/filters').then(r => r.data)
