import { defineStore } from 'pinia'

import { isSuccess } from '../api/http'
import { currentSession } from '../api/session'

export const useSessionStore = defineStore('session', {
  state: () => ({
    username: '',
    role: '',
  }),
  getters: {
    signedIn: (state) => state.username !== '',
  },
  actions: {
    setUser(username: string, role: string) {
      this.username = username
      this.role = role
    },
    clear() {
      this.username = ''
      this.role = ''
    },
    async restore(): Promise<boolean> {
      try {
        const result = await currentSession()
        if (isSuccess(result) && result.body.user && result.body.role) {
          this.setUser(result.body.user, result.body.role)
          return true
        }
        if (result.status === 401) {
          this.clear()
          return true
        }
        return false
      } catch {
        return false
      }
    },
  },
})
