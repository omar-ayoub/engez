import { db, type SyncQueueItem, type ReviewActionOutboxItem } from "./db";

const SYNC_CONFIG = {
  maxRetries: 5,
  maxBackoffMs: 15_000,
  pollIntervalMs: 30_000,
} as const;

export type SyncActionType = SyncQueueItem["type"] | ReviewActionOutboxItem["type"];

export interface SyncStatus {
  pendingExpenses: number;
  pendingReviewActions: number;
  conflictedActions: number;
  failedActions: number;
  total: number;
  state: "idle" | "syncing" | "offline" | "error";
}

export type SyncEventType = "status-change" | "conflict" | "sync-complete";
type SyncListener = (event: SyncEventType, data?: unknown) => void;

let pollingInterval: ReturnType<typeof setInterval> | null = null;
const listeners: Set<SyncListener> = new Set();

function emit(event: SyncEventType, data?: unknown) {
  for (const fn of listeners) {
    try { fn(event, data); } catch { /* listener error, ignore */ }
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { useAuthStore } = await import("@/lib/auth");
  const token = useAuthStore.getState().accessToken;
  if (token) return { Authorization: `Bearer ${token}` };
  return {};
}

async function authedRequest(url: string, options: RequestInit = {}): Promise<Response> {
  const { request } = await import("@/lib/api");
  return request(url, options);
}

function computeBackoff(retryCount: number): number {
  return Math.min(1000 * Math.pow(2, retryCount), SYNC_CONFIG.maxBackoffMs);
}

async function processExpenseQueue(): Promise<void> {
  const items = await db.syncQueue.orderBy("createdAt").toArray();
  const headers = await getAuthHeaders();

  for (const item of items) {
    try {
      const payload = JSON.parse(item.payload);

      if (item.type === "expense") {
        const res = await fetch("/api/v1/expenses/", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...headers },
          credentials: "include",
          body: JSON.stringify(payload),
        });

        if (res.status === 404) continue;
        if (res.status === 409) {
          await db.syncQueue.delete(item.id);
          const expenseId = payload.offline_id || payload.id;
          if (expenseId) {
            await db.expenses.update(expenseId, { status: "synced", syncedAt: new Date() });
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
          headers: { "Content-Type": "application/json", ...headers },
          credentials: "include",
          body: JSON.stringify(payload),
        });

        if (res.status === 404) continue;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await db.syncQueue.delete(item.id);
      }
    } catch {
      const newRetry = item.retryCount + 1;
      const backoff = computeBackoff(newRetry - 1);

      await db.syncQueue.update(item.id, {
        retryCount: newRetry,
        lastAttempt: new Date(),
      });

      if (newRetry > SYNC_CONFIG.maxRetries) {
        const expenseId = payloadIdFromItem(item);
        if (expenseId) {
          await db.expenses.update(expenseId, { syncError: "Max retries exceeded" });
        }
      } else {
        await new Promise((r) => setTimeout(r, backoff));
      }
    }
  }
}

function payloadIdFromItem(item: SyncQueueItem): string {
  try {
    const payload = JSON.parse(item.payload);
    return payload.id || payload.offlineId || payload.offline_id || "";
  } catch {
    return "";
  }
}

async function processReviewOutbox(): Promise<void> {
  const items = await db.reviewActions
    .where("status")
    .anyOf(["pending", "syncing"])
    .sortBy("createdAt");

  for (const item of items) {
    if (item.status === "conflict" || item.status === "failed") continue;
    await processReviewAction(item);
  }
}

