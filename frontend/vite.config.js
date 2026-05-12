import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/MARVL_rel_db/' : '/',
  plugins: [react(), tailwindcss()],
  server: {
    open: true,
    proxy: {
      '/videos': 'http://localhost:8000',
      '/upload': 'http://localhost:8000',
      '/meta': 'http://localhost:8000',
    },
  },
}))
