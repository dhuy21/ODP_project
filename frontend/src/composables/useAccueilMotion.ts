import { onBeforeUnmount, onMounted, type Ref } from 'vue'

const THREE_SRC = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js'
const VANTA_SRC = 'https://cdn.jsdelivr.net/npm/vanta@0.5.24/dist/vanta.waves.min.js'

function loadScript(src: string): Promise<void> {
  const existing = document.querySelector<HTMLScriptElement>(`script[data-src="${src}"]`)
  if (existing) {
    if (existing.dataset.loaded === 'true') {
      return Promise.resolve()
    }
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error(src)), { once: true })
    })
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.dataset.src = src
    script.onload = () => {
      script.dataset.loaded = 'true'
      resolve()
    }
    script.onerror = () => {
      script.remove()
      reject(new Error(src))
    }
    document.head.appendChild(script)
  })
}

export function useAccueilMotion(shell: Ref<HTMLElement | null>, wave: Ref<HTMLElement | null>) {
  let alive = true
  let vantaEffect: VantaEffect | null = null
  let scrollHandler: (() => void) | null = null
  let scrollFrame = 0
  const timeouts: number[] = []
  const cardCleanups: Array<() => void> = []

  function reveal() {
    const root = shell.value
    if (!root) {
      return
    }
    root
      .querySelectorAll<HTMLElement>('.fade-in, .fade-in-up, .fade-in-left, .fade-in-right')
      .forEach((element, index) => {
        const delay = Number(element.dataset.delay)
        const timeout = window.setTimeout(
          () => element.classList.add('animate'),
          Number.isFinite(delay) ? delay : index * 100,
        )
        timeouts.push(timeout)
      })
  }

  function scrollToFeatures() {
    shell.value?.querySelector('.features-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function startParallax() {
    let ticking = false
    scrollHandler = () => {
      if (ticking) {
        return
      }
      ticking = true
      scrollFrame = window.requestAnimationFrame(() => {
        const root = shell.value
        const scrolled = window.pageYOffset
        const particles = root?.querySelector<HTMLElement>('.hero-particles')
        if (particles) {
          particles.style.transform = `translateY(${scrolled * 0.5}px)`
        }
        const heroContent = root?.querySelector<HTMLElement>('.hero-content')
        if (heroContent && scrolled < window.innerHeight) {
          heroContent.style.transform = `translateY(${scrolled * 0.3}px)`
          heroContent.style.opacity = String(1 - scrolled / window.innerHeight)
        }
        ticking = false
      })
    }
    window.addEventListener('scroll', scrollHandler, { passive: true })
  }

  function startCardTilt() {
    const cards = shell.value?.querySelectorAll<HTMLElement>('.feature-card') ?? []
    cards.forEach((card) => {
      const move = (event: MouseEvent) => {
        const rect = card.getBoundingClientRect()
        const rotateX = (event.clientY - rect.top - rect.height / 2) / 10
        const rotateY = (rect.width / 2 - (event.clientX - rect.left)) / 10
        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-10px)`
      }
      const leave = () => {
        card.style.transform = ''
      }
      card.addEventListener('mousemove', move)
      card.addEventListener('mouseleave', leave)
      cardCleanups.push(() => {
        card.removeEventListener('mousemove', move)
        card.removeEventListener('mouseleave', leave)
      })
    })
  }

  async function startWaves() {
    await loadScript(THREE_SRC)
    await loadScript(VANTA_SRC)
    if (!alive || !wave.value || !window.VANTA?.WAVES) {
      return
    }
    vantaEffect = window.VANTA.WAVES({
      el: wave.value,
      mouseControls: true,
      touchControls: true,
      gyroControls: false,
      minHeight: 200,
      minWidth: 200,
      scale: 1,
      scaleMobile: 1,
      color: 0x1a6429,
      shininess: 150,
      waveHeight: 40,
      waveSpeed: 1.45,
      zoom: 0.88,
    })
  }

  onMounted(() => {
    reveal()
    startParallax()
    startCardTilt()
    startWaves().catch(() => {
      // The green hero background stays readable if the wave scripts do not load.
    })
  })

  onBeforeUnmount(() => {
    alive = false
    vantaEffect?.destroy()
    vantaEffect = null
    timeouts.forEach((timeout) => window.clearTimeout(timeout))
    window.cancelAnimationFrame(scrollFrame)
    if (scrollHandler) {
      window.removeEventListener('scroll', scrollHandler)
    }
    cardCleanups.splice(0).forEach((cleanup) => cleanup())
  })

  return { scrollToFeatures }
}
