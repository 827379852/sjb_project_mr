<script setup lang="ts">
import type { Post } from '@/types'

defineProps<{
  post: Post
}>()

function getSentimentEmoji(sentiment: string): string {
  switch (sentiment) {
    case 'positive': return '😊'
    case 'negative': return '😤'
    default: return '😐'
  }
}
</script>

<template>
  <div class="post-item">
    <div class="post-header">
      <span :class="['post-platform', post.platform]">{{ post.platform }}</span>
      <span class="post-sentiment">{{ getSentimentEmoji(post.sentiment) }}</span>
    </div>
    <div class="post-content">{{ post.content }}</div>
  </div>
</template>
