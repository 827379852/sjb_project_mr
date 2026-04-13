import { useAuthStore, type User } from '@/stores/authStore'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api/v1'
  : `${window.location.origin}/api/v1`

export interface CreditLog {
  id: string
  user_id: string
  user_email: string | null
  user_name: string | null
  amount: number
  balance_after: number
  log_type: string
  description: string | null
  related_study_id: string | null
  created_at: string
}

interface CreditLogListResponse {
  items: CreditLog[]
  total: number
  page: number
  page_size: number
}

export function useAuthApi() {
  const authStore = useAuthStore()

  async function login(email: string, password: string): Promise<{ success: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      const data = await res.json()

      if (data.code === 0 && data.data?.access_token) {
        authStore.setToken(data.data.access_token)
        // 登录成功后获取用户信息
        await getMe()
        return { success: true, message: '登录成功' }
      } else {
        return { success: false, message: data.message || '登录失败' }
      }
    } catch (e) {
      return { success: false, message: '网络错误，请重试' }
    }
  }

  async function register(email: string, password: string, name: string): Promise<{ success: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name })
      })

      const data = await res.json()

      if (data.code === 0) {
        return { success: true, message: '注册成功，请登录' }
      } else {
        return { success: false, message: data.message || '注册失败' }
      }
    } catch (e) {
      return { success: false, message: '网络错误，请重试' }
    }
  }

  async function getMe(): Promise<User | null> {
    if (!authStore.token) return null

    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })

      const data = await res.json()

      if (data.code === 0 && data.data) {
        authStore.setUser(data.data)
        return data.data
      } else {
        // Token 无效，清除登录状态
        authStore.logout()
        return null
      }
    } catch {
      return null
    }
  }

  async function checkAuth(): Promise<boolean> {
    if (!authStore.token) return false
    const user = await getMe()
    return user !== null
  }

  async function getMyCreditLogs(page: number = 1, pageSize: number = 20): Promise<CreditLogListResponse | null> {
    if (!authStore.token) return null

    try {
      const res = await fetch(`${API_BASE}/auth/credit-logs?page=${page}&page_size=${pageSize}`, {
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })

      const data = await res.json()

      if (data.code === 0 && data.data) {
        return data.data
      } else {
        return null
      }
    } catch {
      return null
    }
  }

  return {
    login,
    register,
    getMe,
    checkAuth,
    getMyCreditLogs
  }
}
