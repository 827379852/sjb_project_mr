<script setup lang="ts">
import { computed } from 'vue'
import { useMarkdown } from '@/composables'

const props = defineProps<{
  content: string
  streaming?: boolean
}>()

const { simpleMarkdown } = useMarkdown()

const renderedContent = computed(() => {
  return simpleMarkdown(props.content)
})
</script>

<template>
  <div class="report-container markdown">
    <div v-html="renderedContent"></div>
    <span v-if="streaming" class="cursor"></span>
  </div>
</template>
