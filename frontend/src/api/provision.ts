import { requestJson } from './http'
import type { ErrorBody, MachineNode, SuccessBody } from './types'

export interface ProvisionSuccess extends SuccessBody {
  reservation_id: string
  nodes: MachineNode[]
}

export function provision(vmCount: number, duration: number, password: string, packages: string) {
  return requestJson<ProvisionSuccess | ErrorBody>('/api/provision', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      vm_count: vmCount,
      duration,
      password,
      packages,
    }),
  })
}
