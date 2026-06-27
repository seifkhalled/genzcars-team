export interface User {
  id: string
  name: string
  email: string
  phone: string
  avatar_url: string | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  user: User
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  name: string
  email: string
  phone: string
  password: string
}
