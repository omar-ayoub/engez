import { db, type SyncQueueItem } from "./db";

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

        if (res.status === 404) {
          continue;
        }

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        await db.syncQueue.delete(item.id);
      } else if (item.type === "expense_update") {
        const res = await fetch(`/api/v1/expenses/${payload.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        });

        if (res.status === 404) {
          continue;
        }

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        await db.syncQueue.delete(item.id);
      }
    } catch {
      await db.syncQueue.update(item.id, {
        retryCount: item.retryCount + 1,
        lastAttempt: new Date(),
      });

      if (item.retryCount + 1 > 10) {
        await db.expenses.update(payload_id_from_item(item), {
          syncError: "Max retries exceeded",
        });
      }
    }
  }
}

function payload_id_from_item(item: SyncQueueItem): string {
  try {
    const payload = JSON.parse(item.payload);
    return payload.id || payload.offlineId || "";
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

export async function startPollingFallback(): Promise<void> {
  let hasSync = false;
  if ("serviceWorker" in navigator) {
    const sw = await navigator.serviceWorker.ready;
    hasSync = "sync" in sw;
  }

  if (!hasSync && !pollingInterval) {
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
