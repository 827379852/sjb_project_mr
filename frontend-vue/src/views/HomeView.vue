<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
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

// 绑定全局方法供按钮 onclick 调用
onMounted(() => {
  ;(window as any).triggerPersonas = triggerPersonas
  ;(window as any).triggerScout = triggerScout
  ;(window as any).triggerInterview = triggerAutoInterview
  ;(window as any).triggerAutoInterview = triggerAutoInterview
  ;(window as any).triggerReport = triggerReport
  ;(window as any).editStudy = () => {
    inputText.value = researchStore.designContent || ''
    if (inputAreaRef.value) {
      ;(inputAreaRef.value as any).setInputText(inputText.value)
    }
  }
  // 暴露恢复历史消息函数，供侧边栏 selectStudy 后调用
  ;(window as any).restoreMessagesFromStore = restoreMessagesFromStore
  ;(window as any).clearMessages = () => { messages.value = [] }
})

onUnmounted(() => {
  delete (window as any).triggerPersonas
  delete (window as any).triggerScout
  delete (window as any).triggerInterview
  delete (window as any).triggerAutoInterview
  delete (window as any).triggerReport
  delete (window as any).editStudy
  delete (window as any).restoreMessagesFromStore
  delete (window as any).clearMessages
})

// 用于编辑研究方法的变量
const inputText = ref('')

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

// 从 store 恢复历史消息
function restoreMessagesFromStore() {
  console.log('restoreMessagesFromStore called')
  console.log('userRequest:', researchStore.userRequest)
  console.log('designContent:', researchStore.designContent?.substring(0, 100))
  console.log('interviewHistory:', researchStore.interviewHistory)
  console.log('reportContent:', researchStore.reportContent?.substring(0, 100))

  messages.value = []

  // 隐藏欢迎屏幕，显示进度条
  uiStore.hideWelcome()
  uiStore.showProgressBar()

  // 恢复用户请求
  if (researchStore.userRequest) {
    messages.value.push({
      id: `user-init`,
      type: 'user',
      content: researchStore.userRequest
    })
  }

  // 恢复设计内容
  if (researchStore.designContent) {
    const designId = 'design-restored'
    // 根据阶段决定是否显示下一步按钮
    const showDesignFooter = researchStore.phase === 'post-design'
    messages.value.push({
      id: `design-content`,
      type: 'stepCard',
      content: '',
      stepData: {
        id: designId,
        title: '🎯 研究框架设计',
        desc: '已完成',
        status: 'done',
        content: researchStore.designContent,
        footer: showDesignFooter ? `
          <div class="confirm-block">
            <div class="confirm-question">框架已生成 ✓ 接下来要怎么做？</div>
            <div class="confirm-options">
              <button class="confirm-btn primary" onclick="window.triggerPersonas && window.triggerPersonas()">🧠 生成目标人设</button>
              <button class="confirm-btn" onclick="window.editStudy && window.editStudy()">✏️ 调整研究方向</button>
            </div>
          </div>
        ` : ''
      }
    })
    uiStore.expandStep(designId)
  }

  // 恢复人设卡片（如果有）
  if (researchStore.personas.length > 0) {
    const personasId = 'personas-restored'
    const showPersonasFooter = researchStore.phase === 'personas' || researchStore.phase === 'scouting'
    messages.value.push({
      id: personasId,
      type: 'stepCard',
      content: '',
      stepData: {
        id: personasId,
        title: '👥 目标人设',
        desc: `已生成 ${researchStore.personas.length} 个用户画像`,
        status: 'done',
        content: buildPersonasGridHtml(),
        footer: showPersonasFooter ? `
          <div class="confirm-block">
            <div class="confirm-question">人设已生成 ✓ 接下来？</div>
            <div class="confirm-options">
              <button class="confirm-btn primary" onclick="window.triggerScout && window.triggerScout()">🔍 社媒侦察增强</button>
              <button class="confirm-btn" onclick="window.triggerInterview && window.triggerInterview()">💬 开始访谈</button>
            </div>
          </div>
        ` : ''
      }
    })
    uiStore.expandStep(personasId)
  }

  // 恢复访谈记录
  const history = researchStore.interviewHistory
  const hasInterviews = Object.keys(history).length > 0
  Object.entries(history).forEach(([personaId, msgs]) => {
    const persona = researchStore.personas.find(p => p.id === personaId)
    const personaName = persona?.name || '受访者'

    // 添加访谈卡片
    let interviewContent = ''
    msgs.forEach(msg => {
      if (msg.role === 'user') {
        interviewContent += `**问：** ${msg.content}\n\n`
      } else {
        interviewContent += `**${personaName}：** ${msg.content}\n\n`
      }
    })

    messages.value.push({
      id: `interview-${personaId}`,
      type: 'stepCard',
      content: '',
      stepData: {
        id: personaId,
        title: `💬 与 ${personaName} 的访谈`,
        desc: `${msgs.length} 条消息`,
        status: 'done',
        content: interviewContent,
        footer: ''
      }
    })
    uiStore.expandStep(personaId)
  })

  // 恢复报告
  if (researchStore.reportContent) {
    const reportId = 'report-restored'
    messages.value.push({
      id: `report-content`,
      type: 'stepCard',
      content: '',
      stepData: {
        id: reportId,
        title: '📊 研究报告',
        desc: '已完成',
        status: 'done',
        content: researchStore.reportContent,
        footer: ''
      }
    })
    uiStore.expandStep(reportId)
  }

  // 如果没有报告但有访谈，显示生成报告按钮
  if (hasInterviews && !researchStore.reportContent && researchStore.phase === 'interviewing') {
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg?.stepData) {
      lastMsg.stepData.footer = `
        <div class="confirm-block">
          <div class="confirm-question">访谈完成 ✓ 生成研究报告？</div>
          <div class="confirm-options">
            <button class="confirm-btn primary" onclick="window.triggerReport && window.triggerReport()">📊 生成报告</button>
          </div>
        </div>
      `
    }
  }

  console.log('restored messages:', messages.value.length)
}

