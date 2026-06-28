import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Em desenvolvimento, o proxy encaminha /api para a API FastAPI (porta 8000),
// evitando CORS e mantendo o mesmo origin no navegador.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
