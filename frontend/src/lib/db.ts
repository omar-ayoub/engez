import Dexie, { type EntityTable } from "dexie";

export interface OfflineExpense {
  id: string;
  userId: string;
  projectId?: string;
  categoryId: string;
  amount: number;
  currency: string;
  category: string;
  vendor?: string;
  vendorTaxReg?: string;
  notes?: string;
  receiptBlob?: Blob;
  receiptUrl?: string;
  voiceBlob?: Blob;
  voiceTranscript?: string;
  status: "draft" | "pending" | "synced" | "approved" | "rejected";
  etaUuid?: string;
  etaVerified: boolean;
  aiExtraction?: Record<string, unknown>;
  aiConfidence?: Record<string, unknown>;
  createdAt: Date;
  syncedAt?: Date;
  syncError?: string;
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
};

db.version(1).stores({
  expenses: "id, userId, projectId, categoryId, status, createdAt, syncedAt",
  projects: "id, companyId, code, isActive",
  categories: "id, companyId, isActive",
  syncQueue: "id, type, createdAt, retryCount",
});

export { db };
