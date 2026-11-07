<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { register } from '../api/accounts'
import { isSuccess } from '../api/http'
import SiteChrome from '../components/SiteChrome.vue'
import '../assets/register.css'

const router = useRouter()
const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const passwordVisible = ref(false)
const confirmVisible = ref(false)
const error = ref('')
const pending = ref(false)

async function submit() {
  error.value = ''
  if (!username.value || !email.value || !password.value || !confirmPassword.value) {
    error.value = 'Please fill out every field'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }
  pending.value = true
  try {
    const result = await register(username.value, email.value, password.value)
    if (!isSuccess(result)) {
      error.value = result.body?.message || 'Registration failed'
      return
    }
    await router.push({
      name: 'login',
      state: { notice: result.body.message },
    })
  } catch {
    error.value = 'Network error. Please try again.'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="register-shell">
    <SiteChrome current="register">
      <main class="main-content">
        <div class="register-page">
          <div class="register-container">
            <div class="register-left">
              <div class="register-brand">
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
                <h1 class="brand-title">Join ODP Project</h1>
                <p class="brand-subtitle">Start managing your infrastructure today</p>
              </div>
            </div>
            <div class="register-right">
              <div class="register-box">
                <div class="register-header">
                  <h2 class="register-title">Create Account</h2>
                  <p class="register-subtitle">Sign up to get started</p>
                </div>
                <form class="register-form" novalidate @submit.prevent="submit">
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
                      placeholder="Choose a username"
                      autofocus
                    />
                  </div>
                  <div class="form-group">
                    <label class="form-label" for="email">
                      <i class="fas fa-envelope"></i>
                      <span>Email</span>
                    </label>
                    <input
                      id="email"
                      v-model="email"
                      class="form-input"
                      name="email"
                      type="email"
                      autocomplete="email"
                      placeholder="your.email@example.com"
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
                        autocomplete="new-password"
                        placeholder="Create a password"
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
                  <div class="form-group">
                    <label class="form-label" for="confirm_password">
                      <i class="fas fa-lock"></i>
                      <span>Confirm Password</span>
                    </label>
                    <div class="input-wrapper">
                      <input
                        id="confirm_password"
                        v-model="confirmPassword"
                        class="form-input"
                        name="confirm_password"
                        :type="confirmVisible ? 'text' : 'password'"
                        autocomplete="new-password"
                        placeholder="Confirm your password"
                      />
                      <button
                        class="password-toggle"
                        type="button"
                        :aria-label="confirmVisible ? 'Hide password' : 'Show password'"
                        @click="confirmVisible = !confirmVisible"
                      >
                        <i class="fas" :class="confirmVisible ? 'fa-eye-slash' : 'fa-eye'"></i>
                      </button>
                    </div>
                  </div>
                  <p v-if="error" class="error" role="alert">{{ error }}</p>
                  <button class="btn-submit" type="submit" :disabled="pending">
                    <span class="btn-text">{{ pending ? 'Creating account…' : 'Create Account' }}</span>
                    <i v-if="!pending" class="fas fa-user-plus"></i>
                  </button>
                </form>
                <div class="register-footer">
                  <p>Already have an account?</p>
                  <RouterLink to="/login" class="footer-link">
                    Sign in instead <i class="fas fa-arrow-right"></i>
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
.register-shell {
  width: 100%;
  min-height: 100vh;
  font-family: Inter, 'Segoe UI', sans-serif;
  color: #1e293b;
}

.register-shell form {
  display: block;
  margin-top: 0;
}

.register-shell .error {
  margin: 0 0 1rem;
}
</style>
