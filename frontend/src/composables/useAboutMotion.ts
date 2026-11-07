import { onBeforeUnmount, onMounted, type Ref } from 'vue'

export function useAboutMotion(shell: Ref<HTMLElement | null>) {
  const intervals: number[] = []
  const timeouts: number[] = []
  const cleanups: Array<() => void> = []

  function animateCounter(element: Element, target: number) {
    let current = 0
    const increment = target / 50
    const timer = window.setInterval(() => {
      current += increment
      if (current >= target) {
        element.textContent = String(target)
        window.clearInterval(timer)
        return
      }
      element.textContent = String(Math.floor(current))
    }, 40)
    intervals.push(timer)
  }

  function bindMove(selector: string, move: (card: HTMLElement, event: MouseEvent) => void) {
    const root = shell.value
    if (!root) {
      return
    }
    root.querySelectorAll<HTMLElement>(selector).forEach((card) => {
      const onMove = (event: MouseEvent) => move(card, event)
      const onLeave = () => {
        card.style.transform = ''
      }
      card.addEventListener('mousemove', onMove)
      card.addEventListener('mouseleave', onLeave)
      cleanups.push(() => {
        card.removeEventListener('mousemove', onMove)
        card.removeEventListener('mouseleave', onLeave)
      })
    })
  }

  function scrollNext() {
    window.scrollTo({ top: window.innerHeight, behavior: 'smooth' })
  }

  onMounted(() => {
    const root = shell.value
    if (!root) {
      return
    }

    const counters = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return
          }
          const target = Number(entry.target.getAttribute('data-target'))
          if (!Number.isFinite(target)) {
            return
          }
          animateCounter(entry.target, target)
          counters.unobserve(entry.target)
        })
      },
      { threshold: 0.5 },
    )
    root.querySelectorAll('.stat-value').forEach((element) => counters.observe(element))

    const aos = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return
          }
          const delay = Number(entry.target.getAttribute('data-aos-delay')) || 0
          timeouts.push(window.setTimeout(() => entry.target.classList.add('aos-animate'), delay))
          aos.unobserve(entry.target)
        })
      },
      { threshold: 0.15, rootMargin: '0px 0px -50px 0px' },
    )
    root.querySelectorAll('[data-aos]').forEach((element) => aos.observe(element))

    const bars = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting || !(entry.target instanceof HTMLElement)) {
            return
          }
          const bar = entry.target
          const progress = bar.dataset.progress
          if (!progress) {
            return
          }
          timeouts.push(
            window.setTimeout(() => {
              bar.style.width = `${progress}%`
            }, 300),
          )
          bars.unobserve(entry.target)
        })
      },
      { threshold: 0.5 },
    )
    root.querySelectorAll('.tech-progress-bar').forEach((element) => bars.observe(element))

    bindMove('.feature-card-modern', (card, event) => {
      const rect = card.getBoundingClientRect()
      const rotateX = (event.clientY - rect.top - rect.height / 2) / 15
      const rotateY = (rect.width / 2 - (event.clientX - rect.left)) / 15
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-10px)`
    })
    bindMove('.team-member-card', (card, event) => {
      const rect = card.getBoundingClientRect()
      const moveX = (event.clientX - rect.left - rect.width / 2) * 0.1
      const moveY = (event.clientY - rect.top - rect.height / 2) * 0.1
      card.style.transform = `translate(${moveX}px, ${moveY}px) translateY(-10px) scale(1.02)`
    })

    const onScroll = () => {
      const scrolled = window.pageYOffset
      root.querySelectorAll<HTMLElement>('.gradient-orb').forEach((orb, index) => {
        orb.style.transform = `translateY(${-(scrolled * (index + 1) * 0.2)}px)`
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    cleanups.push(
      () => counters.disconnect(),
      () => aos.disconnect(),
      () => bars.disconnect(),
      () => window.removeEventListener('scroll', onScroll),
    )
  })

  onBeforeUnmount(() => {
    intervals.forEach((timer) => window.clearInterval(timer))
    timeouts.forEach((timer) => window.clearTimeout(timer))
    cleanups.splice(0).forEach((cleanup) => cleanup())
  })

  return { scrollNext }
}
