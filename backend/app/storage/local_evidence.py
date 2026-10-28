"""Local evidence store — originals never overwritten.

When S3 credentials are configured later, swap implementation behind ObjectStorageClient.
Until then, files are stored under EVIDENCE_ROOT with SHA-256 integrity hashes.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


@dataclass(frozen=True)
class StoredEvidence:
    storage_path: str
    content_hash: str
    size_bytes: int


class LocalEvidenceStore:
    def __init__(self, root: Path | None = None) -> None:
        settings = get_settings()
        self.root = root or Path(getattr(settings, "evidence_root", "./evidence_store"))
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        *,
        transaction_id: str,
        file_type: str,
        data: bytes,
        extension: str = ".jpg",
    ) -> StoredEvidence:
        digest = hashlib.sha256(data).hexdigest()
        folder = self.root / transaction_id / file_type.lower()
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}{extension}"
        path = folder / name
        # Never overwrite: uuid filename guarantees uniqueness
        path.write_bytes(data)
        relative = str(path.relative_to(self.root)).replace("\\", "/")
        return StoredEvidence(storage_path=relative, content_hash=digest, size_bytes=len(data))

    def absolute_path(self, storage_path: str) -> Path:
        return self.root / storage_path
