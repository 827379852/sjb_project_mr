<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useResearchStore, useUIStore } from '@/stores'
import WelcomeScreen from './WelcomeScreen.vue'
import UserMessage from './UserMessage.vue'
import AgentMessage from './AgentMessage.vue'
import StepCard from './StepCard.vue'
import PersonaGrid from '@/components/personas/PersonaGrid.vue'
import ConfirmBlock from '@/components/common/ConfirmBlock.vue'
import type { SSEEvent, Persona } from '@/types'

const researchStore = useResearchStore()
const uiStore = useUIStore()

const chatArea = ref<HTMLElement | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)

interface Message {
  id: string
  type: 'user' | 'agent'
  content: string
  components?: ComponentItem[]
}

interface ComponentItem {
  type: string
  id: string
  props: Record<string, unknown>
}

const messages = ref<Message[]>([])
type StepStatus = 'pending' | 'running' | 'done' | 'error'

const stepCards = ref<Map<string, { title: string; desc: string; status: StepStatus; content: string }>>(new Map())

function scrollToBottom() {
  nextTick(() => {
    if (chatArea.value) {
      chatArea.value.scrollTop = chatArea.value.scrollHeight
    }
  })
}

function addUserMsg(text: string) {
  uiStore.hideWelcome()
  uiStore.showProgressBar()
  messages.value.push({
    id: `user-${Date.now()}`,
    type: 'user',
    content: text
  })
  scrollToBottom()
}

function addStepCard(id: string, title: string, desc: string, status: StepStatus = 'running') {
  stepCards.value.set(id, { title, desc, status, content: '' })
  scrollToBottom()
}

function updateStepCard(id: string, updates: Partial<{ title: string; desc: string; status: string; content: string }>) {
  const card = stepCards.value.get(id)
  if (card) {
    Object.assign(card, updates)
  }
}

function appendConfirm(question: string, options: Array<{ label: string; action: string }>) {
  messages.value.push({
    id: `confirm-${Date.now()}`,
    type: 'agent',
    content: '',
    components: [{
      type: 'confirm',
      id: `confirm-comp-${Date.now()}`,
      props: { question, options }
    }]
  })
  scrollToBottom()
}

// 示例卡片数据
const exampleCards = [
  {
    icon: '💄',
    title: '国产美妆用户研究',
    desc: '了解年轻女性对国货美妆的真实态度',
    text: '我想研究年轻女性（18-30岁）对国产美妆品牌的态度，特别是她们为什么选择或放弃国货品牌'
  },
  {
    icon: '🚗',
    title: '新能源汽车决策研究',
    desc: '挖掘购车决策中的深层顾虑',
    text: '帮我研究新能源汽车用户在购买决策中最关键的顾虑，特别是第一次购买电动车的人群'
  },
  {
    icon: '💪',
    title: '健康 App 用户研究',
    desc: '探索中年人健康管理需求与痛点',
    text: '我们正在开发一款面向 35-50 岁中年人的健康管理 App，想了解这群人的健康焦虑和产品期望'
  },
  {
    icon: '🤖',
    title: 'AI 工具职场使用研究',
    desc: '理解职场 AI 工具采纳的心理障碍',
    text: '研究在职场中使用 AI 工具的白领群体，他们的使用习惯、信任感和抵触情绪从哪里来'
  }
]

// 处理发送消息
async function handleSend(text: string) {
  if (researchStore.isStreaming) return
  addUserMsg(text)

  if (researchStore.phase === 'idle') {
    await runDesignStudy(text)
  } else if (researchStore.phase === 'interviewing' && researchStore.selectedPersona) {
    await runInterview(text)
  } else {
    await runDesignStudy(text)
  }
}

// 设计研究
async function runDesignStudy(userRequest: string) {
  const attachContext = researchStore.attachments.map(a => a.text).join('\n\n')

  const cardId = `step-design-card-${Date.now()}`
  addStepCard(cardId, '🎯 设计研究框架', '正在分析研究需求，构建访谈框架...', 'running')

  let fullContent = ''

  researchStore.setStreaming(true)
  researchStore.setPhase('designing')
  researchStore.updateStepProgress('design', 'active')

  // 手动处理 SSE 事件
  const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : `${window.location.origin}/api/v1`

  const res = await fetch(`${API_BASE}/research-flow/design-study`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_request: userRequest, context: attachContext })
  })

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const lines = decoder.decode(value).split('\n')
    for (const line of lines) {
      if (!line.startsWith('data: ') || line === 'data: [DONE]') continue
      try {
        const event = JSON.parse(line.slice(6)) as SSEEvent
        if (event.type === 'study_id') {
          researchStore.setStudyId(event.study_id as string)
          researchStore.setStudyTitle(userRequest.substring(0, 20) + '...')
        } else if (event.type === 'content') {
          fullContent += event.delta as string
          updateStepCard(cardId, { content: fullContent })
          scrollToBottom()
        } else if (event.type === 'step' && event.status === 'done') {
          updateStepCard(cardId, { status: 'done' })
        }
      } catch {}
    }
  }

  researchStore.updateStepProgress('design', 'done')
  researchStore.updateStepProgress('personas', 'active')
  researchStore.setPhase('post-design')
  researchStore.setStreaming(false)

  uiStore.showToolbarButton('personas')

  appendConfirm(
    '框架已生成 ✓  接下来要怎么做？',
    [
      { label: '🧠 生成目标人设', action: 'triggerPersonas' },
      { label: '🌐 先做社媒侦察', action: 'triggerScout' },
      { label: '✏️ 调整研究方向', action: 'editStudy' }
    ]
  )
}

