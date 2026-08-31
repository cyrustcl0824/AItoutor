import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [react(), VitePWA({
    registerType: 'autoUpdate',
    manifest: {
      name: 'Emma 英语家教', short_name: 'Emma Tutor', lang: 'zh-CN',
      display: 'standalone', theme_color: '#6c5ce7', background_color: '#fffaf0',
      icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' }]
    },
    workbox: {
      navigateFallback: '/index.html',
      runtimeCaching: [{
        urlPattern: /\/api\/v1\/textbooks\/pages\/.*\/(image|thumbnail)$/,
        handler: 'CacheFirst',
        options: { cacheName: 'recent-textbook-pages', expiration: { maxEntries: 40, maxAgeSeconds: 7 * 86400 }, cacheableResponse: { statuses: [200] } }
      }]
    }
  })],
  server: { proxy: { '/api': 'http://localhost:8000', '/health': 'http://localhost:8000' } }
})

