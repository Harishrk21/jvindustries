from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, UserOut
from app.services.audit_service import write_audit
from app.services.auth_service import authenticate

router = APIRouter()

_SEED_DEFAULTS = {
    "owner": "Owner@123",
    "security": "Security@123",
    "weighbridge": "Weigh@123",
    "store": "Store@123",
}


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        user_code=user.user_code,
        full_name=user.full_name,
        roles=user.role_codes(),
        permissions=sorted(user.permission_codes()),
        must_change_password=bool(getattr(user, "must_change_password", False)),
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user, token_or_error = authenticate(db, body.user_id.strip(), body.password)
    if user is None or token_or_error is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=token_or_error or "Invalid User ID or password.",
        )
    return LoginResponse(access_token=token_or_error, user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.post("/change-password", response_model=UserOut)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserOut:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    new_pw = body.new_password.strip()
    if len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")
    if new_pw == body.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current one.")
    # Block rotating back to published seed defaults
    default = _SEED_DEFAULTS.get(user.user_code.lower())
    if default and new_pw == default:
        raise HTTPException(status_code=400, detail="Choose a password that is not the seed default.")

    user.password_hash = hash_password(new_pw)
    user.must_change_password = False
    write_audit(
        db,
        action="PASSWORD_CHANGED",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        details=user.user_code,
    )
    db.commit()
    db.refresh(user)
    return _user_out(user)
