'use client'

import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

interface ScoreBarProps {
  label: string
  score: number
  maxScore?: number
}

export default function ScoreBar({ label, score, maxScore = 10 }: ScoreBarProps) {
  const [animatedWidth, setAnimatedWidth] = useState(0)
  const percentage = Math.min((score / maxScore) * 100, 100)

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedWidth(percentage), 100)
    return () => clearTimeout(timer)
  }, [percentage])

  const barColor =
    score > 7
      ? 'bg-green-500'
      : score >= 4
        ? 'bg-yellow-500'
        : 'bg-red-500'

  return (
    <div className="flex items-center gap-3">
      <span className="w-32 shrink-0 text-right text-sm font-medium text-muted-foreground">
        {label}
      </span>

      <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full transition-all duration-1000 ease-out', barColor)}
          style={{ width: `${animatedWidth}%` }}
        />
        <div
          className={cn(
            'absolute inset-0 rounded-full shimmer',
            barColor
          )}
        />
      </div>

      <span className="w-8 text-right text-sm font-semibold tabular-nums">
        {score.toFixed(1)}
      </span>
    </div>
  )
}
