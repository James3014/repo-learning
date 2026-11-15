"""Concrete RepoLearn state backends for the portable-runtime gates.

The local backend is intentionally file-only and private-by-default. The Nexus
adapter is compatibility/read-through only during James's pre-migration phase so
RepoLearn cannot accidentally create a second writable mastery source of truth.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import errno
from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import re
import stat
import uuid
from typing import Any

from .cue_policy import _parse_datetime, derive_fading_decision
from .event_validation import clamp_recommended_level, validate_learning_event
from .state import StateBackend, StateUnavailableError


class BackendConflictError(RuntimeError):
    """Raised when a stable identity is reused for different durable content."""


class StaleProjectionError(StateUnavailableError):
    """Raised when a stored projection is no longer bound to its event ledger.

    For normal client interactions this is an unavailable learning-state
    condition and therefore fails open to engineering. Migration preflight treats
    the same condition as fail-closed evidence.
    """


class ProjectionConflictError(StateUnavailableError):
    """Raised when learning evidence requires explicit reassessment."""


class ReadOnlyCanonicalBackendError(RuntimeError):
    """Raised when a compatibility backend refuses an unauthorized write."""


_LEVEL_ORDER = {"UNASSESSED": -1, "L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
_SAFE_PROFILE = re.compile(r"^[A-Za-z0-9._-]+$")
_DIR_FD_REQUIRED = (os.open, os.mkdir, os.stat, os.unlink, os.rmdir, os.rename)


def _has_safe_dir_fd_support() -> bool:
    return (
        hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_DIRECTORY")
        and all(operation in os.supports_dir_fd for operation in _DIR_FD_REQUIRED)
        and {"src_dir_fd", "dst_dir_fd"}.issubset(inspect.signature(os.replace).parameters)
        and os.stat in os.supports_follow_symlinks
        and os.listdir in os.supports_fd
    )


_HAS_SAFE_DIR_FD = _has_safe_dir_fd_support()


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _is_at_or_after(candidate: object, reference: object) -> bool:
    """Compare observed_at values as instants (offsets honoured), never as text.

    Unparseable candidates never become the latest observation.
    """
    candidate_instant = _parse_datetime(candidate)
    if candidate_instant is None:
        return False
    reference_instant = _parse_datetime(reference)
    return reference_instant is None or candidate_instant >= reference_instant


def _validate_profile_id(profile_id: str) -> str:
    if not _SAFE_PROFILE.fullmatch(profile_id):
        raise ValueError("profile_id must contain only letters, digits, dot, underscore or hyphen")
    return profile_id


class LocalFileBackend(StateBackend):
    """Private local JSON/JSONL backend with deterministic projection semantics."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()

    @staticmethod
    def _require_dir_fd_support() -> None:
        if not _HAS_SAFE_DIR_FD:
            raise StateUnavailableError(
                "local backend is unavailable: this platform lacks required no-follow directory-relative filesystem operations"
            )

    def _open_profile_dir(self, profile_id: str, *, create: bool = False, with_parent: bool = False) -> int | tuple[int, int]:
        """Open a profile directory without following replaceable path components."""
        self._require_dir_fd_support()
        profile_id = _validate_profile_id(profile_id)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_fd = os.open(self.root, flags)
        try:
            try:
                profiles_fd = os.open("profiles", flags, dir_fd=root_fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir("profiles", mode=0o700, dir_fd=root_fd)
                profiles_fd = os.open("profiles", flags, dir_fd=root_fd)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise ValueError("profiles directory must not be a symlink") from exc
            raise
        finally:
            os.close(root_fd)
        try:
            try:
                profile_fd = os.open(profile_id, flags, dir_fd=profiles_fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(profile_id, mode=0o700, dir_fd=profiles_fd)
                profile_fd = os.open(profile_id, flags, dir_fd=profiles_fd)
            except OSError as exc:
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                    try:
                        info = os.stat(profile_id, dir_fd=profiles_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        raise
                    if stat.S_ISLNK(info.st_mode):
                        raise ValueError("profile path must not be a symlink") from exc
                    raise BackendConflictError("profile path is not a directory") from exc
                raise
        except BaseException:
            os.close(profiles_fd)
            raise
        if with_parent:
            return profile_fd, profiles_fd
        os.close(profiles_fd)
        return profile_fd

    def _read_events(self, profile_id: str) -> list[dict[str, Any]]:
        self._require_dir_fd_support()
        try:
            profile_fd = self._open_profile_dir(profile_id)
        except FileNotFoundError:
            return []
        try:
            try:
                fd = os.open("events.jsonl", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=profile_fd)
            except FileNotFoundError:
                return []
            except OSError as exc:
                if exc.errno == errno.ELOOP:
                    raise ValueError("profile data files must not be symlinks") from exc
                raise
        finally:
            os.close(profile_fd)
        events: list[dict[str, Any]] = []
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        for line_number, raw in enumerate(lines, start=1):
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

    def _atomic_write_state(self, profile_fd: int, state: Mapping[str, Any]) -> None:
        payload = f"{json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)}\n"
        tmp_name = f".state-{uuid.uuid4().hex}.tmp"
        fd = os.open(tmp_name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=profile_fd)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, "state.json", src_dir_fd=profile_fd, dst_dir_fd=profile_fd)
        finally:
            try:
                os.unlink(tmp_name, dir_fd=profile_fd)
            except FileNotFoundError:
                pass

    def read_current_state(self, profile_id: str) -> Mapping[str, Any] | None:
        self._require_dir_fd_support()
        try:
            profile_fd = self._open_profile_dir(profile_id)
        except FileNotFoundError:
            return None
        try:
            try:
                fd = os.open("state.json", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=profile_fd)
            except FileNotFoundError:
                return None
            with os.fdopen(fd, "r", encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise StateUnavailableError("local state projection is unreadable") from exc
        finally:
            os.close(profile_fd)
        events = self._read_events(profile_id)
        expected_hash = _sha256_text(self._event_ledger_text(events))
        observed_hash = state.get("source", {}).get("content_hash") if isinstance(state, dict) else None
        if observed_hash != expected_hash:
            raise StaleProjectionError("local state projection is stale relative to the event ledger")
        return state

    def append_learning_event(self, profile_id: str, event: Mapping[str, Any]) -> str:
        self._require_dir_fd_support()
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
        validate_learning_event(event, prior_events=events)

        profile_fd = self._open_profile_dir(profile_id, create=True)
        try:
            fd = os.open(
                "events.jsonl",
                os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
                dir_fd=profile_fd,
            )
            with os.fdopen(fd, "a", encoding="utf-8") as handle:
                os.fchmod(handle.fileno(), 0o600)
                handle.write(canonical + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(profile_fd)
        return event_id

    def refresh_projection(self, profile_id: str) -> Mapping[str, Any]:
        self._require_dir_fd_support()
        events = self._read_events(profile_id)

        event_positions: dict[str, int] = {}
        for index, event in enumerate(events):
            event_id = event.get("event_id")
            if isinstance(event_id, str):
                event_positions[event_id] = index

        reassessment_targets: dict[str, str] = {}
        for index, event in enumerate(events):
            assessment = event.get("assessment", {})
            target = assessment.get("reassessment_of_event_id") if isinstance(assessment, Mapping) else None
            if not isinstance(target, str):
                continue
            if target not in event_positions or event_positions[target] >= index:
                raise ProjectionConflictError(
                    f"reassessment target {target!r} must reference an earlier event"
                )
            target_event = events[event_positions[target]]
            target_capability = target_event.get("capability", {})
            resolver_capability = event.get("capability", {})
            if (
                not isinstance(target_capability, Mapping)
                or not isinstance(resolver_capability, Mapping)
                or target_capability.get("domain") != resolver_capability.get("domain")
                or target_capability.get("concept") != resolver_capability.get("concept")
            ):
                raise ProjectionConflictError(
                    f"reassessment target {target!r} must resolve the same domain/concept"
                )
            resolver_id = event.get("event_id")
            if target in reassessment_targets:
                raise ProjectionConflictError(
                    f"reassessment target {target!r} has multiple resolutions"
                )
            reassessment_targets[target] = str(resolver_id)

        domains: dict[str, dict[str, Any]] = {}
        concepts: dict[str, dict[str, Any]] = {}
        latest_observed = "1970-01-01T00:00:00Z"

        def apply_level(
            current: dict[str, Any],
            *,
            level: str,
            event_id: str | None,
            observed_at: str | None,
            is_resolution: bool,
            conflict_has_resolution: bool,
            label: str,
        ) -> None:
            if level != "UNASSESSED":
                settled_level = current["level"]
                if settled_level != "UNASSESSED" and _LEVEL_ORDER[level] < _LEVEL_ORDER[settled_level]:
                    if is_resolution:
                        current["level"] = level
                    elif conflict_has_resolution:
                        pass
                    else:
                        raise ProjectionConflictError(
                            f"assessed level regression for {label!r} from {settled_level} to {level} "
                            "requires explicit reassessment before projection"
                        )
                else:
                    current["level"] = level
            if _is_at_or_after(observed_at, current["last_observed_at"]):
                current["last_event_id"] = event_id
                current["last_observed_at"] = observed_at

        clamped_prior: dict[tuple[Any, Any], str] = {}
        for event in events:
            capability = event.get("capability", {})
            assessment = event.get("assessment", {})
            attempt = event.get("attempt", {})
            domain = capability.get("domain") if isinstance(capability, Mapping) else None
            concept = capability.get("concept") if isinstance(capability, Mapping) else None
            # Persisted events are untrusted: never credit more than the attempt
            # evidence permits (Issue #51). Over-claims are clamped, not dropped.
            prior_key = (domain, concept)
            level = clamp_recommended_level(event, prior_level=clamped_prior.get(prior_key))
            if level != "UNASSESSED" and (
                prior_key not in clamped_prior
                or _LEVEL_ORDER[level] > _LEVEL_ORDER[clamped_prior[prior_key]]
            ):
                clamped_prior[prior_key] = level
            observed_at = event.get("observed_at")
            event_id = event.get("event_id")
            reassessment_of = (
                assessment.get("reassessment_of_event_id")
                if isinstance(assessment, Mapping)
                else None
            )
            is_resolution = isinstance(reassessment_of, str)
            conflict_has_resolution = (
                isinstance(event_id, str) and event_id in reassessment_targets
            )

            if isinstance(domain, str) and level in _LEVEL_ORDER:
                current = domains.setdefault(
                    domain,
                    {
                        "level": "UNASSESSED",
                        "evidence_count": 0,
                        "last_event_id": None,
                        "last_observed_at": None,
                    },
                )
                current["evidence_count"] += 1
                apply_level(
                    current,
                    level=level,
                    event_id=event_id if isinstance(event_id, str) else None,
                    observed_at=observed_at if isinstance(observed_at, str) else None,
                    is_resolution=is_resolution,
                    conflict_has_resolution=conflict_has_resolution,
                    label=domain,
                )

            if isinstance(concept, str) and level in _LEVEL_ORDER:
                current_concept = concepts.setdefault(
                    concept,
                    {
                        "level": "UNASSESSED",
                        "evidence_count": 0,
                        "last_event_id": None,
                        "last_observed_at": None,
                        "last_cue_level": None,
                        "silent_cue_fading_eligible": False,
                        "fading_valid_until": None,
                        "fading_basis_event_id": None,
                    },
                )
                current_concept["evidence_count"] += 1
                previous_observed = current_concept["last_observed_at"]
                apply_level(
                    current_concept,
                    level=level,
                    event_id=event_id if isinstance(event_id, str) else None,
                    observed_at=observed_at if isinstance(observed_at, str) else None,
                    is_resolution=is_resolution,
                    conflict_has_resolution=conflict_has_resolution,
                    label=concept,
                )
                is_latest = _is_at_or_after(observed_at, previous_observed)
                if is_latest and isinstance(attempt, Mapping):
                    cue_level = attempt.get("cue_level")
                    if cue_level in {"NONE", "LIGHT", "HEAVY"}:
                        current_concept["last_cue_level"] = cue_level

                if is_resolution or (
                    isinstance(assessment, Mapping)
                    and assessment.get("requires_reassessment") is True
                ):
                    current_concept["silent_cue_fading_eligible"] = False
                    current_concept["fading_valid_until"] = None
                    current_concept["fading_basis_event_id"] = None

                fading = derive_fading_decision(
                    event,
                    previous_observed_at=(
                        previous_observed if isinstance(previous_observed, str) else None
                    ),
                )
                if fading.eligible and (
                    current_concept["fading_valid_until"] is None
                    or str(fading.valid_until) >= str(current_concept["fading_valid_until"])
                ):
                    current_concept["silent_cue_fading_eligible"] = True
                    current_concept["fading_valid_until"] = fading.valid_until
                    current_concept["fading_basis_event_id"] = fading.basis_event_id

            observed_instant = _parse_datetime(observed_at)
            latest_instant = _parse_datetime(latest_observed)
            if observed_instant is not None and (
                latest_instant is None or observed_instant > latest_instant
            ):
                latest_observed = observed_at

        ledger_text = self._event_ledger_text(events)
        content_hash = _sha256_text(ledger_text)
        state: dict[str, Any] = {
            "schema": "repolearn.learning_state.v1",
            "profile_id": profile_id,
            "updated_at": latest_observed,
            "domains": domains,
            "concepts": concepts,
            "review_queue": [],
            "source": {
                "backend": "local-file",
                "revision": f"events:{len(events)}:{content_hash[:16]}",
                "content_hash": content_hash,
            },
        }
        profile_fd = self._open_profile_dir(profile_id, create=True)
        try:
            self._atomic_write_state(profile_fd, state)
        finally:
            os.close(profile_fd)
        return state

    def resolve_reassessment(
        self,
        profile_id: str,
        *,
        conflict_event_id: str,
        resolution_event: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Append an explicit reassessment resolution and rebuild projection.

        This provides a deterministic append-only recovery path for a previously
        appended contradictory event. The resolution event must have its own
        stable event_id and recommended_level; this method binds it to the exact
        conflicting event before append.
        """

        events = self._read_events(profile_id)
        target_event = next(
            (event for event in events if event.get("event_id") == conflict_event_id),
            None,
        )
        if target_event is None:
            raise ValueError("conflict_event_id does not exist")
        if any(
            isinstance(event.get("assessment"), Mapping)
            and event["assessment"].get("reassessment_of_event_id") == conflict_event_id
            for event in events
        ):
            raise ProjectionConflictError("conflict event already has a reassessment resolution")

        target_capability = target_event.get("capability", {})
        resolver_capability = resolution_event.get("capability", {})
        if (
            not isinstance(target_capability, Mapping)
            or not isinstance(resolver_capability, Mapping)
            or target_capability.get("domain") != resolver_capability.get("domain")
            or target_capability.get("concept") != resolver_capability.get("concept")
        ):
            raise ProjectionConflictError(
                "reassessment resolution must match the conflict event domain/concept"
            )

        payload = dict(resolution_event)
        assessment = dict(payload.get("assessment") or {})
        if assessment.get("recommended_level") not in _LEVEL_ORDER:
            raise ValueError("reassessment resolution requires a valid recommended_level")
        assessment["reassessment_of_event_id"] = conflict_event_id
        payload["assessment"] = assessment
        self.append_learning_event(profile_id, payload)
        return self.refresh_projection(profile_id)

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

    def export_profile(self, profile_id: str) -> str:
        """Return a deterministic privacy-scoped export without mutating state."""

        self._require_dir_fd_support()
        try:
            profile_fd = self._open_profile_dir(profile_id)
        except FileNotFoundError:
            profile_fd = None
        if profile_fd is not None:
            os.close(profile_fd)
        events = self._read_events(profile_id)
        state = self.read_current_state(profile_id)
        if state is None and events:
            raise StaleProjectionError("profile export requires a current state projection")
        payload = {
            "schema": "repolearn.profile_export.v1",
            "profile_id": _validate_profile_id(profile_id),
            "events": events,
            "state": state,
        }
        return _canonical_json(payload) + "\n"

    def delete_profile(self, profile_id: str) -> bool:
        """Delete only recognized files for one profile, refusing surprises."""

        self._require_dir_fd_support()
        try:
            profile_fd, profiles_fd = self._open_profile_dir(profile_id, with_parent=True)
        except FileNotFoundError:
            return False
        profile_id = _validate_profile_id(profile_id)
        allowed = {"events.jsonl", "state.json"}
        try:
            opened = os.fstat(profile_fd)
            current = os.stat(profile_id, dir_fd=profiles_fd, follow_symlinks=False)
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise BackendConflictError("profile directory changed during deletion")
            children = os.listdir(profile_fd)
            unknown = []
            for name in children:
                info = os.stat(name, dir_fd=profile_fd, follow_symlinks=False)
                if name not in allowed or not stat.S_ISREG(info.st_mode):
                    unknown.append(name)
            if unknown:
                raise BackendConflictError(
                    "refusing to delete profile with unrecognized files: " + ", ".join(sorted(unknown))
                )
            try:
                current = os.stat(profile_id, dir_fd=profiles_fd, follow_symlinks=False)
            except FileNotFoundError as exc:
                raise BackendConflictError("profile directory changed during deletion") from exc
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise BackendConflictError("profile directory changed during deletion")
            for name in children:
                os.unlink(name, dir_fd=profile_fd)
            try:
                current = os.stat(profile_id, dir_fd=profiles_fd, follow_symlinks=False)
            except FileNotFoundError as exc:
                raise BackendConflictError("profile directory changed during deletion") from exc
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise BackendConflictError("profile directory changed during deletion")
            # Atomically capture the directory entry, then verify what was
            # captured before removing it. A name-based rmdir after a stat
            # check could otherwise remove a replacement directory.
            quarantine = f".delete-{uuid.uuid4().hex}"
            try:
                os.rename(profile_id, quarantine, src_dir_fd=profiles_fd, dst_dir_fd=profiles_fd)
            except FileNotFoundError as exc:
                raise BackendConflictError("profile directory changed during deletion") from exc
            captured = os.stat(quarantine, dir_fd=profiles_fd, follow_symlinks=False)
            if (opened.st_dev, opened.st_ino) != (captured.st_dev, captured.st_ino):
                try:
                    os.rename(quarantine, profile_id, src_dir_fd=profiles_fd, dst_dir_fd=profiles_fd)
                except OSError:
                    pass
                raise BackendConflictError("profile directory changed during deletion")
            os.rmdir(quarantine, dir_fd=profiles_fd)
        finally:
            os.close(profile_fd)
            os.close(profiles_fd)
        return True

    def reset_profile(self, profile_id: str) -> Mapping[str, Any]:
        """Reset one profile to an empty projection without touching siblings."""

        self.delete_profile(profile_id)
        return self.refresh_projection(profile_id)


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
            "concepts": {},
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
