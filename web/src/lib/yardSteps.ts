/** Blueprint-aligned stepwise yard flow (bulk inward / outward). */

export type YardTxnType = "MATERIAL_LOADING_OUTWARD" | "MATERIAL_RECEIVING_INWARD";

export type YardStepId =
  | "location"
  | "type"
  | "lorry"
  | "driver"
  | "docs"
  | "post_docs"
  | "hub"
  | "gate"
  | "gross"
  | "tare"
  | "density"
  | "slip"
  | "exit"
  | "close"
  | "done";

export type YardStepDef = {
  id: YardStepId;
  label: string;
  short: string;
};

/**
 * Full checklist — order matches state machine:
 * outward: empty entry → tare → load → gross → density → docs → OTP → exit
 * inward: entry → gate → gross → unload tare → density → docs → exit
 */
export function checklistForType(type: YardTxnType): { id: YardStepId; label: string }[] {
  if (type === "MATERIAL_RECEIVING_INWARD") {
    return [
      { id: "lorry", label: "Lorry photo + ANPR" },
      { id: "driver", label: "Driver details" },
      { id: "gate", label: "Gate pass + storage" },
      { id: "gross", label: "Gross weighment" },
      { id: "tare", label: "Tare weighment" },
      { id: "density", label: "Density / litres" },
      { id: "post_docs", label: "Invoice + E-Way (after unload)" },
      { id: "slip", label: "Weighment slip" },
      { id: "exit", label: "Exit photo + ANPR" },
      { id: "close", label: "Supplier + complete" },
      { id: "done", label: "Deliverables" },
    ];
  }
  return [
    { id: "lorry", label: "Lorry photo + ANPR" },
    { id: "driver", label: "Driver details" },
    { id: "gate", label: "Gate pass + storage" },
    { id: "tare", label: "Tare weighment" },
    { id: "gross", label: "Gross weighment" },
    { id: "density", label: "Density / litres" },
    { id: "post_docs", label: "Invoice + E-Way (after load)" },
    { id: "slip", label: "Weighment slip" },
    { id: "exit", label: "Exit photo + ANPR" },
    { id: "close", label: "Customer OTP + close" },
    { id: "done", label: "Deliverables" },
  ];
}

export function stepsForType(type: YardTxnType | null): YardStepDef[] {
  if (!type) {
    return [
      { id: "location", label: "Confirm location", short: "Location" },
      { id: "type", label: "Start transaction", short: "Start" },
    ];
  }
  const list = checklistForType(type);
  return [
    { id: "location", label: "Confirm location", short: "Location" },
    { id: "type", label: "Start transaction", short: "Start" },
    ...list.map((x) => ({ id: x.id, label: x.label, short: x.label.split(" ")[0] })),
  ];
}

export function nextStepId(type: YardTxnType | null, current: YardStepId): YardStepId | "done" {
  if (current === "location") return "type";
  if (!type) return "type";
  const order = checklistForType(type).map((x) => x.id);
  if (current === "type") return order[0] || "lorry";
  if (current === "hub") return order[0];
  if (current === "docs") {
    // legacy early-docs → jump to post_docs position's next if mid-flow
    const post = order.indexOf("post_docs");
    return post >= 0 ? order[post] : order[0];
  }
  const idx = order.indexOf(current);
  if (idx < 0) return order[0];
  if (idx >= order.length - 1) return "done";
  return order[idx + 1];
}

export function stepFromStatus(type: YardTxnType, status: string): YardStepId {
  const s = status.toUpperCase();
  const inward = type === "MATERIAL_RECEIVING_INWARD";
  if (s === "COMPLETED") return "done";
  if (s === "EXIT_COMPLETED" || s === "EXIT_PENDING") return "exit";
  if (s === "CUSTOMER_CONFIRMED" || s === "CUSTOMER_CONFIRMATION_PENDING" || s === "APPROVED") {
    return "close";
  }
  if (s === "DOCUMENTS_VERIFIED") return "slip";
  if (s === "DOCUMENTS_PENDING" || s === "APPROVAL_PENDING" || s === "EXCEPTION") return "post_docs";
  if (s === "DENSITY_PENDING" || s === "GROSS_COMPLETED") return "density";
  // Inward: after loaded gross → UNLOADING → capture empty tare
  if (s === "UNLOADING" && inward) return "tare";
  if (s === "LOADING" || s === "TARE_COMPLETED" || s === "UNLOADING") return "gross";
  if (s === "AWAITING_TARE") return "gate";
  if (s === "VEHICLE_VERIFIED") return "driver";
  if (s === "ENTRY_STARTED") return "lorry";
  return "lorry";
}

export function isOutward(type: YardTxnType): boolean {
  return type === "MATERIAL_LOADING_OUTWARD";
}

export function isDocStep(step: YardStepId): boolean {
  return step === "docs" || step === "post_docs";
}
