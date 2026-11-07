<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { adminPool, recoverPool, type AdminPoolNode } from '../api/admin'
import { isSuccess } from '../api/http'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import { formatUnixTime } from '../time'
import '../assets/dashboard.css'

const router = useRouter()
const session = useSessionStore()
const nodes = ref<AdminPoolNode[]>([])
const error = ref('')
const notice = ref('')
const pending = ref(true)
const confirming = ref(false)
const recovering = ref(false)

function expiryText(value: number) {
  return value > 0 ? formatUnixTime(value) : '—'
}

async function recover() {
  if (recovering.value) {
    return
  }
  error.value = ''
  notice.value = ''
  recovering.value = true
  try {
    const result = await recoverPool()
    if (result.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(result)) {
      error.value = result.body?.message || 'Could not restart the pool containers'
      return
    }
    const restarted = result.body.restarted
    notice.value = `${result.body.message || 'Pool recovery initiated'}. Restarted ${restarted} containers.`
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    recovering.value = false
    confirming.value = false
  }
}

onMounted(async () => {
  try {
    const result = await adminPool()
    if (result.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(result)) {
      error.value = result.body?.message || 'Could not load the pool'
      return
    }
    nodes.value = Array.isArray(result.body.nodes) ? result.body.nodes : []
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
        <div class="dashboard-page pool-page">
          <RouterLink class="btn-back" :to="{ name: 'admin' }">
            <i class="fas fa-arrow-left"></i>
            <span>Back to Overview</span>
          </RouterLink>
          <div class="dashboard-header">
            <div class="header-content pool-header">
              <div class="welcome-section">
                <div class="welcome-icon"><i class="fas fa-server"></i></div>
                <div>
                  <h1>Container Pool Status</h1>
                  <p class="welcome-subtitle">The table is the SQL record. Recover restarts stopped pool containers.</p>
                </div>
              </div>
              <button v-if="!confirming" class="btn-warning" type="button" @click="confirming = true">
                <i class="fas fa-tools"></i>
                <span>Recover Pool</span>
              </button>
            </div>
          </div>
          <div v-if="confirming" class="recover-confirm">
            <p>Restart stopped pool containers? Missing containers are not created, and the SQL table is not changed.</p>
            <div class="recover-actions">
              <button class="btn-warning" type="button" :disabled="recovering" @click="recover">
                <i class="fas fa-tools"></i>
                <span>{{ recovering ? 'Recovering…' : 'Recover' }}</span>
              </button>
              <button class="btn-cancel" type="button" :disabled="recovering" @click="confirming = false">
                Cancel
              </button>
            </div>
          </div>
          <p v-if="notice" class="notice" role="status">{{ notice }}</p>
          <p v-if="pending">Loading…</p>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <div v-else-if="!pending && nodes.length === 0" class="admin-table-wrap empty-wrap">
            <div class="empty-state">
              <i class="fas fa-server"></i>
              <p>No containers found</p>
            </div>
          </div>
          <div v-if="nodes.length" class="admin-table-wrap">
            <table class="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>IP</th>
                  <th>Port</th>
                  <th>Status</th>
                  <th>Owner</th>
                  <th>Expiry</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="node in nodes" :key="node.name">
                  <td>{{ node.name }}</td>
                  <td>{{ node.ip }}</td>
                  <td>{{ node.port }}</td>
                  <td>{{ node.status }}</td>
                  <td>{{ node.owner || '—' }}</td>
                  <td>{{ expiryText(node.expiry) }}</td>
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

.dashboard-shell .pool-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.dashboard-shell .btn-warning,
.dashboard-shell .btn-cancel {
  padding: 0.85rem 1.25rem;
  border: none;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.dashboard-shell .btn-warning {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
}

.dashboard-shell .btn-warning:disabled,
.dashboard-shell .btn-cancel:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.dashboard-shell .recover-confirm {
  margin: 0 0 1rem;
  padding: 1rem 1.25rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.dashboard-shell .recover-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.dashboard-shell .btn-cancel {
  background: #e2e8f0;
  color: #1e293b;
}

.dashboard-shell .error,
.dashboard-shell .notice {
  margin: 1rem 2rem;
}

.dashboard-shell .error {
  color: #8d1d1d;
}

.dashboard-shell .notice {
  color: #1d5c32;
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

.dashboard-shell .pool-page .empty-wrap {
  margin-right: 0;
  margin-left: 0;
}

.pool-page .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem 2rem;
  color: #94a3b8;
  text-align: center;
}

.pool-page .empty-state i {
  font-size: 2.5rem;
  opacity: 0.5;
}

.pool-page .empty-state p {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 500;
}
</style>
