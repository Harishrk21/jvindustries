from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vehicle import GatePassSequence


def next_gate_pass_number(db: Session, when: datetime | None = None) -> str:
    now = when or datetime.now(timezone.utc)
    year = now.year
    seq = db.execute(
        select(GatePassSequence).where(GatePassSequence.year == year).with_for_update()
    ).scalar_one_or_none()
    if seq is None:
        seq = GatePassSequence(year=year, last_value=0)
        db.add(seq)
        db.flush()
    seq.last_value += 1
    db.flush()
    return f"JV/GP/{year}/{seq.last_value:05d}"
