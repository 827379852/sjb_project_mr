<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import TheTopbar from '@/components/layout/TheTopbar.vue'
import TheProgressBar from '@/components/layout/TheProgressBar.vue'
import InputArea from '@/components/layout/InputArea.vue'
import { useResearchStore, useUIStore, useAuthStore } from '@/stores'
import { useMarkdown } from '@/composables'
import type { SSEEvent, Persona } from '@/types'

// 扩展 HTMLElement 以支持自定义属性
declare module 'vue' {
  interface HTMLElement {
    _scoutToggleBound?: boolean
    _postToggleBound?: boolean
  }
}

const router = useRouter()
const researchStore = useResearchStore()
const uiStore = useUIStore()
const authStore = useAuthStore()
const { simpleMarkdown } = useMarkdown()

// ── 社媒侦查折叠事件委托 ──────────────────────────────────────
function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// 用 WeakMap 存储是否已绑定折叠事件（避免重复绑定）
const _scoutBound = new WeakMap<Element, boolean>()
const _postBound = new WeakMap<Element, boolean>()

function applyScoutToggle(el: Element) {
  // 人设头部折叠/展开
  el.querySelectorAll('.persona-scout-header').forEach(header => {
    if (_scoutBound.get(header)) return
    _scoutBound.set(header, true)
    const body = header.nextElementSibling
    const icon = header.querySelector('.toggle-icon')
    const hint = header.querySelector('.expand-hint')
    header.addEventListener('click', () => {
      const isOpen = (body as HTMLElement)?.style.display !== 'none'
      ;(body as HTMLElement).style.display = isOpen ? 'none' : 'block'
      if (icon) (icon as HTMLElement).style.transform = isOpen ? '' : 'rotate(90deg)'
      if (hint) (hint as HTMLElement).textContent = isOpen ? '点击展开详情' : '点击收起'
    })
  })
  // 帖子折叠/展开
  el.querySelectorAll('.post-toggle').forEach(toggle => {
    if (_postBound.get(toggle)) return
    _postBound.set(toggle, true)
    const toggleBody = toggle.querySelector('.post-toggle-body')
    const toggleIcon = toggle.querySelector('.post-toggle-icon')
    toggle.addEventListener('click', () => {
      const isOpen = (toggleBody as HTMLElement)?.style.display !== 'none'
      ;(toggleBody as HTMLElement).style.display = isOpen ? 'none' : 'block'
      if (toggleIcon) (toggleIcon as HTMLElement).style.transform = isOpen ? '' : 'rotate(90deg)'
    })
  })
}

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
    // 只有 post-design 阶段显示下一步按钮（用户可以在此调整）
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
              <button class="confirm-btn primary" onclick="window.triggerPersonas && window.triggerPersonas()">🧠 开始市场调研</button>
              <button class="confirm-btn" onclick="window.editStudy && window.editStudy()">✏️ 调整研究方向</button>
            </div>
          </div>
        ` : ''
      }
    })
    uiStore.expandStep(designId)
  }

  // 恢复人设卡片（如果有）- 不显示后续引导按钮
  if (researchStore.personas.length > 0) {
    const personasId = 'personas-restored'
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
        footer: '' // 不显示后续引导
      }
    })
    uiStore.expandStep(personasId)
  }

  // 恢复社媒侦察结果（如果有）
  if (researchStore.scoutResults.length > 0) {
    const scoutId = 'scout-restored'
    let scoutContent = '<div class="post-feed">'

    researchStore.scoutResults.forEach(result => {
      const pName = escapeHtml(result.personaName)
      const postCount = result.posts.length
      const insightCount = result.insights.length
      scoutContent += `
        <div class="persona-scout-block" data-persona-id="${result.personaId || ''}">
          <div class="persona-scout-header restore-header" style="display:flex;align-items:center;gap:8px;margin:8px 0 4px;padding:6px 8px;background:var(--surface3);border-radius:6px;cursor:pointer;user-select:none">
            <span class="toggle-icon" style="font-size:12px;color:var(--text-dim);transition:transform 0.2s;display:inline-block">▶</span>
            <span style="font-size:12px;color:var(--text-dim)">👤</span>
            <span style="font-size:12px;color:var(--text)">${pName}</span>
            <span style="font-size:11px;color:var(--text-dim)">${postCount} 篇帖子</span>
            ${insightCount > 0 ? `<span style="font-size:10px;color:var(--accent);background:var(--surface2);padding:1px 5px;border-radius:3px">💡 ${insightCount}</span>` : ''}
            <span class="expand-hint" style="margin-left:auto;font-size:10px;color:var(--text-dim)">点击展开详情</span>
          </div>
          <div class="persona-scout-body" style="display:none;padding-left:8px">
      `
      result.posts.forEach(post => {
        const sentimentEmoji = post.sentiment === 'positive' ? '😊' : post.sentiment === 'negative' ? '😤' : '😐'
        const platformColor = post.platform === '小红书' ? 'color:#FF2442' : post.platform === '微博' ? 'color:#FF9744' : 'color:#00BFFF'
        const comments = post.comments || []
        const isReal = post.is_real === true || post.is_real === 'true'
        if (isReal && post.title) {
          scoutContent += `
            <div class="post-item">
              <div class="post-toggle" data-post-id="${result.personaId}-${Date.now()}" style="margin:4px 0;padding:8px;background:var(--surface2);border-radius:8px;border:1px solid var(--border);cursor:pointer;user-select:none">
                <div style="display:flex;align-items:center;gap:8px">
                  <span class="post-toggle-icon" style="font-size:10px;color:var(--text-dim);transition:transform 0.2s;display:inline-block">▶</span>
                  <span style="font-size:11px;${platformColor}">📕 ${post.platform || '小红书'}</span>
                  <span style="font-size:12px;color:var(--text);font-weight:500;flex:1">${escapeHtml(post.title)}</span>
                  <span style="font-size:10px;color:var(--green);background:var(--surface3);padding:2px 6px;border-radius:3px">真实</span>
                  ${comments.length > 0 ? `<span style="font-size:10px;color:var(--text-dim)">💬 ${comments.length}</span>` : ''}
                </div>
                <div class="post-toggle-body" style="display:none;margin-top:8px;padding-top:8px;border-top:1px dashed var(--border)">
                  ${post.author ? `<div style="font-size:11px;color:var(--text-dim);margin-bottom:6px">👤 ${escapeHtml(post.author)}</div>` : ''}
                  ${post.content ? `<div style="font-size:12px;line-height:1.6;color:var(--text-secondary)">${escapeHtml(post.content || '')}</div>` : ''}
                  ${post.link ? `<a href="${escapeHtml(post.link)}" target="_blank" style="font-size:11px;color:var(--accent);text-decoration:none;display:inline-block;margin-top:6px">🔗 查看原文</a>` : ''}
                  ${comments.length > 0 ? `
                    <div style="margin-top:8px;padding-top:8px;border-top:1px dashed var(--border)">
                      <div style="font-size:11px;color:var(--text-dim);margin-bottom:6px">💬 评论（${comments.length} 条）</div>
                      ${comments.slice(0, 5).map((c: any) => `
                        <div style="font-size:12px;padding:4px 0;border-bottom:1px solid var(--border);color:var(--text-secondary)">
                          <span style="color:var(--text)">${escapeHtml(c.user || '用户')}:</span> ${escapeHtml(c.text || '').substring(0, 120)}
                        </div>
                      `).join('')}
                      ${comments.length > 5 ? `<div style="font-size:11px;color:var(--text-dim);padding-top:4px">还有 ${comments.length - 5} 条评论...</div>` : ''}
                    </div>
                  ` : ''}
                </div>
              </div>
            </div>
          `
        } else {
          scoutContent += `
            <div class="post-item" style="margin:4px 0;padding:8px;background:var(--surface2);border-radius:8px">
              <div style="font-size:11px;${platformColor}">${post.platform || '小红书'} ${sentimentEmoji}</div>
              <div style="font-size:12px;line-height:1.5;margin-top:4px;color:var(--text-secondary)">${escapeHtml(post.content || '')}</div>
            </div>
          `
        }
      })
      if (result.insights.length > 0) {
        result.insights.forEach(insight => {
          scoutContent += `
            <div style="margin:6px 0;padding:6px 10px;background:var(--surface2);border-radius:6px;border-left:2px solid var(--accent)">
              <span style="font-size:12px;color:var(--text-dim)">💡 洞察</span> <span style="font-size:12px">${escapeHtml(insight)}</span>
            </div>
          `
        })
      }
      scoutContent += '</div></div>'
    })
    scoutContent += '</div>'

    messages.value.push({
      id: scoutId,
      type: 'stepCard',
      content: '',
      stepData: {
        id: scoutId,
        title: '🌐 社交媒体侦察',
        desc: `已搜索 ${researchStore.scoutResults.length} 个人设的社媒内容`,
        status: 'done',
        content: scoutContent,
        footer: ''
      }
    })
    uiStore.expandStep(scoutId)
  }

  // 恢复访谈记录 - 使用与新建任务相同的格式
  const history = researchStore.interviewHistory
  const personaEntries = Object.entries(history)

  if (personaEntries.length > 0) {
    const interviewId = 'interview-restored'
    const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']

    let interviewContent = '<div class="interview-results">'

    personaEntries.forEach(([personaId, msgs], index) => {
      const persona = researchStore.personas.find(p => p.id === personaId)
      const personaName = persona?.name || '受访者'
      const emoji = emojis[index % 5]

      // 构建 QA 列表
      const qaList: { question: string; answer: string }[] = []
      for (let i = 0; i < msgs.length - 1; i += 2) {
        if (msgs[i].role === 'user' && msgs[i + 1]?.role === 'assistant') {
          qaList.push({
            question: msgs[i].content,
            answer: msgs[i + 1].content
          })
        }
      }

      interviewContent += `
        <div class="interview-persona-block">
          <div class="interview-header">
            <div class="interview-persona-avatar">${emoji}</div>
            <div>
              <div class="interview-persona-name">${escapeHtml(personaName)}</div>
              <div class="interview-persona-meta">${qaList.length} 轮问答完成 ✓</div>
            </div>
            <div class="interview-emotion">✅ 完成</div>
          </div>
          <div class="interview-messages" style="max-height:400px;overflow-y:auto">
            ${qaList.map(qa => `
              <div style="padding:6px 0;border-bottom:1px solid var(--border)">
                <div class="interview-msg-q" style="margin-bottom:4px">${escapeHtml(qa.question)}</div>
                <div class="interview-msg-a">${escapeHtml(qa.answer)}</div>
              </div>
            `).join('')}
          </div>
        </div>
      `
    })

    interviewContent += '</div>'

    // 计算总消息数
    let totalMsgs = 0
    personaEntries.forEach(([, msgs]) => {
      totalMsgs += msgs.length
    })

    messages.value.push({
      id: interviewId,
      type: 'stepCard',
      content: '',
      stepData: {
        id: interviewId,
        title: '🎤 自动深度访谈',
        desc: `已完成 ${personaEntries.length} 位用户的访谈`,
        status: 'done',
        content: interviewContent,
        footer: ''
      }
    })
    uiStore.expandStep(interviewId)
  }

  // 恢复报告 - 显示导出按钮
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
        footer: `
          <div class="confirm-block">
            <div class="confirm-question">✅ 研究报告已生成完毕</div>
            <div class="confirm-options">
              <button class="confirm-btn primary" onclick="window.exportReport && window.exportReport()">📥 导出 Markdown</button>
            </div>
          </div>
        `
      }
    })
    uiStore.expandStep(reportId)
  }

  console.log('restored messages:', messages.value.length)

  // 为侦察结果注入事件绑定（历史恢复 + 实时 SSE 均通过这里生效）
  nextTick(() => {
    applyScoutToggle(document.body)
  })
}

// 标记是否正在创建新任务（用于防止 watch 清空正在显示的消息）
const isCreatingNewStudy = ref(false)

// 监听 studyId 变化，恢复历史消息
// 注意：只在加载历史记录时恢复，创建新任务时不恢复（因为消息已经在实时显示）
watch(() => researchStore.studyId, (newId, oldId) => {
  // 如果正在创建新任务，跳过恢复
  if (isCreatingNewStudy.value) {
    isCreatingNewStudy.value = false
    return
  }
  // 加载历史记录时恢复（oldId 存在说明是从一个研究切换到另一个）
  // 或者 oldId 为 null 但 isStreaming 为 false（页面刷新后首次加载）
  if (newId && newId !== oldId && !researchStore.isStreaming) {
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
      if (res.status === 402) {
        // 积分不足
        const errorData = await res.json()
        updateStepCardStatus('error')
        updateStepCardContent(`❌ ${errorData.detail || '积分不足，无法开始研究'}`)
        researchStore.setStreaming(false)
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
          <button class="confirm-btn primary" onclick="window.triggerPersonas && window.triggerPersonas()">🧠 开始市场调研</button>
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

function buildPersonaDetailHtml(p: Persona): string {
  let html = ''
  if (p.background) html += `<div class="persona-detail-section"><div class="persona-detail-label">📋 背景</div><div class="persona-detail-value">${escapeHtml(p.background)}</div></div>`
  if (p.personality) html += `<div class="persona-detail-section"><div class="persona-detail-label">🧠 性格特征</div><div class="persona-detail-value">${escapeHtml(p.personality)}</div></div>`
  if (p.consumer_habits) html += `<div class="persona-detail-section"><div class="persona-detail-label">🛒 消费习惯</div><div class="persona-detail-value">${escapeHtml(p.consumer_habits)}</div></div>`
  if (p.pain_points) html += `<div class="persona-detail-section"><div class="persona-detail-label">😤 痛点</div><div class="persona-detail-value">${Array.isArray(p.pain_points) ? p.pain_points.map(v => escapeHtml(v)).join('、') : escapeHtml(p.pain_points)}</div></div>`
  if (p.motivations) html += `<div class="persona-detail-section"><div class="persona-detail-label">🎯 动机</div><div class="persona-detail-value">${escapeHtml(p.motivations)}</div></div>`
  if (p.digital_behavior) html += `<div class="persona-detail-section"><div class="persona-detail-label">📱 数字行为</div><div class="persona-detail-value">${escapeHtml(p.digital_behavior)}</div></div>`
  if (p.social_media) html += `<div class="persona-detail-section"><div class="persona-detail-label">💬 社媒偏好</div><div class="persona-detail-value">${escapeHtml(p.social_media)}</div></div>`
  if (p.core_values && p.core_values.length > 0) html += `<div class="persona-detail-section"><div class="persona-detail-label">💎 核心价值观</div><div class="persona-detail-value">${p.core_values.map(v => escapeHtml(v)).join('、')}</div></div>`
  if (p.attitude) html += `<div class="persona-detail-section"><div class="persona-detail-label">💭 态度</div><div class="persona-detail-value">${typeof p.attitude === 'object' ? escapeHtml(JSON.stringify(p.attitude)) : escapeHtml(p.attitude)}</div></div>`
  if (p.attitude_hypotheses) html += `<div class="persona-detail-section"><div class="persona-detail-label">🧪 态度假设</div><div class="persona-detail-value">${escapeHtml(JSON.stringify(p.attitude_hypotheses))}</div></div>`
  if (p.description) html += `<div class="persona-detail-section"><div class="persona-detail-label">📝 完整描述</div><div class="persona-detail-value">${escapeHtml(p.description)}</div></div>`
  if (p.scouted_updates) html += `<div class="persona-detail-section" style="margin-top:10px;padding-top:8px;border-top:1px dashed var(--border)"><div class="persona-detail-label" style="color:var(--green)">🔄 社媒侦察更新</div><div class="persona-detail-value" style="color:var(--green)">${typeof p.scouted_updates === 'object' ? escapeHtml(JSON.stringify(p.scouted_updates, null, 2)) : escapeHtml(p.scouted_updates)}</div></div>`
  return html
}

function updatePersonaCardDetail(p: Persona) {
  const card = document.querySelector(`.persona-card[data-persona-id="${p.id}"]`)
  if (!card) return
  const detailPanel = card.querySelector('.persona-detail-panel')
  if (detailPanel) {
    detailPanel.innerHTML = buildPersonaDetailHtml(p)
  }
  const metaEl = card.querySelector('.persona-card-meta') as HTMLElement
  if (metaEl && (p.age || p.occupation)) {
    metaEl.textContent = `${p.age || ''}岁 · ${escapeHtml(p.occupation || '')}`
  }
  const tagsDiv = card.querySelector('.persona-card-meta + div')
  if (tagsDiv && p.core_values) {
    tagsDiv.innerHTML = p.core_values.slice(0, 3).map((v: string) => `<span class="persona-card-tag">${escapeHtml(v)}</span>`).join('')
  }
  if (!card.querySelector('.persona-enriched-badge')) {
    const badge = document.createElement('div')
    badge.className = 'persona-enriched-badge'
    badge.textContent = '✨ 已由社媒数据增强'
    card.appendChild(badge)
    ;(card as HTMLElement).style.borderColor = 'var(--green)'
    setTimeout(() => { ;(card as HTMLElement).style.borderColor = '' }, 1500)
  }
}

function buildPersonasGridHtml(): string {
  const emojis = ['👩', '👨', '🧑', '👩‍💼', '👨‍💻']
  let html = '<div class="personas-grid">'
  researchStore.personas.forEach((persona, index) => {
    html += `
      <div class="persona-card" data-persona-id="${persona.id}" onclick="this.classList.toggle('expanded')">
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
        <div class="persona-detail-panel">${buildPersonaDetailHtml(persona)}</div>
      </div>
    `
  })
  html += '</div>'
  return html
}

async function triggerPersonas() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  addStepCard(`step-personas-${Date.now()}`, '👥 开始市场调研', '正在构建初始用户画像...', 'running')
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
      if (res.status === 402) {
        // 积分不足
        const errorData = await res.json()
        updateStepCardStatus('error')
        updateStepCardContent(`❌ ${errorData.detail || '积分不足，无法开始市场调研'}`)
        researchStore.setStreaming(false)
        return
      }
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
          } else if (event.type === 'credits_deducted') {
            // 积分扣除，更新前端显示
            authStore.updateCredits((event as any).remaining)
            console.log('积分已扣除:', event.amount, '剩余:', (event as any).remaining)
          } else if (event.type === 'credits_refund') {
            // 积分返还
            authStore.addCredits(event.amount as number)
            console.log('积分已返还:', event.amount)
          } else if (event.type === 'error') {
            updateStepCardStatus('error')
            updateStepCardContent(`❌ ${(event as any).message || '发生错误'}`)
          }
        } catch {
          buffer = eventStr
        }
      }
    }

    researchStore.updateStepProgress('personas', 'done')
    researchStore.updateStepProgress('scout', 'active')

    // 自动进入下一阶段：社媒侦察
    updateStepCardFooter('')
    await nextTick()
    scrollToBottom()
    researchStore.setStreaming(false)
    // 自动触发社媒侦察
    await triggerScout()
    return
  } catch (e) {
    console.error('triggerPersonas error:', e)
    updateStepCardStatus('error')
  }

  researchStore.setStreaming(false)
}

async function triggerScout() {
  if (!researchStore.studyId || researchStore.isStreaming) return

  const cardId = `step-scout-${Date.now()}`
  addStepCard(cardId, '🌐 社交媒体侦察', '为每个人设搜索专属社媒内容...', 'running')
  researchStore.setStreaming(true)
  researchStore.setPhase('scouting')
  researchStore.updateStepProgress('scout', 'active')

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
  let scoutDoneFlag = false  // 标记 SSE 是否已发送完成事件

  function buildPersonaBlock(pId: string, pName: string): HTMLElement {
    const block = document.createElement('div')
    block.className = 'persona-scout-block'
    block.dataset.personaId = pId
    block.innerHTML = `
      <div class="persona-scout-header" data-persona-id="${pId}" style="display:flex;align-items:center;gap:8px;margin:8px 0 4px;padding:6px 8px;background:var(--surface3);border-radius:6px;cursor:pointer;user-select:none">
        <span class="toggle-icon" style="font-size:12px;color:var(--text-dim);transition:transform 0.2s;display:inline-block">▶</span>
        <span style="font-size:12px;color:var(--text-dim)">👤</span>
        <span style="font-size:12px;color:var(--text)">${escapeHtml(pName)}</span>
        <span class="post-count" style="font-size:11px;color:var(--text-dim)">加载中...</span>
        <span class="expand-hint" style="margin-left:auto;font-size:10px;color:var(--text-dim)">点击展开详情</span>
      </div>
      <div class="persona-scout-body" data-persona-id="${pId}" style="display:none;padding-left:8px"></div>
    `
    // 点击头部折叠/展开
    const header = block.querySelector('.persona-scout-header') as HTMLElement
    const body = block.querySelector('.persona-scout-body') as HTMLElement
    const icon = block.querySelector('.toggle-icon') as HTMLElement
    const hint = block.querySelector('.expand-hint') as HTMLElement
    header.addEventListener('click', () => {
      const isOpen = body.style.display !== 'none'
      body.style.display = isOpen ? 'none' : 'block'
      icon.style.transform = isOpen ? '' : 'rotate(90deg)'
      if (hint) hint.textContent = isOpen ? '点击展开详情' : '点击收起'
    })
    return block
  }

  function getPersonaBody(pId: string): HTMLElement | null {
    return postsContainer.querySelector(`.persona-scout-body[data-persona-id="${pId}"]`) as HTMLElement | null
  }

  function addPostToBlock(block: HTMLElement, post: any) {
    const pId = block.dataset.personaId || ''
    const body = getPersonaBody(pId)
    if (!body) return

    const div = document.createElement('div')
    div.className = 'post-item'
    const isReal = post.is_real === true || post.is_real === 'true'
    const platformColor = post.platform === '小红书' ? 'color:#FF2442' : post.platform === '微博' ? 'color:#FF9744' : 'color:#00BFFF'
    const comments = post.comments || []

    if (isReal && post.title) {
      // 真实帖子：默认折叠，点击展开
      div.innerHTML = `
        <div class="post-toggle" data-post-id="${pId}-${Date.now()}" style="margin:4px 0;padding:8px;background:var(--surface2);border-radius:8px;border:1px solid var(--border);cursor:pointer;user-select:none">
          <div class="post-toggle-header" style="display:flex;align-items:center;gap:8px">
            <span class="post-toggle-icon" style="font-size:10px;color:var(--text-dim);transition:transform 0.2s;display:inline-block">▶</span>
            <span style="font-size:11px;${platformColor}">📕 ${post.platform || '小红书'}</span>
            <span style="font-size:12px;color:var(--text);font-weight:500;flex:1">${escapeHtml(post.title)}</span>
            <span style="font-size:10px;color:var(--green);background:var(--surface3);padding:2px 6px;border-radius:3px">真实</span>
            ${comments.length > 0 ? `<span style="font-size:10px;color:var(--text-dim)">💬 ${comments.length}</span>` : ''}
          </div>
          <div class="post-toggle-body" style="display:none;margin-top:8px;padding-top:8px;border-top:1px dashed var(--border)">
            ${post.author ? `<div style="font-size:11px;color:var(--text-dim);margin-bottom:6px">👤 ${escapeHtml(post.author)}</div>` : ''}
            ${post.content ? `<div style="font-size:12px;line-height:1.6;color:var(--text-secondary)">${escapeHtml(post.content || '')}</div>` : ''}
            ${post.link ? `<a href="${escapeHtml(post.link)}" target="_blank" style="font-size:11px;color:var(--accent);text-decoration:none;display:inline-block;margin-top:6px">🔗 查看原文</a>` : ''}
            ${comments.length > 0 ? `
              <div style="margin-top:8px;padding-top:8px;border-top:1px dashed var(--border)">
                <div style="font-size:11px;color:var(--text-dim);margin-bottom:6px">💬 评论（${comments.length} 条）</div>
                ${comments.slice(0, 5).map((c: any) => `
                  <div style="font-size:12px;padding:4px 0;border-bottom:1px solid var(--border);color:var(--text-secondary)">
                    <span style="color:var(--text)">${escapeHtml(c.user || '用户')}:</span> ${escapeHtml(c.text || '').substring(0, 120)}
                  </div>
                `).join('')}
                ${comments.length > 5 ? `<div style="font-size:11px;color:var(--text-dim);padding-top:4px">还有 ${comments.length - 5} 条评论...</div>` : ''}
              </div>
            ` : ''}
          </div>
        </div>
      `
      // 帖子展开/折叠
      const toggle = div.querySelector('.post-toggle') as HTMLElement
      const toggleBody = div.querySelector('.post-toggle-body') as HTMLElement
      const toggleIcon = div.querySelector('.post-toggle-icon') as HTMLElement
      toggle.addEventListener('click', () => {
        const isOpen = toggleBody.style.display !== 'none'
        toggleBody.style.display = isOpen ? 'none' : 'block'
        toggleIcon.style.transform = isOpen ? '' : 'rotate(90deg)'
      })
    } else {
      // 模拟帖子（不折叠，展示完整）
      const sentimentEmoji = post.sentiment === 'positive' ? '😊' : post.sentiment === 'negative' ? '😤' : '😐'
      div.innerHTML = `
        <div style="font-size:11px;${platformColor}">${post.platform || '小红书'}</span> <span style="font-size:12px">${sentimentEmoji}</span></div>
        <div style="font-size:12px;line-height:1.5;margin-top:4px;color:var(--text-secondary)">${escapeHtml(post.content || '')}</div>
      `
    }
    body.appendChild(div)
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

  // 等待 Vue 渲染完成后，再操作 DOM
  await nextTick()
  console.log('[Scout] cardId:', cardId, 'keywords:', keywords)
  const bodyEl = document.getElementById(`${cardId}-body`)
  console.log('[Scout] stepCard body element:', bodyEl)
  if (!bodyEl) {
    console.error('[Scout] ERROR: stepCard body not found, aborting')
    researchStore.setStreaming(false)
    return
  }
  bodyEl.innerHTML = ''
  bodyEl.appendChild(progressDiv)
  bodyEl.appendChild(postsContainer)
  console.log('[Scout] body initialized with progress and posts container')

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
          console.log('[Scout] SSE event type:', event.type, event)
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
          } else if (event.type === 'scout_progress') {
            // 侦察进度消息
            const msg = (event as any).message || ''
            const pId = (event as any).persona_id || currentPersonaId
            updateProgress(`<span style="color:var(--accent)">${msg}</span>`)
          } else if (event.type === 'post') {
            const post = (event as any).post
            const personaId = (event as any).persona_id
            console.log('[Scout] post event, personaId:', personaId, 'currentBlock:', currentPersonaBlock?.dataset?.personaId, 'post:', post?.content?.substring(0, 80))
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].posts.push(post)
              totalPosts++
              // 更新帖子计数
              const header = postsContainer.querySelector(`.persona-scout-header[data-persona-id="${personaId}"]`)
              const countSpan = header?.querySelector('.post-count')
              if (countSpan) countSpan.textContent = `${personaScoutData[personaId].posts.length} 篇帖子`
              // 通过 personaId 查找对应区块，帖子放入折叠 body
              const block = postsContainer.querySelector(`.persona-scout-block[data-persona-id="${personaId}"]`) as HTMLElement
              if (block) {
                addPostToBlock(block, post)
              }
            }
          } else if (event.type === 'persona_insights') {
            const insights = (event as any).insights || []
            const personaId = (event as any).persona_id
            if (personaScoutData[personaId]) {
              personaScoutData[personaId].insights.push(...insights)
              const body = getPersonaBody(personaId)
              if (body && insights.length > 0) {
                insights.forEach(insight => {
                  const insightDiv = document.createElement('div')
                  insightDiv.className = 'insight-item'
                  insightDiv.style.cssText = 'margin:6px 0;padding:6px 10px;background:var(--surface2);border-radius:6px;border-left:2px solid var(--accent)'
                  insightDiv.innerHTML = `<span style="font-size:12px;color:var(--text-dim)">💡 洞察</span> <span style="font-size:12px">${escapeHtml(insight)}</span>`
                  body.appendChild(insightDiv)
                })
              }
            }
          } else if (event.type === 'updated_persona') {
            const p = event.persona as Persona
            console.log('[Scout] updated_persona:', p)
            researchStore.updatePersona(p)
            // 更新人设卡片 UI（详情面板内容 + 增强标记）
            updatePersonaCardDetail(p)
            // 更新社媒区块头部的人设名称
            const block = postsContainer.querySelector(`.persona-scout-block[data-persona-id="${p.id}"]`)
            if (block) {
              const nameSpan = block.querySelector('.persona-scout-header span:nth-child(3)')
              if (nameSpan) nameSpan.textContent = escapeHtml(p.name || '用户')
            }
          } else if (event.type === 'persona_scout_done') {
            const pName = (event as any).persona_name
            const pId = (event as any).persona_id
            const postsCount = (event as any).posts_count || 0
            if (personaScoutData[pId]) {
              personaScoutData[pId].done = true
            }
            // 完成时更新帖子计数
            const header = postsContainer.querySelector(`.persona-scout-header[data-persona-id="${pId}"]`)
            const countSpan = header?.querySelector('.post-count')
            const data = personaScoutData[pId]
            if (countSpan) countSpan.textContent = data ? `${data.posts.length} 篇帖子` : `${postsCount} 篇帖子`
            updateProgress(`<span style="color:var(--green)">✓</span> ${escapeHtml(pName)} 侦察完成${postsCount > 0 ? `（${postsCount} 篇小红书帖子）` : ''}`)
          } else if (event.type === 'step' && event.step === 'build_persona' && event.status === 'done') {
            // 记录完成状态，暂不更新 DOM（等 SSE 结束后统一处理）
            // 通过 flag 标记，等 SSE 结束后设置 stepCard 状态
            scoutDoneFlag = true
          }
        } catch (e) {
          console.warn('[Scout] SSE parse error, keeping buffer. raw:', eventStr?.substring(0, 200), e)
          buffer = eventStr
        }
      }
    }

    // 只有当 SSE 发送了完成事件时才更新状态
    if (scoutDoneFlag) {
      updateStepCardStatus('done')
    }

    // 存储社媒侦察结果到 store
    Object.entries(personaScoutData).forEach(([personaId, data]) => {
      if (data.posts.length > 0 || data.insights.length > 0) {
        researchStore.addScoutResult({
          personaId,
          personaName: data.name,
          posts: data.posts,
          insights: data.insights
        })
      }
    })

    researchStore.updateStepProgress('scout', 'done')
    researchStore.updateStepProgress('interview', 'active')

    // 自动进入下一阶段：自动深度访谈
    await nextTick()
    scrollToBottom()
    applyScoutToggle(document.body)
    researchStore.setStreaming(false)
    // 自动触发访谈
    await triggerAutoInterview()
    return
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

  let totalPersonas = 0
  let completedPersonas = 0
  const questions: string[] = []
  const personaInterviews: Record<string, { name: string; index: number; qaList: { question: string; answer: string }[]; done: boolean }> = {}
  let interviewDoneFlag = false  // 标记 SSE 是否已发送完成事件

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

  // 等待 Vue 渲染完成
  await nextTick()
  console.log('[Interview] cardId:', cardId)
  const cardBody = document.getElementById(`${cardId}-body`)
  console.log('[Interview] stepCard body element:', cardBody)
  if (!cardBody) {
    console.error('[Interview] ERROR: stepCard body not found, aborting')
    researchStore.setStreaming(false)
    return
  }
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

            // 更新进度条（已完成数/总数）
            const progText = document.getElementById(`${cardId}-progress-text`)
            const progBar = document.getElementById(`${cardId}-progress-bar`)
            if (progText) progText.textContent = `正在并行访谈... (${completedPersonas}/${totalPersonas} 已完成)`
            if (progBar) progBar.style.width = `${totalPersonas > 0 ? (completedPersonas / totalPersonas * 100) : 0}%`

            // 并行模式下直接通过 personaId 查找/创建访谈块
            let block = document.getElementById(`${cardId}-persona-${personaId}`) as HTMLElement
            if (!block) {
              block = buildPersonaInterviewBlock(personaId, name, idx, false, [])
              interviewContainer.appendChild(block)
            }
          } else if (event.type === 'qa') {
            const personaId = (event as any).persona_id
            const question = (event as any).question
            const answer = (event as any).answer
            if (personaInterviews[personaId]) {
              personaInterviews[personaId].qaList.push({ question, answer })
            }
            researchStore.addInterviewMessage(personaId, { role: 'user', content: question })
            researchStore.addInterviewMessage(personaId, { role: 'assistant', content: answer })

            // 并行模式下：块可能还未创建，先确保块存在
            let block = document.getElementById(`${cardId}-persona-${personaId}`) as HTMLElement
            if (!block) {
              const name = personaInterviews[personaId]?.name || '用户'
              const idx = personaInterviews[personaId]?.index || 0
              block = buildPersonaInterviewBlock(personaId, name, idx, false, [])
              interviewContainer.appendChild(block)
            }

            // 向该人设的对话框追加 QA
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
          } else if (event.type === 'interview_done') {
            const personaId = (event as any).persona_id
            const qaCount = (event as any).qa_count || 0
            if (personaInterviews[personaId]) {
              personaInterviews[personaId].done = true
            }
            completedPersonas++

            // 更新该人设块的元数据
            const block = document.getElementById(`${cardId}-persona-${personaId}`)
            if (block) {
              const meta = block.querySelector('.interview-persona-meta')
              const emotion = block.querySelector('.interview-emotion')
              if (meta) meta.textContent = `${qaCount} 轮问答完成 ✓`
              if (emotion) emotion.textContent = '✅ 完成'
            }

            // 更新进度
            const progText = document.getElementById(`${cardId}-progress-text`)
            const progBar = document.getElementById(`${cardId}-progress-bar`)
            const total = totalPersonas || Object.keys(personaInterviews).length
            if (progText) progText.textContent = completedPersonas >= total
              ? `全部 ${total} 位用户访谈完成 ✓`
              : `正在并行访谈... (${completedPersonas}/${total} 已完成)`
            if (progBar) progBar.style.width = `${total > 0 ? (completedPersonas / total * 100).toFixed(0) : 0}%`
          } else if (event.type === 'step' && event.step === 'auto_interview' && event.status === 'done') {
            // 记录完成状态，暂不更新 DOM（等 SSE 结束后统一处理）
            interviewDoneFlag = true
          }
        } catch {
          buffer = eventStr
        }
      }
    }

    // 只有当 SSE 发送了完成事件时才更新状态
    if (interviewDoneFlag) {
      updateStepCardStatus('done')
    }
    researchStore.updateStepProgress('interview', 'done')
    researchStore.updateStepProgress('report', 'active')

    // 自动进入下一阶段：生成研究报告
    await nextTick()
    scrollToBottom()
    researchStore.setStreaming(false)
    // 自动触发报告生成
    await triggerReport()
    return
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
  let reportDoneFlag = false  // 标记 SSE 是否已发送完成事件

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
            // 记录完成状态，暂不更新 DOM
            reportDoneFlag = true
            researchStore.setReportContent(fullReport)
          }
        } catch {
          buffer = eventStr
        }
      }
    }

    // 只有当 SSE 发送了完成事件时才更新状态
    if (reportDoneFlag) {
      updateStepCardStatus('done')
    }
    researchStore.updateStepProgress('report', 'done')
    researchStore.setPhase('done')

    // 研究完成，显示导出按钮
    updateStepCardFooter(`
      <div class="confirm-block">
        <div class="confirm-question">✅ 研究报告已生成完毕</div>
        <div class="confirm-options">
          <button class="confirm-btn primary" onclick="window.exportReport && window.exportReport()">📥 导出 Markdown</button>
        </div>
      </div>
    `)
    await nextTick()
    scrollToBottom()
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
                  <div :id="msg.stepData && (msg.stepData.id + '-body')" :class="['step-body', { visible: msg.stepData && uiStore.expandedSteps.includes(msg.stepData.id) }]">
                    <div class="streaming-text">
                      <div class="markdown" v-html="msg.stepData && msg.stepData.content ? simpleMarkdown(msg.stepData.content) : ''"></div>
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
