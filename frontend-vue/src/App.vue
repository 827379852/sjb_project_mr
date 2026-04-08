<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores'

const router = useRouter()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-container">
    <!-- 用户信息栏（仅登录后显示） -->
    <div v-if="authStore.isAuthenticated && $route.meta.requiresAuth" class="user-bar">
      <div class="user-info">
        <span class="user-avatar">👤</span>
        <span class="user-name">{{ authStore.user?.name || '用户' }}</span>
      </div>
      <button class="logout-btn" @click="handleLogout">退出登录</button>
    </div>

    <!-- 路由视图 -->
    <router-view />
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.user-bar {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.95);
  border-bottom-left-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  font-size: 18px;
}

.user-name {
  font-size: 14px;
  color: #333;
}

.logout-btn {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #f5f5f5;
  border-color: #ccc;
}
</style>
