'use client'

import { CheckCircle, XCircle, Minus } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { cn, formatPrice, formatKm } from '@/lib/utils'
import type { CarAnalysis } from '@/types/compare'

interface HeadToHeadTableProps {
  cars: CarAnalysis[]
}

interface RowDef {
  labelKey: string
  getValue: (car: CarAnalysis) => string | number
  compare: (values: (string | number)[]) => number[]
}

function pickWinners(values: (string | number)[]): number[] {
  const nums = values.map((v) => {
    if (typeof v === 'number') return v
    const parsed = parseFloat(String(v).replace(/[^0-9.]/g, ''))
    return isNaN(parsed) ? 0 : parsed
  })

  // Price: lower is better. Everything else: higher is better (or same).
  // We need to know which row this is. We'll handle via compare function.
  return []
}

export default function HeadToHeadTable({ cars }: HeadToHeadTableProps) {
  const t = useTranslations('Compare')

  const rows: RowDef[] = [
    {
      labelKey: 'price',
      getValue: (c) => formatPrice(c.price),
      compare: (values) => {
        const nums = values.map((v) => {
          if (typeof v === 'number') return v
          return parseFloat(String(v).replace(/[^0-9.]/g, '')) || 0
        })
        const min = Math.min(...nums)
        return nums.map((n) => (n === min ? 1 : 0))
      },
    },
    {
      labelKey: 'year',
      getValue: (c) => c.year,
      compare: (values) => {
        const nums = values.map((v) => (typeof v === 'number' ? v : 0))
        const max = Math.max(...nums)
        return nums.map((n) => (n === max ? 1 : 0))
      },
    },
    {
      labelKey: 'kmDriven',
      getValue: (c) => formatKm(c.kmDriven),
      compare: (values) => {
        const nums = values.map((v) => {
          if (typeof v === 'number') return v
          return parseFloat(String(v).replace(/[^0-9.]/g, '')) || 0
        })
        const min = Math.min(...nums)
        return nums.map((n) => (n === min ? 1 : 0))
      },
    },
    {
      labelKey: 'condition',
      getValue: (c) => c.condition,
      compare: (values) => {
        const rank: Record<string, number> = {
          Excellent: 5,
          Good: 4,
          Fair: 3,
          Poor: 2,
          Bad: 1,
        }
        const nums = values.map((v) => rank[String(v)] ?? 0)
        const max = Math.max(...nums)
        return nums.map((n) => (n === max ? 1 : 0))
      },
    },
    {
      labelKey: 'fuelType',
      getValue: (c) => c.fuelType,
      compare: () => [],
    },
    {
      labelKey: 'transmission',
      getValue: (c) => c.transmission,
      compare: () => [],
    },
    {
      labelKey: 'spareParts',
      getValue: (c) => c.sparePartsAvailability ?? '-',
      compare: (values) => {
        const rank: Record<string, number> = {
          Abundant: 3,
          Available: 2,
          Limited: 1,
          Scarce: 0,
        }
        const nums = values.map((v) => rank[String(v)] ?? 0)
        const max = Math.max(...nums)
        return nums.map((n) => (n === max && max > 0 ? 1 : 0))
      },
    },
    {
      labelKey: 'serviceCenters',
      getValue: (c) => c.serviceCenterAvailability ?? '-',
      compare: (values) => {
        const rank: Record<string, number> = {
          Many: 3,
          Adequate: 2,
          Few: 1,
          None: 0,
        }
        const nums = values.map((v) => rank[String(v)] ?? 0)
        const max = Math.max(...nums)
        return nums.map((n) => (n === max && max > 0 ? 1 : 0))
      },
    },
  ]

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="p-3 text-left font-medium text-muted-foreground" />
            {cars.map((car, idx) => (
              <th
                key={car.carId}
                className={cn(
                  'p-3 text-center font-semibold',
                  idx === 0 && 'text-primary-500',
                  idx === 1 && 'text-orange-500',
                  idx === 2 && 'text-green-500',
                )}
              >
                {car.carName}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const values = cars.map(row.getValue)
            const winners = row.compare(values)

            return (
              <tr key={row.labelKey} className="border-b border-border">
                <td className="p-3 font-medium text-muted-foreground">
                  {t(row.labelKey)}
                </td>
                {values.map((val, idx) => {
                  const isWinner = winners[idx] === 1

                  return (
                    <td
                      key={idx}
                      className={cn(
                        'p-3 text-center transition-colors',
                        isWinner && 'bg-green-50',
                      )}
                    >
                      <span className="inline-flex items-center gap-1.5">
                        {winners.length > 0 && (
                          <>
                            {isWinner ? (
                              <CheckCircle className="h-4 w-4 shrink-0 text-green-600" />
                            ) : (
                              <XCircle className="h-4 w-4 shrink-0 text-muted-foreground/40" />
                            )}
                          </>
                        )}
                        {val}
                      </span>
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
