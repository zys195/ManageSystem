<template>
  <MainLayout>
    <div class="page-shell" v-loading="loading">
      <!-- 协作状态通知条 -->
      <transition name="slide-down">
        <div v-if="collab.lastEvent" :class="['collab-notification', `collab-notification--${collab.lastEvent.type}`]">
          <span>{{ collab.lastEvent.message }}</span>
        </div>
      </transition>

      <section class="detail-hero glass-card">
        <div>
          <h2 class="hero-name">{{ contract.contract_name || '合同详情' }}</h2>
          <p class="hero-meta">{{ contract.project_name || '未填写项目名称' }} · {{ contract.contract_no || '未填写合同号' }}</p>
          <div class="hero-tags">
            <span class="status-pill" :style="statusStyle(contract.processing_status)">{{ statusText(contract.processing_status) }}</span>
            <span class="status-pill" :style="settlementStyle(contract.settlement_status)">{{ settlementText(contract.settlement_status) }}</span>
            <span class="status-pill" :style="approvalStyle(contract.approval_status)">{{ approvalText(contract.approval_status) }}</span>
            <!-- 在线协作指示器 -->
            <span v-if="collab.isConnected && collab.currentContractId == route.params.id" class="online-badge">
              <span class="online-dot"></span>
              {{ collab.onlineCount }} 人在线
            </span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button @click="$router.push('/contracts')">返回列表</el-button>
          <!-- 编辑按钮：根据锁状态显示不同状态 -->
          <template v-if="!collab.lockedByOther || collab.isLockOwner">
            <el-button type="primary" @click="goToEdit">编辑合同</el-button>
          </template>
          <template v-else>
            <el-tooltip
              :content="`正在被 ${collab.editLock?.locked_by} 编辑，请稍后重试`"
              placement="bottom"
            >
              <el-button type="primary" disabled>编辑中 ({{ lockCountdown }}s)</el-button>
            </el-tooltip>
          </template>
          <!-- 审批操作按钮 -->
          <template v-if="canSubmitApproval">
            <el-button type="success" @click="openApprovalDialog('submit')">提交审批</el-button>
          </template>
          <template v-if="canApprove">
            <el-button type="success" @click="openApprovalDialog('approve')">通过</el-button>
            <el-button type="danger" @click="openApprovalDialog('reject')">驳回</el-button>
          </template>
          <template v-if="canResubmit">
            <el-button type="warning" @click="openApprovalDialog('resubmit')">重新提交</el-button>
          </template>
        </div>

        <!-- 在线用户头像列表 -->
        <div v-if="collab.isConnected && collab.currentContractId == route.params.id && collab.onlineUsers.length > 0" class="online-avatars">
          <el-avatar
            v-for="(user, idx) in displayOnlineUsers"
            :key="user.session_id"
            :size="32"
            :style="{ marginLeft: idx > 0 ? '-10px' : '0', zIndex: idx }"
          >
            {{ (user.user_name || '?')[0] }}
          </el-avatar>
          <span class="online-label">{{ collab.onlineCount }}人正在查看</span>
        </div>
      </section>

      <!-- 编辑锁提示卡片 -->
      <section v-if="collab.isLocked" class="lock-banner" :class="{ 'lock-banner--mine': collab.isLockOwner }">
        <div class="lock-banner-icon">
          <svg v-if="collab.isLockOwner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#067647" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#b54708" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
        </div>
        <div class="lock-banner-text">
          <strong v-if="collab.isLockOwner">你已获取编辑权</strong>
          <strong v-else>{{ collab.editLock?.locked_by }} 正在编辑</strong>
          <p v-if="collab.isLockOwner">其他人无法同时编辑，完成后请保存退出</p>
          <p v-else>该用户正在编辑此合同，请等待其完成或 {{ lockCountdown }} 秒后自动解锁</p>
        </div>
      </section>

      <section class="metric-grid compact-grid">
        <article class="metric-card compact-card">
          <div class="metric-label">合同金额</div>
          <div class="metric-value amount-text">{{ formatCurrency(contract.contract_amount) }}</div>
          <div class="metric-footnote">合同主金额</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">已收款</div>
          <div class="metric-value amount-text">{{ formatCurrency(contract.received_amount) }}</div>
          <div class="metric-footnote">合同回款进度</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">已付款 / 未付款</div>
          <div class="metric-value amount-text">{{ formatCurrency(contract.paid_amount) }}</div>
          <div class="metric-footnote">未付款 {{ formatCurrency(contract.unpaid_amount) }}</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">未收款</div>
          <div class="metric-value amount-text">{{ formatCurrency(contract.unreceived_amount) }}</div>
          <div class="metric-footnote">结合回款节奏持续跟进</div>
        </article>
      </section>

      <div class="section-grid detail-grid">
        <el-card style="grid-column: span 7">
          <template #header>
            <div>
              <div class="surface-title">合同概览</div>
              <p class="surface-subtitle">首个字段已改为项目号，和列表、表单保持一致。</p>
            </div>
          </template>
          <div class="overview-grid">
            <div class="overview-item"><span>项目号</span><strong>{{ contract.serial_no || '-' }}</strong></div>
            <div class="overview-item"><span>合同号</span><strong>{{ contract.contract_no || '-' }}</strong></div>
            <div class="overview-item"><span>项目名称</span><strong>{{ contract.project_name || '-' }}</strong></div>
            <div class="overview-item"><span>合同类型</span><strong>{{ contract.contract_type || '-' }}</strong></div>
            <div class="overview-item"><span>甲方单位</span><strong>{{ contract.party_a_name || '-' }}</strong></div>
            <div class="overview-item"><span>乙方单位</span><strong>{{ contract.party_b_name || '-' }}</strong></div>
            <div class="overview-item"><span>签订日期</span><strong>{{ contract.sign_date || '-' }}</strong></div>
            <div class="overview-item"><span>币种</span><strong>{{ contract.currency || '-' }}</strong></div>
            <div class="overview-item"><span>负责人</span><strong>{{ contract.owner_name || '非必填' }}</strong></div>
            <div class="overview-item"><span>业务归属</span><strong>{{ contract.department_name || contract.department_id || '非必填' }}</strong></div>
            <div class="overview-item full"><span>备注说明</span><strong>{{ contract.description || '暂无备注' }}</strong></div>
          </div>
        </el-card>

        <div class="side-stack" style="grid-column: span 5">
          <el-card>
            <template #header>
              <div>
                <div class="surface-title">上传附件</div>
                <p class="surface-subtitle">合同正文、报价单与发票附件支持分类上传。</p>
              </div>
            </template>
            <el-form label-position="top">
              <el-form-item label="文件类型">
                <el-select v-model="fileCategory" style="width:100%">
                  <el-option label="合同正文" value="contract_main" />
                  <el-option label="报价单" value="quote" />
                  <el-option label="验收附件" value="acceptance" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
              <el-upload
                v-model:file-list="uploadFileList"
                :auto-upload="false"
                :show-file-list="true"
                :on-change="onFileChange"
                :before-upload="beforeUpload"
                :limit="1"
              >
                <template #trigger>
                  <el-button>选择文件</el-button>
                </template>
                <template #tip>
                  <div class="el-upload__tip">文件大小不超过 5MB</div>
                </template>
              </el-upload>
              <el-button type="primary" style="margin-top: 12px" @click="submitFile">上传附件</el-button>
            </el-form>
          </el-card>

          <el-card>
            <template #header>
              <div>
                <div class="surface-title">快速录入</div>
                <p class="surface-subtitle">在同一页面新增财务与验收记录。</p>
              </div>
            </template>
            <el-tabs>
              <el-tab-pane label="收款">
                <el-form :model="receiptForm" label-position="top">
                  <el-form-item label="金额" required><el-input-number v-model="receiptForm.receipt_amount" :min="0" :precision="2" style="width:100%" /></el-form-item>
                  <el-form-item label="日期" required><el-date-picker v-model="receiptForm.receipt_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
                  <el-form-item label="方式"><el-input v-model="receiptForm.receipt_method" /></el-form-item>
                  <el-button type="primary" @click="submitReceipt">新增收款</el-button>
                </el-form>
              </el-tab-pane>
              <el-tab-pane label="付款">
                <el-form :model="paymentForm" label-position="top">
                  <el-form-item label="金额" required><el-input-number v-model="paymentForm.payment_amount" :min="0" :precision="2" style="width:100%" /></el-form-item>
                  <el-form-item label="日期" required><el-date-picker v-model="paymentForm.payment_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
                  <el-form-item label="方式"><el-input v-model="paymentForm.payment_method" /></el-form-item>
                  <el-button type="primary" @click="submitPayment">新增付款</el-button>
                </el-form>
              </el-tab-pane>
              <el-tab-pane label="验收">
                <el-form :model="acceptanceForm" label-position="top">
                  <el-form-item label="金额" required><el-input-number v-model="acceptanceForm.acceptance_amount" :min="0" :precision="2" style="width:100%" /></el-form-item>
                  <el-form-item label="日期" required><el-date-picker v-model="acceptanceForm.acceptance_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
                  <el-form-item label="说明"><el-input v-model="acceptanceForm.acceptance_note" /></el-form-item>
                  <el-button type="primary" @click="submitAcceptance">新增验收</el-button>
                </el-form>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </div>
      </div>

      <el-card>
        <template #header>
          <div>
            <div class="surface-title">记录与附件</div>
            <p class="surface-subtitle">把收款、付款、验收与附件统一为更清晰的查看区。</p>
          </div>
        </template>
        <el-tabs>
          <el-tab-pane :label="`收款 (${contract.receipts?.length || 0})`">
            <el-table :data="contract.receipts || []" empty-text="暂无收款记录">
              <el-table-column label="金额" width="140"><template #default="scope">{{ formatCurrency(scope.row.receipt_amount) }}</template></el-table-column>
              <el-table-column prop="receipt_date" label="日期" width="130" />
              <el-table-column prop="receipt_method" label="方式" min-width="180" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane :label="`付款 (${contract.payments?.length || 0})`">
            <el-table :data="contract.payments || []" empty-text="暂无付款记录">
              <el-table-column label="金额" width="140"><template #default="scope">{{ formatCurrency(scope.row.payment_amount) }}</template></el-table-column>
              <el-table-column prop="payment_date" label="日期" width="130" />
              <el-table-column prop="payment_method" label="方式" min-width="180" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane :label="`验收 (${contract.acceptances?.length || 0})`">
            <el-table :data="contract.acceptances || []" empty-text="暂无验收记录">
              <el-table-column label="金额" width="140"><template #default="scope">{{ formatCurrency(scope.row.acceptance_amount) }}</template></el-table-column>
              <el-table-column prop="acceptance_date" label="日期" width="130" />
              <el-table-column prop="acceptance_note" label="说明" min-width="180" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane :label="`附件 (${contract.files?.length || 0})`">
            <el-table :data="contract.files || []" empty-text="暂无附件">
              <el-table-column prop="origin_name" label="文件名" min-width="240" />
              <el-table-column prop="file_category" label="类型" width="120" />
              <el-table-column prop="version_no" label="版本" width="90" />
              <el-table-column label="操作" width="160">
                <template #default="scope">
                  <el-button link type="primary" @click="handleDownload(scope.row)">下载</el-button>
                  <el-button
                    v-if="authStore.permissions.includes('file:delete')"
                    link
                    type="danger"
                    @click="handleDeleteFile(scope.row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="审批历史">
            <el-timeline>
              <el-timeline-item
                v-for="item in contract.approval_history || []"
                :key="item.id"
                :type="approvalTimelineType(item.action)"
                :timestamp="formatTime(item.created_at)"
                placement="top"
              >
                <div class="approval-timeline-item">
                  <strong>{{ item.operator_name }}</strong>
                  <span class="approval-action">{{ approvalActionText(item.action) }}</span>
                  <span v-if="item.comment" class="approval-comment">「{{ item.comment }}」</span>
                </div>
              </el-timeline-item>
              <el-timeline-item v-if="!contract.approval_history || !contract.approval_history.length" type="info" timestamp="">
                <div class="approval-timeline-item">暂无审批记录</div>
              </el-timeline-item>
            </el-timeline>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>

    <!-- 审批操作对话框 -->
    <el-dialog
      v-model="approvalDialogVisible"
      :title="approvalDialogType === 'submit' ? '提交审批' : approvalDialogType === 'approve' ? '审批通过' : approvalDialogType === 'reject' ? '审批驳回' : '重新提交审批'"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <el-form-item :label="approvalDialogType === 'reject' ? '审批意见（必填）' : '审批意见（可选）'">
          <el-input
            v-model="approvalComment"
            type="textarea"
            :rows="4"
            :placeholder="approvalDialogType === 'reject' ? '请填写驳回原因' : '请输入审批意见'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="approvalDialogVisible = false">取消</el-button>
          <el-button
            :type="approvalDialogType === 'reject' ? 'danger' : 'primary'"
            @click="confirmApprovalAction"
          >
            {{ approvalDialogType === 'submit' ? '确认提交' : approvalDialogType === 'approve' ? '确认通过' : approvalDialogType === 'reject' ? '确认驳回' : '确认重新提交' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </MainLayout>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MainLayout from '../layouts/MainLayout.vue'
import { addAcceptance, addPayment, addReceipt, deleteContractFile, downloadContractFile, getContract, uploadFile, submitApproval, approveContract, rejectContract, resubmitApproval } from '../api/contract'
import { useCollaborationStore } from '../stores/collaboration'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const contract = reactive({})
const selectedFile = ref(null)
const uploadFileList = ref([])
const fileCategory = ref('contract_main')

const receiptForm = reactive({ receipt_amount: 0, receipt_date: '', receipt_method: '' })
const paymentForm = reactive({ payment_amount: 0, payment_date: '', payment_method: '' })
const acceptanceForm = reactive({ acceptance_amount: 0, acceptance_date: '', acceptance_note: '' })

// 协作相关
const collab = useCollaborationStore()
let lockTimer = null

// 显示的在线用户（限制最多展示5个）
const displayOnlineUsers = computed(() => {
  return collab.onlineUsers.slice(0, 5)
})

// 锁倒计时（秒）
const lockCountdown = computed(() => {
  if (!collab.editLock?.expires_in) return 0
  return Math.max(collab.editLock.expires_in, 0)
})

function formatCurrency(value) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: contract.currency || 'CNY',
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function statusText(status) {
  const map = { executing: '执行中', completed: '已完成' }
  return map[status] || status || '-'
}
function settlementText(status) {
  const map = { pending: '待结清', partially_settled: '部分结清', settled: '全部结清' }
  return map[status] || status || '-'
}
function statusStyle(status) {
  const map = {
    executing: { color: '#155eef', background: 'rgba(46,125,255,0.12)' },
    completed: { color: '#067647', background: 'rgba(18,183,106,0.12)' },
  }
  return map[status] || { color: '#475467', background: 'rgba(17,24,39,0.06)' }
}
function settlementStyle(status) {
  const map = {
    pending: { color: '#b54708', background: 'rgba(247,144,9,0.14)' },
    partially_settled: { color: '#155eef', background: 'rgba(46,125,255,0.12)' },
    settled: { color: '#067647', background: 'rgba(18,183,106,0.12)' },
  }
  return map[status] || map.pending
}

function goToEdit() {
  router.push(`/contracts/${route.params.id}/edit`)
}

// ========== 审批相关 ==========
const authStore = useAuthStore()

const canSubmitApproval = computed(() => {
  // 已驳回状态，且有编辑权限
  return contract.approval_status === 'rejected'
    && authStore.permissions.includes('contract:update')
})

const canApprove = computed(() => {
  // 审批中状态，且有审批权限
  return contract.approval_status === 'pending_approval'
    && authStore.permissions.includes('approval:approve')
})

const canResubmit = computed(() => {
  // 已驳回状态，且有编辑权限
  return contract.approval_status === 'rejected'
    && authStore.permissions.includes('contract:update')
})

const approvalDialogVisible = ref(false)
const approvalDialogType = ref('submit')
const approvalComment = ref('')

function approvalText(status) {
  const map = {
    pending_approval: '审批中',
    approved: '已通过',
    rejected: '已驳回',
  }
  return map[status] || status || '-'
}

function approvalStyle(status) {
  const map = {
    pending_approval: { color: '#b54708', background: 'rgba(247,144,9,0.14)' },
    approved: { color: '#067647', background: 'rgba(18,183,106,0.12)' },
    rejected: { color: '#b42318', background: 'rgba(240,68,56,0.10)' },
  }
  return map[status] || { color: '#475467', background: 'rgba(17,24,39,0.06)' }
}

function approvalActionText(action) {
  const map = {
    submit: '提交审批',
    approve: '审批通过',
    reject: '审批驳回',
    resubmit: '重新提交',
  }
  return map[action] || action
}

function approvalTimelineType(action) {
  const map = {
    submit: 'primary',
    approve: 'success',
    reject: 'danger',
    resubmit: 'warning',
  }
  return map[action] || 'info'
}

function formatTime(val) {
  if (!val) return ''
  return new Date(val).toLocaleString('zh-CN')
}

function openApprovalDialog(type) {
  approvalDialogType.value = type
  approvalComment.value = ''
  approvalDialogVisible.value = true
}

async function confirmApprovalAction() {
  const action = approvalDialogType.value
  const comment = approvalComment.value.trim()
  try {
    if (action === 'submit') {
      await submitApproval(route.params.id, { comment })
      ElMessage.success('已提交审批')
    } else if (action === 'approve') {
      await approveContract(route.params.id, { comment })
      ElMessage.success('审批通过')
    } else if (action === 'reject') {
      if (!comment) {
        ElMessage.warning('驳回时必须填写审批意见')
        return
      }
      await rejectContract(route.params.id, { comment })
      ElMessage.success('已驳回')
    } else if (action === 'resubmit') {
      await resubmitApproval(route.params.id, { comment })
      ElMessage.success('已重新提交审批')
    }
    approvalDialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '操作失败')
  }
}

async function loadData() {
  loading.value = true
  try {
    const { data } = await getContract(route.params.id)
    Object.assign(contract, data)
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载合同详情失败')
  } finally {
    loading.value = false
  }
}

function resetForms() {
  receiptForm.receipt_amount = 0
  receiptForm.receipt_date = ''
  receiptForm.receipt_method = ''
  paymentForm.payment_amount = 0
  paymentForm.payment_date = ''
  paymentForm.payment_method = ''
  acceptanceForm.acceptance_amount = 0
  acceptanceForm.acceptance_date = ''
  acceptanceForm.acceptance_note = ''
}

function hasRequiredAmountAndDate(amount, date) {
  return Number(amount) > 0 && !!date
}

async function submitReceipt() {
  if (!hasRequiredAmountAndDate(receiptForm.receipt_amount, receiptForm.receipt_date)) {
    ElMessage.warning('请填写必填信息')
    return
  }

  try {
    await addReceipt(route.params.id, receiptForm)
    ElMessage.success('新增收款成功')
    resetForms()
    loadData()
  } catch (error) { ElMessage.error(error.response?.data?.message || '新增收款失败') }
}
async function submitPayment() {
  if (!hasRequiredAmountAndDate(paymentForm.payment_amount, paymentForm.payment_date)) {
    ElMessage.warning('请填写必填信息')
    return
  }

  try {
    await addPayment(route.params.id, paymentForm)
    ElMessage.success('新增付款成功')
    resetForms()
    loadData()
  } catch (error) { ElMessage.error(error.response?.data?.message || '新增付款失败') }
}
async function submitAcceptance() {
  if (!hasRequiredAmountAndDate(acceptanceForm.acceptance_amount, acceptanceForm.acceptance_date)) {
    ElMessage.warning('请填写必填信息')
    return
  }

  try {
    await addAcceptance(route.params.id, acceptanceForm)
    ElMessage.success('新增验收成功')
    resetForms()
    loadData()
  } catch (error) { ElMessage.error(error.response?.data?.message || '新增验收失败') }
}

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB

function beforeUpload(rawFile) {
  if (rawFile.size > MAX_FILE_SIZE) {
    const sizeMB = (rawFile.size / (1024 * 1024)).toFixed(2)
    ElMessage.warning(`文件大小为 ${sizeMB}MB，超过 5MB 限制，请选择较小的文件`)
    return false
  }
  return true
}

function onFileChange(file) {
  const rawFile = file.raw
  if (!rawFile) {
    selectedFile.value = null
    uploadFileList.value = []
    return
  }

  if (!beforeUpload(rawFile)) {
    selectedFile.value = null
    uploadFileList.value = []
    return
  }

  selectedFile.value = rawFile
}

async function handleDownload(fileRow) {
  try {
    const response = await downloadContractFile(fileRow.id)
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileRow.origin_name
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) { ElMessage.error(error.response?.data?.message || '下载失败') }
}

async function handleDeleteFile(fileRow) {
  try {
    await ElMessageBox.confirm(
      `确定删除附件「${fileRow.origin_name}」吗？删除后将不再显示在附件列表中。`,
      '删除确认',
      {
        type: 'warning',
        customClass: 'solid-confirm-box',
        confirmButtonText: '确定',
        cancelButtonText: '取消',
      }
    )
    await deleteContractFile(fileRow.id)
    ElMessage.success('附件已删除')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '删除附件失败')
    }
  }
}

