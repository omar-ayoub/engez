import { useState, useCallback } from "react";
import { approveExpense, rejectExpense, correctExpense, ApiConflictError } from "../review-api";
import { addReviewAction, removeReviewAction } from "@/lib/review-sync";
import { useAuthStore } from "@/lib/auth";

function getCompanyId(): string {
  return useAuthStore.getState().user?.company_id || "unknown";
}

export function useReviewActions() {
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<{ currentVersion: number; currentStatus: string } | null>(null);

  const handleApprove = useCallback(async (expenseId: string, reviewVersion: number) => {
    setPendingAction("approve");
    setConflictError(null);
    const companyId = getCompanyId();
    const outboxItem = await addReviewAction(companyId, "approve", { review_version: reviewVersion }, expenseId, reviewVersion);
    try {
      const result = await approveExpense(expenseId, reviewVersion);
      await removeReviewAction(outboxItem.id);
      return result;
    } catch (err: unknown) {
      if (err instanceof ApiConflictError) {
        setConflictError({
          currentVersion: err.currentVersion,
          currentStatus: err.currentStatus,
        });
        await removeReviewAction(outboxItem.id);
      }
      throw err;
    } finally {
      setPendingAction(null);
    }
  }, []);

  const handleReject = useCallback(async (expenseId: string, reviewVersion: number, reason: string) => {
    setPendingAction("reject");
    setConflictError(null);
    const companyId = getCompanyId();
    const outboxItem = await addReviewAction(companyId, "reject", { reason }, expenseId, reviewVersion);
    try {
      const result = await rejectExpense(expenseId, reviewVersion, reason);
      await removeReviewAction(outboxItem.id);
      return result;
    } catch (err: unknown) {
      if (err instanceof ApiConflictError) {
        setConflictError({
          currentVersion: err.currentVersion,
          currentStatus: err.currentStatus,
        });
        await removeReviewAction(outboxItem.id);
      }
      throw err;
    } finally {
      setPendingAction(null);
    }
  }, []);

  const handleCorrect = useCallback(async (
    expenseId: string,
    reviewVersion: number,
    fieldName: string,
    correctedValue: string | number,
  ) => {
    setPendingAction("correct");
    setConflictError(null);
    const companyId = getCompanyId();
    const outboxItem = await addReviewAction(companyId, "correct", { field_name: fieldName, corrected_value: correctedValue }, expenseId, reviewVersion);
    try {
      const result = await correctExpense(expenseId, reviewVersion, fieldName, correctedValue);
      await removeReviewAction(outboxItem.id);
      return result;
    } catch (err: unknown) {
      if (err instanceof ApiConflictError) {
        setConflictError({
          currentVersion: err.currentVersion,
          currentStatus: err.currentStatus,
        });
        await removeReviewAction(outboxItem.id);
      }
      throw err;
    } finally {
      setPendingAction(null);
    }
  }, []);

  return { pendingAction, conflictError, setConflictError, handleApprove, handleReject, handleCorrect };
}
