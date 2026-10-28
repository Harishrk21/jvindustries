import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { Icon, type IconName } from "../components/Icon";
import * as access from "../lib/access";
import { useAuth } from "../state/auth";

type Mod = {
  to: string;
  title: string;
  blurb: string;
  icon: IconName;
  tone: string;
  allow: (u: access.AccessUser) => boolean;
};

type Group = { id: string; label: string; items: Mod[] };

const GROUPS: Group[] = [
  {
    id: "yard",
    label: "Yard operations",
    items: [
      {
        to: "/documents",
        title: "Documents",
        blurb: "Capture and confirm invoice & E-Way bills; resolve vehicle mismatches.",
        icon: "file",
        tone: "ico-blue",
        allow: access.canDocuments,
      },
      {
        to: "/inbox",
        title: "Search & Inbox",
        blurb: "Find trips, review timelines, act on approvals and exceptions.",
        icon: "search",
        tone: "ico-amber",
        allow: access.canInbox,
      },
      {
        to: "/offline",
        title: "Offline queue",
        blurb: "Drafts saved on device — sync when the network returns.",
        icon: "offline",
        tone: "ico-steel",
        allow: access.canOffline,
      },
    ],
  },
  {
    id: "plant",
    label: "Plant & inventory",
    items: [
      {
        to: "/stock",
        title: "Storage & Stock",
        blurb: "Tanks, barrels and IBC balances with movement history.",
        icon: "package",
        tone: "ico-steel",
        allow: access.canStock,
      },
      {
        to: "/job-work",
        title: "Job Work & OTP",
        blurb: "Batches, production loss limits, and customer confirmation OTP.",
        icon: "flask",
        tone: "ico-blue",
        allow: access.canJobWork,
      },
      {
        to: "/equipment",
        title: "Equipment",
        blurb: "Repair out/return, transfers, and disposal requests.",
        icon: "wrench",
        tone: "ico-steel",
        allow: access.canEquipment,
      },
      {
        to: "/canteen",
        title: "Canteen",
        blurb: "Purchase capture with OCR and canteen stock updates.",
        icon: "utensils",
        tone: "ico-teal",
        allow: access.canCanteen,
      },
    ],
  },
  {
    id: "business",
    label: "Business & reporting",
    items: [
      {
        to: "/reports",
        title: "Reports",
        blurb: "Operational PDF/Excel exports for the period you choose.",
        icon: "chart",
        tone: "ico-blue",
        allow: access.canReports,
      },
      {
        to: "/commercial",
        title: "Commercial",
        blurb: "Supply & expense, distillation, costing sheets, and minutes.",
        icon: "file",
        tone: "ico-teal",
        allow: access.canReports,
      },
      {
        to: "/finance",
        title: "Finance",
        blurb: "Customer advances, period settlements, and GST reconcile.",
        icon: "chart",
        tone: "ico-amber",
        allow: access.canReports,
      },
      {
        to: "/alerts",
        title: "Alerts",
        blurb: "Management alerts and message delivery log.",
        icon: "bell",
        tone: "ico-amber",
        allow: access.canAlerts,
      },
    ],
  },
  {
    id: "system",
    label: "Administration",
    items: [
      {
        to: "/masters",
        title: "Masters",
        blurb: "Products, storage units, parties, calibration, and users.",
        icon: "package",
        tone: "ico-steel",
        allow: access.canMasters,
      },
      {
        to: "/settings",
        title: "Settings",
        blurb: "Yard geofence coordinates and password for this device user.",
        icon: "settings",
        tone: "ico-amber",
        allow: access.canSettings,
      },
    ],
  },
];

export function MorePage() {
  const { user } = useAuth();

  const groups = GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((i) => i.allow(user)),
  })).filter((g) => g.items.length > 0);

  return (
    <AppShell title="Modules" subtitle="Everything available for your role">
      {groups.length === 0 ? (
        <div className="panel" style={{ padding: "1rem" }}>
          <p className="muted" style={{ margin: 0 }}>
            No extra modules for this role. Use the Home, Gate, or Weigh tabs.
          </p>
        </div>
      ) : (
        groups.map((g) => (
          <section key={g.id} className="mod-section">
            <header className="mod-section-head">
              <h2>{g.label}</h2>
              <span>{g.items.length}</span>
            </header>
            <nav className="mod-list" aria-label={g.label}>
              {g.items.map((m) => (
                <Link key={m.to} to={m.to} className="mod-row">
                  <span className={`mod-ico ${m.tone}`}>
                    <Icon name={m.icon} size={22} />
                  </span>
                  <span className="mod-copy">
                    <b>{m.title}</b>
                    <em>{m.blurb}</em>
                  </span>
                  <span className="mod-chev" aria-hidden>
                    ›
                  </span>
                </Link>
              ))}
            </nav>
          </section>
        ))
      )}
    </AppShell>
  );
}