async function submitFile() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('file_category', fileCategory.value)
    await uploadFile(route.params.id, formData)
    selectedFile.value = null
    uploadFileList.value = []
    ElMessage.success('上传成功')
    loadData()
  } catch (error) { ElMessage.error(error.response?.data?.message || '上传失败') }
}

onMounted(async () => {
  await loadData()

  // 初始化协作连接
  const auth = useAuthStore()
  if (auth.token) {
    collab.connect(auth.token, auth.user)

    try {
      await collab.enterContract(route.params.id, {
        user_name: auth.user?.real_name || auth.user?.username,
        session_id: sessionStorage.getItem('_collab_session_id'),
      })
    } catch (e) {
      console.warn('[Collab] 加入协作失败:', e)
    }
  }

  // 定期刷新锁状态
  lockTimer = setInterval(() => {
    if (collab.isLocked && !collab.isLockOwner) {
      // 被他人锁定时，定期刷新锁信息以更新倒计时
      // 通过REST API查询最新锁状态
      import('../api/collab').then((m) => m.getLockStatus(route.params.id)).catch(() => {})
    }
  }, 5000)
})

onUnmounted(async () => {
  if (lockTimer) clearInterval(lockTimer)
  // 离开时清理协作连接
  await collab.exitContract()
})
</script>

