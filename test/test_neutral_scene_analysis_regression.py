from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from math import cos, radians, sin

import pytest
from shapely.geometry import Polygon, mapping, shape

from ..adapters.ifc_bonsai import load_ifc_neutral_scene
from ..adapters.svg_scene import load_svg_neutral_scene
from ..features._analysis_domain_handoff import domain_handoff
from ..features.affordance.models import Rect
from ..features.column_grid import column_grid_evidence
from ..features.room_analysis_model import build_room_analysis_model
from ..features.scene_contract import (
    AnalysisContext,
    AnalysisDomain,
    AnalysisPlane,
    AuthoredAffordanceZone,
    AuthoredGridAxis,
    AuthoredGroup,
    MaterialFact,
    MeshGeometry3D,
    NEUTRAL_SCENE_V2,
    NeutralSceneV2,
    SourceOpening,
    SourceObject,
    SurfaceFact,
    UncertaintyRecord,
)
from ..features.scene_evaluator import (
    _cad_room_minus_blocker_component_touch_evidence,
    _line_of_sight_entry_region_evidence,
    evaluate_scene,
)
from ..features.scene_inference import (
    _subject_interface_relation,
    affordance_zones,
    furniture_affordance_extents,
    furniture_groups,
    infer_scene_evidence,
    inferred_region_candidates,
    spatial_networks,
)
from ..features.neutral_scene_views import (
    analysis_scene_view, _analysis_scene_view_with_semantic_enclosure,
    _analysis_scene_view_with_domain_handoff,
)
from .fixtures.ifc4_description_fixture import write_ifc4_description_fixture
from .test_geometry_substitutes import _box_mesh


def _mesh(mesh_id: str, rect: Rect, z: float = 0.0) -> MeshGeometry3D:
    """Build one deterministic rectangular mesh for the neutral fixture."""
    points = (
        (rect.left, rect.top, z),
        (rect.right, rect.top, z),
        (rect.right, rect.bottom, z),
        (rect.left, rect.bottom, z),
    )
    return MeshGeometry3D(
        id=mesh_id,
        vertices=points,
        triangle_indices=((0, 1, 2), (0, 2, 3)),
        normals=((0.0, 0.0, 1.0),) * 4,
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"method": "synthetic_neutral_fixture"},
        source_representation_id=None,
        tessellation_settings={},
        units="m",
    )


def _neutral_scene() -> NeutralSceneV2:
    """Create an adapter-independent scene with furniture, affordance, and grid facts."""
    left_rect = Rect(cx=30.0, cy=50.0, width=30.0, height=10.0)
    right_rect = Rect(cx=90.0, cy=50.0, width=30.0, height=10.0)
    zone_rect = Rect(cx=30.0, cy=65.0, width=30.0, height=20.0)
    meshes = (
        _mesh("mesh_left", left_rect),
        _mesh("mesh_right", right_rect),
        _mesh("mesh_zone", zone_rect),
        _mesh("mesh_slab", Rect(cx=60.0, cy=50.0, width=120.0, height=100.0)),
        _mesh("mesh_wall", Rect(cx=60.0, cy=50.0, width=4.0, height=20.0)),
    )
    objects = (
        SourceObject(
            id="left_table",
            source_role="furniture",
            geometry_refs=("mesh_left",),
            group_refs=("group_left",),
            authored_local_frame={"orientation_degrees": 0.0},
            factual_properties={"region": "left", "group": "left"},
        ),
        SourceObject(
            id="right_table",
            source_role="furniture",
            geometry_refs=("mesh_right",),
            group_refs=("group_right",),
            authored_local_frame={"orientation_degrees": 0.0},
            factual_properties={"region": "right", "group": "right"},
        ),
        SourceObject(
            id="floor_slab",
            source_id="source-floor-slab",
            source_role="slab",
            geometry_refs=("mesh_slab",),
        ),
        SourceObject(
            id="north_wall",
            source_role="wall",
            geometry_refs=("mesh_wall",),
            factual_properties={
                "weights": {
                    "walk_block": 1.0,
                    "see_block": 1.0,
                    "grouping_strength": 1.0,
                }
            },
        ),
    )
    context = AnalysisContext(
        contract_version=NEUTRAL_SCENE_V2,
        source_schema="synthetic",
        adapter_version="test-neutral-scene/1.0",
        source_length_unit="m",
        analysis_length_unit="m",
        world_coordinate_system={"method": "test"},
        level_references=(),
        analysis_plane=AnalysisPlane(
            name="test-plan",
            origin=(0.0, 0.0, 0.0),
            basis=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ),
        geometry_tolerance=1e-6,
        topology_tolerance=1e-6,
        walking_body_profiles=({"required_path_width": 10.0},),
        visual_height_bands=(),
        capability_flags={"planar_geometry": True},
        input_mode="ifc",
        subject_interface_all_pairs=True,
    )
    return NeutralSceneV2(
        context=context,
        analysis_domain=AnalysisDomain(
            id="domain_room",
            geometry_refs=("mesh_slab",),
            source_id="source-floor-slab",
            selection_method="test_fixture",
        ),
        source_objects=objects,
        geometries=meshes,
        authored_groups=(
            AuthoredGroup(
                id="group_left",
                source_id=None,
                member_refs=("left_table",),
                group_role="furniture_group",
            ),
            AuthoredGroup(
                id="group_right",
                source_id=None,
                member_refs=("right_table",),
                group_role="furniture_group",
            ),
        ),
        authored_grid_axes=(
            AuthoredGridAxis(
                id="grid_x0",
                source_id=None,
                curve_points=((0.0, 0.0, 0.0), (120.0, 0.0, 0.0)),
                branch_identifier="main",
                list_identifier="x",
            ),
            AuthoredGridAxis(
                id="grid_x1",
                source_id=None,
                curve_points=((0.0, 100.0, 0.0), (120.0, 100.0, 0.0)),
                branch_identifier="main",
                list_identifier="x",
            ),
            AuthoredGridAxis(
                id="grid_y0",
                source_id=None,
                curve_points=((0.0, 0.0, 0.0), (0.0, 100.0, 0.0)),
                branch_identifier="main",
                list_identifier="y",
            ),
            AuthoredGridAxis(
                id="grid_y1",
                source_id=None,
                curve_points=((120.0, 0.0, 0.0), (120.0, 100.0, 0.0)),
                branch_identifier="main",
                list_identifier="y",
            ),
        ),
        authored_affordances=(
            AuthoredAffordanceZone(
                id="zone_left_table",
                geometry_refs=("mesh_zone",),
                vertical_extent=(0.0, 1.0),
                purpose="sit",
                task_facts={},
                source_furniture_refs=("left_table",),
            ),
        ),
    )


def _closed_channel_scene(
    sources: tuple[SourceObject, ...],
    meshes: tuple[MeshGeometry3D, ...],
    *,
    materials: tuple[MaterialFact, ...] = (),
) -> NeutralSceneV2:
    """Build a minimal Neutral Scene with explicit body and visual queries."""
    base = _neutral_scene()
    context = replace(
        base.context,
        walking_body_profiles=(
            {
                "id": "adult",
                "height_band": (0.0, 1.8),
                "radius": 0.3,
                "required_path_width": 0.6,
            },
        ),
        visual_height_bands=(
            {"id": "standing-eye", "height_band": (1.5, 1.8)},
        ),
        capability_flags={
            "planar_geometry": True,
            "height_queries": True,
            "closed_solid_geometry": True,
            "optical_queries": bool(materials),
        },
    )
    slab = next(geometry for geometry in base.geometries if geometry.id == "mesh_slab")
    return replace(
        base,
        context=context,
        source_objects=sources,
        geometries=(slab, *meshes),
        materials=materials,
        authored_groups=(),
        authored_affordances=(),
    )


def _blocked_domain_identity_scene(
    *,
    shell_source_id: str,
    shell_role: str,
    shell_geometry_refs: tuple[str, ...],
    domain_geometry_refs: tuple[str, ...],
    duplicate_shell_source_id: bool = False,
) -> NeutralSceneV2:
    """Build a valid domain fixture with retained wall and column mass."""
    support = _box_mesh(mesh_id="identity_support", top=0.2)
    missing_shell_geometry = (
        ()
        if shell_geometry_refs
        else (
            UncertaintyRecord(
                code="missing_geometry",
                message="fixture source geometry is intentionally unavailable",
                source_refs=(shell_source_id,),
                operation="test_fixture",
                severity="warning",
            ),
        )
    )
    sources = [
        SourceObject(
            id="domain_shell",
            source_id=shell_source_id,
            source_role=shell_role,
            geometry_refs=shell_geometry_refs,
            uncertainties=missing_shell_geometry,
        ),
        SourceObject(
            id="retained_wall",
            source_id="source-retained-wall",
            source_role="wall",
            geometry_refs=(support.id,),
        ),
        SourceObject(
            id="retained_column",
            source_id="source-retained-column",
            source_role="column",
            geometry_refs=(support.id,),
        ),
    ]
    if duplicate_shell_source_id:
        # Empty geometry is valid; identity matching must count source facts, not only projections.
        sources.append(
            SourceObject(
                id="duplicate_domain_shell",
                source_id=shell_source_id,
                source_role="slab",
                geometry_refs=(),
                uncertainties=(
                    UncertaintyRecord(
                        code="missing_geometry",
                        message="fixture duplicate has no projected geometry",
                        source_refs=(shell_source_id,),
                        operation="test_fixture",
                        severity="warning",
                    ),
                ),
            )
        )
    scene = _closed_channel_scene(tuple(sources), (support,))
    return replace(
        scene,
        analysis_domain=replace(
            scene.analysis_domain,
            source_id="source-domain-shell",
            geometry_refs=domain_geometry_refs,
        ),
    )


def _placed_box(
    mesh_id: str,
    *,
    left: float,
    top: float,
    height: float,
) -> MeshGeometry3D:
    """Translate the shared closed-box fixture into one room location."""
    mesh = _box_mesh(mesh_id=mesh_id, top=height)
    return replace(
        mesh,
        vertices=tuple((x + left, y + top, z) for x, y, z in mesh.vertices),
    )


def test_body_band_requires_positive_vertical_overlap_beyond_support_plane():
    """A supporting slab that only touches the body band must remain clear."""
    support = _box_mesh(mesh_id="support_slab", top=0.2)
    support = replace(
        support,
        vertices=tuple((x, y, z - 0.2) for x, y, z in support.vertices),
    )
    raised = _box_mesh(mesh_id="raised_slab", top=0.2)
    scene = _closed_channel_scene(
        (
            SourceObject(
                id="support_slab",
                source_role="slab",
                geometry_refs=(support.id,),
            ),
            SourceObject(
                id="raised_slab",
                source_role="slab",
                geometry_refs=(raised.id,),
            ),
        ),
        (support, raised),
    )

    view = analysis_scene_view(scene)

    assert view["channel_evidence"]["support_slab"]["walking"][0]["status"] == "clear"
    assert view["channel_evidence"]["raised_slab"]["walking"][0]["status"] == "blocked"
    assert [record["id"] for record in view["walk_blockers"]] == ["raised_slab"]


def test_analysis_domain_support_mass_is_not_a_walking_blocker_when_overlapping_body_band():
    """The selected analysis-domain support remains physical evidence, not an obstacle."""
    support = _box_mesh(mesh_id="analysis_support", top=0.2)
    support = replace(
        support,
        vertices=tuple((x, y, z - 0.1) for x, y, z in support.vertices),
    )
    scene = _closed_channel_scene(
        (
            SourceObject(
                id="analysis_support",
                source_id="source-analysis-support",
                source_role="slab",
                geometry_refs=(support.id,),
            ),
            SourceObject(
                id="wall_shared_geometry",
                source_id="source-wall",
                source_role="wall",
                geometry_refs=(support.id,),
            ),
            SourceObject(
                id="column_shared_geometry",
                source_id="source-column",
                source_role="column",
                geometry_refs=(support.id,),
            ),
        ),
        (support,),
    )
    scene = replace(
        scene,
        analysis_domain=replace(
            scene.analysis_domain,
            source_id="source-analysis-support",
            geometry_refs=(support.id,),
        ),
    )

    view = analysis_scene_view(scene)

    assert view["channel_evidence"]["analysis_support"]["walking"][0]["status"] == "blocked"
    assert [record["id"] for record in view["walk_blockers"]] == [
        "wall_shared_geometry",
        "column_shared_geometry",
    ]
    assert [record["id"] for record in view["physical_occupancy"]] == [
        "wall_shared_geometry",
        "column_shared_geometry",
    ]
    diagnostics = view["_analysis_view"].get("b2_boundary_diagnostics")
    assert diagnostics is not None
    assert diagnostics["domain_scope"]["shell_record_ids"] == ["analysis_support"]
    assert diagnostics["domain_scope"]["shell_identity"] == "established"
    assert [item["source_id"] for item in diagnostics["boundary_support"]] == [
        "source-wall",
        "source-column",
    ]


