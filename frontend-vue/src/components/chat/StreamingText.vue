<script setup lang="ts">
import { computed } from 'vue'
import { useMarkdown } from '@/composables'

const props = defineProps<{
  text: string
  streaming?: boolean
}>()

const { simpleMarkdown } = useMarkdown()

const renderedContent = computed(() => {
  return simpleMarkdown(props.text)
})
</script>

<template>
  <div class="streaming-text">
    <div class="markdown" v-html="renderedContent"></div>
    <span v-if="streaming" class="cursor"></span>
  </div>
</template>
