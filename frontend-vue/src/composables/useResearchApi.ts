import { useResearchStore } from '@/stores'
import { useSSE } from './useSSE'
import type {
  DesignStudyRequest,
  SearchPersonasRequest,
  ScoutRequest,
  InterviewRequest,
  ReportRequest,
  SSEEvent
} from '@/types'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api/v1'
  : `${window.location.origin}/api/v1`

export function useResearchApi() {
  const store = useResearchStore()
  const { streamSSE } = useSSE()

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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
    designStudy,
    searchPersonas,
    scoutAndBuild,
    autoInterview,
    interviewStream,
    generateReport,
    uploadContext
  }
}
