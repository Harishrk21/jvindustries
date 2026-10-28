"""Seed roles, permissions, and a default owner for Phase 1 development."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.core.config import get_settings
from app.models.calibration import WeighbridgeCalibration
from app.models.canteen import CanteenItem, CanteenStockMovement
from app.models.equipment import Equipment
from app.models.parties import Customer, Supplier
from app.models.stock import Product, StockMovement, StorageUnit
from app.models.system_setting import SystemSetting
from app.models.user import Permission, Role, User
from app.services.geofence_config import KEY_LAT, save_geofence_config

PERMISSIONS = [
    ("owner.full", "Full owner access"),
    ("dashboard.view", "View dashboard"),
    ("transaction.create", "Create transactions"),
    ("transaction.view", "View transactions"),
    ("transaction.search", "Search transactions"),
    ("device.register", "Register device"),
    ("photo.live", "Capture live camera evidence"),
    ("photo.gallery", "Owner gallery upload"),
    ("user.manage", "Manage users"),
    ("master.manage", "Manage masters"),
    ("config.geofence", "Configure geofence"),
    ("audit.view", "View audit"),
    ("approval.act", "Act on approvals"),
    ("vehicle.entry", "Vehicle entry"),
    ("vehicle.exit", "Vehicle exit"),
    ("vehicle.anpr", "ANPR recognition"),
    ("gatepass.create", "Create gate pass"),
    ("gatepass.view", "View gate pass"),
    ("weighment.tare", "Tare weighment"),
    ("weighment.gross", "Gross weighment"),
    ("document.invoice.capture", "Capture invoice"),
    ("document.eway.capture", "Capture E-Way Bill"),
    ("document.confirm", "Confirm document OCR"),
    ("storage.select", "Select storage unit"),
    ("stock.view", "View stock balances"),
    ("stock.adjust", "Request stock adjustment"),
    ("jobwork.manage", "Manage job-work batches"),
    ("production.loss.capture", "Capture production loss"),
    ("production.loss.approve", "Approve excess production loss"),
    ("otp.send", "Send customer OTP"),
    ("otp.verify", "Verify customer OTP"),
    ("notification.view", "View management alerts"),
    ("notification.send", "Send management alerts"),
    ("whatsapp.view", "View WhatsApp message log"),
    ("report.view", "View/download reports and PDFs"),
    ("report.export", "Export PDF/Excel reports"),
    ("equipment.repair", "Equipment repair out"),
    ("equipment.return", "Equipment repair return"),
    ("equipment.disposal", "Request equipment disposal"),
    ("equipment.approve", "Approve equipment disposal"),
    ("canteen.purchase", "Canteen purchase"),
    ("canteen.stock", "View/update canteen stock"),
]

ROLE_PERMS: dict[str, list[str]] = {
    "OWNER_ADMIN": [p[0] for p in PERMISSIONS],
    "SUPERVISOR": [
        "dashboard.view",
        "transaction.create",
        "transaction.view",
        "transaction.search",
        "device.register",
        "photo.live",
        "approval.act",
        "audit.view",
        "vehicle.entry",
        "vehicle.exit",
        "vehicle.anpr",
        "gatepass.create",
        "gatepass.view",
        "weighment.tare",
        "weighment.gross",
        "document.invoice.capture",
        "document.eway.capture",
        "document.confirm",
        "storage.select",
        "stock.view",
        "stock.adjust",
        "jobwork.manage",
        "production.loss.capture",
        "production.loss.approve",
        "otp.send",
        "otp.verify",
        "notification.view",
        "notification.send",
        "whatsapp.view",
        "report.view",
        "report.export",
        "equipment.repair",
        "equipment.return",
        "equipment.disposal",
        "equipment.approve",
        "canteen.purchase",
        "canteen.stock",
    ],
    "SECURITY": [
        "dashboard.view",
        "transaction.create",
        "transaction.view",
        "device.register",
        "photo.live",
        "vehicle.entry",
        "vehicle.exit",
        "vehicle.anpr",
        "gatepass.create",
        "gatepass.view",
    ],
    "WEIGHBRIDGE_OPERATOR": [
        "dashboard.view",
        "transaction.view",
        "device.register",
        "photo.live",
        "weighment.tare",
        "weighment.gross",
    ],
    "PRODUCTION_OPERATOR": [
        "dashboard.view",
        "transaction.create",
        "transaction.view",
        "device.register",
        "photo.live",
        "storage.select",
        "stock.view",
        "jobwork.manage",
        "production.loss.capture",
        "otp.send",
        "otp.verify",
        "equipment.repair",
        "equipment.return",
    ],
    "STORE_OPERATOR": [
        "dashboard.view",
        "transaction.create",
        "transaction.view",
        "device.register",
        "photo.live",
        "document.invoice.capture",
        "document.eway.capture",
        "document.confirm",
        "storage.select",
        "stock.view",
        "stock.adjust",
        "otp.send",
        "otp.verify",
        "equipment.repair",
        "equipment.return",
        "equipment.disposal",
    ],
    "CANTEEN_OPERATOR": [
        "dashboard.view",
        "transaction.create",
        "transaction.view",
        "device.register",
        "photo.live",
        "canteen.purchase",
        "canteen.stock",
    ],
}

ROLE_NAMES = {
    "OWNER_ADMIN": "Owner Admin",
    "SUPERVISOR": "Supervisor",
    "SECURITY": "Security",
    "WEIGHBRIDGE_OPERATOR": "Weighbridge Operator",
    "PRODUCTION_OPERATOR": "Production Operator",
    "STORE_OPERATOR": "Store Operator",
    "CANTEEN_OPERATOR": "Canteen Operator",
}


def seed_reference_data(db: Session) -> None:
    perm_by_code: dict[str, Permission] = {}
    for code, desc in PERMISSIONS:
        existing = db.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none()
        if existing is None:
            existing = Permission(code=code, description=desc)
            db.add(existing)
            db.flush()
        perm_by_code[code] = existing

    role_by_code: dict[str, Role] = {}
    for code, name in ROLE_NAMES.items():
        role = db.execute(select(Role).where(Role.code == code)).scalar_one_or_none()
        if role is None:
            role = Role(code=code, name=name)
            db.add(role)
            db.flush()
        role.permissions = [perm_by_code[p] for p in ROLE_PERMS[code] if p in perm_by_code]
        role_by_code[code] = role

    owner = db.execute(select(User).where(User.user_code == "owner")).scalar_one_or_none()
    if owner is None:
        owner = User(
            user_code="owner",
            full_name="JV Owner Admin",
            password_hash=hash_password("Owner@123"),
            is_active=True,
            must_change_password=False,
        )
        owner.roles = [role_by_code["OWNER_ADMIN"]]
        db.add(owner)
        db.flush()

    if owner is None:
        owner = db.execute(select(User).where(User.user_code == "owner")).scalar_one_or_none()

    for code, name, password, role_code in (
        ("security", "Security Operator", "Security@123", "SECURITY"),
        ("weighbridge", "Weighbridge Operator", "Weigh@123", "WEIGHBRIDGE_OPERATOR"),
        ("store", "Store Operator", "Store@123", "STORE_OPERATOR"),
        ("supervisor", "Plant Supervisor", "Super@123", "SUPERVISOR"),
        ("production", "Production Operator", "Prod@123", "PRODUCTION_OPERATOR"),
        ("canteen", "Canteen Operator", "Canteen@123", "CANTEEN_OPERATOR"),
    ):
        if db.execute(select(User).where(User.user_code == code)).scalar_one_or_none() is None:
            u = User(
                user_code=code,
                full_name=name,
                password_hash=hash_password(password),
                is_active=True,
                must_change_password=False,
            )
            if role_code in role_by_code:
                u.roles = [role_by_code[role_code]]
            db.add(u)

    settings = get_settings()
    force_pw = settings.app_env.lower() in {"production", "prod"}
    # Flag seed passwords only in production; development keeps seed logins usable
    for code, password in (
        ("owner", "Owner@123"),
        ("security", "Security@123"),
        ("weighbridge", "Weigh@123"),
        ("store", "Store@123"),
        ("supervisor", "Super@123"),
        ("production", "Prod@123"),
        ("canteen", "Canteen@123"),
    ):
        u = db.execute(select(User).where(User.user_code == code)).scalar_one_or_none()
        if u and verify_password(password, u.password_hash):
            u.must_change_password = force_pw

    _seed_geofence_defaults(db, owner.id if owner else None)
    _seed_stock_masters(db, owner.id if owner else None)
    _seed_equipment_masters(db)
    _seed_canteen_masters(db, owner.id if owner else None)
    _seed_party_masters(db)
    _seed_calibration(db)
    db.commit()


def _seed_geofence_defaults(db: Session, actor_id: str | None) -> None:
    """Persist / refresh yard circle from env (replaces old Chennai demo pin)."""
    s = get_settings()
    # Upgrade known demo pin to Chittoor defaults when still on Chennai sample
    row = db.get(SystemSetting, KEY_LAT)
    if row is not None:
        try:
            cur = float(row.value)
        except (TypeError, ValueError):
            cur = None
        if cur is not None and abs(cur - 13.0827) > 0.0001 and abs(cur - s.gps_geofence_lat) > 0.0001:
            return  # custom plant pin already set by owner
    save_geofence_config(
        db,
        lat=s.gps_geofence_lat,
        lon=s.gps_geofence_lon,
        radius_m=s.gps_geofence_radius_m,
        max_accuracy_m=s.gps_max_accuracy_m,
        actor_user_id=actor_id,
    )


def _seed_calibration(db: Session) -> None:
    """Sample Legal Metrology cert from plant weighment slip template."""
    cert_no = "CTR72521126R0563"
    if db.execute(
        select(WeighbridgeCalibration).where(WeighbridgeCalibration.certificate_no == cert_no)
    ).scalar_one_or_none():
        return
    db.add(
        WeighbridgeCalibration(
            certificate_no=cert_no,
            verification_date=date(2026, 5, 29),
            next_due_date=date(2027, 5, 28),
            officer_name="Sri N. Swamy",
            officer_title="Assistant Controller, Tirupati",
            make_model="TRUWEIGH SYSTEM (IND/09/22/502)",
            max_capacity_kg=60000,
            min_capacity_kg=200,
            accuracy_class="Class III",
            e_value_kg=10,
            d_value_kg=10,
            seals_count=2,
            seals_note="Indicator & JB",
            location_label="JV Industries Weighbridge — Chittoor",
            is_active=True,
        )
    )


def _seed_party_masters(db: Session) -> None:
    if db.execute(select(Customer).where(Customer.code == "CUST-ABC")).scalar_one_or_none() is None:
        db.add(
            Customer(
                code="CUST-ABC",
                name="ABC Industries",
                mobile="9876543210",
                whatsapp="9876543210",
                gstin="33AAAAA0000A1Z5",
                address="Chittoor, Andhra Pradesh",
                active=True,
            )
        )
    if db.execute(select(Customer).where(Customer.code == "SAI-PETRO")).scalar_one_or_none() is None:
        db.add(
            Customer(
                code="SAI-PETRO",
                name="SAI PETRO",
                mobile="9888877777",
                whatsapp="9888877777",
                gstin="37AAAAA0000A1Z5",
                address="Andhra Pradesh",
                active=True,
            )
        )
    if db.execute(select(Supplier).where(Supplier.code == "SUP-XYZ")).scalar_one_or_none() is None:
        db.add(
            Supplier(
                code="SUP-XYZ",
                name="XYZ Petrochem",
                mobile="9000000001",
                whatsapp="9000000001",
                gstin="33BBBBB0000B1Z5",
                address="Supplier yard",
                active=True,
            )
        )


def _seed_equipment_masters(db: Session) -> None:
    for code, name, category, loc in (
        ("EQ-PUMP-01", "Transfer Pump 01", "PUMP", "Pump house"),
        ("EQ-GEN-02", "Diesel Generator 02", "GENERATOR", "Yard B"),
        ("EQ-SCALE-01", "Mobile Weigh Scale", "SCALE", "Weighbridge"),
    ):
        if db.execute(select(Equipment).where(Equipment.code == code)).scalar_one_or_none() is None:
            db.add(
                Equipment(
                    code=code,
                    name=name,
                    category=category,
                    location_label=loc,
                    status="IN_YARD",
                    active=True,
                )
            )


def _seed_canteen_masters(db: Session, owner_id: str | None) -> None:
    """TEST_PLAN: Rice / Dal / Oil with opening stock."""
    seeds = (
        ("RICE", "Rice", "KG", 100.0),
        ("DAL", "Dal", "KG", 50.0),
        ("OIL", "Oil", "L", 40.0),
        ("SUGAR", "Sugar", "KG", 25.0),
        ("WHEAT", "Wheat", "KG", 30.0),
    )
    for code, name, unit, opening_qty in seeds:
        item = db.execute(select(CanteenItem).where(CanteenItem.code == code)).scalar_one_or_none()
        if item is None:
            item = CanteenItem(code=code, name=name, unit=unit, active=True)
            db.add(item)
            db.flush()
        has_open = db.execute(
            select(CanteenStockMovement).where(
                CanteenStockMovement.item_id == item.id,
                CanteenStockMovement.direction == "OPENING",
            )
        ).scalar_one_or_none()
        if has_open is None and owner_id:
            db.add(
                CanteenStockMovement(
                    item_id=item.id,
                    direction="OPENING",
                    quantity=opening_qty,
                    unit=unit,
                    note="Seed opening canteen stock",
                    created_by=owner_id,
                )
            )


def _seed_stock_masters(db: Session, owner_id: str | None) -> None:
    """Fuel Oil + Tank T-03 with opening 100,000 L (TEST_PLAN fixture)."""
    product = db.execute(select(Product).where(Product.code == "FUEL_OIL")).scalar_one_or_none()
    if product is None:
        product = Product(
            code="FUEL_OIL",
            name="Fuel Oil",
            hsn="2710",
            unit="L",
            density_default=0.845,
            loss_limit_percent=2.0,
            active=True,
        )
        db.add(product)
        db.flush()

    tank = db.execute(select(StorageUnit).where(StorageUnit.code == "T-03")).scalar_one_or_none()
    if tank is None:
        tank = StorageUnit(
            code="T-03",
            name="Tank T-03",
            kind="TANK",
            capacity=500000,
            capacity_unit="L",
            product_id=product.id,
            location_label="Main yard",
            active=True,
        )
        db.add(tank)
        db.flush()

    # Opening balance once
    opening = db.execute(
        select(StockMovement).where(
            StockMovement.storage_unit_id == tank.id,
            StockMovement.direction == "OPENING",
        )
    ).scalar_one_or_none()
    if opening is None and owner_id:
        db.add(
            StockMovement(
                product_id=product.id,
                storage_unit_id=tank.id,
                direction="OPENING",
                quantity=100000.0,
                unit="L",
                quantity_litres=100000.0,
                note="Seed opening balance (TEST_PLAN T-03)",
                created_by=owner_id,
            )
        )

    # Extra sample vessels
    for code, name, kind, cap in (
        ("B-01", "Barrel B-01", "BARREL", 200.0),
        ("IBC-01", "IBC-01", "IBC", 1000.0),
    ):
        if db.execute(select(StorageUnit).where(StorageUnit.code == code)).scalar_one_or_none() is None:
            db.add(
                StorageUnit(
                    code=code,
                    name=name,
                    kind=kind,
                    capacity=cap,
                    capacity_unit="L",
                    product_id=product.id,
                    active=True,
                )
            )
