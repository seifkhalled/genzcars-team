'use client'

import { useEffect, useState } from 'react'
import { CheckCircle, AlertCircle, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ToastProps {
  message: string
  type?: 'success' | 'error' | 'info'
  isVisible: boolean
  onClose: () => void
  duration?: number
}

export function Toast({ message, type = 'info', isVisible, onClose, duration = 3000 }: ToastProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (isVisible) {
      setMounted(true)
      const timer = setTimeout(() => {
        onClose()
      }, duration)
      return () => clearTimeout(timer)
    }
    setMounted(false)
  }, [isVisible, duration, onClose])

  if (!mounted) return null

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-success" />,
    error: <AlertCircle className="w-5 h-5 text-danger" />,
    info: <CheckCircle className="w-5 h-5 text-primary-500" />,
  }

  const bg = {
    success: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
    info: 'bg-blue-50 border-blue-200',
  }

  return (
    <div className={cn(
      'fixed bottom-24 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg',
      'animate-slide-up transition-all',
      bg[type]
    )}>
      {icons[type]}
      <p className="text-sm text-text-primary">{message}</p>
      <button onClick={onClose} className="p-1 hover:opacity-70">
        <X className="w-4 h-4 text-text-muted" />
      </button>
    </div>
  )
}
