'use client'

import { MessageCircle } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/Button'
import { useChatStore } from '@/store/chatStore'

export function AskAiBanner() {
  const t = useTranslations('search')

  return (
    <Button variant="primary" className="gap-2" onClick={() => useChatStore.getState().open()}>
      <MessageCircle className="w-4 h-4" />
      {t('tryAiAssistant') || 'Try the AI Assistant'}
    </Button>
  )
}
