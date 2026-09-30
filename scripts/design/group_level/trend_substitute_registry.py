"""Read-only validation helpers for the D6 design-only substitute registry."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.substitute_contract import (
    display_spec as _display_spec,
    load_substitute_registry,
    resolve_substitute_contract,
)


SCHEMA = "d6-trend-substitute-registry/v1"


def _rejected(reason_code: str, **details: object) -> dict[str, object]:
    """Build a stable rejection record for legacy design callers."""
    return {"status": "rejected", "reason_code": reason_code, **details}


def load_registry(path: Path) -> dict[str, object]:
    """Load and validate the stable registry schema from JSON."""
    return load_substitute_registry(path)


def resolve_contract(record: Mapping[str, object], consumer: str, registry: Mapping[str, object]) -> dict[str, object]:
    """Resolve one typed instance without using labels or source names as authority."""
    return resolve_substitute_contract(record, consumer, registry)


def validate_records(records: list[Mapping[str, object]], consumer: str, registry: Mapping[str, object]) -> dict[str, object]:
    """Validate a batch and reject duplicate instance identities deterministically."""
    seen: set[object] = set()
    resolved = []
    for record in records:
        substitute_id = record.get("substitute_id")
        if substitute_id in seen:
            return _rejected("duplicate_substitute_id", substitute_id=substitute_id)
        seen.add(substitute_id)
        result = resolve_contract(record, consumer, registry)
        if result["status"] != "accepted":
            return result
        resolved.append(result)
    return {"status": "accepted", "records": resolved}


def display_spec(contract_key: str, registry: Mapping[str, object]) -> dict[str, object]:
    """Return editable display metadata without exposing it to semantic matching."""
    return _display_spec(contract_key, registry)
