"""Contract tests for the clean-room canonical layout records."""

from __future__ import annotations

import math

import pytest

from ..features.canonical_layout_contract import (
    AnalysisFrame,
    AuthoredGroupFact,
    AxisSpec,
    CanonicalScene,
    DescriptorResult,
    PlanGeometry,
    ResultStatus,
    SourceGeometry3D,
    SourceObjectFact,
    validate_canonical_scene,
)


IDENTITY_4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def _frame() -> AnalysisFrame:
    """Build the small metre-based frame used by hand-built contract facts."""
    return AnalysisFrame(
        frame_id="frame-main",
        origin=(0.0, 0.0, 0.0),
        basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        source_unit="mm",
        analysis_unit="m",
        geometry_tolerance=1e-6,
        topology_tolerance=1e-6,
        plane="xy",
        provenance={"method": "hand_built_fixture"},
    )


def _scene() -> CanonicalScene:
    """Build a valid scene with deliberately unsorted references."""
    objects = (
        SourceObjectFact(
            object_id="object-b",
            semantic_type="IfcFurniture",
            world_transform=IDENTITY_4,
            geometry_refs=("geometry-b",),
            authored_group_refs=("group-1",),
            source_unit="mm",
            provenance={"source": "fixture"},
        ),
        SourceObjectFact(
            object_id="object-a",
            semantic_type="IfcFurniture",
            world_transform=IDENTITY_4,
            geometry_refs=("geometry-a",),
            authored_group_refs=("group-1",),
            source_unit="mm",
            provenance={"source": "fixture"},
        ),
    )
    geometries = (
        SourceGeometry3D(
            geometry_id="geometry-b",
            object_id="object-b",
            vertices=((1000.0, 0.0, 0.0), (1100.0, 0.0, 0.0), (1000.0, 100.0, 0.0)),
            triangles=((0, 1, 2),),
            source_representation="IfcShapeRepresentation:body",
            source_unit="mm",
            world_transform=IDENTITY_4,
            provenance={"source": "fixture"},
        ),
        SourceGeometry3D(
            geometry_id="geometry-a",
            object_id="object-a",
            vertices=((0.0, 0.0, 0.0), (100.0, 0.0, 0.0), (0.0, 100.0, 0.0)),
            triangles=((0, 1, 2),),
            source_representation="IfcShapeRepresentation:body",
            source_unit="mm",
            world_transform=IDENTITY_4,
            provenance={"source": "fixture"},
        ),
    )
    return CanonicalScene(
        frame=_frame(),
        axes=(AxisSpec("frame-main", "x", (1.0, 0.0, 0.0), "increasing"),),
        objects=objects,
        source_geometries=geometries,
        plan_geometries=(
            PlanGeometry(
                object_id="object-b",
                vertices=((1.0, 0.0), (1.1, 0.0), (1.0, 0.1)),
                triangles=((0, 1, 2),),
                frame_id="frame-main",
                unit="m",
                source_representation="IfcShapeRepresentation:body",
                method="project_xy",
                unit_conversion=0.001,
                status=ResultStatus.COMPUTED,
                provenance={"source_representation": "IfcShapeRepresentation:body"},
            ),
        ),
        authored_groups=(AuthoredGroupFact("group-1", ("object-b", "object-a"), "IfcGroup:G1"),),
    )


def test_valid_records_round_trip_and_canonicalize_reference_order() -> None:
    """Valid records serialize strictly and stable references survive a round trip."""
    scene = _scene()
    payload = scene.to_dict()
    restored = CanonicalScene.from_dict(payload)

    assert [item.object_id for item in restored.objects] == ["object-a", "object-b"]
    assert restored.groups[0].member_object_ids == ("object-a", "object-b")
    assert restored == scene
    validate_canonical_scene(restored)


@pytest.mark.parametrize("status", tuple(ResultStatus))
def test_descriptor_result_accepts_each_status_with_explicit_value_rules(
    status: ResultStatus,
) -> None:
    """Computed results carry a value while unavailable states remain value-free."""
    result = DescriptorResult(
        descriptor_id="relative-order",
        scope="objects",
        value=0.5 if status is ResultStatus.COMPUTED else None,
        status=status,
        algorithm_id="relative-order/v1",
        object_ids=("object-b", "object-a"),
        parameters={"tolerance": 1e-6},
        provenance={"method": "fixture"},
        reason=None if status is ResultStatus.COMPUTED else "fixture_reason",
    )

    assert DescriptorResult.from_dict(result.to_dict()) == result


def test_rejects_empty_ids_nonfinite_values_invalid_units_and_bad_frames() -> None:
    """Construction rejects malformed identifiers, numbers, units, and bases."""
    with pytest.raises(ValueError, match="non-empty"):
        SourceObjectFact(" ")
    with pytest.raises(ValueError, match="finite"):
        SourceObjectFact("object", provenance={"bad": math.inf})
    with pytest.raises(ValueError, match="unit"):
        AnalysisFrame(
            "frame",
            (0.0, 0.0, 0.0),
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            "yards",
            "m",
            1e-6,
            1e-6,
        )
    with pytest.raises(ValueError, match="orthonormal"):
        AnalysisFrame(
            "frame",
            (0.0, 0.0, 0.0),
            ((1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            "m",
            "m",
            1e-6,
            1e-6,
        )
    with pytest.raises(ValueError, match="tolerance"):
        AnalysisFrame(
            "frame",
            (0.0, 0.0, 0.0),
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            "m",
            "m",
            0.0,
            1e-6,
        )


def test_rejects_unknown_status_inconsistent_value_and_unexpected_json_field() -> None:
    """Deserialization rejects unknown enums, status/value mismatches, and extra fields."""
    payload = DescriptorResult(
        descriptor_id="relative-order",
        scope="objects",
        value=0.5,
        status=ResultStatus.COMPUTED,
        algorithm_id="relative-order/v1",
    ).to_dict()
    payload["status"] = "maybe"
    with pytest.raises(ValueError, match="status"):
        DescriptorResult.from_dict(payload)

    payload = DescriptorResult(
        descriptor_id="relative-order",
        scope="objects",
        value=None,
        status=ResultStatus.NOT_AVAILABLE,
        algorithm_id="relative-order/v1",
        reason="missing",
    ).to_dict()
    payload["value"] = 0.0
    with pytest.raises(ValueError, match="value"):
        DescriptorResult.from_dict(payload)

    payload = _frame().to_dict()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="unexpected"):
        AnalysisFrame.from_dict(payload)
