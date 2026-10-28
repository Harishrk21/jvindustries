# JV-OMS UI theme (mobile-first)

## Brand mark

Official logo: `web/public/brand/jv-logo.png` via `BrandLogo` (login hero, home header, page mark).  
PWA/APK icons generated from the same mark (`icons/icon-192.png`, `icon-512.png`).

## Brand colors

| Token | Hex | Use |
|-------|-----|-----|
| Steel / ink | `#0F2430` → `#061018` | Headers, text, dark surfaces |
| Amber / gold | `#F0B429` / `#D4890A` | Primary CTA (aligned to JV gold logo) |
| Teal | `#1AA6A0` | Weighment / calm ops |
| Blue | `#2F6FED` | Vehicles in / info |
| Green | `#149A62` | Received / success |
| Orange | `#E67E22` | Approvals pending |
| Violet | `#6C5CE7` | OTP |
| Red | `#E03E3E` | Exceptions |
| Mist bg | `#E8EEF2` | App background |

## Typography

- Display: **Barlow Condensed** (brand titles)
- Body: **Manrope** (UI text)

## Icons & chrome (Pass A)

- Icons: **Lucide** via `web/src/components/Icon.tsx` (no emoji in nav/tiles)
- Shell: `AppShell` — sticky header, online pill, logout, bottom tabs (Home · Gate · Weigh · More)
- Home shows role-primary KPIs (toggle “All metrics”); secondary modules live under **More**
- Owner tools under More: **Masters** (products/storage/users), **Settings** (geofence)
- Owner gallery: EvidenceCapture shows gallery button when `photo.gallery` / `owner.full`

## How to preview mobile view

### A) Chrome phone emulator (fastest)
1. Open http://127.0.0.1:5173
2. Press `F12` → click **device toolbar** (phone icon) or `Ctrl+Shift+M`
3. Choose **iPhone / Pixel**

### B) Real phone on same Wi‑Fi
1. Find PC IP (`ipconfig` → IPv4)
2. On phone browser: `http://YOUR_PC_IP:5173`
3. Vite must listen on `0.0.0.0` (not only localhost)

### C) Install as PWA
Chrome → menu → **Install app** / Add to Home screen

### D) Real APK
```powershell
cd web
npm run build
npx cap add android
npx cap sync android
npx cap open android
```
Build APK in Android Studio and install on phone.
