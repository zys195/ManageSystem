<template>
  <router-view v-slot="{ Component, route }">
    <transition name="page-fade-slide" mode="out-in">
      <div :key="route.fullPath" class="route-view">
        <component :is="Component" />
      </div>
    </transition>
  </router-view>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCollaborationStore } from './stores/collaboration'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const collab = useCollaborationStore()
const auth = useAuthStore()

// 登录后初始化协作Socket连接
function initCollab() {
  if (auth.isLoggedIn && auth.token && !collab.isConnected) {
    collab.connect(auth.token, auth.user)
  }
}

onMounted(() => {
  initCollab()
})

// 监听登录状态变化
watch(() => auth.isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    initCollab()
  } else {
    collab.disconnectAll()
  }
})
</script>

<style scoped>
.route-view {
  min-height: 100vh;
}
</style>
