import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  // Don't set default Content-Type - let axios auto-detect based on data type
  // (FormData will get multipart/form-data, objects will get application/json)
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Set Content-Type to application/json for non-FormData requests
    if (!(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json'
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data),
}

// Users API
export const usersAPI = {
  list: (params) => api.get('/auth/users', { params }),
  get: (id) => api.get(`/auth/users/${id}`),
  create: (data) => api.post('/auth/register', data),
  update: (id, data) => api.patch(`/auth/users/${id}`, data),
  delete: (id) => api.delete(`/auth/users/${id}`),
}

// API Keys API
export const apiKeysAPI = {
  list: () => api.get('/auth/api-keys'),
  create: (data) => api.post('/auth/api-keys', data),
  delete: (id) => api.delete(`/auth/api-keys/${id}`),
}

// Request Logs API
export const logsAPI = {
  list: (params) => api.get('/admin/logs/requests', { params }),
  get: (id) => api.get(`/admin/logs/requests/${id}`),
  stats: (params) => api.get('/admin/logs/stats', { params }),
  cleanup: (params) => api.delete('/admin/logs/cleanup', { params }),
}

// Training Data API
export const trainingAPI = {
  list: (params) => api.get('/admin/training-data', { params }),
  get: (id) => api.get(`/admin/training-data/${id}`),
  create: (data) => api.post('/admin/training-data', data),
  update: (id, data) => api.patch(`/admin/training-data/${id}`, data),
  delete: (id) => api.delete(`/admin/training-data/${id}`),
  stats: () => api.get('/admin/training-data/stats/overview'),
  bulkValidate: (data) => api.post('/admin/training-data/bulk-validate', data),
}

// System Config API
export const configAPI = {
  list: (params) => api.get('/admin/config', { params }),
  get: (key, params) => api.get(`/admin/config/${key}`, { params }),
  create: (data) => api.post('/admin/config', data),
  update: (key, data) => api.patch(`/admin/config/${key}`, data),
  delete: (key) => api.delete(`/admin/config/${key}`),
  bulkUpdate: (data) => api.post('/admin/config/bulk-update', data),
  categories: () => api.get('/admin/config/categories/list'),
}

// Categories API
export const categoriesAPI = {
  list: () => api.get('/categories'),
  count: () => api.get('/admin/categories/count'),
  buildIndex: (data) => api.post('/admin/categories/rebuild-index', data || { force: false, only_leaf_categories: true }),
  rebuildIndex: (data) => api.post('/admin/categories/rebuild-index', data || { force: true, only_leaf_categories: true }),
  sync: (params) => api.post('/admin/categories/sync', { params }),
  syncHistory: (params) => api.get('/admin/categories/sync/history', { params }),
  syncLatest: () => api.get('/admin/categories/sync/latest'),
  syncStats: () => api.get('/admin/categories/sync/stats'),
  import: (formData) => api.post('/admin/categories/import', formData),
  export: () => api.get('/admin/categories/export'),
  generateDescriptions: (params) => api.post('/admin/categories/generate-descriptions', null, { params }),
  // Omni sync
  syncOmni: (params) => api.post('/admin/categories/sync-omni', null, { params }),
  omniConfig: () => api.get('/admin/categories/omni-config'),
  attributes: () => api.get('/admin/categories/attributes'),
  categoryAttributes: (id) => api.get(`/admin/categories/attributes/${id}`),
  updateCategory: (id, data) => api.patch(`/admin/categories/${id}`, data),
}

// Generate / AI API
export const generateAPI = {
  fromImages: (data) => api.post('/generate/from-images', data),
  fromText: (data) => api.post('/generate/from-text', data),
  full: (data) => api.post('/generate/full', data),
  validateConsistency: (data) => api.post('/generate/validate-consistency', data),
}

// System Control API
export const systemAPI = {
  health: () => api.get('/admin/system/health'),
  serviceControl: (service, action) =>
    api.post(`/admin/system/services/${service}/control`, { action }),
  clearCache: (data) => api.post('/admin/system/cache/clear', data),
  logs: (params) => api.get('/admin/system/logs', { params }),
  metrics: () => api.get('/admin/system/metrics'),
  databaseStats: () => api.get('/admin/system/database/stats'),
  info: () => api.get('/admin/system/info'),
}

export default api
