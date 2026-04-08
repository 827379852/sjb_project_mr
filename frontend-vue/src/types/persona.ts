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
