<template>
  <MainLayout>
    <div class="page-shell">
      <div class="page-heading">
        <div>
          <h2 class="page-title">合同列表</h2>
          <p class="page-subtitle">重新梳理筛选、统计与表格密度，让台账页面更像正式商用产品。</p>
        </div>
        <div>
          <el-button type="primary" @click="$router.push('/contracts/create')">新建合同</el-button>
          <el-button type="success" @click="showImportDialog = true">
            <el-icon style="margin-right: 4px"><Upload /></el-icon>导入Excel
          </el-button>
          <el-button type="warning" :loading="exporting" @click="openExportDialog">
            <el-icon style="margin-right: 4px"><Download /></el-icon>导出Excel
          </el-button>
        </div>
      </div>

      <div class="metric-grid compact-grid">
        <article class="metric-card compact-card">
          <div class="metric-label">当前页合同</div>
          <div class="metric-value">{{ items.length }}</div>
          <div class="metric-footnote">当前筛选条件下加载结果</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">合同总数</div>
          <div class="metric-value">{{ total }}</div>
          <div class="metric-footnote">包含所有分页数据</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">当前页合同额</div>
          <div class="metric-value">{{ formatCurrency(pageAmount) }}</div>
          <div class="metric-footnote">帮助快速感知本页金额规模</div>
        </article>
      </div>

      <el-card>
        <template #header>
          <div class="filter-head">
            <div>
              <div class="surface-title">筛选条件</div>
              <p class="surface-subtitle">支持关键词、处理状态与审批状态过滤。</p>
            </div>
            <div class="filter-actions">
              <el-button @click="resetQuery">重置</el-button>
              <el-button type="primary" @click="searchContracts">查询</el-button>
            </div>
          </div>
        </template>

        <div class="filter-grid">
          <el-input
            v-model="query.keyword"
            placeholder="搜索合同号 / 项目名称 / 合同名称"
            clearable
            @keyup.enter="searchContracts"
          />
          <el-select v-model="query.processing_status" placeholder="处理状态" clearable @change="searchContracts">
            <el-option label="草稿" value="draft" />
            <el-option label="执行中" value="executing" />
            <el-option label="已完成" value="completed" />
          </el-select>
          <el-select v-model="query.approval_status" placeholder="审批状态" clearable @change="searchContracts">
            <el-option label="草稿" value="draft" />
            <el-option label="审批中" value="pending_approval" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </div>
      </el-card>

      <el-card>
        <template #header>
          <div class="block-header">
            <div>
              <div class="surface-title">合同台账</div>
              <p class="surface-subtitle">金额、甲乙方、状态与操作统一在同一层级呈现。</p>
            </div>
          </div>
        </template>

        <el-table :data="items" v-loading="loading" empty-text="暂无合同数据">
          <el-table-column prop="serial_no" label="序号" width="110" />
          <el-table-column label="项目 / 合同" min-width="260">
            <template #default="scope">
              <div class="project-cell">
                <div class="project-name">{{ scope.row.project_name }}</div>
                <div class="project-contract">{{ scope.row.contract_name }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="contract_no" label="合同号" width="180" />
          <el-table-column label="甲乙双方" min-width="220">
            <template #default="scope">
              <div class="party-cell">
                <span>{{ scope.row.party_a_name || '-' }}</span>
                <span class="party-sep">/</span>
                <span>{{ scope.row.party_b_name || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="合同金额" width="150">
            <template #default="scope">
              <span class="amount-text">{{ formatCurrency(scope.row.contract_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="收款 / 付款" width="170">
            <template #default="scope">
              <div class="dual-amount">
                <span>收{{ formatCurrency(scope.row.received_amount) }}</span>
                <span>付{{ formatCurrency(scope.row.paid_amount) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="处理状态" width="130">
            <template #default="scope">
              <span class="status-pill" :style="statusStyle(scope.row.processing_status)">
                {{ statusText(scope.row.processing_status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="审批状态" width="130">
            <template #default="scope">
              <span class="status-pill" :style="approvalStyle(scope.row.approval_status)">
                {{ approvalText(scope.row.approval_status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="170" fixed="right" align="center">
            <template #default="scope">
              <div class="op-actions">
                <button type="button" class="table-action is-primary" @click="$router.push(`/contracts/${scope.row.id}`)">查看</button>
                <button type="button" class="table-action is-primary" @click="$router.push(`/contracts/${scope.row.id}/edit`)">编辑</button>
                <button type="button" class="table-action is-danger" @click="onDelete(scope.row.id)">删除</button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="total, prev, pager, next"
            :total="total"
            :page-size="query.page_size"
            :current-page="query.page"
            @current-change="(page) => { query.page = page; loadData() }"
          />
        </div>
      </el-card>

      <!-- 导入Excel对话框 -->
      <el-dialog v-model="showImportDialog" title="导入合同" width="520px" :close-on-click-modal="false" destroy-on-close append-to-body class="import-dialog" modal-class="import-dialog-overlay">
        <div class="import-body">
          <!-- 顶部提示 -->
          <div class="import-tip-bar">
            <el-icon color="#155eef"><InfoFilled /></el-icon>
            <span>上传 Excel 文件后将自动解析并批量创建合同记录</span>
          </div>

          <!-- 文件上传区 -->
          <div class="import-upload-zone" :class="{ 'is-active': !!importFile }" @click="$refs.fileInput?.click()">
            <input ref="fileInput" type="file" accept=".xlsx,.xls" style="display:none" @change="onFileInputChange" />
            <template v-if="!importFile">
              <el-icon :size="36" color="#c0c4cc"><UploadFilled /></el-icon>
              <p class="upload-text">点击选择 Excel 文件</p>
              <p class="upload-hint">支持 .xlsx / .xls 格式，单次最多导入 500 条</p>
            </template>
            <template v-else>
              <el-icon :size="28" color="#067647"><CircleCheckFilled /></el-icon>
              <p class="upload-filename">{{ importFile.name }}</p>
              <el-button type="danger" link size="small" @click.stop="clearFile">移除文件</el-button>
            </template>
          </div>

          <!-- 工作表 -->
          <div class="import-form-row">
            <label class="import-label">工作表名称</label>
            <el-input v-model="importSheetName" placeholder="留空则使用第一个工作表" clearable size="default" />
            <span class="import-field-tip">可选</span>
          </div>

          <!-- 模板下载 -->
          <div class="import-template-row">
            <el-icon color="#909393"><Document /></el-icon>
            <span>不确定格式？</span>
            <el-button type="primary" link @click="downloadTemplate">下载标准模板</el-button>
          </div>
        </div>

        <template #footer>
          <div class="dialog-footer">
            <el-button @click="showImportDialog = false">取消</el-button>
            <el-button type="primary" :loading="importing" :disabled="!importFile" @click="handleImport">
              {{ importing ? '导入中...' : '开始导入' }}
            </el-button>
          </div>
        </template>
      </el-dialog>

      <el-dialog v-model="showExportDialog" title="选择导出合同项目" width="760px" :close-on-click-modal="false" append-to-body class="export-dialog" modal-class="import-dialog-overlay">
        <div class="export-dialog-body">
          <div class="import-tip-bar">
            <el-icon color="#155eef"><InfoFilled /></el-icon>
            <span>请选择需要导出的合同项目，列表会沿用当前筛选条件。</span>
          </div>

          <el-table
            ref="exportTableRef"
            :data="exportCandidates"
            v-loading="exportCandidatesLoading"
            row-key="id"
            empty-text="暂无可导出的合同"
            max-height="420"
            @selection-change="onExportSelectionChange"
          >
            <el-table-column type="selection" width="48" />
            <el-table-column prop="serial_no" label="项目号" width="120" />
            <el-table-column label="项目 / 合同" min-width="240">
              <template #default="scope">
                <div class="project-cell">
                  <div class="project-name">{{ scope.row.project_name }}</div>
                  <div class="project-contract">{{ scope.row.contract_name }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="contract_no" label="合同号" width="160" />
            <el-table-column label="合同金额" width="140" align="right">
              <template #default="scope">{{ formatCurrency(scope.row.contract_amount) }}</template>
            </el-table-column>
          </el-table>

          <div class="export-selection-foot">
            已选择 {{ selectedExportContracts.length }} 项
          </div>
        </div>

        <template #footer>
          <div class="dialog-footer">
            <el-button @click="showExportDialog = false">取消</el-button>
            <el-button type="primary" :loading="exporting" @click="handleExport">
              导出选中项目
            </el-button>
          </div>
        </template>
      </el-dialog>

    </div>
  </MainLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload,
  Download,
  InfoFilled,
  UploadFilled,
  CircleCheckFilled,
  Document,
} from '@element-plus/icons-vue'
import MainLayout from '../layouts/MainLayout.vue'
import { getContracts, deleteContract, importContractsFromExcel, downloadImportTemplate, exportContracts } from '../api/contract'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({
  keyword: '',
  processing_status: '',
  approval_status: '',
  page: 1,
  page_size: 10,
})

// 导入相关状态
const showImportDialog = ref(false)
const importing = ref(false)
const importFile = ref(null)
const importSheetName = ref('')
const fileInputRef = ref(null)

// 导出状态
const exporting = ref(false)
const showExportDialog = ref(false)
const exportCandidates = ref([])
const exportCandidatesLoading = ref(false)
const selectedExportContracts = ref([])
const exportTableRef = ref(null)

function onFileInputChange(event) {
  const file = event.target.files?.[0]
  if (!file) return

  const ext = file.name.toLowerCase()
  if (!ext.endsWith('.xlsx') && !ext.endsWith('.xls')) {
    ElMessage.error('仅支持 Excel 文件（.xlsx / .xls）')
    event.target.value = ''
    return
  }
  importFile.value = file
}

function clearFile() {
  importFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

async function downloadTemplate() {
  try {
    const { data } = await downloadImportTemplate()
    const url = window.URL.createObjectURL(new Blob([data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '合同导入模板.xlsx')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('模板下载成功')
  } catch (error) {
    ElMessage.error('模板下载失败，请重试')
  }
}

async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择要导入的 Excel 文件')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要导入文件「${importFile.value.name}」吗？导入后将自动创建合同记录。`,
      '确认导入',
      {
        type: 'info',
        customClass: 'solid-confirm-box',
        modalClass: 'blur-confirm-overlay',
        confirmButtonText: '开始导入',
        cancelButtonText: '取消',
      }
    )
  } catch {
    return // 用户取消
  }

  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    if (importSheetName.value) {
      formData.append('sheet', importSheetName.value)
    }

    const { data: res } = await importContractsFromExcel(formData)

    ElMessage.success(res.message || `导入完成：成功 ${res.imported_count || 0} 条`)
    showImportDialog.value = false
    clearFile()
    importSheetName.value = ''
    loadData() // 刷新列表
  } catch (error) {
    const msg = error.response?.data?.message || error.message || '导入失败，请检查文件格式后重试'
    ElMessage.error(msg)
  } finally {
    importing.value = false
  }
}

async function openExportDialog() {
  showExportDialog.value = true
  selectedExportContracts.value = []
  exportCandidatesLoading.value = true
  try {
    const { data } = await getContracts({
      ...buildQueryParams(),
      page: 1,
      page_size: 100,
    })
    exportCandidates.value = data.items || []
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载可导出合同失败')
  } finally {
    exportCandidatesLoading.value = false
  }
}

function onExportSelectionChange(rows) {
  selectedExportContracts.value = rows
}

async function handleExport() {
  if (!selectedExportContracts.value.length) {
    ElMessage.warning('请先选择要导出的合同项目')
    return
  }

  exporting.value = true
  try {
    const { data } = await exportContracts({
      ...buildQueryParams(),
      ids: selectedExportContracts.value.map((item) => item.id).join(','),
    })
    const url = window.URL.createObjectURL(new Blob([data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `合同台账_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
    showExportDialog.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

const pageAmount = computed(() =>
  items.value.reduce((sum, item) => sum + Number(item.contract_amount || 0), 0)
)

function formatCurrency(value) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function statusText(status) {
  const map = {
    draft: '草稿',
    executing: '执行中',
    completed: '已完成',
  }
  return map[status] || status || '-'
}

function statusStyle(status) {
  const map = {
    draft: { color: '#475467', background: 'rgba(17,24,39,0.06)' },
    executing: { color: '#155eef', background: 'rgba(46,125,255,0.12)' },
    completed: { color: '#067647', background: 'rgba(18,183,106,0.12)' },
  }
  return map[status] || map.draft
}

function approvalText(status) {
  const map = {
    draft: '草稿',
    pending_approval: '审批中',
    approved: '已通过',
    rejected: '已驳回',
  }
  return map[status] || status || '-'
}

function approvalStyle(status) {
  const map = {
    draft: { color: '#475467', background: 'rgba(17,24,39,0.06)' },
    pending_approval: { color: '#b54708', background: 'rgba(247,144,9,0.14)' },
    approved: { color: '#067647', background: 'rgba(18,183,106,0.12)' },
    rejected: { color: '#b42318', background: 'rgba(240,68,56,0.10)' },
  }
  return map[status] || map.draft
}

function buildQueryParams() {
  return {
    keyword: query.keyword || undefined,
    processing_status: query.processing_status || undefined,
    approval_status: query.approval_status || undefined,
  }
}

function searchContracts() {
  query.page = 1
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const { data } = await getContracts({
      ...buildQueryParams(),
      page: query.page,
      page_size: query.page_size,
    })
    items.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''
  query.processing_status = ''
  query.approval_status = ''
  query.page = 1
  loadData()
}

async function onDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除该合同吗？删除后将无法在列表中看到它。', '删除确认', {
      type: 'warning',
      customClass: 'solid-confirm-box',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await deleteContract(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '删除失败')
    }
  }
}

onMounted(loadData)
</script>
<style scoped>
.compact-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.compact-card {
  min-height: 126px;
}

.filter-head,
.block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.filter-actions {
  display: flex;
  gap: 12px;
}

.filter-grid {
  display: grid;
  grid-template-columns: 1.8fr 0.8fr 0.8fr;
  gap: 16px;
}

.project-cell,
.party-cell,
.dual-amount {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.project-name {
  font-weight: 700;
}

.project-contract,
.dual-amount,
.party-cell {
  color: #667085;
  font-size: 13px;
}

.party-cell {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.party-sep {
  opacity: 0.5;
}

.op-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.table-action {
  appearance: none;
  border: none;
  background: transparent;
  padding: 0;
  margin: 0;
  line-height: 1;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.table-action.is-primary {
  color: #5b6cff;
}

.table-action.is-danger {
  color: #ff6b72;
}

.table-action:hover {
  opacity: 0.82;
}

.table-action:focus {
  outline: none;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

@media (max-width: 900px) {
  .compact-grid,
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .filter-head,
  .block-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

/* ===== 导入对话框样式 ===== */
.import-body {
  padding: 0;
}

.import-tip-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #eff6ff;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #1e40af;
  margin-bottom: 20px;
}

.import-upload-zone {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  padding: 32px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
  margin-bottom: 18px;
  background: #fafbfc;
}

.import-upload-zone:hover {
  border-color: #409eff;
  background: #f0f7ff;
}

.import-upload-zone.is-active {
  border-color: #067647;
  border-style: solid;
  background: #ecfdf5;
}

.upload-text {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
  margin: 0;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.upload-filename {
  font-size: 14px;
  color: #067647;
  font-weight: 600;
  margin: 0;
}

.import-form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.import-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
  min-width: 80px;
}

.import-form-row .el-input {
  flex: 1;
}

.import-field-tip {
  font-size: 12px;
  color: #c0c4cc;
  white-space: nowrap;
}

.import-template-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #909399;
  padding-top: 4px;
}

.dialog-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.export-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.export-selection-foot {
  color: #667085;
  font-size: 13px;
  text-align: right;
}
</style>

<style>
/* ===== 导入合同 - 亚克力模糊风格 ===== */
.import-dialog-overlay.el-overlay {
  background-color: rgba(0, 0, 0, 0.35) !important;
}

.el-dialog.import-dialog {
  background: rgba(255, 255, 255, 0.94) !important;
  backdrop-filter: blur(12px) saturate(1.2) !important;
  -webkit-backdrop-filter: blur(12px) saturate(1.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 16px !important;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.12),
    0 2px 8px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.6) !important;
  overflow: hidden;
}

.el-dialog.export-dialog {
  background: rgba(255, 255, 255, 0.94) !important;
  backdrop-filter: blur(12px) saturate(1.2) !important;
  -webkit-backdrop-filter: blur(12px) saturate(1.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 16px !important;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.12),
    0 2px 8px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.6) !important;
  overflow: hidden;
}

/* 鏍囬鏍?*/
.el-dialog.import-dialog .el-dialog__header {
  background: transparent;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.el-dialog.import-dialog .el-dialog__title {
  font-weight: 600;
  color: #1a1a2e;
}

.el-dialog.export-dialog .el-dialog__title {
  font-weight: 600;
  color: #1a1a2e;
}

/* 搴曢儴鎸夐挳鍖?*/
.el-dialog.import-dialog .el-dialog__footer {
  background: transparent;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

.el-dialog.export-dialog .el-dialog__footer {
  background: transparent;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

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

.blur-confirm-overlay.el-overlay {
  background-color: rgba(15, 23, 42, 0.26) !important;
  backdrop-filter: blur(10px) saturate(1.08);
  -webkit-backdrop-filter: blur(10px) saturate(1.08);
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





