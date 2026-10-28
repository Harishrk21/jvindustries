import { FormEvent, useEffect, useId, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { BrandLogo } from "../components/BrandLogo";
import { Icon } from "../components/Icon";
import { useAuth } from "../state/auth";
import { useToast } from "../state/toast";

const ROLES: { id: string; label: string; hint: string; password: string }[] = [
  { id: "owner", label: "Owner", hint: "Full plant admin", password: "Owner@123" },
  { id: "supervisor", label: "Supervisor", hint: "Approvals · ops", password: "Super@123" },
  { id: "security", label: "Security", hint: "Gate · entry · exit", password: "Security@123" },
  { id: "weighbridge", label: "Weighbridge", hint: "Tare · gross", password: "Weigh@123" },
  { id: "store", label: "Store", hint: "Docs · stock", password: "Store@123" },
  { id: "production", label: "Production", hint: "Job work · loss", password: "Prod@123" },
  { id: "canteen", label: "Canteen", hint: "Purchase · stock", password: "Canteen@123" },
];

export function LoginPage() {
  const { token, login } = useAuth();
  const toast = useToast();
  const [userId, setUserId] = useState("owner");
  const [password, setPassword] = useState("Owner@123");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [capsOn, setCapsOn] = useState(false);
  const [online, setOnline] = useState(() => (typeof navigator !== "undefined" ? navigator.onLine : true));
  const userRef = useRef<HTMLInputElement>(null);
  const formId = useId();

  useEffect(() => {
    const t = window.setTimeout(() => userRef.current?.focus(), 80);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  if (token) return <Navigate to="/" replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const id = userId.trim();
    if (!id || !password) {
      setError("Enter User ID and password to continue.");
      return;
    }
    if (!online) {
      setError("You appear offline. Reconnect, then sign in.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await login(id, password);
      toast.success("Signed in", `Welcome back, ${id}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Sign-in failed. Check User ID and password.";
      setError(msg);
      toast.error("Sign-in failed", msg);
      setPassword("");
    } finally {
      setLoading(false);
    }
  };

  const pickRole = (id: string) => {
    const role = ROLES.find((r) => r.id === id);
    setUserId(id);
    if (role) setPassword(role.password);
    setError(null);
  };

  return (
    <div className="app-stage">
      <div className="app-phone no-tab">
        <div className="login-shell">
          <div className="login-atmosphere" aria-hidden />
          <div className="login-grid" aria-hidden />
          <div className="login-page">
            <header className="login-brand login-brand-enter">
              <div className="login-logo-frame">
                <BrandLogo variant="header" className="login-logo" />
              </div>
              <div className="login-brand-copy">
                <p className="login-product">JV-OMS</p>
                <h1 className="login-title">Operations Management</h1>
                <p className="login-lede">
                  Gate, weighbridge, stock and audit — one secure workspace for the yard.
                </p>
              </div>
            </header>

            <div className="login-status-row" aria-live="polite">
              <span className={online ? "login-status ok" : "login-status bad"}>
                <Icon name={online ? "online" : "offline"} size={14} weight="bold" />
                {online ? "Online" : "Offline"}
              </span>
              <span className="login-status mute login-status-extra">
                <Icon name="shield" size={14} weight="bold" />
                Role-based access
              </span>
            </div>

            <form
              className="login-card login-card-enter"
              onSubmit={(e) => void onSubmit(e)}
              noValidate
              aria-describedby={error ? `${formId}-error` : undefined}
            >
              <div className="login-card-head">
                <h2 className="login-card-title">Sign in</h2>
                <p className="login-card-sub">Use your plant User ID. Passwords are case-sensitive.</p>
              </div>

              <fieldset className="login-roles" disabled={loading}>
                <legend className="login-roles-legend">Quick User ID</legend>
                <div className="login-role-grid" role="list">
                  {ROLES.map((r) => {
                    const active = userId.trim().toLowerCase() === r.id;
                    return (
                      <button
                        key={r.id}
                        type="button"
                        role="listitem"
                        className={active ? "login-role active" : "login-role"}
                        onClick={() => pickRole(r.id)}
                        aria-pressed={active}
                      >
                        <span className="login-role-name">{r.label}</span>
                        <span className="login-role-hint">{r.hint}</span>
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <div className="field">
                <label htmlFor={`${formId}-user`}>User ID</label>
                <input
                  ref={userRef}
                  id={`${formId}-user`}
                  name="username"
                  value={userId}
                  onChange={(e) => {
                    setUserId(e.target.value);
                    setError(null);
                  }}
                  autoComplete="username"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  inputMode="text"
                  placeholder="e.g. security"
                  required
                  disabled={loading}
                />
              </div>

              <div className="field">
                <label htmlFor={`${formId}-password`}>Password</label>
                <div className="login-pw-wrap">
                  <input
                    id={`${formId}-password`}
                    name="password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      setError(null);
                    }}
                    onKeyUp={(e) => setCapsOn(e.getModifierState?.("CapsLock") ?? false)}
                    onKeyDown={(e) => setCapsOn(e.getModifierState?.("CapsLock") ?? false)}
                    autoComplete="current-password"
                    placeholder="Enter password"
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    className="login-pw-toggle"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    tabIndex={0}
                  >
                    <Icon name={showPassword ? "eyeOff" : "eye"} size={20} weight="bold" />
                  </button>
                </div>
                {capsOn && <p className="login-hint warn">Caps Lock is on</p>}
              </div>

              {error && (
                <div id={`${formId}-error`} className="login-error" role="alert">
                  <Icon name="shield" size={18} weight="fill" />
                  <span>{error}</span>
                </div>
              )}

              <button className="btn btn-primary login-submit" type="submit" disabled={loading || !online}>
                {loading ? "Signing in…" : "Sign in to JV-OMS"}
              </button>

              <p className="login-help">
                First-day accounts must change the seed password after sign-in. Ask the owner if you need access.
              </p>
            </form>

            <footer className="login-footer">
              <span>JV Industries · OMS v0.3.0</span>
              <span>Authorized operators only</span>
            </footer>
          </div>
        </div>
      </div>
    </div>
  );
}
