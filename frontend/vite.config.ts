import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: [
        "favicon.svg",
        "pwa-192x192.svg",
      ],
      manifest: {
        name: "إنجز — ENGEZ Field Expense",
        short_name: "إنجز",
        description: "تطبيق إدارة مصروفات الميدان",
        theme_color: "#0D9488",
        background_color: "#0A0A0A",
        display: "standalone",
        orientation: "portrait",
        dir: "rtl",
        lang: "ar",
        start_url: "/",
        scope: "/",
        icons: [
          {
            src: "pwa-192x192.svg",
            sizes: "192x192",
            type: "image/svg+xml",
          },
          {
            src: "pwa-512x512.svg",
            sizes: "512x512",
            type: "image/svg+xml",
          },
          {
            src: "pwa-512x512.svg",
            sizes: "512x512",
            type: "image/svg+xml",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        runtimeCaching: [
          {
            urlPattern: /^\/api\/v1/,
            handler: "NetworkFirst",
            options: {
              networkTimeoutSeconds: 5,
              cacheName: "api-cache",
              expiration: { maxEntries: 100, maxAgeSeconds: 300 },
            },
          },
          {
            urlPattern:
              /^https:\/\/fonts\.gstatic\.com\/.*\.(woff2|ttf|otf)$/,
            handler: "CacheFirst",
            options: {
              cacheName: "font-cache",
              expiration: { maxAgeSeconds: 365 * 24 * 60 * 60 },
            },
          },
        ],
      },
      devOptions: { enabled: true },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
