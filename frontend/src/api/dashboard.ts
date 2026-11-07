import { requestJson } from './http'
import type { ErrorBody, Reservation, SuccessBody } from './types'

export interface PoolStatus extends SuccessBody {
  free: number
  allocated: number
  total: number
}

export interface ReservationList extends SuccessBody {
  reservations: Reservation[]
}

export function poolStatus() {
  return requestJson<PoolStatus | ErrorBody>('/api/pool/status')
}

export function userReservations(username: string) {
  return requestJson<ReservationList | ErrorBody>(
    `/api/users/${encodeURIComponent(username)}/reservations`,
  )
}
