<script setup lang="ts">
interface Example {
  icon: string
  title: string
  desc: string
  text: string
}

defineProps<{
  examples: Example[]
}>()

const emit = defineEmits<{
  useExample: [text: string]
}>()

function handleExampleClick(text: string) {
  emit('useExample', text)
}
</script>

<template>
  <div class="welcome-screen">
    <span class="welcome-icon">🔬</span>
    <h1 class="welcome-title">开始你的用户研究</h1>
    <p class="welcome-sub">
      告诉我你想研究什么，我会帮你完成从框架设计到洞察报告的完整研究流程
    </p>
    <div class="example-cards">
      <div
        v-for="example in examples"
        :key="example.title"
        class="example-card"
        @click="handleExampleClick(example.text)"
      >
        <div class="example-card-icon">{{ example.icon }}</div>
        <div class="example-card-title">{{ example.title }}</div>
        <div class="example-card-desc">{{ example.desc }}</div>
      </div>
    </div>
  </div>
</template>
