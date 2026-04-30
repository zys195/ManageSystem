import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    allowedHosts: ['2085dae3.r32.cpolar.top'],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:7999',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://127.0.0.1:7999',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
