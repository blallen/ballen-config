"""Canonical serialization and digest helpers for review artifacts."""

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _normalize(value: Any) -> Any:
    """Return JSON-compatible NFC-normalized data."""
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    """Serialize one value as compact, sorted, NFC-normalized JSON."""
    payload = json.dumps(
        _normalize(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{payload}\n".encode()


def canonical_digest(value: Any) -> str:
    """Return the SHA-256 digest of canonical JSON bytes."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def source_digest(path: Path) -> str:
    """Return the SHA-256 digest of one exact source file."""
    return source_digest_bytes(path.read_bytes())


def source_digest_bytes(value: bytes) -> str:
    """Return the SHA-256 digest of one exact byte snapshot."""
    return hashlib.sha256(value).hexdigest()


def deduplication_key(
    *,
    provider: str,
    host: str,
    repository: str,
    change_number: int,
    kind: str,
    body: str,
    path: str | None = None,
    line: int | None = None,
    side: str | None = None,
    start_line: int | None = None,
    start_side: str | None = None,
    thread_id: str | None = None,
) -> str:
    """Return a stable key for one provider-targeted logical action."""
    return canonical_digest(
        {
            "provider": provider,
            "host": host,
            "repository": repository,
            "change_number": change_number,
            "kind": kind,
            "body": body,
            "path": path,
            "line": line,
            "side": side,
            "start_line": start_line,
            "start_side": start_side,
            "thread_id": thread_id,
        }
    )
