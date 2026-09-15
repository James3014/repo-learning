"""Concrete RepoLearn state backends for the portable-runtime gates.

The local backend is intentionally file-only and private-by-default. The Nexus
adapter is compatibility/read-through only during James's pre-migration phase so
RepoLearn cannot accidentally create a second writable mastery source of truth.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .state import StateBackend, StateUnavailableError


class BackendConflictError(RuntimeError):
    """Raised when a stable identity is reused for different durable content."""


class StaleProjectionError(RuntimeError):
    """Raised when a stored projection is no longer bound to its event ledger."""


class ReadOnlyCanonicalBackendError(RuntimeError):
    """Raised when a compatibility backend refuses an unauthorized write."""


_LEVEL_ORDER = {"UNASSESSED": -1, "L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
_SAFE_PROFILE = re.compile(r"^[A-Za-z0-9._-]+$")


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _validate_profile_id(profile_id: str) -> str:
    if not _SAFE_PROFILE.fullmatch(profile_id):
        raise ValueError("profile_id must contain only letters, digits, dot, underscore or hyphen")
    return profile_id


class LocalFileBackend(StateBackend):
    """Private local JSON/JSONL backend with deterministic projection semantics."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()

    def _profile_dir(self, profile_id: str) -> Path:
        return self.root / "profiles" / _validate_profile_id(profile_id)

    def _events_path(self, profile_id: str) -> Path:
        return self._profile_dir(profile_id) / "events.jsonl"

    def _state_path(self, profile_id: str) -> Path:
        return self._profile_dir(profile_id) / "state.json"

    def _read_events(self, profile_id: str) -> list[dict[str, Any]]:
        path = self._events_path(profile_id)
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise StateUnavailableError(f"invalid local event ledger at line {line_number}") from exc
            if not isinstance(event, dict):
                raise StateUnavailableError(f"non-object local event at line {line_number}")
            events.append(event)
        return events

    def _event_ledger_text(self, events: Sequence[Mapping[str, Any]]) -> str:
        return "".join(f"{_canonical_json(event)}\n" for event in events)

    def _atomic_write_state(self, path: Path, state: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        payload = f"{json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)}\n"
        fd, tmp_name = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=path.parent, text=True)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
            os.chmod(path, 0o600)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def read_current_state(self, profile_id: str) -> Mapping[str, Any] | None:
        path = self._state_path(profile_id)
        if not path.exists():
            return None
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateUnavailableError("local state projection is unreadable") from exc
        events = self._read_events(profile_id)
        expected_hash = _sha256_text(self._event_ledger_text(events))
        observed_hash = state.get("source", {}).get("content_hash") if isinstance(state, dict) else None
        if observed_hash != expected_hash:
            raise StaleProjectionError("local state projection is stale relative to the event ledger")
        return state

    def append_learning_event(self, profile_id: str, event: Mapping[str, Any]) -> str:
        _validate_profile_id(profile_id)
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id is required")
        event_profile = event.get("profile_id")
        if event_profile is not None and event_profile != profile_id:
            raise ValueError("event profile_id does not match backend profile")
        canonical = _canonical_json(event)
        events = self._read_events(profile_id)
        for existing in events:
            if existing.get("event_id") != event_id:
                continue
            if _canonical_json(existing) == canonical:
                return event_id
            raise BackendConflictError(f"event_id {event_id!r} already exists with different content")

        path = self._events_path(profile_id)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "a", encoding="utf-8") as handle:
                handle.write(canonical + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.chmod(path, 0o600)
        return event_id

    def refresh_projection(self, profile_id: str) -> Mapping[str, Any]:
        events = self._read_events(profile_id)
        domains: dict[str, dict[str, Any]] = {}
        latest_observed = "1970-01-01T00:00:00Z"
        for event in events:
            domain = event.get("capability", {}).get("domain")
            level = event.get("assessment", {}).get("recommended_level")
            observed_at = event.get("observed_at")
            event_id = event.get("event_id")
            if not isinstance(domain, str) or level not in _LEVEL_ORDER:
                continue
            current = domains.setdefault(
                domain,
                {"level": "UNASSESSED", "evidence_count": 0, "last_event_id": None, "last_observed_at": None},
            )
            current["evidence_count"] += 1
            if _LEVEL_ORDER[level] > _LEVEL_ORDER[current["level"]]:
                current["level"] = level
            if isinstance(observed_at, str) and (current["last_observed_at"] is None or observed_at >= current["last_observed_at"]):
                current["last_event_id"] = event_id
                current["last_observed_at"] = observed_at
            if isinstance(observed_at, str) and observed_at > latest_observed:
                latest_observed = observed_at

        ledger_text = self._event_ledger_text(events)
        content_hash = _sha256_text(ledger_text)
        state: dict[str, Any] = {
            "schema": "repolearn.learning_state.v1",
            "profile_id": profile_id,
            "updated_at": latest_observed,
            "domains": domains,
            "review_queue": [],
            "source": {
                "backend": "local-file",
                "revision": f"events:{len(events)}:{content_hash[:16]}",
                "content_hash": content_hash,
            },
        }
        self._atomic_write_state(self._state_path(profile_id), state)
        return state

    def read_related_history(
        self,
        profile_id: str,
        *,
        concept: str | None = None,
        limit: int = 20,
    ) -> Sequence[Mapping[str, Any]]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        events = self._read_events(profile_id)
        if concept is not None:
            events = [event for event in events if event.get("capability", {}).get("concept") == concept]
        return tuple(events[-limit:] if limit else [])


class NexusLedgerBackend(StateBackend):
    """Read-through adapter for the existing Nexus Owner-learning Ledger.

    G4 deliberately keeps this adapter read-only. James's canonical owner remains
    the Nexus Ledger until a later explicit migration transaction. RepoLearn can
    consume its bounded projection without gaining write authority over Nexus-new.
    """

    _STATE_HEADING = "## Current Learning State — bounded bootstrap projection"
    _REVISION_RE = re.compile(r"\*\*目前狀態修訂：\*\*\s*`([^`]+)`")
    _DOMAIN_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(UNASSESSED|L[0-4])\s*\|")

    def __init__(self, ledger_text: str, *, source_revision: str, expected_content_hash: str | None = None) -> None:
        if self._STATE_HEADING not in ledger_text:
            raise StateUnavailableError("Nexus Ledger bounded current-state projection is missing")
        self.ledger_text = ledger_text
        self.source_revision = source_revision
        self.content_hash = _sha256_text(ledger_text)
        if expected_content_hash is not None and self.content_hash != expected_content_hash:
            raise StaleProjectionError("Nexus Ledger content hash does not match the bound source")

    def _projection_section(self) -> str:
        _, tail = self.ledger_text.split(self._STATE_HEADING, 1)
        next_heading = tail.find("\n## ")
        return tail if next_heading < 0 else tail[:next_heading]

    def read_current_state(self, profile_id: str) -> Mapping[str, Any] | None:
        section = self._projection_section()
        revision_match = self._REVISION_RE.search(section)
        if not revision_match:
            raise StateUnavailableError("Nexus Ledger current-state revision is missing")
        state_revision = revision_match.group(1).strip()
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", state_revision)
        updated_at = f"{date_match.group(1)}T00:00:00Z" if date_match else "1970-01-01T00:00:00Z"

        domains: dict[str, dict[str, Any]] = {}
        for line in section.splitlines():
            match = self._DOMAIN_ROW_RE.match(line)
            if not match:
                continue
            domain = match.group(1).strip()
            if domain in {"Architecture domain", "---"}:
                continue
            domains[domain] = {
                "level": match.group(2),
                "evidence_count": 0,
                "last_event_id": None,
                "last_observed_at": None,
            }

        if not domains:
            raise StateUnavailableError("Nexus Ledger domain-level mastery table is missing")

        return {
            "schema": "repolearn.learning_state.v1",
            "profile_id": profile_id,
            "updated_at": updated_at,
            "domains": domains,
            "review_queue": [],
            "source": {
                "backend": "nexus-ledger-readthrough",
                "revision": f"{self.source_revision}:{state_revision}",
                "content_hash": self.content_hash,
            },
        }

    def append_learning_event(self, profile_id: str, event: Mapping[str, Any]) -> str:
        raise ReadOnlyCanonicalBackendError(
            "G4 NexusLedgerBackend is read-through only; RepoLearn has no Nexus Ledger write authority"
        )

    def refresh_projection(self, profile_id: str) -> Mapping[str, Any]:
        state = self.read_current_state(profile_id)
        if state is None:
            raise StateUnavailableError("Nexus Ledger current state is unavailable")
        return state

    def read_related_history(
        self,
        profile_id: str,
        *,
        concept: str | None = None,
        limit: int = 20,
    ) -> Sequence[Mapping[str, Any]]:
        return ()
