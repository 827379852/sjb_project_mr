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
