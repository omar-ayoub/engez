import { useCallback, useEffect, useRef } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db, type OfflineExpense } from "@/lib/db";

interface UseDraftProcessorReturn {
  unprocessedCount: number;
  processedDrafts: OfflineExpense[];
}

export function useDraftProcessor(): UseDraftProcessorReturn {
  const isProcessingRef = useRef(false);
  const unprocessedDrafts = useLiveQuery(
    () =>
      db.expenses
        .where("status")
        .equals("draft")
        .filter(
          (e) =>
            !e.draftProcessed &&
            (e.voiceBlob != null || e.receiptBlob != null)
        )
        .reverse()
        .sortBy("createdAt"),
    [],
    []
  );

  const unprocessedCount = unprocessedDrafts.length;

  const readyForReview = useLiveQuery(
    () =>
      db.expenses
        .where("status")
        .equals("draft")
        .filter((e) => e.draftProcessed && e.aiExtraction != null)
        .toArray(),
    [],
    []
  );

  const processDrafts = useCallback(async () => {
    if (!navigator.onLine || unprocessedDrafts.length === 0 || isProcessingRef.current) return;
    isProcessingRef.current = true;

    for (const draft of unprocessedDrafts) {
      try {
        const { useAuthStore } = await import("@/lib/auth");
        const token = useAuthStore.getState().accessToken;

        if (draft.voiceBlob) {
          const formData = new FormData();
          formData.append("audio", draft.voiceBlob, "audio.webm");

          const res = await fetch("/api/v1/voice/extract", {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            credentials: "include",
            body: formData,
          });

          if (res.ok) {
            const result = await res.json();
            await db.expenses.update(draft.id, {
              aiExtraction: result.extraction || result,
              draftProcessed: true,
              voiceTranscript: result.transcript || null,
            });
          } else {
            await db.expenses.update(draft.id, {
              syncError: "AI processing failed",
              draftProcessed: true,
            });
          }
        } else if (draft.receiptBlob) {
          const formData = new FormData();
          formData.append("image", draft.receiptBlob, "receipt.jpg");

          const res = await fetch("/api/v1/receipts/extract", {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            credentials: "include",
            body: formData,
          });

          if (res.ok) {
            const result = await res.json();
            await db.expenses.update(draft.id, {
              aiExtraction: result.extraction || result,
              draftProcessed: true,
            });
          } else {
            await db.expenses.update(draft.id, {
              syncError: "AI processing failed",
              draftProcessed: true,
            });
          }
        }
      } catch {
        await db.expenses.update(draft.id, {
          syncError: "Processing failed",
        });
      }
    }
    isProcessingRef.current = false;
  }, [unprocessedDrafts]);

  useEffect(() => {
    if (unprocessedDrafts.length > 0) {
      processDrafts();
    }
  }, [unprocessedDrafts, processDrafts]);

  const processedDrafts = readyForReview ?? [];

  return { unprocessedCount, processedDrafts };
}
