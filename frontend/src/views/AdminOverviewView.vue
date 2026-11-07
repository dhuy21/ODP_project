<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { adminOverview, type AdminOverview } from '../api/admin'
import { isSuccess } from '../api/http'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import '../assets/dashboard.css'

const router = useRouter()
const session = useSessionStore()
const overview = ref<AdminOverview | null>(null)
const error = ref('')
const pending = ref(true)

function plural(count: number, word: string) {
  return `${count} ${word}${count > 1 ? 's' : ''}`
}

onMounted(async () => {
  try {
    const result = await adminOverview()
    if (result.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(result)) {
      error.value = result.body?.message || 'Could not load the overview'
      return
    }
    overview.value = result.body
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
        <div class="dashboard-page">
          <div class="dashboard-header">
            <div class="header-content">
              <div class="welcome-section">
                <div class="welcome-icon"><i class="fas fa-chart-line"></i></div>
                <div>
                  <h1>Dashboard Overview</h1>
                  <p class="welcome-subtitle">Administration</p>
                </div>
              </div>
            </div>
          </div>
          <p v-if="pending">Loading…</p>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <div v-if="overview" class="stats-container">
            <div class="stats-grid">
              <div class="stat-card stat-total">
                <div class="stat-icon"><i class="fas fa-users"></i></div>
                <div class="stat-content">
                  <h3>Total Accounts</h3>
                  <div class="stat-value">{{ overview.total_users }}</div>
                  <div class="stat-label">
                    {{ plural(overview.admin_count, 'admin') }} •
                    {{ plural(overview.user_count, 'user') }}
                  </div>
                </div>
              </div>
              <div class="stat-card stat-active">
                <div class="stat-icon"><i class="fas fa-rocket"></i></div>
                <div class="stat-content">
                  <h3>Active Reservations</h3>
                  <div class="stat-value">{{ overview.active_reservations }}</div>
                  <div class="stat-label">Currently running</div>
                </div>
              </div>
              <div class="stat-card stat-available">
                <div class="stat-icon"><i class="fas fa-server"></i></div>
                <div class="stat-content">
                  <h3>Total Containers</h3>
                  <div class="stat-value">{{ overview.total_containers }}</div>
                  <div class="stat-label">Pool size</div>
                </div>
              </div>
              <div class="stat-card stat-available">
                <div class="stat-icon"><i class="fas fa-check-circle"></i></div>
                <div class="stat-content">
                  <h3>Available Containers</h3>
                  <div class="stat-value">{{ overview.available_containers }}</div>
                  <div class="stat-label">Ready to allocate</div>
                </div>
              </div>
            </div>
          </div>
          <section v-if="overview" class="section-container">
            <RouterLink class="btn btn-primary btn-os-select" :to="{ name: 'admin-users' }">
              <span>User Management</span>
              <i class="fas fa-arrow-right"></i>
            </RouterLink>
            <RouterLink class="btn btn-primary btn-os-select" :to="{ name: 'admin-reservations' }">
              <span>All Reservations</span>
              <i class="fas fa-arrow-right"></i>
            </RouterLink>
            <RouterLink class="btn btn-primary btn-os-select" :to="{ name: 'admin-pool' }">
              <span>Container Pool</span>
              <i class="fas fa-arrow-right"></i>
            </RouterLink>
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
</style>
