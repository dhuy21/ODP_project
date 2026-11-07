import type { ApiResult, ErrorBody, SuccessBody } from './types'

async function readJson<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T
  } catch {
    return null
  }
}

export async function requestJson<T>(input: string, init?: RequestInit): Promise<ApiResult<T>> {
  const response = await fetch(input, init)
  return { ok: response.ok, status: response.status, body: await readJson<T>(response) }
}

export function isSuccess<T extends SuccessBody>(
  result: ApiResult<T | ErrorBody>,
): result is ApiResult<T> & { body: T } {
  return result.ok && result.body !== null && result.body.status === 'success'
}
