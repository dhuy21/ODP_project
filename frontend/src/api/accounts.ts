import { requestJson } from './http'
import type { ErrorBody, SuccessBody } from './types'

export interface RegisteredBody extends SuccessBody {
  message: string
}

export function register(username: string, email: string, password: string) {
  return requestJson<RegisteredBody | ErrorBody>('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })
}
