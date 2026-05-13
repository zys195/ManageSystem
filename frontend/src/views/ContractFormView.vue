<template>
  <MainLayout>
    <div class="page-shell" v-loading="loading">
      <div v-if="isEdit && !lockReady" class="lock-overlay">
        <div v-if="lockStatus === 'checking'" class="lock-overlay-content">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
          <p>正在获取编辑权限...</p>
        </div>

        <div v-else-if="lockStatus === 'locked'" class="lock-overlay-content locked">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#b54708" stroke-width="1.5">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 00-3-3.87" />
            <path d="M16 3.13a4 4 0 010 7.75" />
          </svg>
          <h3>{{ lockInfo?.message || '该合同正在被其他人编辑' }}</h3>
          <p v-if="lockInfo?.locked_by">当前编辑者：<strong>{{ lockInfo.locked_by }}</strong></p>
          <div class="lock-actions">
            <el-button @click="$router.push(`/contracts/${route.params.id}`)">返回详情</el-button>
            <el-button type="primary" @click="tryAcquireLock" :loading="lockStatus === 'retrying'">
              {{ lockRetryText }}
            </el-button>
          </div>
        </div>

        <div v-else-if="lockStatus === 'error'" class="lock-overlay-content error">
          <p>{{ lockError }}</p>
          <el-button type="primary" @click="tryAcquireLock">重试</el-button>
          <el-button @click="$router.push('/contracts')">返回列表</el-button>
        </div>
      </div>

      <div :style="{ filter: isEdit && !lockReady ? 'blur(4px)' : 'none', pointerEvents: isEdit && !lockReady ? 'none' : 'auto' }">
        <div class="page-heading">
          <div>
            <h2 class="page-title">{{ isEdit ? '编辑合同' : '新建合同' }}</h2>
            <p class="page-subtitle">录入合同主档、甲乙方、财务与状态信息。</p>
          </div>
          <div>
            <el-button @click="handleCancel">返回</el-button>
            <el-button type="primary" :loading="submitting" :disabled="isEdit && !lockReady" @click="submit">
              {{ isEdit ? '保存修改' : '创建合同' }}
            </el-button>
          </div>
        </div>

        <div class="section-grid form-grid">
          <el-card style="grid-column: span 8">
            <template #header>
              <div>
                <div class="surface-title">基础信息</div>
                <p class="surface-subtitle">合同主体、甲乙方与项目归属信息。</p>
              </div>
            </template>

            <el-form :model="form" label-position="top">
              <div class="form-section">
                <el-form-item label="项目号">
                  <el-input v-model="form.serial_no" placeholder="例如 XM-2026-0001" @input="clearFieldError('serial_no')" />
                  <div v-if="formErrors.serial_no" class="field-error">{{ formErrors.serial_no }}</div>
                </el-form-item>

                <el-form-item label="合同号">
                  <el-input v-model="form.contract_no" placeholder="缺失时可先填内部编号" @input="clearFieldError('contract_no')" />
                  <div v-if="formErrors.contract_no" class="field-error">{{ formErrors.contract_no }}</div>
                </el-form-item>

                <el-form-item label="合同名称">
                  <el-input v-model="form.contract_name" placeholder="请输入合同名称" @input="clearFieldError('contract_name')" />
                  <div v-if="formErrors.contract_name" class="field-error">{{ formErrors.contract_name }}</div>
                </el-form-item>

                <el-form-item label="项目名称">
                  <el-input v-model="form.project_name" placeholder="请输入项目名称" @input="clearFieldError('project_name')" />
                  <div v-if="formErrors.project_name" class="field-error">{{ formErrors.project_name }}</div>
                </el-form-item>

                <el-form-item label="签订日期">
                  <el-date-picker
                    v-model="form.sign_date"
                    type="date"
                    value-format="YYYY-MM-DD"
                    style="width: 100%"
                    @change="clearFieldError('sign_date')"
                  />
                  <div v-if="formErrors.sign_date" class="field-error">{{ formErrors.sign_date }}</div>
                </el-form-item>

                <el-form-item label="合同类型">
                  <el-input v-model="form.contract_type" placeholder="非必填" />
                </el-form-item>
              </div>

              <div class="divider"></div>
              <div class="surface-title small-title">业务归属</div>

              <div class="form-section">
                <el-form-item label="甲方单位">
                  <el-input
                    v-model="form.party_a_name"
                    placeholder="请输入甲方单位"
                    @input="handlePartyNameInput('party_a')"
                  />
                  <div v-if="formErrors.party_a_name" class="field-error">{{ formErrors.party_a_name }}</div>
                </el-form-item>

                <el-form-item label="乙方单位">
                  <el-input
                    v-model="form.party_b_name"
                    placeholder="请输入乙方单位"
                    @input="handlePartyNameInput('party_b')"
                  />
                  <div v-if="formErrors.party_b_name" class="field-error">{{ formErrors.party_b_name }}</div>
                </el-form-item>

                <el-form-item label="负责人">
                  <el-input v-model="form.owner_name" placeholder="非必填" />
                </el-form-item>

                <el-form-item label="业务归属">
                  <el-input v-model="form.department_id" placeholder="非必填" />
                </el-form-item>
              </div>
            </el-form>
          </el-card>

          <div class="side-stack" style="grid-column: span 4">
            <el-card>
              <template #header>
                <div>
                  <div class="surface-title">财务信息</div>
                  <p class="surface-subtitle">金额与币种信息保持简洁明晰。</p>
                </div>
              </template>
              <el-form :model="form" label-position="top">
                <el-form-item label="合同金额">
                  <el-input-number v-model="form.contract_amount" :precision="2" :min="0" style="width: 100%" />
                </el-form-item>
                <el-form-item label="币种">
                  <el-input v-model="form.currency" />
                </el-form-item>
              </el-form>
            </el-card>

            <el-card>
              <template #header>
                <div>
                  <div class="surface-title">状态信息</div>
                  <p class="surface-subtitle">预设成更适合实际业务的状态录入方式。</p>
                </div>
              </template>
              <el-form :model="form" label-position="top">
                <el-form-item label="处理状态">
                  <el-select v-model="form.processing_status" style="width: 100%">
                    <el-option label="执行中" value="executing" />
                    <el-option label="已完成" value="completed" />
                  </el-select>
                </el-form-item>
                <el-form-item label="是否结清">
                  <el-select v-model="form.settlement_status" style="width: 100%">
                    <el-option label="待结清" value="pending" />
                    <el-option label="部分结清" value="partially_settled" />
                    <el-option label="全部结清" value="settled" />
                  </el-select>
                </el-form-item>
                <el-form-item label="审批状态">
                  <el-select v-model="form.approval_status" style="width: 100%" disabled>
                    <el-option label="审批中" value="pending_approval" />
                    <el-option label="已通过" value="approved" />
                    <el-option label="已驳回" value="rejected" />
                  </el-select>
                  <p class="field-tip" v-if="isEdit && form.approval_status === 'rejected'">
                    审批已驳回，修改后可重新提交审批
                  </p>
                  <p class="field-tip" v-else-if="isEdit && form.approval_status === 'pending_approval'">
                    审批中，暂不可修改
                  </p>
                  <p class="field-tip" v-else-if="isEdit && form.approval_status === 'approved'">
                    审批已通过
                  </p>
                </el-form-item>
              </el-form>
            </el-card>

            <el-card>
              <template #header>
                <div>
                  <div class="surface-title">备注说明</div>
                  <p class="surface-subtitle">补充业务背景、履约或审批说明。</p>
                </div>
              </template>
              <el-form :model="form" label-position="top">
                <el-form-item label="备注">
                  <el-input v-model="form.description" type="textarea" :rows="7" placeholder="请输入补充说明" />
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import MainLayout from '../layouts/MainLayout.vue'
import { createContract, getContract, updateContract } from '../api/contract'
import { acquireLockAPI, releaseLockAPI } from '../api/collab'
import { useCollaborationStore } from '../stores/collaboration'

