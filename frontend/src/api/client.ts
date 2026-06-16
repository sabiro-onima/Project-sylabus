import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// ─── AUTH ────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { email: string; full_name: string; password: string }) =>
    api.post('/auth/register', data),
  login: (email: string, password: string) => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    return api.post('/auth/login', form, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
  },
  me: () => api.get('/auth/me'),
}

// ─── SYLLABI ─────────────────────────────────────────────────────────────────
export const syllabiApi = {
  list: (params?: Record<string, unknown>) => api.get('/syllabi/', { params }),
  get: (id: string) => api.get(`/syllabi/${id}`),
  create: (data: unknown) => api.post('/syllabi/', data),
  versions: (id: string) => api.get(`/syllabi/${id}/versions`),
  newVersion: (id: string, data: unknown) => api.post(`/syllabi/${id}/versions`, data),
  updateVersion: (versionId: string, data: unknown) => api.patch(`/syllabi/versions/${versionId}`, data),
  submit: (versionId: string) => api.post(`/syllabi/versions/${versionId}/submit`),
  approve: (versionId: string) => api.post(`/syllabi/versions/${versionId}/approve`),
  grid: (params: { academic_unit_id: string; academic_year: string }) =>
    api.get('/syllabi/grid', { params }),
  versionChanges: (versionId: string) =>
    api.get(`/syllabi/versions/${versionId}/changes`),
}

// ─── EXPORT ──────────────────────────────────────────────────────────────────
export const exportApi = {
  pdf:  (versionId: string) => api.get(`/export/${versionId}/pdf`,  { responseType: 'blob' }),
  docx: (versionId: string) => api.get(`/export/${versionId}/docx`, { responseType: 'blob' }),
}

// ─── UNITS ───────────────────────────────────────────────────────────────────
export const unitsApi = {
  list: () => api.get('/units/'),
}

// ─── ADMIN ────────────────────────────────────────────────────────────────────
export const adminApi = {
  listUsers: (params?: { search?: string; role?: string; page?: number; size?: number }) =>
    api.get('/admin/users', { params }),
  updateUser: (id: string, data: { role?: string; is_active?: boolean }) =>
    api.patch(`/admin/users/${id}`, data),
  getStats: () => api.get('/admin/stats'),
}
