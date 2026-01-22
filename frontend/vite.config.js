import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv, searchForWorkspaceRoot } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { ViteToml } from 'vite-plugin-toml'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [
      vue(),
      vueDevTools(),
      ViteToml(),
    ],
    server: {
      port: parseInt(env.VITE_PORT) || 5173,
      host: env.VITE_HOST || '127.0.0.1',
      fs: {
        allow: [
          searchForWorkspaceRoot(process.cwd()),
          fileURLToPath(new URL('../config', import.meta.url))
        ]
      },
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
      extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json', '.vue', '.toml'],
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@root-config': fileURLToPath(new URL('../config', import.meta.url))
      },
    },
  }
})
