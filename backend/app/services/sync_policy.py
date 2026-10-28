"""Offline sync conflict policy.

Policy (server-authoritative):
1. Idempotent create: same client_transaction_id → return existing (CREATED→replayed as OK).
2. Never silently overwrite a server row that has progressed past DRAFT/ENTRY_STARTED
   with a conflicting offline payload → CONFLICT (client must discard or open new id).
3. Fresh client_transaction_id → create DRAFT with sync_status=SYNCED after accept.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import TransactionStatus

# Statuses still safe to treat as "draft-equivalent" for idempotent replay
_SOFT = {
    TransactionStatus.DRAFT.value,
    TransactionStatus.ENTRY_STARTED.value,
}


@dataclass(frozen=True)
class SyncDecision:
    outcome: str  # CREATED | IDEMPOTENT | CONFLICT
    message: str


def decide_on_existing(*, existing_status: str, incoming_type: str, existing_type: str) -> SyncDecision:
    if existing_type != incoming_type:
        return SyncDecision(
            outcome="CONFLICT",
            message=(
                f"client_transaction_id already used for type {existing_type}; "
                f"offline payload type {incoming_type} rejected."
            ),
        )
    if existing_status in _SOFT:
        return SyncDecision(
            outcome="IDEMPOTENT",
            message="Already synced — returning server transaction (no overwrite).",
        )
    return SyncDecision(
        outcome="CONFLICT",
        message=(
            f"Server transaction already at {existing_status}. "
            "Offline draft cannot overwrite progressed work. Create a new client_transaction_id."
        ),
    )
