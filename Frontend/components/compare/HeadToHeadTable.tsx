'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, XCircle, Minus } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { cn, formatPrice } from '@/lib/utils'
import type { CarAnalysis } from '@/types/compare'

interface HeadToHeadTableProps {
  cars: CarAnalysis[]
}

interface RowDef {
  labelKey: string
  getValue: (car: CarAnalysis) => string | number
  compare: (values: (string | number)[]) => number[]
  isNumeric?: boolean
  lowerIsBetter?: boolean
}

export default function HeadToHeadTable({ cars }: HeadToHeadTableProps) {
  const t = useTranslations('Compare')

  const rows: RowDef[] = [
    {
      labelKey: 'price',
      getValue: (c) => c.price,
      compare: (values) => {
        const nums = values.map((v) => (typeof v === 'number' ? v : 0))
        const best = Math.min(...nums)
        return nums.map((n) => (n === best ? 1 : 0))
      },
      isNumeric: true,
      lowerIsBetter: true,
    },
    {
      labelKey: 'year',
      getValue: (c) => c.year,
      compare: (values) => {
        const nums = values.map((v) => (typeof v === 'number' ? v : 0))
        const best = Math.max(...nums)
        return nums.map((n) => (n === best ? 1 : 0))
      },
      isNumeric: true,
    },
    {
      labelKey: 'condition',
      getValue: (c) => c.condition,
      compare: (values) => {
        const rank: Record<string, number> = { new: 2, used: 1 }
        const nums = values.map((v) => rank[String(v)] ?? 0)
        const max = Math.max(...nums)
        return nums.map((n) => (n === max ? 1 : 0))
      },
    },
    {
      labelKey: 'spareParts',
      getValue: (c) => c.spare_parts_availability ?? '-',
      compare: (values) => {
        const rank: Record<string, number> = {
          Abundant: 3, Available: 2, Limited: 1, Scarce: 0,
        }
        const nums = values.map((v) => rank[String(v)] ?? 0)
        const max = Math.max(...nums)
        return nums.map((n) => (n === max && max > 0 ? 1 : 0))
      },
    },
    {
      labelKey: 'serviceCenters',
      getValue: (c) => c.service_centers_egypt ?? '-',
      compare: (values) => {
        const rank: Record<string, number> = {
          Many: 3, Adequate: 2, Few: 1, None: 0,
        }
        const nums = values.map((v) => rank[String(v)] ?? 0)
        const max = Math.max(...nums)
        return nums.map((n) => (n === max && max > 0 ? 1 : 0))
      },
    },
  ]

  const carColors = ['#3b5bdb', '#f97316', '#16a34a']

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="p-3 text-left font-medium text-text-secondary" />
            {cars.map((car, idx) => (
              <th
                key={car.ad_id}
                className={cn(
                  'p-3 text-center font-semibold',
                  idx === 0 && 'text-primary-500',
                  idx === 1 && 'text-orange-500',
                  idx === 2 && 'text-green-500',
                )}
              >
                {car.brand} {car.model}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const values = cars.map(row.getValue)
            const winners = row.compare(values)

            if (row.isNumeric) {
              const nums = values.map((v) => (typeof v === 'number' ? v : 0))
              const max = Math.max(...nums)
              const min = Math.min(...nums)
              const range = max - min || 1

              return (
                <motion.tr
                  key={row.labelKey}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: rows.indexOf(row) * 0.05, duration: 0.3 }}
                  className="border-b border-surface-border"
                >
                  <td className="p-3 font-medium text-text-secondary whitespace-nowrap">
                    {t(row.labelKey)}
                  </td>
                  {nums.map((val, idx) => {
                    const isWinner = winners[idx] === 1
                    const barPercent = ((val - min) / range) * 100
                    const isBest = row.lowerIsBetter ? val === min : val === max

                    return (
                      <td key={idx} className="p-3">
                        <div className="flex flex-col items-center gap-1">
                          <AnimatedBar
                            value={val}
                            percent={barPercent}
                            color={carColors[idx % carColors.length]}
                            isWinner={isWinner}
                            isBest={isBest}
                            lowerIsBetter={row.lowerIsBetter}
                          />
                        </div>
                      </td>
                    )
                  })}
                </motion.tr>
              )
            }

            return (
              <motion.tr
                key={row.labelKey}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: rows.indexOf(row) * 0.05, duration: 0.3 }}
                className="border-b border-surface-border"
              >
                <td className="p-3 font-medium text-text-secondary whitespace-nowrap">
                  {t(row.labelKey)}
                </td>
                {values.map((val, idx) => {
                  const isWinner = winners[idx] === 1
                  return (
                    <td
                      key={idx}
                      className={cn(
                        'p-3 text-center transition-colors',
                        isWinner && 'relative'
                      )}
                    >
                      {isWinner && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="absolute inset-0 rounded-lg bg-primary-500/5"
                          style={{ boxShadow: 'inset 0 0 20px rgba(59,130,246,0.08)' }}
                        />
                      )}
                      <span className="relative inline-flex items-center gap-1.5">
                        {isWinner ? (
                          <CheckCircle className="h-4 w-4 shrink-0 text-green-600" />
                        ) : (
                          <XCircle className="h-4 w-4 shrink-0 text-text-muted/40" />
                        )}
                        {val}
                      </span>
                    </td>
                  )
                })}
              </motion.tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function AnimatedBar({
  value, percent, color, isWinner, isBest, lowerIsBetter,
}: {
  value: number
  percent: number
  color: string
  isWinner: boolean
  isBest: boolean
  lowerIsBetter?: boolean
}) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => setWidth(percent), 150)
    return () => clearTimeout(timer)
  }, [percent])

  const formatted = value >= 10000
    ? `${(value / 1000).toFixed(0)}k EGP`
    : value.toLocaleString()

  return (
    <div className="flex flex-col items-center w-full gap-1">
      <span className={cn(
        'text-sm font-semibold tabular-nums',
        isWinner ? 'text-green-700' : 'text-text-primary'
      )}>
        {formatted}
      </span>
      <div className="relative w-full h-2 rounded-full bg-surface-border overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${width}%` }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
          className="h-full rounded-full"
          style={{
            backgroundColor: isBest ? '#16a34a' : color,
            opacity: 0.7,
          }}
        />
      </div>
      <span className="text-[10px] text-text-muted uppercase tracking-wider">
        {isBest ? (lowerIsBetter ? 'Best Value' : 'Best') : ''}
      </span>
    </div>
  )
}
