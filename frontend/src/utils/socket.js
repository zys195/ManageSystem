import { io } from 'socket.io-client'

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || window.location.origin
const ACK_TIMEOUT = 3000

let socket = null
let heartbeatTimer = null
const activeContracts = new Set()
const eventHandlers = {}

function emitWithAck(eventName, payload, timeout = ACK_TIMEOUT) {
  if (!socket?.connected) return Promise.reject(new Error('Socket not connected'))

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`${eventName} ack timeout`))
    }, timeout)

    socket.emit(eventName, payload, (response) => {
      clearTimeout(timer)
      resolve(response)
    })
  })
}

export function getSocket() {
  return socket
}

export function isConnected() {
  return socket?.connected || false
}

export function initSocket(token) {
  if (socket?.connected) {
    if (token) {
      socket.auth = { token }
    }
    return socket
  }

  socket = io(SOCKET_URL, {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 10000,
    query: { token },
    auth: { token },
  })

  socket.on('connect', () => {
    activeContracts.forEach((contractId) => {
      joinContract(contractId).catch(console.error)
    })
    startHeartbeat()
  })

  socket.on('disconnect', () => {
    stopHeartbeat()
  })

  socket.on('connect_error', (error) => {
    console.error('[Socket] connect error:', error.message)
  })

  socket.on('collab_event', (data) => {
    const handlers = eventHandlers[data.type]
    if (handlers) {
      handlers.forEach((cb) => cb(data))
    }
  })

  return socket
}

export function disconnect() {
  stopHeartbeat()
  activeContracts.clear()
  if (socket) {
    socket.disconnect()
    socket = null
  }
}

export async function joinContract(contractId, userInfo = {}) {
  const response = await emitWithAck('join_contract', { contract_id: Number(contractId), ...userInfo })
  if (response?.success) {
    activeContracts.add(Number(contractId))
    return response
  }
  throw new Error(response?.message || 'Join contract room failed')
}

export async function leaveContract(contractId) {
  if (!socket?.connected) return
  socket.emit('leave_contract', { contract_id: Number(contractId) })
  activeContracts.delete(Number(contractId))
}

export async function acquireLock(contractId, sessionInfo = {}) {
  const response = await emitWithAck('acquire_lock', { contract_id: Number(contractId), ...sessionInfo })
  if (response?.success) return response.lock
  throw response
}

export async function releaseLock(contractId, sessionInfo = {}) {
  if (!socket?.connected) return
  socket.emit('release_lock', { contract_id: Number(contractId), ...sessionInfo })
}

export function onCollabEvent(eventType, callback) {
  if (!eventHandlers[eventType]) {
    eventHandlers[eventType] = new Set()
  }
  eventHandlers[eventType].add(callback)

  return () => {
    eventHandlers[eventType]?.delete(callback)
  }
}

function startHeartbeat() {
  stopHeartbeat()
  heartbeatTimer = setInterval(() => {
    if (socket?.connected && activeContracts.size > 0) {
      socket.emit('heartbeat', {
        contract_ids: Array.from(activeContracts),
        session_id: generateSessionId(),
      })
    }
  }, 15000)
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function generateSessionId() {
  let sid = sessionStorage.getItem('_collab_session_id')
  if (!sid) {
    sid = `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    sessionStorage.setItem('_collab_session_id', sid)
  }
  return sid
}
