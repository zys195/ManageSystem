<template>
  <div class="layout-root">
    <aside class="layout-aside">
      <div class="brand-block">
        <div class="brand-mark">
          <img :src="logoUrl" alt="JS logo" class="brand-logo" />
        </div>
        <div>
          <div class="brand-title">郑州捷颂信息科技有限公司</div>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        class="aside-menu"
        router
        background-color="transparent"
        text-color="rgba(255,255,255,0.72)"
        active-text-color="#ffffff"
      >
        <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
          <span class="menu-dot"></span>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-foot">
        <div class="aside-foot-label">当前用户</div>
        <div class="aside-user">{{ auth.user?.real_name || '未登录' }}</div>
        <div class="aside-role">{{ auth.user?.roles?.map((item) => item.name).join(' / ') || '访客' }}</div>
      </div>
    </aside>

    <div class="layout-main-wrap">
      <header class="layout-header glass-card">
        <div>
          <div class="header-label">{{ todayLabel }}</div>
          <h1 class="header-title">{{ currentTitle }}</h1>
        </div>
        <div class="header-actions">
          <div class="header-user-card">
            <div class="header-user-name">{{ auth.user?.real_name || '未登录' }}</div>
            <div class="header-user-meta">{{ auth.user?.department || '系统访问中' }}</div>
          </div>
          <el-button class="change-password-btn" @click="openPasswordDialog">修改密码</el-button>
          <el-button class="logout-btn" @click="logout">退出登录</el-button>
        </div>
      </header>

      <main class="layout-main">
        <slot />
      </main>
    </div>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px" class="password-dialog">
      <el-form label-position="top">
        <el-form-item label="原密码">
          <el-input v-model="passwordForm.current_password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="isChangingPassword" @click="submitPasswordChange">保存修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { changePasswordApi } from '../api/auth'
import logoUrl from '../assets/js-logo.svg'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const passwordDialogVisible = ref(false)
const isChangingPassword = ref(false)
const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: '',
})

const menus = [
  { label: '首页概览', path: '/dashboard' },
  { label: '合同列表', path: '/contracts' },
  { label: '发票列表', path: '/invoices' },
  { label: '新建合同', path: '/contracts/create' },
  { label: '数据备份', path: '/backup' },
]

const currentTitle = computed(() => route.meta?.title || '合同管理系统')
const activeMenu = computed(() => {
  if (route.path.startsWith('/contracts')) {
    return route.path === '/contracts/create' ? '/contracts/create' : '/contracts'
  }
  if (route.path.startsWith('/invoices')) return '/invoices'
  if (route.path.startsWith('/backup')) return '/backup'
  return route.path
})
const todayLabel = computed(() => {
  const now = new Date()
  return now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
})

function logout() {
  auth.logout()
  router.push('/login')
}

function resetPasswordForm() {
  passwordForm.current_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
}

function openPasswordDialog() {
  resetPasswordForm()
  passwordDialogVisible.value = true
}

async function submitPasswordChange() {
  if (!passwordForm.current_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    ElMessage.warning('请完整填写密码信息')
    return
  }
  if (passwordForm.new_password.length < 6) {
    ElMessage.warning('新密码至少需要 6 位')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }

  isChangingPassword.value = true
  try {
    const { data } = await changePasswordApi({
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success(data.message || '密码修改成功')
    passwordDialogVisible.value = false
    resetPasswordForm()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '密码修改失败')
  } finally {
    isChangingPassword.value = false
  }
}
</script>

<style scoped>
.layout-root {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 24px;
  padding: 22px;
}

.layout-aside {
  position: sticky;
  top: 22px;
  height: calc(100vh - 44px);
  padding: 24px 18px;
  border-radius: 32px;
  background: linear-gradient(180deg, rgba(10, 15, 27, 0.95), rgba(18, 28, 48, 0.88));
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 24px 60px rgba(2, 6, 23, 0.32);
  color: #fff;
  display: flex;
  flex-direction: column;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 12px 22px;
}

.brand-mark {
  flex: 0 0 58px;
  width: 58px;
  height: 58px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(20, 85, 180, 0.25);
  overflow: hidden;
}

.brand-logo {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
}

.brand-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-subtitle {
  margin-top: 4px;
  color: rgba(255,255,255,0.56);
  font-size: 12px;
}

.aside-menu {
  border-right: none;
  margin-top: 12px;
}

.aside-menu :deep(.el-menu-item) {
  height: 50px;
  border-radius: 16px;
  margin-bottom: 8px;
  font-weight: 600;
}

.aside-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, rgba(91,108,255,0.3), rgba(123,211,255,0.12));
}

.aside-menu :deep(.el-menu-item:hover) {
  background: rgba(255,255,255,0.06);
}

.menu-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.82;
  margin-right: 12px;
}

.aside-foot {
  margin-top: auto;
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.aside-foot-label {
  font-size: 12px;
  color: rgba(255,255,255,0.56);
}

.aside-user {
  margin-top: 10px;
  font-size: 16px;
  font-weight: 700;
}

.aside-role {
  margin-top: 6px;
  color: rgba(255,255,255,0.6);
  font-size: 13px;
  line-height: 1.5;
}

.change-password-btn {
  min-width: 108px;
  color: #4f5cff;
  background: rgba(91, 108, 255, 0.08);
  border: 1px solid rgba(91, 108, 255, 0.16);
}

.change-password-btn:hover {
  color: #4557ff;
  background: rgba(91, 108, 255, 0.14);
  border-color: rgba(91, 108, 255, 0.24);
}

:deep(.password-dialog) {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.76);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
}

:deep(.password-dialog .el-dialog__header) {
  padding: 22px 24px 8px;
}

:deep(.password-dialog .el-dialog__title) {
  color: #111827;
  font-size: 20px;
  font-weight: 700;
}

:deep(.password-dialog .el-dialog__body) {
  padding: 12px 24px 6px;
  color: #111827;
}

:deep(.password-dialog .el-form-item__label) {
  color: #344054;
  font-weight: 600;
}

:deep(.password-dialog .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(15, 23, 42, 0.1);
  box-shadow: none;
}

:deep(.password-dialog .el-input__inner) {
  color: #111827;
}

:deep(.password-dialog .el-dialog__footer) {
  padding: 8px 24px 24px;
}

.layout-main-wrap {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 24px;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 24px;
  border-radius: 28px;
}

.header-label {
  color: #667085;
  font-size: 13px;
  font-weight: 600;
}

.header-title {
  margin: 8px 0 0;
  font-size: 30px;
  letter-spacing: -0.04em;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-user-card {
  padding: 10px 14px;
  border-radius: 18px;
  background: rgba(255,255,255,0.9);
  border: 1px solid rgba(15,23,42,0.06);
}

.header-user-name {
  font-weight: 700;
}

.header-user-meta {
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
}

.logout-btn {
  min-width: 108px;
  background: rgba(17, 24, 39, 0.04);
  border: 1px solid rgba(15,23,42,0.08);
}

.layout-main {
  min-width: 0;
}

@media (max-width: 1100px) {
  .layout-root {
    grid-template-columns: 1fr;
  }

  .layout-aside {
    position: static;
    height: auto;
  }

  .layout-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
