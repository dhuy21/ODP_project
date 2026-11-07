<script setup lang="ts">
import { FitAddon } from '@xterm/addon-fit'
import { Terminal } from '@xterm/xterm'
import { onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { io, type Socket } from 'socket.io-client'

import { useSessionStore } from '../stores/session'
import '@xterm/xterm/css/xterm.css'

interface ReservationInfo {
  error?: string
  username?: string
  node_name?: string
}

interface OutputBody {
  data?: string
}

interface ErrorBody {
  message?: string
}

const route = useRoute()
const session = useSessionStore()
const host = useTemplateRef<HTMLElement>('host')
let term: Terminal | null = null
let fit: FitAddon | null = null
let socket: Socket | null = null

function nodeName() {
  const value = route.params.nodeName
  return typeof value === 'string' ? value : ''
}

function sendSize() {
  if (!fit || !term || !socket) {
    return
  }
  fit.fit()
  socket.emit('resize', { cols: term.cols, rows: term.rows })
}

function stopTerminal() {
  window.removeEventListener('resize', sendSize)
  const closingSocket = socket
  const closingTerm = term
  socket = null
  term = null
  fit = null
  closingSocket?.disconnect()
  closingTerm?.dispose()
}

function startTerminal() {
  const element = host.value
  if (!element) {
    return
  }
  const currentTerm = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: { background: '#1e1e1e', foreground: '#ffffff' },
  })
  const currentFit = new FitAddon()
  currentTerm.loadAddon(currentFit)
  currentTerm.open(element)
  currentFit.fit()
  const currentSocket = io({ path: '/socket.io', withCredentials: true })
  term = currentTerm
  fit = currentFit
  socket = currentSocket

  let ended = false
  let armed = false
  let toldConnectError = false

  function stillCurrent() {
    return socket === currentSocket && term === currentTerm
  }

  function writeError(message: string) {
    if (!stillCurrent()) {
      return
    }
    currentTerm.write(`\r\n\x1b[31m${message}\x1b[0m\r\n`)
  }

  function stopInput(message: string) {
    if (!stillCurrent()) {
      return
    }
    ended = true
    writeError(message)
  }

  currentSocket.on('connect', () => {
    if (ended || !stillCurrent()) {
      return
    }
    currentSocket.emit('request_reservation_info', {
      username: session.username,
      node_name: nodeName(),
    })
  })
  currentSocket.on('reservation_info', (data: ReservationInfo | undefined) => {
    if (ended || !stillCurrent()) {
      return
    }
    if (!data || data.error || !data.username || !data.node_name) {
      stopInput(data?.error || 'No active reservation found for this container')
      return
    }
    currentFit.fit()
    armed = true
    currentSocket.emit('connect_ssh', {
      username: data.username,
      node_name: data.node_name,
      cols: currentTerm.cols,
      rows: currentTerm.rows,
    })
  })
  currentSocket.on('output', (data: OutputBody | undefined) => {
    if (!stillCurrent() || typeof data?.data !== 'string') {
      return
    }
    currentTerm.write(data.data)
  })
  currentSocket.on('force_disconnect', (data: ErrorBody | undefined) => {
    if (!stillCurrent()) {
      return
    }
    stopInput(data?.message || 'Reservation expired')
    currentSocket.disconnect()
  })
  currentSocket.on('error', (data: ErrorBody | undefined) => {
    if (!stillCurrent() || ended) {
      return
    }
    stopInput(data?.message || 'Could not open the terminal')
  })
  currentSocket.on('connect_error', () => {
    if (!stillCurrent() || toldConnectError) {
      return
    }
    toldConnectError = true
    writeError('Could not open the terminal')
  })
  currentTerm.onData((data) => {
    if (!armed || ended || !stillCurrent() || !currentSocket.connected) {
      return
    }
    currentSocket.emit('input', { data })
  })
  window.addEventListener('resize', sendSize)
}

onMounted(startTerminal)
watch(
  () => nodeName(),
  (next, previous) => {
    if (next === '' || next === previous) {
      return
    }
    stopTerminal()
    startTerminal()
  },
)
onBeforeUnmount(stopTerminal)
</script>

<template>
  <div class="terminal-shell">
    <div ref="host" class="terminal-host"></div>
  </div>
</template>

<style>
.terminal-shell {
  width: 100%;
  min-height: 100vh;
  background: #1e1e1e;
  display: flex;
  justify-content: center;
  align-items: center;
}

.terminal-shell .terminal-host {
  width: 90vw;
  height: 90vh;
}
</style>
