# Stack change: Flutter → Native Android APK

The original JV-OMS prompt specified Flutter/Dart. That has been removed.

| Original | Replacement |
|----------|-------------|
| Flutter mobile application | **Native Android APK** (Kotlin + Jetpack Compose) |
| Dart | Kotlin |
| Riverpod/Bloc | ViewModel + StateFlow |
| Drift/SQLite | Room (Phase 11 offline; Phase 1 foundation ready) |
| `Running Flutter` / Flutter folder structure | Android Gradle project under `/mobile` |
| Flutter build | `assembleDebug` → installable `.apk` |

Backend, PostgreSQL, WhatsApp, AI interfaces, business rules, Transaction ID, camera/GPS rules, and phased delivery are unchanged.
