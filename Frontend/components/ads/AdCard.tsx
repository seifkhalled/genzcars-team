'use client'

import { useState } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { Heart, MapPin, Gauge, Fuel, Settings } from 'lucide-react'
import { cn, formatPrice, formatKm, formatViews, getConditionBadge } from '@/lib/utils'
import { useCompareStore } from '@/store/compareStore'
import type { Ad } from '@/types/ad'

interface AdCardProps {
  ad: Ad
}

export function AdCard({ ad }: AdCardProps) {
  const router = useRouter()
  const { addAd, removeAd, isSelected } = useCompareStore()
  const selected = isSelected(ad.id)
  const badge = getConditionBadge(ad.condition)
  const [isSaved, setIsSaved] = useState(false)

  return (
    <div
      className="group bg-surface rounded-xl border border-surface-border overflow-hidden cursor-pointer transition-all hover:shadow-lg"
      onClick={() => router.push(`/ads/${ad.id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') router.push(`/ads/${ad.id}`) }}
    >
      <div className="relative aspect-[16/9] bg-surface-secondary">
        <Image
          src={ad.cover_image_url || 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22800%22 height=%22600%22%3E%3Crect fill=%22%23e2e8f0%22 width=%22800%22 height=%22600%22/%3E%3Ctext fill=%22%2394a3b8%22 font-family=%22Arial%22 font-size=%2224%22 x=%22400%22 y=%22300%22 text-anchor=%22middle%22 dy=%22.3em%22%3ENo Image%3C/text%3E%3C/svg%3E'}
          alt={`${ad.brand} ${ad.model} ${ad.year}`}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-300"
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        />
        <div className="absolute top-2 left-2">
          <span
            className="px-2 py-1 rounded-md text-xs font-medium"
            style={{ backgroundColor: badge.bg, color: badge.text }}
          >
            {badge.label}
          </span>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); setIsSaved(!isSaved) }}
          className="absolute top-2 right-2 p-2 bg-white/80 backdrop-blur-sm rounded-full hover:bg-white transition-colors"
          aria-label={isSaved ? 'Remove from saved' : 'Save'}
        >
          <Heart className={cn('w-4 h-4', isSaved ? 'fill-danger text-danger' : 'text-text-secondary')} />
        </button>
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-text-primary truncate">
          {ad.brand} {ad.model} {ad.year}
        </h3>
        <p className="text-lg font-bold text-primary-500 mt-1">
          {formatPrice(ad.price)} EGP
        </p>
        <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
          <span className="flex items-center gap-1">
            <Gauge className="w-3.5 h-3.5" />
            {formatKm(ad.km_driven)}
          </span>
          <span className="flex items-center gap-1">
            <Fuel className="w-3.5 h-3.5" />
            {ad.fuel_type}
          </span>
          <span className="flex items-center gap-1">
            <Settings className="w-3.5 h-3.5" />
            {ad.transmission}
          </span>
          <span className="flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5" />
            {ad.city}
          </span>
        </div>
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-surface-border">
          <button
            onClick={(e) => {
              e.stopPropagation()
              selected ? removeAd(ad.id) : addAd(ad)
            }}
            className={cn(
              'text-xs font-medium transition-colors',
              selected ? 'text-primary-500' : 'text-text-muted hover:text-primary-500'
            )}
          >
            {selected ? 'Added to Compare' : 'Add to Compare'}
          </button>
          <span className="text-xs text-text-muted flex items-center gap-1">
            {formatViews(ad.views_count)} views
          </span>
        </div>
      </div>
    </div>
  )
}
