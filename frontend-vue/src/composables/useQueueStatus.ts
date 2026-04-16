/**
 * 任务队列状态管理
 */
import { ref, computed, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores'

interface QueueStatus {
  task_id: string
  study_id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'not_in_queue'
  queue_position: number | null
  queue_info: {
    max_concurrent: number
    queued: number
    running: number
    total_tasks: number
  }
  created_at?: string
  started_at?: string
}

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api/v1'
  : `${window.location.origin}/api/v1`

export function useQueueStatus() {
  const queueStatus = ref<QueueStatus | null>(null)
  const isConnected = ref(false)

  // 计算属性
  const isQueued = computed(() => queueStatus.value?.status === 'queued')
  const isRunning = computed(() => queueStatus.value?.status === 'running')
  const queuePosition = computed(() => queueStatus.value?.queue_position ?? 0)
  const maxConcurrent = computed(() => queueStatus.value?.queue_info?.max_concurrent ?? 4)
  const waitingCount = computed(() => queueStatus.value?.queue_info?.queued ?? 0)

  // SSE 连接
  let eventSource: EventSource | null = null
  let reconnectTimer: number | null = null

  async function fetchQueueStatus(studyId: string) {
    const authStore = useAuthStore()
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    try {
      const response = await fetch(`${API_BASE}/research-flow/queue-status?study_id=${studyId}`, {
        headers
      })
      if (response.ok) {
        const data = await response.json()
        if (data.data) {
          queueStatus.value = data.data as QueueStatus
        }
      }
    } catch (e) {
      console.error('[QueueStatus] 获取状态失败:', e)
    }
  }

  function connectQueueStream(studyId: string) {
    const authStore = useAuthStore()

    // EventSource 不支持自定义 headers，使用 fetch 替代
    const url = `${API_BASE}/research-flow/queue-status-stream`

    const fetchStream = async () => {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authStore.token}`
          },
          body: JSON.stringify({ study_id: studyId })
        })

        if (!response.ok) {
          console.error('[QueueStatus] 连接失败:', response.status)
          scheduleReconnect(studyId)
          return
        }

        isConnected.value = true
        const reader = response.body?.getReader()
        if (!reader) return

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()
              if (data === '[DONE]') continue
              try {
                const event = JSON.parse(data)
                if (event.type === 'heartbeat') continue
                queueStatus.value = {
                  task_id: event.task_id,
                  study_id: event.study_id || studyId,
                  status: event.status,
                  queue_position: event.queue_position,
                  queue_info: event.queue_info || queueStatus.value?.queue_info || { max_concurrent: 4, queued: 0, running: 0, total_tasks: 0 },
                }
              } catch (e) {
                // 忽略解析错误
              }
            }
          }
        }
      } catch (e) {
        console.error('[QueueStatus] 连接错误:', e)
        isConnected.value = false
        scheduleReconnect(studyId)
      }
    }

    fetchStream()
  }

  function scheduleReconnect(studyId: string) {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      connectQueueStream(studyId)
    }, 3000) as unknown as number
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    isConnected.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    queueStatus,
    isConnected,
    isQueued,
    isRunning,
    queuePosition,
    maxConcurrent,
    waitingCount,
    fetchQueueStatus,
    connectQueueStream,
    disconnect,
  }
}
