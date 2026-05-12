import type { AuthUser } from '@/types'

const TOKEN_KEY = 'kuaai_token'
const USER_KEY = 'kuaai_user'

export function saveSession(token: string, user: AuthUser) {
  document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${60 * 60 * 24}`
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`
  localStorage.removeItem(USER_KEY)
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  const match = document.cookie.match(new RegExp(`${TOKEN_KEY}=([^;]+)`))
  return match ? match[1] : null
}

export function getUser(): AuthUser | null {
  if (typeof window === 'undefined') return null
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}
