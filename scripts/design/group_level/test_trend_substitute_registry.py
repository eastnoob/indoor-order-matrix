"""Tests for the design-only trend substitute contract registry."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from trend_substitute_registry import display_spec, load_registry, resolve_contract, validate_records


ROOT = Path(__file__).parent


def _record() -> dict[str, object]:
    """Return a complete typed Analysis substitute record."""
    return {
        "substitute_id": "ifc-object:42:analysis",
        "source_object_id": "ifc-object:42",
        "consumer": "trend",
        "substitute_kind": "MassPatch",
        "analysis_role": "analysis_geometry_substitute",
        "representation_identifier": "Analysis",
        "provenance": {"representation_identifier": "Analysis"},
        "display_label": "editable label",
    }


def test_accepts_typed_analysis_record_and_ignores_display_label() -> None:
    """Semantic matching must accept typed Analysis input regardless of its label."""
    registry = load_registry(ROOT / "trend_substitute_registry.json")
    record = _record()
    accepted = resolve_contract(record, "trend", registry)
    assert accepted["status"] == "accepted"
    record["display_label"] = "Body-looking label"
    assert resolve_contract(record, "trend", registry)["status"] == "accepted"
    assert registry["contracts"]["trend_analysis"]["accepted_representation_identifier"] == "Analysis"


def test_rejects_body_provenance_even_when_typed_fields_look_like_analysis() -> None:
    """A Body representation cannot authorize a MassPatch trend substitute."""
    registry = load_registry(ROOT / "trend_substitute_registry.json")
    record = _record()
    record["provenance"] = {"representation_identifier": "Body"}
    result = resolve_contract(record, "trend", registry)
    assert result["status"] == "rejected"
    assert result["reason_code"] == "wrong_representation_identifier"


def test_rejects_wrong_typed_fields_and_missing_fields() -> None:
    """Wrong or incomplete typed bindings must report auditable reasons."""
    registry = load_registry(ROOT / "trend_substitute_registry.json")
    for field, value, reason in (
        ("consumer", "clearance", "wrong_consumer"),
        ("substitute_kind", "SurfacePatch", "wrong_substitute_kind"),
        ("analysis_role", "clearance_geometry", "wrong_analysis_role"),
        ("substitute_id", None, "missing_substitute_id"),
    ):
        record = _record()
        if value is None:
            record.pop(field)
        else:
            record[field] = value
        result = resolve_contract(record, "trend", registry)
        assert result["status"] == "rejected"
        assert result["reason_code"] == reason


def test_rejects_body_only_and_label_only_records() -> None:
    """Body-only and label-only records cannot authorize trend geometry."""
    registry = load_registry(ROOT / "trend_substitute_registry.json")
    body = {"substitute_id": "body:42", "source_object_id": "ifc-object:42", "consumer": "trend", "substitute_kind": "Body", "analysis_role": "body_geometry", "representation_identifier": "Body", "provenance": {"representation_identifier": "Body"}}
    label_only = {"substitute_id": "label:42", "consumer": "trend", "display_label": "trend"}
    assert resolve_contract(body, "trend", registry)["reason_code"] == "body_only"
    assert resolve_contract(label_only, "trend", registry)["reason_code"].startswith("missing_")


def test_rejects_duplicate_instance_ids_and_allows_display_edits() -> None:
    """Duplicate instance identity is rejected while display metadata stays editable."""
    registry = load_registry(ROOT / "trend_substitute_registry.json")
    records = [_record(), copy.deepcopy(_record())]
    result = validate_records(records, "trend", registry)
    assert result["status"] == "rejected"
    assert result["reason_code"] == "duplicate_substitute_id"
    edited = json.loads(json.dumps(registry))
    edited["contracts"]["trend_analysis"]["display"]["label"] = "renamed"
    assert resolve_contract(_record(), "trend", edited)["status"] == "accepted"
    assert display_spec("trend_analysis", edited)["label"] == "renamed"
