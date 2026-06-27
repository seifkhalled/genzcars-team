'use client'

import Image from 'next/image'
import { ExternalLink, Plus, Check } from 'lucide-react'
import { cn, formatPrice } from '@/lib/utils'
import { useCompareStore } from '@/store/compareStore'
import type { Ad } from '@/types/ad'

interface ChatCarCardProps {
  car: Partial<Ad>
}

export function ChatCarCard({ car }: ChatCarCardProps) {
  const { addAd, removeAd, isSelected } = useCompareStore()
  const selected = isSelected(car.id || '')

  const handleCompare = () => {
    if (!car.id) return
    if (selected) {
      removeAd(car.id)
    } else {
      addAd(car as Ad)
    }
  }

  return (
    <div className="w-[200px] shrink-0 rounded-xl border border-surface-border bg-background-primary overflow-hidden flex flex-col">
      <div className="relative w-full h-28 bg-surface-secondary">
        {car.cover_image_url ? (
          <Image
            src={car.cover_image_url}
            alt={`${car.brand} ${car.model}`}
            fill
            className="object-cover"
            sizes="200px"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-text-secondary text-xs">
            No image
          </div>
        )}
      </div>

      <div className="p-3 flex flex-col gap-1.5 flex-1">
        <p className="text-sm font-semibold text-text-primary truncate">
          {car.brand} {car.model} {car.year || ''}
        </p>
        <p className="text-sm font-bold text-primary-500">
          {car.price != null ? `${formatPrice(car.price)} EGP` : '—'}
        </p>
        {car.city && (
          <p className="text-xs text-text-secondary truncate">{car.city}</p>
        )}
      </div>

      <div className="flex border-t border-surface-border divide-x divide-surface-border">
        {car.id && (
          <a
            href={`/ads/${car.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-1 py-2 text-xs font-medium text-text-secondary hover:text-primary-500 hover:bg-surface-secondary transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View Ad
          </a>
        )}
        <button
          onClick={handleCompare}
          disabled={!car.id}
          className={cn(
            'flex-1 flex items-center justify-center gap-1 py-2 text-xs font-medium transition-colors',
            selected
              ? 'text-primary-500 bg-primary-500/10'
              : 'text-text-secondary hover:text-primary-500 hover:bg-surface-secondary',
            !car.id && 'cursor-not-allowed opacity-50'
          )}
        >
          {selected ? (
            <Check className="w-3.5 h-3.5" />
          ) : (
            <Plus className="w-3.5 h-3.5" />
          )}
          {selected ? 'Added' : 'Compare'}
        </button>
      </div>
    </div>
  )
}
