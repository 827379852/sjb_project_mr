import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface User {
  id: string
  email: string
  name: string
  is_active: boolean
  is_superuser: boolean
  credits: number
  created_at: string
}

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export const useAuthStore = defineStore('auth', () => {
  // State - 从 localStorage 恢复
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(null)

  // 初始化时尝试恢复用户信息
  const savedUser = localStorage.getItem(USER_KEY)
  if (savedUser) {
    try {
      user.value = JSON.parse(savedUser)
    } catch {
      localStorage.removeItem(USER_KEY)
    }
  }

  // Computed
  const isAuthenticated = computed(() => !!token.value)
  const isSuperuser = computed(() => user.value?.is_superuser ?? false)
  const credits = computed(() => user.value?.credits ?? 0)

  // Actions
  function setToken(newToken: string | null) {
    token.value = newToken
    if (newToken) {
      localStorage.setItem(TOKEN_KEY, newToken)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
  }

  function setUser(newUser: User | null) {
    user.value = newUser
    if (newUser) {
      localStorage.setItem(USER_KEY, JSON.stringify(newUser))
    } else {
      localStorage.removeItem(USER_KEY)
    }
  }

  function logout() {
    setToken(null)
    setUser(null)
  }

  function updateCredits(newCredits: number) {
    if (user.value) {
      user.value.credits = newCredits
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    }
  }

  function addCredits(amount: number) {
    if (user.value) {
      user.value.credits += amount
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    }
  }

  function deductCredits(amount: number) {
    if (user.value) {
      user.value.credits -= amount
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    }
  }

  return {
    // State
    token,
    user,
    // Computed
    isAuthenticated,
    isSuperuser,
    credits,
    // Actions
    setToken,
    setUser,
    logout,
    updateCredits,
    addCredits,
    deductCredits
  }
})
