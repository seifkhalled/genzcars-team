'use client'

import { MessageCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useChatStore } from '@/store/chatStore'

interface AskAiButtonProps {
  adId: string
}

export function AskAiButton({ adId }: AskAiButtonProps) {
  return (
    <Button
      variant="secondary"
      className="w-full gap-2"
      onClick={() => useChatStore.getState().open(adId)}
    >
      <MessageCircle className="w-4 h-4" />
      Ask AI about this car
    </Button>
  )
}
