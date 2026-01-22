import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [
      vue(),
      vueDevTools(),
    ],
    server: {
      port: parseInt(env.VITE_PORT) || 5173,
      host: env.VITE_HOST || '127.0.0.1',
      proxy: {
        // Unified backend at port 8000
        '/api': {
          target: env.VITE_BASE_API_URL || 'http://127.0.0.1:8000',
          changeOrigin: true,
          // No rewrite needed as backend now uses /api prefix
        },
      },
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
  }
})