def test_unidentified_analysis_domain_keeps_shared_wall_and_column_occupancy():
    """Geometry overlap cannot identify a shell or suppress wall and column mass."""
    support = _box_mesh(mesh_id="unidentified_analysis_support", top=0.2)
    scene = _closed_channel_scene(
        (
            SourceObject(
                id="unidentified_support",
                source_id=None,
                source_role="slab",
                geometry_refs=(support.id,),
            ),
            SourceObject(
                id="unidentified_wall",
                source_id=None,
                source_role="wall",
                geometry_refs=(support.id,),
            ),
            SourceObject(
                id="unidentified_column",
                source_id=None,
                source_role="column",
                geometry_refs=(support.id,),
            ),
        ),
        (support,),
    )
    scene = replace(
        scene,
        analysis_domain=replace(
            scene.analysis_domain,
            source_id=None,
            geometry_refs=(support.id,),
        ),
    )

    view = analysis_scene_view(scene)
    diagnostics = view["_analysis_view"].get("b2_boundary_diagnostics")
    assert diagnostics is not None

    assert diagnostics["domain_scope"]["availability"] == "available"
    assert diagnostics["domain_scope"]["source"] == "explicit_authored"
    assert diagnostics["domain_scope"]["shell_identity"] == "blocked"
    assert diagnostics["domain_scope"]["blocker"] == "analysis_domain_source_id_missing"
    assert diagnostics["domain_scope"]["shell_record_ids"] == []
    assert [record["id"] for record in view["physical_occupancy"]] == [
        "unidentified_support",
        "unidentified_wall",
        "unidentified_column",
    ]
    assert all(item["source_id"] is None for item in diagnostics["physical_occupancy"])
    assert [item["source_id"] for item in diagnostics["boundary_support"]] == [None, None]
    assert [item["candidate_segment_ids"] for item in diagnostics["boundary_support"]] == [
        [],
        [],
    ]
    assert diagnostics["candidate_promotion"]["status"] == "refused"


@pytest.mark.parametrize(
    (
        "shell_source_id",
        "shell_role",
        "shell_geometry_refs",
        "domain_geometry_refs",
        "duplicate_shell_source_id",
        "expected_blocker",
    ),
    (
        pytest.param(
            "source-domain-shell",
            "slab",
            ("identity_support",),
            ("identity_support",),
            True,
            "analysis_domain_source_id_ambiguous",
            id="duplicate-source-id",
        ),
        pytest.param(
            "unmatched-shell-source",
            "slab",
            ("identity_support",),
            ("identity_support",),
            False,
            "analysis_domain_source_id_unmatched",
            id="unmatched-source-id",
        ),
        pytest.param(
            "source-domain-shell",
            "wall",
            ("identity_support",),
            ("identity_support",),
            False,
            "analysis_domain_source_role_ineligible",
            id="wall-role",
        ),
        pytest.param(
            "source-domain-shell",
            "boundary",
            ("identity_support",),
            ("identity_support",),
            False,
            "analysis_domain_source_role_ineligible",
            id="boundary-role",
        ),
        pytest.param(
            "source-domain-shell",
            "column",
            ("identity_support",),
            ("identity_support",),
            False,
            "analysis_domain_source_role_ineligible",
            id="column-role",
        ),
        pytest.param(
            "source-domain-shell",
            "slab",
            ("identity_support",),
            (),
            False,
            "analysis_domain_geometry_unavailable",
            id="empty-domain-geometry-refs",
        ),
        pytest.param(
            "source-domain-shell",
            "slab",
            (),
            ("identity_support",),
            False,
            "analysis_domain_source_record_unavailable",
            id="matched-source-without-projected-record",
        ),
    ),
)
def test_blocked_domain_shell_identity_keeps_wall_and_column_occupancy(
    shell_source_id: str,
    shell_role: str,
    shell_geometry_refs: tuple[str, ...],
    domain_geometry_refs: tuple[str, ...],
    duplicate_shell_source_id: bool,
    expected_blocker: str,
):
    """Blocked shell identity never removes shared-geometry walls or columns."""
    scene = _blocked_domain_identity_scene(
        shell_source_id=shell_source_id,
        shell_role=shell_role,
        shell_geometry_refs=shell_geometry_refs,
        domain_geometry_refs=domain_geometry_refs,
        duplicate_shell_source_id=duplicate_shell_source_id,
    )

    view = analysis_scene_view(scene)
    diagnostics = view["_analysis_view"]["b2_boundary_diagnostics"]
    expected_retained = {"retained_wall", "retained_column"}

    assert diagnostics["domain_scope"]["shell_record_ids"] == []
    assert diagnostics["domain_scope"]["shell_identity"] == "blocked"
    assert diagnostics["domain_scope"]["blocker"] == expected_blocker
    assert expected_retained <= {
        record["id"] for record in view["physical_occupancy"]
    }
    assert expected_retained <= {record["id"] for record in view["walk_blockers"]}
    if shell_geometry_refs:
        assert "domain_shell" in {
            record["id"] for record in view["physical_occupancy"]
        }


def _opening_uncertainty(
    code: str,
    source_refs: tuple[str, ...],
    *,
    details: dict[str, object] | None = None,
) -> UncertaintyRecord:
    """Create one concise uncertainty fact for B2 opening-state fixtures."""
    return UncertaintyRecord(
        code=code,
        message=f"fixture uncertainty: {code}",
        source_refs=source_refs,
        operation="test_fixture",
        severity="warning",
        details=details or {},
    )


@pytest.mark.parametrize(
    ("host_refs", "geometry_refs", "codes", "expected_state"),
    (
        (("wall",), ("opening-mesh",), ("host_conflict", "host_unsupported", "host_invalid"), "conflict"),
        (("wall",), (), ("host_unsupported", "missing_geometry"), "unsupported"),
        (("wall",), (), ("host_invalid", "missing_geometry"), "invalid"),
        (("wall",), (), ("missing_geometry",), "partial"),
        ((), (), ("missing_geometry",), "not_available"),
        (("wall",), ("opening-mesh",), (), "diagnostic_only"),
    ),
)
def test_b2_opening_diagnostic_preserves_state_precedence_and_nullable_source_id(
    host_refs: tuple[str, ...],
    geometry_refs: tuple[str, ...],
    codes: tuple[str, ...],
    expected_state: str,
):
    """Opening state follows local precedence and never fabricates source identity."""
    opening = SourceOpening(
        id="opening-under-review",
        source_id=None,
        host_refs=host_refs,
        geometry_refs=geometry_refs,
        opening_kind="boundary_opening",
        uncertainties=tuple(
            _opening_uncertainty(code, ("opening-under-review",))
            for code in codes
        ),
    )
    view = analysis_scene_view(replace(_neutral_scene(), openings=(opening,)))
    diagnostics = view["_analysis_view"].get("b2_boundary_diagnostics")
    assert diagnostics is not None
    diagnostic = diagnostics["openings"][0]

    assert diagnostic["local_diagnostic_state"] == expected_state
    assert diagnostic["source_id"] is None
    assert {"opening-under-review", *host_refs, *geometry_refs}.issubset(
        diagnostic["source_refs"]
    )
    assert diagnostic["subtraction_performed"] is False
    if not geometry_refs:
        assert "opening-under-review" not in {
            item["id"] for item in view["entries"]
        }


def test_b2_opening_joins_only_exact_scene_uncertainty_and_keeps_omitted_host():
    """Opening diagnostics join host omissions only through exact uncertainty refs."""
    opening = SourceOpening(
        id="opening-exact-ref",
        source_id=None,
        host_refs=("wall",),
        geometry_refs=("opening-mesh",),
        opening_kind="boundary_opening",
    )
    matching = _opening_uncertainty(
        "unresolved_opening_host_ref",
        (opening.id,),
        details={"omitted_refs": ("missing-wall",)},
    )
    unrelated = _opening_uncertainty(
        "opening_conflict",
        ("another-opening",),
    )
    view = analysis_scene_view(
        replace(
            _neutral_scene(),
            openings=(opening,),
            uncertainties=(matching, unrelated),
        )
    )
    diagnostics = view["_analysis_view"].get("b2_boundary_diagnostics")
    assert diagnostics is not None
    diagnostic = diagnostics["openings"][0]

    assert diagnostic["local_diagnostic_state"] == "partial"
    assert diagnostic["omitted_host_refs"] == ["missing-wall"]
    assert [item["code"] for item in diagnostic["uncertainties"]] == [
        "unresolved_opening_host_ref"
    ]
    assert {"opening-exact-ref", "wall", "opening-mesh", "missing-wall"}.issubset(
        diagnostic["source_refs"]
    )
    assert diagnostic["subtraction_performed"] is False


def test_b2_diagnostics_are_invariant_to_context_tolerance_values():
    """Local B2 provenance does not consume unrelated geometry tolerances."""
    scene = _neutral_scene()
    changed_tolerance_scene = replace(
        scene,
        context=replace(
            scene.context,
            geometry_tolerance=0.25,
            topology_tolerance=0.75,
        ),
    )

    first = analysis_scene_view(scene)["_analysis_view"].get("b2_boundary_diagnostics")
    second = analysis_scene_view(changed_tolerance_scene)["_analysis_view"].get("b2_boundary_diagnostics")

    assert first is not None
    assert second is not None
    assert first == second
    assert first["candidate_polygon_validity"]["status"] == "not_available"
    assert first["source_components"]["status"] == "not_available"
    assert first["downstream"]["subtraction"] == "refused"
    assert first["downstream"]["free_space"] == "not_evaluated"
    assert first["downstream"]["route"] == "not_evaluated"


def test_neutral_role_neutral_mass_enters_physical_occupancy():
    """Physical occupancy must include mass geometry even when its role is not wall-like."""
    partition = _box_mesh(mesh_id="role_neutral_partition", top=1.2)
    scene = _closed_channel_scene(
        (
            SourceObject(
                id="role_neutral_partition",
                source_role="partition",
                geometry_refs=(partition.id,),
            ),
        ),
        (partition,),
    )

    view = analysis_scene_view(scene)

    assert "role_neutral_partition" in {
        record["id"] for record in view["physical_occupancy"]
    }


def test_neutral_scene_drives_inference_without_svg_parser():
    """Neutral Scene facts should produce furniture, regions, and a gap path."""
    evidence = infer_scene_evidence(_neutral_scene())

    assert {item["object_id"] for item in evidence["furniture_affordance_extents"]} == {
        "left_table",
        "right_table",
    }
    assert evidence["furniture_affordance_extents"][0]["object_id"] == "left_table"
    assert len(evidence["furniture_groups"]) == 2
    assert {item["region"] for item in evidence["inferred_regions"]} == {"left", "right"}
    assert evidence["inferred_region_gap_paths"]
    assert all("weights" not in item for item in evidence["inferred_region_candidates"])
    assert all("weights" not in item for item in evidence["inferred_regions"])


def test_neutral_boundary_fact_expands_the_matching_inferred_region():
    """Weight-free Neutral boundary geometry must participate in region construction."""
    boundary_mesh = _mesh(
        "mesh_left_boundary_cue",
        Rect(cx=50.0, cy=50.0, width=10.0, height=20.0),
    )
    boundary = SourceObject(
        id="left_boundary_cue",
        source_role="wall",
        geometry_refs=(boundary_mesh.id,),
        factual_properties={"region": "left"},
    )
    scene = replace(
        _neutral_scene(),
        source_objects=_neutral_scene().source_objects + (boundary,),
        geometries=_neutral_scene().geometries + (boundary_mesh,),
    )

    candidate = next(
        item
        for item in inferred_region_candidates(scene)
        if item["region"] == "left"
    )

    assert "left_boundary_cue" in candidate["metadata"]["boundary_cue_ids"]
    assert candidate["rect"].right >= 55.0


def test_neutral_boundary_semantics_consumes_weight_free_boundary_facts():
    """Neutral boundaries should expose four factual channels without legacy weights."""
    semantics = infer_scene_evidence(_neutral_scene())["boundary_semantics"]

    by_id = {record["id"]: record for record in semantics}
    assert {"left_table", "right_table", "north_wall"} <= set(by_id)
    assert "floor_slab" not in by_id
    wall = by_id["north_wall"]
    assert wall["physical_continuity"][0]["channel_geometry_status"] == "unknown"
    assert wall["walking_permeability"] == []
    assert wall["walking_permeability_status"] == "unknown"
    assert wall["visual_permeability"] == []
    assert wall["visual_permeability_status"] == "unknown"
    assert wall["gestalt_continuity"][0]["alignment"] == "not_evaluated"
    assert {
        "weights",
        "walk_passable",
        "see_passable",
        "grouping_strength",
    }.isdisjoint(wall)


