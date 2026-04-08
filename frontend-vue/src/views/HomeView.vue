<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import TheTopbar from '@/components/layout/TheTopbar.vue'
import TheProgressBar from '@/components/layout/TheProgressBar.vue'
import InputArea from '@/components/layout/InputArea.vue'
import { useResearchStore, useUIStore, useAuthStore } from '@/stores'
import { useMarkdown } from '@/composables'
import type { SSEEvent, Persona } from '@/types'

const router = useRouter()
const researchStore = useResearchStore()
const uiStore = useUIStore()
const authStore = useAuthStore()
const { simpleMarkdown } = useMarkdown()

const chatArea = ref<HTMLElement | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)
const inputAreaRef = ref<InstanceType<typeof InputArea> | null>(null)

interface Message {
  id: string
  type: 'user' | 'agent' | 'stepCard'
  content: string
  html?: string
  stepData?: {
    id: string
    title: string
    desc: string
    status: string
    content: string
    footer: string
  }
}

const messages = ref<Message[]>([])

function scrollToBottom() {
  requestAnimationFrame(() => {
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

function addStepCard(id: string, title: string, desc: string, status: string = 'running') {
  messages.value.push({
    id: id,
    type: 'stepCard',
    content: '',
    stepData: { id, title, desc, status, content: '', footer: '' }
  })
  uiStore.expandStep(id)
  scrollToBottom()
}

function updateStepCardStatus(status: string) {
  const lastStepCard = [...messages.value].reverse().find(m => m.type === 'stepCard')
  if (lastStepCard?.stepData) {
    lastStepCard.stepData.status = status
  }
}

function updateStepCardContent(content: string) {
  const lastStepCard = [...messages.value].reverse().find(m => m.type === 'stepCard')
  if (lastStepCard?.stepData) {
    lastStepCard.stepData.content = content
  }
}

function updateStepCardFooter(footer: string) {
  const lastStepCard = [...messages.value].reverse().find(m => m.type === 'stepCard')
  if (lastStepCard?.stepData) {
    lastStepCard.stepData.footer = footer
  }
}

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api/v1'
  : `${window.location.origin}/api/v1`

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (authStore.token) {
    headers['Authorization'] = `Bearer ${authStore.token}`
  }
  return headers
}

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

function parseSSEEvents(text: string): string[] {
  const events: string[] = []
  const lines = text.split('\n')
  let currentEvent = ''

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      if (currentEvent) events.push(currentEvent)
      currentEvent = line.slice(6)
    } else if (line === '' && currentEvent) {
      events.push(currentEvent)
      currentEvent = ''
    }
  }
  if (currentEvent) events.push(currentEvent)
  return events
}

async function runDesignStudy(userRequest: string) {
  const attachContext = researchStore.attachments.map(a => a.text).join('\n\n')
  addStepCard(`step-design-${Date.now()}`, '🎯 设计研究框架', '正在分析研究需求，构建访谈框架...', 'running')

  let fullContent = ''
  researchStore.setStreaming(true)
  researchStore.setPhase('designing')
  researchStore.updateStepProgress('design', 'active')

  try {
    const res = await fetch(`${API_BASE}/research-flow/design-study`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_request: userRequest, context: attachContext })
    })

    if (!res.ok) {
      if (res.status === 401) {
        authStore.logout()
        router.push('/login')
        return
      }
      updateStepCardStatus('error')
      researchStore.setStreaming(false)
      return
    }

    const reader = res.body?.getReader()
    if (!reader) {
      updateStepCardStatus('error')
      researchStore.setStreaming(false)
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (value) {
        buffer += decoder.decode(value, { stream: true })
      }
      if (done) {
        if (buffer.trim()) {
          const events = parseSSEEvents(buffer)
          for (const eventStr of events) {
            if (eventStr === '[DONE]') continue
            try {
              const event = JSON.parse(eventStr) as SSEEvent
              if (event.type === 'study_id') {
                researchStore.setStudyId(event.study_id as string)
                researchStore.setStudyTitle(userRequest.substring(0, 20) + '...')
              } else if (event.type === 'content') {
                fullContent += event.delta as string
                updateStepCardContent(fullContent)
              } else if (event.type === 'step' && event.status === 'done') {
                updateStepCardStatus('done')
              }
            } catch {}
          }
        }
        break
      }

      const events = parseSSEEvents(buffer)
      buffer = ''

      for (const eventStr of events) {
        if (eventStr === '[DONE]') continue
        try {
          const event = JSON.parse(eventStr) as SSEEvent
          if (event.type === 'study_id') {
            researchStore.setStudyId(event.study_id as string)
            researchStore.setStudyTitle(userRequest.substring(0, 20) + '...')
          } else if (event.type === 'content') {
            fullContent += event.delta as string
            updateStepCardContent(fullContent)
            scrollToBottom()
          } else if (event.type === 'step' && event.status === 'done') {
            updateStepCardStatus('done')
          }
        } catch {
          buffer = eventStr
        }
      }
    }

    researchStore.updateStepProgress('design', 'done')
    researchStore.updateStepProgress('personas', 'active')
    researchStore.setPhase('post-design')
    uiStore.showToolbarButton('personas')

    updateStepCardFooter(`
      <div class="confirm-block">
        <div class="confirm-question">框架已生成 ✓ 接下来要怎么做？</div>
        <div class="confirm-options">
          <button class="confirm-btn primary" onclick="window.triggerPersonas && window.triggerPersonas()">🧠 生成目标人设</button>
          <button class="confirm-btn" onclick="window.editStudy && window.editStudy()">✏️ 调整研究方向</button>
        </div>
      </div>
    `)
    scrollToBottom()
  } catch (e) {
    console.error('runDesignStudy error:', e)
    updateStepCardStatus('error')
  }

  researchStore.setStreaming(false)
}

