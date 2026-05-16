import { db, type SyncQueueItem, type OfflineVendor } from "./db";

function generateId(): string {
  return crypto.randomUUID();
}

export async function addToQueue(
  type: "expense" | "expense_update",
  payload: Record<string, unknown>
): Promise<void> {
  const item: SyncQueueItem = {
    id: generateId(),
    type,
    payload: JSON.stringify(payload),
    retryCount: 0,
    createdAt: new Date(),
  };
  await db.syncQueue.add(item);
}

async function processQueue(): Promise<void> {
  const items = await db.syncQueue.orderBy("createdAt").toArray();

  for (const item of items) {
    try {
      const payload = JSON.parse(item.payload);

      if (item.type === "expense") {
        const res = await fetch("/api/v1/expenses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        });

        if (res.status === 404) continue;
        if (res.status === 409) {
          await db.syncQueue.delete(item.id);
          const expenseId = payload.offline_id || payload.id;
          if (expenseId) {
            await db.expenses.update(expenseId, {
              status: "synced",
              syncedAt: new Date(),
            });
          }
          continue;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        await db.expenses.update(payload.offline_id || payload.id, {
          status: "synced",
          syncedAt: new Date(),
        });
        await db.syncQueue.delete(item.id);
      } else if (item.type === "expense_update") {
        const res = await fetch(`/api/v1/expenses/${payload.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        });

        if (res.status === 404) continue;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        await db.syncQueue.delete(item.id);
      }
    } catch {
      const newRetry = item.retryCount + 1;
      const backoff = Math.min(1000 * Math.pow(2, newRetry - 1), 8000);

      await db.syncQueue.update(item.id, {
        retryCount: newRetry,
        lastAttempt: new Date(),
      });

      if (newRetry > 5) {
        const expenseId = payload_id_from_item(item);
        if (expenseId) {
          await db.expenses.update(expenseId, {
            syncError: "Max retries exceeded",
          });
        }
      } else {
        await new Promise((r) => setTimeout(r, backoff));
      }
    }
  }
}

function payload_id_from_item(item: SyncQueueItem): string {
  try {
    const payload = JSON.parse(item.payload);
    return payload.id || payload.offlineId || payload.offline_id || "";
  } catch {
    return "";
  }
}

export function registerBackgroundSync(): void {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready.then((sw) => {
      if ("sync" in sw) {
        (sw as unknown as { sync: { register: (tag: string) => void } }).sync.register("engez-sync");
      }
    });
  }
}

let pollingInterval: ReturnType<typeof setInterval> | null = null;

export function startPollingFallback(): void {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready.then((sw) => {
      const hasSync = "sync" in sw;
      if (!hasSync && !pollingInterval) {
        pollingInterval = setInterval(processQueue, 30000);
      }
    });
  } else if (!pollingInterval) {
    pollingInterval = setInterval(processQueue, 30000);
  }
}

export function initSync(): void {
  registerBackgroundSync();
  startPollingFallback();

  window.addEventListener("online", () => {
    processQueue();
  });
}

export { processQueue };

// --- Vendor Cache Sync ---

export async function syncVendorCache(token?: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch("/api/v1/vendors", {
    headers,
    credentials: "include",
  });

  if (!res.ok) return;

  const data = await res.json();
  const vendors: OfflineVendor[] = (data.vendors || []).map(
    (v: Record<string, unknown>) => ({
      id: v.id as string,
      companyId: v.company_id as string,
      name: v.name as string,
      nameAr: (v.name_ar as string) || undefined,
      taxRegistration: (v.tax_registration as string) || undefined,
      categoryHint: (v.category_hint as string) || undefined,
    })
  );

  if (vendors.length > 0) {
    await db.vendorCache.bulkPut(vendors);
  }
}

let vendorSyncInterval: ReturnType<typeof setInterval> | null = null;

export function startVendorSync(token?: string): void {
  syncVendorCache(token);
  if (!vendorSyncInterval) {
    vendorSyncInterval = setInterval(() => syncVendorCache(token), 15 * 60 * 1000);
  }
}

export function stopVendorSync(): void {
  if (vendorSyncInterval) {
    clearInterval(vendorSyncInterval);
    vendorSyncInterval = null;
  }
}
