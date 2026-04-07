<script setup lang="ts">
import { useResearchStore } from '@/stores'
import type { Persona } from '@/types'

const researchStore = useResearchStore()

const emit = defineEmits<{
  select: [persona: Persona]
}>()

const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']

function selectPersona(persona: Persona) {
  researchStore.setSelectedPersona(persona)
  emit('select', persona)
}
</script>

<template>
  <div class="confirm-block">
    <div class="confirm-question">选择要访谈的人设：</div>
    <div class="personas-grid">
      <div
        v-for="(persona, index) in researchStore.personas"
        :key="persona.id"
        class="persona-card"
        style="cursor: pointer"
        @click="selectPersona(persona)"
      >
        <div class="persona-card-avatar">{{ emojis[index % 5] }}</div>
        <div class="persona-card-name">{{ persona.name }}</div>
        <div class="persona-card-meta">
          {{ persona.age || '' }}岁 · {{ persona.occupation || '' }}
        </div>
      </div>
    </div>
  </div>
</template>
