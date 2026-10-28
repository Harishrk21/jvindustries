const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || "";

export type Gps = { lat: number; lon: number; accuracy_m: number };

export type CaptureSource = "LIVE_CAMERA" | "OWNER_GALLERY_UPLOAD";

export type User = {
  id: string;
  user_code: string;
  full_name: string;
  roles: string[];
  permissions: string[];
  must_change_password?: boolean;
};

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (data.message) return data.message;
    return "Request failed.";
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function apiJson<T>(
  path: string,
  options: RequestInit & { token?: string } = {},
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<T>;
}

export async function login(userId: string, password: string) {
  return apiJson<{ access_token: string; user: User }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, password }),
  });
}

export async function fetchMe(token: string) {
  return apiJson<User>("/api/v1/auth/me", { token });
}

export async function changePassword(token: string, currentPassword: string, newPassword: string) {
  return apiJson<User>("/api/v1/auth/change-password", {
    method: "POST",
    token,
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export async function dashboard(token: string) {
  return apiJson<Record<string, number>>("/api/v1/dashboard/summary", { token });
}

export async function startEntry(token: string, gps: Gps, type = "MATERIAL_LOADING_OUTWARD") {
  return apiJson<{
    id: string;
    transaction_id: string;
    status: string;
    vehicle_number?: string;
  }>("/api/v1/vehicles/entry/start", {
    method: "POST",
    token,
    body: JSON.stringify({
      client_transaction_id: crypto.randomUUID(),
      type,
      gps,
    }),
  });
}

export async function runAnpr(
  token: string,
  args: {
    transactionPk: string;
    gps: Gps;
    ocrText: string;
    blob: Blob;
    captureSource?: CaptureSource;
  },
) {
  const fd = new FormData();
  fd.append("transaction_pk", args.transactionPk);
  fd.append("gps_lat", String(args.gps.lat));
  fd.append("gps_lon", String(args.gps.lon));
  fd.append("gps_accuracy_m", String(args.gps.accuracy_m));
  fd.append("capture_source", args.captureSource || "LIVE_CAMERA");
  fd.append("ocr_text", args.ocrText);
  fd.append("image", args.blob, `live-${Date.now()}.jpg`);
  return apiJson<{
    id: string;
    vehicle_number?: string;
    confidence?: number;
    provider: string;
    status: string;
    message?: string;
    candidates?: string[];
    photo_id?: string;
  }>("/api/v1/vehicles/anpr", { method: "POST", token, body: fd });
}

export async function confirmAnpr(
  token: string,
  body: {
    transaction_pk: string;
    anpr_result_id: string;
    vehicle_number?: string;
    manual_reason?: string;
    gps: Gps;
  },
) {
  return apiJson("/api/v1/vehicles/anpr/confirm", {
    method: "POST",
    token,
    body: JSON.stringify({ ...body, confirm: true }),
  });
}

export async function saveDriver(
  token: string,
  body: {
    transaction_pk: string;
    driver_name: string;
    driver_mobile: string;
    transporter_name?: string;
    license_no?: string;
    vehicle_type?: string;
    customer_whatsapp?: string;
  },
) {
  return apiJson("/api/v1/vehicles/driver", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export type GatePassCreateOpts = {
  pass_type?: string;
  direction?: "INWARD" | "OUTWARD";
  purpose?: string;
  material_description?: string;
  quantity_text?: string;
  unit_text?: string;
  invoice_challan_no?: string;
  from_location?: string;
  to_location?: string;
  remarks?: string;
  vehicle_checked?: boolean;
  goods_verified?: boolean;
  documents_verified?: boolean;
};

export async function createGatePass(token: string, transactionPk: string, opts?: GatePassCreateOpts) {
  const outward = opts?.direction === "OUTWARD" || opts?.pass_type === "OUTWARD_LOADING";
  return apiJson<{ gate_pass_number: string; id?: string }>("/api/v1/gate-passes", {
    method: "POST",
    token,
    body: JSON.stringify({
      transaction_pk: transactionPk,
      pass_type: opts?.pass_type || (outward ? "OUTWARD_LOADING" : "INWARD_MATERIAL"),
      direction: opts?.direction || (outward ? "OUTWARD" : "INWARD"),
      purpose: opts?.purpose || (outward ? "OUTWARD" : "INWARD"),
      material_description: opts?.material_description,
      quantity_text: opts?.quantity_text,
      unit_text: opts?.unit_text,
      invoice_challan_no: opts?.invoice_challan_no,
      from_location: opts?.from_location,
      to_location: opts?.to_location,
      remarks: opts?.remarks,
      vehicle_checked: opts?.vehicle_checked ?? false,
      goods_verified: opts?.goods_verified ?? false,
      documents_verified: opts?.documents_verified ?? false,
    }),
  });
}

export async function detectExitAnpr(
  token: string,
  args: {
    transactionPk: string;
    gps: Gps;
    ocrText: string;
    blob: Blob;
    captureSource?: CaptureSource;
  },
) {
  const fd = new FormData();
  fd.append("transaction_pk", args.transactionPk);
  fd.append("gps_lat", String(args.gps.lat));
  fd.append("gps_lon", String(args.gps.lon));
  fd.append("gps_accuracy_m", String(args.gps.accuracy_m));
  fd.append("capture_source", args.captureSource || "LIVE_CAMERA");
  fd.append("ocr_text", args.ocrText);
  fd.append("image", args.blob, `exit-${Date.now()}.jpg`);
  return apiJson<{
    id: string;
    vehicle_number?: string;
    confidence?: number;
    provider: string;
    status: string;
    message?: string;
    photo_id?: string;
  }>("/api/v1/vehicles/exit/detect", { method: "POST", token, body: fd });
}

export async function confirmExit(
  token: string,
  body: {
    transaction_pk: string;
    anpr_result_id: string;
    gps: Gps;
    complete_transaction?: boolean;
  },
) {
  return apiJson<{
    id: string;
    transaction_id: string;
    status: string;
    vehicle_number?: string;
  }>("/api/v1/vehicles/exit/confirm", {
    method: "POST",
    token,
    body: JSON.stringify({
      transaction_pk: body.transaction_pk,
      anpr_result_id: body.anpr_result_id,
      gps: body.gps,
      complete_transaction: body.complete_transaction ?? false,
    }),
  });
}

export async function detectWeighment(
  token: string,
  args: {
    transactionPk: string;
    kind: "TARE" | "GROSS";
    gps: Gps;
    ocrText: string;
    blob: Blob;
    captureSource?: CaptureSource;
  },
) {
  const fd = new FormData();
  fd.append("transaction_pk", args.transactionPk);
  fd.append("kind", args.kind);
  fd.append("gps_lat", String(args.gps.lat));
  fd.append("gps_lon", String(args.gps.lon));
  fd.append("gps_accuracy_m", String(args.gps.accuracy_m));
  fd.append("capture_source", args.captureSource || "LIVE_CAMERA");
  fd.append("ocr_text", args.ocrText);
  fd.append("image", args.blob, `${args.kind.toLowerCase()}-${Date.now()}.jpg`);
  return apiJson<{
    detected_weight_kg?: number;
    confidence: number;
    provider: string;
    failed: boolean;
    message: string;
    photo_id?: string;
  }>("/api/v1/weighments/detect", { method: "POST", token, body: fd });
}

export type WeighmentSummary = {
  transaction_id: string;
  status: string;
  tare_kg?: number | null;
  gross_kg?: number | null;
  net_kg?: number | null;
  density_kg_per_l?: number | null;
  temperature_c?: number | null;
  calculated_litres?: number | null;
  calculated_quantity_label?: string;
};

export async function confirmWeighment(token: string, body: Record<string, unknown>) {
  return apiJson<WeighmentSummary>("/api/v1/weighments/confirm", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function detectDensity(
  token: string,
  args: { transactionPk: string; gps: Gps; ocrText: string; blob: Blob; captureSource?: CaptureSource },
) {
  const fd = new FormData();
  fd.append("transaction_pk", args.transactionPk);
  fd.append("gps_lat", String(args.gps.lat));
  fd.append("gps_lon", String(args.gps.lon));
  fd.append("gps_accuracy_m", String(args.gps.accuracy_m));
  fd.append("capture_source", args.captureSource || "LIVE_CAMERA");
  fd.append("ocr_text", args.ocrText);
  fd.append("image", args.blob, `density-${Date.now()}.jpg`);
  return apiJson<{
    detected_density?: number;
    detected_temperature_c?: number;
    confidence: number;
    failed: boolean;
    message: string;
    photo_id?: string;
  }>("/api/v1/weighments/density/detect", { method: "POST", token, body: fd });
}

export async function confirmDensity(token: string, body: Record<string, unknown>) {
  return apiJson<{
    id: string;
    transaction_id: string;
    density_kg_per_l: number;
    temperature_c?: number | null;
    calculated_litres?: number | null;
    net_kg_snapshot?: number | null;
  }>("/api/v1/weighments/density/confirm", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function weighmentSummary(token: string, transactionPk: string) {
  return apiJson<WeighmentSummary>(`/api/v1/weighments/summary/${transactionPk}`, { token });
}

/** Fetch PDF blob for download or Web Share (mobile APK/PWA). */
export async function fetchPdfBlob(token: string, path: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.blob();
}

export async function shareOrDownloadPdf(token: string, path: string, filename: string) {
  const blob = await fetchPdfBlob(token, path);
  const file = new File([blob], filename, { type: "application/pdf" });
  const navShare = navigator as Navigator & {
    share?: (data: ShareData) => Promise<void>;
    canShare?: (data: ShareData) => boolean;
  };
  if (navShare.share && (!navShare.canShare || navShare.canShare({ files: [file] }))) {
    try {
      await navShare.share({ files: [file], title: filename, text: "JV Industries OMS" });
      return "shared" as const;
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return "cancelled" as const;
    }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  return "downloaded" as const;
}

export type DocumentStatus = {
  transaction_id: string;
  status: string;
  invoice_confirmed: boolean;
  eway_confirmed: boolean;
  anpr_vehicle?: string;
  invoice_vehicle?: string;
  eway_vehicle?: string;
  match_status?: string;
  mismatch_reason?: string;
  verification_id?: string;
};

export type DocDetectOut = {
  id: string;
  transaction_id: string;
  photo_id?: string;
  fields: Record<string, string | null>;
  confidence: number;
  provider: string;
  failed: boolean;
  message: string;
  vehicle_candidates?: string[];
  ocr_raw_preview?: string;
};

export async function documentStatus(token: string, transactionPk: string) {
  return apiJson<DocumentStatus>(`/api/v1/documents/status/${transactionPk}`, { token });
}

export async function detectInvoice(
  token: string,
  args: { transactionPk: string; gps: Gps; ocrText: string; blob: Blob; captureSource?: CaptureSource },
) {
  const fd = new FormData();
  fd.append("transaction_pk", args.transactionPk);
  fd.append("gps_lat", String(args.gps.lat));
  fd.append("gps_lon", String(args.gps.lon));
  fd.append("gps_accuracy_m", String(args.gps.accuracy_m));
  fd.append("capture_source", args.captureSource || "LIVE_CAMERA");
  fd.append("ocr_text", args.ocrText);
  fd.append("image", args.blob, `invoice-${Date.now()}.jpg`);
  return apiJson<DocDetectOut>("/api/v1/documents/invoice/detect", {
    method: "POST",
    token,
    body: fd,
  });
}

export async function confirmInvoice(
  token: string,
  body: {
    transaction_pk: string;
    invoice_id: string;
    gps: Gps;
    invoice_number?: string;
    invoice_date?: string;
    gstin?: string;
    vehicle_number?: string;
    total?: string;
    hsn?: string;
    quantity?: string;
  },
) {
  return apiJson<DocumentStatus>("/api/v1/documents/invoice/confirm", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function detectEway(
  token: string,
  args: { transactionPk: string; gps: Gps; ocrText: string; blob: Blob; captureSource?: CaptureSource },
) {
  const fd = new FormData();
  fd.append("transaction_pk", args.transactionPk);
  fd.append("gps_lat", String(args.gps.lat));
  fd.append("gps_lon", String(args.gps.lon));
  fd.append("gps_accuracy_m", String(args.gps.accuracy_m));
  fd.append("capture_source", args.captureSource || "LIVE_CAMERA");
  fd.append("ocr_text", args.ocrText);
  fd.append("image", args.blob, `eway-${Date.now()}.jpg`);
  return apiJson<DocDetectOut>("/api/v1/documents/eway/detect", {
    method: "POST",
    token,
    body: fd,
  });
}

export async function confirmEway(
  token: string,
  body: {
    transaction_pk: string;
    eway_id: string;
    gps: Gps;
    eway_bill_number?: string;
    vehicle_number?: string;
    from_place?: string;
    to_place?: string;
  },
) {
  return apiJson<DocumentStatus>("/api/v1/documents/eway/confirm", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function approveMismatch(
  token: string,
  body: {
    transaction_pk: string;
    verification_id: string;
    approval_note: string;
    gps: Gps;
  },
) {
  return apiJson<DocumentStatus>("/api/v1/documents/mismatch/approve", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export type Product = {
  id: string;
  code: string;
  name: string;
  hsn?: string;
  unit: string;
  density_default?: number;
  loss_limit_percent: number;
  active: boolean;
};

export type StorageUnit = {
  id: string;
  code: string;
  name: string;
  kind: string;
  capacity?: number;
  capacity_unit: string;
  product_id?: string;
  location_label?: string;
  active: boolean;
};

export type StockBalance = {
  product_id: string;
  product_code: string;
  product_name: string;
  storage_unit_id: string;
  storage_code: string;
  storage_kind: string;
  quantity: number;
  unit: string;
};

export type TxnStock = {
  transaction_id: string;
  status: string;
  product_id?: string;
  product_code?: string;
  storage_unit_id?: string;
  storage_code?: string;
  net_kg?: number;
  calculated_litres?: number;
  stock_posted: boolean;
  movements: Array<{
    id: string;
    direction: string;
    quantity: number;
    unit: string;
  }>;
};

export async function listProducts(token: string) {
  return apiJson<Product[]>("/api/v1/products", { token });
}

export async function listStorageUnits(token: string, kind?: string) {
  const q = kind ? `?kind=${encodeURIComponent(kind)}` : "";
  return apiJson<StorageUnit[]>(`/api/v1/storage/units${q}`, { token });
}

export async function stockBalances(token: string) {
  return apiJson<StockBalance[]>("/api/v1/stock/balances", { token });
}

export async function txnStock(token: string, transactionPk: string) {
  return apiJson<TxnStock>(`/api/v1/stock/txn/${transactionPk}`, { token });
}

export async function assignStorage(
  token: string,
  body: { transaction_pk: string; product_id: string; storage_unit_id: string; gps: Gps },
) {
  return apiJson<TxnStock>("/api/v1/stock/assign", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function postStock(
  token: string,
  body: {
    transaction_pk: string;
    direction: "IN" | "OUT";
    use_transaction_qty?: boolean;
    quantity?: number;
    unit?: string;
    gps: Gps;
    note?: string;
  },
) {
  return apiJson<TxnStock>("/api/v1/stock/post", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export type JobWorkBatch = {
  id: string;
  transaction_id: string;
  transaction_pk: string;
  batch_code: string;
  product_id?: string;
  customer_name?: string;
  customer_mobile?: string;
  qty_in?: number;
  qty_out?: number;
  unit: string;
  status: string;
  loss?: {
    id: string;
    loss_qty: number;
    loss_percent: number;
    loss_limit_percent: number;
    excess_percent: number;
    requires_approval: boolean;
    approved: boolean;
  } | null;
};

export type OtpSend = {
  otp_id: string;
  transaction_id: string;
  status: string;
  channel: string;
  provider: string;
  customer_mobile: string;
  expires_at: string;
  whatsapp_delivery_status: string;
  otp_preview?: string;
  message: string;
};

export async function createJobWorkBatch(
  token: string,
  body: {
    batch_code: string;
    product_id?: string;
    customer_name?: string;
    customer_mobile?: string;
    unit?: string;
    gps: Gps;
  },
) {
  return apiJson<JobWorkBatch>("/api/v1/job-work/batches", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function setJobWorkQty(
  token: string,
  body: { batch_id: string; qty_in: number; qty_out: number; gps: Gps },
) {
  return apiJson<JobWorkBatch>("/api/v1/job-work/batches/quantities", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function approveLoss(
  token: string,
  body: { loss_id: string; approval_note: string; gps: Gps },
) {
  return apiJson<JobWorkBatch>("/api/v1/job-work/loss/approve", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function sendOtp(
  token: string,
  body: { transaction_pk: string; customer_mobile: string; customer_name?: string; gps: Gps },
) {
  return apiJson<OtpSend>("/api/v1/otp/send", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function verifyOtp(
  token: string,
  body: { transaction_pk: string; otp_id: string; otp_code: string; gps: Gps },
) {
  return apiJson<{
    transaction_id: string;
    transaction_status: string;
    verified: boolean;
    otp_status?: string;
  }>("/api/v1/otp/verify", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export type AppNotification = {
  id: string;
  category: string;
  severity: string;
  title: string;
  body: string;
  transaction_id?: string;
  whatsapp_sent: boolean;
  is_read: boolean;
  created_at: string;
};

export type WhatsappMsg = {
  id: string;
  transaction_id?: string;
  to_mobile: string;
  template_name: string;
  body_preview?: string;
  provider: string;
  delivery_status: string;
  created_at: string;
};

export async function listNotifications(token: string, unreadOnly = false) {
  const q = unreadOnly ? "?unread_only=true" : "";
  return apiJson<AppNotification[]>(`/api/v1/notifications${q}`, { token });
}

export async function markNotificationRead(token: string, id: string) {
  return apiJson<AppNotification>(`/api/v1/notifications/${id}/read`, { method: "POST", token });
}

export async function sendManualAlert(
  token: string,
  body: { title: string; body: string; category?: string; severity?: string },
) {
  return apiJson<AppNotification>("/api/v1/notifications/alert", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function listWhatsappMessages(token: string) {
  return apiJson<WhatsappMsg[]>("/api/v1/whatsapp/messages", { token });
}

export async function downloadPdf(token: string, path: string, filename: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await parseError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function postPdfDownload(token: string, path: string, body: unknown, filename: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadSupplyExpensePdf(token: string, body: Record<string, unknown>) {
  await postPdfDownload(token, "/api/v1/commercial/supply-expense.pdf", body, "supply-expense.pdf");
}

export async function downloadDistillationPdf(token: string, body: Record<string, unknown>) {
  await postPdfDownload(token, "/api/v1/commercial/distillation.pdf", body, "distillation.pdf");
}

export async function downloadCostingPdf(token: string, body: Record<string, unknown>) {
  await postPdfDownload(token, "/api/v1/commercial/costing.pdf", body, "costing-sheet.pdf");
}

export async function downloadMinutesPdf(token: string, body: Record<string, unknown>) {
  await postPdfDownload(token, "/api/v1/commercial/minutes.pdf", body, "minutes.pdf");
}

export type AdvanceEntry = {
  id: string;
  customer_id: string;
  entry_date: string;
  direction: string;
  amount: number;
  reference?: string | null;
  notes?: string | null;
  created_at: string;
};

export type AdvanceBalance = {
  customer_id: string;
  customer_code: string;
  customer_name: string;
  paid_total: number;
  received_back_total: number;
  balance: number;
};

export type Settlement = {
  id: string;
  customer_id: string;
  report_no: string;
  period_from: string;
  period_to: string;
  status: string;
  feedstock_kg: number;
  delivery_kg: number;
  feedstock_consignments: number;
  delivery_trips: number;
  bleaching_return_kg: number;
  burner_fuel_kg: number;
  burner_rate: number;
  retail_kg: number;
  retail_rate: number;
  processing_rate_per_kg: number;
  gst_percent: number;
  advance_paid: number;
  advance_received_back: number;
  processing_base: number;
  gst_amount: number;
  deductions_total: number;
  net_processing: number;
  payable: number;
  notes?: string | null;
  finalized: boolean;
  created_at: string;
};

export type GstReconcileRow = {
  invoice_id?: string | null;
  transaction_id?: string | null;
  invoice_number?: string | null;
  invoice_gstin?: string | null;
  party_gstin?: string | null;
  invoice_total?: string | null;
  match_status: string;
  detail?: string | null;
};

export type GstReconcileResult = {
  run_id: string;
  period_from: string;
  period_to: string;
  total: number;
  matched: number;
  mismatches: number;
  rows: GstReconcileRow[];
};

export async function createAdvance(
  token: string,
  body: {
    customer_id: string;
    entry_date: string;
    direction: string;
    amount: number;
    reference?: string;
    notes?: string;
  },
) {
  return apiJson<AdvanceEntry>("/api/v1/finance/advances", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function listAdvances(token: string, customerId?: string) {
  const q = customerId ? `?customer_id=${encodeURIComponent(customerId)}` : "";
  return apiJson<AdvanceEntry[]>(`/api/v1/finance/advances${q}`, { token });
}

export async function getAdvanceBalance(token: string, customerId: string) {
  return apiJson<AdvanceBalance>(
    `/api/v1/finance/advances/balance?customer_id=${encodeURIComponent(customerId)}`,
    { token },
  );
}

export async function listAdvanceBalances(token: string) {
  return apiJson<AdvanceBalance[]>("/api/v1/finance/advances/balances", { token });
}

export async function createSettlement(
  token: string,
  body: {
    customer_id: string;
    period_from: string;
    period_to: string;
    report_no?: string;
    auto_fill_yard?: boolean;
    feedstock_kg?: number;
    delivery_kg?: number;
    feedstock_consignments?: number;
    delivery_trips?: number;
    bleaching_return_kg?: number;
    burner_fuel_kg?: number;
    burner_rate?: number;
    retail_kg?: number;
    retail_rate?: number;
    processing_rate_per_kg?: number;
    gst_percent?: number;
    notes?: string;
  },
) {
  return apiJson<Settlement>("/api/v1/finance/settlements", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function listSettlements(token: string, customerId?: string) {
  const q = customerId ? `?customer_id=${encodeURIComponent(customerId)}` : "";
  return apiJson<Settlement[]>(`/api/v1/finance/settlements${q}`, { token });
}

export async function finalizeSettlement(token: string, settlementId: string) {
  return apiJson<Settlement>(`/api/v1/finance/settlements/${settlementId}/finalize`, {
    method: "POST",
    token,
  });
}

export async function downloadSettlementSupplyPdf(token: string, settlementId: string) {
  await postPdfDownload(
    token,
    `/api/v1/finance/settlements/${settlementId}/supply-expense.pdf`,
    {},
    `supply-expense-${settlementId}.pdf`,
  );
}

export async function reconcileGst(token: string, periodFrom: string, periodTo: string) {
  const q = new URLSearchParams({ period_from: periodFrom, period_to: periodTo });
  return apiJson<GstReconcileResult>(`/api/v1/finance/gst/reconcile?${q}`, {
    method: "POST",
    token,
  });
}

export type Equipment = {
  id: string;
  code: string;
  name: string;
  category: string;
  status: string;
  location_label?: string;
  active: boolean;
};

export type EquipmentAction = {
  equipment: Equipment;
  transaction_id: string;
  transaction_pk: string;
  transaction_status: string;
  repair?: { id: string; status: string; vendor_name: string } | null;
  disposal?: { id: string; status: string; reason: string } | null;
};

export async function listEquipment(token: string, status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiJson<Equipment[]>(`/api/v1/equipment${q}`, { token });
}

export async function repairOut(
  token: string,
  body: { equipment_id: string; vendor_name: string; reason: string; expected_return_date?: string; gps: Gps },
) {
  return apiJson<EquipmentAction>("/api/v1/equipment/repair-out", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function repairReturn(
  token: string,
  body: { equipment_id: string; repair_id?: string; note?: string; gps: Gps },
) {
  return apiJson<EquipmentAction>("/api/v1/equipment/repair-return", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function transferEquipment(
  token: string,
  body: { equipment_id: string; destination: string; reason: string; gps: Gps },
) {
  return apiJson<EquipmentAction>("/api/v1/equipment/transfer", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function requestDisposal(
  token: string,
  body: { equipment_id: string; reason: string; gps: Gps },
) {
  return apiJson<EquipmentAction>("/api/v1/equipment/disposal", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function decideDisposal(
  token: string,
  body: { disposal_id: string; approve: boolean; approval_note: string; gps: Gps },
) {
  return apiJson<EquipmentAction>("/api/v1/equipment/disposal/decide", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export type CanteenItem = { id: string; code: string; name: string; unit: string };
export type CanteenBalance = {
  item_id: string;
  item_code: string;
  item_name: string;
  quantity: number;
  unit: string;
};
export type CanteenLine = {
  item_id?: string;
  item_code?: string;
  item_name: string;
  quantity: number;
  unit: string;
};
export type CanteenDetect = {
  purchase_id: string;
  transaction_id: string;
  transaction_pk: string;
  photo_id?: string;
  invoice_number?: string;
  supplier_name?: string;
  invoice_total?: string;
  lines: CanteenLine[];
  confidence: number;
  failed: boolean;
  message: string;
};
export type CanteenPurchase = {
  id: string;
  transaction_id: string;
  status: string;
  invoice_number?: string;
  lines: CanteenLine[];
  stock_posted: boolean;
  photo_id?: string;
};

export async function listCanteenItems(token: string) {
  return apiJson<CanteenItem[]>("/api/v1/canteen/items", { token });
}

export async function canteenBalances(token: string) {
  return apiJson<CanteenBalance[]>("/api/v1/canteen/balances", { token });
}

export async function startCanteenPurchase(token: string, gps: Gps) {
  const fd = new FormData();
  fd.append("gps_lat", String(gps.lat));
  fd.append("gps_lon", String(gps.lon));
  fd.append("gps_accuracy_m", String(gps.accuracy_m));
  return apiJson<{ id: string; transaction_id: string; status: string }>("/api/v1/canteen/purchase/start", {
    method: "POST",
    token,
    body: fd,
  });
}

export async function detectCanteenPurchase(
  token: string,
  args: { transactionPk: string; gps: Gps; ocrText: string; blob: Blob; captureSource?: CaptureSource },
) {
  const fd = new FormData();
  fd.append("transaction_pk", args.transactionPk);
  fd.append("gps_lat", String(args.gps.lat));
  fd.append("gps_lon", String(args.gps.lon));
  fd.append("gps_accuracy_m", String(args.gps.accuracy_m));
  fd.append("capture_source", args.captureSource || "LIVE_CAMERA");
  fd.append("ocr_text", args.ocrText);
  fd.append("image", args.blob, `canteen-${Date.now()}.jpg`);
  return apiJson<CanteenDetect>("/api/v1/canteen/purchase/detect", { method: "POST", token, body: fd });
}

export async function confirmCanteenPurchase(
  token: string,
  body: {
    purchase_id: string;
    transaction_pk: string;
    gps: Gps;
    invoice_number?: string;
    supplier_name?: string;
    lines: CanteenLine[];
  },
) {
  return apiJson<CanteenPurchase>("/api/v1/canteen/purchase/confirm", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export type ReportSummary = {
  report_type: string;
  date_from: string;
  date_to: string;
  title: string;
  summary: Record<string, number>;
  row_count: number;
  sample_rows: Array<Record<string, string>>;
};

export type ReportExportMeta = {
  id: string;
  report_type: string;
  format: string;
  date_from: string;
  date_to: string;
  row_count: number;
  file_name: string;
  created_at: string;
};

export async function reportSummary(
  token: string,
  params: { period: string; date_from?: string; date_to?: string; on_day?: string },
) {
  const q = new URLSearchParams({ period: params.period });
  if (params.date_from) q.set("date_from", params.date_from);
  if (params.date_to) q.set("date_to", params.date_to);
  if (params.on_day) q.set("on_day", params.on_day);
  return apiJson<ReportSummary>(`/api/v1/reports/summary?${q}`, { token });
}

export async function listReportExports(token: string) {
  return apiJson<ReportExportMeta[]>("/api/v1/reports/exports", { token });
}

export async function exportReport(
  token: string,
  params: { period: string; format: string; date_from?: string; date_to?: string; on_day?: string },
) {
  const q = new URLSearchParams({ period: params.period, format: params.format });
  if (params.date_from) q.set("date_from", params.date_from);
  if (params.date_to) q.set("date_to", params.date_to);
  if (params.on_day) q.set("on_day", params.on_day);
  const path = `/api/v1/reports/export?${q}`;
  const ext = params.format.toLowerCase();
  await downloadPdf(token, path, `jv-report.${ext === "xlsx" ? "xlsx" : ext}`);
}

export type OpsReportKind = "stock" | "tank" | "customer" | "jobwork" | "audit";

export type OpsReport = {
  kind: string;
  title: string;
  date_from: string;
  date_to: string;
  columns: string[];
  rows: string[][];
  summary: Record<string, string | number>;
  row_count: number;
};

export async function opsReport(
  token: string,
  kind: OpsReportKind,
  params: { period: string; date_from?: string; date_to?: string; on_day?: string },
) {
  const q = new URLSearchParams({ period: params.period });
  if (params.date_from) q.set("date_from", params.date_from);
  if (params.date_to) q.set("date_to", params.date_to);
  if (params.on_day) q.set("on_day", params.on_day);
  return apiJson<OpsReport>(`/api/v1/reports/ops/${kind}?${q}`, { token });
}

export async function exportOpsReport(
  token: string,
  kind: OpsReportKind,
  params: { period: string; format: string; date_from?: string; date_to?: string; on_day?: string },
) {
  const q = new URLSearchParams({ period: params.period, format: params.format });
  if (params.date_from) q.set("date_from", params.date_from);
  if (params.date_to) q.set("date_to", params.date_to);
  if (params.on_day) q.set("on_day", params.on_day);
  const ext = params.format.toLowerCase();
  await downloadPdf(token, `/api/v1/reports/ops/${kind}/export?${q}`, `jv-${kind}.${ext === "xlsx" ? "xlsx" : ext}`);
}

export type SyncPushResponse = {
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

export async function syncPolicy(token: string) {
  return apiJson<{ policy: string; rules: string[] }>("/api/v1/sync/policy", { token });
}

export async function syncPush(
  token: string,
  drafts: Array<{
    client_transaction_id: string;
    type: string;
    notes?: string;
    device_id?: string;
    gps?: Gps;
    queued_at?: string;
  }>,
) {
  return apiJson<SyncPushResponse>("/api/v1/sync/push", {
    method: "POST",
    token,
    body: JSON.stringify({ drafts }),
  });
}

export type GeofenceConfig = {
  lat: number;
  lon: number;
  radius_m: number;
  max_accuracy_m: number;
  source: string;
};

export async function getGeofenceConfig(token: string) {
  return apiJson<GeofenceConfig>("/api/v1/geofence/config", { token });
}

export async function checkGeofence(token: string, gps: Gps) {
  return apiJson<{ authorized: boolean; message: string; distance_m: number; accuracy_m: number }>(
    "/api/v1/geofence/check",
    { method: "POST", token, body: JSON.stringify(gps) },
  );
}

export async function putGeofenceConfig(
  token: string,
  body: { lat: number; lon: number; radius_m: number; max_accuracy_m: number },
) {
  return apiJson<GeofenceConfig>("/api/v1/geofence/config", {
    method: "PUT",
    token,
    body: JSON.stringify(body),
  });
}

export type AdminUser = {
  id: string;
  user_code: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
};

export async function listUsers(token: string) {
  return apiJson<AdminUser[]>("/api/v1/users", { token });
}

export async function listRoleCodes(token: string) {
  return apiJson<string[]>("/api/v1/users/roles", { token });
}

export async function createUser(
  token: string,
  body: {
    user_code: string;
    full_name: string;
    password: string;
    role_codes: string[];
    is_active?: boolean;
  },
) {
  return apiJson<AdminUser>("/api/v1/users", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function updateUser(
  token: string,
  userId: string,
  body: {
    full_name?: string;
    password?: string;
    role_codes?: string[];
    is_active?: boolean;
  },
) {
  return apiJson<AdminUser>(`/api/v1/users/${userId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(body),
  });
}

export async function createProduct(
  token: string,
  body: {
    code: string;
    name: string;
    hsn?: string;
    unit?: string;
    density_default?: number;
    loss_limit_percent?: number;
  },
) {
  return apiJson("/api/v1/products", { method: "POST", token, body: JSON.stringify(body) });
}

export async function updateProduct(
  token: string,
  productId: string,
  body: Record<string, unknown>,
) {
  return apiJson(`/api/v1/products/${productId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(body),
  });
}

export async function createStorageUnit(
  token: string,
  body: {
    code: string;
    name: string;
    kind: string;
    capacity?: number;
    capacity_unit?: string;
    product_id?: string;
    location_label?: string;
  },
) {
  return apiJson("/api/v1/storage/units", { method: "POST", token, body: JSON.stringify(body) });
}

export async function updateStorageUnit(
  token: string,
  unitId: string,
  body: Record<string, unknown>,
) {
  return apiJson(`/api/v1/storage/units/${unitId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(body),
  });
}

export type TransactionListItem = {
  id: string;
  transaction_id: string;
  type: string;
  status: string;
  vehicle_number?: string | null;
  driver_name?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type TimelineEvent = {
  id: string;
  from_status: string | null;
  to_status: string;
  actor_user_id: string;
  reason: string | null;
  created_at: string;
};

export type InboxItem = {
  kind: string;
  id: string;
  transaction_pk?: string | null;
  transaction_id?: string | null;
  title: string;
  detail?: string | null;
  status: string;
  created_at?: string | null;
  action_hint?: string | null;
};

export async function searchTransactions(
  token: string,
  params: { q?: string; status?: string; type?: string; page?: number; page_size?: number } = {},
) {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.status) sp.set("status", params.status);
  if (params.type) sp.set("type", params.type);
  if (params.page) sp.set("page", String(params.page));
  if (params.page_size) sp.set("page_size", String(params.page_size));
  const qs = sp.toString();
  return apiJson<{
    items: TransactionListItem[];
    total: number;
    page: number;
    page_size: number;
  }>(`/api/v1/transactions${qs ? `?${qs}` : ""}`, { token });
}

export async function getTimeline(token: string, transactionPk: string) {
  return apiJson<{
    transaction_pk: string;
    transaction_id: string;
    type: string;
    status: string;
    vehicle_number?: string | null;
    events: TimelineEvent[];
  }>(`/api/v1/transactions/${transactionPk}/timeline`, { token });
}

export type Party = {
  id: string;
  code: string;
  name: string;
  mobile?: string | null;
  whatsapp?: string | null;
  gstin?: string | null;
  address?: string | null;
  active: boolean;
  created_at: string;
};

export type PartyWrite = {
  code: string;
  name: string;
  mobile?: string;
  whatsapp?: string;
  gstin?: string;
  address?: string;
};

export async function listCustomers(token: string) {
  return apiJson<Party[]>("/api/v1/customers", { token });
}

export async function createCustomer(token: string, body: PartyWrite) {
  return apiJson<Party>("/api/v1/customers", { method: "POST", token, body: JSON.stringify(body) });
}

export async function listSuppliers(token: string) {
  return apiJson<Party[]>("/api/v1/suppliers", { token });
}

export async function createSupplier(token: string, body: PartyWrite) {
  return apiJson<Party>("/api/v1/suppliers", { method: "POST", token, body: JSON.stringify(body) });
}

export type Calibration = {
  id: string;
  certificate_no: string;
  verification_date?: string | null;
  next_due_date?: string | null;
  officer_name?: string | null;
  officer_title?: string | null;
  make_model?: string | null;
  max_capacity_kg?: number | null;
  min_capacity_kg?: number | null;
  accuracy_class?: string | null;
  e_value_kg?: number | null;
  d_value_kg?: number | null;
  seals_count?: number | null;
  seals_note?: string | null;
  location_label?: string | null;
  notes?: string | null;
  is_active: boolean;
  created_at: string;
};

export async function listCalibrations(token: string) {
  return apiJson<Calibration[]>("/api/v1/calibration", { token });
}

export async function getActiveCalibration(token: string) {
  return apiJson<Calibration>("/api/v1/calibration/active", { token });
}

export async function createCalibration(
  token: string,
  body: {
    certificate_no: string;
    verification_date?: string;
    next_due_date?: string;
    officer_name?: string;
    officer_title?: string;
    make_model?: string;
    max_capacity_kg?: number;
    min_capacity_kg?: number;
    accuracy_class?: string;
    e_value_kg?: number;
    d_value_kg?: number;
    seals_count?: number;
    seals_note?: string;
    location_label?: string;
    is_active?: boolean;
  },
) {
  return apiJson<Calibration>("/api/v1/calibration", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function attachParties(
  token: string,
  transactionPk: string,
  body: { customer_id?: string; supplier_id?: string },
) {
  return apiJson<{ id: string; customer_id?: string; supplier_id?: string }>(
    `/api/v1/transactions/${transactionPk}/parties`,
    { method: "POST", token, body: JSON.stringify(body) },
  );
}

export async function closureCheck(token: string, transactionPk: string) {
  return apiJson<{
    transaction_pk: string;
    transaction_id: string;
    type: string;
    status: string;
    can_complete: boolean;
    blockers: string[];
  }>(`/api/v1/transactions/${transactionPk}/closure-check`, { token });
}

export async function listApprovals(token: string, limit = 50) {
  return apiJson<{ items: InboxItem[]; total: number }>(
    `/api/v1/approvals?limit=${limit}`,
    { token },
  );
}

export async function listExceptions(token: string, limit = 50) {
  return apiJson<{ items: InboxItem[]; total: number }>(
    `/api/v1/exceptions?limit=${limit}`,
    { token },
  );
}

export async function approveDocumentMismatch(
  token: string,
  body: {
    transaction_pk: string;
    verification_id: string;
    approval_note: string;
    gps: Gps;
  },
) {
  return apiJson<{ status: string; match_status?: string }>(
    "/api/v1/documents/mismatch/approve",
    { method: "POST", token, body: JSON.stringify(body) },
  );
}
