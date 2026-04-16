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
    // 处理 FastAPI 的验证错误格式
    const errorMsg = error.detail?.msg || error.detail || JSON.stringify(error.detail || error)
    throw new Error(errorMsg)
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

    // 获取积分记录列表（超级管理员）
    async listCreditLogs(
      page: number = 1,
      pageSize: number = 20,
      userId?: string,
      logType?: string
    ): Promise<CreditLogListResponse> {
      let url = `${API_BASE}/credit-logs?page=${page}&page_size=${pageSize}`
      if (userId) url += `&user_id=${userId}`
      if (logType) url += `&log_type=${logType}`
      return request<CreditLogListResponse>(url)
    },

    // 获取系统配置列表
    async getSystemConfigs(): Promise<any[]> {
      return request<any[]>(`${API_BASE}/system-configs`)
    },

    // 更新系统配置
    async updateSystemConfig(key: string, value: string): Promise<any> {
      return request<any>(`${API_BASE}/system-configs/${key}`, {
        method: 'PUT',
        body: JSON.stringify({ value }),
      })
    },

    // 获取队列状态
    async getQueueStatus(): Promise<{
      max_concurrent: number
      queued: number
      running: number
      total_tasks: number
    }> {
      return request(`${API_BASE}/queue-status`)
    },
  }
}