<style scoped>
.detail-hero { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 28px 30px; border-radius: 30px; position: relative; }
.hero-caption { color: #667085; font-size: 13px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
.hero-name { margin: 12px 0 8px; font-size: 36px; line-height: 1.08; letter-spacing: -0.04em; }
.hero-meta { margin: 0; color: #667085; }
.hero-tags { display: flex; gap: 10px; margin-top: 18px; flex-wrap: wrap; align-items: center; }
.hero-actions { display: flex; gap: 12px; }
.compact-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.compact-card { min-height: 126px; }
.detail-grid { align-items: start; }
.side-stack { display: flex; flex-direction: column; gap: 18px; }
.overview-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.overview-item { padding: 18px; border-radius: 18px; background: rgba(248,250,252,0.86); border: 1px solid rgba(15,23,42,0.05); }
.overview-item span { display: block; color: #667085; font-size: 12px; margin-bottom: 8px; }
.overview-item strong { line-height: 1.65; }
.overview-item.full { grid-column: 1 / -1; }

/* 在线标识 */
.online-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  color: #067647;
  background: rgba(16,185,129,0.08);
  border: 1px solid rgba(16,185,129,0.15);
}
.online-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #10b981;
  animation: pulse-green 2s ease-in-out infinite;
}
@keyframes pulse-green {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
  50% { opacity: .8; box-shadow: 0 0 0 4px rgba(16,185,129,0); }
}
.online-avatars {
  position: absolute; bottom: 12px; left: 28px;
  display: flex; align-items: center; gap: 4px;
}
.online-label { margin-left: 10px; font-size: 12px; color: #667085; font-weight: 500; }

/* 协作通知 */
.collab-notification {
  padding: 10px 20px; text-align: center; font-size: 14px; font-weight: 500;
  border-radius: 12px; margin-bottom: 16px; animation: fadeIn 0.3s ease;
}
.collab-notification--info { background: #eff6ff; color: #155eef; border: 1px solid rgba(59,130,246,0.15); }
.collab-notification--warning { background: #fffbeb; color: #b54708; border: 1px solid rgba(245,158,11,0.15); }
.collab-notification--success { background: #ecfdf5; color: #067647; border: 1px solid rgba(16,185,129,0.15); }
.collab-notification--update { background: #f5f3ff; color: #6d28d9; border: 1px solid rgba(124,58,237,0.15); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }

/* 编辑锁横幅 */
.lock-banner {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 16px 20px; border-radius: 16px; margin-bottom: 20px;
  background: #fffbeb; border: 1px solid rgba(245,158,11,0.2);
}
.lock-banner--mine {
  background: #ecfdf5; border-color: rgba(16,185,129,0.2);
}
.lock-banner-icon { flex-shrink: 0; margin-top: 2px; }
.lock-banner-text strong { font-size: 15px; }
.lock-banner-text p { margin: 4px 0 0; font-size: 13px; color: #667085; }

.slide-down-enter-active { transition: all 0.35s ease-out; }
.slide-down-leave-active { transition: all 0.25s ease-in; }
.slide-down-enter-from { opacity: 0; transform: translateY(-16px); }
.slide-down-leave-to { opacity: 0; transform: translateY(-8px); }

.side-stack .el-card:first-child :deep(.el-upload .el-button),
.side-stack .el-card:first-child :deep(.el-form > .el-button--primary) {
  width: 129px;
  height: 48px;
  min-height: 48px;
  padding: 0 20px;
  border: none !important;
  border-radius: 16px !important;
  font-size: 16px;
  font-weight: 700;
  line-height: 1;
}

.side-stack .el-card:first-child :deep(.el-upload .el-button) {
  color: #fff !important;
  background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%) !important;
  box-shadow: 0 14px 30px rgba(22, 163, 74, 0.24);
}

.side-stack :deep(.el-upload .el-button:hover),
.side-stack :deep(.el-upload .el-button:focus) {
  color: #fff !important;
  transform: translateY(-1px);
  box-shadow: 0 18px 34px rgba(22, 163, 74, 0.3);
}

@media (max-width: 900px) {
  .detail-hero, .hero-actions { flex-direction: column; align-items: flex-start; }
  .compact-grid, .overview-grid { grid-template-columns: 1fr; }
  .online-avatars { position: static; margin-top: 12px; }
}

/* 审批时间线 */
.approval-timeline-item { line-height: 1.8; }
.approval-timeline-item strong { margin-right: 8px; }
.approval-action { color: #667085; font-size: 13px; margin-right: 8px; }
.approval-comment { color: #155eef; font-size: 13px; }
</style>

<style>
.solid-confirm-box.el-message-box {
  width: 420px;
  padding: 0;
  overflow: hidden;
  border-radius: 22px !important;
  background: rgba(255, 255, 255, 0.96) !important;
  border: 1px solid rgba(255, 255, 255, 0.76) !important;
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.26) !important;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.solid-confirm-box .el-message-box__header {
  padding: 22px 24px 8px;
}

.solid-confirm-box .el-message-box__content {
  padding: 12px 24px 22px;
}

.solid-confirm-box .el-message-box__status {
  color: #f59e0b !important;
}

.solid-confirm-box .el-message-box__title,
.solid-confirm-box .el-message-box__message {
  color: #111827 !important;
}

.solid-confirm-box .el-message-box__title {
  font-size: 20px;
  font-weight: 800;
}

.solid-confirm-box .el-message-box__message {
  color: #475467 !important;
  font-size: 14px;
  line-height: 1.7;
}

.solid-confirm-box .el-message-box__btns {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 22px;
  background: #fff !important;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}

.solid-confirm-box .el-message-box__btns .el-button {
  min-width: 86px;
  border-radius: 14px;
  font-weight: 700;
}

.solid-confirm-box .el-message-box__btns .el-button--primary {
  background: #5b6cff;
  border-color: #5b6cff;
  box-shadow: 0 12px 28px rgba(91, 108, 255, 0.26);
}
</style>
