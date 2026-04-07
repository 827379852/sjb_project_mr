<script setup lang="ts">
defineProps<{
  content?: string
}>()
</script>

<template>
  <div class="msg-agent fade-in">
    <div class="agent-avatar">✦</div>
    <div class="agent-content">
      <div class="agent-name">ResearchMind</div>
      <div class="agent-body">
        <div v-if="content" v-html="content"></div>
        <slot />
      </div>
    </div>
  </div>
</template>
