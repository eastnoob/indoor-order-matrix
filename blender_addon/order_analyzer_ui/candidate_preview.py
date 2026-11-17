"""Transient candidate selection and eye state for the Analyzer workbench."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

_EYE_IDS: set[str] = set()


def candidate_id(candidate: Mapping[str, object]) -> str:
    """Return the stable UI identity already present in the domain session."""
    return str(candidate.get("version_id") or candidate.get("id") or candidate.get("source_id") or "")


def select_candidate(candidates: Iterable[Mapping[str, object]], selected_id: str | None) -> str | None:
    """Keep selection single-valued and reject ids absent from the current cache."""
    wanted = str(selected_id or "")
    return wanted if any(candidate_id(item) == wanted for item in candidates) else None


def eye_enabled(candidates: Iterable[Mapping[str, object]], eye_ids: Iterable[str]) -> tuple[Mapping[str, object], ...]:
    """Return only eye-enabled candidates, preserving their true polygon rings."""
    enabled = {str(item) for item in eye_ids}
    return tuple(item for item in candidates if candidate_id(item) in enabled)


def toggle_eye(candidate: Mapping[str, object]) -> bool:
    """Toggle one transient eye flag and return its new state."""
    item_id = candidate_id(candidate)
    if item_id in _EYE_IDS:
        _EYE_IDS.remove(item_id)
        return False
    _EYE_IDS.add(item_id)
    return True


def eye_ids() -> frozenset[str]:
    """Expose transient eye ids for rebuilding the GPU cache."""
    return frozenset(_EYE_IDS)


