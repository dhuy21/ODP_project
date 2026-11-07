<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import {
  adminUsers,
  createAdminUser,
  deleteAdminUser,
  updateAdminRole,
  type AdminAccount,
} from '../api/admin'
import { isSuccess } from '../api/http'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import '../assets/dashboard.css'

const router = useRouter()
const session = useSessionStore()
const users = ref<AdminAccount[]>([])
const error = ref('')
const formError = ref('')
const notice = ref('')
const pending = ref(true)
const loaded = ref(false)
const creating = ref(false)
const saving = ref(false)
const confirming = ref('')
const confirmKind = ref<'role' | 'delete' | ''>('')
const savingRole = ref(false)
const savingDelete = ref(false)
const username = ref('')
const email = ref('')
const password = ref('')

function createdDay(value: string) {
  return value.length >= 10 ? value.slice(0, 10) : value
}

function roleLocked(account: AdminAccount) {
  return account.username === 'admin' || account.role === 'admin'
}

function ask(kind: 'role' | 'delete', name: string) {
  if (savingRole.value || savingDelete.value) {
    return
  }
  confirmKind.value = kind
  confirming.value = name
}

function cancelConfirm() {
  if (savingRole.value || savingDelete.value) {
    return
  }
  confirming.value = ''
  confirmKind.value = ''
}

async function loadUsers() {
  const result = await adminUsers()
  if (result.status === 401) {
    session.clear()
    await router.push({ name: 'login' })
    return
  }
  if (!isSuccess(result)) {
    error.value = result.body?.message || 'Could not load users'
    return
  }
  error.value = ''
  loaded.value = true
  users.value = Array.isArray(result.body.users) ? result.body.users : []
}

function openForm() {
  formError.value = ''
  creating.value = true
}

function closeForm() {
  creating.value = false
  formError.value = ''
  username.value = ''
  email.value = ''
  password.value = ''
}

async function remove() {
  const name = confirming.value
  if (!name || confirmKind.value !== 'delete' || savingDelete.value) {
    return
  }
  formError.value = ''
  notice.value = ''
  savingDelete.value = true
  try {
    const result = await deleteAdminUser(name)
    if (result.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(result)) {
      error.value = result.body?.message || 'Could not delete the user'
      return
    }
    error.value = ''
    notice.value = result.body.message || 'User deleted'
    users.value = users.value.filter((account) => account.username !== name)
    try {
      await loadUsers()
    } catch {
      error.value = 'Network error. Please try again.'
    }
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    savingDelete.value = false
    confirming.value = ''
    confirmKind.value = ''
  }
}

async function promote() {
  const name = confirming.value
  if (!name || confirmKind.value !== 'role' || savingRole.value) {
    return
  }
  formError.value = ''
  notice.value = ''
  savingRole.value = true
  try {
    const result = await updateAdminRole(name, 'admin')
    if (result.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(result)) {
      error.value = result.body?.message || 'Could not change the role'
      return
    }
    error.value = ''
    notice.value = result.body.message || 'Role updated to admin'
    const account = users.value.find((item) => item.username === name)
    if (account) {
      account.role = 'admin'
    }
    try {
      await loadUsers()
    } catch {
      error.value = 'Network error. Please try again.'
    }
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    savingRole.value = false
    confirming.value = ''
    confirmKind.value = ''
  }
}

