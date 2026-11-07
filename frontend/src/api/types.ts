export interface ErrorBody {
  status: 'error'
  message?: string
}

export interface SuccessBody {
  status: 'success'
  message?: string
}

export interface MachineNode {
  name: string
  ip: string
  port: number
}

export interface Reservation {
  id: string
  username: string
  vm_count: number
  duration_minutes: number
  status: string
  created_at: number
  expires_at: number
  nodes: MachineNode[]
  packages: string[]
}

export interface ApiResult<T> {
  ok: boolean
  status: number
  body: T | null
}
