'use client'

import { TrendingUp, TrendingDown, Minus, BarChart3, Sparkles } from 'lucide-react'
import { formatPrice } from '@/lib/utils'
import type { CarAnalysis } from '@/types/compare'

interface MarketPriceCardProps {
  cars: CarAnalysis[]
}

export default function MarketPriceCard({ cars }: MarketPriceCardProps) {
  const hasData = cars.some((c) => c.market_price && c.market_price.estimated_range.high > 0)
  if (!hasData) return null

  return (
    <div className="bg-surface rounded-xl border border-surface-border p-6">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-5 h-5 text-primary-500" />
        <h2 className="text-lg font-semibold text-text-primary">Market Price Analysis</h2>
      </div>

      <div className={`grid grid-cols-1 ${cars.length === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-4`}>
        {cars.map((car) => {
          const mp = car.market_price
          const hasMp = mp && mp.estimated_range.high > 0
          const diff = hasMp ? car.price - mp!.estimated_range.average : 0
          const diffPercent = hasMp ? ((car.price / mp!.estimated_range.average - 1) * 100) : 0
          const isAbove = diff > 0
          const isBelow = diff < 0

          return (
            <div
              key={car.ad_id}
              className="p-4 bg-surface-secondary rounded-lg space-y-3"
            >
              <div className="flex items-center justify-between">
                <p className="font-semibold text-sm text-text-primary">
                  {car.brand} {car.model}
                </p>
                {hasMp && (
                  <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${
                    mp!.confidence === 'high'
                      ? 'bg-green-500/10 text-green-600'
                      : mp!.confidence === 'medium'
                        ? 'bg-yellow-500/10 text-yellow-600'
                        : 'bg-gray-500/10 text-gray-500'
                  }`}>
                    {mp!.confidence}
                  </span>
                )}
              </div>

              {hasMp ? (
                <>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-text-muted">Market Range</p>
                      <p className="font-medium text-text-primary">
                        {formatPrice(mp!.estimated_range.low)} — {formatPrice(mp!.estimated_range.high)}
                      </p>
                    </div>
                    <div>
                      <p className="text-text-muted">Market Average</p>
                      <p className="font-medium text-text-primary">
                        {formatPrice(mp!.estimated_range.average)}
                      </p>
                    </div>
                    <div>
                      <p className="text-text-muted">Median</p>
                      <p className="font-medium text-text-primary">
                        {formatPrice(mp!.median)}
                      </p>
                    </div>
                    <div>
                      <p className="text-text-muted">Listings</p>
                      <p className="font-medium text-text-primary">
                        {mp!.sample_count} cars
                      </p>
                    </div>
                  </div>

                  <div className={`flex items-center justify-between px-2 py-1.5 rounded-lg ${
                    isAbove ? 'bg-red-500/5' : isBelow ? 'bg-green-500/5' : 'bg-surface'
                  }`}>
                    <span className="text-xs text-text-muted">vs. Market Avg</span>
                    <span className={`flex items-center gap-1 text-xs font-medium ${
                      isAbove ? 'text-red-600' : isBelow ? 'text-green-600' : 'text-text-muted'
                    }`}>
                      {isAbove ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : isBelow ? (
                        <TrendingDown className="w-3 h-3" />
                      ) : (
                        <Minus className="w-3 h-3" />
                      )}
                      {isAbove ? '+' : ''}{formatPrice(Math.round(diff))} ({diffPercent.toFixed(0)}%)
                    </span>
                  </div>

                  {mp!.summary && (
                    <div className="flex items-start gap-1.5 pt-1 border-t border-surface-border">
                      <Sparkles className="w-3.5 h-3.5 text-primary-500 mt-0.5 shrink-0" />
                      <p className="text-xs text-text-muted leading-relaxed">{mp!.summary}</p>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-xs text-text-muted py-2">No market data available</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
