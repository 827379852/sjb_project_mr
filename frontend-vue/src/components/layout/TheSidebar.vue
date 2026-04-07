<script setup lang="ts">
import { useResearchStore, useUIStore } from '@/stores'

const researchStore = useResearchStore()
const uiStore = useUIStore()

function newStudy() {
  researchStore.reset()
  uiStore.reset()
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-logo">
      <div class="logo-text">ResearchMind</div>
      <div class="logo-sub">AI 定性用户研究平台</div>
    </div>

    <div class="sidebar-section">
      <div class="sidebar-section-title">工作区</div>
      <div class="sidebar-item active" @click="newStudy">
        <span class="icon">✦</span>
        <span>新建研究</span>
      </div>
      <div class="sidebar-item">
        <span class="icon">📁</span>
        <span>我的研究</span>
      </div>
      <div class="sidebar-item">
        <span class="icon">👥</span>
        <span>人设库</span>
        <span class="badge">12</span>
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
