'use client'

import { useState } from 'react'
import Image from 'next/image'
import { ChevronLeft, ChevronRight, Expand } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Modal } from '@/components/ui/Modal'
import type { AdImage } from '@/types/ad'

const PLACEHOLDER = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22800%22 height=%22600%22%3E%3Crect fill=%22%23e2e8f0%22 width=%22800%22 height=%22600%22/%3E%3Ctext fill=%22%2394a3b8%22 font-family=%22Arial%22 font-size=%2224%22 x=%22400%22 y=%22300%22 text-anchor=%22middle%22 dy=%22.3em%22%3ENo Image%3C/text%3E%3C/svg%3E'

interface AdImageGalleryProps {
  images: AdImage[]
  coverImageUrl: string | null
}

export function AdImageGallery({ images, coverImageUrl }: AdImageGalleryProps) {
  const allImages = images.length > 0
    ? [...images].sort((a, b) => a.order_index - b.order_index)
    : coverImageUrl
      ? [{ id: 'cover', url: coverImageUrl, order_index: 0 }]
      : []

  const [selectedIndex, setSelectedIndex] = useState(0)
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const currentImage = allImages[selectedIndex]

  const goTo = (index: number) => {
    setSelectedIndex(Math.max(0, Math.min(index, allImages.length - 1)))
  }

  if (allImages.length === 0) {
    return (
      <div className="relative aspect-[16/10] bg-surface-secondary rounded-xl overflow-hidden flex items-center justify-center">
        <Image
          src={PLACEHOLDER}
          alt="No image"
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, 60vw"
          priority
        />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div
        className="relative aspect-[16/10] bg-surface-secondary rounded-xl overflow-hidden group cursor-pointer"
        onClick={() => setLightboxOpen(true)}
      >
        <Image
          src={currentImage.url}
          alt="Car image"
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, 60vw"
          priority
        />
        <button
          className="absolute top-3 right-3 p-2 bg-black/40 hover:bg-black/60 rounded-lg text-white transition-colors opacity-0 group-hover:opacity-100"
          onClick={(e) => { e.stopPropagation(); setLightboxOpen(true) }}
          aria-label="Expand image"
        >
          <Expand className="w-5 h-5" />
        </button>
        {allImages.length > 1 && (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); goTo(selectedIndex - 1) }}
              className="absolute left-3 top-1/2 -translate-y-1/2 p-2 bg-white/80 hover:bg-white rounded-full shadow transition-all opacity-0 group-hover:opacity-100"
              aria-label="Previous image"
            >
              <ChevronLeft className="w-5 h-5 text-text-primary" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); goTo(selectedIndex + 1) }}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-white/80 hover:bg-white rounded-full shadow transition-all opacity-0 group-hover:opacity-100"
              aria-label="Next image"
            >
              <ChevronRight className="w-5 h-5 text-text-primary" />
            </button>
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-black/60 text-white text-xs px-3 py-1 rounded-full">
              {selectedIndex + 1} / {allImages.length}
            </div>
          </>
        )}
      </div>

      {allImages.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {allImages.map((img, i) => (
            <button
              key={img.id}
              onClick={() => setSelectedIndex(i)}
              className={cn(
                'relative flex-shrink-0 w-20 h-16 rounded-lg overflow-hidden border-2 transition-all',
                i === selectedIndex
                  ? 'border-primary-500 ring-1 ring-primary-500'
                  : 'border-transparent hover:border-surface-border'
              )}
            >
              <Image
                src={img.url}
                alt={`Thumbnail ${i + 1}`}
                fill
                className="object-cover"
                sizes="80px"
              />
            </button>
          ))}
        </div>
      )}

      <Modal
        isOpen={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
        className="max-w-4xl"
      >
        <div className="relative w-full aspect-[16/10]">
          <Image
            src={currentImage.url}
            alt="Car image fullscreen"
            fill
            className="object-contain"
            sizes="(max-width: 768px) 100vw, 80vw"
          />
        </div>
        {allImages.length > 1 && (
          <div className="flex items-center justify-between mt-4">
            <button
              onClick={() => goTo(selectedIndex - 1)}
              disabled={selectedIndex === 0}
              className="flex items-center gap-1 text-sm text-text-primary disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>
            <span className="text-sm text-text-muted">
              {selectedIndex + 1} / {allImages.length}
            </span>
            <button
              onClick={() => goTo(selectedIndex + 1)}
              disabled={selectedIndex === allImages.length - 1}
              className="flex items-center gap-1 text-sm text-text-primary disabled:opacity-40"
            >
              Next <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </Modal>
    </div>
  )
}
