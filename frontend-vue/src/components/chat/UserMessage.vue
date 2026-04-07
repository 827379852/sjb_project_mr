<script setup lang="ts">
defineProps<{
  content: string
}>()
</script>

<template>
  <div class="msg-user fade-in">
    <div class="bubble">{{ content }}</div>
  </div>
</template>