function buildPersonasGridHtml(): string {
  const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']
  let html = '<div class="personas-grid">'
  researchStore.personas.forEach((persona, index) => {
    const painPoints = Array.isArray(persona.pain_points)
      ? persona.pain_points.join('、')
      : (persona.pain_points || '')
    html += `
      <div class="persona-card" onclick="this.classList.toggle('expanded')">
        <div class="persona-expand-icon">▼</div>
        <div class="persona-card-header">
          <div class="persona-card-avatar">${emojis[index % 5]}</div>
          <div class="persona-card-info">
            <div class="persona-card-name">${persona.name}</div>
            <div class="persona-card-meta">${persona.age || ''}岁 · ${persona.occupation || ''}</div>
          </div>
        </div>
        <div class="persona-card-tags">
          ${(persona.core_values || []).slice(0, 3).map((v: string) => `<span class="persona-card-tag">${v}</span>`).join('')}
        </div>
        <div class="persona-detail-panel">
          <div class="persona-detail-section">
            <div class="persona-detail-label">📋 背景</div>
            <div class="persona-detail-value">${persona.background || ''}</div>
          </div>
          <div class="persona-detail-section">
            <div class="persona-detail-label">😤 痛点</div>
            <div class="persona-detail-value">${painPoints}</div>
          </div>
          <div class="persona-detail-section">
            <div class="persona-detail-label">🎯 态度</div>
            <div class="persona-detail-value">${persona.attitude || ''}</div>
          </div>
        </div>
      </div>
    `
  })
  html += '</div>'
  return html
}

async function triggerPersonas() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  addStepCard(`step-personas-${Date.now()}`, '👥 生成目标人设', '正在构建初始用户画像...', 'running')
  researchStore.setStreaming(true)
  researchStore.setPhase('personas')
  researchStore.updateStepProgress('personas', 'active')

  try {
    const res = await fetch(`${API_BASE}/research-flow/search-personas`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        study_id: researchStore.studyId,
        persona_description: '根据研究背景生成',
        max_count: 10
      })
    })

    if (!res.ok) {
      updateStepCardStatus('error')
      researchStore.setStreaming(false)
      return
    }

    const reader = res.body?.getReader()
    if (!reader) return

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = parseSSEEvents(buffer)
      buffer = ''

      for (const eventStr of events) {
        if (eventStr === '[DONE]') continue
        try {
          const event = JSON.parse(eventStr) as SSEEvent
          if (event.type === 'persona') {
            const p = event.persona as Persona
            researchStore.addPersona(p)
            updateStepCardContent(buildPersonasGridHtml())
            scrollToBottom()
          } else if (event.type === 'step' && event.status === 'done') {
            updateStepCardStatus('done')
          }
        } catch {
          buffer = eventStr
        }
      }
    }

    researchStore.updateStepProgress('personas', 'done')
    researchStore.updateStepProgress('scout', 'active')
    uiStore.showToolbarButton('scout')
    uiStore.showToolbarButton('interview')

    updateStepCardFooter(`
      <div class="confirm-block">
        <div class="confirm-question">已生成 ${researchStore.personas.length} 个用户画像</div>
        <div class="confirm-options">
          <button class="confirm-btn primary" onclick="window.triggerScout && window.triggerScout()">🌐 开始社媒侦察</button>
        </div>
      </div>
    `)
  } catch (e) {
    console.error('triggerPersonas error:', e)
    updateStepCardStatus('error')
  }

  researchStore.setStreaming(false)
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