// 监听 studyId 变化，恢复历史消息
// 注意：只在加载历史记录时恢复，创建新任务时不恢复（因为消息已经在实时显示）
watch(() => researchStore.studyId, (newId, oldId) => {
  // 如果正在流式传输，说明是新创建任务，不需要恢复
  if (researchStore.isStreaming) return
  // 只要有新的 studyId 就恢复（包括页面刷新后的首次加载，oldId 此时为 null）
  if (newId && newId !== oldId) {
    restoreMessagesFromStore()
  }
})

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
    researchStore.setUserRequest(userRequest)
    researchStore.setDesignContent(fullContent)
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

  const cardId = `step-scout-${Date.now()}`
  addStepCard(cardId, '🌐 社交媒体侦察', '为每个人设搜索专属社媒内容...', 'running')
  researchStore.setStreaming(true)
  researchStore.setPhase('scouting')
  researchStore.updateStepProgress('scout', 'active')

  // 获取 stepCard 的 body 元素
  const stepBody = document.getElementById(`${cardId}-body`)
  if (stepBody) {
    stepBody.style.display = 'block'
  }

  // 从研究标题提取关键词
  const title = researchStore.studyTitle.replace('...', '')
  const keywords = title.split(/[，,、\s]+/).filter(k => k.length > 1).slice(0, 3)
  if (keywords.length === 0) keywords.push('用户研究')

  // 侦察进度提示区
  const progressDiv = document.createElement('div')
  progressDiv.id = `scout-progress-${cardId}`
  progressDiv.style.cssText = 'margin-bottom:12px;font-size:12px;color:var(--text-secondary)'

  // 帖子流容器
  const postsContainer = document.createElement('div')
  postsContainer.className = 'post-feed'

  // 人设分块数据
  const personaScoutData: Record<string, { name: string; posts: any[]; insights: string[]; done: boolean }> = {}
  let currentPersonaBlock: HTMLElement | null = null
  let currentPersonaId = ''
  let totalPosts = 0

  function buildPersonaBlock(pId: string, pName: string): HTMLElement {
    const block = document.createElement('div')
    block.className = 'persona-scout-block'
    block.dataset.personaId = pId
    block.innerHTML = `
      <div style="font-size:11px;color:var(--text-dim);margin:8px 0 4px;padding:4px 8px;background:var(--surface3);border-radius:4px">
        👤 ${escapeHtml(pName)} 的社媒声音
      </div>
    `
    return block
  }

  function addPostToBlock(block: HTMLElement, post: any) {
    const div = document.createElement('div')
    div.className = 'post-item'
    const sentimentEmoji = post.sentiment === 'positive' ? '😊' : post.sentiment === 'negative' ? '😤' : '😐'
    div.innerHTML = `
      <div class="post-header">
        <span class="post-platform ${post.platform}">${post.platform}</span>
        <span class="post-sentiment">${sentimentEmoji}</span>
      </div>
      <div class="post-content">${escapeHtml(post.content || '')}</div>
    `
    block.appendChild(div)
  }

  function updateProgress(html: string) {
    progressDiv.innerHTML = html
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      const chatArea = document.querySelector('.chat-area') as HTMLElement
      if (chatArea) {
        chatArea.scrollTop = chatArea.scrollHeight
      }
    })
  }

  // 构建 body 内容
  const bodyEl = document.getElementById(`${cardId}-body`)
  if (bodyEl) {
    bodyEl.innerHTML = ''
    bodyEl.appendChild(progressDiv)
    bodyEl.appendChild(postsContainer)
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
            // 新人设开始侦察
            currentPersonaId = (event as any).persona_id
            const pName = (event as any).persona_name
            const pKeywords = (event as any).keywords || []
            personaScoutData[currentPersonaId] = { name: pName, posts: [], insights: [], done: false }
            updateProgress(`<span style="color:var(--accent)">🔍</span> 正在为 <b>${escapeHtml(pName)}</b> 搜索: ${pKeywords.map((k: string) => `"${escapeHtml(k)}"`).join(', ')}`)
            // 创建该人设的帖子区块
            currentPersonaBlock = buildPersonaBlock(currentPersonaId, pName)
            postsContainer.appendChild(currentPersonaBlock)
            scrollToBottom()
          } else if (event.type === 'post') {
            const post = (event as any).post
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].posts.push(post)
              totalPosts++
              // 找到对应的人设区块并添加帖子
              const block = postsContainer.querySelector(`.persona-scout-block[data-persona-id="${personaId}"]`) as HTMLElement
              if (block && currentPersonaBlock && currentPersonaBlock.dataset.personaId === personaId) {
                addPostToBlock(currentPersonaBlock, post)
              }
              scrollToBottom()
            }
          } else if (event.type === 'persona_insights') {
            const insights = (event as any).insights || []
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].insights.push(...insights)
              // 在对应人设区块内添加洞察
              const block = postsContainer.querySelector(`.persona-scout-block[data-persona-id="${personaId}"]`) as HTMLElement
              if (block && insights.length > 0) {
                const insightDiv = document.createElement('div')
                insightDiv.className = 'insight-item'
                insightDiv.style.cssText = 'margin:6px 0;padding:6px 10px;background:var(--surface2);border-radius:6px;border-left:2px solid var(--accent)'
                insightDiv.innerHTML = `<span style="font-size:12px;color:var(--text-dim)">💡 洞察</span> <span style="font-size:12px">${escapeHtml(insights[0])}</span>`
                block.appendChild(insightDiv)
                scrollToBottom()
              }
            }
          } else if (event.type === 'updated_persona') {
            const p = event.persona as Persona
            researchStore.updatePersona(p)
            // 更新人设卡片 UI（对标 index.html：详情更新 + 增强标记）
            const block = postsContainer.querySelector(`.persona-scout-block[data-persona-id="${p.id}"]`)
            if (block) {
              // 更新 header 区的人设名称（可能人设名被更新）
              const header = block.querySelector('div[style*="surface3"]')
              if (header) {
                header.textContent = `👤 ${escapeHtml(p.name || '用户')} 的社媒声音`
              }
              // 添加或更新增强标记
              if (!block.querySelector('.persona-enriched-badge')) {
                const badge = document.createElement('div')
                badge.className = 'persona-enriched-badge'
                badge.textContent = '✨ 已由社媒数据增强'
                block.appendChild(badge)
                // 短暂绿色边框闪烁提示
                ;(block as HTMLElement).style.borderColor = 'var(--green)'
                setTimeout(() => { ;(block as HTMLElement).style.borderColor = '' }, 1500)
              }
            }
          } else if (event.type === 'persona_scout_done') {
            const pName = (event as any).persona_name
            const pId = (event as any).persona_id
            const count = personaScoutData[pId]?.posts.length || 0
            if (personaScoutData[pId]) {
              personaScoutData[pId].done = true
            }
            updateProgress(`<span style="color:var(--green)">✓</span> ${escapeHtml(pName)} 侦察完成（${count} 条帖子）`)
          } else if (event.type === 'step' && event.step === 'build_persona' && event.status === 'done') {
            updateProgress(`<span style="color:var(--green)">✓</span> 全部 ${Object.keys(personaScoutData).length} 个人设侦察完成，共 ${totalPosts} 条帖子`)
            updateStepCardStatus('done')
            scrollToBottom()
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
        <div class="confirm-question">社媒侦察完成 ✓ 已收集 ${totalPosts} 条内容，每个人设已根据真实用户声音增强</div>
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

async function triggerAutoInterview() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  const cardId = `step-interview-${Date.now()}`
  addStepCard(cardId, '🎤 自动深度访谈', '正在对所有用户人设执行访谈...', 'running')
  researchStore.setStreaming(true)
  researchStore.setPhase('interviewing')
  researchStore.updateStepProgress('interview', 'active')

  // DOM 引用
  const cardBody = document.getElementById(`${cardId}-body`)
  if (!cardBody) return

  let totalPersonas = 0
  let completedPersonas = 0
  const questions: string[] = []
  const personaInterviews: Record<string, { name: string; index: number; qaList: { question: string; answer: string }[]; done: boolean }> = {}

  // 进度区
  const progressDiv = document.createElement('div')
  progressDiv.className = 'auto-interview-progress'
  progressDiv.innerHTML = `
    <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px" id="${cardId}-progress-text">准备中...</div>
    <div style="background:var(--surface3);border-radius:4px;height:4px;overflow:hidden">
      <div id="${cardId}-progress-bar" style="background:var(--accent);height:100%;width:0%;transition:width 0.3s"></div>
    </div>
  `

  // 问题列表区
  const questionsDiv = document.createElement('div')
  questionsDiv.style.cssText = 'margin:10px 0;display:none'
  questionsDiv.id = `${cardId}-questions`

  // 访谈记录容器（所有人设在同一个对话框内）
  const interviewContainer = document.createElement('div')
  interviewContainer.className = 'interview-results'
  interviewContainer.id = `${cardId}-interviews`

  cardBody.innerHTML = ''
  cardBody.appendChild(progressDiv)
  cardBody.appendChild(questionsDiv)
  cardBody.appendChild(interviewContainer)

  function buildPersonaInterviewBlock(personaId: string, name: string, index: number, done: boolean, qaList: { question: string; answer: string }[]): HTMLElement {
    const block = document.createElement('div')
    block.className = 'interview-persona-block'
    block.id = `${cardId}-persona-${personaId}`
    const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']
    const emoji = emojis[index % 5]
    block.innerHTML = `
      <div class="interview-header">
        <div class="interview-persona-avatar">${emoji}</div>
        <div>
          <div class="interview-persona-name">${escapeHtml(name)}</div>
          <div class="interview-persona-meta">${done ? `${qaList.length} 轮问答完成 ✓` : '自动访谈进行中...'}</div>
        </div>
        <div class="interview-emotion">${done ? '✅ 完成' : '🎤 访谈中'}</div>
      </div>
    `
    const msgsDiv = document.createElement('div')
    msgsDiv.className = 'interview-messages'
    msgsDiv.id = `${cardId}-msgs-${personaId}`
    msgsDiv.style.maxHeight = '400px'
    msgsDiv.style.overflowY = 'auto'

    qaList.forEach(qa => {
      const qaDiv = document.createElement('div')
      qaDiv.style.cssText = 'padding:6px 0;border-bottom:1px solid var(--border)'
      qaDiv.innerHTML = `
        <div class="interview-msg-q" style="margin-bottom:4px">${escapeHtml(qa.question)}</div>
        <div class="interview-msg-a">${escapeHtml(qa.answer)}</div>
      `
      msgsDiv.appendChild(qaDiv)
    })
    block.appendChild(msgsDiv)
    return block
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      const chatArea = document.querySelector('.chat-area') as HTMLElement
      if (chatArea) chatArea.scrollTop = chatArea.scrollHeight
    })
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
            const qs = (event as any).questions || []
            questions.push(...qs)
            if (qs.length > 0) {
              questionsDiv.style.display = 'block'
              questionsDiv.innerHTML = `<div style="font-size:11px;color:var(--text-dim);margin-bottom:4px">📋 访谈提纲 (${qs.length} 题)</div>` +
                qs.map((q: string, i: number) => `<div style="font-size:12px;color:var(--text-secondary);padding:2px 0">${i+1}. ${escapeHtml(q)}</div>`).join('')
            }
          } else if (event.type === 'interview_start') {
            totalPersonas = (event as any).total || totalPersonas
            const personaId = (event as any).persona_id
            const name = (event as any).persona_name
            const idx = (event as any).index || 0
            personaInterviews[personaId] = { name, index: idx, qaList: [], done: false }

            // 更新进度
            const cur = (event as any).index || 0
            const progText = document.getElementById(`${cardId}-progress-text`)
            const progBar = document.getElementById(`${cardId}-progress-bar`)
            if (progText) progText.textContent = `正在访谈 ${name}（${cur + 1}/${totalPersonas}）...`
            if (progBar) progBar.style.width = `${totalPersonas > 0 ? (cur / totalPersonas * 100) : 0}%`

            // 创建该人设的访谈块（带完整对话界面）
            const block = buildPersonaInterviewBlock(personaId, name, idx, false, [])
            interviewContainer.appendChild(block)
            scrollToBottom()
          } else if (event.type === 'qa') {
            const personaId = (event as any).persona_id
            const question = (event as any).question
            const answer = (event as any).answer
            if (personaInterviews[personaId]) {
              personaInterviews[personaId].qaList.push({ question, answer })
            }
            researchStore.addInterviewMessage(personaId, { role: 'user', content: question })
            researchStore.addInterviewMessage(personaId, { role: 'assistant', content: answer })

            // 向该人设的对话框追加消息
            const msgsDiv = document.getElementById(`${cardId}-msgs-${personaId}`)
            if (msgsDiv) {
              const qaDiv = document.createElement('div')
              qaDiv.style.cssText = 'padding:6px 0;border-bottom:1px solid var(--border)'
              qaDiv.innerHTML = `
                <div class="interview-msg-q" style="margin-bottom:4px">${escapeHtml(question)}</div>
                <div class="interview-msg-a">${escapeHtml(answer)}</div>
              `
              msgsDiv.appendChild(qaDiv)
              msgsDiv.scrollTop = msgsDiv.scrollHeight
            }
            scrollToBottom()
          } else if (event.type === 'interview_done') {
            const personaId = (event as any).persona_id
            if (personaInterviews[personaId]) personaInterviews[personaId].done = true
            completedPersonas++

            // 更新该人设块的元数据
            const block = document.getElementById(`${cardId}-persona-${personaId}`)
            if (block) {
              const meta = block.querySelector('.interview-persona-meta')
              const emotion = block.querySelector('.interview-emotion')
              const qaCount = personaInterviews[personaId]?.qaList.length || 0
              if (meta) meta.textContent = `${qaCount} 轮问答完成 ✓`
              if (emotion) emotion.textContent = '✅ 完成'
            }

            // 更新进度
            const progText = document.getElementById(`${cardId}-progress-text`)
            const progBar = document.getElementById(`${cardId}-progress-bar`)
            if (progText) progText.textContent = completedPersonas >= totalPersonas
              ? `全部 ${totalPersonas} 位用户访谈完成 ✓`
              : `正在访谈... (${completedPersonas}/${totalPersonas})`
            if (progBar) progBar.style.width = `${(completedPersonas / totalPersonas * 100).toFixed(0)}%`
            scrollToBottom()
          } else if (event.type === 'step' && event.step === 'auto_interview' && event.status === 'done') {
            updateStepCardStatus('done')
          }
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
        <div class="confirm-question">自动访谈完成 ✓ 共对 ${completedPersonas} 位用户进行了深度访谈</div>
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

        <template v-for="msg in messages">
          <div v-if="msg.type === 'user'" :key="msg.id" class="msg-user fade-in">
            <div class="bubble">{{ msg.content }}</div>
          </div>
          <div v-else-if="msg.type === 'agent'" :key="msg.id" class="msg-agent fade-in">
            <div class="agent-avatar">✦</div>
            <div class="agent-content">
              <div class="agent-name">ResearchMind</div>
              <div class="agent-body" v-html="msg.html || msg.content"></div>
            </div>
          </div>
          <div v-else-if="msg.type === 'stepCard' && msg.stepData" :key="msg.id" class="msg-agent fade-in">
            <div class="agent-avatar">✦</div>
            <div class="agent-content">
              <div class="agent-name">ResearchMind</div>
              <div class="agent-body">
                <div class="step-card fade-in">
                  <div class="step-header" @click="uiStore.toggleStep(msg.stepData && msg.stepData.id)">
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
                  <div :class="['step-body', { visible: msg.stepData && uiStore.expandedSteps.includes(msg.stepData.id) }]">
                    <div v-if="msg.stepData && msg.stepData.content" class="streaming-text">
                      <div class="markdown" v-html="simpleMarkdown(msg.stepData.content)"></div>
                      <span v-if="msg.stepData && msg.stepData.status === 'running'" class="cursor"></span>
                    </div>
                    <div v-if="msg.stepData && msg.stepData.footer && msg.stepData.status === 'done'" class="step-footer" v-html="msg.stepData.footer"></div>
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
