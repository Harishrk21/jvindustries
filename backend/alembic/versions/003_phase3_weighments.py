"""Phase 3 weighments + density + transaction weight columns

Revision ID: 003_phase3
Revises: 002_phase2
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_phase3"
down_revision: Union[str, None] = "002_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("tare_kg", sa.Float(), nullable=True))
    op.add_column("transactions", sa.Column("gross_kg", sa.Float(), nullable=True))
    op.add_column("transactions", sa.Column("net_kg", sa.Float(), nullable=True))
    op.add_column("transactions", sa.Column("density_kg_per_l", sa.Float(), nullable=True))
    op.add_column("transactions", sa.Column("temperature_c", sa.Float(), nullable=True))
    op.add_column("transactions", sa.Column("calculated_litres", sa.Float(), nullable=True))

    op.create_table(
        "weighments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_pk", sa.String(36), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("transaction_id", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("ocr_weight_kg", sa.Float(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("ocr_provider", sa.String(50), nullable=True),
        sa.Column("ocr_raw_text", sa.Text(), nullable=True),
        sa.Column("photo_id", sa.String(36), sa.ForeignKey("photos.id"), nullable=True),
        sa.Column("confirmed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("hardware_weight_kg", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("transaction_pk", "kind", name="uq_txn_weighment_kind"),
    )
    op.create_index("ix_weighments_transaction_pk", "weighments", ["transaction_pk"])
    op.create_index("ix_weighments_transaction_id", "weighments", ["transaction_id"])

    op.create_table(
        "density_readings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_pk", sa.String(36), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("transaction_id", sa.String(32), nullable=False),
        sa.Column("density_kg_per_l", sa.Float(), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("calculated_litres", sa.Float(), nullable=True),
        sa.Column("net_kg_snapshot", sa.Float(), nullable=True),
        sa.Column("ocr_density", sa.Float(), nullable=True),
        sa.Column("ocr_temperature", sa.Float(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("ocr_provider", sa.String(50), nullable=True),
        sa.Column("ocr_raw_text", sa.Text(), nullable=True),
        sa.Column("photo_id", sa.String(36), sa.ForeignKey("photos.id"), nullable=True),
        sa.Column("confirmed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_density_readings_transaction_pk", "density_readings", ["transaction_pk"])


def downgrade() -> None:
    op.drop_table("density_readings")
    op.drop_table("weighments")
    op.drop_column("transactions", "calculated_litres")
    op.drop_column("transactions", "temperature_c")
    op.drop_column("transactions", "density_kg_per_l")
    op.drop_column("transactions", "net_kg")
    op.drop_column("transactions", "gross_kg")
    op.drop_column("transactions", "tare_kg")
