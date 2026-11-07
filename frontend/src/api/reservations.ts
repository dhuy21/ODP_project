import { requestJson } from './http'
import type { ErrorBody, Reservation, SuccessBody } from './types'

export interface ReservationDetail extends SuccessBody {
  reservation?: Reservation
}

export function reservationDetail(reservationId: string) {
  return requestJson<ReservationDetail | ErrorBody>(
    `/api/reservations/${encodeURIComponent(reservationId)}`,
  )
}

export function releaseReservation(reservationId: string) {
  return requestJson<SuccessBody | ErrorBody>(
    `/api/reservations/${encodeURIComponent(reservationId)}/release`,
    { method: 'POST' },
  )
}