def test_neutral_interfaces_include_furniture_mass_and_surface_facts():
    """Interface evidence must follow mass and surface facts rather than roles."""
    cabinet_mesh = _placed_box(
        "mesh_low_cabinet_interface",
        left=50.0,
        top=49.0,
        height=1.0,
    )
    cabinet = SourceObject(
        id="low_cabinet_interface",
        source_role="cabinet",
        geometry_refs=(cabinet_mesh.id,),
    )
    scene = _closed_channel_scene((cabinet,), (cabinet_mesh,))
    scene = replace(
        scene,
        surfaces=(
            SurfaceFact(
                id="carpet_cue",
                source_id=None,
                host_refs=(),
                identity="carpet",
                color="#aa0000",
                finish=None,
                texture=None,
                elevation={"constant": 0.0},
                slope=None,
                geometry_refs=("mesh_slab",),
            ),
        ),
    )

    inference = infer_scene_evidence(scene)
    semantics = {
        record["id"]: record
        for record in inference["boundary_semantics"]
    }

    cabinet_interface = semantics["low_cabinet_interface"]
    assert cabinet_interface["kind"] == "cabinet"
    assert cabinet_interface["physical_continuity"][0]["mass_present"] is True
    assert cabinet_interface["walking_permeability"][0]["status"] == "blocked"
    assert cabinet_interface["visual_permeability"][0]["status"] == "clear"
    surface_interface = semantics["surface:carpet_cue"]
    assert surface_interface["physical_continuity"][0]["mass_present"] is False
    assert surface_interface["walking_permeability"][0]["status"] == "clear"
    assert surface_interface["visual_permeability"][0]["status"] == "clear"
    assert surface_interface["gestalt_continuity"][0]["surface_identity"] == (
        "carpet_cue"
    )
    surface_relation = next(
        record
        for record in inference["subject_interface_relations"]
        if record["interface_id"] == "surface:carpet_cue"
    )
    assert surface_relation["interface_kind"] == "surface"
    assert surface_relation["physical_continuity"][0]["mass_present"] is False


def test_neutral_subject_interface_relations_are_weight_free_descriptions():
    """Regions should receive factual interface relations without aggregate scores."""
    table_mesh = _placed_box(
        "mesh_relation_table", left=20.0, top=20.0, height=0.75
    )
    cabinet_mesh = _placed_box(
        "mesh_relation_cabinet", left=30.0, top=20.0, height=1.0
    )
    scene = _closed_channel_scene(
        (
            SourceObject(
                id="relation_table",
                source_role="furniture",
                geometry_refs=(table_mesh.id,),
            ),
            SourceObject(
                id="relation_cabinet",
                source_role="cabinet",
                geometry_refs=(cabinet_mesh.id,),
            ),
        ),
        (table_mesh, cabinet_mesh),
    )

    inference = infer_scene_evidence(scene)
    relation = next(
        record
        for record in inference["subject_interface_relations"]
        if record["subject_id"] == "inferred_region_relation_table"
        and record["interface_id"] == "relation_cabinet"
    )

    assert relation["status"] == "evaluated"
    assert relation["distance"] is not None
    assert len(relation["nearest_side"]) == 2
    assert relation["frame_relation"]["status"] == "computed"
    assert relation["frame_relation"]["angle_delta_degrees"] is not None
    assert relation["subject_coverage_ratio"] is not None
    assert relation["interface_coverage_ratio"] is not None
    assert relation["containment"]["status"] == "computed"
    assert isinstance(relation["containment"]["subject_within_interface"], bool)
    assert isinstance(relation["containment"]["interface_within_subject"], bool)
    assert relation["opening_ids"] == []
    assert relation["permeability"]["walking"][0]["status"] == "blocked"
    assert relation["permeability"]["visual"][0]["status"] == "clear"
    assert "score" not in relation
    assert "weights" not in relation
    assert not any(
        item["subject_id"] == "inferred_region_relation_table"
        and item["interface_id"] == "relation_table"
        for item in inference["subject_interface_relations"]
    )
    assert not any(
        pair_id.endswith("__relation_table")
        for pair_id in inference["subject_interface_relation_scope"][
            "not_evaluated_pair_ids"
        ]
    )

    matrix = evaluate_scene(scene)
    relation_row = next(
        row
        for row in matrix["rows"]
        if row["metric"] == "subject_interface_relation_count"
    )
    assert relation_row["status"] == "computed"
    assert relation_row["subject_interface_relations"] == matrix[
        "subject_interface_relations"
    ]
    assert matrix["room_analysis_model"]["reference_layer"][
        "subject_interface_relations"
    ] == matrix["subject_interface_relations"]


def test_neutral_support_mass_is_not_an_external_interface_but_surface_cue_survives():
    """Domain support mass is common context while explicit surface cues remain local."""
    scene = _neutral_scene()
    scene = replace(
        scene,
        surfaces=(
            SurfaceFact(
                id="support_carpet",
                source_id=None,
                host_refs=("floor_slab",),
                identity="carpet",
                color="#aa0000",
                finish=None,
                texture=None,
                elevation={"constant": 0.0},
                slope=None,
                geometry_refs=("mesh_slab",),
            ),
        ),
    )

    inference = infer_scene_evidence(scene)

    assert "floor_slab" not in {
        record["interface_id"]
        for record in inference["subject_interface_relations"]
    }
    assert "floor_slab" not in {
        record["id"] for record in inference["boundary_semantics"]
    }
    assert "surface:support_carpet" in {
        record["id"] for record in inference["boundary_semantics"]
    }


def test_subject_interface_relation_uses_exact_holes_and_parallel_coverage():
    """A subject inside an interface hole is not covered by its outer bounds."""
    relation = _subject_interface_relation(
        {
            "id": "region_hole_subject",
            "rect": Rect(cx=10.0, cy=10.0, width=4.0, height=4.0),
            "points": ((8.0, 8.0), (12.0, 8.0), (12.0, 12.0), (8.0, 12.0)),
            "metadata": {"axis-angle": "0"},
        },
        {
            "id": "donut_interface",
            "rect": Rect(cx=10.0, cy=10.0, width=20.0, height=20.0),
            "geometry_components": (
                {
                    "exterior": ((0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)),
                    "holes": (((8.0, 8.0), (12.0, 8.0), (12.0, 12.0), (8.0, 12.0)),),
                },
            ),
            "metadata": {"orientation": "0"},
        },
        {"interface_kind": "mass", "opening_ids": []},
    )

    assert relation["subject_coverage_ratio"] == 0.0
    assert relation["interface_coverage_ratio"] == 0.0
    assert relation["containment"]["subject_within_interface"] is False
    assert relation["parallel_coverage"]["status"] == "computed"
    assert relation["parallel_coverage"]["ratio"] == 0.0


def test_adjacent_aligned_interface_has_parallel_coverage_without_area_overlap():
    """A shared aligned boundary is continuous evidence even with zero area overlap."""
    relation = _subject_interface_relation(
        {
            "id": "region_adjacent_subject",
            "points": ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
            "metadata": {"axis-angle": "90"},
        },
        {
            "id": "adjacent_wall",
            "geometry_components": (
                {
                    "exterior": ((10.0, 0.0), (12.0, 0.0), (12.0, 10.0), (10.0, 10.0)),
                    "holes": (),
                },
            ),
            "metadata": {"orientation": "90"},
        },
        {"interface_kind": "mass", "opening_ids": []},
    )

    assert relation["subject_coverage_ratio"] == 0.0
    assert relation["parallel_coverage"]["status"] == "computed"
    assert relation["parallel_coverage"]["ratio"] > 0.0


def test_subject_interface_relations_require_an_explicit_range_contract():
    """Missing range configuration must not silently evaluate every pair."""
    scene = _neutral_scene()
    scene = replace(
        scene,
        context=replace(
            scene.context,
            subject_interface_max_distance=None,
            subject_interface_all_pairs=False,
        ),
    )

    evidence = infer_scene_evidence(scene)

    assert evidence["subject_interface_relations"] == []
    assert evidence["subject_interface_relation_scope"] == {
        "status": "not_available",
        "method": "explicit_subject_interface_range_contract",
        "max_distance": None,
        "all_pairs": False,
        "candidate_pair_count": 0,
        "relation_count": 0,
        "not_evaluated_pair_ids": [],
        "uncertainty": "missing_subject_interface_range",
    }
    matrix = evaluate_scene(scene)
    assert matrix["subject_interface_relation_scope"] == evidence[
        "subject_interface_relation_scope"
    ]
    assert matrix["room_analysis_model"]["reference_layer"][
        "subject_interface_relation_scope"
    ] == evidence["subject_interface_relation_scope"]
    row = next(
        row
        for row in matrix["rows"]
        if row["metric"] == "subject_interface_relation_count"
    )
    assert row["score"] is None
    assert row["status"] == "not_available"
    assert row["uncertainty"] == "missing_subject_interface_range"


def test_neutral_legacy_boundary_weight_rows_are_unavailable_not_zero():
    """Neutral output must not turn absent authored weights into zero scores."""
    rows = {
        row["metric"]: row
        for row in evaluate_scene(_neutral_scene())["rows"]
    }
    legacy_weight_metrics = {
        "region_source_boundary_weighted_axis_agreement",
        "region_source_boundary_proximity",
        "closed_blocking_boundary_ratio",
        "boundary_weight_metadata_coverage",
        "walk_block_mean",
        "see_block_mean",
        "grouping_strength_mean",
        "walk_see_block_gap_mean",
        "non_blocking_grouping_cue_mean",
    }

    for metric in legacy_weight_metrics:
        assert rows[metric]["score"] is None
        assert rows[metric]["status"] == "not_available"
        assert rows[metric]["method"] == "not_available_without_legacy_boundary_weights"


