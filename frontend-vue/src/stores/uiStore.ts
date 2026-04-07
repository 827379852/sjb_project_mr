import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUIStore = defineStore('ui', () => {
  // State - 使用数组代替 Set 以确保响应式
  const welcomeVisible = ref(true)
  const progressBarVisible = ref(false)
  const expandedSteps = ref<string[]>([])
  const expandedPersonas = ref<string[]>([])
  const activeToolbarButtons = ref<string[]>([])

  // Computed helpers
  const isStepExpanded = computed(() => (stepId: string) => expandedSteps.value.includes(stepId))
  const isPersonaExpanded = computed(() => (personaId: string) => expandedPersonas.value.includes(personaId))

  // Actions
  function hideWelcome() {
    welcomeVisible.value = false
  }

  function showWelcome() {
    welcomeVisible.value = true
  }

  function showProgressBar() {
    progressBarVisible.value = true
  }

  function hideProgressBar() {
    progressBarVisible.value = false
  }

  function toggleStep(stepId: string) {
    const idx = expandedSteps.value.indexOf(stepId)
    if (idx >= 0) {
      expandedSteps.value.splice(idx, 1)
    } else {
      expandedSteps.value.push(stepId)
    }
  }

  function expandStep(stepId: string) {
    if (!expandedSteps.value.includes(stepId)) {
      expandedSteps.value.push(stepId)
    }
  }

  function collapseStep(stepId: string) {
    const idx = expandedSteps.value.indexOf(stepId)
    if (idx >= 0) {
      expandedSteps.value.splice(idx, 1)
    }
  }

  function togglePersona(personaId: string) {
    const idx = expandedPersonas.value.indexOf(personaId)
    if (idx >= 0) {
      expandedPersonas.value.splice(idx, 1)
    } else {
      expandedPersonas.value.push(personaId)
    }
  }

  function showToolbarButton(buttonId: string) {
    if (!activeToolbarButtons.value.includes(buttonId)) {
      activeToolbarButtons.value.push(buttonId)
    }
  }

  function hideToolbarButton(buttonId: string) {
    const idx = activeToolbarButtons.value.indexOf(buttonId)
    if (idx >= 0) {
      activeToolbarButtons.value.splice(idx, 1)
    }
  }

  function isToolbarButtonVisible(buttonId: string) {
    return activeToolbarButtons.value.includes(buttonId)
  }

  function reset() {
    welcomeVisible.value = true
    progressBarVisible.value = false
    expandedSteps.value = []
    expandedPersonas.value = []
    activeToolbarButtons.value = []
  }

  return {
    // State
    welcomeVisible,
    progressBarVisible,
    expandedSteps,
    expandedPersonas,
    activeToolbarButtons,
    // Computed
    isStepExpanded,
    isPersonaExpanded,
    // Actions
    hideWelcome,
    showWelcome,
    showProgressBar,
    hideProgressBar,
    toggleStep,
    expandStep,
    collapseStep,
    togglePersona,
    showToolbarButton,
    hideToolbarButton,
    isToolbarButtonVisible,
    reset
  }
})
