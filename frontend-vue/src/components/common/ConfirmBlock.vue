<script setup lang="ts">
interface Option {
  label: string
  action: string
}

defineProps<{
  question: string
  options: Option[]
}>()

const emit = defineEmits<{
  action: [action: string]
}>()

function handleClick(action: string) {
  emit('action', action)
}
</script>

<template>
  <div class="confirm-block fade-in">
    <div class="confirm-question">{{ question }}</div>
    <div class="confirm-options">
      <button
        v-for="(opt, index) in options"
        :key="opt.action"
        :class="['confirm-btn', { primary: index === 0 }]"
        @click="handleClick(opt.action)"
      >
        {{ opt.label }}
      </button>
    </div>
  </div>
</template>