def test_neutral_public_description_surfaces_are_weight_free_recursively():
    """Neutral public descriptions must not expose authored aggregate weights."""
    matrix = evaluate_scene(_neutral_scene())
    surfaces = (
        matrix["inferred_region_candidates"],
        matrix["inferred_regions"],
        matrix["room_analysis_model"]["region_layer"],
        matrix["room_analysis_model"]["reference_layer"],
        matrix["adapter_payload"],
    )
    forbidden = {
        "weights",
        "walk_block",
        "see_block",
        "grouping_strength",
        "boundary_strength",
        "walk-block",
        "see-block",
        "grouping-strength",
        "boundary-strength",
    }

    def walk(value):
        """Yield mapping keys and nested values for one public record tree."""
        if isinstance(value, dict):
            for key, nested in value.items():
                yield key
                yield from walk(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                yield from walk(nested)

    assert not forbidden.intersection(
        key for surface in surfaces for key in walk(surface)
    )


def test_neutral_scene_drives_evaluator_and_column_grid():
    """The evaluator should expose trend evidence and authored grid relations."""
    matrix = evaluate_scene(_neutral_scene())

    assert matrix["column_grid"]["status"] == "computed"
    assert matrix["column_grid"]["local_profiles"]
    assert matrix["column_grid"]["global_relations"]
    assert matrix["inferred_regions"]
    trend = matrix["inferred_regions"][0]["metadata"]
    assert float(trend["axis-trend-strength"]) > 0.0
    assert float(trend["secondary-axis-angle"]) == 90.0
    assert matrix["room_analysis_model"]["reference_layer"]["column_axes"]


def test_shared_networks_preserve_internal_and_isolated_region_components():
    """Network components should follow edges and retain isolated activity regions."""
    groups = [
        {
            "id": "group_a",
            "activity_region_id": "region_a",
            "furniture_affordance_extent_ids": ["extent_a1", "extent_a2", "extent_a3"],
            "overlap_evidence": [
                {"a": "extent_a1", "b": "extent_a2", "overlap_area": 2.0},
                {"a": "extent_a2", "b": "extent_a3", "overlap_area": 0.0},
            ],
        },
        {
            "id": "group_b",
            "activity_region_id": "region_b",
            "furniture_affordance_extent_ids": ["extent_b"],
            "overlap_evidence": [],
        },
        {
            "id": "group_isolated",
            "activity_region_id": "region_isolated",
            "furniture_affordance_extent_ids": ["extent_isolated"],
            "overlap_evidence": [],
        },
    ]
    gap_paths = [
        {
            "id": "gap_a_b",
            "region_a": "inferred_region_region_a",
            "region_b": "inferred_region_region_b",
            "thickness": 1.0,
        }
    ]

    networks = spatial_networks(groups, gap_paths)

    internal_a = next(network for network in networks if network["id"].endswith("region_a"))
    assert internal_a["components"] == [["extent_a1", "extent_a2"], ["extent_a3"]]
    inter_region = next(network for network in networks if network["scope"] == "inter_region")
    assert [node["id"] for node in inter_region["nodes"]] == [
        "inferred_region_region_a",
        "inferred_region_region_b",
        "inferred_region_region_isolated",
    ]
    assert inter_region["components"] == [
        ["inferred_region_region_a", "inferred_region_region_b"],
        ["inferred_region_region_isolated"],
    ]


def test_low_closed_cabinet_blocks_walk_but_not_visual_band():
    """A closed cabinet below eye height should separate walk and visual channels."""
    cabinet_mesh = _placed_box(
        "mesh_low_cabinet",
        left=50.0,
        top=49.0,
        height=1.0,
    )
    cabinet = SourceObject(
        id="low_cabinet",
        source_role="cabinet",
        geometry_refs=(cabinet_mesh.id,),
    )
    scene = _closed_channel_scene((cabinet,), (cabinet_mesh,))

    view = analysis_scene_view(scene)
    evidence = view["channel_evidence"]["low_cabinet"]
    matrix = evaluate_scene(scene)

    assert evidence["walking"][0]["status"] == "blocked"
    assert evidence["visual"][0]["geometry_status"] == "clear"
    assert evidence["visual"][0]["status"] == "clear"
    assert [record["id"] for record in view["walk_blockers"]] == ["low_cabinet"]
    assert view["visibility_blockers"] == []
    assert matrix["sampled_walkable_space"]["walk_status"] == "computed"
    assert matrix["sampled_walkable_space"]["visibility_status"] == "computed"
    assert "low_cabinet" in matrix["negative_space"]["blocker_evidence"]


def test_transparent_partition_keeps_obstruction_without_opaque_visual_blocking():
    """Visible transmittance should separate geometry obstruction from opacity."""
    glass_mesh = _placed_box(
        "mesh_glass_partition",
        left=45.0,
        top=49.0,
        height=3.0,
    )
    viewport_mesh = _placed_box(
        "mesh_viewport_partition",
        left=65.0,
        top=49.0,
        height=3.0,
    )
    glass = MaterialFact(
        id="glass_material",
        source_id=None,
        identity="glass",
        visible_transmittance=0.8,
        viewport_transparency=0.0,
    )
    viewport_only = MaterialFact(
        id="viewport_material",
        source_id=None,
        identity="viewport-only",
        visible_transmittance=None,
        viewport_transparency=1.0,
    )
    sources = (
        SourceObject(
            id="glass_partition",
            source_role="wall",
            geometry_refs=(glass_mesh.id,),
            material_refs=(glass.id,),
        ),
        SourceObject(
            id="viewport_partition",
            source_role="wall",
            geometry_refs=(viewport_mesh.id,),
            material_refs=(viewport_only.id,),
        ),
    )
    scene = _closed_channel_scene(
        sources,
        (glass_mesh, viewport_mesh),
        materials=(glass, viewport_only),
    )

    view = analysis_scene_view(scene)
    glass_evidence = view["channel_evidence"]["glass_partition"]
    viewport_evidence = view["channel_evidence"]["viewport_partition"]

    assert glass_evidence["material_refs"] == ["glass_material"]
    assert glass_evidence["visible_transmittance"] == 0.8
    assert glass_evidence["visual"][0]["geometry_status"] == "blocked"
    assert glass_evidence["visual"][0]["status"] == "transmitting"
    assert viewport_evidence["visible_transmittance"] is None
    assert viewport_evidence["visual"][0]["geometry_status"] == "blocked"
    assert viewport_evidence["visual"][0]["status"] == "unknown"
    assert view["visibility_blockers"] == []
    assert view["_analysis_view"]["capability_flags"]["visibility_channel"] is False
    assert evaluate_scene(scene)["sampled_walkable_space"]["visibility_status"] == "not_available"
    assert {record["id"] for record in view["physical_blockers"]} == {
        "glass_partition",
        "viewport_partition",
    }


def test_sofa_visual_blocker_uses_only_high_back_query_projection():
    """A visual band must emit only the local high sofa-back geometry."""
    seat_mesh = _placed_box("mesh_sofa_seat", left=50.0, top=49.0, height=0.45)
    back_mesh = _placed_box("mesh_sofa_back", left=55.0, top=49.0, height=1.8)
    opaque = MaterialFact(
        id="opaque", source_id=None, identity="opaque",
        visible_transmittance=0.0, viewport_transparency=1.0,
    )
    sofa = SourceObject(
        id="sofa", source_role="sofa",
        geometry_refs=(seat_mesh.id, back_mesh.id), material_refs=(opaque.id,),
    )
    scene = _closed_channel_scene(
        (sofa,), (seat_mesh, back_mesh), materials=(opaque,),
    )

    view = analysis_scene_view(scene)
    blocker = view["visibility_blockers"][0]

    assert blocker["id"] == "sofa"
    assert len(blocker["geometry_components"]) == 1
    assert blocker["geometry_components"][0]["exterior"]
    assert min(point[0] for point in blocker["geometry_components"][0]["exterior"]) >= 55.0


def test_ambiguous_material_assignment_keeps_visual_channel_unknown():
    """Unassigned differing material refs cannot manufacture object opacity."""
    mesh = _placed_box("mesh_ambiguous", left=50.0, top=49.0, height=2.0)
    first = MaterialFact(
        id="mat-clear", source_id=None, identity="clear",
        visible_transmittance=0.2, viewport_transparency=0.0,
    )
    second = MaterialFact(
        id="mat-opaque", source_id=None, identity="opaque",
        visible_transmittance=0.0, viewport_transparency=0.0,
    )
    source = SourceObject(
        id="ambiguous-partition", source_role="wall",
        geometry_refs=(mesh.id,), material_refs=(first.id, second.id),
    )
    scene = _closed_channel_scene(
        (source,), (mesh,), materials=(first, second),
    )

    view = analysis_scene_view(scene)

    evidence = view["channel_evidence"][source.id]
    assert evidence["visible_transmittance"] is None
    assert evidence["visual"][0]["status"] == "unknown"
    assert view["_analysis_view"]["capability_flags"]["visibility_channel"] is False


def test_public_analysis_consumers_accept_neutral_scene_directly():
    """Public consumer entrypoints should share the same neutral-view boundary."""
    scene = _neutral_scene()
    matrix = evaluate_scene(scene)

    assert affordance_zones(scene)
    assert furniture_affordance_extents(scene)
    assert furniture_groups(scene)
    assert inferred_region_candidates(scene)
    assert column_grid_evidence(scene)["status"] == "computed"
    model = build_room_analysis_model(scene, matrix)
    assert model["object_layer"]["objects"]
    assert all("weights" not in item for item in model["object_layer"]["objects"])
    assert model["region_layer"]["activity_regions"] == matrix["inferred_regions"]
    assert [item["id"] for item in model["base_layer"]["room"]["boundaries"]] == [
        "north_wall"
    ]
    assert "weights" not in model["base_layer"]["room"]["boundaries"][0]


def test_provenance_source_metadata_remains_audit_only():
    """Provenance metadata must not override factual or authored analysis facts."""
    scene = _neutral_scene()
    left, right, *others = scene.source_objects
    scene = replace(
        scene,
        source_objects=(
            replace(
                left,
                factual_properties={
                    "group": "factual_group",
                    "region": "factual_region",
                    "role": "chair",
                },
                provenance={
                    "source_metadata": {
                        "group": "provenance_group",
                        "region": "provenance_region",
                        "role": "wall",
                        "affordance-left": "99",
                    }
                },
            ),
            replace(
                right,
                factual_properties={},
                provenance={
                    "source_metadata": {
                        "group": "provenance_group",
                        "region": "provenance_region",
                        "role": "wall",
                    }
                },
            ),
            *others,
        ),
    )

    records = {item["id"]: item for item in analysis_scene_view(scene)["objects"]}

    assert records["left_table"]["role"] == "chair"
    assert records["left_table"]["group"] == "factual_group"
    assert records["left_table"]["region"] == "factual_region"
    assert "affordance-left" not in records["left_table"]["metadata"]
    assert records["right_table"]["role"] == "furniture"
    assert records["right_table"]["group"] == "group_right"
    assert records["right_table"]["region"] == "group_right"


def test_weight_free_wall_fact_can_block_an_inferred_gap_path():
    """Physical wall geometry should enter path occupancy without authored weights."""
    matrix = evaluate_scene(_neutral_scene())
    occupancy = next(
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_occupancy_ratio"
    )

    assert any(
        occupier["id"] == "north_wall"
        for evidence in occupancy["inferred_region_gap_path_occupancy_evidence"]
        for occupier in evidence["occupiers"]
    )


def test_open_planar_wall_occupies_space_without_claiming_channels():
    """Planar wall geometry should remain occupancy evidence with unknown channels."""
    matrix = evaluate_scene(_neutral_scene())

    assert "north_wall" in matrix["negative_space"]["blocker_evidence"]
    assert matrix["sampled_walkable_space"]["walk_status"] == "not_available"
    assert matrix["sampled_walkable_space"]["visibility_status"] == "not_available"
    assert matrix["line_of_sight_graph"]["status"] == "not_available"
    assert matrix["line_of_sight_graph"]["edges"] == []


def test_legacy_weighted_boundary_channels_remain_compatible():
    """A plain legacy dict should retain object and weighted-boundary blocking."""
    scene = analysis_scene_view(_neutral_scene())
    legacy_boundary = dict(scene["physical_blockers"][0])
    legacy_boundary["weights"] = {
        "walk_block": 1.0,
        "see_block": 1.0,
        "grouping_strength": 1.0,
    }
    scene["boundaries"] = [legacy_boundary]
    scene.pop("_neutral_scene")
    scene.pop("_analysis_view")

    matrix = evaluate_scene(scene)
    region_pair = next(
        edge
        for edge in matrix["line_of_sight_graph"]["edges"]
        if edge["kind"] == "region_pair_centerline_visibility"
    )

    assert matrix["negative_space"]["blocker_evidence"].count("north_wall") == 1
    assert matrix["sampled_walkable_space"]["blocker_evidence"].count("north_wall") == 1
    assert (
        matrix["sampled_walkable_space"]["visibility_blocker_evidence"].count(
            "north_wall"
        )
        == 1
    )
    assert region_pair["blocking_boundary_ids"] == ["north_wall"]


def test_disconnected_wall_components_and_holes_survive_path_consumers():
    """Path consumers must preserve component gaps and interior projection holes."""
    scene = _neutral_scene()
    hole_path_mesh = _mesh(
        "mesh_hole_path",
        Rect(cx=60.0, cy=20.0, width=5.0, height=5.0),
    )
    hole_path = SourceObject(
        id="hole_path",
        source_role="path",
        geometry_refs=("mesh_hole_path",),
    )
    vertices = (
        (50.0, 10.0, 0.0),
        (70.0, 10.0, 0.0),
        (70.0, 30.0, 0.0),
        (50.0, 30.0, 0.0),
        (55.0, 15.0, 0.0),
        (65.0, 15.0, 0.0),
        (65.0, 25.0, 0.0),
        (55.0, 25.0, 0.0),
        (50.0, 70.0, 0.0),
        (70.0, 70.0, 0.0),
        (70.0, 90.0, 0.0),
        (50.0, 90.0, 0.0),
    )
    split_wall = MeshGeometry3D(
        id="mesh_wall",
        vertices=vertices,
        triangle_indices=(
            (0, 1, 5),
            (0, 5, 4),
            (1, 2, 6),
            (1, 6, 5),
            (2, 3, 7),
            (2, 7, 6),
            (3, 0, 4),
            (3, 4, 7),
            (8, 9, 10),
            (8, 10, 11),
        ),
        normals=((0.0, 0.0, 1.0),) * 12,
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"method": "synthetic_neutral_fixture"},
        source_representation_id=None,
        tessellation_settings={},
        units="m",
    )
    scene = replace(
        scene,
        source_objects=scene.source_objects + (hole_path,),
        geometries=tuple(
            split_wall if geometry.id == "mesh_wall" else geometry
            for geometry in scene.geometries
        )
        + (hole_path_mesh,),
    )

    view = analysis_scene_view(scene)
    wall = view["boundary_facts"][0]
    matrix = evaluate_scene(scene)
    occupancy = next(
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_occupancy_ratio"
    )

    assert len(wall["geometry_components"]) == 2
    assert any(component["holes"] for component in wall["geometry_components"])
    assert all(
        occupier["id"] != "north_wall"
        for evidence in occupancy["inferred_region_gap_path_occupancy_evidence"]
        for occupier in evidence["occupiers"]
    )
    assert matrix["negative_space"]["blocker_overlap_area"] == 1300.0
    assert matrix["sampled_walkable_space"]["walk_status"] == "not_available"
    assert matrix["sampled_walkable_space"]["blocked_cells"] is None
    assert matrix["path_geometry"]["hole_path"]["status"] == "not_available"
    assert matrix["path_geometry"]["hole_path"]["blocker_overlap_area"] is None
    assert matrix["line_of_sight_graph"]["status"] == "not_available"
    rows = {row["metric"]: row for row in matrix["rows"]}
    assert rows["path_min_clearance_to_blocker"]["status"] == "not_available"
    assert rows["sampled_entry_reachable_cell_ratio"]["status"] == "not_available"
    assert rows["line_of_sight_region_pair_ratio"]["status"] == "not_available"


