<template>
  <MainLayout>
    <div class="page-shell">
      <div class="page-heading">
        <div>
          <h2 class="page-title">数据备份</h2>
          <p class="page-subtitle">导出数据库与附件，迁移服务器时可用备份包完整恢复。</p>
        </div>
        <el-button type="primary" :loading="loadingInfo" @click="loadInfo">刷新状态</el-button>
      </div>

      <section class="metric-grid compact-grid">
        <article class="metric-card compact-card">
          <div class="metric-label">数据表</div>
          <div class="metric-value">{{ info.table_count || 0 }}</div>
          <div class="metric-footnote">当前会随备份导出的表数量</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">数据行</div>
          <div class="metric-value">{{ info.row_count || 0 }}</div>
          <div class="metric-footnote">所有业务表记录合计</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">附件</div>
          <div class="metric-value">{{ info.upload_file_count || 0 }}</div>
          <div class="metric-footnote">上传目录文件数量</div>
        </article>
        <article class="metric-card compact-card">
          <div class="metric-label">附件大小</div>
          <div class="metric-value small">{{ formatBytes(info.upload_size || 0) }}</div>
          <div class="metric-footnote">迁移时会一并打包</div>
        </article>
      </section>

      <div class="backup-grid">
        <el-card>
          <template #header>
            <div>
              <div class="surface-title">导出备份</div>
              <p class="surface-subtitle">生成一个 ZIP 包，包含数据库 JSON 和 uploads 附件。</p>
            </div>
          </template>
          <div class="action-panel">
            <div class="action-icon export-icon">↓</div>
            <div class="action-text">
              <strong>建议在更新服务器前先导出一份</strong>
              <span>备份文件可以长期保存，也可以传到新服务器进行恢复。</span>
            </div>
            <el-button type="success" :loading="exporting" @click="handleExport">下载备份包</el-button>
          </div>
        </el-card>

        <el-card>
          <template #header>
            <div>
              <div class="surface-title">恢复备份</div>
              <p class="surface-subtitle">上传本系统导出的 ZIP 包，替换当前数据库和附件。</p>
            </div>
          </template>
          <div class="restore-panel">
            <div class="warning-box">
              恢复会清空当前服务器已有数据，再写入备份包内容。请先确认已经导出当前数据。
            </div>
            <input ref="fileInputRef" type="file" accept=".zip" class="hidden-input" @change="onFileChange" />
            <button type="button" class="file-picker" @click="fileInputRef?.click()">
              {{ restoreFile ? restoreFile.name : '选择备份 ZIP 文件' }}
            </button>
            <el-button
              type="danger"
              :disabled="!restoreFile"
              :loading="restoring"
              @click="handleRestore"
            >
              开始恢复
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MainLayout from '../layouts/MainLayout.vue'
import { downloadBackup, getBackupInfo, restoreBackup } from '../api/backup'

const info = reactive({})
const loadingInfo = ref(false)
const exporting = ref(false)
const restoring = ref(false)
const restoreFile = ref(null)
const fileInputRef = ref(null)

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = Number(bytes)
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

async function loadInfo() {
  loadingInfo.value = true
  try {
    const { data } = await getBackupInfo()
    Object.assign(info, data)
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载备份状态失败')
  } finally {
    loadingInfo.value = false
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const response = await downloadBackup()
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `system_backup_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('备份包已开始下载')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '导出备份失败')
  } finally {
    exporting.value = false
  }
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.zip')) {
    ElMessage.warning('请选择 ZIP 备份文件')
    event.target.value = ''
    restoreFile.value = null
    return
  }
  restoreFile.value = file
}

async function handleRestore() {
  if (!restoreFile.value) {
    ElMessage.warning('请先选择备份文件')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要恢复「${restoreFile.value.name}」吗？当前服务器数据会被备份包覆盖。`,
      '确认恢复备份',
      {
        type: 'warning',
        confirmButtonText: '确认恢复',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  restoring.value = true
  try {
    const formData = new FormData()
    formData.append('file', restoreFile.value)
    const { data } = await restoreBackup(formData)
    ElMessage.success(data.message || '恢复完成')
    restoreFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
    await loadInfo()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '恢复失败')
  } finally {
    restoring.value = false
  }
}

onMounted(loadInfo)
</script>

<style scoped>
.compact-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.compact-card { min-height: 126px; }
.metric-value.small { font-size: 28px; }
.backup-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.action-panel,
.restore-panel {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 18px;
}
.action-icon {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 28px;
  font-weight: 900;
}
.export-icon {
  background: linear-gradient(135deg, #16a34a, #22c55e);
  box-shadow: 0 16px 30px rgba(22, 163, 74, 0.22);
}
.action-text {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #667085;
  line-height: 1.6;
}
.action-text strong { color: #111827; font-size: 18px; }
.warning-box {
  padding: 14px 16px;
  border-radius: 16px;
  background: #fff7ed;
  color: #b54708;
  border: 1px solid rgba(245, 158, 11, 0.22);
  line-height: 1.7;
}
.hidden-input { display: none; }
.file-picker {
  min-width: 220px;
  height: 48px;
  padding: 0 20px;
  border: 0;
  border-radius: 16px;
  color: #fff;
  font-size: 16px;
  font-weight: 800;
  background: linear-gradient(135deg, #5b6cff, #7a89ff);
  box-shadow: 0 14px 30px rgba(91, 108, 255, 0.24);
  cursor: pointer;
}
@media (max-width: 1100px) {
  .backup-grid,
  .compact-grid { grid-template-columns: 1fr; }
}
</style>