async function triggerScout() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  addStepCard(`step-scout-${Date.now()}`, '🌐 社交媒体侦察', '为每个人设搜索专属社媒内容...', 'running')
  researchStore.setStreaming(true)
  researchStore.setPhase('scouting')
  researchStore.updateStepProgress('scout', 'active')

  const title = researchStore.studyTitle.replace('...', '')
  const keywords = title.split(/[，,、\s]+/).filter(k => k.length > 1).slice(0, 3)
  if (keywords.length === 0) keywords.push('用户研究')

  const personaScoutData: Record<string, { name: string; posts: any[]; insights: string[]; done: boolean }> = {}
  let currentPersonaId = ''
  let currentPersonaName = ''
  let totalPosts = 0

  function buildScoutContentHtml(): string {
    let html = ''
    if (currentPersonaName && !personaScoutData[currentPersonaId]?.done) {
      html += `<div class="scout-progress">🔍 正在为「${currentPersonaName}」搜索社媒内容...</div>`
    }
    html += '<div class="scout-persona-cards">'
    Object.entries(personaScoutData).forEach(([pid, data]) => {
      const statusIcon = data.done ? '✓' : '⏳'
      const statusClass = data.done ? 'done' : 'loading'
      html += `
        <div class="scout-persona-card ${statusClass}">
          <div class="scout-persona-card-header">
            <span class="scout-persona-status">${statusIcon}</span>
            <span class="scout-persona-name">${escapeHtml(data.name)}</span>
            <span class="scout-persona-count">${data.posts.length} 条</span>
          </div>
          <div class="scout-persona-card-body">
            ${data.insights.length > 0 ? `
              <div class="scout-insights-block">
                <div class="scout-insights-title">💡 核心洞察</div>
                ${data.insights.map(i => `<div class="scout-insight-item">${escapeHtml(i)}</div>`).join('')}
              </div>
            ` : ''}
          </div>
        </div>
      `
    })
    html += '</div>'
    return html
  }

  try {
    const res = await fetch(`${API_BASE}/research-flow/scout-and-build`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        study_id: researchStore.studyId,
        keywords,
        platforms: ['小红书', '微博', '抖音']
      })
    })

    if (!res.ok) {
      updateStepCardStatus('error')
      researchStore.setStreaming(false)
      return
    }

    const reader = res.body?.getReader()
    if (!reader) return
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = parseSSEEvents(buffer)
      buffer = ''

      for (const eventStr of events) {
        if (eventStr === '[DONE]') continue
        try {
          const event = JSON.parse(eventStr) as SSEEvent
          if (event.type === 'persona_scout_start') {
            currentPersonaId = (event as any).persona_id
            currentPersonaName = (event as any).persona_name
            personaScoutData[currentPersonaId] = { name: currentPersonaName, posts: [], insights: [], done: false }
            updateStepCardContent(buildScoutContentHtml())
          } else if (event.type === 'post') {
            const post = (event as any).post
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].posts.push(post)
              totalPosts++
            }
            updateStepCardContent(buildScoutContentHtml())
          } else if (event.type === 'persona_insights') {
            const insights = (event as any).insights || []
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].insights.push(...insights)
            }
          } else if (event.type === 'updated_persona') {
            researchStore.updatePersona(event.persona as Persona)
          } else if (event.type === 'persona_scout_done') {
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) personaScoutData[personaId].done = true
          } else if (event.type === 'step' && event.step === 'build_persona' && event.status === 'done') {
            updateStepCardStatus('done')
          }
        } catch {
          buffer = eventStr
        }
      }
    }

    researchStore.updateStepProgress('scout', 'done')
    researchStore.updateStepProgress('interview', 'active')
    updateStepCardFooter(`
      <div class="confirm-block">
        <div class="confirm-question">社媒侦察完成 ✓ 已收集 ${totalPosts} 条内容</div>
        <div class="confirm-options">
          <button class="confirm-btn primary" onclick="window.triggerAutoInterview && window.triggerAutoInterview()">🎤 自动深度访谈</button>
        </div>
      </div>
    `)
  } catch (e) {
    console.error('triggerScout error:', e)
    updateStepCardStatus('error')
  }

  researchStore.setStreaming(false)
}

