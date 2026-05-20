import { useState, useEffect, useCallback } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import * as syncEngine from "@/lib/sync-engine";

interface UseSyncStatusReturn {
  isOnline: boolean;
  syncStatus: "idle" | "syncing" | "offline" | "error";
  pendingCount: number;
  queueCount: number;
  conflictCount: number;
  failedCount: number;
  totalPending: number;
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
    0,
  );

  const queueCount = useLiveQuery(() => db.syncQueue.count(), [], 0);

  const conflictCount = useLiveQuery(
    () => db.reviewActions.where("status").equals("conflict").count(),
    [],
    0,
  );
  const failedCount = useLiveQuery(
    () => db.reviewActions.where("status").equals("failed").count(),
    [],
    0,
  );
  const pendingReviewCount = useLiveQuery(
    () => db.reviewActions.where("status").anyOf(["pending", "syncing"]).count(),
    [],
    0,
  );

  const totalPending = queueCount + pendingReviewCount + conflictCount + failedCount;

  useEffect(() => {
    const handleOnline = () => { setIsOnline(true); setSyncStatus("idle"); };
    const handleOffline = () => { setIsOnline(false); setSyncStatus("offline"); };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    const unsub = syncEngine.subscribe((event) => {
      if (event === "status-change") setSyncStatus("idle");
      if (event === "conflict") setSyncStatus("error");
    });

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      unsub();
    };
  }, []);

  const triggerSync = useCallback(async () => {
    if (!isOnline) return;
    setSyncStatus("syncing");
    try {
      await syncEngine.triggerSync();
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
        } catch { /* ignore */ }
      }
    };
    checkStorage();
    const interval = setInterval(checkStorage, 60000);
    return () => clearInterval(interval);
  }, []);

  return {
    isOnline,
    syncStatus,
    pendingCount,
    queueCount,
    conflictCount,
    failedCount,
    totalPending,
    storageWarning,
    triggerSync,
  };
}
