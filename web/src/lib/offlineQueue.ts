/** Local offline draft queue (localStorage) + sync push helper. */

const STORAGE_KEY = "jvoms.offline.drafts.v1";

export type OfflineDraft = {
  client_transaction_id: string;
  type: string;
  notes?: string;
  device_id?: string;
  gps?: { lat: number; lon: number; accuracy_m: number };
  queued_at: string;
  last_error?: string;
  conflict?: boolean;
  server_transaction_id?: string;
};

export type SyncPushResult = {
  accepted: number;
  conflicts: number;
  errors: number;
  results: Array<{
    client_transaction_id: string;
    outcome: string;
    message: string;
    transaction_pk?: string | null;
    transaction_id?: string | null;
    status?: string | null;
    sync_status?: string | null;
  }>;
};

function readAll(): OfflineDraft[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as OfflineDraft[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(items: OfflineDraft[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function listOfflineDrafts(): OfflineDraft[] {
  return readAll();
}

export function enqueueOfflineDraft(
  partial: Omit<OfflineDraft, "queued_at" | "client_transaction_id"> & {
    client_transaction_id?: string;
  },
): OfflineDraft {
  const draft: OfflineDraft = {
    client_transaction_id: partial.client_transaction_id || crypto.randomUUID(),
    type: partial.type,
    notes: partial.notes,
    device_id: partial.device_id,
    gps: partial.gps,
    queued_at: new Date().toISOString(),
  };
  const all = readAll();
  all.unshift(draft);
  writeAll(all);
  return draft;
}

export function removeOfflineDraft(clientTransactionId: string) {
  writeAll(readAll().filter((d) => d.client_transaction_id !== clientTransactionId));
}

export function clearSyncedDrafts(clientIds: string[]) {
  const drop = new Set(clientIds);
  writeAll(readAll().filter((d) => !drop.has(d.client_transaction_id)));
}

export function markDraftConflict(clientTransactionId: string, message: string, serverTxn?: string) {
  writeAll(
    readAll().map((d) =>
      d.client_transaction_id === clientTransactionId
        ? {
            ...d,
            conflict: true,
            last_error: message,
            server_transaction_id: serverTxn || d.server_transaction_id,
          }
        : d,
    ),
  );
}

export function isProbablyOffline(): boolean {
  return typeof navigator !== "undefined" && navigator.onLine === false;
}