async function triggerAutoInterview() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  addStepCard(`step-interview-${Date.now()}`, '🎤 自动深度访谈', '正在对所有用户人设执行访谈...', 'running')
  researchStore.setStreaming(true)
  researchStore.setPhase('interviewing')
  researchStore.updateStepProgress('interview', 'active')

  let totalPersonas = 0
  let completedPersonas = 0
  const questions: string[] = []
  const personaInterviews: Record<string, { name: string; index: number; qaList: { question: string; answer: string }[]; done: boolean }> = {}

  function buildInterviewContentHtml(): string {
    let html = `
      <div class="interview-progress">
        <div class="interview-progress-text">${completedPersonas >= totalPersonas ? `✓ 全部 ${totalPersonas} 位用户访谈完成` : `正在访谈... (${completedPersonas}/${totalPersonas})`}</div>
        <div class="interview-progress-bar-bg">
          <div class="interview-progress-bar" style="width: ${totalPersonas > 0 ? (completedPersonas / totalPersonas * 100) : 0}%"></div>
        </div>
      </div>
    `
    if (questions.length > 0) {
      html += `<div class="interview-questions"><div class="interview-questions-title">📋 访谈提纲</div>`
      questions.forEach((q, i) => { html += `<div class="interview-question-item">${i + 1}. ${escapeHtml(q)}</div>` })
      html += `</div>`
    }
    html += `<div class="interview-persona-cards">`
    Object.entries(personaInterviews).forEach(([, data]) => {
      const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']
      const emoji = emojis[data.index % 5]
      html += `
        <div class="interview-persona-card ${data.done ? 'done' : 'active'}">
          <div class="interview-persona-header">
            <div class="interview-persona-avatar">${emoji}</div>
            <div class="interview-persona-info">
              <div class="interview-persona-name">${escapeHtml(data.name)}</div>
              <div class="interview-persona-meta">${data.done ? `${data.qaList.length} 轮问答完成 ✓` : '访谈进行中...'}</div>
            </div>
          </div>
        </div>
      `
    })
    html += `</div>`
    return html
  }

  try {
    const res = await fetch(`${API_BASE}/research-flow/auto-interview`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ study_id: researchStore.studyId })
    })

    if (!res.ok) {
      updateStepCardStatus('error')
      researchStore.setStreaming(false)
      return
    }

    const reader = res.body?.getReader()
    if (!reader) return
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = parseSSEEvents(buffer)
      buffer = ''

      for (const eventStr of events) {
        if (eventStr === '[DONE]') continue
        try {
          const event = JSON.parse(eventStr) as SSEEvent
          if (event.type === 'questions') {
            questions.push(...((event as any).questions || []))
          } else if (event.type === 'interview_start') {
            totalPersonas = (event as any).total || totalPersonas
            const personaId = (event as any).persona_id
            personaInterviews[personaId] = { name: (event as any).persona_name, index: (event as any).index || 0, qaList: [], done: false }
          } else if (event.type === 'qa') {
            const personaId = (event as any).persona_id
            if (personaInterviews[personaId]) {
              personaInterviews[personaId].qaList.push({ question: (event as any).question, answer: (event as any).answer })
            }
            researchStore.addInterviewMessage(personaId, { role: 'user', content: (event as any).question })
            researchStore.addInterviewMessage(personaId, { role: 'assistant', content: (event as any).answer })
          } else if (event.type === 'interview_done') {
            const personaId = (event as any).persona_id
            if (personaInterviews[personaId]) personaInterviews[personaId].done = true
            completedPersonas++
          } else if (event.type === 'step' && event.step === 'auto_interview' && event.status === 'done') {
            updateStepCardStatus('done')
          }
          updateStepCardContent(buildInterviewContentHtml())
        } catch {
          buffer = eventStr
        }
      }
    }

    researchStore.updateStepProgress('interview', 'done')
    researchStore.updateStepProgress('report', 'active')
    uiStore.showToolbarButton('report')
    updateStepCardFooter(`
      <div class="confirm-block">
        <div class="confirm-question">自动访谈完成 ✓ 共 ${completedPersonas} 位用户</div>
        <div class="confirm-options">
          <button class="confirm-btn primary" onclick="window.triggerReport && window.triggerReport()">📊 生成研究报告</button>
        </div>
      </div>
    `)
  } catch (e) {
    console.error('triggerAutoInterview error:', e)
    updateStepCardStatus('error')
  }

  researchStore.setStreaming(false)
}

