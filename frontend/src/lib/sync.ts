export {
  enqueueExpense as addToQueue,
  registerBackgroundSync,
  init as initSync,
  triggerSync as processQueue,
} from "./sync-engine";

import { db, type OfflineVendor } from "./db";

export async function syncVendorCache(token?: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch("/api/v1/vendors", {
      headers,
      credentials: "include",
    });
  } catch {
    return; // Network error — silently skip, will retry on next interval
  }

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

export function startPollingFallback(): void {
  // No-op: polling handled by sync-engine
}
