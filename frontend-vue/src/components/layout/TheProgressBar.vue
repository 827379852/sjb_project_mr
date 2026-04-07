<script setup lang="ts">
import { computed } from 'vue'
import { useResearchStore, useUIStore } from '@/stores'
import type { StepProgress, StepStatus } from '@/types'

const researchStore = useResearchStore()
const uiStore = useUIStore()

const visible = computed(() => uiStore.progressBarVisible)

const steps: { key: keyof StepProgress; label: string }[] = [
  { key: 'design', label: '设计框架' },
  { key: 'personas', label: '生成人设' },
  { key: 'scout', label: '社媒侦察' },
  { key: 'interview', label: '深度访谈' },
  { key: 'report', label: '生成报告' }
]

function getStepStatus(step: keyof StepProgress): StepStatus {
  return researchStore.stepProgress[step]
}

function getStatusClass(status: StepStatus): string {
  return status
}
</script>

<template>
  <div v-if="visible" class="progress-steps">
    <div
      v-for="(step, index) in steps"
      :key="step.key"
      :class="['progress-step', getStatusClass(getStepStatus(step.key))]"
    >
      <span>{{ ['①', '②', '③', '④', '⑤'][index] }}</span>
      <span>{{ step.label }}</span>
    </div>
  </div>
</template>