def test_cad_negative_space_touch_ignores_disconnected_region_bbox_gap():
    """CAD free-space touch must use region components rather than their union bbox."""
    cad_polygons = [
        {
            "component_index": 0,
            "outer_ring": ((40.0, 40.0), (60.0, 40.0), (60.0, 60.0), (40.0, 60.0)),
            "holes": (),
        }
    ]
    disconnected_region = {
        "id": "split_region",
        "rect": Rect(cx=50.0, cy=50.0, width=100.0, height=20.0),
        "geometry_components": [
            {
                "exterior": ((0.0, 40.0), (20.0, 40.0), (20.0, 60.0), (0.0, 60.0)),
                "holes": (),
            },
            {
                "exterior": ((80.0, 40.0), (100.0, 40.0), (100.0, 60.0), (80.0, 60.0)),
                "holes": (),
            },
        ],
    }

    evidence = _cad_room_minus_blocker_component_touch_evidence(
        cad_polygons,
        [],
        [disconnected_region],
    )

    assert evidence[0]["region_ids"] == []
    assert evidence[0]["region_overlap_areas"] == {}


def test_entry_bbox_touch_does_not_hide_disconnected_los_intersection():
    """Entry contact at one bbox edge must not hide a farther component hit."""
    entry = {
        "id": "entry",
        "rect": Rect(cx=5.0, cy=50.0, width=10.0, height=10.0),
    }
    region = {
        "id": "region",
        "rect": Rect(cx=80.0, cy=50.0, width=10.0, height=10.0),
    }
    blocker = {
        "id": "split_wall",
        "role": "boundary",
        "rect": Rect(cx=27.5, cy=47.5, width=35.0, height=15.0),
        "geometry_components": [
            {
                "exterior": ((10.0, 40.0), (20.0, 40.0), (20.0, 44.0), (10.0, 44.0)),
                "holes": (),
            },
            {
                "exterior": ((40.0, 45.0), (45.0, 45.0), (45.0, 55.0), (40.0, 55.0)),
                "holes": (),
            },
        ],
        "metadata": {"boundary-kind": "wall"},
        "weights": {
            "walk_block": 1.0,
            "see_block": 1.0,
            "grouping_strength": 1.0,
        },
    }
    scene = {
        "size": (100.0, 100.0),
        "entries": [entry],
        "regions": [region],
        "boundaries": [blocker],
        "physical_blockers": [],
    }

    evidence = _line_of_sight_entry_region_evidence(scene)

    assert evidence[0]["visible"] is False
    assert evidence[0]["blocking_boundary_ids"] == ["split_wall"]
    assert sorted(
        evidence[0]["blocking_boundary_evidence"][0]["intersection_points"]
    ) == [
        (40.0, 50.0),
        (45.0, 50.0),
    ]


def test_missing_furniture_frame_uses_projected_geometry_pca():
    """A missing authored frame should use geometry orientation, not horizontal zero."""
    scene = _neutral_scene()
    angle = radians(30.0)
    base = ((-15.0, -5.0), (15.0, -5.0), (15.0, 5.0), (-15.0, 5.0))
    rotated = tuple(
        (
            30.0 + x * cos(angle) - y * sin(angle),
            40.0 + x * sin(angle) + y * cos(angle),
            0.0,
        )
        for x, y in base
    )
    oblique_mesh = MeshGeometry3D(
        id="mesh_oblique",
        vertices=rotated,
        triangle_indices=((0, 1, 2), (0, 2, 3)),
        normals=((0.0, 0.0, 1.0),) * 4,
        is_manifold=False,
        is_closed=False,
        local_to_world_provenance={"method": "synthetic_neutral_fixture"},
        source_representation_id=None,
        tessellation_settings={},
        units="m",
    )
    oblique = SourceObject(
        id="oblique_table",
        source_role="furniture",
        geometry_refs=("mesh_oblique",),
        factual_properties={"region": "oblique", "group": "oblique"},
    )
    scene = replace(
        scene,
        source_objects=scene.source_objects + (oblique,),
        geometries=scene.geometries + (oblique_mesh,),
    )

    record = next(
        item for item in analysis_scene_view(scene)["objects"] if item["id"] == "oblique_table"
    )
    orientation = float(record["metadata"]["orientation"])
    assert abs(orientation - 30.0) < 1.0


def test_missing_analysis_domain_marks_domain_metrics_unavailable():
    """A fallback canvas must not masquerade as an authored analysis domain."""
    scene = replace(_neutral_scene(), analysis_domain=None)

    matrix = evaluate_scene(scene)
    path_rows = [row for row in matrix["rows"] if row["view_id"] == "path_connectivity"]

    assert matrix["inferred_regions"]
    assert path_rows
    assert all(row["status"] == "not_available" for row in path_rows)
    assert all(row["score"] is None for row in path_rows)
    free_space_overlap = next(
        row
        for row in matrix["rows"]
        if row["metric"] == "inferred_region_gap_path_free_space_overlap_ratio"
    )
    assert free_space_overlap["status"] == "not_available"
    assert free_space_overlap["score"] is None


