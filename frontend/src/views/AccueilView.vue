<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import { useAccueilMotion } from '../composables/useAccueilMotion'
import SiteChrome from '../components/SiteChrome.vue'
import { useSessionStore } from '../stores/session'
import '../assets/accueil.css'

const session = useSessionStore()
const shell = ref<HTMLElement | null>(null)
const wave = ref<HTMLElement | null>(null)
const { scrollToFeatures } = useAccueilMotion(shell, wave)
</script>

<template>
  <div ref="shell" class="accueil-shell">
    <SiteChrome current="accueil">

    <main class="main-content">
      <div class="accueil-page">
        <section class="hero-section">
          <div class="hero-background">
            <div id="vanta-waves" ref="wave"></div>
            <div class="hero-gradient"></div>
            <div class="hero-particles"></div>
          </div>
          <div class="hero-content">
            <div class="hero-badge fade-in-up">
              <i class="fas fa-rocket"></i>
              <span>Infrastructure as Code</span>
            </div>
            <h1 class="hero-title fade-in-up" data-delay="100">
              Bienvenue sur <span class="gradient-text">ODP Project</span>
            </h1>
            <p class="hero-subtitle fade-in-up" data-delay="200">
              Plateforme de provisioning et d'orchestration de ressources conteneurisées
            </p>
            <p class="hero-description fade-in-up" data-delay="300">
              Gérez vos machines virtuelles facilement et efficacement avec notre solution IaC moderne
            </p>
            <div v-if="session.signedIn" class="hero-actions fade-in-up" data-delay="400">
              <RouterLink to="/home" class="btn btn-primary btn-hero">
                <span>Accéder au Dashboard</span>
                <i class="fas fa-arrow-right"></i>
              </RouterLink>
            </div>
            <div v-else class="hero-actions fade-in-up" data-delay="400">
              <RouterLink to="/register" class="btn btn-primary btn-hero">
                <span>Commencer maintenant</span>
                <i class="fas fa-arrow-right"></i>
              </RouterLink>
              <RouterLink to="/login" class="btn btn-secondary btn-hero">
                <span>Se connecter</span>
              </RouterLink>
            </div>
          </div>
          <div class="hero-scroll fade-in-up" data-delay="600">
            <button class="scroll-indicator" type="button" aria-label="Voir les fonctionnalités" @click="scrollToFeatures">
              <i class="fas fa-chevron-down"></i>
            </button>
          </div>
        </section>

        <section class="features-section">
          <div class="container">
            <div class="section-header fade-in">
              <span class="section-badge">
                <i class="fas fa-star"></i>
                Fonctionnalités
              </span>
              <h2 class="section-title">Tout ce dont vous avez besoin</h2>
              <p class="section-subtitle">Une plateforme complète pour gérer votre infrastructure</p>
            </div>
            <div class="features-grid">
              <div class="feature-card fade-in-up">
                <div class="feature-icon-wrapper">
                  <div class="feature-icon-bg"></div>
                  <i class="fas fa-server feature-icon"></i>
                </div>
                <h3 class="feature-title">Gestion de VMs</h3>
                <p class="feature-description">
                  Créez, démarrez et arrêtez vos machines virtuelles en quelques clics. Pool de ressources
                  automatiquement géré.
                </p>
              </div>
              <div class="feature-card fade-in-up" data-delay="100">
                <div class="feature-icon-wrapper">
                  <div class="feature-icon-bg"></div>
                  <i class="fas fa-bolt feature-icon"></i>
                </div>
                <h3 class="feature-title">Monitoring en temps réel</h3>
                <p class="feature-description">
                  Surveillez les performances et l'état de vos VMs instantanément. Statistiques détaillées et alertes
                  automatiques.
                </p>
              </div>
              <div class="feature-card fade-in-up">
                <div class="feature-icon-wrapper">
                  <div class="feature-icon-bg"></div>
                  <i class="fas fa-terminal feature-icon"></i>
                </div>
                <h3 class="feature-title">Terminal Web</h3>
                <p class="feature-description">
                  Accédez à vos VMs directement depuis votre navigateur. Terminal SSH intégré avec support temps réel.
                </p>
              </div>
              <div class="feature-card fade-in-up" data-delay="100">
                <div class="feature-icon-wrapper">
                  <div class="feature-icon-bg"></div>
                  <i class="fas fa-cogs feature-icon"></i>
                </div>
                <h3 class="feature-title">Automatisation Ansible</h3>
                <p class="feature-description">
                  Installation automatique de packages et configuration via Ansible. Provisioning rapide et
                  reproductible.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section class="how-it-works-section">
          <div class="container">
            <div class="section-header fade-in">
              <span class="section-badge">
                <i class="fas fa-play-circle"></i>
                Comment ça marche
              </span>
              <h2 class="section-title">Simple et rapide</h2>
              <p class="section-subtitle">En 3 étapes simples</p>
            </div>
            <div class="steps-container">
              <div class="step-item fade-in-left">
                <div class="step-number">01</div>
                <div class="step-icon"><i class="fas fa-user-plus"></i></div>
                <h3 class="step-title">Créer un compte</h3>
                <p class="step-description">Inscrivez-vous gratuitement en quelques secondes</p>
              </div>
              <div class="step-connector fade-in" data-delay="200">
                <i class="fas fa-arrow-right"></i>
              </div>
              <div class="step-item fade-in-up" data-delay="100">
                <div class="step-number">02</div>
                <div class="step-icon"><i class="fas fa-server"></i></div>
                <h3 class="step-title">Réserver des VMs</h3>
                <p class="step-description">Choisissez le nombre de machines et la durée</p>
              </div>
              <div class="step-connector fade-in" data-delay="400">
                <i class="fas fa-arrow-right"></i>
              </div>
              <div class="step-item fade-in-right" data-delay="200">
                <div class="step-number">03</div>
                <div class="step-icon"><i class="fas fa-rocket"></i></div>
                <h3 class="step-title">Commencer à utiliser</h3>
                <p class="step-description">Accédez à vos VMs via le terminal web intégré</p>
              </div>
            </div>
          </div>
        </section>

        <section v-if="!session.signedIn" class="cta-section">
          <div class="cta-background">
            <div class="cta-gradient"></div>
            <div class="cta-pattern"></div>
          </div>
          <div class="container">
            <div class="cta-content fade-in-up">
              <h2 class="cta-title">Prêt à commencer ?</h2>
              <p class="cta-description">
                Créez votre compte gratuitement et commencez à gérer vos VMs dès aujourd'hui
              </p>
              <RouterLink to="/register" class="btn btn-cta">
                <span>S'inscrire maintenant</span>
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
.accueil-shell {
  width: 100%;
  min-height: 100vh;
  box-sizing: border-box;
  background: #f5f7fa;
  color: #2d3748;
  font-family: Inter, 'Segoe UI', sans-serif;
}

.accueil-shell *,
.accueil-shell *::before,
.accueil-shell *::after {
  box-sizing: border-box;
}

.accueil-shell .hero-section {
  background: #064e3b;
}

.accueil-shell .container {
  max-width: 1200px;
  margin: 2rem auto;
  padding: 2rem;
  background-color: #fff;
}

.accueil-shell .features-section .container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
  background: transparent;
}

.accueil-shell button.scroll-indicator {
  width: 30px;
  height: 50px;
  margin: 0;
  padding: 10px 0 0;
  border: 2px solid rgba(255, 255, 255, 0.5);
  border-radius: 25px;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
</style>
