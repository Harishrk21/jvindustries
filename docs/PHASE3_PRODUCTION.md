# Phase 3 — Production capture & weighbridge

## What is real (not mock)

| Capability | Implementation |
|------------|----------------|
| Live camera | Android CameraX — `capture_source=LIVE_CAMERA` only for operators |
| GPS / geofence | Device Fused Location + server haversine + accuracy threshold |
| ANPR / OCR | On-device **ML Kit** text recognition → server parses candidates from OCR text |
| Evidence files | Stored under `evidence_store/` with SHA-256 hash (S3 when credentials provided) |
| Tare / Gross | Live display photo + OCR parse + operator confirm |
| Net kg | **Server only** (`gross - tare`) |
| Density / litres | Hydrometer photo + OCR + server `net / density` labeled **CALCULATED QUANTITY** |
| Hardware | `WeighbridgeHardwareClient` abstraction ready; returns null until wired |

## Explicitly removed

- Invented plate `TN 09 AB 1234` when OCR is empty
- Invented weights without OCR text
- Hard-coded site GPS on the mobile production path

## Operator flow

1. Vehicle Entry → grant camera + location  
2. Live photo → ML Kit OCR → confirm plate (manual + reason if OCR fails)  
3. Driver → Gate pass  
4. Weighment → live TARE → live GROSS → server NET  
5. Density → calculated litres  
6. Exit live photo when ready  

## Credentials still required later

- S3 / object storage  
- WhatsApp Business API  
- Optional cloud AI (if replacing on-device OCR)