// 生成人设
async function triggerPersonas() {
  const cardId = `step-personas-card-${Date.now()}`
  addStepCard(cardId, '👥 生成目标人设', '正在构建初始用户画像...', 'running')

  const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : `${window.location.origin}/api/v1`

  const res = await fetch(`${API_BASE}/research-flow/search-personas`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      study_id: researchStore.studyId,
      persona_description: '根据研究背景生成',
      max_count: 10
    })
  })

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split('\n')
    for (const line of lines) {
      if (!line.startsWith('data: ') || line === 'data: [DONE]') continue
      try {
        const event = JSON.parse(line.slice(6)) as SSEEvent
        if (event.type === 'persona') {
          const p = event.persona as Persona
          researchStore.addPersona(p)
        } else if (event.type === 'step' && event.status === 'done') {
          updateStepCard(cardId, { status: 'done' })
        }
      } catch {}
    }
  }

  researchStore.updateStepProgress('personas', 'done')
  researchStore.updateStepProgress('scout', 'active')

  uiStore.showToolbarButton('scout')
  uiStore.showToolbarButton('interview')

  appendConfirm(
    `已生成 ${researchStore.personas.length} 个用户画像。选择下一步操作：`,
    [
      { label: '🌐 社媒侦察', action: 'triggerScout' },
      { label: '🎤 自动深度访谈', action: 'triggerAutoInterview' },
      { label: '📊 直接生成报告', action: 'triggerReport' }
    ]
  )
}

// 社媒侦察
async function triggerScout() {
  const cardId = `step-scout-card-${Date.now()}`
  addStepCard(cardId, '🌐 社交媒体侦察', '为每个人设搜索专属社媒内容...', 'running')

  // 从标题提取关键词
  const title = researchStore.studyTitle.replace('...', '')
  const keywords = title.split(/[，,、\s]+/).filter(k => k.length > 1).slice(0, 3)
  if (keywords.length === 0) keywords.push('用户研究')

  const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : `${window.location.origin}/api/v1`

  const res = await fetch(`${API_BASE}/research-flow/scout-and-build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      study_id: researchStore.studyId,
      keywords,
      platforms: ['小红书', '微博', '抖音']
    })
  })

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split('\n')
    for (const line of lines) {
      if (!line.startsWith('data: ') || line === 'data: [DONE]') continue
      try {
        const event = JSON.parse(line.slice(6)) as SSEEvent
        if (event.type === 'updated_persona') {
          researchStore.updatePersona(event.persona as Persona)
        } else if (event.type === 'step' && event.step === 'build_persona' && event.status === 'done') {
          updateStepCard(cardId, { status: 'done' })
        }
      } catch {}
    }
  }

  researchStore.updateStepProgress('scout', 'done')
  researchStore.updateStepProgress('interview', 'active')

  appendConfirm(
    '社媒侦察完成，每个人设已根据专属的真实用户声音增强 ✓  建议进行深度访谈来挖掘更深层的动机。',
    [
      { label: '🎤 自动深度访谈', action: 'triggerAutoInterview' },
      { label: '📊 直接生成报告', action: 'triggerReport' }
    ]
  )
}

// 自动访谈
async function triggerAutoInterview() {
  const cardId = `step-auto-interview-card-${Date.now()}`
  addStepCard(cardId, '🎤 自动深度访谈', '正在基于访谈框架对所有用户人设执行访谈...', 'running')

  const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : `${window.location.origin}/api/v1`

  const res = await fetch(`${API_BASE}/research-flow/auto-interview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ study_id: researchStore.studyId })
  })

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let totalPersonas = 0

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split('\n')
    for (const line of lines) {
      if (!line.startsWith('data: ') || line === 'data: [DONE]') continue
      try {
        const event = JSON.parse(line.slice(6)) as SSEEvent
        if (event.type === 'qa') {
          const personaId = event.persona_id as string
          researchStore.addInterviewMessage(personaId, { role: 'user', content: event.question as string })
          researchStore.addInterviewMessage(personaId, { role: 'assistant', content: event.answer as string })
        } else if (event.type === 'interview_start') {
          totalPersonas = event.total as number
        } else if (event.type === 'step' && event.step === 'auto_interview' && event.status === 'done') {
          updateStepCard(cardId, { status: 'done' })
        }
      } catch {}
    }
  }

  researchStore.updateStepProgress('interview', 'done')
  researchStore.updateStepProgress('report', 'active')

  uiStore.showToolbarButton('report')

  appendConfirm(
    `自动访谈完成 ✓  共对 ${totalPersonas} 位用户进行了深度访谈。接下来生成研究报告？`,
    [
      { label: '📊 生成研究报告', action: 'triggerReport' },
      { label: '🎤 继续手动追问', action: 'showInterviewPicker' }
    ]
  )
}

