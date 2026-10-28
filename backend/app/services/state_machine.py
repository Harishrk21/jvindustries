"""Explicit transaction state transitions for Phase 2 entry/exit."""

from app.models.enums import TransactionStatus

# Allowed transitions (from -> set of to)
ALLOWED: dict[str, set[str]] = {
    TransactionStatus.DRAFT.value: {
        TransactionStatus.ENTRY_STARTED.value,
        TransactionStatus.CANCELLED.value,
    },
    TransactionStatus.ENTRY_STARTED.value: {
        TransactionStatus.VEHICLE_VERIFIED.value,
        TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value,  # job-work OTP path
        TransactionStatus.EXIT_PENDING.value,  # equipment repair-out / transfer
        TransactionStatus.COMPLETED.value,  # equipment return (no yard exit)
        TransactionStatus.EXCEPTION.value,
        TransactionStatus.CANCELLED.value,
    },
    TransactionStatus.VEHICLE_VERIFIED.value: {
        TransactionStatus.AWAITING_TARE.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.EXIT_PENDING.value,  # canteen/simple flows later
        TransactionStatus.APPROVAL_PENDING.value,
        TransactionStatus.CANCELLED.value,
    },
    TransactionStatus.AWAITING_TARE.value: {
        TransactionStatus.TARE_COMPLETED.value,
        TransactionStatus.UNLOADING.value,  # inward: loaded gross first, then unload → tare
        TransactionStatus.DOCUMENTS_PENDING.value,  # docs can precede weighment
        TransactionStatus.EXIT_PENDING.value,  # Phase 2 gate-only path; full weighment in Phase 3
        TransactionStatus.CANCELLED.value,
    },
    TransactionStatus.TARE_COMPLETED.value: {
        TransactionStatus.LOADING.value,
        TransactionStatus.UNLOADING.value,
        TransactionStatus.GROSS_COMPLETED.value,  # inward: tare after loaded gross → net ready
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.CANCELLED.value,
    },
    TransactionStatus.LOADING.value: {
        TransactionStatus.GROSS_COMPLETED.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.CANCELLED.value,
    },
    TransactionStatus.UNLOADING.value: {
        TransactionStatus.TARE_COMPLETED.value,  # inward empty weigh after unload
        TransactionStatus.GROSS_COMPLETED.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.CANCELLED.value,
    },
    TransactionStatus.GROSS_COMPLETED.value: {
        TransactionStatus.DENSITY_PENDING.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.EXIT_PENDING.value,
        TransactionStatus.APPROVAL_PENDING.value,
    },
    TransactionStatus.DENSITY_PENDING.value: {
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value,
        TransactionStatus.EXIT_PENDING.value,
        TransactionStatus.APPROVAL_PENDING.value,
    },
    TransactionStatus.DOCUMENTS_PENDING.value: {
        TransactionStatus.DOCUMENTS_VERIFIED.value,
        TransactionStatus.APPROVAL_PENDING.value,
        TransactionStatus.EXIT_PENDING.value,
        TransactionStatus.EXCEPTION.value,
    },
    TransactionStatus.DOCUMENTS_VERIFIED.value: {
        TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value,
        TransactionStatus.APPROVAL_PENDING.value,
        TransactionStatus.EXIT_PENDING.value,
        TransactionStatus.APPROVED.value,
    },
    TransactionStatus.CUSTOMER_CONFIRMATION_PENDING.value: {
        TransactionStatus.CUSTOMER_CONFIRMED.value,
        TransactionStatus.EXCEPTION.value,
    },
    TransactionStatus.CUSTOMER_CONFIRMED.value: {
        TransactionStatus.APPROVAL_PENDING.value,
        TransactionStatus.APPROVED.value,
        TransactionStatus.EXIT_PENDING.value,
    },
    TransactionStatus.APPROVAL_PENDING.value: {
        TransactionStatus.APPROVED.value,
        TransactionStatus.REJECTED.value,
        TransactionStatus.EXCEPTION.value,
        TransactionStatus.DOCUMENTS_VERIFIED.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
    },
    TransactionStatus.APPROVED.value: {
        TransactionStatus.EXIT_PENDING.value,
    },
    TransactionStatus.EXIT_PENDING.value: {
        TransactionStatus.EXIT_COMPLETED.value,
        TransactionStatus.EXCEPTION.value,  # exit ANPR mismatch → supervisor
    },
    TransactionStatus.EXIT_COMPLETED.value: {
        TransactionStatus.COMPLETED.value,
    },
    TransactionStatus.EXCEPTION.value: {
        TransactionStatus.APPROVAL_PENDING.value,
        TransactionStatus.DOCUMENTS_PENDING.value,
        TransactionStatus.DOCUMENTS_VERIFIED.value,
        TransactionStatus.CANCELLED.value,
        TransactionStatus.REJECTED.value,
    },
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in ALLOWED.get(from_status, set())


def assert_transition(from_status: str, to_status: str) -> None:
    if not can_transition(from_status, to_status):
        raise ValueError(f"Invalid status change from {from_status} to {to_status}.")
