export interface AdImage {
  id: string
  url: string
  order_index: number
}

export interface Ad {
  id: string
  user_id: string
  brand: string
  model: string
  year: number
  price: number
  condition: string
  km_driven: number
  fuel_type: string
  transmission: string
  body_type: string
  color: string
  city: string
  cc_range: string
  description: string
  special_conditions: string | null
  is_active: boolean
  cover_image_url: string
  images: AdImage[]
  views_count: number
  created_at: string
  updated_at: string
}

export interface AdListResponse {
  ads: Ad[]
  total: number
  page: number
  limit: number
  total_pages: number
}

export interface AdFilters {
  brand?: string
  price_min?: number
  price_max?: number
  city?: string
  condition?: string
  fuel_type?: string
  transmission?: string
  body_type?: string
  year_min?: number
  year_max?: number
  sort?: string
  page?: number
  limit?: number
}

export interface SearchResponse {
  ads: Ad[]
  query: string
  total: number
}