async function processReviewAction(item: ReviewActionOutboxItem): Promise<boolean> {
  const payload = JSON.parse(item.payload);
  let url: string;
  let method: string;
  let body: Record<string, unknown> = payload;

  switch (item.type) {
    case "approve":
      url = `/api/v1/expenses/${item.expenseId}/approve`;
      method = "POST";
      body = { review_version: item.reviewVersion };
      break;
    case "reject":
      url = `/api/v1/expenses/${item.expenseId}/reject`;
      method = "POST";
      body = { review_version: item.reviewVersion, reason: payload.reason };
      break;
    case "correct":
      url = `/api/v1/expenses/${item.expenseId}/correct`;
      method = "POST";
      body = {
        review_version: item.reviewVersion,
        field_name: payload.field_name,
        corrected_value: payload.corrected_value,
      };
      break;
    case "bulk_approve":
      url = "/api/v1/expenses/bulk-approve";
      method = "POST";
      break;
    case "resubmit":
      url = `/api/v1/expenses/${item.expenseId}/resubmit`;
      method = "POST";
      break;
    default:
      await db.reviewActions.delete(item.id);
      return true;
  }

  try {
    await db.reviewActions.update(item.id, { status: "syncing", lastAttempt: new Date() });

    const res = await authedRequest(url, {
      method,
      body: JSON.stringify(body),
    });

    if (res.status === 401 || res.status === 403) {
      await db.reviewActions.delete(item.id);
      return true;
    }
    if (res.status === 409) {
      await db.reviewActions.update(item.id, {
        status: "conflict",
        error: "Conflict: expense was modified",
        lastAttempt: new Date(),
      });
      emit("conflict", { actionId: item.id, expenseId: item.expenseId });
      return false;
    }
    if (res.status === 404 || res.status === 422) {
      await db.reviewActions.delete(item.id);
      return true;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    await db.reviewActions.delete(item.id);
    return true;
  } catch (err) {
    const newRetry = item.retryCount + 1;
    const backoff = computeBackoff(newRetry - 1);

    if (newRetry >= SYNC_CONFIG.maxRetries) {
      await db.reviewActions.update(item.id, {
        status: "failed",
        retryCount: newRetry,
        error: err instanceof Error ? err.message : "Unknown error",
        lastAttempt: new Date(),
      });
      return false;
    }

    await db.reviewActions.update(item.id, {
      retryCount: newRetry,
      status: "pending",
      error: err instanceof Error ? err.message : "Unknown error",
      lastAttempt: new Date(),
    });

    await new Promise((r) => setTimeout(r, backoff));
    return false;
  }
}

async function drainAll(): Promise<void> {
  if (!navigator.onLine) return;
  emit("status-change", "syncing");
  try {
    await processExpenseQueue();
    await processReviewOutbox();
    emit("sync-complete");
  } catch {
    // individual items handle their own errors
  }
  emit("status-change", "idle");
}

export async function enqueueExpense(
  type: "expense" | "expense_update",
  payload: Record<string, unknown>,
): Promise<void> {
  const item: SyncQueueItem = {
    id: crypto.randomUUID(),
    type,
    payload: JSON.stringify(payload),
    retryCount: 0,
    createdAt: new Date(),
  };
  await db.syncQueue.add(item);
}

export async function enqueueReviewAction(
  companyId: string,
  type: ReviewActionOutboxItem["type"],
  payload: Record<string, unknown>,
  expenseId?: string,
  reviewVersion?: number,
): Promise<ReviewActionOutboxItem> {
  const item: ReviewActionOutboxItem = {
    id: crypto.randomUUID(),
    companyId,
    expenseId,
    type,
    payload: JSON.stringify(payload),
    reviewVersion,
    status: "pending",
    retryCount: 0,
    createdAt: new Date(),
  };
  await db.reviewActions.add(item);
  return item;
}

export async function getStatus(): Promise<SyncStatus> {
  const pendingExpenses = await db.syncQueue.count();
  const pendingReviewActions = await db.reviewActions
    .where("status").anyOf(["pending", "syncing"]).count();
  const conflictedActions = await db.reviewActions
    .where("status").equals("conflict").count();
  const failedActions = await db.reviewActions
    .where("status").equals("failed").count();

  const total = pendingExpenses + pendingReviewActions + conflictedActions + failedActions;
  const state: SyncStatus["state"] = !navigator.onLine
    ? "offline"
    : total > 0
      ? "syncing"
      : "idle";

  return { pendingExpenses, pendingReviewActions, conflictedActions, failedActions, total, state };
}

export function subscribe(listener: SyncListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export async function resolveConflict(actionId: string): Promise<void> {
  await db.reviewActions.delete(actionId);
}

export async function getConflicts(): Promise<ReviewActionOutboxItem[]> {
  return db.reviewActions.where("status").equals("conflict").toArray();
}

export async function getFailures(): Promise<ReviewActionOutboxItem[]> {
  return db.reviewActions.where("status").equals("failed").toArray();
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

export async function triggerSync(): Promise<void> {
  registerBackgroundSync();
  await drainAll();
}

let onlineHandler: (() => void) | null = null;

export function init(): void {
  registerBackgroundSync();

  if (!pollingInterval) {
    pollingInterval = setInterval(drainAll, SYNC_CONFIG.pollIntervalMs);
  }

  if (!onlineHandler) {
    onlineHandler = () => { drainAll(); };
    window.addEventListener("online", onlineHandler);
  }
}

export function stop(): void {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
  if (onlineHandler) {
    window.removeEventListener("online", onlineHandler);
    onlineHandler = null;
  }
}
