<template>
  <MainLayout>
    <div class="page-shell">
      <section class="hero-banner glass-card">
        <div>
          <h2 class="hero-title">郑州捷颂信息科技有限公司合同管理平台</h2>
        </div>
        <div class="hero-actions">
          <el-button type="primary" @click="router.push('/contracts/create')">新建合同</el-button>
          <el-button @click="router.push('/contracts')">查看全部合同</el-button>
        </div>
      </section>

      <section class="metric-grid">
        <article v-for="item in cards" :key="item.label" class="metric-card">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-footnote">{{ item.footnote }}</div>
        </article>
      </section>

      <section class="section-grid">
        <el-card style="grid-column: span 12">
          <template #header>
            <div class="block-header">
              <div>
                <div class="surface-title">开票数据</div>
                <p class="surface-subtitle">汇总发票数量、金额和最近开票记录。</p>
              </div>
              <el-button type="primary" @click="router.push('/invoices')">查看发票列表</el-button>
            </div>
          </template>
          <div class="invoice-summary-grid">
            <article class="metric-card compact-card">
              <div class="metric-label">发票总数</div>
              <div class="metric-value">{{ summary.invoice_total || 0 }}</div>
              <div class="metric-footnote">系统登记的发票数量</div>
            </article>
            <article class="metric-card compact-card">
              <div class="metric-label">发票总金额</div>
              <div class="metric-value">{{ formatCurrency(summary.invoice_amount) }}</div>
              <div class="metric-footnote">登记发票的累计金额</div>
            </article>
            <div class="recent-invoice-list">
              <el-table :data="summary.recent_invoices || []" empty-text="暂无发票记录">
                <el-table-column prop="buyer_company_name" label="购买方公司名称" min-width="220" />
                <el-table-column prop="invoice_no" label="发票编号" width="160" />
                <el-table-column prop="invoice_date" label="日期" width="130" />
                <el-table-column label="金额" width="150" align="right">
                  <template #default="scope">{{ formatCurrency(scope.row.invoice_amount) }}</template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </section>

      <section class="section-grid">
        <el-card class="overview-card" style="grid-column: span 8">
          <template #header>
            <div class="block-header">
              <div>
                <div class="surface-title">最近合同</div>
                <p class="surface-subtitle">最近创建或更新的合同，方便快速继续跟进。</p>
              </div>
            </div>
          </template>
          <el-table :data="summary.recent_contracts || []" empty-text="暂无合同记录">
            <el-table-column label="项目号" width="120">
              <template #default="scope">
                <button type="button" class="project-code-chip project-code-link" @click="goDetail(scope.row.id)">
                  {{ scope.row.serial_no || '-' }}
                </button>
              </template>
            </el-table-column>
            <el-table-column prop="project_name" label="项目名称" min-width="220" />
            <el-table-column prop="contract_no" label="合同号" width="170" />
            <el-table-column label="处理状态" width="130">
              <template #default="scope">
                <span class="status-pill" :style="statusStyle(scope.row.processing_status)">{{ statusText(scope.row.processing_status) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="110">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.id)">查看详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <div class="side-stack" style="grid-column: span 4">
          <el-card>
            <template #header>
              <div>
                <div class="surface-title">快捷入口</div>
                <p class="surface-subtitle">常用操作一步直达。</p>
              </div>
            </template>
            <div class="shortcut-grid">
              <button class="shortcut-card" @click="router.push('/contracts/create')">
                <div class="shortcut-title">新建合同</div>
                <div class="shortcut-desc">录入项目、甲乙方与金额信息</div>
              </button>
              <button class="shortcut-card" @click="router.push('/contracts')">
                <div class="shortcut-title">合同台账</div>
                <div class="shortcut-desc">查看全部合同与搜索筛选</div>
              </button>
            </div>
          </el-card>
        </div>
      </section>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import { getDashboardSummary } from '../api/contract'

const router = useRouter()
const summary = reactive({})
const cards = computed(() => [
  { label: '合同总数', value: summary.total_contracts || 0, footnote: '系统当前沉淀的合同存量' },
  { label: '执行中合同', value: summary.executing_contracts || 0, footnote: '正在推进执行与履约过程' },
  { label: '已完成合同', value: summary.archived_contracts || 0, footnote: '已完成履约，可随时追溯' },
  { label: '待结清合同', value: summary.pending_settlement_contracts || 0, footnote: '建议优先跟进财务闭环' },
])
function goDetail(id) { router.push(`/contracts/${id}`) }
function formatCurrency(value) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}
function statusText(status) {
  const map = { executing: '执行中', completed: '已完成' }
  return map[status] || status || '-'
}
function statusStyle(status) {
  const map = {
    executing: { color: '#155eef', background: 'rgba(46, 125, 255, 0.12)' },
    completed: { color: '#067647', background: 'rgba(18, 183, 106, 0.12)' },
  }
  return map[status] || { color: '#475467', background: 'rgba(17,24,39,0.06)' }
}
async function loadData() {
  try {
    const { data } = await getDashboardSummary()
    Object.assign(summary, data)
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '加载首页失败')
  }
}
onMounted(loadData)
</script>

<style scoped>
.hero-banner { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; padding: 28px 30px; border-radius: 30px; }
.hero-title { margin: 0 0 12px; max-width: 760px; font-size: 36px; line-height: 1.12; letter-spacing: -0.04em; }
.hero-desc { max-width: 720px; color: #667085; font-size: 14px; line-height: 1.85; }
.hero-actions { display: flex; gap: 12px; align-self: center; }
.block-header { display: flex; align-items: center; justify-content: space-between; }
.invoice-summary-grid { display: grid; grid-template-columns: repeat(2, minmax(180px, 260px)) minmax(0, 1fr); gap: 18px; align-items: start; }
.recent-invoice-list { min-width: 0; }
.side-stack { display: flex; flex-direction: column; gap: 18px; }
.shortcut-grid { display: grid; gap: 14px; }
.shortcut-card { padding: 18px; border: 1px solid rgba(15,23,42,0.08); border-radius: 20px; background: rgba(255,255,255,0.88); cursor: pointer; text-align: left; transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease; }
.shortcut-card:hover { transform: translateY(-2px); box-shadow: 0 16px 30px rgba(15,23,42,0.1); border-color: rgba(91,108,255,0.24); }
.shortcut-title { font-weight: 700; }
.shortcut-desc { margin-top: 6px; color: #667085; font-size: 13px; }
@media (max-width: 900px) {
  .hero-banner { flex-direction: column; align-items: flex-start; }
  .invoice-summary-grid { grid-template-columns: 1fr; }
}
</style>
