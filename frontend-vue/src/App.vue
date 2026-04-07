<script setup lang="ts">
import { ref } from 'vue'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import TheTopbar from '@/components/layout/TheTopbar.vue'
import TheProgressBar from '@/components/layout/TheProgressBar.vue'
import InputArea from '@/components/layout/InputArea.vue'
import { useResearchStore, useUIStore } from '@/stores'
import { useMarkdown } from '@/composables'
import type { SSEEvent, Persona } from '@/types'

const researchStore = useResearchStore()
const uiStore = useUIStore()
const { simpleMarkdown } = useMarkdown()

const chatArea = ref<HTMLElement | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)
const inputAreaRef = ref<InstanceType<typeof InputArea> | null>(null)

interface Message {
  id: string
  type: 'user' | 'agent' | 'stepCard'
  content: string
  html?: string
  // 步骤卡片专用字段
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
  // 自动展开步骤卡片
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

// 处理发送消息
async function handleSend(text: string) {
  console.log('handleSend called with:', text)
  console.log('isStreaming:', researchStore.isStreaming, 'phase:', researchStore.phase)

  if (researchStore.isStreaming) {
    console.log('Already streaming, ignoring...')
    return
  }

  addUserMsg(text)
  console.log('User message added, calling runDesignStudy...')

  if (researchStore.phase === 'idle') {
    await runDesignStudy(text)
  } else if (researchStore.phase === 'interviewing' && researchStore.selectedPersona) {
    await runInterview(text)
  } else {
    await runDesignStudy(text)
  }
}

// 解析 SSE 事件流的辅助函数
function parseSSEEvents(text: string): string[] {
  const events: string[] = []
  const lines = text.split('\n')
  let currentEvent = ''

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      if (currentEvent) {
        events.push(currentEvent)
      }
      currentEvent = line.slice(6)
    } else if (line === '' && currentEvent) {
      events.push(currentEvent)
      currentEvent = ''
    }
  }

  if (currentEvent) {
    events.push(currentEvent)
  }

  return events
}

