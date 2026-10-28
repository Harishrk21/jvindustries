import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import { resolveGps } from "../lib/gps";
import { useAuth } from "../state/auth";
import { Icon } from "./Icon";

type Props = {
  onGps?: (gps: api.Gps | null, ok: boolean) => void;
};

export function GpsBanner({ onGps }: Props) {
  const { token } = useAuth();
  const [state, setState] = useState<"acquiring" | "ok" | "warn" | "fail">("acquiring");
  const [detail, setDetail] = useState("GPS…");

  const refresh = useCallback(async () => {
    if (!token) return;
    setState("acquiring");
    setDetail("Checking location…");
    try {
      const { gps, source } = await resolveGps(token);
      try {
        const chk = await api.checkGeofence(token, gps);
        if (chk.authorized) {
          setState("ok");
          const tag = source === "plant" ? "yard pin" : source === "cache" ? "cached" : "live";
          setDetail(`${tag} · ±${Math.round(chk.accuracy_m || gps.accuracy_m)} m`);
          onGps?.(gps, true);
        } else {
          setState("fail");
          setDetail(chk.message || "Outside yard");
          onGps?.(gps, false);
        }
      } catch {
        // API/DB blip — keep yard moving with resolved GPS (dev soft-enforce)
        setState("warn");
        setDetail(source === "plant" ? "yard pin · offline check" : `live · offline check · ±${Math.round(gps.accuracy_m)} m`);
        onGps?.(gps, true);
      }
    } catch (e) {
      setState("fail");
      setDetail(e instanceof Error ? e.message : "GPS unavailable");
      onGps?.(null, false);
    }
  }, [token, onGps]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className={`ve-gps ve-gps-compact ${state}`} role="status">
      {state === "acquiring" ? <span className="jv-spin" /> : <Icon name="mapPin" size={16} weight="fill" />}
      <span className="ve-gps-line">{detail}</span>
      <button type="button" className="ve-gps-refresh" onClick={() => void refresh()}>
        Retry
      </button>
    </div>
  );
}
