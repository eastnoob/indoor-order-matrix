"""Contract tests for package-owned parameter snapshots."""

from dataclasses import replace
import json

import pytest

from features.evidence_package_parameters import (
    ParameterImpact,
    ParameterSchema,
    ParameterSnapshot,
    ParameterSpec,
    compare_parameter_snapshots,
)


def _schema() -> ParameterSchema:
    """Provide calculation, warning and display knobs for contract tests."""
    return ParameterSchema("contract-package", "contract-parameters/1", (
        ParameterSpec("width_m", float, 1.0, unit="m", minimum=0.0),
        ParameterSpec("review_m", float, 0.01, unit="m", minimum=0.0,
                      impact=ParameterImpact.REUSE_WITH_WARNING),
        ParameterSpec("label", str, "A", impact=ParameterImpact.METADATA_ONLY),
    ))


def test_source_labels_do_not_change_identity():
    """An explicit default value denotes the same calculation."""
    first = _schema().resolve()
    gui = _schema().resolve({"width_m": 1}, sources={"width_m": "gui"})
    assert gui.effective_parameters["width_m"] == 1.0
    assert first.parameter_fingerprint == gui.parameter_fingerprint
    assert first.parameter_sources != gui.parameter_sources


def test_warning_projection_preserves_calculated_and_requested_values():
    """Warning reuse cannot pretend current intent was historically calculated."""
    first = _schema().resolve()
    requested = _schema().resolve({"review_m": 0.02, "label": "B"})
    status = compare_parameter_snapshots(first, requested)
    assert first.parameter_fingerprint == requested.parameter_fingerprint
    assert status["reuse"] == "reuse_with_warning"
    assert status["exact_match"] is False
    assert status["calculated_parameters"]["review_m"] == 0.01
    assert status["requested_parameters"]["review_m"] == 0.02
    assert [item["parameter"] for item in status["warnings"]] == ["review_m"]
    changed = _schema().resolve({"width_m": 2.0})
    assert changed.parameter_fingerprint != first.parameter_fingerprint
    assert compare_parameter_snapshots(first, changed)["recompute_required"]


@pytest.mark.parametrize("values", [
    {"width_m": True}, {"width_m": float("nan")}, {"width_m": float("inf")},
    {"width_m": -1.0}, {"width_m": {"value": 100, "unit": "cm"}},
    {"unknown": 1.0},
])
def test_invalid_values(values):
    """Malformed inputs never reach algorithms or fingerprinting."""
    with pytest.raises((TypeError, ValueError)):
        _schema().resolve(values)


def test_required_context_and_old_default_roundtrip():
    """Required geometry stays required and saved defaults stay expanded."""
    required = ParameterSchema("p", "p/1", (ParameterSpec("plane", dict),))
    with pytest.raises(ValueError, match="missing"):
        required.resolve()
    old = _schema().resolve()
    changed = replace(_schema(), specs=(
        replace(_schema().specs[0], default=2.0),
        _schema().specs[1], _schema().specs[2]))
    saved = ParameterSnapshot.from_json(json.loads(json.dumps(old.to_json())))
    assert saved == old
    assert saved.calculated_parameters["width_m"] == 1.0
    assert changed.resolve().effective_parameters["width_m"] == 2.0
    with pytest.raises(TypeError):
        saved.calculated_parameters["width_m"] = 3.0


def test_required_nullable_context_has_stable_schema_and_roundtrip():
    """An absent datum is explicit context, independent of requiredness/defaults."""
    schema = ParameterSchema("p", "p/1", (
        ParameterSpec("datum", dict, unit="request_context", nullable=True),))
    with pytest.raises(ValueError, match="missing"):
        schema.resolve()
    absent = schema.resolve({"datum": None})
    present = schema.resolve({"datum": {"kind": "slab", "z_m": 0.0}})
    assert absent.config_schema_version == present.config_schema_version == "p/1"
    assert absent.parameter_fingerprint != present.parameter_fingerprint
    assert ParameterSnapshot.from_json(absent.to_json()) == absent
    assert ParameterSnapshot.from_json(present.to_json()) == present
    assert absent.parameter_value_contracts["datum"] == {
        "type": "dict", "nullable": True, "unit": "request_context"}
    with pytest.raises((TypeError, ValueError)):
        ParameterSchema("p", "p/1", (ParameterSpec("datum", dict),)).resolve(
            {"datum": None})
    malformed = absent.to_json()
    malformed["parameter_value_contracts"]["datum"]["nullable"] = False
    with pytest.raises((TypeError, ValueError)):
        ParameterSnapshot.from_json(malformed)


