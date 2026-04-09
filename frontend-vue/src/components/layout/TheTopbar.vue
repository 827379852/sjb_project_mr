<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useResearchStore, useAuthStore } from '@/stores'

const router = useRouter()
const researchStore = useResearchStore()
const authStore = useAuthStore()

function clearChat() {
  researchStore.reset()
}

function exportReport() {
  if (!researchStore.reportContent) {
    alert('暂无报告内容，请先生成报告')
    return
  }
  const blob = new Blob([researchStore.reportContent], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `research-report-${researchStore.studyId || Date.now()}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function goAdmin() {
  router.push('/admin')
}

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="topbar">
    <span class="topbar-title">{{ researchStore.studyTitle }}</span>
    <div v-if="researchStore.studyId" class="study-badge">
      <div class="dot"></div>
      <span>研究 #{{ researchStore.studyId }}</span>
    </div>
    <div class="topbar-actions">
      <!-- 积分显示 -->
      <div class="credits-badge" v-if="authStore.user && !authStore.isSuperuser">
        <span class="credits-icon">💎</span>
        <span class="credits-value">{{ authStore.user.credits }}</span>
        <span class="credits-label">积分</span>
      </div>
      <div class="superuser-badge" v-if="authStore.isSuperuser">
        <span>👑 管理员</span>
      </div>
      <!-- 管理员入口 -->
      <button v-if="authStore.isSuperuser" class="btn btn-ghost" @click="goAdmin">管理后台</button>
      <button class="btn btn-ghost" @click="clearChat">清空</button>
      <button class="btn btn-primary" @click="exportReport">导出报告</button>
      <button class="btn btn-ghost" @click="logout">退出</button>
    </div>
  </div>
</template>

<style scoped>
.credits-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: linear-gradient(135deg, #ffd700, #ffaa00);
  border-radius: 16px;
  color: #1a1a1a;
  font-size: 13px;
  font-weight: 600;
}

.credits-icon {
  font-size: 14px;
}

.credits-value {
  font-weight: 700;
}

.credits-label {
  font-weight: 400;
  opacity: 0.8;
}

.superuser-badge {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 16px;
  color: white;
  font-size: 13px;
  font-weight: 600;
}
</style>
