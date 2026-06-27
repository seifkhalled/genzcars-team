'use client'

import { useCallback } from 'react'
import { useChatStore } from '@/store/chatStore'
import { useSSE } from './useSSE'
import type { ChatMessage } from '@/types/chat'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export function useChat() {
  const {
    messages, isStreaming, sessionToken, contextAdId,
    addMessage, appendToken, setStreaming, setSessionToken,
  } = useChatStore()

  const { start, stop } = useSSE()

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return

    const token = sessionToken || Math.random().toString(36).substring(2, 15)
    if (!sessionToken) setSessionToken(token)

    const userMsg: Omit<ChatMessage, 'id'> = {
      role: 'user',
      content: text,
      type: 'text',
    }
    addMessage(userMsg)
    setStreaming(true)

    await start(
      `${API_URL}/chat/message`,
      {
        session_token: token,
        message: text,
        context_ad_id: contextAdId,
      },
      {
        onEvent: (event) => {
          switch (event.type) {
            case 'token':
              appendToken(event.content)
              break
            case 'cars':
              addMessage({
                role: 'assistant',
                content: '',
                type: 'cars',
                cars: event.content,
              })
              break
            case 'similar_cars':
              addMessage({
                role: 'assistant',
                content: '',
                type: 'similar_cars',
                similar_cars: event.content,
              })
              break
            case 'price_analysis':
              addMessage({
                role: 'assistant',
                content: '',
                type: 'price_analysis',
                price_analysis: event.content,
              })
              break
            case 'new_match':
              addMessage({
                role: 'assistant',
                content: 'New listings matching your preferences!',
                type: 'new_match',
                cars: event.content,
              })
              break
            case 'status':
              addMessage({
                role: 'system',
                content: event.content,
                type: 'status',
              })
              break
            case 'error':
              addMessage({
                role: 'system',
                content: event.content,
                type: 'error',
              })
              break
          }
        },
        onDone: () => {
          setStreaming(false)
        },
        onError: (err) => {
          addMessage({
            role: 'system',
            content: err,
            type: 'error',
          })
          setStreaming(false)
        },
      }
    )
  }, [sessionToken, contextAdId, isStreaming])

  return { messages, isStreaming, sendMessage, stop }
}
