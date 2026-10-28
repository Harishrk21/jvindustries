"""User administration (owner)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permissions
from app.core.security import hash_password
from app.models.user import Role, User
from app.services.audit_service import write_audit

router = APIRouter()


class UserAdminOut(BaseModel):
    id: str
    user_code: str
    full_name: str
    is_active: bool
    roles: list[str]

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    user_code: str = Field(..., min_length=2, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=150)
    password: str = Field(..., min_length=6, max_length=128)
    role_codes: list[str] = Field(..., min_length=1)
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role_codes: list[str] | None = None
    is_active: bool | None = None


def _to_admin(u: User) -> UserAdminOut:
    return UserAdminOut(
        id=u.id,
        user_code=u.user_code,
        full_name=u.full_name,
        is_active=u.is_active,
        roles=u.role_codes(),
    )


def _roles_or_400(db: Session, codes: list[str]) -> list[Role]:
    roles = list(db.execute(select(Role).where(Role.code.in_(codes))).scalars().all())
    found = {r.code for r in roles}
    missing = [c for c in codes if c not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown roles: {', '.join(missing)}")
    return roles


@router.get("/roles", response_model=list[str])
def list_role_codes(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("user.manage")),
) -> list[str]:
    return [r.code for r in db.execute(select(Role).order_by(Role.code)).scalars().all()]


@router.get("", response_model=list[UserAdminOut])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("user.manage")),
) -> list[UserAdminOut]:
    rows = list(db.execute(select(User).order_by(User.user_code)).scalars().all())
    return [_to_admin(u) for u in rows]


@router.post("", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permissions("user.manage")),
) -> UserAdminOut:
    code = body.user_code.strip().lower()
    exists = db.execute(select(User).where(User.user_code == code)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="User ID already exists.")
    roles = _roles_or_400(db, body.role_codes)
    row = User(
        user_code=code,
        full_name=body.full_name.strip(),
        password_hash=hash_password(body.password),
        is_active=body.is_active,
        must_change_password=True,
    )
    row.roles = roles
    db.add(row)
    db.flush()
    write_audit(
        db,
        action="USER_CREATED",
        entity_type="user",
        entity_id=row.id,
        actor_user_id=actor.id,
        details=f"{row.user_code} roles={','.join(body.role_codes)}",
    )
    db.commit()
    db.refresh(row)
    return _to_admin(row)


@router.patch("/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permissions("user.manage")),
) -> UserAdminOut:
    row = db.get(User, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if body.full_name is not None:
        row.full_name = body.full_name.strip()
    if body.password is not None:
        row.password_hash = hash_password(body.password)
        row.must_change_password = True
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.role_codes is not None:
        row.roles = _roles_or_400(db, body.role_codes)
    write_audit(
        db,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=row.id,
        actor_user_id=actor.id,
        details=row.user_code,
    )
    db.commit()
    db.refresh(row)
    return _to_admin(row)
