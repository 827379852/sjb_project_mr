<script setup lang="ts">
import { computed } from 'vue'
import { useMarkdown } from '@/composables'

const props = defineProps<{
  content: string
}>()

const { simpleMarkdown } = useMarkdown()

const renderedContent = computed(() => {
  return simpleMarkdown(props.content)
})
</script>

<template>
  <div class="markdown" v-html="renderedContent"></div>
</template>