def test_capture_calculated_never_fills_a_missing_saved_default():
    """Historical capture requires every field even when today's schema has defaults."""
    with pytest.raises(ValueError, match="missing"):
        _schema().capture_calculated({"width_m": 1.0}, sources={"width_m": "legacy"})


def test_saved_value_contract_cannot_reclassify_current_calculation_fields():
    """A receipt cannot self-attest a weaker impact/type contract for reuse."""
    current = _schema().resolve()
    weaker_schema = replace(_schema(), specs=(
        replace(_schema().specs[0], impact=ParameterImpact.METADATA_ONLY),
        _schema().specs[1], _schema().specs[2]))
    weaker = weaker_schema.resolve()
    assert compare_parameter_snapshots(weaker, current)["recompute_required"]
    malformed = current.to_json()
    malformed["parameter_value_contracts"]["width_m"]["type"] = "arbitrary.Class"
    with pytest.raises((TypeError, ValueError)):
        ParameterSnapshot.from_json(malformed)


def test_schema_rejects_duplicates_choices_and_noncanonical_declarations():
    """Declaration errors fail before any package calculation can use them."""
    with pytest.raises(ValueError, match="duplicate"):
        ParameterSchema("p", "v1", (
            ParameterSpec("x", int, 1), ParameterSpec("x", int, 2)))
    with pytest.raises(ValueError, match="choice"):
        ParameterSchema("p", "v1", (ParameterSpec("x", int, 1, choices=(1, 2)),)).resolve({"x": 3})
    with pytest.raises(ValueError):
        ParameterSpec("x", float, 1.0, unit="cm")


def test_nested_values_are_frozen_and_key_order_is_canonical():
    """Nested JSON is detached and equivalent mapping order has one identity."""
    value = {"b": [2, {"z": 0.0}], "a": 1}
    schema = ParameterSchema("p", "v1", (ParameterSpec("context", dict, unit="request_context"),))
    first = schema.resolve({"context": value})
    value["b"][1]["z"] = 3.0
    second = schema.resolve({"context": {"a": 1, "b": [2, {"z": 0.0}]}})
    assert first == second
    with pytest.raises(TypeError):
        first.effective_parameters["context"]["a"] = 2


def test_snapshot_corruption_and_source_contracts_are_rejected():
    """Receipt corruption and invalid provenance labels fail closed."""
    snapshot = _schema().resolve()
    malformed = snapshot.to_json()
    malformed["parameter_fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint"):
        ParameterSnapshot.from_json(malformed)
    with pytest.raises(TypeError):
        _schema().resolve(sources={"width_m": 1})
    with pytest.raises(ValueError):
        _schema().capture_calculated(
            {"width_m": 1.0, "review_m": 0.01, "label": "A"},
            sources={"width_m": "legacy"})


def test_direct_snapshot_construction_freezes_mutable_inputs():
    """Public snapshot construction must detach mutable nested caller data."""
    effective = {"context": {"nested": [1, {"value": 2.0}]}}
    snapshot = ParameterSnapshot(
        "p",
        "v1",
        effective,
        effective,
        {"context": "request"},
        {"context": ParameterImpact.RECOMPUTE_REQUIRED.value},
        {"context": {"type": "dict", "nullable": False, "unit": "request_context"}},
        "",
    )
    effective["context"]["nested"][1]["value"] = 9.0
    assert snapshot.effective_parameters["context"]["nested"][1]["value"] == 2.0
    with pytest.raises(TypeError):
        snapshot.effective_parameters["context"]["nested"][1]["value"] = 3.0