// 生成报告
async function triggerReport() {
  const cardId = `step-report-card-${Date.now()}`
  addStepCard(cardId, '📊 生成研究报告', '整合人设数据与访谈洞察...', 'running')

  const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : `${window.location.origin}/api/v1`

  const transcripts = Object.entries(researchStore.interviewHistory).map(([id, msgs]) => ({
    persona_id: id,
    messages: msgs
  }))

  const res = await fetch(`${API_BASE}/research-flow/generate-report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      study_id: researchStore.studyId,
      personas: researchStore.personas,
      interview_transcripts: transcripts,
      format: 'markdown'
    })
  })

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let fullReport = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split('\n')
    for (const line of lines) {
      if (!line.startsWith('data: ') || line === 'data: [DONE]') continue
      try {
        const event = JSON.parse(line.slice(6)) as SSEEvent
        if (event.type === 'content') {
          fullReport += event.delta as string
          updateStepCard(cardId, { content: fullReport })
        } else if (event.type === 'step' && event.status === 'done') {
          updateStepCard(cardId, { status: 'done' })
          researchStore.setReportContent(fullReport)
        }
      } catch {}
    }
  }

  researchStore.updateStepProgress('report', 'done')

  appendConfirm(
    '✅ 研究报告已生成完毕',
    [
      { label: '📥 导出 Markdown', action: 'exportReport' },
      { label: '📋 复制全文', action: 'copyReport' },
      { label: '🎤 继续访谈', action: 'showInterviewPicker' }
    ]
  )
}

// 单次访谈
async function runInterview(question: string) {
  if (!researchStore.selectedPersona) return

  const personaId = researchStore.selectedPersona.id
  const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : `${window.location.origin}/api/v1`

  const res = await fetch(`${API_BASE}/research-flow/interview/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      study_id: researchStore.studyId,
      persona_id: personaId,
      question,
      conversation_history: researchStore.interviewHistory[personaId] || []
    })
  })

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let fullResponse = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split('\n')
    for (const line of lines) {
      if (!line.startsWith('data: ') || line === 'data: [DONE]') continue
      try {
        const event = JSON.parse(line.slice(6)) as SSEEvent
        if (event.type === 'content') {
          fullResponse += event.delta as string
        }
      } catch {}
    }
  }

  researchStore.addInterviewMessage(personaId, { role: 'user', content: question })
  researchStore.addInterviewMessage(personaId, { role: 'assistant', content: fullResponse })
}

function handleConfirmAction(action: string) {
  switch (action) {
    case 'triggerPersonas':
      triggerPersonas()
      break
    case 'triggerScout':
      triggerScout()
      break
    case 'triggerAutoInterview':
      triggerAutoInterview()
      break
    case 'triggerReport':
      triggerReport()
      break
    case 'editStudy':
      // TODO: 实现编辑研究
      break
    case 'exportReport':
      // 由 topbar 处理
      break
    case 'copyReport':
      if (researchStore.reportContent) {
        navigator.clipboard.writeText(researchStore.reportContent)
        alert('报告已复制到剪贴板')
      }
      break
    case 'showInterviewPicker':
      // TODO: 显示访谈选择器
      break
  }
}

function useExample(text: string) {
  handleSend(text)
}

defineExpose({
  handleSend,
  triggerPersonas,
  triggerScout,
  triggerAutoInterview,
  triggerReport
})
</script>

<template>
  <div ref="chatArea" class="chat-area">
    <div ref="messagesContainer" class="messages-container">
      <!-- 欢迎界面 -->
      <WelcomeScreen v-if="uiStore.welcomeVisible" :examples="exampleCards" @use-example="useExample" />

      <!-- 消息列表 -->
      <template v-for="msg in messages" :key="msg.id">
        <UserMessage v-if="msg.type === 'user'" :content="msg.content" />
        <AgentMessage v-else :content="msg.content">
          <template v-for="comp in msg.components" :key="comp.id">
            <ConfirmBlock
              v-if="comp.type === 'confirm'"
              :question="(comp.props.question as string)"
              :options="(comp.props.options as Array<{ label: string; action: string }>)"
              @action="handleConfirmAction"
            />
          </template>
        </AgentMessage>
      </template>

      <!-- 步骤卡片 -->
      <AgentMessage v-if="stepCards.size > 0">
        <template v-for="[id, card] in stepCards" :key="id">
          <StepCard
            :id="id"
            :title="card.title"
            :desc="card.desc"
            :status="card.status"
            :content="card.content"
          />
        </template>
      </AgentMessage>

      <!-- 人设网格 -->
      <AgentMessage v-if="researchStore.personas.length > 0">
        <PersonaGrid :personas="researchStore.personas" />
      </AgentMessage>
    </div>
  </div>
</template>