async function triggerReport() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  addStepCard(`step-report-${Date.now()}`, '📊 生成研究报告', '整合人设数据与访谈洞察...', 'running')
  researchStore.setStreaming(true)
  researchStore.setPhase('reporting')
  researchStore.updateStepProgress('report', 'active')

  const transcripts = Object.entries(researchStore.interviewHistory).map(([id, msgs]) => ({
    persona_id: id,
    messages: msgs
  }))

  let fullReport = ''

  try {
    const res = await fetch(`${API_BASE}/research-flow/generate-report`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        study_id: researchStore.studyId,
        personas: researchStore.personas,
        interview_transcripts: transcripts,
        format: 'markdown'
      })
    })

    if (!res.ok) {
      updateStepCardStatus('error')
      researchStore.setStreaming(false)
      return
    }

    const reader = res.body?.getReader()
    if (!reader) return
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = parseSSEEvents(buffer)
      buffer = ''

      for (const eventStr of events) {
        if (eventStr === '[DONE]') continue
        try {
          const event = JSON.parse(eventStr) as SSEEvent
          if (event.type === 'content') {
            fullReport += event.delta as string
            updateStepCardContent(fullReport)
            scrollToBottom()
          } else if (event.type === 'step' && event.status === 'done') {
            updateStepCardStatus('done')
            researchStore.setReportContent(fullReport)
          }
        } catch {
          buffer = eventStr
        }
      }
    }

    researchStore.updateStepProgress('report', 'done')
    updateStepCardFooter(`
      <div class="confirm-block">
        <div class="confirm-question">✅ 研究报告已生成完毕</div>
        <div class="confirm-options">
          <button class="confirm-btn primary" onclick="window.exportReport && window.exportReport()">📥 导出 Markdown</button>
        </div>
      </div>
    `)
  } catch (e) {
    console.error('triggerReport error:', e)
    updateStepCardStatus('error')
  }

  researchStore.setStreaming(false)
}

async function runInterview(question: string) {
  if (!researchStore.selectedPersona || !researchStore.studyId) return
  const personaId = researchStore.selectedPersona.id
  researchStore.setStreaming(true)

  try {
    const res = await fetch(`${API_BASE}/research-flow/interview/stream`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        study_id: researchStore.studyId,
        persona_id: personaId,
        question,
        conversation_history: researchStore.interviewHistory[personaId] || []
      })
    })

    if (!res.ok) {
      researchStore.setStreaming(false)
      return
    }

    const reader = res.body?.getReader()
    if (!reader) return
    const decoder = new TextDecoder()
    let buffer = ''
    let fullResponse = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = parseSSEEvents(buffer)
      buffer = ''

      for (const eventStr of events) {
        if (eventStr === '[DONE]') continue
        try {
          const event = JSON.parse(eventStr) as SSEEvent
          if (event.type === 'content') {
            fullResponse += event.delta as string
          }
        } catch {
          buffer = eventStr
        }
      }
    }

    researchStore.addInterviewMessage(personaId, { role: 'user', content: question })
    researchStore.addInterviewMessage(personaId, { role: 'assistant', content: fullResponse })
  } catch (e) {
    console.error('访谈出错', e)
  }

  researchStore.setStreaming(false)
  scrollToBottom()
}

