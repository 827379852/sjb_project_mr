<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useResearchStore, useUIStore, useAuthStore } from '@/stores'
import { useResearchApi } from '@/composables'
import type { StudyListItem, StudyDetail } from '@/types'

const researchStore = useResearchStore()
const uiStore = useUIStore()
const authStore = useAuthStore()
const { listStudies, getStudy, deleteStudy, loadStudy } = useResearchApi()

const studies = ref<StudyListItem[]>([])
const loading = ref(false)

// 是否已登录
const isLoggedIn = computed(() => authStore.isAuthenticated)

// 加载研究列表
async function loadStudies() {
  if (!isLoggedIn.value) return
  loading.value = true
  studies.value = await listStudies()
  loading.value = false
}

// 选择研究
async function selectStudy(study: StudyListItem) {
  const detail = await getStudy(study.id)
  if (detail) {
    loadStudy(detail)
    uiStore.hideWelcome()
    uiStore.showProgressBar()
  }
}

// 新建研究
function newStudy() {
  researchStore.reset()
  uiStore.reset()
  // 清空对话框消息
  if (typeof window !== 'undefined' && (window as any).clearMessages) {
    ;(window as any).clearMessages()
  }
}

// 删除研究
async function handleDelete(studyId: string, event: Event) {
  event.stopPropagation()
  if (confirm('确定要删除这个研究吗？')) {
    const success = await deleteStudy(studyId)
    if (success) {
      studies.value = studies.value.filter(s => s.id !== studyId)
      if (researchStore.studyId === studyId) {
        newStudy()
      }
    }
  }
}

// 判断是否是当前选中的研究
function isActive(studyId: string) {
  return researchStore.studyId === studyId
}

// 格式化日期
function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

// 登录后加载研究列表
onMounted(() => {
  if (isLoggedIn.value) {
    loadStudies()
  }
})
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-logo">
      <div class="logo-text">ResearchMind</div>
      <div class="logo-sub">AI 定性用户研究平台</div>
    </div>

    <div class="sidebar-section">
      <div class="sidebar-section-title">工作区</div>
      <div class="sidebar-item" :class="{ active: !researchStore.studyId }" @click="newStudy">
        <span class="icon">✦</span>
        <span>新建研究</span>
      </div>
    </div>

    <div class="sidebar-section studies-section">
      <div class="sidebar-section-title">
        我的研究
        <span v-if="studies.length > 0" class="study-count">{{ studies.length }}</span>
      </div>

      <div v-if="loading" class="sidebar-loading">
        <span class="loading-text">加载中...</span>
      </div>

      <div v-else-if="studies.length === 0" class="sidebar-empty">
        <span class="empty-text">暂无研究</span>
      </div>

      <div v-else class="studies-list">
        <div
          v-for="study in studies"
          :key="study.id"
          class="sidebar-item study-item"
          :class="{ active: isActive(study.id) }"
          @click="selectStudy(study)"
        >
          <span class="icon">📄</span>
          <div class="study-info">
            <span class="study-title">{{ study.title }}</span>
            <span class="study-date">{{ formatDate(study.updated_at) }}</span>
          </div>
          <button class="delete-btn" @click="handleDelete(study.id, $event)" title="删除">
            ×
          </button>
        </div>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="sidebar-section-title">研究工具</div>
      <div class="sidebar-item">
        <span class="icon">🔍</span>
        <span>深度访谈</span>
      </div>
      <div class="sidebar-item">
        <span class="icon">📊</span>
        <span>问卷调研</span>
      </div>
      <div class="sidebar-item">
        <span class="icon">🌐</span>
        <span>社媒侦察</span>
      </div>
      <div class="sidebar-item">
        <span class="icon">📝</span>
        <span>研究报告</span>
      </div>
    </div>

    <div class="sidebar-section" style="margin-top: auto">
      <div class="sidebar-item">
        <span class="icon">⚙️</span>
        <span>设置</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.studies-section {
  flex: 1;
  overflow-y: auto;
  min-height: 100px;
}

.study-count {
  font-size: 10px;
  background: var(--accent-dim);
  color: var(--accent);
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: auto;
}

.sidebar-loading,
.sidebar-empty {
  padding: 16px;
  text-align: center;
}

.loading-text,
.empty-text {
  font-size: 12px;
  color: var(--text-dim);
}

.studies-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.study-item {
  position: relative;
  padding-right: 32px !important;
}

.study-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.study-title {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.study-date {
  font-size: 10px;
  color: var(--text-dim);
}

.delete-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  opacity: 0;
  transition: all 0.2s;
}

.study-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(248, 113, 113, 0.15);
  color: var(--red);
}
</style>
