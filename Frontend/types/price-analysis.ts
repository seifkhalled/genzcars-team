export interface PriceAnalysisRequest {
  make: string
  model: string
  year: number
}

export interface PriceAnalysisReport {
  make: string
  model: string
  year: number
  estimated_range: {
    low: number
    high: number
    average: number
  }
  median?: number
  confidence: 'high' | 'medium' | 'low' | 'none'
  summary: string
  currency: string
  sample_count?: number
  sources: { title: string; url: string; source?: string }[]
}
