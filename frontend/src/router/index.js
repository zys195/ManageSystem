import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const LoginView = () => import('../views/LoginView.vue')
const DashboardView = () => import('../views/DashboardView.vue')
const ContractListView = () => import('../views/ContractListView.vue')
const ContractFormView = () => import('../views/ContractFormView.vue')
const ContractDetailView = () => import('../views/ContractDetailView.vue')
const InvoiceListView = () => import('../views/InvoiceListView.vue')
const SystemBackupView = () => import('../views/SystemBackupView.vue')

const routes = [
  { path: '/login', component: LoginView, meta: { title: '登录' } },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: DashboardView, meta: { requiresAuth: true, title: '首页概览' } },
  { path: '/contracts', component: ContractListView, meta: { requiresAuth: true, title: '合同列表' } },
  { path: '/contracts/create', component: ContractFormView, meta: { requiresAuth: true, title: '新建合同' } },
  { path: '/contracts/:id/edit', component: ContractFormView, meta: { requiresAuth: true, title: '编辑合同' } },
  { path: '/contracts/:id', component: ContractDetailView, meta: { requiresAuth: true, title: '合同详情' } },
  { path: '/invoices', component: InvoiceListView, meta: { requiresAuth: true, title: '发票列表' } },
  { path: '/backup', component: SystemBackupView, meta: { requiresAuth: true, title: '数据备份' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return '/login'
  }
  if (auth.isLoggedIn && !auth.user) {
    try {
      await auth.fetchMe()
    } catch (e) {
      auth.logout()
      return '/login'
    }
  }
  if (to.path === '/login' && auth.isLoggedIn) {
    return '/dashboard'
  }
})

router.afterEach((to) => {
  document.title = `${to.meta?.title || '合同管理系统'} - 合同管理系统`
})

export default router
