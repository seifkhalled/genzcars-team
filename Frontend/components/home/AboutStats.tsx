'use client'

import { useEffect, useState } from 'react'
import { Car, MapPin, MessageCircle, Users } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface SiteStats {
  total_ads: number
  total_cities: number
  total_users: number
  total_chat_sessions: number
}

export function AboutStats() {
  const [stats, setStats] = useState<SiteStats | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/analytics/stats`)
      .then((res) => res.json())
      .then(setStats)
      .catch(() => {})
  }, [])

  const items = [
    { label: 'Cars Listed', value: stats?.total_ads, icon: Car },
    { label: 'Cities Covered', value: stats?.total_cities, icon: MapPin },
    { label: 'AI Conversations', value: stats?.total_chat_sessions, icon: MessageCircle },
    { label: 'Registered Users', value: stats?.total_users, icon: Users },
  ]

  return (
    <section className="max-w-7xl mx-auto px-4 -mt-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {items.map((item) => (
          <div key={item.label} className="bg-surface rounded-xl border border-surface-border p-6 text-center shadow-sm">
            <item.icon className="w-5 h-5 text-primary-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-primary-500">
              {item.value != null ? `${item.value.toLocaleString()}+` : '—'}
            </p>
            <p className="text-sm text-text-muted mt-1">{item.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
