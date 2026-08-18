"""Run both Gate 8 geometry paths and serialize neutral acceptance outputs."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass, replace
import json
from pathlib import Path
from typing import Mapping

try:
    from ...adapters.blender_geometry import load_blender_neutral_scene
    from ...adapters.ifc_bonsai import load_ifc_neutral_scene
    from ...features.geometry_substitutes import mass_patch_from_mesh
    from ...features.geometry_views import vertical_intervals_at
    from ...features.neutral_scene_views import analysis_scene_view
    from ...features.scene_contract import (
        AnalysisDomain,
        AuthoredAffordanceZone,
        AuthoredGrid,
        AuthoredGridAxis,
        AuthoredGroup,
        MaterialFact,
        SurfaceFact,
    )
    from ...features.scene_evaluator import evaluate_scene
    from ...features.scene_inference import infer_scene_evidence
    from .generate_bim_acceptance_scene import generate_acceptance_scene
except ImportError:
    from adapters.blender_geometry import load_blender_neutral_scene
    from adapters.ifc_bonsai import load_ifc_neutral_scene
    from features.geometry_substitutes import mass_patch_from_mesh
    from features.geometry_views import vertical_intervals_at
    from features.neutral_scene_views import analysis_scene_view
    from features.scene_contract import (
        AnalysisDomain,
        AuthoredAffordanceZone,
        AuthoredGrid,
        AuthoredGridAxis,
        AuthoredGroup,
        MaterialFact,
        SurfaceFact,
    )
    from features.scene_evaluator import evaluate_scene
    from features.scene_inference import infer_scene_evidence
    from test.blender.generate_bim_acceptance_scene import generate_acceptance_scene


ROOT = Path(__file__).parents[2]


def _source_by_logical_id(scene, source_ids: Mapping[str, str]) -> dict[str, object]:
    """Index IFC neutral source objects by stable logical fixture id."""
    logical_by_source = {source_id: logical_id for logical_id, source_id in source_ids.items()}
    return {
        logical_by_source[source.source_id]: source
        for source in scene.source_objects
        if source.source_id in logical_by_source
    }


def _blender_source_by_logical_id(scene) -> dict[str, object]:
    """Index explicit Blender neutral records by their selected object id."""
    return {
        str(source.provenance["object_id"]): source
        for source in scene.source_objects
    }


def _blender_authored_records(snapshot: Mapping[str, object]) -> dict[str, tuple[object, ...]]:
    """Convert generated Blender authored payloads into validated contract records."""
    return {
        "authored_groups": tuple(AuthoredGroup(**record) for record in snapshot.get("authored_groups", ())),
        "authored_grids": tuple(AuthoredGrid(**record) for record in snapshot.get("authored_grids", ())),
        "authored_grid_axes": tuple(AuthoredGridAxis(**record) for record in snapshot.get("authored_grid_axes", ())),
        "materials": tuple(MaterialFact(**record) for record in snapshot.get("materials", ())),
        "surfaces": tuple(SurfaceFact(**record) for record in snapshot.get("surfaces", ())),
        "authored_affordances": tuple(
            AuthoredAffordanceZone(**record)
            for record in snapshot.get("authored_affordances", ())
        ),
    }


def _mesh_bounds(scene, source) -> list[float]:
    """Return rounded XYZ bounds over every geometry reference on one source object."""
    geometry_by_id = {geometry.id: geometry for geometry in scene.geometries}
    vertices = [
        vertex
        for geometry_ref in source.geometry_refs
        for vertex in geometry_by_id[geometry_ref].vertices
    ]
    return [
        round(value, 6)
        for value in (
            min(vertex[0] for vertex in vertices),
            min(vertex[1] for vertex in vertices),
            min(vertex[2] for vertex in vertices),
            max(vertex[0] for vertex in vertices),
            max(vertex[1] for vertex in vertices),
            max(vertex[2] for vertex in vertices),
        )
    ]


def _shared_geometry_facts(ifc_scene, blender_scene, source_ids: Mapping[str, str]) -> dict:
    """Compare adapter outputs only where both paths describe identical source geometry."""
    ifc_sources = _source_by_logical_id(ifc_scene, source_ids)
    blender_sources = _blender_source_by_logical_id(blender_scene)
    compared = sorted(set(ifc_sources) & set(blender_sources))
    records = []
    for logical_id in compared:
        ifc_bounds = _mesh_bounds(ifc_scene, ifc_sources[logical_id])
        blender_bounds = _mesh_bounds(blender_scene, blender_sources[logical_id])
        records.append(
            {
                "id": logical_id,
                "ifc_bounds": ifc_bounds,
                "blender_bounds": blender_bounds,
                "match": ifc_bounds == blender_bounds,
            }
        )
    return {
        "method": "world_mesh_bounds_cross_adapter_comparison",
        "compared_ids": compared,
        "records": records,
        "all_match": bool(records) and all(record["match"] for record in records),
    }


def _sofa_height_queries(scene, source_ids: Mapping[str, str]) -> dict:
    """Measure local sofa occupancy at probes that separate seat and back geometry."""
    source = _source_by_logical_id(scene, source_ids)["sofa"]
    geometry_by_id = {geometry.id: geometry for geometry in scene.geometries}
    patches = [mass_patch_from_mesh(geometry_by_id[item]) for item in source.geometry_refs]

    def query(point: tuple[float, float]) -> dict:
        """Merge deterministic local intervals from every sofa geometry patch."""
        intervals = []
        uncertainties = []
        for patch in patches:
            result = vertical_intervals_at(patch, point)
            intervals.extend(result.intervals)
            uncertainties.extend(result.uncertainties)
        return {
            "point": list(point),
            "intervals": [
                [round(bound, 6) for bound in interval]
                for interval in sorted(set(intervals))
            ],
            "uncertainties": sorted(set(uncertainties)),
            "method": "vertical_triangle_intersections",
        }

    # The two probes deliberately hit different connected parts; a one-height
    # bbox cannot satisfy these assertions.
    return {
        "seat_probe": query((8.0, 6.2)),
        "back_probe": query((8.0, 6.82)),
    }


def _surface_evidence(scene, source_ids: Mapping[str, str]) -> dict:
    """Serialize carpet surface evidence while explicitly keeping mass references empty."""
    carpet_source_id = source_ids["carpet"]
    carpet = next(surface for surface in scene.surfaces if surface.source_id == carpet_source_id)
    return {
        "carpet": {
            "source_id": carpet.source_id,
            "surface_geometry_refs": list(carpet.geometry_refs),
            "mass_geometry_refs": [],
            "identity": carpet.identity,
            "method": carpet.provenance.get("method"),
            "uncertainties": [item.to_dict() for item in carpet.uncertainties],
        }
    }


def _channel_summary(scene, source_ids: Mapping[str, str]) -> dict:
    """Extract separate walking and visual observations for two contrasting objects."""
    view = analysis_scene_view(scene)
    sources = _source_by_logical_id(scene, source_ids)
    result = {}
    for logical_id in ("low_cabinet", "glass_partition"):
        evidence = view["channel_evidence"][sources[logical_id].id]
        result[logical_id] = {
            "walking": evidence["walking"][0],
            "visual": evidence["visual"][0],
            "visible_transmittance": evidence["visible_transmittance"],
            "method": "height_band_and_optical_channel_evidence",
        }
    return result


def _ordering_cases(inference: dict, scene, source_ids: Mapping[str, str]) -> dict:
    """Map canonical furniture-group frame evidence back to logical fixture cases."""
    sources = _source_by_logical_id(scene, source_ids)
    expected_members = {
        "aligned": {sources["aligned_table_a"].id, sources["aligned_chair"].id},
        "oblique": {sources["oblique_table_a"].id, sources["oblique_chair"].id},
        "mixed": {sources["mixed_table_a"].id, sources["mixed_table_b"].id},
    }
    result = {}
    for case, member_ids in expected_members.items():
        group = next(
            item
            for item in inference["furniture_groups"]
            if set(item["member_ids"]) == member_ids
        )
        metadata = group["metadata"]
        result[case] = {
            "group_id": group["id"],
            "primary_angle": float(metadata["group-axis-angle"]),
            "secondary_angle": float(metadata["group-secondary-axis-angle"]),
            "concentration": float(metadata["group-axis-strength"]),
            "method": metadata["group-axis-basis"],
        }
    return result


def _grid_relations(matrix: dict) -> dict:
    """Expose concrete local and global column-grid relation evidence."""
    evidence = matrix["column_grid"]
    return {
        "local": list(evidence.get("local_profiles", [])),
        "global": list(evidence.get("global_relations", [])),
        "method": "authored_grid_axis_relation_views",
    }


def _path_signature(inference: dict, matrix: dict, scene, affordance_ids: list[str]) -> dict:
    """Build a path-independent signature for high-level authored and derived evidence."""
    ordering = []
    for group in inference["furniture_groups"]:
        metadata = group["metadata"]
        ordering.append(
            {
                "member_count": len(group["member_ids"]),
                "primary_angle": round(float(metadata["group-axis-angle"]), 4),
                "secondary_angle": round(float(metadata["group-secondary-axis-angle"]), 4),
                "concentration": round(float(metadata["group-axis-strength"]), 4),
            }
        )
    ordering.sort(key=lambda item: (item["primary_angle"], item["member_count"]))
    return {
        "ordering_cases": ordering,
        "network_scopes": sorted({item["scope"] for item in inference["spatial_networks"]}),
        "authored_affordance_ids": sorted(affordance_ids),
        "grid_relations": {
            "local": bool(matrix["column_grid"].get("local_profiles")),
            "global": bool(matrix["column_grid"].get("global_relations")),
        },
        "source": scene.context.input_mode,
    }


def _logical_affordance_ids(scene, source_ids: Mapping[str, str]) -> list[str]:
    """Normalize authored affordance identities across IFC and Blender adapters."""
    if scene.context.input_mode == "blender_geometry":
        return sorted(zone.source_id for zone in scene.authored_affordances if zone.source_id)
    reverse = {source_id: logical_id for logical_id, source_id in source_ids.items()}
    return sorted(
        reverse[zone.source_id]
        for zone in scene.authored_affordances
        if zone.source_id in reverse
    )


def _without_scoring_fields(value: object) -> object:
    """Remove fitted scoring and perceptual-weight keys from a neutral JSON export."""
    if is_dataclass(value) and not isinstance(value, type):
        return _without_scoring_fields(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _without_scoring_fields(nested)
            for key, nested in value.items()
            if "weight" not in str(key).lower()
            and "score" not in str(key).lower()
        }
    if isinstance(value, (list, tuple)):
        return [_without_scoring_fields(item) for item in value]
    return value


def _write_json(path: Path, value: object) -> None:
    """Write one canonical UTF-8 JSON artifact with deterministic ordering."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Canonical formatting makes rerun equivalence directly testable without
    # deleting fields or relying on Python object identity.
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def run_acceptance(output_dir: Path) -> dict[str, Path]:
    """Generate, analyze, compare, and serialize the complete Gate 8 fixture."""
    generated = generate_acceptance_scene(Path(output_dir))
    source_ids = generated["source_ids"]
    ifc_scene = load_ifc_neutral_scene(
        generated["ifc"],
        analysis_domain_source_id=source_ids["room"],
    )
    # Height bands are explicit analysis demands, not inferred object
    # affordances or adapter classifications.
    ifc_scene = replace(
        ifc_scene,
        context=replace(
            ifc_scene.context,
            walking_body_profiles=(
                {"id": "adult-body", "height_band": (0.05, 1.0), "radius": 0.3, "required_path_width": 0.6},
            ),
            visual_height_bands=(
                {"id": "standing-eye", "height_band": (1.5, 1.8)},
            ),
            capability_flags={
                **dict(ifc_scene.context.capability_flags),
                "height_queries": True,
                "closed_solid_geometry": True,
                "optical_queries": True,
            },
        ),
    )
    blender_scene = load_blender_neutral_scene(
        generated["blender_snapshot"],
        mode="blender_geometry",
        roles=generated["roles"],
        **_blender_authored_records(generated["blender_snapshot"]),
        analysis_domain=AnalysisDomain(
            id="blender-domain:room",
            geometry_refs=("blender-mesh:room",),
            source_id=None,
            selection_method="generated_explicit_selection",
        ),
    )

    # Both routes receive the same explicit analysis demands so differences in
    # signatures reflect source facts and adapter transport, not query defaults.
    blender_scene = replace(
        blender_scene,
        context=replace(
            blender_scene.context,
            walking_body_profiles=ifc_scene.context.walking_body_profiles,
            visual_height_bands=ifc_scene.context.visual_height_bands,
            capability_flags={
                **dict(blender_scene.context.capability_flags),
                "height_queries": True,
                "closed_solid_geometry": True,
                "optical_queries": True,
            },
        ),
    )
    # Gate 7 public APIs consume both Neutral Scenes directly; no SVG or
    # adapter-private fields participate in either path's analysis.
    ifc_inference = infer_scene_evidence(ifc_scene)
    ifc_matrix = evaluate_scene(ifc_scene)
    blender_inference = infer_scene_evidence(blender_scene)
    blender_matrix = evaluate_scene(blender_scene)
    ifc_affordance_ids = _logical_affordance_ids(ifc_scene, source_ids)
    blender_affordance_ids = _logical_affordance_ids(blender_scene, source_ids)
    ifc_signature = _path_signature(
        ifc_inference, ifc_matrix, ifc_scene, ifc_affordance_ids
    )
    blender_signature = _path_signature(
        blender_inference, blender_matrix, blender_scene, blender_affordance_ids
    )
    description = {
        "contract": {"id": "bim_acceptance_description", "version": 1},
        "fixture_ids": sorted(source_ids),
        "input_modes": ["ifc", "blender_geometry"],
        "shared_facts": _shared_geometry_facts(ifc_scene, blender_scene, source_ids),
        "height_queries": {"sofa": _sofa_height_queries(ifc_scene, source_ids)},
        "surface_evidence": _surface_evidence(ifc_scene, source_ids),
        "channel_evidence": _channel_summary(ifc_scene, source_ids),
        "authored_affordances": sorted(
            logical_id
            for logical_id in ("chair_affordance_aligned", "chair_affordance_oblique")
            if any(zone.source_id == source_ids[logical_id] for zone in ifc_scene.authored_affordances)
        ),
        "ordering_cases": _ordering_cases(ifc_inference, ifc_scene, source_ids),
        "spatial_networks": ifc_inference["spatial_networks"],
        "grid_relations": _grid_relations(ifc_matrix),
        "path_analyses": {
            "ifc": ifc_signature,
            "blender_geometry": blender_signature,
        },
        "cross_path_signatures": {
            "ordering_equivalent": ifc_signature["ordering_cases"] == blender_signature["ordering_cases"],
            "network_scopes_equivalent": ifc_signature["network_scopes"] == blender_signature["network_scopes"],
            "authored_affordances_equivalent": ifc_signature["authored_affordance_ids"] == blender_signature["authored_affordance_ids"],
            "grid_relations_equivalent": ifc_signature["grid_relations"] == blender_signature["grid_relations"],
        },
        "provenance": {
            "methods": [
                "ifc4_native_adapter",
                "explicit_blender_geometry_snapshot",
                "neutral_scene_gate7_analysis",
            ],
            "source_ids": dict(sorted(source_ids.items())),
            "geometry_tolerance": ifc_scene.context.geometry_tolerance,
            "topology_tolerance": ifc_scene.context.topology_tolerance,
            "ifc_artifact": generated["ifc"].name,
        },
        "uncertainties": [item.to_dict() for item in ifc_scene.uncertainties],
    }
    description = _without_scoring_fields(description)
    room_model = _without_scoring_fields(ifc_matrix["room_analysis_model"])
    description_path = Path(output_dir) / "blender_demo_description.json"
    room_model_path = Path(output_dir) / "blender_demo_room_analysis_model.json"
    _write_json(description_path, description)
    _write_json(room_model_path, room_model)
    return {
        "ifc": generated["ifc"],
        "description": description_path,
        "room_model": room_model_path,
    }


if __name__ == "__main__":
    run_acceptance(ROOT / "test" / "output")
