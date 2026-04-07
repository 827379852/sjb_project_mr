import type { SSEEvent } from '@/types'

type EventHandler = (event: SSEEvent) => void

export function useSSE() {
  async function streamSSE(
    url: string,
    options: RequestInit,
    handlers: {
      onEvent?: EventHandler
      onDone?: () => void
      onError?: (error: Error) => void
    }
  ): Promise<void> {
    try {
      const response = await fetch(url, options)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No reader available')
      }

      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const lines = decoder.decode(value).split('\n')
        for (const line of lines) {
          if (!line.startsWith('data: ') || line === 'data: [DONE]') continue

          try {
            const event = JSON.parse(line.slice(6)) as SSEEvent
            handlers.onEvent?.(event)
          } catch {
            // Ignore parse errors
          }
        }
      }

      handlers.onDone?.()
    } catch (error) {
      handlers.onError?.(error instanceof Error ? error : new Error(String(error)))
    }
  }

  return {
    streamSSE
  }
}
