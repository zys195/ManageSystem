/**
 * Socket.IO 客户端封装
 * - 管理连接生命周期
 * - 提供房间加入/离开
 * - 编辑锁获取/释放/心跳
 */
import { io } from 'socket.io-client'

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || window.location.origin

let socket = null
let heartbeatTimer = null
const activeContracts = new Set() // 当前正在查看的合同ID列表
const eventHandlers = {} // 事件监听器 { eventType: Set<callback> }

export function getSocket() {
  return socket
}

export function isConnected() {
  return socket?.connected || false
}

/**
 * 初始化Socket.IO连接（带JWT认证）
 * @param {string} token - JWT token
 */
export function initSocket(token) {
  if (socket?.connected) {
    // 如果已连接，重新认证或复用
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
    console.log('[Socket] 已连接, sid:', socket.id)
    // 重连后重新加入所有活跃合同房间
    activeContracts.forEach((contractId) => {
      joinContract(contractId).catch(console.error)
    })
    startHeartbeat()
  })

  socket.on('disconnect', (reason) => {
    console.log('[Socket] 断开连接:', reason)
    stopHeartbeat()
  })

  socket.on('connect_error', (error) => {
    console.error('[Socket] 连接错误:', error.message)
  })

  socket.on('collab_event', (data) => {
    const handlers = eventHandlers[data.type]
    if (handlers) {
      handlers.forEach((cb) => cb(data))
    }
  })

  return socket
}

/**
 * 断开连接
 */
export function disconnect() {
  stopHeartbeat()
  activeContracts.clear()
  if (socket) {
    socket.disconnect()
    socket = null
  }
}

/**
 * 加入合同协作房间
 */
export async function joinContract(contractId, userInfo = {}) {
  if (!socket?.connected) throw new Error('Socket未连接')

  return new Promise((resolve, reject) => {
    socket.emit(
      'join_contract',
      { contract_id: Number(contractId), ...userInfo },
      (response) => {
        if (response?.success) {
          activeContracts.add(Number(contractId))
          resolve(response)
        } else {
          reject(new Error(response?.message || '加入失败'))
        }
      }
    )
  })
}

/**
 * 离开合同协作房间
 */
export async function leaveContract(contractId) {
  if (!socket?.connected) return
  socket.emit('leave_contract', { contract_id: Number(contractId) })
  activeContracts.delete(Number(contractId))
}

/**
 * 获取编辑锁（WebSocket方式）
 */
export async function acquireLock(contractId, sessionInfo = {}) {
  if (!socket?.connected) throw new Error('Socket未连接')

  return new Promise((resolve, reject) => {
    socket.emit(
      'acquire_lock',
      { contract_id: Number(contractId), ...sessionInfo },
      (response) => {
        if (response?.success) {
          resolve(response.lock)
        } else {
          reject(response)
        }
      }
    )
  })
}

/**
 * 释放编辑锁
 */
export async function releaseLock(contractId, sessionInfo = {}) {
  if (!socket?.connected) return
  socket.emit('release_lock', { contract_id: Number(contractId), ...sessionInfo })
}

/**
 * 注册协作事件监听
 * @param {string} eventType - 事件类型，如 'lock_acquired_by_other', 'user_joined' 等
 * @param {Function} callback - 回调函数
 * @returns {Function} 取消注册的函数
 */
export function onCollabEvent(eventType, callback) {
  if (!eventHandlers[eventType]) {
    eventHandlers[eventType] = new Set()
  }
  eventHandlers[eventType].add(callback)

  return () => {
    eventHandlers[eventType]?.delete(callback)
  }
}

// ===== 心跳保活 =====

function startHeartbeat() {
  stopHeartbeat()
  heartbeatTimer = setInterval(() => {
    if (socket?.connected && activeContracts.size > 0) {
      socket.emit('heartbeat', {
        contract_ids: Array.from(activeContracts),
        session_id: generateSessionId(),
      })
    }
  }, 15000) // 每15秒一次心跳
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

/**
 * 生成前端会话ID（用于标识同一浏览器的多个标签）
 */
function generateSessionId() {
  let sid = sessionStorage.getItem('_collab_session_id')
  if (!sid) {
    sid = `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    sessionStorage.setItem('_collab_session_id', sid)
  }
  return sid
}