class _EquivalentIfcSource:
    """Provide normalized IFC facts equivalent to the temporary planar SVG."""

    schema = "IFC4"

    def __init__(self) -> None:
        """Build two rectangular IFC furniture records in analysis units."""
        self.payload = {
            "source_length_unit": "m",
            "objects": (
                self._object("ifc-object:left", 15.0, 45.0, 45.0, 55.0),
                self._object("ifc-object:right", 75.0, 45.0, 105.0, 55.0),
            ),
        }

    @staticmethod
    def _object(
        global_id: str,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> dict:
        """Return one normalized IFC furniture rectangle."""
        return {
            "global_id": global_id,
            "ifc_class": "IfcFurniture",
            "geometry": {
                "vertices": (
                    (left, top, 0.0),
                    (right, top, 0.0),
                    (right, bottom, 0.0),
                    (left, bottom, 0.0),
                ),
                "triangles": ((0, 1, 2), (0, 2, 3)),
            },
        }


def _rect_signature(record: dict) -> tuple[float, float, float, float]:
    """Return one rounded rectangle signature for cross-adapter comparison."""
    rect = record["rect"]
    return tuple(round(value, 6) for value in (rect.cx, rect.cy, rect.width, rect.height))


def _network_signature(network: dict) -> tuple:
    """Normalize one network to source-id-independent topology facts."""
    return (
        network["scope"],
        len(network["nodes"]),
        tuple(sorted(edge["kind"] for edge in network["edges"])),
        tuple(sorted(len(component) for component in network["components"])),
    )


def _equivalent_authored_axes() -> tuple[AuthoredGridAxis, ...]:
    """Provide identical explicit axes for the two adapter-equivalence fixtures."""
    return (
        AuthoredGridAxis(
            id="grid:x0",
            source_id="grid:equivalent",
            curve_points=((0.0, 0.0, 0.0), (120.0, 0.0, 0.0)),
            branch_identifier="main",
            list_identifier="x",
        ),
        AuthoredGridAxis(
            id="grid:x1",
            source_id="grid:equivalent",
            curve_points=((0.0, 100.0, 0.0), (120.0, 100.0, 0.0)),
            branch_identifier="main",
            list_identifier="x",
        ),
        AuthoredGridAxis(
            id="grid:y0",
            source_id="grid:equivalent",
            curve_points=((0.0, 0.0, 0.0), (0.0, 100.0, 0.0)),
            branch_identifier="main",
            list_identifier="y",
        ),
        AuthoredGridAxis(
            id="grid:y1",
            source_id="grid:equivalent",
            curve_points=((120.0, 0.0, 0.0), (120.0, 100.0, 0.0)),
            branch_identifier="main",
            list_identifier="y",
        ),
    )


def _equivalent_neutral_scene_facts(scene: NeutralSceneV2) -> NeutralSceneV2:
    """Attach the same query and authored-grid facts after adapter extraction."""
    return replace(
        scene,
        context=replace(scene.context, subject_interface_all_pairs=True),
        authored_grid_axes=_equivalent_authored_axes(),
    )


def _grid_relation_signature(column_grid: dict) -> tuple:
    """Normalize local and global grid relation values for source-independent comparison."""
    local = tuple(
        (
            item["scale"],
            round(item["frame_agreement"], 6),
            len(item["included_bay_ids"]),
            repr(item["bay_grammar"]),
        )
        for item in column_grid["local_profiles"]
    )
    global_ = tuple(
        (
            item["target_kind"],
            round(item["region_angle"], 6),
            round(item["target_angle"], 6),
            round(item["target_strength"], 6),
            round(item["agreement"], 6),
        )
        for item in column_grid["global_relations"]
    )
    return local, global_


def _subject_interface_relation_signature(result: dict) -> tuple:
    """Normalize relation values while excluding adapter-specific audit identifiers."""
    scope = result["subject_interface_relation_scope"]
    normalized_scope = (
        scope["status"],
        scope["method"],
        scope["max_distance"],
        scope["all_pairs"],
        scope["candidate_pair_count"],
        scope["relation_count"],
        len(scope["not_evaluated_pair_ids"]),
        scope["uncertainty"],
    )
    relations = tuple(
        (
            relation["subject_kind"],
            relation["interface_kind"],
            round(relation["distance"], 6),
            relation["nearest_side"],
            relation["frame_relation"],
            relation["subject_coverage_ratio"],
            relation["interface_coverage_ratio"],
            relation["containment"],
            relation["opening_ids"],
            relation["permeability"],
            relation["gestalt_continuity"],
            relation["parallel_coverage"],
        )
        for relation in result["subject_interface_relations"]
    )
    return normalized_scope, relations


def test_equivalent_svg_and_ifc_planar_facts_produce_equivalent_evidence(
    tmp_path: Path,
):
    """Equivalent adapter facts should converge after the Neutral Scene boundary."""
    svg_path = tmp_path / "equivalent.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 100">
        <rect id="ifc-object:left" data-role="furniture" x="15" y="45" width="30" height="10"/>
        <rect id="ifc-object:right" data-role="furniture" x="75" y="45" width="30" height="10"/>
        </svg>""",
        encoding="utf-8",
    )
    svg_scene = _equivalent_neutral_scene_facts(
        load_svg_neutral_scene(svg_path, source_length_unit="m")
    )
    ifc_scene = _equivalent_neutral_scene_facts(load_ifc_neutral_scene(_EquivalentIfcSource()))

    svg_evidence = infer_scene_evidence(svg_scene)
    ifc_evidence = infer_scene_evidence(ifc_scene)

    assert [_rect_signature(item) for item in svg_evidence["furniture_affordance_extents"]] == [
        _rect_signature(item) for item in ifc_evidence["furniture_affordance_extents"]
    ]
    assert [_rect_signature(item) for item in svg_evidence["inferred_regions"]] == [
        _rect_signature(item) for item in ifc_evidence["inferred_regions"]
    ]
    assert [_rect_signature(item) for item in svg_evidence["inferred_region_gap_paths"]] == [
        _rect_signature(item) for item in ifc_evidence["inferred_region_gap_paths"]
    ]
    assert [
        (
            len(group["member_ids"]),
            _rect_signature(group),
            group["metadata"]["group-axis-angle"],
            group["metadata"]["group-axis-strength"],
        )
        for group in svg_evidence["furniture_groups"]
    ] == [
        (
            len(group["member_ids"]),
            _rect_signature(group),
            group["metadata"]["group-axis-angle"],
            group["metadata"]["group-axis-strength"],
        )
        for group in ifc_evidence["furniture_groups"]
    ]
    assert [
        _network_signature(network) for network in svg_evidence["spatial_networks"]
    ] == [
        _network_signature(network) for network in ifc_evidence["spatial_networks"]
    ]
    assert [
        (region["metadata"]["axis-angle"], region["metadata"]["axis-trend-strength"])
        for region in svg_evidence["inferred_regions"]
    ] == [
        (region["metadata"]["axis-angle"], region["metadata"]["axis-trend-strength"])
        for region in ifc_evidence["inferred_regions"]
    ]
    assert [
        (
            interface["kind"],
            interface["interface_kind"],
            interface["physical_continuity"][0]["mass_present"],
        )
        for interface in svg_evidence["boundary_semantics"]
    ] == [
        (
            interface["kind"],
            interface["interface_kind"],
            interface["physical_continuity"][0]["mass_present"],
        )
        for interface in ifc_evidence["boundary_semantics"]
    ]
    assert evaluate_scene(svg_scene)["column_grid"]["status"] == (
        evaluate_scene(ifc_scene)["column_grid"]["status"]
    )
    svg_matrix = evaluate_scene(svg_scene)
    ifc_matrix = evaluate_scene(ifc_scene)
    assert _subject_interface_relation_signature(svg_matrix) == (
        _subject_interface_relation_signature(ifc_matrix)
    )
    assert _grid_relation_signature(svg_matrix["column_grid"]) == _grid_relation_signature(
        ifc_matrix["column_grid"]
    )
    svg_capabilities = analysis_scene_view(svg_scene)["_analysis_view"]["capability_flags"]
    assert svg_capabilities["height_queries"] is False


def test_real_ifc_fixture_keeps_non_furniture_out_of_region_inference(
    tmp_path: Path,
):
    """A real IFC adapter result should expose only furniture as region anchors."""
    path = tmp_path / "analysis-consumer.ifc"
    ids = write_ifc4_description_fixture(path)
    scene = load_ifc_neutral_scene(path, analysis_domain_source_id=ids["room"])
    furniture_ids = {
        item.id for item in scene.source_objects if item.source_role == "furniture"
    }

    evidence = infer_scene_evidence(scene)
    matrix = evaluate_scene(scene)

    assert {item["object_id"] for item in evidence["furniture_affordance_extents"]} == (
        furniture_ids
    )
    assert evidence["affordance_zones"]
    assert len(evidence["furniture_groups"]) == 1
    assert matrix["column_grid"]["status"] == "computed"
    assert all(
        item["branch_id"] == "default_branch"
        for item in matrix["column_grid"]["axes"]
    )
    assert all(
        item["id"] not in {f"ifc-object:{ids['wall']}", f"ifc-object:{ids['slab']}"}
        for item in matrix["room_analysis_model"]["object_layer"]["objects"]
    )


def _enclosure_box(ref, bounds):
    """Scale a clean existing box fixture to explicit analytic dimensions."""
    base = _box_mesh(mesh_id=ref)
    # The general substitute fixture intentionally includes a degenerate face;
    # remove it while constructing this valid input, never in production.
    return replace(base, vertices=tuple((bounds[0] + x / 2 * (bounds[3] - bounds[0]),
                                        bounds[1] + y / 2 * (bounds[4] - bounds[1]),
                                        bounds[2] + z * (bounds[5] - bounds[2])) for x, y, z in base.vertices),
                   triangle_indices=tuple(face for face in base.triangle_indices if len(set(face)) == 3))


def _enclosure_scene(inset=0.0):
    """Build two shared-wall contours, a multipart aperture and interior occupancy."""
    definitions = {"left": (0, 0, 0, 2, .25, 3), "right": (3, 0, 0, 6, .25, 3),
                   "lintel": (2, 0, 2.1, 3, .25, 3), "north": (0, 5.75, 0, 6, 6, 3),
                   "west": (0, .25, 0, .25, 5.75, 3), "east": (5.75, .25, 0, 6, 5.75, 3),
                   "divider": (4, .25, 0, 4.25, 5.75, 3), "column": (1, 2, 0, 1.3, 2.3, 3),
                   "furniture": (2, 2, 0, 2.5, 2.5, 2), "beam": (3, 3, 0, 3.5, 3.5, 3)}
    meshes = tuple(_enclosure_box(ref, bounds) for ref, bounds in definitions.items())
    objects = [SourceObject(id="host", source_role="wall", geometry_refs=("left", "right", "lintel"))]
    objects.extend(SourceObject(id=ref, source_role=ref if ref in {"column", "furniture", "beam"} else "wall", geometry_refs=(ref,))
                   for ref in definitions if ref not in {"left", "right", "lintel"})
    # This horizontal nonwatertight leaf has no material at the cut. Its actual
    # span can support the authorized scenario without inventing solid mass.
    window = _mesh("window-mesh", Rect(cx=2.5, cy=.125, width=1 - 2 * inset, height=.25), z=2.5)
    objects.append(SourceObject(id="window", source_role="window", geometry_refs=(window.id,),
                                factual_properties={"OM_Layout": {"AnalysisParticipation": "exclude"}}))
    return replace(_neutral_scene(), source_objects=tuple(objects), geometries=meshes + (window,),
                   openings=(), analysis_domain=None, authored_groups=())


def _enclosure_request(scene, contact=1e-6):
    """Supply every task/frame/measurement policy explicitly in test calls."""
    return {"analysis_plane": scene.context.analysis_plane, "units": "m", "datum_m": 0.0,
            "cut_height_m": 1.5, "contact_distance_m": contact, "aperture_area_budget_m2": 1e-6,
            "default_closed_authority": "test explicitly authorizes closed doors/windows",
            "exclude_override_authority": "test overrides exclude for this enclosure scenario"}


def _enclosure_diagnostics(scene, request=None):
    """Invoke the actual private production entry for composed regression cases."""
    return _analysis_scene_view_with_semantic_enclosure(scene, request=_enclosure_request(scene) if request is None else request)["_analysis_view"]["b2_boundary_diagnostics"]["semantic_enclosure"]


def test_private_enclosure_opt_in_preserves_default_sources_and_compound_scope():
    """Explicit carriers add contours while preserving ordinary occupancy/refusals."""
    scene = _enclosure_scene()
    facts = scene.to_dict()
    ordinary = analysis_scene_view(scene)
    assert "semantic_enclosure" not in ordinary["_analysis_view"]["b2_boundary_diagnostics"]
    opted = _analysis_scene_view_with_semantic_enclosure(scene, request=_enclosure_request(scene))
    result = opted["_analysis_view"]["b2_boundary_diagnostics"].pop("semantic_enclosure")
    assert opted == ordinary and scene.to_dict() == facts
    assert len(result["carriers"]) == 1 and len(result["enclosure_contours"]) == 2
    assert len(result["scope_proposals"]) == 1
    assert {c["scope_ref"] for c in result["enclosure_contours"]} == {"S1"}
    assert "column" in result["scope_proposals"][0]["occupancy_source_refs"]
    assert result["scope_proposals"][0]["geometry"]["area_m2"] == pytest.approx(36)
    window = next(row for row in result["sources"] if row["source_ref"] == "window")
    assert window["physical_section"]["area_m2"] == 0 and window["span_qualified"]
    assert window["source"]["source_id"] is None and window["source"]["source_class"] is None
    assert window["source"]["factual_properties"]["OM_Layout"]["AnalysisParticipation"] == "exclude"
    assert all(not row["enclosure_support_eligible"] for row in result["sources"] if row["kind"] in {"beam", "furniture"})
    assert result["candidate_promotion"] == "refused" and not result["active"]
    assert result["downstream"] == {"subtraction": "refused", "free_space": "not_evaluated", "route": "not_evaluated"}
    changed = replace(scene, context=replace(scene.context, geometry_tolerance=.25, topology_tolerance=.75))
    assert _enclosure_diagnostics(changed) == result


def test_private_enclosure_measured_contact_and_explicit_authority():
    """Distance-qualified contact stays distinct and never moves source coordinates."""
    scene = _enclosure_scene(inset=5e-7)
    strict = _enclosure_diagnostics(scene, _enclosure_request(scene, contact=0))
    measured = _enclosure_diagnostics(scene)
    assert not strict["carriers"] and len(measured["carriers"]) == 1
    alternative = measured["treatments"][0]["alternatives"][0]
    assert alternative["qualified"] and not alternative["literal_contact_qualified"]
    assert all(0 < c["distance_m"] <= 1e-6 and not c["exact_intersection"] for c in alternative["jamb_contacts"])
    refused = _enclosure_diagnostics(scene, _enclosure_request(scene) | {"exclude_override_authority": None})
    assert not refused["carriers"] and refused["treatments"][0]["refusal"] == "authored_exclude_without_task_override"
    for updates in ({"units": "mm"}, {"contact_distance_m": -1}, {"aperture_area_budget_m2": float("nan")},
                    {"datum_m": True}, {"cut_height_m": float("inf")}, {"default_closed_authority": ""},
                    {"exclude_override_authority": True}, {"analysis_plane": AnalysisPlane(name="other", origin=(0, 0, 0), basis=scene.context.analysis_plane.basis)}):
        with pytest.raises(ValueError):
            _enclosure_diagnostics(scene, _enclosure_request(scene) | updates)
    missing = _enclosure_request(scene)
    del missing["contact_distance_m"]
    with pytest.raises(ValueError, match="missing"):
        _enclosure_diagnostics(scene, missing)
    for key in ("datum_m", "cut_height_m", "contact_distance_m", "aperture_area_budget_m2"):
        with pytest.raises(ValueError, match=key):
            _enclosure_diagnostics(scene, _enclosure_request(scene) | {key: 10 ** 400})
    # Individually representable numbers can still overflow their accumulated
    # plane height, for both Python integer and floating-point inputs.
    for value in (10 ** 308, 1e308):
        with pytest.raises(ValueError, match="datum plus cut"):
            _enclosure_diagnostics(scene, _enclosure_request(scene) | {"datum_m": value, "cut_height_m": value})


def test_private_enclosure_local_refusals_and_authored_opening_precedence():
    """Preserve missing-only inference while refusing contrary or deficient evidence."""
    scene = _enclosure_scene()
    window = scene.source_objects[-1]
    opening = SourceOpening(id="opening", source_id=None, host_refs=("host",), geometry_refs=("window-mesh",), opening_kind="unfilled")
    unfilled = _enclosure_diagnostics(replace(scene, openings=(opening,)))
    assert not unfilled["carriers"] and unfilled["treatments"][0]["alternatives"][0]["opening_veto_refs"] == ["opening"]
    for kind in ("unfilled", "window", "door", "unknown"):
        for hosts in ((), ("absent",), ("north",)):
            local_opening = replace(opening, host_refs=hosts, opening_kind=kind)
            denied = _enclosure_diagnostics(replace(scene, openings=(local_opening,)))
            if kind != "unfilled" and hosts != ("north",):
                # Missing-only contextual facts stay unresolved while a known
                # leaf independently supplies one qualified inferred candidate.
                assert len(denied["carriers"]) == 1 and denied["carriers"][0]["association"] == "inferred"
                assert denied["treatments"][0]["authored_opening_refs"] == []
                evidence = denied["treatments"][0]["alternatives"][0]["unresolved_contextual_opening_evidence"][0]
                assert evidence["reason"] == "missing_contextual_host_relation_not_a_leaf_geometry_veto"
                assert denied["authored_opening_spans"][opening.id]["source"]["host_refs"] == list(hosts)
            else:
                assert not denied["carriers"]
                evidence = denied["treatments"][0]["alternatives"][0]["opening_veto_evidence"][0]
                reason = "explicit_local_unfilled_extent" if kind == "unfilled" else "unresolved_local_opening_host_relation"
                assert evidence["reason"] == reason
            assert evidence["authored_host_refs"] == list(hosts) and not evidence["host_mapping_inferred"]
            assert evidence["local_overlap"]["area_m2"] > 0
        unrelated = replace(opening, host_refs=(), geometry_refs=("north",), opening_kind=kind)
        assert len(_enclosure_diagnostics(replace(scene, openings=(unrelated,)))["carriers"]) == 1
    contextual = replace(opening, host_refs=(), opening_kind="window")
    opted = _analysis_scene_view_with_semantic_enclosure(replace(scene, openings=(contextual,)), request=_enclosure_request(scene))
    original = opted["_analysis_view"]["b2_boundary_diagnostics"]["openings"][0]
    assert original["host_refs"] == [] and original["local_diagnostic_state"] == "partial"
    ambiguous_context = replace(scene, openings=(contextual,),
                                source_objects=scene.source_objects + (replace(scene.source_objects[0], id="other-host"),))
    assert _enclosure_diagnostics(ambiguous_context)["treatments"][0]["host_mapping"] == "ambiguous"
    missing_context = replace(scene, openings=(contextual,), geometries=scene.geometries[:-1])
    assert not _enclosure_diagnostics(missing_context)["carriers"]
    linked = replace(scene, source_objects=scene.source_objects[:-1] + (replace(window, opening_refs=(opening.id,)),),
                     openings=(replace(opening, opening_kind="window"),))
    assert _enclosure_diagnostics(linked)["carriers"][0]["association"] == "authored"
    valid_link_missing_host = replace(linked, openings=(contextual,))
    derived = _enclosure_diagnostics(valid_link_missing_host)
    assert len(derived["carriers"]) == 1 and derived["carriers"][0]["association"] == "inferred"
    assert derived["treatments"][0]["authored_opening_refs"] == [opening.id]
    assert derived["treatments"][0]["authored_host_refs"] == []
    assert derived["authored_opening_spans"][opening.id]["qualified_aperture_refs"] == [derived["carriers"][0]["aperture_ref"]]
    invalid_host_target = replace(valid_link_missing_host, openings=(replace(contextual, host_refs=("absent",)),))
    assert not _enclosure_diagnostics(invalid_host_target)["carriers"]
    invalid_geometry_target = replace(valid_link_missing_host, openings=(replace(contextual, geometry_refs=("absent",)),))
    assert not _enclosure_diagnostics(invalid_geometry_target)["carriers"]
    partial = _mesh("partial-opening", Rect(cx=2.25, cy=.125, width=.5, height=.25), z=2.5)
    for geometry_refs, extra in ((("north",), ()), ((partial.id,), (partial,)), (("window-mesh", "north"), ())):
        contradictory = replace(linked, geometries=linked.geometries + extra,
                                 openings=(replace(opening, opening_kind="window", geometry_refs=geometry_refs),))
        before = contradictory.to_dict()
        denied = _enclosure_diagnostics(contradictory)
        assert not denied["carriers"] and denied["treatments"][0]["host_mapping"] == "unresolved"
        assert denied["treatments"][0]["refusal"] == "authored_opening_span_inconsistent"
        assert denied["authored_opening_spans"][opening.id]["qualified_aperture_refs"] == []
        assert contradictory.to_dict() == before
    duplicate = (replace(opening, opening_kind="window"), replace(opening, opening_kind="window", host_refs=("north",)))
    for records in (duplicate, duplicate[::-1]):
        denied = _enclosure_diagnostics(replace(linked, openings=records))
        assert not denied["carriers"] and denied["treatments"][0]["refusal"] == "authored_opening_mapping_unresolved"
        assert denied["treatments"][0]["duplicate_opening_refs"] == [opening.id]
        assert len(denied["opening_identity_conflicts"][0]["source_records"]) == 2
        # Duplicate authored host evidence must also veto an inferred seal when
        # no leaf relationship is available, rather than choosing by order.
        unlinked_duplicate = _enclosure_diagnostics(replace(scene, openings=records))
        assert not unlinked_duplicate["carriers"]
    conflict = replace(linked, openings=(replace(opening, opening_kind="window", host_refs=("host", "north")),))
    assert not _enclosure_diagnostics(conflict)["carriers"]
    missing_opening = replace(linked, openings=())
    assert not _enclosure_diagnostics(missing_opening)["carriers"]
    missing_geometry = replace(scene, source_objects=(replace(scene.source_objects[0], geometry_refs=("left", "right", "absent")),) + scene.source_objects[1:])
    result = _enclosure_diagnostics(missing_geometry)
    assert not result["carriers"] and result["sources"][0]["missing_geometry_refs"] == ["absent"]
    ambiguous = replace(scene, source_objects=scene.source_objects + (replace(scene.source_objects[0], id="second-host"),))
    assert _enclosure_diagnostics(ambiguous)["treatments"][0]["host_mapping"] == "ambiguous"
    remote = replace(scene, geometries=scene.geometries[:-1] + (_mesh("window-mesh", Rect(cx=2.5, cy=1, width=1, height=.25), z=2.5),))
    assert not _enclosure_diagnostics(remote)["carriers"]
    # Two surface components sharing only a vertex are not a qualified solid,
    # but their genuine face extent remains independently measurable as a leaf.
    surface = scene.geometries[-1]
    pinched = replace(surface, vertices=surface.vertices + ((2.4, .125, 2.6), (2.5, .125, 2.6)),
                      triangle_indices=surface.triangle_indices + ((0, 4, 5),))
    surface_result = _enclosure_diagnostics(replace(scene, geometries=scene.geometries[:-1] + (pinched,)))
    observation = surface_result["sources"][-1]["mesh_observations"][0]
    assert observation["pinched_components"] and not observation["solid_qualified"] and observation["span_qualified"]
    assert len(surface_result["carriers"]) == 1


def _handoff_frame(scene):
    """Supply one explicit session plane without authored floor metadata."""
    return {"analysis_plane": scene.context.analysis_plane, "units": "m",
            "datum_m": 0.0, "cut_height_m": 1.5}


def _handoff_confirm(preview, version_id, action_id="confirm-1", **overrides):
    """Target a preview's exact session/source/frame/request identities."""
    action = {"kind": "confirm", "candidate_version_id": version_id,
              "expected_candidate_identity": next((candidate["identity"] for candidate in preview["candidates"]
                                                   if candidate["version_id"] == version_id), None),
              "expected_session_revision": preview["session_revision"],
              "expected_source_revision": preview["provenance"]["source_revision"],
              "expected_plane_identity": preview["provenance"]["frame_id"],
              "expected_request_identity": preview["provenance"]["request_id"],
              "action_id": action_id, "actor": "test-user", "time": "2026-10-08T00:00:00Z",
              "reason": "explicitly selected scope"}
    return action | overrides


def test_private_domain_handoff_authored_confirmation_and_default_compatibility():
    """A caller-qualified authored polygon reaches only the private view seam."""
    scene = _neutral_scene()
    original = scene.to_dict()
    ordinary = analysis_scene_view(scene)
    frame = _handoff_frame(scene)
    start = _analysis_scene_view_with_domain_handoff(scene, frame_request=frame)
    assert start["current"]["status"] == "not_available"
    assert start["analysis_domain"] is None and start["downstream"]["formal_field"] == "not_available"
    assert len(start["candidates"]) == 1 and start["candidates"][0]["status"] == "provisional"
    assert start["session_revision"] == 0
    selected = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, session_state=start["session_state"],
        action={"kind": "select", "candidate_version_id": "domain_room"},
    )
    assert selected["session_revision"] == 0 and selected["current"]["status"] == "not_available"
    assert selected["candidates"][0]["status"] == "selected" and not selected["session_state"]["events"]
    hovered = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, session_state=start["session_state"],
        action={"kind": "hover", "candidate_version_id": "domain_room"},
    )
    assert hovered["candidates"][0]["status"] == "preview" and hovered["session_revision"] == 0
    action = _handoff_confirm(start, "domain_room")
    active = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, session_state=start["session_state"], action=action,
        expected_session_revision=0, expected_source_revision=start["provenance"]["source_revision"],
    )
    assert active["attempt"]["status"] == "accepted" and active["current"]["status"] == "active"
    assert active["candidates"][0]["status"] == "confirmed"
    assert active["session_revision"] == 1 and active["analysis_domain"] == scene.analysis_domain
    assert shape(active["scope_polygon"]).equals(shape(start["candidates"][0]["outline"]))
    assert active["preview"]["physical_occupancy"] == ordinary["physical_occupancy"]
    assert "floor_slab" not in {item["id"] for item in active["preview"]["physical_occupancy"]}
    assert "view" not in active and "_analysis_view" not in active["preview"]
    assert scene.to_dict() == original and analysis_scene_view(scene) == ordinary


