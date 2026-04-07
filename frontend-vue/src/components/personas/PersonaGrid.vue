<script setup lang="ts">
import type { Persona } from '@/types'
import PersonaCard from './PersonaCard.vue'

defineProps<{
  personas: Persona[]
}>()
</script>

<template>
  <div class="personas-grid">
    <PersonaCard
      v-for="(persona, index) in personas"
      :key="persona.id"
      :persona="persona"
      :index="index"
    />
  </div>
</template>
