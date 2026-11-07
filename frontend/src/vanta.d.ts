interface VantaEffect {
  destroy: () => void
}

interface VantaWaveOptions {
  el: HTMLElement
  mouseControls: boolean
  touchControls: boolean
  gyroControls: boolean
  minHeight: number
  minWidth: number
  scale: number
  scaleMobile: number
  color: number
  shininess: number
  waveHeight: number
  waveSpeed: number
  zoom: number
}

interface Window {
  VANTA?: {
    WAVES?: (options: VantaWaveOptions) => VantaEffect
  }
}