function exportReport() {
  if (!researchStore.reportContent) {
    alert('暂无报告内容')
    return
  }
  const blob = new Blob([researchStore.reportContent], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `research-report-${researchStore.studyId || Date.now()}.md`
  a.click()
  URL.revokeObjectURL(url)
}

function editStudy() {
  inputAreaRef.value?.setInputText('请调整研究方向：')
}

// 暴露全局函数供 onclick 调用
if (typeof window !== 'undefined') {
  const w = window as any
  w.triggerPersonas = triggerPersonas
  w.triggerScout = triggerScout
  w.triggerAutoInterview = triggerAutoInterview
  w.triggerReport = triggerReport
  w.exportReport = exportReport
  w.editStudy = editStudy
}

const statusIcons: Record<string, string> = {
  pending: '○',
  running: '↻',
  done: '✓',
  error: '✗'
}
</script>

<template>
  <div class="home-layout">
    <TheSidebar />
    <main class="main">
      <TheTopbar />
      <TheProgressBar />

      <div ref="chatArea" class="chat-area">
      <div ref="messagesContainer" class="messages-container">
        <div v-if="uiStore.welcomeVisible" class="welcome-screen">
          <span class="welcome-icon">🔬</span>
          <h1 class="welcome-title">开始你的用户研究</h1>
          <p class="welcome-sub">告诉我你想研究什么，我会帮你完成从框架设计到洞察报告的完整研究流程</p>
          <div class="example-cards">
            <div class="example-card" @click="handleSend('我想研究年轻女性对国产美妆品牌的态度')">
              <div class="example-card-icon">💄</div>
              <div class="example-card-title">国产美妆用户研究</div>
              <div class="example-card-desc">了解年轻女性对国货美妆的真实态度</div>
            </div>
            <div class="example-card" @click="handleSend('帮我研究新能源汽车用户的购买决策顾虑')">
              <div class="example-card-icon">🚗</div>
              <div class="example-card-title">新能源汽车决策研究</div>
              <div class="example-card-desc">挖掘购车决策中的深层顾虑</div>
            </div>
            <div class="example-card" @click="handleSend('研究 35-50 岁中年人的健康管理需求')">
              <div class="example-card-icon">💪</div>
              <div class="example-card-title">健康 App 用户研究</div>
              <div class="example-card-desc">探索中年人健康管理需求与痛点</div>
            </div>
            <div class="example-card" @click="handleSend('研究职场中使用 AI 工具的白领群体')">
              <div class="example-card-icon">🤖</div>
              <div class="example-card-title">AI 工具职场使用研究</div>
              <div class="example-card-desc">理解职场 AI 工具采纳的心理障碍</div>
            </div>
          </div>
        </div>

        <template v-for="msg in messages" :key="msg.id">
          <div v-if="msg.type === 'user'" class="msg-user fade-in">
            <div class="bubble">{{ msg.content }}</div>
          </div>
          <div v-else-if="msg.type === 'agent'" class="msg-agent fade-in">
            <div class="agent-avatar">✦</div>
            <div class="agent-content">
              <div class="agent-name">ResearchMind</div>
              <div class="agent-body" v-html="msg.html || msg.content"></div>
            </div>
          </div>
          <div v-else-if="msg.type === 'stepCard' && msg.stepData" class="msg-agent fade-in">
            <div class="agent-avatar">✦</div>
            <div class="agent-content">
              <div class="agent-name">ResearchMind</div>
              <div class="agent-body">
                <div class="step-card fade-in">
                  <div class="step-header" @click="uiStore.toggleStep(msg.stepData!.id)">
                    <div :class="['step-status-icon', msg.stepData.status]">
                      {{ statusIcons[msg.stepData.status] || '○' }}
                    </div>
                    <div class="step-info">
                      <div class="step-title">{{ msg.stepData.title }}</div>
                      <div class="step-desc">{{ msg.stepData.desc }}</div>
                    </div>
                    <div class="step-expand-icon">
                      {{ uiStore.expandedSteps.includes(msg.stepData.id) ? '▼' : '▶' }}
                    </div>
                  </div>
                  <div :class="['step-body', { visible: uiStore.expandedSteps.includes(msg.stepData.id) }]">
                    <div v-if="msg.stepData.content" class="streaming-text">
                      <div class="markdown" v-html="simpleMarkdown(msg.stepData.content)"></div>
                      <span v-if="msg.stepData.status === 'running'" class="cursor"></span>
                    </div>
                    <div v-if="msg.stepData.footer && msg.stepData.status === 'done'" class="step-footer" v-html="msg.stepData.footer"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <InputArea
      ref="inputAreaRef"
      @send="handleSend"
      @trigger-personas="triggerPersonas"
      @trigger-scout="triggerScout"
      @trigger-interview="triggerAutoInterview"
      @trigger-report="triggerReport"
    />
    </main>
  </div>
</template>

<style scoped>
/* 样式从原有 App.vue 继承 */
</style>