// 设计研究
async function runDesignStudy(userRequest: string) {
  console.log('runDesignStudy called, API_BASE:', API_BASE)
  const attachContext = researchStore.attachments.map(a => a.text).join('\n\n')

  addStepCard(`step-design-${Date.now()}`, '🎯 设计研究框架', '正在分析研究需求，构建访谈框架...', 'running')

  let fullContent = ''

  researchStore.setStreaming(true)
  researchStore.setPhase('designing')
  researchStore.updateStepProgress('design', 'active')

  try {
    const url = `${API_BASE}/research-flow/design-study`
    console.log('Fetching:', url)
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_request: userRequest, context: attachContext })
    })

    if (!res.ok) {
      console.error('HTTP error:', res.status, res.statusText)
      updateStepCardStatus('error')
      researchStore.setStreaming(false)
      return
    }

    const reader = res.body?.getReader()
    if (!reader) {
      console.error('No reader available')
      updateStepCardStatus('error')
      researchStore.setStreaming(false)
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    console.log('Starting to read SSE stream...')

    while (true) {
      const { done, value } = await reader.read()
      console.log('Read chunk, done:', done, 'value length:', value?.length)

      if (value) {
        const chunkText = decoder.decode(value, { stream: true })
        console.log('Chunk text:', chunkText.substring(0, 200))
        buffer += chunkText
      }

      if (done) {
        console.log('Stream done, processing remaining buffer...')
        // 处理剩余的 buffer
        if (buffer.trim()) {
          const events = parseSSEEvents(buffer)
          for (const eventStr of events) {
            if (eventStr === '[DONE]') continue
            try {
              const event = JSON.parse(eventStr) as SSEEvent
              console.log('Final SSE event:', event.type, event)
              if (event.type === 'study_id') {
                researchStore.setStudyId(event.study_id as string)
                researchStore.setStudyTitle(userRequest.substring(0, 20) + '...')
              } else if (event.type === 'content') {
                fullContent += event.delta as string
                updateStepCardContent(fullContent)
              } else if (event.type === 'step' && event.status === 'done') {
                updateStepCardStatus('done')
              }
            } catch (parseError) {
              console.warn('Failed to parse final SSE event:', eventStr)
            }
          }
        }
        break
      }

      const events = parseSSEEvents(buffer)
      console.log('Parsed events:', events.length)
      buffer = ''

      for (const eventStr of events) {
        if (eventStr === '[DONE]') continue
        try {
          const event = JSON.parse(eventStr) as SSEEvent
          console.log('SSE event:', event.type, event)
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
        } catch (parseError) {
          console.warn('Failed to parse SSE event:', eventStr, parseError)
          // 不完整的 JSON 可能是因为 chunk 边界，保存到 buffer 继续处理
          buffer = eventStr
        }
      }
    }

    console.log('Stream finished, updating UI...')
    researchStore.updateStepProgress('design', 'done')
    researchStore.updateStepProgress('personas', 'active')
    researchStore.setPhase('post-design')

    uiStore.showToolbarButton('personas')

    // 将确认按钮添加到步骤卡片 footer
    console.log('Adding confirm buttons to step card footer...')
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

// 生成人设网格 HTML
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

// 生成人设
async function triggerPersonas() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  addStepCard(`step-personas-${Date.now()}`, '👥 生成目标人设', '正在构建初始用户画像...', 'running')

  researchStore.setStreaming(true)
  researchStore.setPhase('personas')
  researchStore.updateStepProgress('personas', 'active')

  try {
    const res = await fetch(`${API_BASE}/research-flow/search-personas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        study_id: researchStore.studyId,
        persona_description: '根据研究背景生成',
        max_count: 10
      })
    })

    if (!res.ok) {
      console.error('HTTP error:', res.status)
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
            // 实时更新步骤卡片内容，显示已生成的人设
            updateStepCardContent(buildPersonasGridHtml())
            scrollToBottom()
          } else if (event.type === 'step' && event.status === 'done') {
            updateStepCardStatus('done')
          }
        } catch (parseError) {
          console.warn('Failed to parse SSE event:', eventStr)
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

// 社媒侦察
async function triggerScout() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  addStepCard(`step-scout-${Date.now()}`, '🌐 社交媒体侦察', '为每个人设搜索专属社媒内容...', 'running')

  researchStore.setStreaming(true)
  researchStore.setPhase('scouting')
  researchStore.updateStepProgress('scout', 'active')

  const title = researchStore.studyTitle.replace('...', '')
  const keywords = title.split(/[，,、\s]+/).filter(k => k.length > 1).slice(0, 3)
  if (keywords.length === 0) keywords.push('用户研究')

  // 按人设分组收集数据
  const personaScoutData: Record<string, {
    name: string
    posts: any[]
    insights: string[]
    done: boolean
  }> = {}
  let currentPersonaId = ''
  let currentPersonaName = ''
  let totalPosts = 0

  // 转义 HTML
  function escapeHtml(str: string): string {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  }

  // 构建侦察结果 HTML
  function buildScoutContentHtml(): string {
    let html = ''

    // 当前进度提示
    if (currentPersonaName && !personaScoutData[currentPersonaId]?.done) {
      html += `<div class="scout-progress">🔍 正在为「${currentPersonaName}」搜索社媒内容...</div>`
    }

    // 人设卡片列表
    html += '<div class="scout-persona-cards">'

    Object.entries(personaScoutData).forEach(([pid, data]) => {
      const statusIcon = data.done ? '✓' : '⏳'
      const statusClass = data.done ? 'done' : 'loading'
      const postCount = data.posts.length

      html += `
        <div class="scout-persona-card ${statusClass}" onclick="this.classList.toggle('expanded')">
          <div class="scout-persona-card-header">
            <span class="scout-persona-status">${statusIcon}</span>
            <span class="scout-persona-name">${escapeHtml(data.name)}</span>
            <span class="scout-persona-count">${postCount} 条</span>
            <span class="scout-persona-expand">▼</span>
          </div>
          <div class="scout-persona-card-body">
            ${data.insights.length > 0 ? `
              <div class="scout-insights-block">
                <div class="scout-insights-title">💡 核心洞察</div>
                ${data.insights.map(insight => `<div class="scout-insight-item">${escapeHtml(insight)}</div>`).join('')}
              </div>
            ` : ''}
            ${data.posts.length > 0 ? `
              <div class="scout-posts-block">
                <div class="scout-posts-title">📝 社媒内容</div>
                ${data.posts.map(post => {
                  const platformClass = post.platform || '社媒'
                  const sentimentIcon = post.sentiment === 'positive' ? '😊' : post.sentiment === 'negative' ? '😟' : '😐'
                  return `
                    <div class="scout-post-item">
                      <div class="scout-post-header">
                        <span class="scout-post-platform ${platformClass}">${post.platform || '社媒'}</span>
                        <span class="scout-post-sentiment">${sentimentIcon}</span>
                      </div>
                      <div class="scout-post-content">${escapeHtml(post.content || '')}</div>
                    </div>
                  `
                }).join('')}
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        study_id: researchStore.studyId,
        keywords,
        platforms: ['小红书', '微博', '抖音']
      })
    })

    if (!res.ok) {
      console.error('HTTP error:', res.status)
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
            // 初始化该人设的数据
            if (!personaScoutData[currentPersonaId]) {
              personaScoutData[currentPersonaId] = {
                name: currentPersonaName,
                posts: [],
                insights: [],
                done: false
              }
            }
            updateStepCardContent(buildScoutContentHtml())

          } else if (event.type === 'post') {
            const post = (event as any).post
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].posts.push(post)
              totalPosts++
            }
            updateStepCardContent(buildScoutContentHtml())
            scrollToBottom()

          } else if (event.type === 'persona_insights') {
            const insights = (event as any).insights || []
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].insights.push(...insights)
            }
            updateStepCardContent(buildScoutContentHtml())

          } else if (event.type === 'updated_persona') {
            researchStore.updatePersona(event.persona as Persona)

          } else if (event.type === 'persona_scout_done') {
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].done = true
            }
            updateStepCardContent(buildScoutContentHtml())

          } else if (event.type === 'step' && event.step === 'build_persona' && event.status === 'done') {
            updateStepCardStatus('done')
          }
        } catch (parseError) {
          console.warn('Failed to parse SSE event:', eventStr)
          buffer = eventStr
        }
      }
    }

    researchStore.updateStepProgress('scout', 'done')
    researchStore.updateStepProgress('interview', 'active')

    updateStepCardFooter(`
      <div class="confirm-block">
        <div class="confirm-question">社媒侦察完成 ✓ 已为 ${Object.keys(personaScoutData).length} 个人设收集 ${totalPosts} 条社媒内容。建议进行深度访谈来挖掘更深层的动机。</div>
        <div class="confirm-options">
          <button class="confirm-btn primary" onclick="window.triggerAutoInterview && window.triggerAutoInterview()">🎤 自动深度访谈</button>
          <button class="confirm-btn" onclick="window.triggerReport && window.triggerReport()">📊 直接生成报告</button>
        </div>
      </div>
    `)
  } catch (e) {
    console.error('triggerScout error:', e)
    updateStepCardStatus('error')
  }

  researchStore.setStreaming(false)
}

// 自动访谈
async function triggerAutoInterview() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  addStepCard(`step-interview-${Date.now()}`, '🎤 自动深度访谈', '正在基于访谈框架对所有用户人设执行访谈...', 'running')

  researchStore.setStreaming(true)
  researchStore.setPhase('interviewing')
  researchStore.updateStepProgress('interview', 'active')

  // 访谈数据收集
  let totalPersonas = 0
  let completedPersonas = 0
  const questions: string[] = []
  const personaInterviews: Record<string, {
    name: string
    index: number
    qaList: { question: string; answer: string }[]
    done: boolean
  }> = {}
  let currentPersonaId = ''
  let questionsPerPersona = 0

  // 转义 HTML
  function escapeHtml(str: string): string {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  }

  // 构建访谈内容 HTML
  function buildInterviewContentHtml(): string {
    let html = ''

    // 进度条
    html += `
      <div class="interview-progress">
        <div class="interview-progress-text">
          ${completedPersonas >= totalPersonas
            ? `✓ 全部 ${totalPersonas} 位用户访谈完成`
            : `正在访谈... (${completedPersonas}/${totalPersonas})`}
        </div>
        <div class="interview-progress-bar-bg">
          <div class="interview-progress-bar" style="width: ${totalPersonas > 0 ? (completedPersonas / totalPersonas * 100) : 0}%"></div>
        </div>
      </div>
    `

    // 问题列表
    if (questions.length > 0) {
      html += `<div class="interview-questions">`
      html += `<div class="interview-questions-title">📋 访谈提纲 (${questions.length} 题)</div>`
      questions.forEach((q, i) => {
        html += `<div class="interview-question-item">${i + 1}. ${escapeHtml(q)}</div>`
      })
      html += `</div>`
    }

    // 人设访谈卡片
    html += `<div class="interview-persona-cards">`
    Object.entries(personaInterviews).forEach(([pid, data]) => {
      const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']
      const emoji = emojis[data.index % 5]
      const statusText = data.done ? `${data.qaList.length} 轮问答完成 ✓` : '访谈进行中...'
      const statusIcon = data.done ? '✅' : '🎤'

      html += `
        <div class="interview-persona-card ${data.done ? 'done' : 'active'}">
          <div class="interview-persona-header">
            <div class="interview-persona-avatar">${emoji}</div>
            <div class="interview-persona-info">
              <div class="interview-persona-name">${escapeHtml(data.name)}</div>
              <div class="interview-persona-meta">${statusText}</div>
            </div>
            <div class="interview-persona-status">${statusIcon}</div>
          </div>
          <div class="interview-messages">
            ${data.qaList.map(qa => `
              <div class="interview-qa-item">
                <div class="interview-msg-q">${escapeHtml(qa.question)}</div>
                <div class="interview-msg-a">${escapeHtml(qa.answer)}</div>
              </div>
            `).join('')}
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ study_id: researchStore.studyId })
    })

    if (!res.ok) {
      console.error('HTTP error:', res.status)
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

          if (event.type === 'status') {
            // 状态消息，更新进度文本
            updateStepCardContent(buildInterviewContentHtml())

          } else if (event.type === 'questions') {
            // 收到问题列表
            const qs = (event as any).questions || []
            questions.push(...qs)
            updateStepCardContent(buildInterviewContentHtml())

          } else if (event.type === 'interview_start') {
            // 新人设开始访谈
            totalPersonas = (event as any).total || totalPersonas
            currentPersonaId = (event as any).persona_id
            const name = (event as any).persona_name
            const index = (event as any).index || 0

            personaInterviews[currentPersonaId] = {
              name,
              index,
              qaList: [],
              done: false
            }
            updateStepCardContent(buildInterviewContentHtml())
            scrollToBottom()

          } else if (event.type === 'qa') {
            // 收到 Q&A
            const personaId = (event as any).persona_id
            const question = (event as any).question
            const answer = (event as any).answer

            if (personaInterviews[personaId]) {
              personaInterviews[personaId].qaList.push({ question, answer })
            }

            // 同时更新 store
            researchStore.addInterviewMessage(personaId, { role: 'user', content: question })
            researchStore.addInterviewMessage(personaId, { role: 'assistant', content: answer })

            updateStepCardContent(buildInterviewContentHtml())
            scrollToBottom()

          } else if (event.type === 'interview_done') {
            // 该人设访谈完成
            const personaId = (event as any).persona_id
            questionsPerPersona = (event as any).qa_count || questionsPerPersona
            completedPersonas++

            if (personaInterviews[personaId]) {
              personaInterviews[personaId].done = true
            }
            updateStepCardContent(buildInterviewContentHtml())

          } else if (event.type === 'step' && event.step === 'auto_interview' && event.status === 'done') {
            updateStepCardStatus('done')
          }
        } catch (parseError) {
          console.warn('Failed to parse SSE event:', eventStr)
          buffer = eventStr
        }
      }
    }

    researchStore.updateStepProgress('interview', 'done')
    researchStore.updateStepProgress('report', 'active')

    uiStore.showToolbarButton('report')

    updateStepCardFooter(`
      <div class="confirm-block">
        <div class="confirm-question">自动访谈完成 ✓ 共对 ${completedPersonas} 位用户进行了深度访谈，每人 ${questionsPerPersona} 个问题。接下来生成研究报告？</div>
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

// 生成报告
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        study_id: researchStore.studyId,
        personas: researchStore.personas,
        interview_transcripts: transcripts,
        format: 'markdown'
      })
    })

    if (!res.ok) {
      console.error('HTTP error:', res.status)
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
        } catch (parseError) {
          console.warn('Failed to parse SSE event:', eventStr)
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
          <button class="confirm-btn" onclick="window.copyReport && window.copyReport()">📋 复制全文</button>
        </div>
      </div>
    `)
  } catch (e) {
    console.error('triggerReport error:', e)
    updateStepCardStatus('error')
  }

  researchStore.setStreaming(false)
}

