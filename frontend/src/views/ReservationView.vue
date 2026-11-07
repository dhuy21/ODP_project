<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { isSuccess } from '../api/http'
import type { Reservation } from '../api/types'
import { releaseReservation, reservationDetail } from '../api/reservations'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import { formatUnixTime } from '../time'
import '../assets/reservation.css'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const reservation = ref<Reservation | null>(null)
const error = ref('')
const pending = ref(true)
const confirming = ref(false)
const releasing = ref(false)

const canRelease = computed(
  () =>
    reservation.value?.status === 'active' && reservation.value.username === session.username,
)

const packageText = computed(() => {
  const packages = reservation.value?.packages
  if (!Array.isArray(packages) || packages.length === 0) {
    return 'None'
  }
  return packages.join(', ')
})

const nodes = computed(() =>
  Array.isArray(reservation.value?.nodes) ? reservation.value.nodes : [],
)

const statusClass = computed(() => {
  const status = reservation.value?.status
  if (status === 'active') {
    return 'badge badge-success'
  }
  if (status === 'expired') {
    return 'badge badge-warning'
  }
  return 'badge badge-info'
})

let loadSeq = 0

function sameReservation(reservationId: string) {
  return reservationId === String(route.params.id)
}

async function load(options: { keepError?: boolean } = {}) {
  const keepError = options.keepError === true
  const requestedId = String(route.params.id)
  const seq = ++loadSeq
  confirming.value = false
  if (!keepError) {
    error.value = ''
    reservation.value = null
    pending.value = true
  }
  const current = () => seq === loadSeq && sameReservation(requestedId)
  try {
    const result = await reservationDetail(requestedId)
    if (!current()) {
      return
    }
    const body = result.body
    if (!isSuccess(result)) {
      if (!keepError) {
        error.value = body?.message || 'Could not load the reservation'
      }
      return
    }
    if (!result.body.reservation || result.body.reservation.username !== session.username) {
      if (!keepError) {
        error.value = 'Reservation not found'
      }
      return
    }
    reservation.value = result.body.reservation
  } catch {
    if (!current() || keepError) {
      return
    }
    error.value = 'Network error. Please try again.'
  } finally {
    if (current()) {
      pending.value = false
    }
  }
}

async function release() {
  const requestedId = String(route.params.id)
  error.value = ''
  confirming.value = false
  releasing.value = true
  try {
    const result = await releaseReservation(requestedId)
    if (!sameReservation(requestedId)) {
      return
    }
    const body = result.body
    if (result.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(result)) {
      error.value = body?.message || 'Could not release the reservation'
      await load({ keepError: true })
      return
    }
    await load()
  } catch {
    if (sameReservation(requestedId)) {
      error.value = 'Network error. Please try again.'
    }
  } finally {
    releasing.value = false
  }
}

watch(
  () => route.params.id,
  () => {
    void load()
  },
  { immediate: true },
)
</script>

<template>
  <div class="reservation-shell">
    <SiteChrome current="home">
      <main class="main-content">
        <div class="reservation-detail">
          <RouterLink class="back-button" :to="{ name: 'home' }">← Back to Dashboard</RouterLink>
          <p v-if="pending">Loading…</p>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <template v-if="reservation">
            <div class="reservation-header">
              <h1><i class="fas fa-server"></i> Reservation Details</h1>
              <code>ID: {{ reservation.id }}</code>
              <div class="reservation-meta">
                <div class="meta-item">
                  <div class="meta-label">Status</div>
                  <div class="meta-value">
                    <span :class="statusClass">{{ reservation.status }}</span>
                  </div>
                </div>
                <div class="meta-item">
                  <div class="meta-label">Virtual Machines</div>
                  <div class="meta-value">{{ reservation.vm_count }}</div>
                </div>
                <div class="meta-item">
                  <div class="meta-label">Duration</div>
                  <div class="meta-value">{{ reservation.duration_minutes }} min</div>
                </div>
                <div class="meta-item">
                  <div class="meta-label">Packages</div>
                  <div class="meta-value">{{ packageText }}</div>
                </div>
                <div class="meta-item">
                  <div class="meta-label">From</div>
                  <div class="meta-value">{{ formatUnixTime(reservation.created_at) }}</div>
                </div>
                <div class="meta-item">
                  <div class="meta-label">Until</div>
                  <div class="meta-value">{{ formatUnixTime(reservation.expires_at) }}</div>
                </div>
              </div>
            </div>
            <div class="data-table-container">
              <div class="table-header">
                <h2><i class="fas fa-desktop"></i> Your Virtual Machines</h2>
              </div>
              <p v-if="nodes.length === 0" class="empty-nodes">No machines.</p>
              <div v-else class="nodes-grid padded">
                <article v-for="node in nodes" :key="node.name" class="node-card">
                  <div class="node-header">
                    <div>
                      <div class="node-name">{{ node.name }}</div>
                      <span v-if="reservation.status === 'active'" class="badge badge-success success-margin">
                        Running
                      </span>
                    </div>
                  </div>
                  <div class="node-info">
                    <div class="node-info-item">
                      <i class="fas fa-globe"></i>
                      <strong>IP:</strong> {{ node.ip }}
                    </div>
                    <div class="node-info-item">
                      <i class="fas fa-plug"></i>
                      <strong>SSH Port:</strong> {{ node.port }}
                    </div>
                    <div class="node-info-item">
                      <i class="fas fa-hdd"></i>
                      <strong>Platform:</strong> Ubuntu 22.04
                    </div>
                  </div>
                  <RouterLink
                    v-if="reservation.status === 'active'"
                    class="terminal-link"
                    :to="{ name: 'terminal', params: { nodeName: node.name } }"
                  >
                    <i class="fas fa-terminal"></i> Open Terminal
                  </RouterLink>
                  <button
                    v-else
                    class="btn disabled-btn"
                    type="button"
                    disabled
                  >
                    <i class="fas fa-lock"></i> Reservation Inactive
                  </button>
                </article>
              </div>
            </div>
            <div v-if="canRelease" class="action-buttons">
              <button
                v-if="!confirming"
                class="release-button"
                type="button"
                :disabled="releasing"
                @click="confirming = true"
              >
                {{ releasing ? 'Releasing…' : 'Release Resources' }}
              </button>
              <template v-else>
                <p>Are you sure you want to release these resources? This action cannot be undone.</p>
                <button class="release-button" type="button" :disabled="releasing" @click="release">
                  Release
                </button>
                <button class="cancel-button" type="button" :disabled="releasing" @click="confirming = false">
                  Cancel
                </button>
              </template>
            </div>
          </template>
        </div>
      </main>
    </SiteChrome>
  </div>
</template>

<style>
.reservation-shell {
  width: 100%;
  min-height: 100vh;
  font-family: Inter, 'Segoe UI', sans-serif;
}

.reservation-shell .error {
  color: #8d1d1d;
}

.reservation-shell .release-button,
.reservation-shell .cancel-button {
  font: inherit;
  padding: 0.75rem 1.25rem;
  border: 0;
  border-radius: 10px;
  cursor: pointer;
}

.reservation-shell .release-button {
  background: #b91c1c;
  color: #fff;
}

.reservation-shell .cancel-button {
  background: #e2e8f0;
  color: #1e293b;
}

.reservation-shell .terminal-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem 1.25rem;
  border-radius: 10px;
  background: #059669;
  color: #fff;
  font-weight: 600;
  text-decoration: none;
}

.reservation-shell .release-button:disabled,
.reservation-shell .cancel-button:disabled {
  opacity: 0.6;
  cursor: wait;
}
</style>
