<script setup lang="ts">
import { computed } from 'vue'
import { useUIStore } from '@/stores'
import StreamingText from './StreamingText.vue'

const props = defineProps<{
  id: string
  title: string
  desc: string
  status: 'pending' | 'running' | 'done' | 'error'
  content?: string
}>()

const uiStore = useUIStore()

const expanded = computed(() => uiStore.expandedSteps.includes(props.id))

const statusIcons = {
  pending: '○',
  running: '↻',
  done: '✓',
  error: '✗'
}

function toggle() {
  uiStore.toggleStep(props.id)
}
</script>

<template>
  <div class="step-card fade-in">
    <div class="step-header" @click="toggle">
      <div :class="['step-status-icon', status]">{{ statusIcons[status] }}</div>
      <div class="step-info">
        <div class="step-title">{{ title }}</div>
        <div class="step-desc">{{ desc }}</div>
      </div>
      <div class="step-expand-icon">{{ expanded ? '▼' : '▶' }}</div>
    </div>
    <div :class="['step-body', { visible: expanded }]">
      <StreamingText v-if="content" :text="content" :streaming="status === 'running'" />
      <slot />
    </div>
  </div>
</template>
