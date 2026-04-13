import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Persona, Phase, StepProgress, InterviewMessage, Attachment, StepStatus, ScoutResult } from '@/types'

// ========== 废弃全局 localStorage 存储 ==========
// 问题：全局存储会导致不同研究的数据混淆
// 解决：不再使用 localStorage 存储 scoutResults，改为内存存储
// const SCOUT_RESULTS_KEY = 'research_scout_results'
// function loadScoutResultsFromStorage(): ScoutResult[] { ... }
// ====================================================

export const useResearchStore = defineStore('research', () => {
  // State
  const studyId = ref<string | null>(null)
  const studyTitle = ref('新研究')
  const phase = ref<Phase>('idle')
  const userRequest = ref('')
  const designContent = ref('')
  const previousDesignContent = ref('')  // 调整前的设计框架
  const personas = ref<Persona[]>([])
  const selectedPersona = ref<Persona | null>(null)
  const interviewHistory = ref<Record<string, InterviewMessage[]>>({})
  // ========== 修改：不再从 localStorage 恢复，改为内存存储 ==========
  // 这样切换研究时会自动隔离数据
  const scoutResults = ref<ScoutResult[]>([])
  // ==============================================================
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

  // ========== SSE 取消控制器 ==========
  // 用于在任务切换时取消所有正在进行的 SSE 请求
  const abortController = ref<AbortController | null>(null)

  // 取消当前所有 SSE 请求
  function abortAllRequests() {
    if (abortController.value) {
      abortController.value.abort()
      console.log('[ResearchStore] 已取消所有 SSE 请求')
    }
    abortController.value = new AbortController()
    isStreaming.value = false
  }

  // 获取当前 AbortController 的 signal
  function getAbortSignal(): AbortSignal {
    if (!abortController.value) {
      abortController.value = new AbortController()
    }
    return abortController.value.signal
  }

  // 创建新的 AbortController（开始新请求时调用）
  function createAbortController(): AbortController {
    abortController.value = new AbortController()
    return abortController.value
  }
  // ====================================

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

  function setUserRequest(request: string) {
    userRequest.value = request
  }

  function setDesignContent(content: string) {
    designContent.value = content
  }

  function setPreviousDesignContent(content: string) {
    previousDesignContent.value = content
  }

  function setPersonas(list: Persona[]) {
    personas.value = list
  }

  function setInterviewHistory(history: Record<string, InterviewMessage[]>) {
    interviewHistory.value = history
  }

  function addScoutResult(result: ScoutResult) {
    scoutResults.value.push(result)
    // 不再保存到 localStorage，改为内存存储
  }

  function setScoutResults(results: ScoutResult[]) {
    scoutResults.value = results
    // 不再保存到 localStorage，改为内存存储
  }

  function updateStepProgress(step: keyof StepProgress, status: StepStatus) {
    stepProgress.value[step] = status
  }

  function reset() {
    // 先取消所有正在进行的 SSE 请求
    abortAllRequests()
    studyId.value = null
    studyTitle.value = '新研究'
    phase.value = 'idle'
    userRequest.value = ''
    designContent.value = ''
    previousDesignContent.value = ''
    personas.value = []
    selectedPersona.value = null
    interviewHistory.value = {}
    scoutResults.value = []
    // 不再需要清除 localStorage，因为已经不使用了
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
    userRequest,
    designContent,
    previousDesignContent,
    personas,
    selectedPersona,
    interviewHistory,
    scoutResults,
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
    setUserRequest,
    setDesignContent,
    setPreviousDesignContent,
    setPersonas,
    setInterviewHistory,
    setScoutResults,
    addPersona,
    updatePersona,
    setSelectedPersona,
    addInterviewMessage,
    addScoutResult,
    addAttachment,
    removeAttachment,
    clearAttachments,
    setStreaming,
    setReportContent,
    updateStepProgress,
    reset,
    // SSE 取消控制
    abortAllRequests,
    getAbortSignal,
    createAbortController,
  }
})
