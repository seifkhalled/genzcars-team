'use client'

import { useRef, useCallback } from 'react'
import { SSEParser, type SSEEventCallback } from '@/lib/sse'

interface UseSSEOptions {
  onEvent: SSEEventCallback
  onDone: () => void
  onError: (err: string) => void
}

export function useSSE() {
  const parserRef = useRef<SSEParser | null>(null)

  const start = useCallback(async (url: string, body: object, options: UseSSEOptions) => {
    parserRef.current?.disconnect()
    const parser = new SSEParser()
    parserRef.current = parser
    await parser.connect(url, body, options)
  }, [])

  const stop = useCallback(() => {
    parserRef.current?.disconnect()
    parserRef.current = null
  }, [])

  return { start, stop }
}
