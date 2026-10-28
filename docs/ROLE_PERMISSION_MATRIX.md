# JV-OMS Role / Permission Matrix

## Roles

| Role | Purpose |
|------|---------|
| OWNER_ADMIN | Full access, config, gallery upload, exceptions |
| SUPERVISOR | Review/approve/reject, mismatches, loss, equipment |
| SECURITY | Entry/exit, gate pass, live vehicle photo, ANPR |
| WEIGHBRIDGE_OPERATOR | Tare/gross evidence, density evidence, confirm AI |
| PRODUCTION_OPERATOR | Processing batches, I/O, production loss capture |
| STORE_OPERATOR | Receiving, storage, tank/barrel/IBC, stock moves |
| CANTEEN_OPERATOR | Canteen purchase, invoice, canteen stock |

## Permission codes (granular)

Prefix style: `module.action`

Examples:

- `auth.login`, `device.register`
- `dashboard.view`
- `transaction.create`, `transaction.view`, `transaction.search`
- `vehicle.entry`, `vehicle.exit`, `vehicle.anpr`
- `gatepass.create`, `gatepass.view`
- `weighment.tare`, `weighment.gross`, `density.capture`
- `document.invoice.capture`, `document.eway.capture`, `document.confirm`
- `storage.select`, `stock.view`, `stock.adjust` (adjust needs approval)
- `jobwork.manage`, `production.loss.capture`, `production.loss.approve`
- `otp.request`, `otp.view`
- `equipment.repair`, `equipment.return`, `equipment.disposal`, `equipment.approve`
- `canteen.purchase`, `canteen.stock`
- `report.view`, `report.export`
- `approval.act`, `exception.act`
- `audit.view`
- `master.manage`, `user.manage`, `config.geofence`, `config.rules`
- `photo.live`, `photo.gallery` (**gallery = OWNER_ADMIN only**)

## Matrix (high level)

| Capability | Owner | Supervisor | Security | Weighbridge | Production | Store | Canteen |
|------------|:-----:|:----------:|:--------:|:-----------:|:----------:|:-----:|:-------:|
| All records / export | ✓ | view/approve | limited | limited | limited | limited | limited |
| User/master config | ✓ | — | — | — | — | — | — |
| Gallery upload | ✓ | — | — | — | — | — | — |
| Approve exceptions/disposal/excess loss | ✓ | ✓ | — | — | — | — | — |
| Vehicle entry/exit/ANPR | ✓ | ✓ | ✓ | — | — | — | — |
| Gate pass ops | ✓ | ✓ | ✓ | — | — | view | canteen GP |
| Tare/Gross/Density | ✓ | ✓ | — | ✓ | — | — | — |
| Invoice/EWB capture | ✓ | ✓ | — | — | — | ✓ | canteen inv |
| Storage/stock | ✓ | ✓ | — | — | — | ✓ | canteen |
| Job work / loss capture | ✓ | ✓ | — | — | ✓ | — | — |
| Customer OTP flows | ✓ | ✓ | — | — | — | ✓ | — |
| Equipment workflows | ✓ | approve | entry assist | — | — | — | — |
| Canteen | ✓ | ✓ | — | — | — | — | ✓ |
| Reports | ✓ | ✓ | limited | limited | limited | limited | own |
| Audit view | ✓ | ✓ | — | — | — | — | — |

Navigation in the Android app must hide modules without permissions (not only disable buttons).

## Live camera rule

| Role | Live camera | Gallery |
|------|-------------|---------|
| OWNER_ADMIN | ✓ | ✓ (`OWNER_GALLERY_UPLOAD`) |
| All others | ✓ mandatory for evidence | ✗ blocked |

Never reclassify gallery as `LIVE_CAMERA`.
