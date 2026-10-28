import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { Icon, type IconName } from "../components/Icon";
import * as access from "../lib/access";
import * as api from "../lib/api";
import { useAuth } from "../state/auth";

type Action = { to: string; title: string; icon: IconName; primary?: boolean; allow: (u: access.AccessUser) => boolean };

const ACTIONS: Action[] = [
  { to: "/yard", title: "Vehicle entry", icon: "truck", primary: true, allow: access.canGate },
  { to: "/yard", title: "Continue / gate pass", icon: "gate", allow: access.canGate },
  { to: "/weighment", title: "Weighment", icon: "scale", allow: access.canWeigh },
  { to: "/documents", title: "Documents", icon: "file", allow: access.canDocuments },
  { to: "/stock", title: "Storage & stock", icon: "package", allow: access.canStock },
  { to: "/job-work", title: "Job work & OTP", icon: "flask", allow: access.canJobWork },
  { to: "/canteen", title: "Canteen", icon: "utensils", allow: access.canCanteen },
  { to: "/inbox", title: "Search & inbox", icon: "search", allow: access.canInbox },
  { to: "/reports", title: "Reports", icon: "chart", allow: access.canReports },
  { to: "/masters", title: "Masters", icon: "package", allow: access.canMasters },
  { to: "/settings", title: "Settings", icon: "settings", allow: access.canSettings },
];

export function DashboardPage() {
  const { token, user } = useAuth();
  const [summary, setSummary] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .dashboard(token)
      .then(setSummary)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load dashboard"));
  }, [token]);

  const role = user?.roles?.[0]?.replace(/_/g, " ") || "OPERATOR";
  const pending = (summary?.pending_approvals || 0) + (summary?.customer_otp_pending || 0);
  const actions = useMemo(() => ACTIONS.filter((a) => a.allow(user)), [user]);

  return (
    <AppShell showBrand>
      <section className="dash-hero">
        <div className="dash-hero-top">
          <div>
            <div className="brand-mark dash-hero-title">Operations</div>
            <p className="dash-hero-copy">
              {user?.full_name || user?.user_code} · {role}
            </p>
          </div>
          <span className="live-dot">
            <i /> LIVE
          </span>
        </div>
      </section>

      {error && <div className="err">{error}</div>}

      <section className="jv-summary">
        <h2>Today&apos;s summary</h2>
        <div className="jv-summary-grid">
          <div className="jv-stat">
            <div className="k">Vehicles in</div>
            <div className="v">{summary?.vehicles_in ?? "—"}</div>
          </div>
          <div className="jv-stat">
            <div className="k">Vehicles out</div>
            <div className="v">{summary?.vehicles_out ?? "—"}</div>
          </div>
          <div className="jv-stat pending">
            <div className="k">Pending</div>
            <div className="v">{pending}</div>
          </div>
          <div className="jv-stat exc">
            <div className="k">Exceptions</div>
            <div className="v">{summary?.exceptions ?? 0}</div>
          </div>
        </div>
      </section>

      <div className="section-title">
        <h2>Your actions</h2>
        <Link className="text-link" to="/more">
          More modules
        </Link>
      </div>

      <nav className="jv-menu" aria-label="Role actions">
        {actions.map((a) => (
          <Link key={`${a.to}-${a.title}`} className={a.primary ? "primary" : undefined} to={a.to}>
            <Icon name={a.icon} size={24} />
            {a.title}
            <span className="chev">›</span>
          </Link>
        ))}
        {actions.length === 0 && <p className="muted">No yard actions for this role.</p>}
      </nav>
    </AppShell>
  );
}
