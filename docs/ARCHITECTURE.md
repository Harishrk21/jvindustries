# JV-OMS Architecture

## System context

```
┌─────────────────────┐     HTTPS/JWT      ┌──────────────────────┐
│  Android APK        │◄──────────────────►│  FastAPI (Python)    │
│  Kotlin + Compose   │                    │  /api/v1/*           │
│  Room offline queue │                    │  SQLAlchemy/Alembic  │
└─────────┬───────────┘                    └──────────┬───────────┘
          │ live camera / GPS                         │
          ▼                                           ▼
┌─────────────────────┐                    ┌──────────────────────┐
│  Device sensors     │                    │  PostgreSQL          │
│  CameraX, Location  │                    │  transactional core  │
└─────────────────────┘                    └──────────┬───────────┘
                                                      │
               ┌──────────────────────────────────────┼────────────────┐
               ▼                      ▼               ▼                ▼
        S3-compatible          AI service        WhatsApp         PDF/Excel
        object storage         interfaces        Business API     workers
```

## Mobile (Android APK)

### Layers

| Layer | Responsibility |
|-------|----------------|
| **Presentation** | Compose UI, ViewModels, navigation (role-based) |
| **Domain** | Use cases, entities, repository interfaces, state machine guards |
| **Data** | Retrofit APIs, Room DAOs, mappers, sync, secure prefs |

### Modules (package layout)

```
mobile/app/src/main/java/com/jvindustries/oms/
  core/          # network, di, security, result types
  config/        # remote/local config, geofence
  auth/
  dashboard/
  vehicle/
  documents/
  weighbridge/
  density/
  storage/
  jobwork/
  equipment/
  canteen/
  gatepass/
  reports/
  audit/
  settings/
  offline/       # queue, sync workers
```

### Key mobile libraries

- Jetpack Compose + Navigation
- Hilt
- Room + WorkManager (offline sync)
- Retrofit / OkHttp / Moshi or Kotlinx Serialization
- CameraX
- Play Services Location (or Android LocationManager) for GPS
- EncryptedSharedPreferences
- Coil (images)
- PDF viewer library for slips

### Camera security

- Operators: CameraX capture only → `capture_source = LIVE_CAMERA`
- Owner (permissioned): gallery picker → `capture_source = OWNER_GALLERY_UPLOAD`
- Every photo metadata: user_id, device_id, timestamp, GPS, accuracy, transaction_id, content hash

### Offline

- Local Room tables mirror critical transaction drafts + evidence blobs (staged files)
- Sync statuses: `PENDING | UPLOADING | SYNCED | FAILED | CONFLICT`
- Idempotency via `client_transaction_id` ↔ `server_transaction_id`

## Backend

```
backend/app/
  api/           # versioned routers
  core/          # config, security, logging, deps
  models/        # SQLAlchemy
  schemas/       # Pydantic
  services/      # business logic (authoritative calculations)
  repositories/
  workers/       # background jobs
  ai/            # OCR/ANPR interfaces + providers/mocks
  storage/       # S3 client, signed URLs
  whatsapp/
  reports/
  audit/
```

### Authority boundaries

| Concern | Authority |
|---------|-----------|
| Net weight, litres, loss %, stock | **Server only** |
| State transitions | Server state machine |
| Photo integrity hash | Server verifies on upload |
| Geofence pass/fail | Server re-validates submitted GPS + accuracy |
| Client display math | UX only; never trusted on commit |

## Integrations (pluggable)

```
VehicleRecognitionService
InvoiceOCRService
EWayBillOCRService
WeighbridgeOCRService
DensityRecognitionService
WeighbridgeHardwareClient   # future RS-232/USB/Ethernet/BT/API
WhatsAppClient
ObjectStorageClient
```

MOCK implementations are explicit and never marketed as production AI.

## Security architecture (summary)

- HTTPS only
- JWT access (+ refresh policy TBD in Phase 1 config)
- RBAC on every API
- Device registration binding
- Rate limiting + input validation
- Secrets via environment (`.env.example` only in repo)
- Append-only audit_logs
- Signed URLs for evidence download

## Reporting

- Server-side PDF/Excel generation (deterministic templates + JV branding)
- Mobile shares via Android share sheet / WhatsApp / email intents after download

## Scalability notes

- Modular services and routers so new integrations do not rewrite core transaction engine
- Indexes on transaction_id, vehicle, documents, dates
- Background workers for OCR, WhatsApp delivery, report exports
