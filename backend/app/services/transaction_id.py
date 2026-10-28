from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import TransactionSequence


def next_transaction_id(db: Session, when: datetime | None = None) -> str:
    """Generate JV-YYYY-NNNNNN using a yearly sequence row (transactional)."""
    now = when or datetime.now(timezone.utc)
    year = now.year

    seq = db.execute(
        select(TransactionSequence).where(TransactionSequence.year == year).with_for_update()
    ).scalar_one_or_none()

    if seq is None:
        seq = TransactionSequence(year=year, last_value=0)
        db.add(seq)
        db.flush()

    seq.last_value += 1
    db.flush()
    return f"JV-{year}-{seq.last_value:06d}"
