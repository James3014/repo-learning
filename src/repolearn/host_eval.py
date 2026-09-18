"""Helpers for privacy-safe host-level interaction evaluation."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

from .version import CONTRACT_CONTROL_FILES


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_user_visible_trace(
    *,
    user_message: str,
    progress_messages: Iterable[str] = (),
    final_response: str,
) -> str:
    """Bind evaluation to an exact user-visible trace without persisting it."""

    payload = {
        "user_message": user_message,
        "progress_messages": list(progress_messages),
        "final_response": final_response,
    }
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def compute_skill_content_sha256(skill_root: str | Path) -> str:
    """Fingerprint canonical Skill control files, excluding the manifest itself."""

    root = Path(skill_root)
    digest = sha256()
    for relative in CONTRACT_CONTROL_FILES:
        path = root / relative
        data = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()
