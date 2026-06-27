import { createSharedPathnamesNavigation } from 'next-intl/navigation'

export const locales = ['en', 'ar'] as const
export type Locale = (typeof locales)[number]

export const { useRouter, usePathname } = createSharedPathnamesNavigation({ locales })
