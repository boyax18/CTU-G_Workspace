import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: process.env.CTUG_API_TARGET || 'http://127.0.0.1:8000',
        // Preserve Host and Origin for Django's same-origin CSRF checks.
        changeOrigin: false,
      },
    },
  },
});


