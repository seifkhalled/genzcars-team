'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { api } from '@/lib/api'

export default function SettingsPage() {
  const t = useTranslations('profile')
  const { user } = useAuth()
  const [name, setName] = useState(user?.name || '')
  const [phone, setPhone] = useState(user?.phone || '')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  if (!user) {
    return <div className="max-w-7xl mx-auto px-4 py-20 text-center text-text-secondary">Please sign in.</div>
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.patch('/users/me', { name, phone })
      setMessage('Saved!')
    } catch {
      setMessage('Error saving')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-text-primary mb-8">{t('settings')}</h1>

      <div className="space-y-6">
        <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <Input label="Email" value={user.email} disabled />
        <Input label={t('phone_placeholder')} value={phone} onChange={(e) => setPhone(e.target.value)} />

        <Button onClick={handleSave} isLoading={saving}>{t('save_changes')}</Button>

        {message && <p className="text-sm text-success">{message}</p>}
      </div>
    </div>
  )
}