// 单次访谈
async function runInterview(question: string) {
  if (!researchStore.selectedPersona || !researchStore.studyId) return

  const personaId = researchStore.selectedPersona.id

  researchStore.setStreaming(true)

  try {
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

    if (!res.ok) {
      console.error('HTTP error:', res.status)
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
        } catch (parseError) {
          console.warn('Failed to parse SSE event:', eventStr)
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

// 导出报告
function exportReport() {
  if (!researchStore.reportContent) {
    alert('暂无报告内容，请先生成报告')
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

// 复制报告
function copyReport() {
  if (researchStore.reportContent) {
    navigator.clipboard.writeText(researchStore.reportContent)
    alert('报告已复制到剪贴板')
  }
}

// 调整研究方向
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
  w.copyReport = copyReport
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
  <TheSidebar />
  <main class="main">
    <TheTopbar />
    <TheProgressBar />

    <!-- 对话区域 -->
    <div ref="chatArea" class="chat-area">
      <div ref="messagesContainer" class="messages-container">
        <!-- 欢迎界面 -->
        <div v-if="uiStore.welcomeVisible" class="welcome-screen">
          <span class="welcome-icon">🔬</span>
          <h1 class="welcome-title">开始你的用户研究</h1>
          <p class="welcome-sub">
            告诉我你想研究什么，我会帮你完成从框架设计到洞察报告的完整研究流程
          </p>
          <div class="example-cards">
            <div class="example-card" @click="handleSend('我想研究年轻女性（18-30岁）对国产美妆品牌的态度，特别是她们为什么选择或放弃国货品牌')">
              <div class="example-card-icon">💄</div>
              <div class="example-card-title">国产美妆用户研究</div>
              <div class="example-card-desc">了解年轻女性对国货美妆的真实态度</div>
            </div>
            <div class="example-card" @click="handleSend('帮我研究新能源汽车用户在购买决策中最关键的顾虑，特别是第一次购买电动车的人群')">
              <div class="example-card-icon">🚗</div>
              <div class="example-card-title">新能源汽车决策研究</div>
              <div class="example-card-desc">挖掘购车决策中的深层顾虑</div>
            </div>
            <div class="example-card" @click="handleSend('我们正在开发一款面向 35-50 岁中年人的健康管理 App，想了解这群人的健康焦虑和产品期望')">
              <div class="example-card-icon">💪</div>
              <div class="example-card-title">健康 App 用户研究</div>
              <div class="example-card-desc">探索中年人健康管理需求与痛点</div>
            </div>
            <div class="example-card" @click="handleSend('研究在职场中使用 AI 工具的白领群体，他们的使用习惯、信任感和抵触情绪从哪里来')">
              <div class="example-card-icon">🤖</div>
              <div class="example-card-title">AI 工具职场使用研究</div>
              <div class="example-card-desc">理解职场 AI 工具采纳的心理障碍</div>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <template v-for="msg in messages" :key="msg.id">
          <!-- 用户消息 -->
          <div v-if="msg.type === 'user'" class="msg-user fade-in">
            <div class="bubble">{{ msg.content }}</div>
          </div>
          <!-- Agent 消息 -->
          <div v-else-if="msg.type === 'agent'" class="msg-agent fade-in">
            <div class="agent-avatar">✦</div>
            <div class="agent-content">
              <div class="agent-name">ResearchMind</div>
              <div class="agent-body" v-html="msg.html || msg.content"></div>
            </div>
          </div>
          <!-- 步骤卡片 -->
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
                    <!-- 步骤完成后显示 footer（确认按钮等） -->
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
</template>