const route = useRoute()
const router = useRouter()
const collab = useCollaborationStore()

const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const submitting = ref(false)

const lockReady = ref(!isEdit.value)
const lockStatus = ref(isEdit.value ? 'checking' : '')
const lockInfo = ref(null)
const lockError = ref('')
const retryCountdown = ref(10)

let lockTimer = null
let retryTimer = null

const lockRetryText = computed(() => {
  if (lockStatus.value === 'retrying') return '重试中...'
  if (retryCountdown.value > 0) return `${retryCountdown.value}秒后可重试`
  return '尝试获取编辑权'
})

const form = reactive({
  serial_no: '',
  contract_no: '',
  contract_name: '',
  project_name: '',
  contract_type: '',
  sign_date: '',
  party_a_company_id: undefined,
  party_b_company_id: undefined,
  party_a_name: '',
  party_b_name: '',
  owner_user_id: undefined,
  owner_name: '',
  department_id: '',
  contract_amount: 0,
  currency: 'CNY',
  processing_status: 'executing',
  settlement_status: 'pending',
  approval_status: 'pending_approval',
  archive_status: 'unarchived',
  description: '',
  version: 1,
})

const formErrors = reactive({
  serial_no: '',
  contract_no: '',
  contract_name: '',
  project_name: '',
  sign_date: '',
  party_a_name: '',
  party_b_name: '',
})

function clearFieldError(field) {
  formErrors[field] = ''
}

function handlePartyNameInput(type) {
  if (type === 'party_a') {
    form.party_a_company_id = undefined
    clearFieldError('party_a_name')
    return
  }

  form.party_b_company_id = undefined
  clearFieldError('party_b_name')
}

function validateForm() {
  const requiredMessage = '请填写数据'
  formErrors.serial_no = form.serial_no ? '' : requiredMessage
  formErrors.contract_no = form.contract_no ? '' : requiredMessage
  formErrors.contract_name = form.contract_name ? '' : requiredMessage
  formErrors.project_name = form.project_name ? '' : requiredMessage
  formErrors.sign_date = form.sign_date ? '' : requiredMessage
  formErrors.party_a_name = form.party_a_name ? '' : requiredMessage
  formErrors.party_b_name = form.party_b_name ? '' : requiredMessage

  return !Object.values(formErrors).some(Boolean)
}

