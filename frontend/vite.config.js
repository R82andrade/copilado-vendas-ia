import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/clientes': 'http://localhost:8000',
      '/conversas': 'http://localhost:8000',
      '/produtos': 'http://localhost:8000',
      '/pedidos': 'http://localhost:8000',
      '/ia': 'http://localhost:8000',
      '/webhooks': 'http://localhost:8000',
    },
  },
});
