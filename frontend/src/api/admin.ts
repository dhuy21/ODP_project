import { requestJson } from './http'
import type { ErrorBody, Reservation, SuccessBody } from './types'

export interface AdminOverview extends SuccessBody {
  total_users: number
  admin_count: number
  user_count: number
  active_reservations: number
  total_containers: number
  available_containers: number
}

export function adminOverview() {
  return requestJson<AdminOverview | ErrorBody>('/api/admin/overview')
}

export interface AdminAccount {
  username: string
  email: string
  role: string
  created_at: string
  reservation_count: number
}

export interface AdminUserList extends SuccessBody {
  users: AdminAccount[]
}

export function adminUsers() {
  return requestJson<AdminUserList | ErrorBody>('/api/admin/users')
}

export function createAdminUser(username: string, email: string, password: string) {
  return requestJson<SuccessBody | ErrorBody>('/api/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })
}

export function deleteAdminUser(username: string) {
  return requestJson<SuccessBody | ErrorBody>(
    `/api/admin/users/${encodeURIComponent(username)}`,
    { method: 'DELETE' },
  )
}

export function updateAdminRole(username: string, role: 'user' | 'admin') {
  return requestJson<SuccessBody | ErrorBody>(
    `/api/admin/users/${encodeURIComponent(username)}/role`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    },
  )
}

export interface AdminReservationList extends SuccessBody {
  reservations: Reservation[]
}

export function adminReservations() {
  return requestJson<AdminReservationList | ErrorBody>('/api/admin/reservations')
}

export function deleteAdminReservation(reservationId: string) {
  return requestJson<SuccessBody | ErrorBody>(
    `/api/admin/reservations/${encodeURIComponent(reservationId)}`,
    { method: 'DELETE' },
  )
}

export interface AdminPoolNode {
  name: string
  ip: string
  port: number
  status: string
  owner: string | null
  expiry: number
}

export interface AdminPoolList extends SuccessBody {
  nodes: AdminPoolNode[]
}

export function adminPool() {
  return requestJson<AdminPoolList | ErrorBody>('/api/admin/pool')
}

export interface PoolRecovered extends SuccessBody {
  restarted: number
}

export function recoverPool() {
  return requestJson<PoolRecovered | ErrorBody>('/api/admin/pool/recover', { method: 'POST' })
}
