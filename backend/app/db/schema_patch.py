"""Additive MySQL column patches for create_all gaps (no Alembic yet)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger("jvoms.schema")

_TXN_COLUMNS = [
    ("product_id", "VARCHAR(36) NULL"),
    ("storage_unit_id", "VARCHAR(36) NULL"),
    ("stock_posted", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("customer_id", "VARCHAR(36) NULL"),
    ("supplier_id", "VARCHAR(36) NULL"),
    ("vehicle_type", "VARCHAR(40) NULL"),
    ("customer_whatsapp", "VARCHAR(20) NULL"),
    ("purpose", "VARCHAR(40) NULL"),
    ("from_location", "VARCHAR(200) NULL"),
    ("to_location", "VARCHAR(200) NULL"),
    ("remarks", "TEXT NULL"),
]

_PARTY_COLUMNS = [
    ("whatsapp", "VARCHAR(20) NULL"),
]

_GATE_PASS_COLUMNS = [
    ("vehicle_type", "VARCHAR(40) NULL"),
    ("driver_mobile", "VARCHAR(20) NULL"),
    ("transporter_name", "VARCHAR(150) NULL"),
    ("purpose", "VARCHAR(40) NULL"),
    ("material_description", "VARCHAR(200) NULL"),
    ("quantity_text", "VARCHAR(80) NULL"),
    ("unit_text", "VARCHAR(40) NULL"),
    ("invoice_challan_no", "VARCHAR(80) NULL"),
    ("from_location", "VARCHAR(200) NULL"),
    ("to_location", "VARCHAR(200) NULL"),
    ("remarks", "TEXT NULL"),
    ("vehicle_checked", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("goods_verified", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("documents_verified", "TINYINT(1) NOT NULL DEFAULT 0"),
]


def _ensure_columns(conn, table: str, columns: list[tuple[str, str]]) -> None:
    existing = {
        row[0]
        for row in conn.execute(
            text(
                """
                SELECT COLUMN_NAME FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table
                """
            ),
            {"table": table},
        )
    }
    for name, ddl in columns:
        if name in existing:
            continue
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        logger.info("Added %s.%s", table, name)


_USER_COLUMNS = [
    ("must_change_password", "TINYINT(1) NOT NULL DEFAULT 0"),
]


def ensure_phase5_columns(engine: Engine) -> None:
    with engine.begin() as conn:
        _ensure_columns(conn, "transactions", _TXN_COLUMNS)
        _ensure_columns(conn, "gate_passes", _GATE_PASS_COLUMNS)
        _ensure_columns(conn, "customers", _PARTY_COLUMNS)
        _ensure_columns(conn, "suppliers", _PARTY_COLUMNS)
        _ensure_columns(conn, "users", _USER_COLUMNS)
        for idx, col in (
            ("ix_transactions_product_id", "product_id"),
            ("ix_transactions_storage_unit_id", "storage_unit_id"),
            ("ix_transactions_customer_id", "customer_id"),
            ("ix_transactions_supplier_id", "supplier_id"),
        ):
            try:
                conn.execute(text(f"CREATE INDEX {idx} ON transactions ({col})"))
            except Exception:  # noqa: BLE001
                pass
