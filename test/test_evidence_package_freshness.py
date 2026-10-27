"""Focused tests for evidence package freshness and cache status."""

from __future__ import annotations

import json

import pytest

from features.field_core import (
    build_evidence_package_contract,
    evaluate_evidence_package_freshness,
    fingerprint_evidence_dependency,
)


def _contract(
    *,
    target_ids: tuple[str, ...] = ("group-a", "group-b"),
    package_id: str = "group-geometry-relation",
    package_schema: str = "group-geometry-relation/v1",
    producer: str = "test-runner",
    algorithm_version: str = "algorithm/1",
    schema_version: str = "schema/1",
    changes: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a complete deterministic contract for status comparisons."""
    values: dict[str, object] = {
        "scene": {"model": "scene-1"},
        "model": {"groups": target_ids},
        "source": {"ifc": "source-1"},
        "plane": {"axis": "z", "value": 1.2},
        "query": {"height": "0-2", "demand": "relation"},
        "recipe": {"channels": ["overlap", "distance"]},
        "channels": ["overlap", "distance"],
    }
    if changes:
        values.update(changes)
    dependencies = {name: fingerprint_evidence_dependency(value) for name, value in values.items()}
    return build_evidence_package_contract(
        package_id=package_id,
        package_schema=package_schema,
        producer=producer,
        target_ids=target_ids,
        dependencies=dependencies,
        algorithm_version=algorithm_version,
        schema_version=schema_version,
        artifacts={"report": "report.json"},
    )


def _reason_codes(status: dict[str, object]) -> set[str]:
    """Extract reason codes from the JSON-facing status payload."""
    return {reason["code"] for reason in status["reasons"]}  # type: ignore[index]


def test_identical_contracts_are_fresh_with_no_invalidation_targets() -> None:
    """An unchanged package is reusable and does not request recomputation."""
    contract = _contract()

    status = evaluate_evidence_package_freshness(
        cached_contract=contract,
        current_contract=_contract(),
    )

    assert status["freshness"] == "fresh"
    assert status["recompute_required"] is False
    assert status["reasons"] == []
    assert status["affected_targets"] == []
    json.dumps(contract)
    json.dumps(status)
    assert status["invalidation_scope"] == "whole_package"
    assert status["algorithm"] == {
        "status": "same",
        "cached_version": "algorithm/1",
        "current_version": "algorithm/1",
        "recompute_required": False,
    }
    assert set(status) == {
        "schema",
        "package_id",
        "cached_package_identity",
        "current_package_identity",
        "freshness",
        "recompute_required",
        "reasons",
        "affected_targets",
        "invalidation_scope",
        "algorithm",
    }


@pytest.mark.parametrize(
    ("dependency", "expected_code"),
    [
        ("scene", "scene_changed"),
        ("model", "model_changed"),
        ("source", "source_changed"),
        ("plane", "plane_changed"),
        ("query", "query_changed"),
        ("recipe", "recipe_changed"),
        ("channels", "channel_set_changed"),
    ],
)
def test_dependency_change_marks_whole_package_stale(
    dependency: str, expected_code: str
) -> None:
    """Every declared dependency invalidates the complete package in v1."""
    cached = _contract()
    current = _contract(changes={dependency: {"changed": True}})

    status = evaluate_evidence_package_freshness(
        cached_contract=cached,
        current_contract=current,
    )

    assert status["freshness"] == "stale"
    assert status["recompute_required"] is True
    assert expected_code in _reason_codes(status)
    assert status["affected_targets"] == ["group-a", "group-b"]
    assert status["invalidation_scope"] == "whole_package"


def test_algorithm_mismatch_is_reported_separately_and_is_stale() -> None:
    """Algorithm drift is conservative while remaining distinct from inputs."""
    cached = _contract(algorithm_version="algorithm/1")
    current = _contract(algorithm_version="algorithm/2")

    status = evaluate_evidence_package_freshness(
        cached_contract=cached,
        current_contract=current,
    )

    assert status["freshness"] == "stale"
    assert "algorithm_version_changed" in _reason_codes(status)
    assert status["algorithm"] == {
        "status": "changed",
        "cached_version": "algorithm/1",
        "current_version": "algorithm/2",
        "recompute_required": True,
    }


def test_schema_change_is_stale_with_schema_reason() -> None:
    """Package or result schema drift cannot reuse the cached artifact."""
    cached = _contract(package_schema="group-geometry-relation/v1", schema_version="schema/1")
    current = _contract(package_schema="group-geometry-relation/v2", schema_version="schema/2")

    status = evaluate_evidence_package_freshness(
        cached_contract=cached,
        current_contract=current,
    )

    assert status["freshness"] == "stale"
    assert "schema_changed" in _reason_codes(status)


def test_target_additions_and_removals_use_union_for_affected_targets() -> None:
    """Target-set drift reports all potentially invalid group targets."""
    cached = _contract(target_ids=("group-a", "group-b"))
    current = _contract(target_ids=("group-b", "group-c"))

    status = evaluate_evidence_package_freshness(
        cached_contract=cached,
        current_contract=current,
    )

    assert status["freshness"] == "stale"
    assert "model_changed" in _reason_codes(status)
    assert status["affected_targets"] == ["group-a", "group-b", "group-c"]


def test_edit_then_undo_restores_freshness() -> None:
    """Restoring every dependency to its original identity restores freshness."""
    cached = _contract()
    changed = _contract(changes={"scene": {"model": "scene-2"}})

    stale = evaluate_evidence_package_freshness(
        cached_contract=cached,
        current_contract=changed,
    )
    restored = evaluate_evidence_package_freshness(
        cached_contract=cached,
        current_contract=_contract(),
    )

    assert stale["freshness"] == "stale"
    assert restored["freshness"] == "fresh"
    assert restored["reasons"] == []
    assert restored["affected_targets"] == []


def test_missing_contract_is_unavailable_and_requires_recompute() -> None:
    """Without a cached snapshot, the current package cannot claim reuse."""
    status = evaluate_evidence_package_freshness(
        cached_contract=None,
        current_contract=_contract(),
    )

    assert status["freshness"] == "unavailable"
    assert status["recompute_required"] is True
    assert _reason_codes(status) == {"package_missing"}
    assert status["affected_targets"] == ["group-a", "group-b"]


def test_malformed_contract_is_unavailable_and_invalid() -> None:
    """Malformed snapshots fail closed with a stable invalid reason."""
    status = evaluate_evidence_package_freshness(
        cached_contract={"schema": "wrong", "target_ids": ["group-a"]},
        current_contract=_contract(),
    )

    assert status["freshness"] == "unavailable"
    assert status["recompute_required"] is True
    assert _reason_codes(status) == {"package_invalid"}
    assert status["affected_targets"] == ["group-a", "group-b"]


def test_unavailable_artifacts_force_package_invalid_status() -> None:
    """A missing report artifact makes an otherwise matching package unusable."""
    contract = _contract()

    status = evaluate_evidence_package_freshness(
        cached_contract=contract,
        current_contract=_contract(),
        artifacts_available=False,
    )

    assert status["freshness"] == "unavailable"
    assert status["recompute_required"] is True
    assert _reason_codes(status) == {"package_invalid"}
    assert status["affected_targets"] == ["group-a", "group-b"]


def test_missing_both_contracts_is_unavailable() -> None:
    """A status request without either side of the comparison fails closed."""
    status = evaluate_evidence_package_freshness(
        cached_contract=None,
        current_contract=None,
    )

    assert status["freshness"] == "unavailable"
    assert status["recompute_required"] is True
    assert _reason_codes(status) == {"package_missing"}


def test_contract_requires_all_dependency_roles() -> None:
    """Partial dependency declarations cannot claim a reproducible package."""
    with pytest.raises(ValueError, match="missing required names"):
        build_evidence_package_contract(
            package_id="package",
            package_schema="package/v1",
            producer="test",
            target_ids=("group-a",),
            dependencies={"scene": "scene"},
            algorithm_version="algorithm/1",
            schema_version="schema/1",
        )
