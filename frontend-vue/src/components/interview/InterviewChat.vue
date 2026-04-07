<script setup lang="ts">
import { ref, computed } from 'vue'
import { useResearchStore } from '@/stores'
import type { Persona } from '@/types'

const props = defineProps<{
  persona: Persona
}>()

const researchStore = useResearchStore()

const messages = computed(() => {
  return researchStore.interviewHistory[props.persona.id] || []
})

const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']
const emojiIndex = computed(() => {
  return researchStore.personas.findIndex(p => p.id === props.persona.id) % 5
})

const hints = ref<string[]>([])
</script>

<template>
  <div class="interview-chat">
    <div class="interview-header">
      <div class="interview-persona-avatar">{{ emojis[emojiIndex] }}</div>
      <div>
        <div class="interview-persona-name">{{ persona.name }}</div>
        <div class="interview-persona-meta">
          {{ persona.age || '' }}岁 · {{ persona.occupation || '' }} · {{ persona.city || '' }}
        </div>
      </div>
      <div class="interview-emotion">😌 沉稳</div>
    </div>
    <div class="interview-messages">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="msg.role === 'user' ? 'interview-msg-q' : 'interview-msg-a'"
      >
        {{ msg.content }}
      </div>
    </div>
    <div v-if="hints.length > 0" class="follow-up-hints">
      <span
        v-for="hint in hints"
        :key="hint"
        class="hint-chip"
      >
        {{ hint }}
      </span>
    </div>
  </div>
</template>
