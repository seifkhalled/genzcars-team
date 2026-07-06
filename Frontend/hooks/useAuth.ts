'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { useChatStore } from '@/store/chatStore'
import { useCompareStore } from '@/store/compareStore'
import { api } from '@/lib/api'
import type { User } from '@/types/auth'

export function useAuth() {
  const router = useRouter()
  const { user, isLoading, setUser, setLoading, clear } = useAuthStore()

  useEffect(() => {
    if (isLoading) {
      api.get<User>('/users/me')
        .then(setUser)
        .catch(() => clear())
    }
  }, [])

  const clearUserData = () => {
    localStorage.removeItem('chat_session_token')
    useChatStore.getState().clearMessages()
    useChatStore.getState().setSessionToken(null)
    useCompareStore.getState().clearAll()
  }

  const login = async (email: string, password: string) => {
    clearUserData()
    const res = await api.post<{ user: User }>('/auth/login', { email, password })
    setUser(res.user)
    return res.user
  }

  const register = async (data: { name: string; email: string; phone: string; password: string }) => {
    clearUserData()
    const res = await api.post<{ user: User }>('/auth/register', data)
    setUser(res.user)
    return res.user
  }

  const logout = async () => {
    try {
      await api.post('/auth/logout')
    } catch {}
    clearUserData()
    clear()
    router.push('/')
  }

  return { user, isLoading, login, register, logout, isAuthenticated: !!user }
}
