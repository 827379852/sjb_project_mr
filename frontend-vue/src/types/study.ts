import type { Persona, Phase, StepProgress, InterviewMessage, Attachment } from './persona'

export interface ResearchState {
  studyId: string | null
  studyTitle: string
  phase: Phase
  personas: Persona[]
  selectedPersona: Persona | null
  interviewHistory: Record<string, InterviewMessage[]>
  attachments: Attachment[]
  isStreaming: boolean
  reportContent: string
  stepProgress: StepProgress
}

export interface UIState {
  welcomeVisible: boolean
  progressBarVisible: boolean
  expandedSteps: Set<string>
  expandedPersonas: Set<string>
  activeToolbarButtons: string[]
}

// 研究列表项
export interface StudyListItem {
  id: string
  user_id: string
  title: string
  status: string
  current_phase: string
  created_at: string
  updated_at: string
}

// 访谈记录
export interface InterviewRecord {
  id: string
  persona_id: string
  persona_name: string
  messages: { role: string; content: string }[]
}

// 侦察结果
export interface ScoutResultRecord {
  id: string
  keywords: string[]
  platforms: string[]
  posts: any[]
  insights: string[]
}

// 报告记录
export interface ReportRecord {
  id: string
  content: string
  format: string
}

// 研究详情
export interface StudyDetail {
  id: string
  user_id: string
  title: string
  user_request: string
  design_content: string
  status: string
  current_phase: string
  created_at: string
  updated_at: string
  personas: Persona[]
  interviews: InterviewRecord[]
  scout_results: ScoutResultRecord[]
  reports: ReportRecord[]
}
