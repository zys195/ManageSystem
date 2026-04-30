<template>
  <div class="login-page">
    <section class="login-shell glass-card">
      <div class="hero-panel">
        <h1>合同管理系统</h1>
        <p>统一管理合同台账、甲乙方信息、财务状态与归档过程。</p>

        <div class="feature-list">
          <div class="feature-item"><span class="feature-badge"></span> 合同录入与编辑协作</div>
          <div class="feature-item"><span class="feature-badge"></span> 回款、付款与验收记录</div>
          <div class="feature-item"><span class="feature-badge"></span> 权限角色与工作台入口</div>
        </div>
      </div>

      <div class="login-panel">
        <div>
          <div class="panel-label">欢迎回来</div>
          <div class="panel-title">登录合同管理系统</div>
          <div class="panel-subtitle">请输入账号密码进入工作台。</div>
        </div>

        <el-form :model="loginForm" class="login-form" @submit.prevent="onLogin">
          <el-form-item>
            <el-input v-model="loginForm.username" size="large" placeholder="用户名" />
          </el-form-item>

          <el-form-item>
            <el-input
              v-model="loginForm.password"
              size="large"
              type="password"
              placeholder="密码"
              show-password
            />
          </el-form-item>

          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="onLogin">
            进入工作台
          </el-button>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

async function onLogin() {
  loading.value = true
  try {
    await auth.login(loginForm)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background:
    radial-gradient(circle at 20% 20%, rgba(99, 126, 255, 0.14), transparent 32%),
    linear-gradient(135deg, #eef4fb 0%, #f8fafc 100%);
}

.login-shell {
  width: min(1320px, 100%);
  min-height: 680px;
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  overflow: hidden;
  border-radius: 36px;
}

.hero-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 64px;
  color: #fff;
  background:
    linear-gradient(145deg, rgba(15, 23, 42, 0.96), rgba(43, 55, 77, 0.98)),
    radial-gradient(circle at 70% 25%, rgba(95, 116, 255, 0.24), transparent 30%);
}

.hero-panel h1 {
  margin: 0;
  font-size: clamp(42px, 4vw, 64px);
  font-weight: 900;
  letter-spacing: -0.08em;
}

.hero-panel p {
  margin: 28px 0 0;
  max-width: 560px;
  color: rgba(255, 255, 255, 0.68);
  font-size: 20px;
  line-height: 1.7;
}

.feature-list {
  display: grid;
  gap: 18px;
  margin-top: 64px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 18px;
  font-weight: 700;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 14px;
}

.feature-badge {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: radial-gradient(circle, #93c5fd 34%, rgba(96, 165, 250, 0.22) 38%);
}

.login-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 72px 56px;
  background: rgba(255, 255, 255, 0.84);
}

.panel-label {
  color: #64748b;
  font-size: 18px;
  font-weight: 800;
}

.panel-title {
  margin-top: 12px;
  color: #0f172a;
  font-size: 40px;
  font-weight: 900;
  letter-spacing: -0.06em;
}

.panel-subtitle {
  margin-top: 10px;
  color: #64748b;
  font-size: 16px;
}

.login-form {
  display: grid;
  gap: 18px;
  margin-top: 34px;
}

.submit-btn {
  width: 100%;
  height: 56px;
  margin-top: 8px;
  border-radius: 16px;
  font-size: 18px;
  font-weight: 800;
}

@media (max-width: 1100px) {
  .login-page {
    padding: 24px;
  }

  .login-shell {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .hero-panel,
  .login-panel {
    padding: 44px 28px;
  }
}
</style>
