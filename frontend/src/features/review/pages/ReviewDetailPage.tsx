import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useReviewDetail } from "../hooks/useReviewDetail";
import { useReviewActions } from "../hooks/useReviewActions";
import ReceiptZoomViewer from "../components/ReceiptZoomViewer";
import ExpenseEvidencePanel from "../components/ExpenseEvidencePanel";
import AuditTimeline from "../components/AuditTimeline";
import RejectReasonDialog from "../components/RejectReasonDialog";
import ConfidenceBadge from "../components/ConfidenceBadge";
import AnomalyBadges from "../components/AnomalyBadges";

export default function ReviewDetailPage() {
  const { expenseId } = useParams<{ expenseId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("review");

  const { data, loading, error, refresh, handleReceiptError, setData } = useReviewDetail(expenseId!);
  const { pendingAction, conflictError, setConflictError, handleApprove, handleReject, handleCorrect } = useReviewActions();

  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [actionResult, setActionResult] = useState<{ status: string; nextId: string | null } | null>(null);

  const onApprove = useCallback(async () => {
    if (!data) return;
    try {
      const result = await handleApprove(data.id, data.review_version);
      setActionResult({ status: "approved", nextId: result.next_pending_id });
    } catch {}
  }, [data, handleApprove]);

  const onReject = useCallback(async (reason: string) => {
    if (!data) return;
    try {
      const result = await handleReject(data.id, data.review_version, reason);
      setActionResult({ status: "rejected", nextId: result.next_pending_id });
      setRejectDialogOpen(false);
    } catch {}
  }, [data, handleReject]);

  const onCorrect = useCallback(async (fieldName: string, correctedValue: string | number) => {
    if (!data) return;
    const result = await handleCorrect(data.id, data.review_version, fieldName, correctedValue);
    if (result) refresh();
  }, [data, handleCorrect, refresh]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-gray-400">{t("detail.loading")}</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center">
        <p className="text-red-400">{error || t("detail.error")}</p>
        <button onClick={() => navigate("/review")} className="mt-4 px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 min-h-[44px]">
          {t("detail.backToQueue")}
        </button>
      </div>
    );
  }

  const navigateNext = () => {
    if (actionResult?.nextId) {
      navigate(`/review/${actionResult.nextId}`);
    } else {
      navigate("/review");
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate("/review")}
            className="text-gray-400 hover:text-white transition-colors min-h-[44px] flex items-center gap-2"
          >
            <span aria-hidden="true" className="rtl:rotate-180 inline-block">→</span>
            {t("detail.backToQueue")}
          </button>
          <ConfidenceBadge
            confidence={data.ai_confidence ? {
              min: Math.min(...Object.values(data.ai_confidence)),
              all_high: Object.values(data.ai_confidence).every((v) => v >= 0.8),
              low_count: Object.values(data.ai_confidence).filter((v) => v < 0.8).length,
            } : null}
          />
        </div>

        {data.anomaly_flags && Object.keys(data.anomaly_flags).length > 0 && (
          <div className="mb-4">
            <AnomalyBadges flags={data.anomaly_flags as Record<string, { severity: string; message: string; message_en: string }> | null} />
          </div>
        )}

        {conflictError && (
          <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-700 rounded text-yellow-400 flex items-center justify-between">
            <span>{t("actions.conflict")}</span>
            <button onClick={() => { setConflictError(null); refresh(); }} className="px-3 py-1 bg-yellow-700/50 rounded text-sm min-h-[44px]">
              {t("actions.conflictRefresh")}
            </button>
          </div>
        )}

        {actionResult && (
          <div className="mb-4 p-3 bg-green-900/20 border border-green-700 rounded text-green-400 flex items-center justify-between">
            <span>
              {actionResult.status === "approved" ? t("actions.approveSuccess") : t("actions.rejectSuccess")}
            </span>
            <button onClick={navigateNext} className="px-3 py-1 bg-green-700/50 rounded text-sm min-h-[44px]">
              {actionResult.nextId ? t("actions.nextPending") : t("actions.backToQueue")}
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            {data.receipt_url ? (
              <ReceiptZoomViewer
                src={data.receipt_url}
                onRefreshed={(newUrl) => {
                  setData((prev) => prev ? { ...prev, receipt_url: newUrl } : prev);
                }}
                onRefreshError={handleReceiptError}
              />
            ) : (
              <div className="flex items-center justify-center p-8 bg-gray-800 rounded-lg text-gray-500">
                {t("detail.noReceipt")}
              </div>
            )}

            <div className="p-4 bg-gray-800/50 rounded-lg">
              <h3 className="text-lg font-semibold mb-3">{t("detail.auditHistory")}</h3>
              <AuditTimeline items={data.audit_history} />
            </div>
          </div>

          <div className="space-y-4">
            <ExpenseEvidencePanel
              detail={data}
              onCorrect={onCorrect}
              correcting={pendingAction === "correct"}
            />

            {data.status === "pending" && !actionResult && (
              <div className="flex gap-3 pt-4">
                <button
                  onClick={onApprove}
                  disabled={pendingAction !== null}
                  className="flex-1 px-4 py-3 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 rounded font-medium transition-colors min-h-[44px]"
                >
                  {pendingAction === "approve" ? t("actions.pendingConfirmation") : t("actions.approve")}
                </button>
                <button
                  onClick={() => setRejectDialogOpen(true)}
                  disabled={pendingAction !== null}
                  className="flex-1 px-4 py-3 bg-red-600 hover:bg-red-500 disabled:bg-gray-600 rounded font-medium transition-colors min-h-[44px]"
                >
                  {t("actions.reject")}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <RejectReasonDialog
        open={rejectDialogOpen}
        onConfirm={onReject}
        onCancel={() => setRejectDialogOpen(false)}
        loading={pendingAction === "reject"}
      />
    </div>
  );
}
