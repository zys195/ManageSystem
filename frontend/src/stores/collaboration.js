/**
 * 协作编辑状态管理
 * - 管理当前合同的在线用户
 * - 管理编辑锁状态
 * - 处理协作事件分发
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  initSocket,
  joinContract,
  leaveContract,
  acquireLock,
  releaseLock,
  onCollabEvent,
  getSocket,
  disconnect as socketDisconnect,
} from '../utils/socket'

export const useCollaborationStore = defineStore('collaboration', () => {
  // ===== 状态 =====
  const isConnected = ref(false)
  const currentContractId = ref(null) // 当前查看的合同ID
  const onlineUsers = ref([]) // 在线用户列表
  const editLock = ref(null) // 当前锁状态
  const isLockOwner = ref(false) // 当前用户是否持有锁
  const typingUsers = ref({}) // 正在输入的用户 { userId: { user_name, field } }
  const lastEvent = ref(null) // 最近一次事件（用于UI提示）

  // ===== 计算属性 =====
  const onlineCount = computed(() => onlineUsers.value.length)
  const isLocked = computed(() => !!editLock.value && editLock.value.is_active !== false)
  const lockedByOther = computed(() => isLocked.value && !isLockOwner.value)

  // ===== 方法 =====

  /**
   * 初始化Socket连接
   */
  function connect(token, userInfo) {
    if (!token) return

    const socket = initSocket(token)
    _registerEvents()
    _bindSocketState(socket)

    // 保存用户信息供后续使用
    _userInfo = userInfo || {}
    _token = token
  }

  /**
   * 进入合同详情页
   */
  async function enterContract(contractId, userInfo) {
    if (currentContractId.value === contractId) return

    try {
      await joinContract(contractId, userInfo)
      currentContractId.value = contractId
      console.log(`[Collab] 已加入合同 ${contractId}`)
    } catch (err) {
      console.error('[Collab] 加入合同失败:', err)
      throw err
    }
  }

  /**
   * 离开合同页面
   */
  async function exitContract() {
    if (currentContractId.value) {
      await leaveContract(currentContractId.value)
      currentContractId.value = null
      onlineUsers.value = []
      editLock.value = null
      isLockOwner.value = false
      typingUsers.value = {}
    }
  }

  /**
   * 尝试获取编辑锁
   * @returns {boolean} 是否成功获取
   */
  async function requestEditLock() {
    if (isLockOwner.value) return true

    try {
      const lockData = await acquireLock(currentContractId.value, {
        session_id: _getSessionId(),
        user_name: _userInfo?.real_name || _userInfo?.username || '',
      })
      editLock.value = lockData
      isLockOwner.value = true
      return true
    } catch (errorData) {
      editLock.value = errorData
      isLockOwner.value = false
      return false
    }
  }

  /**
   * 释放编辑锁
   */
  async function freeEditLock() {
    if (!isLockOwner.value) return
    try {
      await releaseLock(currentContractId.value, { session_id: _getSessionId() })
      editLock.value = null
      isLockOwner.value = false
    } catch (e) {
      console.error('[Collab] 释放锁失败:', e)
    }
  }

  /**
   * 断开所有连接
   */
  function disconnectAll() {
    exitContract()
    socketDisconnect()
    isConnected.value = false
  }

  // ===== 内部方法 =====
  let _userInfo = {}
  let _token = ''

  function _getSessionId() {
    let sid = sessionStorage.getItem('_collab_session_id')
    if (!sid) {
      sid = `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
      sessionStorage.setItem('_collab_session_id', sid)
    }
    return sid
  }

  function _bindSocketState(socketInstance) {
    if (!socketInstance) return

    // 监听连接状态
    socketInstance.on('connect', () => { isConnected.value = true })
    socketInstance.on('disconnect', () => { isConnected.value = false })

    // 初始状态
    isConnected.value = socketInstance.connected
  }

  function _registerEvents() {
    // 用户加入
    onCollabEvent('user_joined', (data) => {
      lastEvent.value = { type: 'info', message: `${data.user?.user_name || '某用户'} 加入了协作` }
      setTimeout(() => { if (lastEvent.value?.type === 'info') lastEvent.value = null }, 3000)
    })

    // 用户离开
    onCollabEvent('user_left', (data) => {
      lastEvent.value = { type: 'info', message: `一位用户离开了协作` }
      setTimeout(() => { if (lastEvent.value?.type === 'info') lastEvent.value = null }, 3000)
    })

    // 锁被其他人获取
    onCollabEvent('lock_acquired_by_other', (data) => {
      editLock.value = data
      isLockOwner.value = false
      lastEvent.value = { type: 'warning', message: `${data.locked_by} 正在编辑此合同` }
      setTimeout(() => { if (lastEvent.value?.type === 'warning') lastEvent.value = null }, 5000)
    })

    // 锁被获取成功（自己或其他）
    onCollabEvent('lock_acquired', (data) => {
      const mySessionId = _getSessionId()
      // 判断是否是自己获取的
      const amIOwner = data.locked_by_id === (_userInfo?.id)
      if (amIOwner) {
        isLockOwner.value = true
      }
      editLock.value = data
    })

    // 锁释放
    onCollabEvent('lock_released', () => {
      editLock.value = null
      isLockOwner.value = false
      lastEvent.value = { type: 'success', message: '编辑锁已释放，现在可以编辑了' }
      setTimeout(() => { if (lastEvent.value?.type === 'success') lastEvent.value = null }, 3000)
    })

    // 合同数据更新通知
    onCollabEvent('contract_updated', (data) => {
      if (data.user) {
        lastEvent.value = { type: 'update', message: `${data.user} 更新了合同数据` }
        setTimeout(() => { if (lastEvent.value?.type === 'update') lastEvent.value = null }, 3000)
      }
    })

    // 文件上传通知
    onCollabEvent('file_uploaded', (data) => {
      if (data.user) {
        lastEvent.value = { type: 'success', message: `${data.user} 上传了文件` }
        setTimeout(() => { if (lastEvent.value?.type === 'success') lastEvent.value = null }, 3000)
      }
    })

    // 正在输入指示器
    onCollabEvent('user_typing', (data) => {
      if (data.user_id && data.user_name) {
        typingUsers.value[data.user_id] = { user_name: data.user_name, field: data.field, time: Date.now() }
        // 3秒后清除
        setTimeout(() => {
          const entry = typingUsers.value[data.user_id]
          if (entry && Date.now() - entry.time > 2500) {
            delete typingUsers.value[data.user_id]
          }
        }, 3500)
      }
    })

    // 在线状态更新
    onCollabEvent('presence_update', (data) => {
      onlineUsers.value = data.online_users || []
    })
  }

  return {
    // 状态
    isConnected,
    currentContractId,
    onlineUsers,
    editLock,
    isLockOwner,
    typingUsers,
    lastEvent,

    // 计算属性
    onlineCount,
    isLocked,
    lockedByOther,

    // 方法
    connect,
    enterContract,
    exitContract,
    requestEditLock,
    freeEditLock,
    disconnectAll,
  }
})
