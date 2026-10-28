import * as api from "./api";
import { Capacitor } from "@capacitor/core";
import { Geolocation } from "@capacitor/geolocation";

const PLANT_FALLBACK: api.Gps = { lat: 13.0827, lon: 80.2707, accuracy_m: 50 };

let cache: api.Gps | null = null;
let cacheAt = 0;

function toGps(coords: { latitude: number; longitude: number; accuracy?: number | null }): api.Gps {
  return {
    lat: coords.latitude,
    lon: coords.longitude,
    accuracy_m: coords.accuracy ?? 99,
  };
}

function remember(gps: api.Gps): api.Gps {
  cache = gps;
  cacheAt = Date.now();
  return gps;
}

/** Recent fix (60s) — keeps steps smooth without re-locking every tap. */
export function peekCachedGps(maxAgeMs = 60_000): api.Gps | null {
  if (!cache) return null;
  if (Date.now() - cacheAt > maxAgeMs) return null;
  return cache;
}

function browserOnce(opts: PositionOptions): Promise<api.Gps> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("GPS unavailable"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve(toGps(pos.coords)),
      (err) => reject(err),
      opts,
    );
  });
}

async function readDeviceGps(): Promise<api.Gps> {
  if (Capacitor.isNativePlatform()) {
    try {
      const pos = await Geolocation.getCurrentPosition({
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 15_000,
      });
      return remember(toGps(pos.coords));
    } catch {
      const pos = await Geolocation.getCurrentPosition({
        enableHighAccuracy: false,
        timeout: 8000,
        maximumAge: 60_000,
      });
      return remember(toGps(pos.coords));
    }
  }

  // Browser: quick network/cache fix first; don't stall the yard UI.
  try {
    return remember(
      await browserOnce({ enableHighAccuracy: false, timeout: 2500, maximumAge: 120_000 }),
    );
  } catch {
    /* continue */
  }
  try {
    return remember(await browserOnce({ enableHighAccuracy: true, timeout: 3500, maximumAge: 0 }));
  } catch {
    /* continue */
  }
  return remember(await browserOnce({ enableHighAccuracy: false, timeout: 3500, maximumAge: 0 }));
}

async function plantFallback(token?: string | null): Promise<api.Gps> {
  if (token) {
    try {
      const cfg = await api.getGeofenceConfig(token);
      return remember({ lat: cfg.lat, lon: cfg.lon, accuracy_m: Math.min(cfg.max_accuracy_m || 50, 80) });
    } catch {
      /* use default */
    }
  }
  return remember({ ...PLANT_FALLBACK });
}

/**
 * Always returns a GPS sample so yard steps never stall.
 * Prefers live fix → cache → plant centre (works with GPS_ENFORCE=false).
 */
export async function resolveGps(token?: string | null): Promise<{ gps: api.Gps; source: "live" | "cache" | "plant" }> {
  const fresh = peekCachedGps(45_000);
  if (fresh) return { gps: fresh, source: "cache" };

  try {
    const gps = await readDeviceGps();
    return { gps, source: "live" };
  } catch {
    const stale = peekCachedGps(10 * 60_000);
    if (stale) return { gps: stale, source: "cache" };
    const gps = await plantFallback(token);
    return { gps, source: "plant" };
  }
}

/** Drop-in replacement for readGps() that does not throw. */
export async function readGpsSafe(token?: string | null): Promise<api.Gps> {
  const { gps } = await resolveGps(token);
  return gps;
}
