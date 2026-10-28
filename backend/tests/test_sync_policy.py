from app.services.sync_policy import decide_on_existing


def test_idempotent_soft_status():
    d = decide_on_existing(
        existing_status="DRAFT",
        incoming_type="MATERIAL_LOADING_OUTWARD",
        existing_type="MATERIAL_LOADING_OUTWARD",
    )
    assert d.outcome == "IDEMPOTENT"


def test_conflict_progressed_status():
    d = decide_on_existing(
        existing_status="COMPLETED",
        incoming_type="MATERIAL_LOADING_OUTWARD",
        existing_type="MATERIAL_LOADING_OUTWARD",
    )
    assert d.outcome == "CONFLICT"


def test_conflict_type_mismatch():
    d = decide_on_existing(
        existing_status="DRAFT",
        incoming_type="JOB_WORK",
        existing_type="MATERIAL_LOADING_OUTWARD",
    )
    assert d.outcome == "CONFLICT"
