<template>
  <MainLayout>
    <div class="page-shell">
      <div class="page-heading">
        <div>
          <h2 class="page-title">发票列表</h2>
          <p class="page-subtitle">管理客户、发票编号、日期与金额信息。</p>
        </div>
        <div class="invoice-actions">
          <el-button type="primary" @click="openCreateDialog">新增发票</el-button>
          <el-button type="success" :loading="ocrUploading" @click="openOcrFilePicker">上传电子发票图片</el-button>
          <el-button type="warning" :loading="exporting" @click="handleExport">导出Excel</el-button>
        </div>
      </div>

      <section class="metric-grid compact-grid">
        <article class="metric-card compact-card">
          <div class="metric-label">发票总数</div>
          <div class="metric-value">{{ total }}</div>
          <div class="metric-footnote">当前筛选下的发票数量</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">发票总金额</div>
          <div class="metric-value">{{ formatCurrency(totalAmount) }}</div>
          <div class="metric-footnote">系统累计开票金额</div>
        </article>
      </section>

      <el-card>
        <template #header>
          <div class="filter-head">
            <div>
              <div class="surface-title">筛选条件</div>
              <p class="surface-subtitle">支持客户公司名称和发票编号搜索。</p>
            </div>
            <div class="filter-actions">
              <el-button @click="resetQuery">重置</el-button>
              <el-button type="primary" @click="loadData">查询</el-button>
            </div>
          </div>
        </template>
        <el-input v-model="query.keyword" placeholder="搜索客户公司名称 / 发票编号" clearable @keyup.enter="loadData" />
      </el-card>

      <el-card>
        <template #header>
          <div>
            <div class="surface-title">发票台账</div>
            <p class="surface-subtitle">客户、编号、日期和金额集中呈现。</p>
          </div>
        </template>
        <el-table :data="items" v-loading="loading" empty-text="暂无发票数据">
          <el-table-column prop="buyer_company_name" label="客户公司名称" min-width="260" />
          <el-table-column prop="invoice_no" label="发票编号" width="190" />
          <el-table-column prop="invoice_date" label="日期" width="150" />
          <el-table-column label="金额" width="160" align="right">
            <template #default="scope">
              <span class="amount-text">{{ formatCurrency(scope.row.invoice_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template #default="scope">
              <button type="button" class="table-action is-danger" @click="onDelete(scope.row.id)">删除</button>
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

      <el-dialog v-model="showCreateDialog" width="860px" append-to-body class="invoice-dialog" modal-class="invoice-dialog-overlay">
        <div class="invoice-form-shell">
          <div class="invoice-form-heading">
            <div>
              <h3>新增发票</h3>
              <p>录入客户、发票编号、日期与金额信息。</p>
            </div>
          </div>

          <div class="invoice-form-grid">
            <el-card class="invoice-form-card">
              <template #header>
                <div>
                  <div class="surface-title">基础信息</div>
                  <p class="surface-subtitle">发票归属、编号、日期与金额信息。</p>
                </div>
              </template>
              <el-form :model="form" label-position="top">
                <el-form-item label="客户公司名称" required>
                  <el-input v-model="form.buyer_company_name" placeholder="请输入客户公司名称" />
                </el-form-item>
                <el-form-item label="发票编号" required>
                  <el-input v-model="form.invoice_no" placeholder="请输入发票编号" />
                </el-form-item>
                <el-form-item label="日期" required>
                  <el-date-picker v-model="form.invoice_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="金额" required>
                  <el-input-number v-model="form.invoice_amount" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </div>
        <template #footer>
          <div class="invoice-dialog-footer">
            <el-button @click="showCreateDialog = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="submitInvoice">保存</el-button>
          </div>
        </template>
      </el-dialog>

      <el-dialog v-model="showOcrUploadDialog" width="760px" append-to-body class="ocr-upload-dialog" modal-class="invoice-dialog-overlay">
        <div class="ocr-upload-shell">
          <div class="invoice-form-heading">
            <div>
              <h3>上传电子发票图片</h3>
              <p>支持单张或批量上传图片，系统会尝试识别发票信息并自动新增到台账。</p>
            </div>
          </div>

          <el-card class="ocr-upload-card">
            <template #header>
              <div>
                <div class="surface-title">图片文件</div>
                <p class="surface-subtitle">支持常见图片格式，可一次选择多张。</p>
              </div>
            </template>
            <el-upload
              v-model:file-list="ocrUploadFiles"
              drag
              multiple
              accept="image/*"
              :auto-upload="false"
            >
              <div class="ocr-upload-drop-title">点击或拖拽图片到这里</div>
              <div class="ocr-upload-drop-tip">识别成功后会自动创建发票记录</div>
            </el-upload>
          </el-card>
        </div>
        <template #footer>
          <div class="invoice-dialog-footer">
            <el-button @click="showOcrUploadDialog = false">取消</el-button>
            <el-button type="primary" :loading="ocrUploading" @click="submitOcrImages">开始识别</el-button>
          </div>
        </template>
      </el-dialog>
    </div>
  </MainLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MainLayout from '../layouts/MainLayout.vue'
import { createInvoice, deleteInvoice, exportInvoices, getInvoices, uploadInvoiceImages } from '../api/contract'

const items = ref([])
const total = ref(0)
const totalAmount = ref(0)
const loading = ref(false)
const saving = ref(false)
const exporting = ref(false)
const ocrUploading = ref(false)
const showCreateDialog = ref(false)
const showOcrUploadDialog = ref(false)
const ocrUploadFiles = ref([])
const query = reactive({ keyword: '', page: 1, page_size: 10 })
const form = reactive({
  buyer_company_name: '',
  invoice_no: '',
  invoice_date: '',
  invoice_amount: 0,
})

function formatCurrency(value) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function resetForm() {
  form.buyer_company_name = ''
  form.invoice_no = ''
  form.invoice_date = ''
  form.invoice_amount = 0
}

function openCreateDialog() {
  resetForm()
  showCreateDialog.value = true
}

function openOcrFilePicker() {
  ocrUploadFiles.value = []
  showOcrUploadDialog.value = true
}

async function submitOcrImages() {
  const files = ocrUploadFiles.value.map((file) => file.raw).filter(Boolean)
  if (!files.length) return

  const invalidFile = files.find((file) => !file.type.startsWith('image/'))
  if (invalidFile) {
    ElMessage.warning('仅支持上传图片文件')
    return
  }

  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))

  ocrUploading.value = true
  try {
    const { data } = await uploadInvoiceImages(formData)
    if (data.failed?.length) {
      ElMessage.warning(data.message || `新增 ${data.created?.length || 0} 条，失败 ${data.failed.length} 条`)
    } else {
      ElMessage.success(data.message || '识别并新增成功')
    }
    showOcrUploadDialog.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'OCR识别失败')
  } finally {
    ocrUploading.value = false
  }
}

