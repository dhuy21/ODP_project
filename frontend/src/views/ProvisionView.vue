<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { isSuccess } from '../api/http'
import type { ProvisionSuccess } from '../api/provision'
import { provision } from '../api/provision'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import '../assets/dashboard.css'

const session = useSessionStore()
const router = useRouter()
const vmCount = ref(1)
const duration = ref(60)
const password = ref('')
const packages = ref('')
const error = ref('')
const result = ref<ProvisionSuccess | null>(null)
const pending = ref(false)

async function submit() {
  error.value = ''
  result.value = null
  if (!Number.isInteger(vmCount.value) || vmCount.value < 1) {
    error.value = 'Number of machines must be a whole number of at least 1'
    return
  }
  if (!Number.isInteger(duration.value) || duration.value < 1) {
    error.value = 'Duration must be a whole number of minutes, at least 1'
    return
  }
  pending.value = true
  try {
    const response = await provision(vmCount.value, duration.value, password.value, packages.value)
    if (response.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(response)) {
      error.value = response.body?.message || 'Could not reserve machines'
      return
    }
    result.value = response.body
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="dashboard-shell">
    <SiteChrome current="home">
      <main class="main-content">
        <div class="dashboard-page">
          <section class="section-container">
            <div class="provision-form">
              <div class="form-header">
                <RouterLink class="btn-back" :to="{ name: 'home' }">
                  <i class="fas fa-arrow-left"></i>
                  <span>Back</span>
                </RouterLink>
                <h3>Ubuntu 22.04 LTS</h3>
              </div>
              <p v-if="session.role === 'admin'" class="error" role="alert">
                Admin users cannot create reservations.
              </p>
              <form v-else class="modern-form" novalidate @submit.prevent="submit">
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">
                      <i class="fas fa-lock"></i>
                      <span>VM Password</span>
                    </label>
                    <input v-model="password" class="form-input" type="password" autocomplete="new-password" placeholder="Enter password for VM access" />
                    <small class="form-hint"><i class="fas fa-info-circle"></i> This password will be used to access your VMs via SSH</small>
                  </div>
                  <div class="form-group">
                    <label class="form-label">
                      <i class="fas fa-desktop"></i>
                      <span>Number of VMs</span>
                    </label>
                    <input v-model.number="vmCount" class="form-input" type="number" min="1" step="1" />
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">
                      <i class="fas fa-clock"></i>
                      <span>Reservation Duration</span>
                    </label>
                    <select v-model.number="duration" class="form-input">
                      <option :value="1">1 minute (testing)</option>
                      <option :value="60">1 hour</option>
                      <option :value="120">2 hours</option>
                      <option :value="180">3 hours</option>
                      <option :value="360">6 hours</option>
                      <option :value="720">12 hours</option>
                      <option :value="1440">24 hours</option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label class="form-label">
                      <i class="fas fa-box"></i>
                      <span>Software Packages</span>
                    </label>
                    <input v-model="packages" class="form-input" type="text" placeholder="nginx, git, vim (comma-separated)" />
                    <small class="form-hint"><i class="fas fa-info-circle"></i> Optional: Packages will be installed automatically</small>
                  </div>
                </div>
                <p v-if="error" class="error" role="alert">{{ error }}</p>
                <button class="btn btn-primary btn-submit" type="submit" :disabled="pending">
                  <i class="fas fa-rocket"></i>
                  <span>{{ pending ? 'Reserving…' : 'Create Reservation' }}</span>
                </button>
              </form>
              <section v-if="result" class="reservation-grid">
                <article class="reservation-card">
                  <div class="card-header">
                    <div class="card-title-section">
                      <div class="card-icon"><i class="fas fa-check"></i></div>
                      <div>
                        <h3>Reserved</h3>
                        <code class="reservation-id">{{ result.reservation_id }}</code>
                      </div>
                    </div>
                  </div>
                  <div class="card-body">
                    <div
                      v-for="node in Array.isArray(result.nodes) ? result.nodes : []"
                      :key="node.name"
                      class="detail-item"
                    >
                      <i class="fas fa-server"></i>
                      <span class="detail-value">{{ node.name }} · {{ node.ip }} · {{ node.port }}</span>
                    </div>
                    <p v-if="!Array.isArray(result.nodes) || result.nodes.length === 0">No machines returned.</p>
                  </div>
                  <div class="card-footer">
                    <RouterLink
                      class="btn btn-primary btn-card"
                      :to="{ name: 'reservation', params: { id: result.reservation_id } }"
                    >
                      <span>View Details</span>
                      <i class="fas fa-arrow-right"></i>
                    </RouterLink>
                  </div>
                </article>
              </section>
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

.dashboard-shell form {
  display: block;
  margin-top: 0;
}

.dashboard-shell .error {
  color: #8d1d1d;
}
</style>
