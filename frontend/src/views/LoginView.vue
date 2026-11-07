<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { isSuccess } from '../api/http'
import { login } from '../api/session'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import '../assets/login.css'

const router = useRouter()
const session = useSessionStore()
const username = ref('')
const password = ref('')
const passwordVisible = ref(false)
const error = ref('')
const historyState = window.history.state as { notice?: unknown } | null
const notice = ref(typeof historyState?.notice === 'string' ? historyState.notice : '')
const pending = ref(false)

async function submit() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = 'Username and password are required'
    return
  }
  pending.value = true
  try {
    const result = await login(username.value, password.value)
    if (!isSuccess(result) || !result.body.user || !result.body.role) {
      error.value = result.body?.message || 'Login failed'
      return
    }
    session.setUser(result.body.user, result.body.role)
    await router.push({ name: 'home' })
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="login-shell">
    <SiteChrome current="login">
      <main class="main-content">
        <div class="login-page">
          <div class="login-container">
            <div class="login-left">
              <div class="login-brand">
                <div class="loader" aria-hidden="true">
                  <div class="box box0"><div></div></div>
                  <div class="box box1"><div></div></div>
                  <div class="box box2"><div></div></div>
                  <div class="box box3"><div></div></div>
                  <div class="box box4"><div></div></div>
                  <div class="box box5"><div></div></div>
                  <div class="box box6"><div></div></div>
                  <div class="box box7"><div></div></div>
                  <div class="ground"><div></div></div>
                </div>
                <h1 class="brand-title">ODP Project</h1>
                <p class="brand-subtitle">Infrastructure as Code Platform</p>
              </div>
            </div>
            <div class="login-right">
              <div class="login-box">
                <div class="login-header">
                  <h2 class="login-title">Welcome Back</h2>
                  <p class="login-subtitle">Sign in to continue</p>
                </div>
                <p v-if="notice" class="notice">{{ notice }}</p>
                <form class="login-form" novalidate @submit.prevent="submit">
                  <div class="form-group">
                    <label class="form-label" for="username">
                      <i class="fas fa-user"></i>
                      <span>Username</span>
                    </label>
                    <input
                      id="username"
                      v-model="username"
                      class="form-input"
                      name="username"
                      autocomplete="username"
                      placeholder="Enter your username"
                      autofocus
                    />
                  </div>
                  <div class="form-group">
                    <label class="form-label" for="password">
                      <i class="fas fa-lock"></i>
                      <span>Password</span>
                    </label>
                    <div class="input-wrapper">
                      <input
                        id="password"
                        v-model="password"
                        class="form-input"
                        name="password"
                        :type="passwordVisible ? 'text' : 'password'"
                        autocomplete="current-password"
                        placeholder="Enter your password"
                      />
                      <button
                        class="password-toggle"
                        type="button"
                        :aria-label="passwordVisible ? 'Hide password' : 'Show password'"
                        @click="passwordVisible = !passwordVisible"
                      >
                        <i class="fas" :class="passwordVisible ? 'fa-eye-slash' : 'fa-eye'"></i>
                      </button>
                    </div>
                  </div>
                  <p v-if="error" class="error" role="alert">{{ error }}</p>
                  <button class="btn-submit" type="submit" :disabled="pending">
                    <span class="btn-text">{{ pending ? 'Signing in…' : 'Sign In' }}</span>
                    <i v-if="!pending" class="fas fa-arrow-right"></i>
                  </button>
                </form>
                <div class="login-footer">
                  <p>Don't have an account?</p>
                  <RouterLink to="/register" class="footer-link">
                    Create one now <i class="fas fa-arrow-right"></i>
                  </RouterLink>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </SiteChrome>
  </div>
</template>

<style>
.login-shell {
  width: 100%;
  min-height: 100vh;
  font-family: Inter, 'Segoe UI', sans-serif;
  color: #1e293b;
}

.login-shell form {
  display: block;
  margin-top: 0;
}

.login-shell .error {
  margin: 0 0 1rem;
}
</style>
