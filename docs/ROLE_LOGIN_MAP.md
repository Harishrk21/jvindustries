# JV-OMS — Login map vs blueprint

WhatsApp Meta is **not required**. With `WHATSAPP_ALLOW_MOCK=true`, OTP/alerts use mock delivery and return `otp_preview` on screen — that path is the accepted success path until Meta is wired.

## Seeded logins (development)

| User ID | Password | Role | Primary modules |
|---------|----------|------|-----------------|
| owner | Owner@123 | OWNER_ADMIN | Everything |
| supervisor | Super@123 | SUPERVISOR | Gate, weigh, docs, stock, job work, OTP, approvals, reports, equipment, canteen |
| security | Security@123 | SECURITY | Gate / ANPR / gate pass |
| weighbridge | Weigh@123 | WEIGHBRIDGE_OPERATOR | Tare / gross |
| store | Store@123 | STORE_OPERATOR | Docs, stock, OTP, equipment requests |
| production | Prod@123 | PRODUCTION_OPERATOR | Job work, loss, OTP, equipment repair |
| canteen | Canteen@123 | CANTEEN_OPERATOR | Canteen purchase / stock |

Nav and Home actions **hide** modules the role cannot use (blueprint rule).

## Blueprint phases → present?

| Blueprint | Present |
|-----------|---------|
| Auth / roles / JWT / devices | Yes |
| Gate entry/exit / ANPR / gate pass | Yes (security+) |
| Weighment tare/gross/density | Yes (weighbridge+) |
| Invoice / E-Way / mismatch / approvals | Yes (store/supervisor/owner) |
| Storage / stock | Yes (store+) |
| Job work / loss / OTP | Yes (production/store+); OTP via **mock WhatsApp** |
| PDFs / alerts | Yes |
| Equipment | Yes |
| Canteen | Yes |
| Reports / commercial / finance | Yes (owner/supervisor report perms) |
| Offline sync | Yes |
| Live Meta WhatsApp | Deferred — mock OK |
| TRUWEIGH hardware serial | Optional later |

## Site config set for this environment

- Strong `JWT_SECRET` in `.env`
- Geofence: Chittoor approx **13.2172, 79.1004**, radius **500 m** (`GPS_ENFORCE=false` for off-site desktop)
- `WHATSAPP_ALLOW_MOCK=true`
