'use client'

import { MessageCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/store/chatStore'

let pingTimeout: ReturnType<typeof setTimeout> | null = null

export function ChatBubble() {
  const { open, messages } = useChatStore()
  const hasNewMatch = messages.some((m) => m.type === 'new_match')

  const handleClick = () => {
    open()
  }

  return (
      <button
        onClick={handleClick}
        className={cn(
          'fixed z-50 bottom-6 ltr:right-6 rtl:left-6',
          'flex items-center justify-center',
          'w-14 h-14 rounded-full bg-primary-500 text-white',
          'shadow-lg hover:shadow-xl hover:bg-primary-600',
          'transition-all duration-200 active:scale-95',
          'before:absolute before:inset-0 before:rounded-full before:bg-primary-400/20 before:animate-pulse before:scale-150'
        )}
        aria-label="Open chat"
      >
        {hasNewMatch && (
          <span className="absolute inset-0 rounded-full animate-ping bg-primary-400 opacity-75" />
        )}
        <MessageCircle className="w-6 h-6 relative" />
      </button>
  )
}
