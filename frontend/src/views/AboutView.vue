<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import SiteChrome from '../components/SiteChrome.vue'
import { useAboutMotion } from '../composables/useAboutMotion'
import { useSessionStore } from '../stores/session'
import '../assets/about.css'

const session = useSessionStore()
const shell = ref<HTMLElement | null>(null)
const { scrollNext } = useAboutMotion(shell)
</script>

<template>
  <div ref="shell" class="about-shell">
    <SiteChrome current="about">
      <main class="main-content">
        <div class="about-wrapper">
          <div class="animated-bg">
            <div class="gradient-orb orb-1"></div>
            <div class="gradient-orb orb-2"></div>
            <div class="gradient-orb orb-3"></div>
          </div>

          <section class="hero-section">
            <div class="hero-content">
              <div class="hero-badge">
                <span class="badge-dot"></span>
                <span class="badge-text">Infrastructure as Code Platform</span>
              </div>
              <h1 class="hero-title">
                <span class="title-line">Welcome to</span>
                <span class="title-main">
                  <span class="gradient-text">ODP</span>
                  <span class="gradient-text-alt">Project</span>
                </span>
              </h1>
              <p class="hero-description">
                Empowering developers with cutting-edge container orchestration and automated infrastructure
                provisioning.
              </p>
              <div class="hero-stats">
                <div class="stat-item">
                  <div class="stat-value" data-target="99">0</div>
                  <div class="stat-label">Uptime %</div>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-item">
                  <div class="stat-value" data-target="30">0</div>
                  <div class="stat-label">Sec Deploy</div>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-item">
                  <div class="stat-value" data-target="24">0</div>
                  <div class="stat-label">Hours Support</div>
                </div>
              </div>
              <button class="scroll-indicator" type="button" aria-label="See the next section" @click="scrollNext">
                <i class="fas fa-chevron-down"></i>
              </button>
            </div>
          </section>

          <section class="features-showcase">
            <div class="section-header-modern">
              <span class="section-subtitle">What We Offer</span>
              <h2 class="section-title-modern">Powerful Features</h2>
              <p class="section-description">Built for developers, designed for scale</p>
            </div>
            <div class="features-container">
              <div class="feature-card-modern" data-aos="fade-up">
                <div class="feature-card-glow"></div>
                <div class="feature-icon-modern"><i class="fas fa-bolt"></i></div>
                <h3 class="feature-title-modern">Lightning Fast</h3>
                <p class="feature-desc-modern">
                  Deploy containers in under 30 seconds with our optimized infrastructure and smart caching
                </p>
                <div class="feature-tech-tags">
                  <span class="tech-tag">Docker</span>
                  <span class="tech-tag">Optimized</span>
                </div>
              </div>
              <div class="feature-card-modern" data-aos="fade-up" data-aos-delay="100">
                <div class="feature-card-glow"></div>
                <div class="feature-icon-modern"><i class="fas fa-shield-alt"></i></div>
                <h3 class="feature-title-modern">Enterprise Security</h3>
                <p class="feature-desc-modern">
                  Military-grade encryption, SSH key authentication, and isolated container environments
                </p>
                <div class="feature-tech-tags">
                  <span class="tech-tag">SSL/TLS</span>
                  <span class="tech-tag">SSH</span>
                </div>
              </div>
              <div class="feature-card-modern" data-aos="fade-up" data-aos-delay="200">
                <div class="feature-card-glow"></div>
                <div class="feature-icon-modern"><i class="fas fa-terminal"></i></div>
                <h3 class="feature-title-modern">Web Terminal</h3>
                <p class="feature-desc-modern">
                  Full-featured browser terminal with real-time WebSocket connection and command history
                </p>
                <div class="feature-tech-tags">
                  <span class="tech-tag">WebSocket</span>
                  <span class="tech-tag">Real-time</span>
                </div>
              </div>
              <div class="feature-card-modern" data-aos="fade-up" data-aos-delay="300">
                <div class="feature-card-glow"></div>
                <div class="feature-icon-modern"><i class="fas fa-magic"></i></div>
                <h3 class="feature-title-modern">Auto Configuration</h3>
                <p class="feature-desc-modern">
                  Automated software installation using Ansible playbooks with one-click deployment
                </p>
                <div class="feature-tech-tags">
                  <span class="tech-tag">Ansible</span>
                  <span class="tech-tag">IaC</span>
                </div>
              </div>
              <div class="feature-card-modern" data-aos="fade-up" data-aos-delay="400">
                <div class="feature-card-glow"></div>
                <div class="feature-icon-modern"><i class="fas fa-clock"></i></div>
                <h3 class="feature-title-modern">Flexible Scheduling</h3>
                <p class="feature-desc-modern">
                  Time-based reservations from 1 minute to 24 hours with automatic resource cleanup
                </p>
                <div class="feature-tech-tags">
                  <span class="tech-tag">Smart</span>
                  <span class="tech-tag">Efficient</span>
                </div>
              </div>
              <div class="feature-card-modern" data-aos="fade-up" data-aos-delay="500">
                <div class="feature-card-glow"></div>
                <div class="feature-icon-modern"><i class="fas fa-sync-alt"></i></div>
                <h3 class="feature-title-modern">Self-Healing</h3>
                <p class="feature-desc-modern">
                  Automatic health checks and container recovery with zero downtime architecture
                </p>
                <div class="feature-tech-tags">
                  <span class="tech-tag">Auto-recovery</span>
                  <span class="tech-tag">HA</span>
                </div>
              </div>
            </div>
          </section>

          <section class="tech-section">
            <div class="section-header-modern">
              <span class="section-subtitle">Built With</span>
              <h2 class="section-title-modern">Technology Stack</h2>
              <p class="section-description">Powered by industry-leading technologies</p>
            </div>
            <div class="tech-stack-container">
              <div class="tech-card" data-aos="zoom-in">
                <div class="tech-card-inner">
                  <div class="tech-logo"><i class="fab fa-docker"></i></div>
                  <h4 class="tech-name">Docker</h4>
                  <p class="tech-role">Container Engine</p>
                  <div class="tech-progress"><div class="tech-progress-bar" data-progress="95"></div></div>
                </div>
              </div>
              <div class="tech-card" data-aos="zoom-in" data-aos-delay="100">
                <div class="tech-card-inner">
                  <div class="tech-logo"><i class="fab fa-python"></i></div>
                  <h4 class="tech-name">FastAPI</h4>
                  <p class="tech-role">Backend Framework</p>
                  <div class="tech-progress"><div class="tech-progress-bar" data-progress="90"></div></div>
                </div>
              </div>
              <div class="tech-card" data-aos="zoom-in" data-aos-delay="200">
                <div class="tech-card-inner">
                  <div class="tech-logo"><i class="fas fa-plug"></i></div>
                  <h4 class="tech-name">Socket.IO</h4>
                  <p class="tech-role">Real-time Engine</p>
                  <div class="tech-progress"><div class="tech-progress-bar" data-progress="88"></div></div>
                </div>
              </div>
              <div class="tech-card" data-aos="zoom-in" data-aos-delay="300">
                <div class="tech-card-inner">
                  <div class="tech-logo"><i class="fas fa-cogs"></i></div>
                  <h4 class="tech-name">Ansible</h4>
                  <p class="tech-role">Configuration Mgmt</p>
                  <div class="tech-progress"><div class="tech-progress-bar" data-progress="85"></div></div>
                </div>
              </div>
              <div class="tech-card" data-aos="zoom-in" data-aos-delay="400">
                <div class="tech-card-inner">
                  <div class="tech-logo"><i class="fab fa-ubuntu"></i></div>
                  <h4 class="tech-name">Ubuntu</h4>
                  <p class="tech-role">Operating System</p>
                  <div class="tech-progress"><div class="tech-progress-bar" data-progress="92"></div></div>
                </div>
              </div>
              <div class="tech-card" data-aos="zoom-in" data-aos-delay="500">
                <div class="tech-card-inner">
                  <div class="tech-logo"><i class="fas fa-code"></i></div>
                  <h4 class="tech-name">TypeScript</h4>
                  <p class="tech-role">Frontend Logic</p>
                  <div class="tech-progress"><div class="tech-progress-bar" data-progress="87"></div></div>
                </div>
              </div>
            </div>
          </section>

          <section class="team-section">
            <div class="section-header-modern">
              <span class="section-subtitle">Meet The Team</span>
              <h2 class="section-title-modern">Our Amazing Team</h2>
              <p class="section-description">Passionate developers building the future</p>
            </div>
            <div class="team-container">
              <div class="team-member-card" data-aos="flip-left">
                <div class="member-avatar-wrapper">
                  <div class="member-avatar"><i class="fas fa-user"></i></div>
                  <div class="member-status"></div>
                </div>
                <h4 class="member-name">Mehdi Ouseggua</h4>
                <p class="member-role">Full Stack Developer</p>
              </div>
              <div class="team-member-card" data-aos="flip-left" data-aos-delay="100">
                <div class="member-avatar-wrapper">
                  <div class="member-avatar"><i class="fas fa-user"></i></div>
                  <div class="member-status"></div>
                </div>
                <h4 class="member-name">Vinh Tri NGUYEN</h4>
                <p class="member-role">Backend Developer</p>
              </div>
              <div class="team-member-card" data-aos="flip-left" data-aos-delay="200">
                <div class="member-avatar-wrapper">
                  <div class="member-avatar"><i class="fas fa-user"></i></div>
                  <div class="member-status"></div>
                </div>
                <h4 class="member-name">Dinh Huy NGUYEN</h4>
                <p class="member-role">DevOps Engineer</p>
              </div>
              <div class="team-member-card" data-aos="flip-left" data-aos-delay="300">
                <div class="member-avatar-wrapper">
                  <div class="member-avatar"><i class="fas fa-user"></i></div>
                  <div class="member-status"></div>
                </div>
                <h4 class="member-name">Khalid</h4>
                <p class="member-role">Cloud Architect</p>
              </div>
              <div class="team-member-card" data-aos="flip-left" data-aos-delay="400">
                <div class="member-avatar-wrapper">
                  <div class="member-avatar"><i class="fas fa-user"></i></div>
                  <div class="member-status"></div>
                </div>
                <h4 class="member-name">Thanh Tu VO</h4>
                <p class="member-role">Frontend Developer</p>
              </div>
              <div class="team-member-card" data-aos="flip-left" data-aos-delay="500">
                <div class="member-avatar-wrapper">
                  <div class="member-avatar"><i class="fas fa-user"></i></div>
                  <div class="member-status"></div>
                </div>
                <h4 class="member-name">Gia Khanh NGUYEN</h4>
                <p class="member-role">System Administrator</p>
              </div>
            </div>
          </section>

          <section class="cta-section">
            <div class="cta-container">
              <div class="cta-content" data-aos="fade-up">
                <h2 class="cta-title">Ready to Transform Your Infrastructure?</h2>
                <p class="cta-description">
                  Join thousands of developers who trust ODP for their container orchestration needs
                </p>
                <div class="cta-buttons">
                  <RouterLink v-if="session.signedIn" to="/home" class="btn-primary-modern">
                    <span class="btn-text">Go to Dashboard</span>
                    <i class="fas fa-arrow-right btn-icon"></i>
                  </RouterLink>
                  <template v-else>
                    <RouterLink to="/register" class="btn-primary-modern">
                      <span class="btn-text">Get Started Free</span>
                      <i class="fas fa-rocket btn-icon"></i>
                    </RouterLink>
                    <RouterLink to="/login" class="btn-secondary-modern">
                      <span class="btn-text">Sign In</span>
                      <i class="fas fa-sign-in-alt btn-icon"></i>
                    </RouterLink>
                  </template>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </SiteChrome>
  </div>
</template>

<style>
.about-shell {
  width: 100%;
  min-height: 100vh;
  box-sizing: border-box;
  font-family: Inter, 'Segoe UI', sans-serif;
}

.about-shell *,
.about-shell *::before,
.about-shell *::after {
  box-sizing: border-box;
}

.about-shell button.scroll-indicator {
  border: 0;
  background: transparent;
  padding: 0;
  font: inherit;
  cursor: pointer;
}
</style>
