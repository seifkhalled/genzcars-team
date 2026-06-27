'use client'

import { useState, useCallback } from 'react'
import { useCompareStore } from '@/store/compareStore'
import { useSSE } from './useSSE'
import type { ComparisonReport, CompareRequest } from '@/types/compare'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export function useCompare() {
  const { ads, clearAll } = useCompareStore()
  const { start, stop } = useSSE()

  const [isLoading, setIsLoading] = useState(false)
  const [statusText, setStatusText] = useState('')
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [report, setReport] = useState<ComparisonReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  const startComparison = useCallback(async () => {
    if (ads.length < 2) return

    setIsLoading(true)
    setStatusText('')
    setProgress({ current: 0, total: 0 })
    setReport(null)
    setError(null)

    const body: CompareRequest = {
      ad_ids: ads.map((a) => a.id),
    }

    await start(`${API_URL}/compare`, body, {
      onEvent: (event) => {
        switch (event.type) {
          case 'status':
            setStatusText(event.content)
            break
          case 'progress':
            setProgress(event.content)
            break
          case 'report':
            setReport(event.content)
            break
          case 'error':
            setError(event.content)
            break
        }
      },
      onDone: () => {
        setIsLoading(false)
      },
      onError: (err) => {
        setError(err)
        setIsLoading(false)
      },
    })
  }, [ads])

  const reset = useCallback(() => {
    clearAll()
    setReport(null)
    setStatusText('')
    setProgress({ current: 0, total: 0 })
    setError(null)
    stop()
  }, [clearAll, stop])

  return {
    selectedAds: ads,
    isLoading,
    statusText,
    progress,
    report,
    error,
    startComparison,
    reset,
  }
}
