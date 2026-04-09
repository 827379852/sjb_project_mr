<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores'

const router = useRouter()
const authStore = useAuthStore()

// API 基础 URL
const API_BASE = typeof window !== 'undefined' && window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api/v1'
  : `${window.location.origin}/api/v1`

// 刷新用户信息（包括积分）
async function refreshUserInfo() {
  if (!authStore.isAuthenticated) return

  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })

    if (res.ok) {
      const data = await res.json()
      if (data.code === 0 && data.data) {
        authStore.setUser(data.data)
      }
    } else if (res.status === 401) {
      // Token 过期，退出登录
      authStore.logout()
      router.push('/login')
    }
  } catch (err) {
    console.error('刷新用户信息失败:', err)
  }
}

// 页面加载时刷新用户信息
onMounted(() => {
  refreshUserInfo()
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-container">
    <!-- 路由视图 -->
    <router-view @user-updated="refreshUserInfo" />
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
