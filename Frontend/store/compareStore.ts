import { create } from 'zustand'
import type { Ad } from '@/types/ad'

interface CompareState {
  ads: Ad[]
  hydrated: boolean
  hydrate: () => void
  addAd: (ad: Ad) => boolean
  removeAd: (adId: string) => void
  clearAll: () => void
  isSelected: (adId: string) => boolean
}

export const useCompareStore = create<CompareState>((set, get) => ({
  ads: [],
  hydrated: false,

  hydrate: () => {
    if (get().hydrated) return
    if (typeof window === 'undefined') return
    try {
      const stored = sessionStorage.getItem('compare_ads')
      if (stored) {
        set({ ads: JSON.parse(stored), hydrated: true })
      } else {
        set({ hydrated: true })
      }
    } catch {
      set({ hydrated: true })
    }
  },

  addAd: (ad) => {
    const { ads } = get()
    if (ads.length >= 3) return false
    if (ads.some((a) => a.id === ad.id)) return false
    const updated = [...ads, ad]
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('compare_ads', JSON.stringify(updated))
    }
    set({ ads: updated })
    return true
  },

  removeAd: (adId) => {
    const updated = get().ads.filter((a) => a.id !== adId)
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('compare_ads', JSON.stringify(updated))
    }
    set({ ads: updated })
  },

  clearAll: () => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('compare_ads', JSON.stringify([]))
    }
    set({ ads: [] })
  },

  isSelected: (adId) => get().ads.some((a) => a.id === adId),
}))
