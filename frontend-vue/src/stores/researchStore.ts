import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Persona, Phase, StepProgress, InterviewMessage, Attachment, StepStatus } from '@/types'

export const useResearchStore = defineStore('research', () => {
  // State
  const studyId = ref<string | null>(null)
  const studyTitle = ref('新研究')
  const phase = ref<Phase>('idle')
  const personas = ref<Persona[]>([])
  const selectedPersona = ref<Persona | null>(null)
  const interviewHistory = ref<Record<string, InterviewMessage[]>>({})
  const attachments = ref<Attachment[]>([])
  const isStreaming = ref(false)
  const reportContent = ref('')
  const stepProgress = ref<StepProgress>({
    design: 'pending',
    personas: 'pending',
    scout: 'pending',
    interview: 'pending',
    report: 'pending'
  })

  // Computed
  const hasPersonas = computed(() => personas.value.length > 0)
  const hasReport = computed(() => reportContent.value.length > 0)

  // Actions
  function setStudyId(id: string | null) {
    studyId.value = id
  }

  function setStudyTitle(title: string) {
    studyTitle.value = title
  }

  function setPhase(newPhase: Phase) {
    phase.value = newPhase
  }

  function addPersona(persona: Persona) {
    personas.value.push(persona)
  }

  function updatePersona(persona: Persona) {
    const idx = personas.value.findIndex(p => p.id === persona.id)
    if (idx >= 0) {
      personas.value[idx] = persona
    }
  }

  function setSelectedPersona(persona: Persona | null) {
    selectedPersona.value = persona
  }

  function addInterviewMessage(personaId: string, message: InterviewMessage) {
    if (!interviewHistory.value[personaId]) {
      interviewHistory.value[personaId] = []
    }
    interviewHistory.value[personaId].push(message)
  }

  function addAttachment(attachment: Attachment) {
    attachments.value.push(attachment)
  }

  function removeAttachment(index: number) {
    attachments.value.splice(index, 1)
  }

  function clearAttachments() {
    attachments.value = []
  }

  function setStreaming(value: boolean) {
    isStreaming.value = value
  }

  function setReportContent(content: string) {
    reportContent.value = content
  }

  function updateStepProgress(step: keyof StepProgress, status: StepStatus) {
    stepProgress.value[step] = status
  }

  function reset() {
    studyId.value = null
    studyTitle.value = '新研究'
    phase.value = 'idle'
    personas.value = []
    selectedPersona.value = null
    interviewHistory.value = {}
    attachments.value = []
    isStreaming.value = false
    reportContent.value = ''
    stepProgress.value = {
      design: 'pending',
      personas: 'pending',
      scout: 'pending',
      interview: 'pending',
      report: 'pending'
    }
  }

  return {
    // State
    studyId,
    studyTitle,
    phase,
    personas,
    selectedPersona,
    interviewHistory,
    attachments,
    isStreaming,
    reportContent,
    stepProgress,
    // Computed
    hasPersonas,
    hasReport,
    // Actions
    setStudyId,
    setStudyTitle,
    setPhase,
    addPersona,
    updatePersona,
    setSelectedPersona,
    addInterviewMessage,
    addAttachment,
    removeAttachment,
    clearAttachments,
    setStreaming,
    setReportContent,
    updateStepProgress,
    reset
  }
})
