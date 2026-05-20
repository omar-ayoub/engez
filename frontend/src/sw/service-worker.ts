/// <reference lib="webworker" />
declare let self: ServiceWorkerGlobalScope;

import { precacheAndRoute, cleanupOutdatedCaches } from "workbox-precaching";
import { registerRoute } from "workbox-routing";
import { NetworkFirst, CacheFirst } from "workbox-strategies";
import { ExpirationPlugin } from "workbox-expiration";
import { BackgroundSyncPlugin } from "workbox-background-sync";

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

registerRoute(
  ({ url }) => url.pathname.startsWith("/api/v1"),
  new NetworkFirst({
    cacheName: "api-cache",
    networkTimeoutSeconds: 5,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 24 * 60 * 60,
      }),
    ],
  })
);

registerRoute(
  ({ url }) => url.hostname === "fonts.gstatic.com",
  new CacheFirst({
    cacheName: "font-cache",
    plugins: [
      new ExpirationPlugin({
        maxAgeSeconds: 365 * 24 * 60 * 60,
      }),
    ],
  })
);

const expenseSyncPlugin = new BackgroundSyncPlugin("expense-sync-queue", {
  maxRetentionTime: 7 * 24 * 60,
});

registerRoute(
  ({ url, request }) => url.pathname === "/api/v1/expenses" && request.method === "POST",
  new NetworkFirst({
    cacheName: "expense-post-cache",
    plugins: [expenseSyncPlugin],
  })
);

const receiptUploadPlugin = new BackgroundSyncPlugin("receipt-upload-queue", {
  maxRetentionTime: 7 * 24 * 60,
});

registerRoute(
  ({ url, request }) => url.pathname === "/api/v1/receipts/extract" && request.method === "POST",
  new NetworkFirst({
    cacheName: "receipt-upload-cache",
    plugins: [receiptUploadPlugin],
  })
);

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
