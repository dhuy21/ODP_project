<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { isSuccess } from '../api/http'
import { poolStatus, userReservations, type PoolStatus } from '../api/dashboard'
import type { Reservation } from '../api/types'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import { formatUnixTime } from '../time'
import '../assets/dashboard.css'

const session = useSessionStore()
const pool = ref<PoolStatus | null>(null)
const reservations = ref<Reservation[]>([])
const reservationsLoaded = ref(false)
const error = ref('')
const pending = ref(true)

const activeReservations = computed(() =>
  reservations.value.filter(
    (item) => item.status === 'active' && Date.now() / 1000 < item.expires_at,
  ),
)

const activeCount = computed(() => activeReservations.value.length)

const earlierReservations = computed(() =>
  reservations.value.filter((item) => !activeReservations.value.some((active) => active.id === item.id)),
)

onMounted(async () => {
  try {
    const [poolResult, reservationResult] = await Promise.all([
      poolStatus(),
      userReservations(session.username),
    ])
    const problems: string[] = []
    if (isSuccess(poolResult)) {
      pool.value = poolResult.body
    } else {
      problems.push(poolResult.body?.message || 'Could not load the pool')
    }
    if (isSuccess(reservationResult)) {
      reservations.value = Array.isArray(reservationResult.body.reservations)
        ? reservationResult.body.reservations
        : []
      reservationsLoaded.value = true
    } else {
      problems.push(reservationResult.body?.message || 'Could not load reservations')
    }
    error.value = problems.join(' ')
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    pending.value = false
  }
})
</script>

