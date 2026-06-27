export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'text' | 'cars' | 'similar_cars' | 'price_analysis' | 'new_match' | 'status' | 'error'
  cars?: any[]
  similar_cars?: any[]
  price_analysis?: any
  created_at?: string
}

export interface SSEEvent {
  type: 'token' | 'status' | 'cars' | 'similar_cars' | 'price_analysis' | 'new_match' | 'error' | 'done'
  content: any
}

export interface UserPreferences {
  budget_min?: number | null
  budget_max?: number | null
  preferred_brands?: string[]
  preferred_body_types?: string[]
  preferred_fuel_types?: string[]
  preferred_transmission?: string | null
  preferred_cities?: string[]
  max_km_driven?: number | null
  year_min?: number | null
  year_max?: number | null
  use_case?: string | null
  is_seller?: boolean
  seller_car_brand?: string | null
  seller_car_model?: string | null
  seller_car_year?: number | null
  seller_asking_price?: number | null
}

export interface ChatHistory {
  session_token: string
  messages: {
    role: string
    content: string
    node_used?: string
    created_at: string
  }[]
  preferences: UserPreferences
  turn_count: number
}

export interface ChatRequest {
  session_token: string
  message: string
  user_id?: string | null
  context_ad_id?: string | null
}
