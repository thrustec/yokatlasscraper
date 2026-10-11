"""Atomic archive helpers that preserve the source response bytes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class ArchiveReceipt:
    path: str
    sha256: str
    byte_count: int
    captured_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_path(root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("archive path must stay inside the archive root")
    return root / relative


def write_bytes(root: Path, relative_path: str, body: bytes) -> ArchiveReceipt:
    destination = safe_path(root, relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_bytes(body)
    temporary.replace(destination)
    return ArchiveReceipt(
        path=relative_path.replace("\\", "/"),
        sha256=hashlib.sha256(body).hexdigest(),
        byte_count=len(body),
        captured_at=utc_now(),
    )


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def read_json(path: Path) -> object:
    return json.loads(path.read_bytes())


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)

