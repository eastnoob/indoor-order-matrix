"""Red contract tests for the frozen B3 read-only adapter seam."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from ..features.field_core import FieldQuery, FieldStatus
from ..features.space_field_adapter import B3AdapterView
from .test_discrete_space_field import load, payloads, write_package


def test_adapter_preserves_loader_identity_and_open_completeness(tmp_path, payloads):
    """The adapter keeps the validated package facts and conditional limitations."""
    field, sections = payloads
    write_package(tmp_path, field, sections)
    delivery = load(tmp_path)

    view = B3AdapterView.from_loaded(delivery)

    assert view.field == delivery["field"]
    assert view.variant == delivery["variant"]
    assert view.source_sections == delivery["source_sections"]
    assert view.artifact_manifest == delivery["artifact_manifest"]
    assert view.units == "m"
    assert view.primary_plane_world_z_m == 1.6
    assert view.complete_occupancy_geometry is None
    assert view.complete_physical_clearance_m is None
    assert view.provenance["schema"] == delivery["field"]["schema"]


@pytest.mark.parametrize(
    ("sample_index", "expected_status", "expected_value"),
    [
        (0, FieldStatus.CONDITIONAL, True),
        (1, FieldStatus.CONDITIONAL, False),
        (2, FieldStatus.UNKNOWN, None),
        (3, FieldStatus.OUTSIDE, None),
    ],
)
def test_adapter_maps_raw_b3_statuses_without_promoting_section_truth(
    tmp_path, payloads, sample_index, expected_status, expected_value
):
    """B3 section samples retain conditional, unknown, and outside semantics."""
    field, sections = payloads
    write_package(tmp_path, field, sections)
    view = B3AdapterView.from_loaded(load(tmp_path))

    sample = view.evaluate(sample_index, FieldQuery(domain_id="b3", frame="world-xy"))

    assert sample.status is expected_status
    assert sample.value == expected_value
    assert sample.query.frame == "world-xy"
    assert sample.provenance["algorithm_version"]
    assert sample.provenance["schema_version"]
    if expected_status is FieldStatus.CONDITIONAL:
        assert sample.explanation.strip()
        assert "section" in sample.explanation.lower()


def test_adapter_exposes_immutable_views_and_does_not_mutate_loader_result(tmp_path, payloads):
    """Adapter metadata is read-only and source delivery remains unchanged."""
    field, sections = payloads
    write_package(tmp_path, field, sections)
    delivery = load(tmp_path)
    view = B3AdapterView.from_loaded(delivery)

    assert isinstance(view.provenance, MappingProxyType)
    with pytest.raises((AttributeError, TypeError)):
        view.variant["samples"][0]["status"] = "changed"
    with pytest.raises((AttributeError, TypeError)):
        view.units = "mm"
    assert delivery["variant"]["samples"][0]["status"] == "established_occupied"
