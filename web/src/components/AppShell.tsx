import { Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import * as access from "../lib/access";
import { BrandLogo } from "./BrandLogo";
import { Icon, type IconName } from "./Icon";
import { useAuth } from "../state/auth";

type Tab = {
  to: string;
  label: string;
  icon: IconName;
  allow: (u: access.AccessUser) => boolean;
  match?: (path: string) => boolean;
};

const TABS: Tab[] = [
  { to: "/", label: "Home", icon: "home", allow: access.canHome, match: (p) => p === "/" },
  {
    to: "/yard",
    label: "Gate",
    icon: "truck",
    allow: access.canGate,
    match: (p) => p.startsWith("/yard") || p.startsWith("/vehicle-entry"),
  },
  {
    to: "/weighment",
    label: "Weigh",
    icon: "scale",
    allow: access.canWeigh,
    match: (p) => p.startsWith("/weighment"),
  },
  {
    to: "/inbox",
    label: "Inbox",
    icon: "search",
    allow: access.canInbox,
    match: (p) => p.startsWith("/inbox"),
  },
];

const DRAWER: {
  to: string;
  title: string;
  hint: string;
  icon: IconName;
  allow: (u: access.AccessUser) => boolean;
}[] = [
  { to: "/more", title: "All modules", hint: "Full menu", icon: "more", allow: () => true },
  { to: "/documents", title: "Documents", hint: "Invoice · E-Way", icon: "file", allow: access.canDocuments },
  { to: "/stock", title: "Storage & stock", hint: "Tanks · barrels", icon: "package", allow: access.canStock },
  { to: "/job-work", title: "Job work", hint: "Loss · OTP", icon: "flask", allow: access.canJobWork },
  { to: "/equipment", title: "Equipment", hint: "Repair · scrap", icon: "wrench", allow: access.canEquipment },
  { to: "/canteen", title: "Canteen", hint: "Purchase · stock", icon: "utensils", allow: access.canCanteen },
  { to: "/reports", title: "Reports", hint: "PDF · Excel", icon: "chart", allow: access.canReports },
  { to: "/commercial", title: "Commercial", hint: "Statements", icon: "file", allow: access.canReports },
  { to: "/finance", title: "Finance", hint: "Advances · GST", icon: "chart", allow: access.canReports },
  { to: "/alerts", title: "Alerts", hint: "WhatsApp · PDF", icon: "bell", allow: access.canAlerts },
  { to: "/offline", title: "Offline queue", hint: "Sync drafts", icon: "offline", allow: access.canOffline },
  { to: "/masters", title: "Masters", hint: "Products · users", icon: "package", allow: access.canMasters },
  { to: "/settings", title: "Settings", hint: "Geofence · GPS", icon: "settings", allow: access.canSettings },
];

type Props = {
  title?: string;
  subtitle?: string;
  backTo?: string;
  showBrand?: boolean;
  children: React.ReactNode;
  wide?: boolean;
  hideNav?: boolean;
};

export function AppShell({ title, subtitle, backTo, showBrand, children, hideNav }: Props) {
  const loc = useLocation();
  const nav = useNavigate();
  const { user, logout } = useAuth();
  const [online, setOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);
  const [drawer, setDrawer] = useState(false);

  const tabs = useMemo(() => TABS.filter((t) => t.allow(user)), [user]);
  const drawerItems = useMemo(() => DRAWER.filter((d) => d.allow(user)), [user]);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  useEffect(() => {
    setDrawer(false);
  }, [loc.pathname]);

  useEffect(() => {
    document.body.classList.toggle("drawer-open", drawer);
    return () => document.body.classList.remove("drawer-open");
  }, [drawer]);

  return (
    <div className="app-stage">
      <div className={`app-phone${hideNav ? " no-tab" : ""}`}>
        <div className="app-shell">
          <header className="shell-header">
            <div className="shell-title-row">
              {backTo ? (
                <button type="button" className="shell-back" onClick={() => nav(backTo)} aria-label="Back">
                  ←
                </button>
              ) : (
                <button
                  type="button"
                  className="shell-menu"
                  aria-label="Open menu"
                  aria-expanded={drawer}
                  onClick={() => setDrawer(true)}
                >
                  <span />
                  <span />
                  <span />
                </button>
              )}

              <div className="shell-titles">
                {showBrand ? (
                  <>
                    <BrandLogo variant="header" />
                    <div className="shell-sub">
                      {user?.full_name}
                      {user?.roles?.[0] ? ` · ${user.roles[0].replace(/_/g, " ")}` : ""}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="brand-mark shell-page-title">{title}</div>
                    {subtitle ? <div className="shell-sub">{subtitle}</div> : null}
                  </>
                )}
              </div>

              <div className="shell-actions">
                <span className={`net-pill ${online ? "on" : "off"}`} title={online ? "Online" : "Offline"}>
                  <i />
                  {online ? "On" : "Off"}
                </span>
                <button
                  type="button"
                  className="icon-btn"
                  aria-label="Log out"
                  onClick={() => {
                    logout();
                    nav("/login");
                  }}
                >
                  <Icon name="logout" size={20} />
                </button>
              </div>
            </div>
          </header>

          <main className="shell-main stack">{children}</main>

          {!hideNav && (
            <nav className="bottom-nav" aria-label="Primary">
              {tabs.map((t) => {
                const active = t.match ? t.match(loc.pathname) : loc.pathname === t.to;
                return (
                  <Link key={t.to} to={t.to} className={active ? "active" : undefined}>
                    <span className="nav-ico">
                      <Icon name={t.icon} size={22} weight={active ? "fill" : "duotone"} />
                    </span>
                    {t.label}
                  </Link>
                );
              })}
              <button type="button" className={drawer ? "active" : undefined} onClick={() => setDrawer(true)}>
                <span className="nav-ico">
                  <Icon name="more" size={22} weight={drawer ? "fill" : "duotone"} />
                </span>
                Menu
              </button>
            </nav>
          )}
        </div>

        <div className={`app-drawer${drawer ? " open" : ""}`} aria-hidden={!drawer}>
          <button type="button" className="app-drawer-scrim" aria-label="Close menu" onClick={() => setDrawer(false)} />
          <aside className="app-drawer-panel" role="dialog" aria-modal="true" aria-label="App menu">
            <div className="app-drawer-head">
              <div>
                <p className="ve-kicker">JV Industries</p>
                <strong>{user?.full_name || "Operator"}</strong>
                <span>{user?.roles?.[0]?.replace(/_/g, " ") || "OPERATOR"}</span>
              </div>
              <button type="button" className="icon-btn" aria-label="Close" onClick={() => setDrawer(false)}>
                ✕
              </button>
            </div>
            <nav className="app-drawer-nav">
              {drawerItems.map((item) => (
                <Link key={item.to} to={item.to} onClick={() => setDrawer(false)}>
                  <span className="app-drawer-ico">
                    <Icon name={item.icon} size={22} />
                  </span>
                  <span>
                    <b>{item.title}</b>
                    <em>{item.hint}</em>
                  </span>
                </Link>
              ))}
            </nav>
            <button
              type="button"
              className="btn btn-ghost app-drawer-logout"
              onClick={() => {
                logout();
                nav("/login");
              }}
            >
              <Icon name="logout" size={18} /> Sign out
            </button>
          </aside>
        </div>
      </div>
    </div>
  );
}