def test_private_domain_handoff_authored_shape_holes_and_multiple_candidates():
    """Actual refs define the outline; mismatch and disjoint refs refuse."""
    scene = _neutral_scene()
    frame = _handoff_frame(scene)
    second = AnalysisDomain(id="second-domain", geometry_refs=("mesh_left",),
                            source_id=None, selection_method="explicit_test")
    start = _analysis_scene_view_with_domain_handoff(
        scene, candidates=({"analysis_domain": second},), frame_request=frame,
    )
    assert len(start["candidates"]) == 2 and start["current"]["status"] == "not_available"
    wrong = _analysis_scene_view_with_domain_handoff(
        scene, candidates=({"analysis_domain": second,
                            "selected_polygon": start["candidates"][0]["outline"]},),
        frame_request=frame,
    )
    assert wrong["candidates"][1]["reason"] == "authored_outline_projection_mismatch"
    refused = _analysis_scene_view_with_domain_handoff(
        scene, candidates=({"analysis_domain": second,
                            "selected_polygon": start["candidates"][0]["outline"]},),
        frame_request=frame, session_state=wrong["session_state"],
        action=_handoff_confirm(wrong, second.id), expected_session_revision=0,
        expected_source_revision=wrong["provenance"]["source_revision"],
    )
    assert refused["attempt"]["reason"] == "authored_outline_projection_mismatch"
    assert refused["analysis_domain"] is None
    disjoint = AnalysisDomain(id="disjoint", geometry_refs=("mesh_left", "mesh_right"),
                              source_id=None, selection_method="explicit_test")
    split = _analysis_scene_view_with_domain_handoff(
        scene, candidates=({"analysis_domain": disjoint},), frame_request=frame,
    )
    assert split["candidates"][1]["status"] == "refused"
    ring = _mesh("ring", Rect(cx=2, cy=2, width=4, height=4))
    ring = replace(ring, vertices=((0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0),
                                   (1, 1, 0), (3, 1, 0), (3, 3, 0), (1, 3, 0)),
                   triangle_indices=((0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
                                     (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)))
    holed_scene = replace(scene, analysis_domain=None, geometries=scene.geometries + (ring,))
    holed = AnalysisDomain(id="holed", geometry_refs=("ring",), source_id=None,
                            selection_method="explicit_test")
    holes = _analysis_scene_view_with_domain_handoff(
        holed_scene, candidates=({"analysis_domain": holed},), frame_request=_handoff_frame(holed_scene),
    )
    assert len(shape(holes["candidates"][0]["outline"]).interiors) == 1
    holed_active = _analysis_scene_view_with_domain_handoff(
        holed_scene, candidates=({"analysis_domain": holed},),
        frame_request=_handoff_frame(holed_scene), session_state=holes["session_state"],
        action=_handoff_confirm(holes, holed.id), expected_session_revision=0,
        expected_source_revision=holes["provenance"]["source_revision"],
    )
    assert holed_active["current"]["status"] == "active"
    assert len(shape(holed_active["scope_polygon"]).interiors) == 1
    filled_outline = mapping(Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]))
    lost_hole = _analysis_scene_view_with_domain_handoff(
        holed_scene, candidates=({"analysis_domain": holed, "selected_polygon": filled_outline},),
        frame_request=_handoff_frame(holed_scene),
    )
    assert lost_hole["candidates"][0]["reason"] == "authored_outline_projection_mismatch"


def test_private_domain_handoff_stale_replacement_and_source_change():
    """A refused attempt cannot erase a valid current choice or reuse changed input."""
    scene = _neutral_scene()
    frame = _handoff_frame(scene)
    second = AnalysisDomain(id="second-domain", geometry_refs=("mesh_left",),
                            source_id=None, selection_method="explicit_test")
    candidates = ({"analysis_domain": second},)
    start = _analysis_scene_view_with_domain_handoff(scene, candidates=candidates, frame_request=frame)
    first_action = _handoff_confirm(start, "domain_room")
    first = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=start["session_state"],
        action=first_action, expected_session_revision=0,
        expected_source_revision=start["provenance"]["source_revision"],
    )
    stale = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=first["session_state"],
        action=_handoff_confirm(start, second.id, action_id="stale"), expected_session_revision=0,
        expected_source_revision=start["provenance"]["source_revision"],
    )
    assert stale["attempt"]["reason"] == "stale_session_revision"
    assert stale["current"]["status"] == "active" and stale["selected_candidate_id"] == "domain_room"
    assert stale["session_revision"] == 1
    rejected = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=first["session_state"],
        action={"kind": "replace", "old_version_id": "domain_room", "new_version_id": "missing",
                **{k: v for k, v in _handoff_confirm(first, "missing", "bad-replace").items()
                   if k not in {"kind", "candidate_version_id"}}},
        expected_session_revision=1, expected_source_revision=first["provenance"]["source_revision"],
    )
    assert rejected["attempt"]["reason"] == "candidate_version_unavailable"
    assert rejected["current"]["status"] == "active" and rejected["analysis_domain"] == scene.analysis_domain
    changed = replace(scene, geometries=scene.geometries[:-1] +
                      (replace(scene.geometries[-1], vertices=tuple((x + .1, y, z)
                                                               for x, y, z in scene.geometries[-1].vertices)),))
    invalidated = _analysis_scene_view_with_domain_handoff(
        changed, candidates=candidates, frame_request=_handoff_frame(changed),
        session_state=rejected["session_state"],
    )
    assert invalidated["current"]["status"] == "not_available"
    assert invalidated["analysis_domain"] is None and invalidated["scope_polygon"] is None
    restored = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=invalidated["session_state"],
    )
    assert restored["current"]["status"] == "not_available" and restored["analysis_domain"] is None
    standalone = replace(scene, analysis_domain=None)
    candidate_start = _analysis_scene_view_with_domain_handoff(
        standalone, candidates=candidates, frame_request=_handoff_frame(standalone),
    )
    candidate_active = _analysis_scene_view_with_domain_handoff(
        standalone, candidates=candidates, frame_request=_handoff_frame(standalone),
        session_state=candidate_start["session_state"],
        action=_handoff_confirm(candidate_start, second.id, action_id="candidate-confirm"),
        expected_session_revision=0,
        expected_source_revision=candidate_start["provenance"]["source_revision"],
    )
    changed_candidate = _analysis_scene_view_with_domain_handoff(
        standalone, candidates=({"analysis_domain": replace(second, geometry_refs=("mesh_right",))},),
        frame_request=_handoff_frame(standalone), session_state=candidate_active["session_state"],
    )
    assert changed_candidate["current"]["status"] == "not_available"
    conflict = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=first["session_state"],
        action=first_action | {"reason": "contradictory reuse"}, expected_session_revision=1,
        expected_source_revision=first["provenance"]["source_revision"],
    )
    assert conflict["current"]["status"] == "conflict" and conflict["analysis_domain"] is None
    assert conflict["session_revision"] == 2 and len(conflict["session_state"]["events"]) == 2


