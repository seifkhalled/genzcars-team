'use client'

import { useEffect, useState, useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { MessageCircle, BarChart3, Search, TrendingUp, Shield, Car, MapPin, Users } from 'lucide-react'
import Link from 'next/link'
import { useChatStore } from '@/store/chatStore'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface SiteStats {
  total_ads: number
  total_cities: number
  total_users: number
  total_chat_sessions: number
}

function AnimatedCounter({ target, suffix = '' }: { target: number; suffix?: string }) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })

  useEffect(() => {
    if (!inView) return
    const duration = 2000
    const steps = 60
    const increment = target / steps
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= target) {
        setCount(target)
        clearInterval(timer)
      } else {
        setCount(Math.floor(current))
      }
    }, duration / steps)
    return () => clearInterval(timer)
  }, [inView, target])

  return <span ref={ref}>{count.toLocaleString()}{suffix}</span>
}

const features = [
  {
    icon: Search,
    title: 'Smart Car Search',
    description: 'Find exactly what you need with AI-powered semantic search across thousands of listings.',
    link: '/search',
  },
  {
    icon: BarChart3,
    title: 'AI Comparison',
    description: 'Get detailed head-to-head analysis with price insights, reliability scores, and personalized recommendations.',
    link: '/compare',
  },
  {
    icon: MessageCircle,
    title: 'AI Chat Assistant',
    description: 'Ask questions, get advice, and find cars naturally — like talking to a expert friend.',
    action: 'openChat' as const,
  },
  {
    icon: TrendingUp,
    title: 'Price Analysis',
    description: 'Know if a listing is fairly priced with AI-driven market analysis and price history.',
    link: '#',
  },
]

export function AIShowcase() {
  const { open: openChat } = useChatStore()
  const headerRef = useRef<HTMLDivElement>(null)
  const headerInView = useInView(headerRef, { once: true })
  const [stats, setStats] = useState<SiteStats | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/analytics/stats`)
      .then((res) => res.json())
      .then(setStats)
      .catch(() => {})
  }, [])

  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <motion.div
        ref={headerRef}
        initial={{ opacity: 0, y: 20 }}
        animate={headerInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.5 }}
        className="text-center mb-12"
      >
        <h2 className="text-3xl font-bold text-text-primary mb-3">
          What Can AI Do For You?
        </h2>
        <p className="text-text-muted max-w-xl mx-auto">
          Our AI engine works across the entire platform to help you make smarter car decisions.
        </p>
      </motion.div>

      {/* Stat counters — real data from database */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
        {[
          { label: 'Cars Listed', key: 'total_ads' as const, icon: Car },
          { label: 'Cities Covered', key: 'total_cities' as const, icon: MapPin },
          { label: 'AI Conversations', key: 'total_chat_sessions' as const, icon: MessageCircle },
          { label: 'Registered Users', key: 'total_users' as const, icon: Users },
        ].map((stat, idx) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 16 }}
            animate={headerInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.1 + idx * 0.1, duration: 0.4 }}
            className="text-center p-4 rounded-xl bg-surface border border-surface-border"
          >
            <stat.icon className="w-5 h-5 text-primary-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-text-primary tabular-nums">
              {stats ? <AnimatedCounter target={stats[stat.key]} suffix="+" /> : '—'}
            </p>
            <p className="text-xs text-text-muted mt-1">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {features.map((feature, idx) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 16 }}
            animate={headerInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.3 + idx * 0.1, duration: 0.4 }}
          >
            {feature.action === 'openChat' ? (
              <button
                onClick={() => openChat()}
                className="group w-full text-left p-5 rounded-xl bg-surface border border-surface-border hover:border-primary-500/30 hover:shadow-lg hover:shadow-primary-500/5 transition-all duration-300"
              >
                <feature.icon className="w-6 h-6 text-primary-500 mb-3 group-hover:scale-110 transition-transform" />
                <h3 className="font-semibold text-text-primary mb-1.5">{feature.title}</h3>
                <p className="text-sm text-text-muted leading-relaxed">{feature.description}</p>
              </button>
            ) : (
              <Link
                href={feature.link!}
                className="group block p-5 rounded-xl bg-surface border border-surface-border hover:border-primary-500/30 hover:shadow-lg hover:shadow-primary-500/5 transition-all duration-300"
              >
                <feature.icon className="w-6 h-6 text-primary-500 mb-3 group-hover:scale-110 transition-transform" />
                <h3 className="font-semibold text-text-primary mb-1.5">{feature.title}</h3>
                <p className="text-sm text-text-muted leading-relaxed">{feature.description}</p>
              </Link>
            )}
          </motion.div>
        ))}
      </div>
    </section>
  )
}
