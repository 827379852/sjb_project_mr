export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface SSEEvent {
  type: string
  [key: string]: unknown
}

export interface DesignStudyRequest {
  user_request: string
  context?: string
}

export interface SearchPersonasRequest {
  study_id: string
  persona_description: string
  max_count?: number
}

export interface ScoutRequest {
  study_id: string
  keywords: string[]
  platforms: string[]
  persona_ids?: string[]
}

export interface InterviewRequest {
  study_id: string
  persona_id: string
  question: string
  conversation_history: Array<{ role: string; content: string }>
}

export interface ReportRequest {
  study_id: string
  personas: unknown[]
  interview_transcripts: Array<{
    persona_id: string
    messages: Array<{ role: string; content: string }>
  }>
  format?: string
}

export interface UploadContextResponse {
  extracted_text: string
}
