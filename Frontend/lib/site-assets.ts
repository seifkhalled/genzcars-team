const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const BUCKET = 'site-assets'

export function getSiteAssetUrl(filename: string): string {
  if (!SUPABASE_URL) return `/${filename}`
  return `${SUPABASE_URL}/storage/v1/object/public/${BUCKET}/${filename}`
}