async function loadData() {
  loading.value = true
  try {
    const { data } = await getInvoices(query)
    items.value = data.items || []
    total.value = data.total || 0
    totalAmount.value = data.total_amount || 0
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载发票失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''
  query.page = 1
  loadData()
}

async function submitInvoice() {
  if (!form.buyer_company_name || !form.invoice_no || !form.invoice_date || Number(form.invoice_amount) <= 0) {
    ElMessage.warning('请填写必填信息')
    return
  }

  saving.value = true
  try {
    await createInvoice({ ...form })
    ElMessage.success('新增成功')
    showCreateDialog.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '新增失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除该发票吗？', '删除确认', {
      type: 'warning',
      customClass: 'solid-confirm-box',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await deleteInvoice(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '删除失败')
    }
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const { data } = await exportInvoices({ keyword: query.keyword })
    const url = window.URL.createObjectURL(new Blob([data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `发票列表_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.compact-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.compact-card { min-height: 126px; }
.invoice-actions,
.filter-head,
.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.filter-head { justify-content: space-between; }
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}
.table-action {
  appearance: none;
  border: 0;
  background: transparent;
  padding: 0;
  color: #ff6b72;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.invoice-form-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.invoice-form-heading {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 4px 2px 0;
}
.invoice-form-heading h3 {
  margin: 0;
  color: #111827;
  font-size: 28px;
  line-height: 1.2;
  letter-spacing: 0;
}
.invoice-form-heading p {
  margin: 8px 0 0;
  color: #667085;
  font-size: 14px;
}
.invoice-form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
.invoice-form-card {
  min-height: 0;
}
.invoice-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.ocr-upload-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.ocr-upload-card {
  background: rgba(255, 255, 255, 0.92) !important;
}
.ocr-upload-drop-title {
  color: #111827;
  font-size: 16px;
  font-weight: 700;
}
.ocr-upload-drop-tip {
  margin-top: 8px;
  color: #667085;
  font-size: 13px;
}
@media (max-width: 900px) {
  .compact-grid { grid-template-columns: 1fr; }
  .filter-head { flex-direction: column; align-items: flex-start; }
  .invoice-form-grid { grid-template-columns: 1fr; }
}
</style>

<style>
.invoice-dialog-overlay.el-overlay {
  background-color: rgba(15, 23, 42, 0.46) !important;
}

.el-dialog.invoice-dialog {
  background: rgba(245, 247, 252, 0.96) !important;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 28px !important;
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.26) !important;
  overflow: hidden;
}

.el-dialog.ocr-upload-dialog {
  background: rgba(245, 247, 252, 0.96) !important;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 28px !important;
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.26) !important;
  overflow: hidden;
}

.el-dialog.invoice-dialog .el-dialog__header {
  display: none;
}

.el-dialog.ocr-upload-dialog .el-dialog__header {
  display: none;
}

.el-dialog.invoice-dialog .el-dialog__body {
  padding: 28px 30px 10px;
}

.el-dialog.ocr-upload-dialog .el-dialog__body {
  padding: 28px 30px 10px;
}

.el-dialog.invoice-dialog .el-dialog__footer {
  padding: 8px 30px 28px;
}

.el-dialog.ocr-upload-dialog .el-dialog__footer {
  padding: 8px 30px 28px;
}

.el-dialog.invoice-dialog .el-card {
  background: rgba(255, 255, 255, 0.92) !important;
}

.el-dialog.ocr-upload-dialog .el-upload-dragger {
  background: rgba(255, 255, 255, 0.92) !important;
  border: 2px dashed rgba(91, 108, 255, 0.24) !important;
  border-radius: 18px !important;
  padding: 34px 18px !important;
}

.el-dialog.ocr-upload-dialog .el-upload-list__item {
  background: rgba(248, 250, 252, 0.96);
  border-radius: 12px;
  color: #111827;
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