<template>
  <div class="dashboard-shell">
    <SiteChrome current="home">
      <main class="main-content">
        <div class="dashboard-page">
          <div class="dashboard-header">
            <div class="header-content">
              <div class="welcome-section">
                <div class="welcome-icon"><i class="fas fa-hand-sparkles"></i></div>
                <div>
                  <h1>Welcome back, <span class="username-highlight">{{ session.username }}</span>!</h1>
                  <p class="welcome-subtitle">Manage your infrastructure resources</p>
                </div>
              </div>
            </div>
          </div>
          <p v-if="pending">Loading…</p>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <div v-if="pool || reservationsLoaded" class="stats-container">
            <div class="stats-grid">
              <div v-if="pool" class="stat-card stat-available">
                <div class="stat-icon"><i class="fas fa-server"></i></div>
                <div class="stat-content">
                  <h3>Available Containers</h3>
                  <div class="stat-value">{{ pool.free }}</div>
                  <div class="stat-label">Ready to use</div>
                </div>
              </div>
              <div v-if="reservationsLoaded" class="stat-card stat-active">
                <div class="stat-icon"><i class="fas fa-rocket"></i></div>
                <div class="stat-content">
                  <h3>Active Reservations</h3>
                  <div class="stat-value">{{ activeCount }}</div>
                  <div class="stat-label">Currently running</div>
                </div>
              </div>
              <div v-if="reservationsLoaded" class="stat-card stat-total">
                <div class="stat-icon"><i class="fas fa-chart-line"></i></div>
                <div class="stat-content">
                  <h3>Total Reservations</h3>
                  <div class="stat-value">{{ reservations.length }}</div>
                  <div class="stat-label">All time</div>
                </div>
              </div>
            </div>
          </div>
          <section v-if="reservationsLoaded" class="section-container">
            <div class="section-header">
              <div class="section-title-wrapper">
                <div class="section-icon"><i class="fas fa-bolt"></i></div>
                <h2>Active Reservations</h2>
              </div>
              <p class="section-description">Your currently running virtual machines</p>
            </div>
            <p v-if="activeReservations.length === 0">No active reservations.</p>
            <div v-else class="reservation-grid">
              <article v-for="item in activeReservations" :key="item.id" class="reservation-card">
                <div class="card-header">
                  <div class="card-title-section">
                    <div class="card-icon"><i class="fas fa-server"></i></div>
                    <div>
                      <h3>{{ item.vm_count }} Virtual Machine{{ item.vm_count === 1 ? '' : 's' }}</h3>
                      <code class="reservation-id">{{ item.id }}</code>
                    </div>
                  </div>
                  <span class="status-badge status-active"><i class="fas fa-circle"></i> Active</span>
                </div>
                <div class="card-body">
                  <div class="detail-item">
                    <i class="fas fa-clock"></i>
                    <span class="detail-label">Duration:</span>
                    <span class="detail-value">{{ item.duration_minutes }} minutes</span>
                  </div>
                  <div class="detail-item">
                    <i class="fas fa-box"></i>
                    <span class="detail-label">Packages:</span>
                    <span class="detail-value">{{
                      Array.isArray(item.packages) && item.packages.length ? item.packages.join(', ') : 'None'
                    }}</span>
                  </div>
                </div>
                <div class="card-footer">
                  <RouterLink class="btn btn-primary btn-card" :to="{ name: 'reservation', params: { id: item.id } }">
                    <span>View Details</span>
                    <i class="fas fa-arrow-right"></i>
                  </RouterLink>
                </div>
              </article>
            </div>
          </section>
          <section v-if="earlierReservations.length" class="section-container">
            <div class="section-header">
              <div class="section-title-wrapper">
                <div class="section-icon"><i class="fas fa-history"></i></div>
                <h2>Earlier Reservations</h2>
              </div>
            </div>
            <div class="reservation-grid">
              <article v-for="item in earlierReservations" :key="item.id" class="reservation-card">
                <div class="card-header">
                  <div>
                    <h3>{{ item.status }} · until {{ formatUnixTime(item.expires_at) }}</h3>
                    <code class="reservation-id">{{ item.id }}</code>
                  </div>
                </div>
                <div class="card-footer">
                  <RouterLink class="btn btn-primary btn-card" :to="{ name: 'reservation', params: { id: item.id } }">
                    <span>View Details</span>
                    <i class="fas fa-arrow-right"></i>
                  </RouterLink>
                </div>
              </article>
            </div>
          </section>
          <section v-if="session.role === 'admin'" class="section-container">
            <div class="admin-notice">
              <div class="admin-notice-icon"><i class="fas fa-shield-alt"></i></div>
              <h2>Admin Account</h2>
              <p>Admin users cannot create reservations.</p>
            </div>
          </section>
          <section v-else class="section-container">
            <div class="section-header">
              <div class="section-title-wrapper">
                <div class="section-icon"><i class="fas fa-server"></i></div>
                <h2>Choose Operating System</h2>
              </div>
              <p class="section-description">Select an operating system for your virtual machines</p>
            </div>
            <div class="os-grid">
              <div class="os-card">
                <div class="os-card-header">
                  <div class="os-icon"><i class="fab fa-ubuntu"></i></div>
                  <div class="os-info">
                    <h3>Ubuntu</h3>
                    <p class="os-version">22.04 LTS</p>
                  </div>
                </div>
                <div class="os-card-body">
                  <div class="os-features">
                    <span class="os-feature"><i class="fas fa-check"></i> Long-term support</span>
                    <span class="os-feature"><i class="fas fa-check"></i> Production ready</span>
                  </div>
                </div>
                <RouterLink class="btn btn-primary btn-os-select" to="/provision">
                  <span>Get these VMs</span>
                  <i class="fas fa-arrow-right"></i>
                </RouterLink>
              </div>
            </div>
          </section>
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

.dashboard-shell .error {
  margin: 1rem 2rem;
  color: #8d1d1d;
}

.dashboard-shell .admin-notice {
  padding: 2rem;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  text-align: center;
}

.dashboard-shell .admin-notice-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.dashboard-shell .admin-notice h2 {
  margin-bottom: 0.5rem;
  color: #fff;
}
</style>
