'use client'

import Link from 'next/link'
import { Trophy, Award } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/Button'
import { formatPrice } from '@/lib/utils'
import type { Verdict, CarAnalysis } from '@/types/compare'

interface VerdictCardProps {
  verdict: Verdict
  cars: CarAnalysis[]
}

export default function VerdictCard({ verdict, cars }: VerdictCardProps) {
  const t = useTranslations('Compare')

  const winner = cars.find((c) => c.ad_id === verdict.winner_ad_id)
  const runnerUp = cars.find((c) => c.ad_id === verdict.runner_up_ad_id)

  if (!winner) return null

  return (
    <div className="space-y-4">
      {/* Winner */}
      <div className="rounded-lg border-2 border-primary-500 p-5 shadow-sm shadow-primary-500/10">
        <div className="mb-3 flex items-center gap-2">
          <Trophy className="h-5 w-5 text-primary-500" />
          <span className="rounded-md bg-primary-500/10 px-2.5 py-0.5 text-xs font-semibold text-primary-500">
            {t('recommended')}
          </span>
        </div>

        <h3 className="text-lg font-bold">{winner.brand} {winner.model}</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {formatPrice(winner.price)}
        </p>

        <div className="mt-3 flex items-center gap-2">
          <span className="text-xs text-muted-foreground">{t('confidence')}:</span>
          <span className="text-sm font-semibold">{verdict.confidence === 'high' ? '90%' : verdict.confidence === 'medium' ? '70%' : '50%'}</span>
        </div>

        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {verdict.reasoning}
        </p>

        <Link href={`/cars/${winner.ad_id}`}>
          <Button className="mt-4 w-full">{t('viewDetails')}</Button>
        </Link>
      </div>

      {/* Runner-up */}
      {runnerUp && (
        <div className="rounded-lg border border-muted p-4">
          <div className="mb-2 flex items-center gap-2">
            <Award className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">
              {t('runnerUp')}
            </span>
          </div>

          <h4 className="text-base font-semibold">{runnerUp.brand} {runnerUp.model}</h4>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {formatPrice(runnerUp.price)}
          </p>

          <Link href={`/cars/${runnerUp.ad_id}`}>
            <Button variant="outline" className="mt-3 w-full">{t('viewDetails')}</Button>
          </Link>
        </div>
      )}
    </div>
  )
}
