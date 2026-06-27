'use client'

import { useLocale } from 'next-intl'
import { usePathname, useRouter } from '@/lib/navigation'
import { Button } from './Button'

export function LanguageToggle() {
  const locale = useLocale()
  const router = useRouter()
  const pathname = usePathname()

  const toggle = () => {
    const next = locale === 'en' ? 'ar' : 'en'
    router.replace(pathname, { locale: next })
  }

  return (
    <Button variant="ghost" size="sm" onClick={toggle}>
      {locale === 'en' ? 'العربية' : 'English'}
    </Button>
  )
}
