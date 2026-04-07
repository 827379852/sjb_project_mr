<script setup lang="ts">
import { useResearchStore } from '@/stores'

const researchStore = useResearchStore()

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
</script>

<template>
  <div class="topbar">
    <span class="topbar-title">{{ researchStore.studyTitle }}</span>
    <div v-if="researchStore.studyId" class="study-badge">
      <div class="dot"></div>
      <span>研究 #{{ researchStore.studyId }}</span>
    </div>
    <div class="topbar-actions">
      <button class="btn btn-ghost" @click="clearChat">清空</button>
      <button class="btn btn-primary" @click="exportReport">导出报告</button>
    </div>
  </div>
</template>
