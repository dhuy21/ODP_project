import { requestJson } from './http'
import type { ErrorBody, SuccessBody } from './types'

export interface SessionBody extends SuccessBody {
  user: string
  role: string
}

function jsonPost(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export function login(username: string, password: string) {
  return requestJson<SessionBody | ErrorBody>('/api/login', jsonPost({ username, password }))
}

export function currentSession() {
  return requestJson<SessionBody | ErrorBody>('/api/session')
}

export function logout() {
  return requestJson<SuccessBody | ErrorBody>('/api/logout', { method: 'POST' })
}
