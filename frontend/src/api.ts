export class ApiError extends Error { constructor(public status: number, message: string) { super(message) } }

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: 'include' })
  if (response.status === 401 && path !== '/auth/refresh') {
    const refreshed = await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include' })
    if (refreshed.ok) return api<T>(path, init)
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail || body.message || '请求失败，请稍后再试')
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export type Student = { id: string; name: string; display_name: string; grade: number; preferences: Record<string, unknown>; active: boolean }
export type TutorDecision = { reply: string; intent: string; knowledge_point_code?: string; result?: string; hint_count: number }

