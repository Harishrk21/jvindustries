"""Phase 2 vehicle, ANPR, gate pass tables

Revision ID: 002_phase2
Revises: 001_phase1
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_phase2"
down_revision: Union[str, None] = "001_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vehicle_number", sa.String(32), nullable=False),
        sa.Column("transporter_name", sa.String(150), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vehicles_vehicle_number", "vehicles", ["vehicle_number"], unique=True)

    op.create_table(
        "drivers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("mobile", sa.String(20), nullable=False),
        sa.Column("license_no", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_drivers_mobile", "drivers", ["mobile"])

    op.create_table(
        "gate_pass_sequences",
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column("transactions", sa.Column("vehicle_id", sa.String(36), sa.ForeignKey("vehicles.id"), nullable=True))
    op.add_column("transactions", sa.Column("vehicle_number", sa.String(32), nullable=True))
    op.add_column("transactions", sa.Column("driver_id", sa.String(36), sa.ForeignKey("drivers.id"), nullable=True))
    op.add_column("transactions", sa.Column("driver_name", sa.String(150), nullable=True))
    op.add_column("transactions", sa.Column("driver_mobile", sa.String(20), nullable=True))
    op.add_column("transactions", sa.Column("transporter_name", sa.String(150), nullable=True))
    op.add_column("transactions", sa.Column("entry_photo_id", sa.String(36), nullable=True))
    op.add_column("transactions", sa.Column("exit_photo_id", sa.String(36), nullable=True))
    op.create_index("ix_transactions_vehicle_number", "transactions", ["vehicle_number"])

    op.create_table(
        "photos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_pk", sa.String(36), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("transaction_id", sa.String(32), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("capture_source", sa.String(40), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_id", sa.String(36), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("gps_accuracy", sa.Float(), nullable=True),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_photos_transaction_pk", "photos", ["transaction_pk"])
    op.create_index("ix_photos_transaction_id", "photos", ["transaction_id"])

    op.create_table(
        "anpr_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_pk", sa.String(36), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("transaction_id", sa.String(32), nullable=False),
        sa.Column("photo_id", sa.String(36), sa.ForeignKey("photos.id"), nullable=True),
        sa.Column("vehicle_number", sa.String(32), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("manual_reason", sa.Text(), nullable=True),
        sa.Column("confirmed_vehicle_number", sa.String(32), nullable=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_anpr_results_transaction_pk", "anpr_results", ["transaction_pk"])

    op.create_table(
        "gate_passes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("gate_pass_number", sa.String(40), nullable=False),
        sa.Column("transaction_pk", sa.String(36), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("transaction_id", sa.String(32), nullable=False),
        sa.Column("pass_type", sa.String(50), nullable=False),
        sa.Column("vehicle_number", sa.String(32), nullable=True),
        sa.Column("driver_name", sa.String(150), nullable=True),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gate_passes_gate_pass_number", "gate_passes", ["gate_pass_number"], unique=True)
    op.create_index("ix_gate_passes_transaction_pk", "gate_passes", ["transaction_pk"])
    op.create_index("ix_gate_passes_transaction_id", "gate_passes", ["transaction_id"])


def downgrade() -> None:
    op.drop_table("gate_passes")
    op.drop_table("anpr_results")
    op.drop_table("photos")
    op.drop_index("ix_transactions_vehicle_number", table_name="transactions")
    op.drop_column("transactions", "exit_photo_id")
    op.drop_column("transactions", "entry_photo_id")
    op.drop_column("transactions", "transporter_name")
    op.drop_column("transactions", "driver_mobile")
    op.drop_column("transactions", "driver_name")
    op.drop_column("transactions", "driver_id")
    op.drop_column("transactions", "vehicle_number")
    op.drop_column("transactions", "vehicle_id")
    op.drop_table("gate_pass_sequences")
    op.drop_table("drivers")
    op.drop_table("vehicles")