async function loadMeta() {}

async function loadDetail() {
  if (!isEdit.value) return

  loading.value = true
  try {
    const { data } = await getContract(route.params.id)
    Object.assign(form, data)
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载合同失败')
  } finally {
    loading.value = false
  }
}

async function tryAcquireLock() {
  if (!isEdit.value) return

  lockStatus.value = 'retrying'
  try {
    await acquireLockAPI(route.params.id)
    lockReady.value = true
    lockStatus.value = 'ready'
    lockInfo.value = null
    collab.isLockOwner = true

    if (collab.isConnected) {
      collab.requestEditLock().catch((error) => {
        console.warn('[Lock] WebSocket lock sync failed:', error)
      })
    }

    startLockHeartbeat()
  } catch (error) {
    lockStatus.value = 'locked'
    lockInfo.value = error.response?.data || error
    startRetryCountdown()
  }
}

function startRetryCountdown() {
  stopRetryTimer()
  retryCountdown.value = 10
  retryTimer = setInterval(() => {
    retryCountdown.value -= 1
    if (retryCountdown.value <= 0) {
      stopRetryTimer()
    }
  }, 1000)
}

function stopRetryTimer() {
  if (retryTimer) {
    clearInterval(retryTimer)
    retryTimer = null
  }
}

function startLockHeartbeat() {
  stopLockHeartbeat()
  lockTimer = setInterval(async () => {
    try {
      const { heartbeatLock } = await import('../api/collab')
      await heartbeatLock(route.params.id)
    } catch (error) {
      console.warn('[Lock] 心跳失败:', error)
    }
  }, 25000)
}

function stopLockHeartbeat() {
  if (lockTimer) {
    clearInterval(lockTimer)
    lockTimer = null
  }
}

async function handleCancel() {
  if (isEdit.value && lockReady.value) {
    try {
      await releaseLockAPI(route.params.id)
      collab.freeEditLock()
    } catch (_) {
      // 取消时释放锁失败不影响返回。
    }
    stopLockHeartbeat()
  }

  if (isEdit.value) {
    router.push(`/contracts/${route.params.id}`)
  } else {
    router.push('/contracts')
  }
}

async function submit() {
  if (!validateForm()) return

  submitting.value = true
  try {
    if (isEdit.value) {
      if (!lockReady.value) {
        ElMessage.warning('请先获取编辑权限')
        return
      }

      const result = await updateContract(route.params.id, { ...form })
      if (result.status === 409) {
        await ElMessageBox.alert(
          result.data?.message || '数据已被他人修改，请刷新后重试',
          '冲突提示',
          { confirmButtonText: '我知道了', type: 'warning' },
        )
        await loadDetail()
        return
      }

      ElMessage.success('更新成功')
      try {
        await releaseLockAPI(route.params.id)
        collab.freeEditLock()
      } catch (_) {
        // 保存成功后的释放锁失败不影响结果页跳转。
      }
      stopLockHeartbeat()
      lockReady.value = false
      router.push(`/contracts/${route.params.id}`)
    } else {
      const { data } = await createContract({ ...form })
      ElMessage.success('创建成功')
      router.push(`/contracts/${data.id}`)
    }
  } catch (error) {
    const msg = error.response?.data?.message || '保存失败'
    if (error.response?.status === 409) {
      ElMessage.warning(msg)
      await loadDetail()
    } else {
      ElMessage.error(msg)
    }
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    await loadMeta()
    await loadDetail()

    if (isEdit.value) {
      await tryAcquireLock()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '初始化页面失败')
  }
})

onUnmounted(() => {
  stopLockHeartbeat()
  stopRetryTimer()
  if (isEdit.value && lockReady.value) {
    releaseLockAPI(route.params.id).catch(() => {})
    collab.freeEditLock()
  }
})
</script>

<style scoped>
.form-grid { align-items: start; }
.form-section { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 18px; }
.side-stack { display: flex; flex-direction: column; gap: 18px; }
.divider { margin: 6px 0 18px; height: 1px; background: rgba(15, 23, 42, 0.06); }
.small-title { margin-bottom: 14px; font-size: 16px; }
.field-error { margin-top: 6px; color: #f56c6c; font-size: 12px; line-height: 1.2; }
.field-tip { margin-top: 6px; color: #667085; font-size: 12px; line-height: 1.4; }

@media (max-width: 900px) {
  .form-section { grid-template-columns: 1fr; }
}

.lock-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lock-overlay-content {
  text-align: center;
  max-width: 420px;
}

.lock-overlay-content p { color: #667085; font-size: 15px; margin-top: 12px; }
.lock-overlay-content h3 { font-size: 20px; color: #111827; margin-bottom: 4px; }
.lock-overlay-content strong { color: #b54708; }
.lock-overlay-content svg { margin: 0 auto 16px; display: block; }
.lock-overlay-content.error p { color: #dc2626; }
.lock-actions { margin-top: 24px; display: flex; gap: 12px; justify-content: center; }

</style>
