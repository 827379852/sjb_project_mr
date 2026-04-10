export interface Persona {
  id: string
  name: string
  age?: number
  occupation?: string
  city?: string
  background?: string
  personality?: string
  consumer_habits?: string
  pain_points?: string[] | string
  motivations?: string
  digital_behavior?: string
  social_media?: string
  core_values?: string[]
  attitude?: Record<string, unknown> | string
  attitude_hypotheses?: Record<string, unknown>
  description?: string
  scouted_updates?: Record<string, unknown> | string
}

export interface Post {
  platform: string
  content: string
  sentiment: 'positive' | 'negative' | 'neutral'
}

// 社媒侦察帖子（完整字段，来自 SSE 实时事件）
export interface ScoutPost {
  platform?: string
  content?: string
  title?: string
  author?: string
  link?: string
  sentiment?: 'positive' | 'negative' | 'neutral'
  comments?: { user?: string; text?: string }[]
  is_real?: boolean | string
}

// 社媒侦察结果（按人设分组）
export interface ScoutResult {
  personaId: string
  personaName: string
  posts: ScoutPost[]
  insights: string[]
}

// 社媒侦察原始数据（从后端加载的格式）
export interface ScoutResultRaw {
  id: string
  persona_id?: string
  keywords: string[]
  platforms: string[]
  posts: ScoutPost[]
  insights: string[]
}

export interface InterviewMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface Attachment {
  name: string
  text: string
}

export type Phase =
  | 'idle'
  | 'designing'
  | 'post-design'
  | 'personas'
  | 'scouting'
  | 'interviewing'
  | 'reporting'
  | 'done'

export type StepStatus = 'pending' | 'active' | 'done'

export interface StepProgress {
  design: StepStatus
  personas: StepStatus
  scout: StepStatus
  interview: StepStatus
  report: StepStatus
}
