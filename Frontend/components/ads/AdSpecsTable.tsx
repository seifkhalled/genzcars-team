'use client'

import { useTranslations } from 'next-intl'
import { formatPrice, formatKm } from '@/lib/utils'
import type { Ad } from '@/types/ad'

interface AdSpecsTableProps {
  ad: Ad
}

const specRows = [
  { key: 'brand', labelKey: 'brand', formatter: (_: string, ad: Ad) => ad.brand },
  { key: 'model', labelKey: 'model', formatter: (_: string, ad: Ad) => ad.model },
  { key: 'year', labelKey: 'year', formatter: (_: string, ad: Ad) => String(ad.year) },
  { key: 'condition', labelKey: 'condition', formatter: (_: string, ad: Ad) => ad.condition },
  { key: 'price', labelKey: 'price', formatter: (_: string, ad: Ad) => `${formatPrice(ad.price)} EGP` },
  { key: 'km_driven', labelKey: 'km_driven', formatter: (t: string, ad: Ad) => `${formatKm(ad.km_driven)} km` },
  { key: 'fuel_type', labelKey: 'fuel_type', formatter: (_: string, ad: Ad) => ad.fuel_type },
  { key: 'transmission', labelKey: 'transmission', formatter: (_: string, ad: Ad) => ad.transmission },
  { key: 'body_type', labelKey: 'body_type', formatter: (_: string, ad: Ad) => ad.body_type },
  { key: 'color', labelKey: 'color', formatter: (_: string, ad: Ad) => ad.color },
  { key: 'cc_range', labelKey: 'cc_range', formatter: (_: string, ad: Ad) => ad.cc_range },
  { key: 'city', labelKey: 'city', formatter: (_: string, ad: Ad) => ad.city },
] as const

export function AdSpecsTable({ ad }: AdSpecsTableProps) {
  const t = useTranslations('ad')

  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-4">
      {specRows.map(({ key, labelKey, formatter }) => (
        <div key={key} className="flex flex-col gap-1">
          <span className="text-sm text-text-muted">{t(labelKey)}</span>
          <span className="text-sm font-medium text-text-primary capitalize">
            {formatter(t(labelKey), ad)}
          </span>
        </div>
      ))}
    </div>
  )
}
