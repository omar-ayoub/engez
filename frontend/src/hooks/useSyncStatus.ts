import { useState, useEffect, useCallback } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";

interface UseSyncStatusReturn {
  isOnline: boolean;
  syncStatus: "idle" | "syncing" | "offline" | "error";
  pendingCount: number;
  queueCount: number;
  storageWarning: boolean;
  triggerSync: () => Promise<void>;
}

export function useSyncStatus(): UseSyncStatusReturn {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncStatus, setSyncStatus] = useState<"idle" | "syncing" | "offline" | "error">(
    navigator.onLine ? "idle" : "offline"
  );

  const pendingCount = useLiveQuery(
    () => db.expenses.where("status").equals("pending").count(),
    [],
    0
  );

  const queueCount = useLiveQuery(() => db.syncQueue.count(), [], 0);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setSyncStatus("idle");
    };
    const handleOffline = () => {
      setIsOnline(false);
      setSyncStatus("offline");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const triggerSync = useCallback(async () => {
    if (!isOnline) return;

    setSyncStatus("syncing");
    try {
      if ("serviceWorker" in navigator) {
        const sw = await navigator.serviceWorker.ready;
        if ("sync" in sw) {
          (sw as unknown as { sync: { register: (tag: string) => void } }).sync.register("expense-sync");
        }
      }
      const { processQueue } = await import("@/lib/sync");
      await processQueue();
      setSyncStatus("idle");
    } catch {
      setSyncStatus("error");
    }
  }, [isOnline]);

  const [storageWarning, setStorageWarning] = useState(false);

  useEffect(() => {
    const checkStorage = async () => {
      if ("storage" in navigator && "estimate" in navigator.storage) {
        try {
          const estimate = await navigator.storage.estimate();
          if (estimate.quota && estimate.usage) {
            setStorageWarning(estimate.usage / estimate.quota > 0.8);
          }
        } catch {
          // ignore
        }
      }
    };
    checkStorage();
    const interval = setInterval(checkStorage, 60000);
    return () => clearInterval(interval);
  }, []);

  return { isOnline, syncStatus, pendingCount, queueCount, storageWarning, triggerSync };
}
