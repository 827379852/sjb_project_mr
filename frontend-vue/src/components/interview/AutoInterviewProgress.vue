<script setup lang="ts">
import { ref } from 'vue'

const progressText = ref('准备中...')
const progressPercent = ref(0)
const questions = ref<string[]>([])
const interviewResults = ref<Map<string, { name: string; messages: Array<{ q: string; a: string }> }>>(new Map())

function updateProgress(text: string, percent: number) {
  progressText.value = text
  progressPercent.value = percent
}

function setQuestions(qs: string[]) {
  questions.value = qs
}

function addInterviewResult(personaId: string, name: string, qa: { q: string; a: string }) {
  if (!interviewResults.value.has(personaId)) {
    interviewResults.value.set(personaId, { name, messages: [] })
  }
  interviewResults.value.get(personaId)!.messages.push(qa)
}

defineExpose({
  updateProgress,
  setQuestions,
  addInterviewResult
})
</script>

<template>
  <div class="auto-interview-progress">
    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px">
      {{ progressText }}
    </div>
    <div style="background: var(--surface3); border-radius: 4px; height: 4px; overflow: hidden">
      <div
        style="background: var(--accent); height: 100%; transition: width 0.3s"
        :style="{ width: progressPercent + '%' }"
      ></div>
    </div>

    <div v-if="questions.length > 0" style="margin: 10px 0">
      <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 4px">
        📋 访谈提纲 ({{ questions.length }} 题)
      </div>
      <div
        v-for="(q, i) in questions"
        :key="i"
        style="font-size: 12px; color: var(--text-secondary); padding: 2px 0"
      >
        {{ i + 1 }}. {{ q }}
      </div>
    </div>

    <div class="interview-results">
      <div
        v-for="[id, result] in interviewResults"
        :key="id"
        class="interview-persona-block"
      >
        <div class="interview-header">
          <div class="interview-persona-avatar">👩</div>
          <div>
            <div class="interview-persona-name">{{ result.name }}</div>
            <div class="interview-persona-meta">自动访谈进行中...</div>
          </div>
          <div class="interview-emotion">🎤 访谈中</div>
        </div>
        <div class="interview-messages" style="max-height: 400px">
          <div
            v-for="(msg, i) in result.messages"
            :key="i"
            style="padding: 6px 0; border-bottom: 1px solid var(--border)"
          >
            <div class="interview-msg-q" style="margin-bottom: 4px">{{ msg.q }}</div>
            <div class="interview-msg-a">{{ msg.a }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
