import { create } from 'zustand'
import { authApi } from '../api/client'

interface User {
  id: string
  email: string
  full_name: string
  role: string
  auth_provider: string
}

interface AuthStore {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  fetchMe: () => Promise<void>
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  loading: false,

  login: async (email, password) => {
    set({ loading: true })
    try {
      const { data } = await authApi.login(email, password)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      const me = await authApi.me()
      set({ user: me.data, loading: false })
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null })
    window.location.href = '/login'
  },

  fetchMe: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    try {
      const { data } = await authApi.me()
      set({ user: data })
    } catch {
      localStorage.removeItem('access_token')
    }
  },
}))