def test_private_domain_handoff_replacement_switchback_and_retry():
    """A replacement is provisional and an older version needs fresh consent."""
    scene = _neutral_scene()
    frame = _handoff_frame(scene)
    second = AnalysisDomain(id="second-domain", geometry_refs=("mesh_left",),
                            source_id=None, selection_method="explicit_test")
    candidates = ({"analysis_domain": second},)
    start = _analysis_scene_view_with_domain_handoff(scene, candidates=candidates, frame_request=frame)
    action = _handoff_confirm(start, "domain_room")
    first = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=start["session_state"],
        action=action, expected_session_revision=0,
        expected_source_revision=start["provenance"]["source_revision"],
    )
    duplicate = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=first["session_state"],
        action=action, expected_session_revision=0,
        expected_source_revision=start["provenance"]["source_revision"],
    )
    assert duplicate["attempt"]["status"] == "duplicate" and duplicate["session_revision"] == 1
    replacement = {"kind": "replace", "old_version_id": "domain_room", "new_version_id": second.id,
                   **{key: value for key, value in _handoff_confirm(first, second.id, "replace-1").items()
                      if key not in {"kind", "candidate_version_id"}}}
    replaced = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=duplicate["session_state"],
        action=replacement, expected_session_revision=1,
        expected_source_revision=first["provenance"]["source_revision"],
    )
    assert replaced["attempt"]["status"] == "accepted" and replaced["session_revision"] == 2
    assert replaced["current"]["status"] == "not_available" and replaced["analysis_domain"] is None
    switched = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=replaced["session_state"],
        action=_handoff_confirm(replaced, "domain_room", "switch-back"),
        expected_session_revision=2, expected_source_revision=replaced["provenance"]["source_revision"],
    )
    assert switched["attempt"]["status"] == "accepted"
    assert switched["current"]["status"] == "active" and switched["session_revision"] == 3


def test_private_domain_handoff_no_domain_and_changed_frame():
    """No candidate and a changed caller frame cannot yield a consumable domain."""
    scene = replace(_neutral_scene(), analysis_domain=None)
    frame = _handoff_frame(scene)
    empty = _analysis_scene_view_with_domain_handoff(scene, frame_request=frame)
    assert not empty["candidates"] and empty["analysis_domain"] is None
    assert empty["downstream"] == {"formal_field": "not_available", "topology": "not_available",
                                   "route": "not_available"}
    domain = AnalysisDomain(id="room", geometry_refs=("mesh_slab",), source_id=None,
                            selection_method="explicit_test")
    candidates = ({"analysis_domain": domain},)
    start = _analysis_scene_view_with_domain_handoff(scene, candidates=candidates, frame_request=frame)
    active = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame, session_state=start["session_state"],
        action=_handoff_confirm(start, domain.id), expected_session_revision=0,
        expected_source_revision=start["provenance"]["source_revision"],
    )
    changed = _analysis_scene_view_with_domain_handoff(
        scene, candidates=candidates, frame_request=frame | {"datum_m": 1.0},
        session_state=active["session_state"],
    )
    assert changed["current"]["status"] == "not_available" and changed["analysis_domain"] is None
    assert changed["session_state"]["invalidated"]
    with pytest.raises(ValueError, match="datum_m"):
        _analysis_scene_view_with_domain_handoff(
            scene, candidates=candidates, frame_request={key: value for key, value in frame.items()
                                                   if key != "datum_m"},
        )


def test_private_domain_handoff_inferred_scope_and_explicit_frame():
    """The accepted B2 helper supplies an inferred scope without auto-activation."""
    scene = _enclosure_scene()
    facts = scene.to_dict()
    request = _enclosure_request(scene)
    frame = _handoff_frame(scene)
    start = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request,
    )
    assert len(start["candidates"]) == 1 and start["current"]["status"] == "not_available"
    version = start["candidates"][0]["version_id"]
    active = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request, session_state=start["session_state"],
        action=_handoff_confirm(start, version), expected_session_revision=0,
        expected_source_revision=start["provenance"]["source_revision"],
    )
    assert active["attempt"]["status"] == "accepted" and active["current"]["status"] == "active"
    assert active["analysis_domain"].source_id is None
    assert active["analysis_domain"].selection_method == "explicit_session_confirmation_of_inferred_candidate"
    assert shape(active["scope_polygon"]).equals(shape(start["candidates"][0]["outline"]))
    assert {item["id"] for item in active["preview"]["physical_occupancy"]} >= {"host", "column"}
    assert "view" not in active and scene.to_dict() == facts
    with pytest.raises(ValueError, match="analysis_plane"):
        _analysis_scene_view_with_domain_handoff(
            scene, frame_request=frame | {"analysis_plane": AnalysisPlane(
                name="other", origin=(0, 0, 0), basis=scene.context.analysis_plane.basis)},
        )


def test_private_domain_handoff_inferred_conflict_and_local_refusal():
    """Authored disagreement needs explicit acknowledgement; residuals still refuse."""
    scene = _enclosure_scene()
    authored = AnalysisDomain(id="authored-small", geometry_refs=("furniture",),
                              source_id=None, selection_method="explicit_test")
    scene = replace(scene, analysis_domain=authored)
    frame, request = _handoff_frame(scene), _enclosure_request(scene)
    start = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request,
    )
    inferred = next(item for item in start["candidates"] if item["source"] == "inferred")
    unacknowledged = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request, session_state=start["session_state"],
        action=_handoff_confirm(start, inferred["version_id"]), expected_session_revision=0,
        expected_source_revision=start["provenance"]["source_revision"],
    )
    assert unacknowledged["attempt"]["reason"] == "authored_inferred_conflict_unacknowledged"
    assert unacknowledged["analysis_domain"] is None
    acknowledged = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request, session_state=unacknowledged["session_state"],
        action=_handoff_confirm(start, inferred["version_id"], action_id="acknowledged",
                                acknowledged_conflict_ids=[authored.id]),
        expected_session_revision=0, expected_source_revision=start["provenance"]["source_revision"],
    )
    assert acknowledged["current"]["status"] == "active"
    observed = _enclosure_diagnostics(scene, request)
    local_scope = dict(observed["scope_proposals"][0], local_unresolved_aperture_refs=["local-open-residual"])
    unresolved = dict(observed, scope_proposals=[local_scope])
    probe = domain_handoff(scene, candidates=(), session_state=None, action=None,
                           expected_session_revision=None, expected_source_revision=None,
                           frame_request=frame, b2=unresolved, b2_request=request)
    local = next(item for item in probe["candidates"] if item["source"] == "inferred")
    assert local["status"] == "refused" and local["reason"] == "unresolved_local_aperture"
    assert local["unresolved_aperture_refs"] == ("local-open-residual",)
    denied = domain_handoff(scene, candidates=(), session_state=probe["session_state"],
                            action=_handoff_confirm(probe, local["version_id"],
                                                    acknowledged_conflict_ids=[authored.id]),
                            expected_session_revision=0,
                            expected_source_revision=probe["provenance"]["source_revision"],
                            frame_request=frame, b2=unresolved, b2_request=request)
    assert denied["attempt"]["reason"] == "unresolved_local_aperture"
    assert denied["current"]["status"] == "not_available" and denied["analysis_domain"] is None


def test_private_domain_handoff_rejects_unconfirmed_session_projection():
    """A claimed current choice needs an accepted confirm in its event history."""
    scene = _neutral_scene()
    frame = _handoff_frame(scene)
    start = _analysis_scene_view_with_domain_handoff(scene, frame_request=frame)
    candidate = start["candidates"][0]
    forged = {"revision": 1, "current_version_id": candidate["version_id"],
              "current_binding": {"source_revision": start["provenance"]["source_revision"],
                                  "frame_id": start["provenance"]["frame_id"],
                                  "request_id": start["provenance"]["request_id"],
                                  "candidate_identity": candidate["identity"],
                                  "acknowledged_conflicts": []},
              "conflict": False, "invalidated": False, "events": []}
    refused = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, session_state=forged,
    )
    assert refused["attempt"]["reason"] == "inconsistent_session_state"
    assert refused["current"]["status"] == "not_available"
    assert refused["analysis_domain"] is None and refused["session_revision"] == 0
    # A valid projection cannot change its claimed binding independently of the log.
    active = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, session_state=start["session_state"],
        action=_handoff_confirm(start, candidate["version_id"]),
        expected_session_revision=0, expected_source_revision=start["provenance"]["source_revision"],
    )
    inconsistent = active["session_state"] | {"current_binding": forged["current_binding"] | {
        "candidate_identity": "not-the-confirmed-candidate"}}
    refused = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, session_state=inconsistent,
    )
    assert refused["current"]["status"] == "not_available"
    assert refused["attempt"]["reason"] == "inconsistent_session_state"


def test_private_domain_handoff_rechecks_later_candidate_disagreements():
    """A later opposite-source disagreement requires a fresh acknowledgement."""
    scene = _enclosure_scene()
    scene = replace(scene, geometries=scene.geometries +
                    (_mesh("equal-scope", Rect(cx=3, cy=3, width=6, height=6)),))
    frame, request = _handoff_frame(scene), _enclosure_request(scene)
    start = _analysis_scene_view_with_domain_handoff(scene, frame_request=frame, b2_request=request)
    inferred = start["candidates"][0]
    active = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request, session_state=start["session_state"],
        action=_handoff_confirm(start, inferred["version_id"]),
        expected_session_revision=0, expected_source_revision=start["provenance"]["source_revision"],
    )
    same = AnalysisDomain(id="same-outline", geometry_refs=("equal-scope",),
                          source_id=None, selection_method="explicit_test")
    same_source = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request, session_state=active["session_state"],
        candidates=({"analysis_domain": same},),
    )
    assert shape(same_source["candidates"][0]["outline"]).equals(shape(inferred["outline"]))
    assert same_source["current"]["status"] == "active"
    authored = AnalysisDomain(id="later-authored", geometry_refs=("furniture",),
                              source_id=None, selection_method="explicit_test")
    candidates = ({"analysis_domain": authored},)
    later = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request, candidates=candidates,
        session_state=active["session_state"],
    )
    assert len(later["candidates"]) == 2
    assert later["current"]["status"] == "not_available" and later["analysis_domain"] is None
    assert later["session_state"]["invalidated"] and later["session_revision"] == 2
    stale = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request, candidates=candidates,
        session_state=later["session_state"],
        action=_handoff_confirm(active, inferred["version_id"], action_id="stale-ack",
                                acknowledged_conflict_ids=[authored.id]),
        expected_session_revision=active["session_revision"],
        expected_source_revision=active["provenance"]["source_revision"],
    )
    assert stale["attempt"]["reason"] == "stale_session_revision"
    assert stale["current"]["status"] == "not_available"
    acknowledged = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, b2_request=request, candidates=candidates,
        session_state=later["session_state"],
        action=_handoff_confirm(later, inferred["version_id"], action_id="fresh-ack",
                                acknowledged_conflict_ids=[authored.id]),
        expected_session_revision=later["session_revision"],
        expected_source_revision=later["provenance"]["source_revision"],
    )
    assert acknowledged["current"]["status"] == "active"
    assert acknowledged["analysis_domain"] is not None and acknowledged["session_revision"] == 3


def test_private_domain_handoff_preserves_furniture_source_occupancy():
    """An authored source identifier must not turn furniture into a domain shell."""
    base = _neutral_scene()
    scene = replace(base, analysis_domain=None,
                    source_objects=(replace(base.source_objects[0], source_id="table-src"),)
                    + base.source_objects[1:])
    domain = AnalysisDomain(id="table-domain", geometry_refs=("mesh_left",),
                            source_id="table-src", selection_method="explicit_test")
    candidates = ({"analysis_domain": domain},)
    frame = _handoff_frame(scene)
    start = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, candidates=candidates,
    )
    active = _analysis_scene_view_with_domain_handoff(
        scene, frame_request=frame, candidates=candidates, session_state=start["session_state"],
        action=_handoff_confirm(start, domain.id), expected_session_revision=0,
        expected_source_revision=start["provenance"]["source_revision"],
    )
    ordinary_ids = {item["id"] for item in analysis_scene_view(scene)["physical_occupancy"]}
    preview_ids = {item["id"] for item in active["preview"]["physical_occupancy"]}
    assert active["current"]["status"] == "active" and "left_table" in ordinary_ids & preview_ids
    assert active["analysis_domain"].source_id == "table-src"
    assert scene.analysis_domain is None
