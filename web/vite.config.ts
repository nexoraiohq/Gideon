import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: npm run dev → React dev server on :5173, /api proxied to FastAPI :8420
// Prod: npm run build → web/dist, served by FastAPI at :8420
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8420', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
