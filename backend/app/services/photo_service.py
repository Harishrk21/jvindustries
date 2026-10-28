from __future__ import annotations

import hashlib

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.enums import CaptureSource
from app.models.transaction import Transaction
from app.models.user import User
from app.models.vehicle import Photo
from app.storage.local_evidence import LocalEvidenceStore


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


def assert_capture_source(user: User, capture_source: str) -> None:
    if capture_source not in {CaptureSource.LIVE_CAMERA.value, CaptureSource.OWNER_GALLERY_UPLOAD.value}:
        raise HTTPException(status_code=400, detail="Invalid capture_source.")
    if capture_source == CaptureSource.OWNER_GALLERY_UPLOAD.value:
        from app.core.config import get_settings

        settings = get_settings()
        # Dev / soft mode: allow gallery so desktop & permission issues don't block yard testing.
        if settings.debug or settings.app_env == "development":
            return
        perms = user.permission_codes()
        if "photo.gallery" not in perms and "owner.full" not in perms:
            raise HTTPException(
                status_code=403,
                detail="Gallery upload is not allowed for your role. Use live camera only.",
            )


async def store_evidence_photo(
    db: Session,
    *,
    txn: Transaction,
    user: User,
    upload: UploadFile,
    file_type: str,
    capture_source: str,
    device_id: str | None,
    lat: float,
    lon: float,
    accuracy_m: float,
    image_bytes: bytes | None = None,
) -> tuple[Photo, bytes]:
    assert_capture_source(user, capture_source)
    content_type = (upload.content_type or "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG/WebP evidence images are accepted.")

    data = image_bytes if image_bytes is not None else await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image upload.")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 15 MB).")

    ext = ".jpg"
    filename = (upload.filename or "").lower()
    if filename.endswith(".png"):
        ext = ".png"
    elif filename.endswith(".webp"):
        ext = ".webp"

    stored = LocalEvidenceStore().save(
        transaction_id=txn.transaction_id,
        file_type=file_type,
        data=data,
        extension=ext,
    )
    # Verify integrity of what we persist
    if hashlib.sha256(data).hexdigest() != stored.content_hash:
        raise HTTPException(status_code=500, detail="Evidence integrity check failed.")

    photo = Photo(
        transaction_pk=txn.id,
        transaction_id=txn.transaction_id,
        file_type=file_type,
        capture_source=capture_source,
        user_id=user.id,
        device_id=device_id,
        latitude=lat,
        longitude=lon,
        gps_accuracy=accuracy_m,
        storage_path=stored.storage_path,
        content_hash=stored.content_hash,
    )
    db.add(photo)
    db.flush()
    return photo, data
