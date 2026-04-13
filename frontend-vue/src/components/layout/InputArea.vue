<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useResearchStore, useUIStore } from '@/stores'
import { useResearchApi } from '@/composables'

const researchStore = useResearchStore()
const uiStore = useUIStore()
const { uploadContext } = useResearchApi()

const inputText = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const toolbarButtons = [
  { id: 'scout', label: '🌐 社媒侦察' },
  { id: 'interview', label: '🎤 开始访谈' },
  { id: 'report', label: '📊 生成报告' }
]

const emit = defineEmits<{
  send: [text: string]
  triggerPersonas: []
  triggerScout: []
  triggerInterview: []
  triggerReport: []
}>()

const placeholder = computed(() => {
  if (researchStore.selectedPersona) {
    return `向 ${researchStore.selectedPersona.name} 提问...`
  }
  return '描述你的研究需求，或直接提问...'
})

function autoResize(el: HTMLTextAreaElement) {
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function sendMessage() {
  if (researchStore.isStreaming || !inputText.value.trim()) return
  const text = inputText.value.trim()
  inputText.value = ''
  nextTick(() => {
    if (textareaRef.value) textareaRef.value.style.height = 'auto'
  })
  emit('send', text)
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  const extractedText = await uploadContext(file)
  if (extractedText) {
    researchStore.addAttachment({ name: file.name, text: extractedText })
  }
  target.value = ''
}

function removeAttachment(index: number) {
  researchStore.removeAttachment(index)
}

function handleToolbarClick(buttonId: string) {
  switch (buttonId) {
    case 'personas':
      emit('triggerPersonas')
      break
    case 'scout':
      emit('triggerScout')
      break
    case 'interview':
      emit('triggerInterview')
      break
    case 'report':
      emit('triggerReport')
      break
  }
}

function isButtonVisible(buttonId: string): boolean {
  return uiStore.isToolbarButtonVisible(buttonId)
}

// 设置输入框文本并聚焦
function setInputText(text: string) {
  inputText.value = text
  nextTick(() => {
    textareaRef.value?.focus()
    // 将光标移到文本末尾
    if (textareaRef.value) {
      textareaRef.value.selectionStart = textareaRef.value.selectionEnd = textareaRef.value.value.length
    }
  })
}

// 暴露方法给父组件
defineExpose({
  setInputText
})
</script>

<template>
  <div class="input-area">
    <div class="input-wrapper">
      <div class="input-toolbar">
        <button
          v-for="btn in toolbarButtons"
          :key="btn.id"
          v-show="isButtonVisible(btn.id)"
          class="toolbar-btn"
          @click="handleToolbarClick(btn.id)"
        >
          {{ btn.label }}
        </button>
      </div>

      <div v-if="researchStore.attachments.length > 0" class="attachments">
        <div
          v-for="(att, index) in researchStore.attachments"
          :key="index"
          class="attachment-tag"
        >
          📄 {{ att.name }}
          <span class="attachment-remove" @click="removeAttachment(index)">×</span>
        </div>
      </div>

      <div style="position: relative">
        <textarea
          ref="textareaRef"
          v-model="inputText"
          class="input-box"
          :placeholder="placeholder"
          rows="1"
          @keydown="handleKeyDown"
          @input="autoResize($event.target as HTMLTextAreaElement)"
        ></textarea>
        <button
          class="input-send"
          :disabled="researchStore.isStreaming || !inputText.trim()"
          @click="sendMessage"
        >
          ↑
        </button>
      </div>

      <input
        ref="fileInput"
        type="file"
        class="file-input"
        accept=".txt,.md,.pdf,.doc,.docx"
        @change="handleFileUpload"
      />
    </div>
  </div>
</template>
