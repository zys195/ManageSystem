/**
 * 协作编辑锁 REST API
 * 作为 WebSocket 的补充，提供 HTTP 方式的锁管理
 */
import request from './http'

/**
 * 获取编辑锁
 */
export function acquireLockAPI(contractId, sessionId = null) {
  return request.post(`/contracts/${contractId}/lock`, {
    session_id: sessionId || _getSessionId(),
  })
}

/**
 * 释放编辑锁
 */
export function releaseLockAPI(contractId) {
  return request.delete(`/contracts/${contractId}/lock`, {
    data: { session_id: _getSessionId() },
  })
}

/**
 * 查询锁状态
 */
export function getLockStatus(contractId) {
  return request.get(`/contracts/${contractId}/lock`)
}

/**
 * 心跳续期
 */
export function heartbeatLock(contractId) {
  return request.post(`/contracts/${contractId}/lock/heartbeat`, {
    session_id: _getSessionId(),
  })
}

/**
 * 获取在线用户信息
 */
export function getOnlineUsers(contractId) {
  return request.get(`/contracts/${contractId}/online-users`)
}

function _getSessionId() {
  let sid = sessionStorage.getItem('_collab_session_id')
  if (!sid) {
    sid = `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    sessionStorage.setItem('_collab_session_id', sid)
  }
  return sid
}
