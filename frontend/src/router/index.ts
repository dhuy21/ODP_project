import { createRouter, createWebHistory } from 'vue-router'

import { useSessionStore } from '../stores/session'
import AboutView from '../views/AboutView.vue'
import AdminOverviewView from '../views/AdminOverviewView.vue'
import AdminPoolView from '../views/AdminPoolView.vue'
import AdminReservationsView from '../views/AdminReservationsView.vue'
import AdminUsersView from '../views/AdminUsersView.vue'
import AccueilView from '../views/AccueilView.vue'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import ProvisionView from '../views/ProvisionView.vue'
import RegisterView from '../views/RegisterView.vue'
import ReservationView from '../views/ReservationView.vue'
import TerminalView from '../views/TerminalView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'accueil', component: AccueilView },
    { path: '/about', name: 'about', component: AboutView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },
    { path: '/home', name: 'home', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/admin', name: 'admin', component: AdminOverviewView, meta: { requiresAuth: true } },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: AdminUsersView,
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/reservations',
      name: 'admin-reservations',
      component: AdminReservationsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/pool',
      name: 'admin-pool',
      component: AdminPoolView,
      meta: { requiresAuth: true },
    },
    { path: '/provision', name: 'provision', component: ProvisionView, meta: { requiresAuth: true } },
    {
      path: '/reservations/:id',
      name: 'reservation',
      component: ReservationView,
      meta: { requiresAuth: true },
    },
    {
      path: '/terminal/:nodeName',
      name: 'terminal',
      component: TerminalView,
      meta: { requiresAuth: true },
    },
  ],
})

let restored: Promise<void> | null = null

router.beforeEach(async (to) => {
  const session = useSessionStore()
  if (restored === null) {
    restored = session.restore().then((settled) => {
      if (!settled) {
        restored = null
      }
    })
  }
  await restored
  if (to.meta.requiresAuth && !session.signedIn) {
    return { name: 'login' }
  }
  if ((to.name === 'login' || to.name === 'register') && session.signedIn) {
    return { name: 'home' }
  }
  return true
})

export default router
