<script setup lang="ts">
import type { Post } from '@/types'
import PostItem from './PostItem.vue'

defineProps<{
  posts: Post[]
}>()
</script>

<template>
  <div class="post-feed">
    <PostItem v-for="(post, index) in posts" :key="index" :post="post" />
  </div>
</template>
