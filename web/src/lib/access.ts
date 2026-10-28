/** Role-aware module access — hide nav without permission (blueprint rule). */

export type AccessUser = {
  permissions?: string[];
  roles?: string[];
} | null;

function perms(user: AccessUser): Set<string> {
  return new Set(user?.permissions || []);
}

export function hasAny(user: AccessUser, ...codes: string[]): boolean {
  const p = perms(user);
  if (p.has("owner.full")) return true;
  return codes.some((c) => p.has(c));
}

export function canHome(user: AccessUser) {
  return hasAny(user, "dashboard.view");
}

export function canGate(user: AccessUser) {
  return hasAny(user, "vehicle.entry", "vehicle.exit", "vehicle.anpr", "gatepass.create", "gatepass.view");
}

export function canWeigh(user: AccessUser) {
  return hasAny(user, "weighment.tare", "weighment.gross");
}

export function canInbox(user: AccessUser) {
  return hasAny(user, "transaction.search", "transaction.view", "approval.act");
}

export function canDocuments(user: AccessUser) {
  return hasAny(user, "document.invoice.capture", "document.eway.capture", "document.confirm");
}

export function canStock(user: AccessUser) {
  return hasAny(user, "stock.view", "storage.select", "stock.adjust");
}

export function canJobWork(user: AccessUser) {
  return hasAny(user, "jobwork.manage", "production.loss.capture", "otp.send", "otp.verify");
}

export function canEquipment(user: AccessUser) {
  return hasAny(user, "equipment.repair", "equipment.return", "equipment.disposal", "equipment.approve");
}

export function canCanteen(user: AccessUser) {
  return hasAny(user, "canteen.purchase", "canteen.stock");
}

export function canReports(user: AccessUser) {
  return hasAny(user, "report.view", "report.export");
}

export function canAlerts(user: AccessUser) {
  return hasAny(user, "notification.view", "notification.send", "whatsapp.view");
}

export function canMasters(user: AccessUser) {
  return hasAny(user, "master.manage", "user.manage");
}

export function canSettings(user: AccessUser) {
  return hasAny(user, "config.geofence");
}

export function canOffline(_user: AccessUser) {
  return true;
}
