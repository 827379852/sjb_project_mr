/**
 * 管理员 API 调用
 */
import { useAuthStore } from '@/stores/authStore'

const API_BASE = '/api/v1/admin'

interface User {
  id: string
  email: string
  name: string
  is_active: boolean
  is_superuser: boolean
  credits: number
  created_at: string
}

interface UserListResponse {
  items: User[]
  total: number
  page: number
  page_size: number
}

interface StatsResponse {
  total_users: number
  active_users: number
  total_credits: number
  default_credits: number
  task_cost_credits: number
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const authStore = useAuthStore()
  const token = authStore.token

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }))
    throw new Error(error.detail || '请求失败')
  }

  const data = await response.json()
  return data.data
}

export function useAdminApi() {
  return {
    // 获取用户列表
    async listUsers(page: number = 1, pageSize: number = 20): Promise<UserListResponse> {
      return request<UserListResponse>(`${API_BASE}/users?page=${page}&page_size=${pageSize}`)
    },

    // 获取用户详情
    async getUser(userId: string): Promise<User> {
      return request<User>(`${API_BASE}/users/${userId}`)
    },

    // 更新用户
    async updateUser(userId: string, data: { name?: string; is_active?: boolean; credits?: number }): Promise<User> {
      return request<User>(`${API_BASE}/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      })
    },

    // 重置密码
    async resetPassword(userId: string): Promise<{ message: string }> {
      return request<{ message: string }>(`${API_BASE}/users/${userId}/reset-password`, {
        method: 'POST',
      })
    },

    // 增加积分
    async addCredits(userId: string, amount: number): Promise<User> {
      return request<User>(`${API_BASE}/users/${userId}/add-credits?amount=${amount}`, {
        method: 'POST',
      })
    },

    // 删除用户
    async deleteUser(userId: string): Promise<{ message: string }> {
      return request<{ message: string }>(`${API_BASE}/users/${userId}`, {
        method: 'DELETE',
      })
    },

    // 获取统计
    async getStats(): Promise<StatsResponse> {
      return request<StatsResponse>(`${API_BASE}/stats`)
    },
  }
}
