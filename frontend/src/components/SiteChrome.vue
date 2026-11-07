<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { isSuccess } from '../api/http'
import { logout } from '../api/session'
import { useSessionStore } from '../stores/session'
import '../assets/chrome.css'

defineProps<{
  current: 'accueil' | 'about' | 'login' | 'register' | 'home' | 'admin'
}>()

const router = useRouter()
const session = useSessionStore()
const signingOut = ref(false)
const signOutError = ref('')

async function signOut() {
  if (signingOut.value) {
    return
  }
  signOutError.value = ''
  signingOut.value = true
  try {
    const result = await logout()
    if (!isSuccess(result)) {
      signOutError.value = result.body?.message || 'Logout failed'
      return
    }
    session.clear()
    await router.push({ name: 'login' })
  } catch {
    signOutError.value = 'Network error. Please try again.'
  } finally {
    signingOut.value = false
  }
}
</script>

<template>
  <nav class="main-nav">
    <div class="nav-container">
      <RouterLink to="/" class="nav-brand">
        <div class="nav-brand-icon-wrapper">
          <i class="fas fa-server nav-brand-icon"></i>
        </div>
        <span class="nav-brand-text">
          <span class="brand-text-main">ODP</span>
          <span class="brand-text-sub">Projet</span>
        </span>
      </RouterLink>
      <div class="nav-menu">
        <RouterLink to="/" class="nav-link" :class="{ 'nav-link-active': current === 'accueil' }">
          <span class="nav-link-icon-wrapper"><i class="fas fa-home nav-link-icon"></i></span>
          <span class="nav-link-text">Accueil</span>
          <span class="nav-link-indicator"></span>
        </RouterLink>
        <RouterLink to="/about" class="nav-link" :class="{ 'nav-link-active': current === 'about' }">
          <span class="nav-link-icon-wrapper"><i class="fas fa-info-circle nav-link-icon"></i></span>
          <span class="nav-link-text">About</span>
          <span class="nav-link-indicator"></span>
        </RouterLink>
        <RouterLink v-if="session.signedIn" to="/home" class="nav-link" :class="{ 'nav-link-active': current === 'home' }">
          <span class="nav-link-icon-wrapper"><i class="fas fa-chart-line nav-link-icon"></i></span>
          <span class="nav-link-text">Dashboard</span>
          <span class="nav-link-indicator"></span>
        </RouterLink>
        <RouterLink
          v-if="session.signedIn && session.role === 'admin'"
          to="/admin"
          class="nav-link"
          :class="{ 'nav-link-active': current === 'admin' }"
        >
          <span class="nav-link-icon-wrapper"><i class="fas fa-shield-alt nav-link-icon"></i></span>
          <span class="nav-link-text">Admin</span>
          <span class="nav-link-indicator"></span>
        </RouterLink>
        <div v-if="session.signedIn" class="nav-user-dropdown">
          <div class="nav-user-trigger">
            <div class="nav-user-avatar"><i class="fas fa-user nav-user-icon"></i></div>
            <span class="nav-user-name">{{ session.username }}</span>
            <i class="fas fa-chevron-down nav-user-arrow"></i>
          </div>
          <div class="nav-user-menu">
            <div class="nav-user-info">
              <div class="nav-user-role">{{ session.role.toUpperCase() }}</div>
            </div>
            <a href="/login" class="nav-user-logout" @click.prevent="signOut">
              <i class="fas fa-sign-out-alt logout-icon"></i>
              <span>{{ signingOut ? 'Logout…' : 'Logout' }}</span>
            </a>
          </div>
        </div>
        <template v-else>
          <RouterLink to="/login" class="nav-link" :class="{ 'nav-link-active': current === 'login' }">
            <span class="nav-link-icon-wrapper"><i class="fas fa-sign-in-alt nav-link-icon"></i></span>
            <span class="nav-link-text">Login</span>
            <span class="nav-link-indicator"></span>
          </RouterLink>
          <RouterLink to="/register" class="nav-link" :class="{ 'nav-link-active': current === 'register' }">
            <span class="nav-link-icon-wrapper"><i class="fas fa-user-plus nav-link-icon"></i></span>
            <span class="nav-link-text">Register</span>
            <span class="nav-link-indicator"></span>
          </RouterLink>
        </template>
      </div>
      <button class="nav-mobile-toggle" type="button" aria-label="Toggle menu">
        <span></span>
        <span></span>
        <span></span>
      </button>
    </div>
  </nav>
  <p v-if="signOutError" class="sign-out-error" role="alert">{{ signOutError }}</p>
  <slot />
  <footer class="main-footer">
    <div class="footer-container">
      <div class="footer-section">
        <div class="footer-logo">
          <div class="footer-logo-icon-wrapper">
            <i class="fas fa-server footer-logo-icon"></i>
          </div>
          <h4>ODP Project</h4>
        </div>
        <p>Infrastructure as Code Platform</p>
        <p class="footer-tagline">Empowering your infrastructure needs</p>
      </div>
      <div class="footer-section">
        <h5>Quick Links</h5>
        <ul class="footer-links">
          <li>
            <RouterLink to="/">
              <i class="fas fa-home footer-link-icon"></i>
              <span>Home</span>
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/about">
              <i class="fas fa-info-circle footer-link-icon"></i>
              <span>About</span>
            </RouterLink>
          </li>
          <li v-if="session.signedIn">
            <RouterLink to="/home">
              <i class="fas fa-chart-line footer-link-icon"></i>
              <span>Dashboard</span>
            </RouterLink>
          </li>
          <li v-else>
            <RouterLink to="/login">
              <i class="fas fa-sign-in-alt footer-link-icon"></i>
              <span>Login</span>
            </RouterLink>
          </li>
        </ul>
      </div>
      <div class="footer-section">
        <h5>Contact</h5>
        <div class="footer-contact">
          <a href="mailto:contact@odp.com" class="footer-contact-item">
            <i class="fas fa-envelope footer-contact-icon"></i>
            <span>contact@odp.com</span>
          </a>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <p>&copy; 2026 ODP Project. All rights reserved.</p>
    </div>
  </footer>
</template>

<style>
.sign-out-error {
  margin: 0;
  padding: 0.75rem 1.5rem;
  background: #fde8e8;
  color: #8d1d1d;
}
</style>
