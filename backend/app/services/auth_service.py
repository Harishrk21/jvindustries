from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.services.audit_service import write_audit

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15


def authenticate(db: Session, user_code: str, password: str) -> tuple[User | None, str | None]:
    user = db.execute(select(User).where(User.user_code == user_code)).scalar_one_or_none()
    if user is None:
        return None, "Invalid User ID or password."

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        return None, "Account temporarily locked due to failed login attempts. Try again later."

    if not user.is_active:
        return None, "User account is inactive."

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            user.failed_login_count = 0
        write_audit(
            db,
            action="LOGIN_FAILED",
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            details=f"Failed login for {user_code}",
        )
        db.commit()
        return None, "Invalid User ID or password."

    user.failed_login_count = 0
    user.locked_until = None
    token = create_access_token(user.id, {"roles": user.role_codes()})
    write_audit(
        db,
        action="LOGIN_SUCCESS",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        details=f"Login success for {user_code}",
    )
    db.commit()
    return user, token


def set_password(user: User, password: str) -> None:
    user.password_hash = hash_password(password)
