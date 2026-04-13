import { useResearchStore, useAuthStore } from '@/stores'
import { useSSE } from './useSSE'
import type {
  DesignStudyRequest,
  SearchPersonasRequest,
  ScoutRequest,
  InterviewRequest,
  ReportRequest,
  SSEEvent,
  StudyListItem,
  StudyDetail
} from '@/types'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api/v1'
  : `${window.location.origin}/api/v1`

export function useResearchApi() {
  const store = useResearchStore()
  const authStore = useAuthStore()
  const { streamSSE } = useSSE()

  // 获取认证头
  function getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }
    return headers
  }

  // 获取研究列表
  async function listStudies(): Promise<StudyListItem[]> {
    try {
      const res = await fetch(`${API_BASE}/research-flow/studies`, {
        headers: getAuthHeaders()
      })
      const data = await res.json()
      return data.code === 0 ? data.data : []
    } catch (e) {
      console.error('获取研究列表失败', e)
      return []
    }
  }

  // 获取研究详情
  async function getStudy(studyId: string): Promise<StudyDetail | null> {
    try {
      const res = await fetch(`${API_BASE}/research-flow/studies/${studyId}`, {
        headers: getAuthHeaders()
      })
      const data = await res.json()
      console.log('getStudy response:', data)
      if (data.code === 0) {
        console.log('study detail:', {
          id: data.data.id,
          title: data.data.title,
          user_request: data.data.user_request?.substring(0, 50),
          design_content: data.data.design_content?.substring(0, 100),
          personas_count: data.data.personas?.length,
          interviews_count: data.data.interviews?.length,
          reports_count: data.data.reports?.length
        })
      }
      return data.code === 0 ? data.data : null
    } catch (e) {
      console.error('获取研究详情失败', e)
      return null
    }
  }

  // 删除研究
  async function deleteStudy(studyId: string): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/research-flow/studies/${studyId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })
      const data = await res.json()
      return data.code === 0
    } catch (e) {
      console.error('删除研究失败', e)
      return false
    }
  }

  // 加载历史研究到 store
  function loadStudy(study: StudyDetail): StudyDetail {
    // ========== 关键修复：加载新研究前先取消之前的请求并清空旧数据 ==========
    store.abortAllRequests()

    // 清空旧数据，防止上一个任务的数据混入
    store.setPersonas([])
    store.setInterviewHistory({})
    store.setScoutResults([])
    store.setReportContent('')
    store.setSelectedPersona(null)
    store.clearAttachments()
    // 重置步骤进度
    store.updateStepProgress('design', 'pending')
    store.updateStepProgress('personas', 'pending')
    store.updateStepProgress('scout', 'pending')
    store.updateStepProgress('interview', 'pending')
    store.updateStepProgress('report', 'pending')
    // ============================================================

    // 先设置其他数据，最后设置 studyId 以触发 watch
    store.setStudyTitle(study.title)
    store.setPhase(study.current_phase as any)
    store.setUserRequest(study.user_request || '')
    store.setDesignContent(study.design_content || '')

    // 恢复人设
    const personaList: any[] = study.personas.map(p => ({
      id: p.id,
      name: p.name,
      age: p.age,
      occupation: p.occupation,
      city: p.city,
      background: p.background,
      ...((p as any).persona_data || {})
    }))
    store.setPersonas(personaList)

    // 恢复访谈历史 - 同一 persona 可能有多条记录，需要合并
    const history: Record<string, { role: 'user' | 'assistant'; content: string }[]> = {}
    study.interviews.forEach(i => {
      if (!history[i.persona_id]) {
        history[i.persona_id] = []
      }
      history[i.persona_id].push(...(i.messages as { role: 'user' | 'assistant'; content: string }[]))
    })
    store.setInterviewHistory(history as Record<string, import('@/types').InterviewMessage[]>)

    // 恢复社媒侦察结果 - 从后端加载并按 persona_id 分组，跳过无归属的汇总记录
    if (study.scout_results && study.scout_results.length > 0) {
      const grouped: Record<string, { personaId: string; personaName: string; posts: any[]; insights: string[] }> = {}
      study.scout_results.forEach((sr: any) => {
        // 跳过无 persona_id 的汇总记录（只保留有人设归属的数据）
        const pid = sr.persona_id
        if (!pid) return
        if (!grouped[pid]) {
          // 查找对应的人设名称
          const persona = personaList.find((p: any) => p.id === pid)
          grouped[pid] = {
            personaId: pid,
            personaName: persona?.name || sr.keywords?.[0] || '未知用户',
            posts: [],
            insights: []
          }
        }
        // 合并帖子（去重）
        const existingPostIds = new Set((grouped[pid].posts as any[]).map((p: any) => p.link || p.title))
        ;(sr.posts || []).forEach((post: any) => {
          const key = post.link || post.title
          if (key && !existingPostIds.has(key)) {
            grouped[pid].posts.push(post)
            existingPostIds.add(key)
          }
        })
        // 合并洞察
        if (sr.insights) {
          grouped[pid].insights.push(...sr.insights)
        }
      })
      store.setScoutResults(Object.values(grouped))
    }

    // 恢复报告
    if (study.reports && study.reports.length > 0) {
      store.setReportContent(study.reports[0].content)
    }

    // 更新步骤进度 - 根据当前阶段恢复各步骤状态
    const phase = study.current_phase
    const phaseOrder: Record<string, string[]> = {
      'post-design': ['design'],
      'personas': ['design', 'personas'],
      'scouting': ['design', 'personas', 'scout'],
      'interviewing': ['design', 'personas', 'scout', 'interview'],
      'reporting': ['design', 'personas', 'scout', 'interview', 'report'],
      'completed': ['design', 'personas', 'scout', 'interview', 'report'],
    }
    const doneSteps = phaseOrder[phase] || []
    const stepNames: (keyof typeof store.stepProgress)[] = ['design', 'personas', 'scout', 'interview', 'report']
    stepNames.forEach(step => {
      if (doneSteps.includes(step)) {
        store.updateStepProgress(step, 'done')
      }
    })

    // 最后设置 studyId，触发 watch
    store.setStudyId(study.id)

    return study
  }

  // 设计研究框架
  async function designStudy(userRequest: string, context?: string): Promise<void> {
    store.setStreaming(true)
    store.setPhase('designing')

    const body: DesignStudyRequest = {
      user_request: userRequest,
      context: context || ''
    }

    let fullContent = ''

    await streamSSE(
      `${API_BASE}/research-flow/design-study`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
      },
      {
        onEvent: (event: SSEEvent) => {
          if (event.type === 'study_id') {
            store.setStudyId(event.study_id as string)
          } else if (event.type === 'content') {
            fullContent += event.delta as string
          } else if (event.type === 'step' && event.status === 'done') {
            store.updateStepProgress('design', 'done')
            store.updateStepProgress('personas', 'active')
            store.setPhase('post-design')
          }
        },
        onDone: () => {
          store.setStreaming(false)
        },
        onError: () => {
          store.setStreaming(false)
        }
      }
    )

    return { fullContent } as unknown as void
  }

  // 生成人设
  async function searchPersonas(
    onPersona: (persona: SSEEvent) => void,
    onDone?: () => void
  ): Promise<void> {
    if (!store.studyId || store.isStreaming) return

    store.setStreaming(true)
    store.setPhase('personas')
    store.updateStepProgress('personas', 'active')

    const body: SearchPersonasRequest = {
      study_id: store.studyId,
      persona_description: '根据研究背景生成',
      max_count: 10
    }

    await streamSSE(
      `${API_BASE}/research-flow/search-personas`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
      },
      {
        onEvent: (event: SSEEvent) => {
          if (event.type === 'persona') {
            onPersona(event)
          } else if (event.type === 'step' && event.status === 'done') {
            store.updateStepProgress('personas', 'done')
            store.updateStepProgress('scout', 'active')
          }
        },
        onDone: () => {
          store.setStreaming(false)
          onDone?.()
        },
        onError: () => {
          store.setStreaming(false)
        }
      }
    )
  }

  // 社媒侦察
  async function scoutAndBuild(
    keywords: string[],
    onEvent: (event: SSEEvent) => void,
    onDone?: () => void
  ): Promise<void> {
    if (!store.studyId || store.isStreaming) return

    store.setStreaming(true)
    store.setPhase('scouting')
    store.updateStepProgress('scout', 'active')

    const body: ScoutRequest = {
      study_id: store.studyId,
      keywords,
      platforms: ['小红书', '微博', '抖音']
    }

    await streamSSE(
      `${API_BASE}/research-flow/scout-and-build`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
      },
      {
        onEvent: (event: SSEEvent) => {
          onEvent(event)
        },
        onDone: () => {
          store.updateStepProgress('scout', 'done')
          store.updateStepProgress('interview', 'active')
          store.setStreaming(false)
          onDone?.()
        },
        onError: () => {
          store.setStreaming(false)
        }
      }
    )
  }

  // 自动访谈
  async function autoInterview(
    onEvent: (event: SSEEvent) => void,
    onDone?: () => void
  ): Promise<void> {
    if (!store.studyId || store.isStreaming) return

    store.setStreaming(true)
    store.setPhase('interviewing')
    store.updateStepProgress('interview', 'active')

    await streamSSE(
      `${API_BASE}/research-flow/auto-interview`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ study_id: store.studyId })
      },
      {
        onEvent: (event: SSEEvent) => {
          onEvent(event)
        },
        onDone: () => {
          store.updateStepProgress('interview', 'done')
          store.updateStepProgress('report', 'active')
          store.setStreaming(false)
          onDone?.()
        },
        onError: () => {
          store.setStreaming(false)
        }
      }
    )
  }

  // 单次访谈问答
  async function interviewStream(
    personaId: string,
    question: string,
    onContent: (delta: string) => void,
    onDone?: (fullResponse: string) => void
  ): Promise<void> {
    if (!store.studyId || store.isStreaming) return

    store.setStreaming(true)

    const body: InterviewRequest = {
      study_id: store.studyId,
      persona_id: personaId,
      question,
      conversation_history: store.interviewHistory[personaId] || []
    }

    let fullResponse = ''

    await streamSSE(
      `${API_BASE}/research-flow/interview/stream`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
      },
      {
        onEvent: (event: SSEEvent) => {
          if (event.type === 'content') {
            const delta = event.delta as string
            fullResponse += delta
            onContent(delta)
          }
        },
        onDone: () => {
          store.setStreaming(false)
          onDone?.(fullResponse)
        },
        onError: () => {
          store.setStreaming(false)
        }
      }
    )
  }

  // 生成报告
  async function generateReport(
    onContent: (delta: string) => void,
    onDone?: () => void
  ): Promise<void> {
    if (!store.studyId || store.isStreaming) return

    store.setStreaming(true)
    store.setPhase('reporting')
    store.updateStepProgress('report', 'active')

    const transcripts = Object.entries(store.interviewHistory).map(([id, msgs]) => ({
      persona_id: id,
      messages: msgs
    }))

    const body: ReportRequest = {
      study_id: store.studyId,
      personas: store.personas,
      interview_transcripts: transcripts,
      format: 'markdown'
    }

    let fullReport = ''

    await streamSSE(
      `${API_BASE}/research-flow/generate-report`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body)
      },
      {
        onEvent: (event: SSEEvent) => {
          if (event.type === 'content') {
            const delta = event.delta as string
            fullReport += delta
            onContent(delta)
          } else if (event.type === 'step' && event.status === 'done') {
            store.setReportContent(fullReport)
            store.updateStepProgress('report', 'done')
          }
        },
        onDone: () => {
          store.setStreaming(false)
          onDone?.()
        },
        onError: () => {
          store.setStreaming(false)
        }
      }
    )
  }

  // 上传文件
  async function uploadContext(file: File): Promise<string | null> {
    const formData = new FormData()
    formData.append('file', file)
    if (store.studyId) {
      formData.append('study_id', store.studyId)
    }

    try {
      const res = await fetch(`${API_BASE}/research-flow/upload-context`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      if (data.code === 0) {
        return data.data.extracted_text
      }
    } catch (e) {
      console.error('上传失败', e)
    }
    return null
  }

  return {
    listStudies,
    getStudy,
    deleteStudy,
    loadStudy,
    designStudy,
    searchPersonas,
    scoutAndBuild,
    autoInterview,
    interviewStream,
    generateReport,
    uploadContext
  }
}
