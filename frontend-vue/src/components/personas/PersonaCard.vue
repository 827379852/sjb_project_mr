<script setup lang="ts">
import { computed } from 'vue'
import { useUIStore } from '@/stores'
import type { Persona } from '@/types'
import { useMarkdown } from '@/composables'

const props = defineProps<{
  persona: Persona
  index: number
}>()

const uiStore = useUIStore()
const { escapeHtml } = useMarkdown()

const expanded = computed(() => uiStore.expandedPersonas.includes(props.persona.id))

const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']
const avatar = computed(() => emojis[props.index % 5])

function toggle() {
  uiStore.togglePersona(props.persona.id)
}

function buildPersonaDetailHtml(p: Persona): string {
  let html = ''
  if (p.background) html += `<div class="persona-detail-section"><div class="persona-detail-label">📋 背景</div><div class="persona-detail-value">${escapeHtml(p.background)}</div></div>`
  if (p.personality) html += `<div class="persona-detail-section"><div class="persona-detail-label">🧠 性格特征</div><div class="persona-detail-value">${escapeHtml(p.personality)}</div></div>`
  if (p.consumer_habits) html += `<div class="persona-detail-section"><div class="persona-detail-label">🛒 消费习惯</div><div class="persona-detail-value">${escapeHtml(p.consumer_habits)}</div></div>`
  if (p.pain_points) html += `<div class="persona-detail-section"><div class="persona-detail-label">😤 痛点</div><div class="persona-detail-value">${Array.isArray(p.pain_points) ? p.pain_points.map(v => escapeHtml(v)).join('、') : escapeHtml(p.pain_points)}</div></div>`
  if (p.motivations) html += `<div class="persona-detail-section"><div class="persona-detail-label">🎯 动机</div><div class="persona-detail-value">${escapeHtml(p.motivations)}</div></div>`
  if (p.digital_behavior) html += `<div class="persona-detail-section"><div class="persona-detail-label">📱 数字行为</div><div class="persona-detail-value">${escapeHtml(p.digital_behavior)}</div></div>`
  if (p.social_media) html += `<div class="persona-detail-section"><div class="persona-detail-label">💬 社媒偏好</div><div class="persona-detail-value">${escapeHtml(p.social_media)}</div></div>`
  if (p.core_values && p.core_values.length > 0) html += `<div class="persona-detail-section"><div class="persona-detail-label">💎 核心价值观</div><div class="persona-detail-value">${p.core_values.map(v => escapeHtml(v)).join('、')}</div></div>`
  return html
}
</script>

<template>
  <div :class="['persona-card', { expanded }]" @click="toggle">
    <div class="persona-expand-icon">▼</div>
    <div class="persona-card-header">
      <div class="persona-card-avatar">{{ avatar }}</div>
      <div class="persona-card-info">
        <div class="persona-card-name">{{ persona.name }}</div>
        <div class="persona-card-meta">
          {{ persona.age || '' }}岁 · {{ persona.occupation || '' }}
        </div>
      </div>
    </div>
    <div class="persona-card-tags">
      <span
        v-for="value in (persona.core_values || []).slice(0, 3)"
        :key="value"
        class="persona-card-tag"
      >
        {{ value }}
      </span>
    </div>
    <div v-if="expanded" class="persona-detail-panel" v-html="buildPersonaDetailHtml(persona)"></div>
  </div>
</template>
