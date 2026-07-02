'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Car } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { getSiteAssetUrl } from '@/lib/site-assets'

const TAGLINES = [
  'Find Your Perfect Car',
  'AI-Powered Car Search',
  'Compare Any Two Cars',
  'Know the Fair Price',
  'Your AI Car Advisor',
]

export function HeroSection() {
  const t = useTranslations('home')
  const [taglineIndex, setTaglineIndex] = useState(0)
  const [searchFocused, setSearchFocused] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      setTaglineIndex((i) => (i + 1) % TAGLINES.length)
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  return (
    <section className="relative overflow-hidden bg-cover bg-center text-white" style={{ backgroundImage: `url('${getSiteAssetUrl('wallpaper.jpg')}')` }}>
      <div className="absolute inset-0 bg-black/40" />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2 mb-4 text-primary-100">
            <Car className="w-5 h-5" />
            <span className="text-sm font-medium uppercase tracking-wider">
              AI-Powered Car Marketplace
            </span>
          </div>

          <div className="h-16 md:h-20 mb-4">
            <AnimatePresence mode="wait">
              <motion.h1
                key={taglineIndex}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
                className="text-4xl md:text-5xl font-bold leading-tight"
              >
                {TAGLINES[taglineIndex]}
              </motion.h1>
            </AnimatePresence>
          </div>

          <p className="text-lg text-primary-100 mb-8">
            {t('hero_subtitle')}
          </p>

          <form action="/search" className="relative max-w-xl">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              name="q"
              placeholder={t('search_placeholder')}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              className="w-full h-14 pl-12 pr-4 rounded-xl bg-white text-gray-900 placeholder:text-gray-400 outline-none text-base shadow-lg transition-all duration-300"
              style={{
                boxShadow: searchFocused
                  ? '0 0 0 3px rgba(59,130,246,0.4), 0 0 20px rgba(59,130,246,0.15)'
                  : undefined,
              }}
            />
          </form>
        </div>
      </div>
    </section>
  )
}
