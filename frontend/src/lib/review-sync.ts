export {
  enqueueReviewAction as addReviewAction,
  resolveConflict as markReviewConflictResolved,
  getConflicts as getConflictReviewActions,
  getFailures as getFailedReviewActions,
} from "./sync-engine";

export async function getPendingReviewActions() {
  const { db } = await import("./db");
  return db.reviewActions
    .where("status")
    .anyOf(["pending", "syncing"])
    .toArray();
}

export { triggerSync as drainReviewOutbox } from "./sync-engine";

export async function removeReviewAction(id: string) {
  const { db } = await import("./db");
  await db.reviewActions.delete(id);
}
