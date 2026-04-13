<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useResearchStore, useAuthStore } from '@/stores'

const router = useRouter()
const researchStore = useResearchStore()
const authStore = useAuthStore()

function goAdmin() {
  router.push('/admin')
}
</script>

<template>
  <div class="topbar">
    <span class="topbar-title">{{ researchStore.studyTitle || '新建研究' }}</span>
    <div v-if="researchStore.studyId" class="study-badge">
      <div class="dot"></div>
      <span>研究 #{{ researchStore.studyId.slice(0, 8) }}</span>
    </div>
    <div class="topbar-actions">
      <!-- 管理员入口 -->
      <button v-if="authStore.isSuperuser" class="btn btn-ghost" @click="goAdmin">管理后台</button>
    </div>
  </div>
</template>

<style scoped>
</style>
