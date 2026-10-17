"""Shared typed substitute contract loading and matching."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path


SCHEMA = "d6-trend-substitute-registry/v1"
_REQUIRED = (
    "substitute_id",
    "source_object_id",
    "consumer",
    "substitute_kind",
    "analysis_role",
    "representation_identifier",
    "provenance",
)
_DEFAULT_REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "design"
    / "group_level"
    / "trend_substitute_registry.json"
)


def load_substitute_registry(path: Path = _DEFAULT_REGISTRY) -> dict[str, object]:
    """Load the repository's single substitute contract registry."""
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema") not in {SCHEMA, "d6-substitute-registry/v2"} or not isinstance(registry.get("contracts"), dict):
        raise ValueError(f"unsupported registry schema: {registry.get('schema')!r}")
    for key, contract in registry["contracts"].items():
        if (
            not contract.get("consumer")
            or not contract.get("accepted_substitute_kind")
            or not contract.get("accepted_analysis_role")
            or not (contract.get("accepted_representation_identifier") or contract.get("accepted_representation_identifiers"))
        ):
            raise ValueError(f"incomplete contract: {key}")
    operations = registry.get("operations", {})
    if operations and not isinstance(operations, Mapping):
        raise ValueError("operations must be a mapping")
    return registry


def resolve_substitute_contract(
    record: Mapping[str, object],
    consumer: str,
    registry: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Match one typed binding against registry semantics only."""
    registry = registry or load_substitute_registry()
    for field in _REQUIRED:
        if field not in record or record[field] in (None, ""):
            return {"status": "rejected", "reason_code": f"missing_{field}"}
    if not isinstance(record.get("provenance"), Mapping):
        return {"status": "rejected", "reason_code": "invalid_provenance"}
    if record.get("consumer") != consumer:
        return {"status": "rejected", "reason_code": "wrong_consumer"}
    if str(record.get("substitute_kind")).lower() == "body" or str(record.get("analysis_role")).lower() == "body_geometry":
        return {"status": "rejected", "reason_code": "body_only"}
    contracts = registry.get("contracts", {})
    matching_consumers = [
        (key, contract)
        for key, contract in contracts.items()
        if contract.get("consumer") == consumer
    ]
    for key, contract in matching_consumers:
        if record.get("substitute_kind") not in contract.get("accepted_substitute_kind", []):
            continue
        if record.get("analysis_role") not in contract.get("accepted_analysis_role", []):
            continue
        accepted_representations = contract.get("accepted_representation_identifiers") or [contract.get("accepted_representation_identifier")]
        expected_representation = record.get("representation_identifier")
        if expected_representation not in accepted_representations:
            return {
                "status": "rejected",
                "reason_code": "wrong_representation_identifier",
                "contract_key": key,
                "expected": accepted_representations,
            }
        if record["provenance"].get("representation_identifier") != expected_representation:
            return {
                "status": "rejected",
                "reason_code": "wrong_representation_identifier",
                "contract_key": key,
                "expected": accepted_representations,
            }
        return {
            "status": "accepted",
            "contract_key": key,
            "substitute_id": record["substitute_id"],
            "source_object_id": record["source_object_id"],
            "accepted_representation_identifier": expected_representation,
        }
    if matching_consumers:
        contract = matching_consumers[0][1]
        if record.get("substitute_kind") not in contract.get("accepted_substitute_kind", []):
            reason = "wrong_substitute_kind"
        elif record.get("analysis_role") not in contract.get("accepted_analysis_role", []):
            reason = "wrong_analysis_role"
        else:
            reason = "no_matching_contract"
        return {"status": "rejected", "reason_code": reason}
    return {"status": "rejected", "reason_code": "no_matching_contract"}


def display_spec(contract_key: str, registry: Mapping[str, object] | None = None) -> dict[str, object]:
    """Return editable display metadata without affecting contract matching."""
    registry = registry or load_substitute_registry()
    try:
        return dict(registry["contracts"][contract_key]["display"])
    except KeyError as exc:
        raise KeyError(f"unknown contract: {contract_key}") from exc


__all__ = ["display_spec", "load_substitute_registry", "resolve_substitute_contract"]