async function submit() {
  if (saving.value) {
    return
  }
  formError.value = ''
  notice.value = ''
  if (!username.value || !email.value || !password.value) {
    formError.value = 'Please fill out every field'
    return
  }
  saving.value = true
  try {
    const result = await createAdminUser(username.value, email.value, password.value)
    if (result.status === 401) {
      session.clear()
      await router.push({ name: 'login' })
      return
    }
    if (!isSuccess(result)) {
      formError.value = result.body?.message || 'Could not create the user'
      return
    }
    const created: AdminAccount = {
      username: username.value,
      email: email.value,
      role: 'user',
      created_at: new Date().toISOString(),
      reservation_count: 0,
    }
    notice.value = result.body.message || 'User registered successfully'
    closeForm()
    if (!users.value.some((account) => account.username === created.username)) {
      users.value = [...users.value, created].sort((a, b) => a.username.localeCompare(b.username))
    }
    try {
      await loadUsers()
    } catch {
      error.value = 'Network error. Please try again.'
    }
  } catch {
    formError.value = 'Network error. Please try again.'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadUsers()
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
        <div class="dashboard-page users-page">
          <RouterLink class="btn-back" :to="{ name: 'admin' }">
            <i class="fas fa-arrow-left"></i>
            <span>Back to Overview</span>
          </RouterLink>
          <div class="dashboard-header">
            <div class="header-content users-header">
              <div class="welcome-section">
                <div class="welcome-icon"><i class="fas fa-users"></i></div>
                <div>
                  <h1>User Management</h1>
                  <p class="welcome-subtitle">Manage platform users and permissions</p>
                </div>
              </div>
              <button v-if="loaded && !creating" class="btn-add" type="button" @click="openForm">
                <i class="fas fa-plus-circle"></i>
                <span>Add User</span>
              </button>
            </div>
          </div>
          <p v-if="notice" class="notice" role="status">{{ notice }}</p>
          <section v-if="creating" class="section-container">
            <form class="modern-form" novalidate @submit.prevent="submit">
              <div class="form-header">
                <h3>Create New User</h3>
              </div>
              <p class="form-hint">
                <i class="fas fa-info-circle"></i>
                <span>The account is created as a user.</span>
              </p>
              <div class="form-group">
                <label class="form-label" for="create-username">
                  <i class="fas fa-user"></i>
                  <span>Username</span>
                </label>
                <input
                  id="create-username"
                  v-model="username"
                  class="form-input"
                  name="username"
                  autocomplete="username"
                  placeholder="Enter username"
                />
              </div>
              <div class="form-group">
                <label class="form-label" for="create-email">
                  <i class="fas fa-envelope"></i>
                  <span>Email</span>
                </label>
                <input
                  id="create-email"
                  v-model="email"
                  class="form-input"
                  name="email"
                  type="email"
                  autocomplete="email"
                  placeholder="user@example.com"
                />
              </div>
              <div class="form-group">
                <label class="form-label" for="create-password">
                  <i class="fas fa-lock"></i>
                  <span>Password</span>
                </label>
                <input
                  id="create-password"
                  v-model="password"
                  class="form-input"
                  name="password"
                  type="password"
                  autocomplete="new-password"
                  placeholder="Secure password"
                />
              </div>
              <p v-if="formError" class="error" role="alert">{{ formError }}</p>
              <button class="btn-submit" type="submit" :disabled="saving">
                {{ saving ? 'Creating…' : 'Create User' }}
              </button>
              <button class="btn-form-cancel" type="button" :disabled="saving" @click="closeForm">
                Cancel
              </button>
            </form>
          </section>
          <div v-if="confirming" class="role-confirm">
            <p v-if="confirmKind === 'delete'">
              Delete user "{{ confirming }}"? Containers from active reservations are released. This action cannot be undone.
            </p>
            <p v-else>Change {{ confirming }}'s role from USER to ADMIN?</p>
            <div class="role-actions">
              <button
                v-if="confirmKind === 'delete'"
                class="btn-delete"
                type="button"
                :disabled="savingDelete"
                @click="remove"
              >
                {{ savingDelete ? 'Deleting…' : 'Delete' }}
              </button>
              <button v-else class="btn-role" type="button" :disabled="savingRole" @click="promote">
                {{ savingRole ? 'Saving…' : 'Change' }}
              </button>
              <button
                class="btn-form-cancel"
                type="button"
                :disabled="savingRole || savingDelete"
                @click="cancelConfirm"
              >
                Cancel
              </button>
            </div>
          </div>
          <p v-if="pending">Loading…</p>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <div v-else-if="!pending && users.length === 0" class="admin-table-wrap empty-wrap">
            <div class="empty-state">
              <i class="fas fa-users-slash"></i>
              <p>No users found</p>
            </div>
          </div>
          <div v-if="users.length" class="admin-table-wrap">
            <table class="admin-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Created</th>
                  <th>Reservations</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="account in users" :key="account.username">
                  <td>{{ account.username }}</td>
                  <td>{{ account.email }}</td>
                  <td class="role-cell">
                    <span>{{ account.role }}</span>
                    <span v-if="roleLocked(account)" class="protected-badge">Admin Protected</span>
                    <template v-else>
                      <button
                        class="btn-role"
                        type="button"
                        :disabled="savingRole || savingDelete"
                        @click="ask('role', account.username)"
                      >
                        Make admin
                      </button>
                      <button
                        class="btn-delete"
                        type="button"
                        :disabled="savingRole || savingDelete"
                        @click="ask('delete', account.username)"
                      >
                        Delete User
                      </button>
                    </template>
                  </td>
                  <td>{{ createdDay(account.created_at) }}</td>
                  <td>{{ account.reservation_count }}</td>
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

.users-page .users-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.users-page .btn-add,
.users-page .btn-form-cancel,
.users-page .btn-role,
.users-page .btn-delete {
  padding: 0.85rem 1.25rem;
  border: none;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.users-page .btn-add {
  background: #fff;
  color: #047857;
}

.users-page .btn-role {
  padding: 0.45rem 0.8rem;
  background: #047857;
  color: #fff;
}

.users-page .btn-delete {
  padding: 0.45rem 0.8rem;
  background: #b91c1c;
  color: #fff;
}

.users-page .btn-form-cancel {
  background: #e2e8f0;
  color: #1e293b;
}

.users-page .btn-add:disabled,
.users-page .btn-form-cancel:disabled,
.users-page .btn-role:disabled,
.users-page .btn-delete:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.users-page .role-cell {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.users-page .protected-badge {
  color: #64748b;
  font-size: 0.85rem;
}

.users-page .role-confirm {
  margin: 0 0 1rem;
  padding: 1rem 1.25rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.users-page .role-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.users-page .error,
.users-page .notice {
  margin: 1rem 0;
}

.users-page .error {
  color: #8d1d1d;
}

.users-page .notice {
  color: #1d5c32;
}

.dashboard-shell .users-page .empty-wrap {
  margin-right: 0;
  margin-left: 0;
}

.users-page .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem 2rem;
  color: #94a3b8;
  text-align: center;
}

.users-page .empty-state i {
  font-size: 2.5rem;
  opacity: 0.5;
}

.users-page .empty-state p {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 500;
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
