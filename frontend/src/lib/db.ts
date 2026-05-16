import Dexie, { type EntityTable } from "dexie";

export interface OfflineExpense {
  id: string;
  userId: string;
  projectId?: string;
  categoryId?: string;
  amount: number;
  currency: string;
  vendor?: string;
  vendorTaxReg?: string;
  items: string;
  notes?: string;
  captureMode: "voice" | "receipt" | "combined" | "manual";
  receiptBlob?: Blob;
  receiptUrl?: string;
  voiceBlob?: Blob;
  voiceUrl?: string;
  voiceTranscript?: string;
  status: "draft" | "pending" | "synced" | "approved" | "rejected";
  etaUuid?: string;
  etaVerified: boolean;
  aiExtraction?: Record<string, unknown>;
  aiConfidence?: Record<string, unknown>;
  draftProcessed: boolean;
  createdAt: Date;
  syncedAt?: Date;
  syncError?: string;
}

export interface OfflineVendor {
  id: string;
  companyId: string;
  name: string;
  nameAr?: string;
  taxRegistration?: string;
  categoryHint?: string;
}

export interface OfflineProject {
  id: string;
  companyId: string;
  name: string;
  nameAr: string;
  code: string;
  budget?: number;
  isActive: boolean;
}

export interface OfflineCategory {
  id: string;
  companyId: string;
  name: string;
  nameAr: string;
  sortOrder: number;
  isActive: boolean;
}

export interface SyncQueueItem {
  id: string;
  type: "expense" | "expense_update";
  payload: string;
  retryCount: number;
  createdAt: Date;
  lastAttempt?: Date;
}

const db = new Dexie("EngezDB") as Dexie & {
  expenses: EntityTable<OfflineExpense, "id">;
  projects: EntityTable<OfflineProject, "id">;
  categories: EntityTable<OfflineCategory, "id">;
  syncQueue: EntityTable<SyncQueueItem, "id">;
  vendorCache: EntityTable<OfflineVendor, "id">;
};

db.version(1).stores({
  expenses: "id, userId, projectId, categoryId, status, createdAt, syncedAt",
  projects: "id, companyId, code, isActive",
  categories: "id, companyId, isActive",
  syncQueue: "id, type, createdAt, retryCount",
});

db.version(2).stores({
  expenses: "id, userId, projectId, categoryId, status, captureMode, createdAt, syncedAt",
  projects: "id, companyId, code, isActive",
  categories: "id, companyId, isActive",
  syncQueue: "id, type, createdAt, retryCount",
  vendorCache: "id, companyId, name, nameAr, taxRegistration",
}).upgrade(tx => {
  return tx.table("expenses").toCollection().modify(expense => {
    expense.captureMode = expense.captureMode || "manual";
    expense.items = expense.items || "";
    expense.draftProcessed = expense.draftProcessed ?? false;
  });
});

export { db };
