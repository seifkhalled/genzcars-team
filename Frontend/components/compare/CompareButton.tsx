'use client'

import { useState } from 'react'
import { Plus, Check } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/Button'
import { useCompareStore } from '@/store/compareStore'
import type { Ad } from '@/types/ad'

interface CompareButtonProps {
  ad: Ad
}

export default function CompareButton({ ad }: CompareButtonProps) {
  const t = useTranslations('Compare')
  const { addAd: addCar, removeAd: removeCar, isSelected: isInCompare } = useCompareStore()
  const selected = isInCompare(ad.id)
  const [showToast, setShowToast] = useState(false)

  function handleToggle() {
    if (selected) {
      removeCar(ad.id)
      return
    }

    const added = addCar(ad)
    if (!added) {
      setShowToast(true)
      setTimeout(() => setShowToast(false), 3000)
    }
  }

  return (
    <div className="relative">
      <Button
        variant={selected ? 'default' : 'outline'}
        size="sm"
        onClick={handleToggle}
        className="gap-2"
      >
        {selected ? (
          <>
            <Check className="h-4 w-4" />
            {t('addedToCompare')}
          </>
        ) : (
          <>
            <Plus className="h-4 w-4" />
            {t('addToCompare')}
          </>
        )}
      </Button>

      {showToast && (
        <div className="absolute -top-12 left-1/2 z-50 -translate-x-1/2 whitespace-nowrap rounded-md bg-destructive px-3 py-1.5 text-sm text-destructive-foreground shadow-lg">
          {t('maxThreeCars')}
        </div>
      )}
    </div>
  )
}
