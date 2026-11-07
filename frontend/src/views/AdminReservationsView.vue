<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { adminReservations, deleteAdminReservation } from '../api/admin'
import { isSuccess } from '../api/http'
import type { Reservation } from '../api/types'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import { formatUnixTime } from '../time'
import '../assets/dashboard.css'

const router = useRouter()
const session = useSessionStore()
const reservations = ref<Reservation[]>([])
const error = ref('')
const notice = ref('')
const pending = ref(true)
const confirming = ref('')
const deleting = ref(false)

function ownerOf(id: string) {
  return reservations.value.find((item) => item.id === id)?.username || 'unknown'
}

function askDelete(id: string) {
  if (deleting.value) {
    return
  }
  confirming.value = id
}

function cancelConfirm() {
  if (deleting.value) {
    return
  }
  confirming.value = ''
}

async function loadReservations() {
  const result = await adminReservations()
  if (result.status === 401) {
    session.clear()
    await router.push({ name: 'login' })
    return
  }
  if (!isSuccess(result)) {
    error.value = result.body?.message || 'Could not load reservations'
    return
  }
  error.value = ''
  reservations.value = Array.isArray(result.body.reservations) ? result.body.reservations : []
}

async function remove() {
  const id = confirming.value
  if (!id || deleting.value) {
    return
  }
  notice.value = ''
  deleting.value = true
  try {
    const result = await deleteAdminReservation(id)
    if (result.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(result)) {
      error.value = result.body?.message || 'Could not delete the reservation'
      return
    }
    error.value = ''
    notice.value = result.body.message || 'Reservation deleted'
    const row = reservations.value.find((item) => item.id === id)
    if (row) {
      row.status = 'deleted'
    }
    try {
      await loadReservations()
    } catch {
      error.value = 'Network error. Please try again.'
    }
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    deleting.value = false
    confirming.value = ''
  }
}

onMounted(async () => {
  try {
    await loadReservations()
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    pending.value = false
  }
})
</script>

<template>
  <div class="dashboard-shell">
    <SiteChrome current="admin">
      <main class="main-content">
        <div class="dashboard-page reservations-page">
          <RouterLink class="btn-back" :to="{ name: 'admin' }">
            <i class="fas fa-arrow-left"></i>
            <span>Back to Overview</span>
          </RouterLink>
          <div class="dashboard-header">
            <div class="header-content">
              <div class="welcome-section">
                <div class="welcome-icon"><i class="fas fa-clipboard-list"></i></div>
                <div>
                  <h1>All Reservations</h1>
                  <p class="welcome-subtitle">Monitor all reservation activities</p>
                </div>
              </div>
            </div>
          </div>
          <p v-if="notice" class="notice" role="status">{{ notice }}</p>
          <div v-if="confirming" class="delete-confirm">
            <p>
              Delete reservation {{ confirming }} for {{ ownerOf(confirming) }}? Containers still owned by that user are released, and the status becomes deleted.
            </p>
            <div class="delete-actions">
              <button class="btn-delete" type="button" :disabled="deleting" @click="remove">
                {{ deleting ? 'Deleting…' : 'Delete' }}
              </button>
              <button class="btn-form-cancel" type="button" :disabled="deleting" @click="cancelConfirm">
                Cancel
              </button>
            </div>
          </div>
          <p v-if="pending">Loading…</p>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <div v-else-if="!pending && reservations.length === 0" class="admin-table-wrap empty-wrap">
            <div class="empty-state">
              <i class="fas fa-clipboard"></i>
              <p>No reservations found</p>
            </div>
          </div>
          <div v-if="reservations.length" class="admin-table-wrap">
            <table class="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Owner</th>
                  <th>VMs</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in reservations" :key="item.id">
                  <td><code>{{ item.id }}</code></td>
                  <td>{{ item.username }}</td>
                  <td>{{ item.vm_count }}</td>
                  <td>{{ item.duration_minutes }} min</td>
                  <td>{{ item.status }}</td>
                  <td>{{ formatUnixTime(item.created_at) }}</td>
                  <td>
                    <button
                      class="btn-delete"
                      type="button"
                      :disabled="deleting"
                      @click="askDelete(item.id)"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </SiteChrome>
  </div>
</template>

<style>
.dashboard-shell {
  width: 100%;
  min-height: 100vh;
  font-family: Inter, 'Segoe UI', sans-serif;
}

.reservations-page .error,
.reservations-page .notice {
  margin: 1rem 0;
}

.reservations-page .error {
  color: #8d1d1d;
}

.reservations-page .notice {
  color: #1d5c32;
}

.dashboard-shell .reservations-page .empty-wrap {
  margin-right: 0;
  margin-left: 0;
}

.reservations-page .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem 2rem;
  color: #94a3b8;
  text-align: center;
}

.reservations-page .empty-state i {
  font-size: 2.5rem;
  opacity: 0.5;
}

.reservations-page .empty-state p {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 500;
}

.reservations-page .delete-confirm {
  margin: 0 0 1rem;
  padding: 1rem 1.25rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.reservations-page .delete-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.reservations-page .btn-delete,
.reservations-page .btn-form-cancel {
  padding: 0.45rem 0.8rem;
  border: none;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
}

.reservations-page .btn-delete {
  background: #b91c1c;
  color: #fff;
}

.reservations-page .btn-form-cancel {
  background: #e2e8f0;
  color: #1e293b;
}

.reservations-page .btn-delete:disabled,
.reservations-page .btn-form-cancel:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.dashboard-shell .admin-table-wrap {
  margin: 0 0 2rem;
  overflow-x: auto;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.dashboard-shell .admin-table {
  width: 100%;
  border-collapse: collapse;
}

.dashboard-shell .admin-table th,
.dashboard-shell .admin-table td {
  padding: 0.9rem 1rem;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}

.dashboard-shell .admin-table th {
  color: #64748b;
  font-size: 0.85rem;
}
</style>
