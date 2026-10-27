"""Recompute group geometry and trend envelopes before and after an in-memory IFC rotation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.field_core import FieldQuery, fingerprint_evidence_dependency  # noqa: E402
from features.group_geometry_relation_field import build_group_geometry_relation_envelopes  # noqa: E402
from features.group_self_description import describe_group_relations  # noqa: E402
from features.group_trend_alignment_field import build_group_trend_alignment_envelopes  # noqa: E402
from scripts.design.group_level.run_group_evidence_freshness_ifc_diagnostic import (  # noqa: E402
    EXPECTED_SOURCE_BYTES,
    EXPECTED_SOURCE_SHA256,
    ROTATION_DEGREES,
    _group_points,
    _plan_svg,
    _rotate_scene_geometry,
)
from scripts.design.group_level.run_group_trend_alignment_field_ifc import (  # noqa: E402
    DEFAULT_IFC,
    _build_scene,
    _fingerprint,
    _plain,
    _write,
)

SCHEMA = "group-evidence-actual-recompute-ifc/v1"
GEOMETRY_ALGORITHM = "group-geometry-relation/v1"
GEOMETRY_SCHEMA = "group-geometry-relation-field/v1"
GEOMETRY_PACKAGE_SCHEMA = "group-geometry-relation-envelopes/v1"
TREND_ALGORITHM = "group-trend-alignment-field-v2"
TREND_PACKAGE_SCHEMA = "group-trend-alignment-envelopes/v2"
EVIDENCE_FIELDS = (
    "target",
    "query",
    "raw_status",
    "channel_set",
    "value",
    "support",
    "field_projection",
    "source_ids",
    "provenance",
    "visualization_ref",
    "explanation",
    "schema",
)


def _scene_fingerprint(scene: Any) -> str:
    """Fingerprint the actual geometry and membership inputs consumed by both builders."""
    return fingerprint_evidence_dependency(
        {
            "analysis_plane": scene.context.analysis_plane,
            "geometries": scene.geometries,
            "authored_groups": scene.authored_groups,
            "source_objects": scene.source_objects,
        }
    )


def _build_envelopes(
    scene: Any,
    *,
    geometry_query: FieldQuery,
    trend_query: FieldQuery,
    source_sha256: str,
    input_fingerprint: str,
) -> dict[str, tuple[Any, ...]]:
    """Run both real evidence builders with stable source/query/recipe identity."""
    geometry = build_group_geometry_relation_envelopes(
        scene,
        query=geometry_query,
        input_fingerprint=input_fingerprint,
        source_fingerprint=source_sha256,
        recipe_fingerprint="group-geometry-relation-working-contract-v1",
        algorithm_version=GEOMETRY_ALGORITHM,
        schema_version=GEOMETRY_SCHEMA,
    )
    trend = build_group_trend_alignment_envelopes(
        scene,
        query=trend_query,
        input_fingerprint=input_fingerprint,
        source_fingerprint=source_sha256,
        recipe_fingerprint="group-trend-alignment-working-contract-v1",
        algorithm_version=TREND_ALGORITHM,
        schema_version=TREND_PACKAGE_SCHEMA,
    )
    return {"geometry_relation": geometry, "trend_alignment": trend}


def _difference_paths(before: Any, after: Any, path: str) -> list[dict[str, Any]]:
    """Return exact leaf changes between two JSON-safe evidence values."""
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        differences = []
        for key in sorted(set(before) | set(after), key=str):
            child = f"{path}.{key}"
            if key not in before or key not in after:
                differences.append(
                    {
                        "path": child,
                        "before_present": key in before,
                        "after_present": key in after,
                        "before": before.get(key),
                        "after": after.get(key),
                    }
                )
            else:
                differences.extend(_difference_paths(before[key], after[key], child))
        return differences
    if isinstance(before, list) and isinstance(after, list):
        differences = []
        for index in range(max(len(before), len(after))):
            child = f"{path}[{index}]"
            if index >= len(before) or index >= len(after):
                differences.append(
                    {
                        "path": child,
                        "before_present": index < len(before),
                        "after_present": index < len(after),
                        "before": before[index] if index < len(before) else None,
                        "after": after[index] if index < len(after) else None,
                    }
                )
            else:
                differences.extend(_difference_paths(before[index], after[index], child))
        return differences
    if before != after:
        return [{"path": path, "before": before, "after": after}]
    return []


def _compare_envelopes(before: tuple[Any, ...], after: tuple[Any, ...]) -> dict[str, Any]:
    """Compare evidence values by target while reporting cache identity separately."""
    before_by_id = {str(item.target["id"]): _plain(item) for item in before}
    after_by_id = {str(item.target["id"]): _plain(item) for item in after}
    before_ids, after_ids = set(before_by_id), set(after_by_id)
    changed = []
    cache_identity_changed = []
    unchanged = []
    for target_id in sorted(before_ids | after_ids):
        old, new = before_by_id.get(target_id), after_by_id.get(target_id)
        if old is None or new is None:
            changed.append(
                {
                    "target_id": target_id,
                    "presence": "added" if old is None else "removed",
                    "changed_fields": ["target_presence"],
                    "field_differences": [],
                    "cache_identity_changed": True,
                    "cache_identity_before": old.get("cache_identity") if old else None,
                    "cache_identity_after": new.get("cache_identity") if new else None,
                }
            )
            cache_identity_changed.append(target_id)
            continue

        field_differences = []
        changed_fields = []
        for field in EVIDENCE_FIELDS:
            differences = _difference_paths(old.get(field), new.get(field), field)
            if differences:
                changed_fields.append(field)
                field_differences.extend(differences)
        identity_diff = old.get("cache_identity") != new.get("cache_identity")
        if identity_diff:
            cache_identity_changed.append(target_id)
        if changed_fields:
            changed.append(
                {
                    "target_id": target_id,
                    "presence": "both",
                    "changed_fields": changed_fields,
                    "field_differences": field_differences,
                    "cache_identity_changed": identity_diff,
                    "cache_identity_before": old.get("cache_identity"),
                    "cache_identity_after": new.get("cache_identity"),
                }
            )
        else:
            unchanged.append(target_id)

    return {
        "baseline_target_count": len(before_ids),
        "rotated_target_count": len(after_ids),
        "added_target_ids": sorted(after_ids - before_ids),
        "removed_target_ids": sorted(before_ids - after_ids),
        "evidence_changed_target_ids": [item["target_id"] for item in changed],
        "evidence_unchanged_target_ids": unchanged,
        "cache_identity_changed_target_ids": cache_identity_changed,
        "target_differences": changed,
    }


def _select_target(description: Mapping[str, Any]) -> tuple[str, tuple[float, float]]:
    """Choose the first stable-ID group with projected geometry and a rotation center."""
    candidates = sorted(
        (group for group in description.get("group_geometry", ()) if _group_points(group)),
        key=lambda group: str(group.get("target_id")),
    )
    for group in candidates:
        center = group.get("center")
        if center is not None:
            return str(group["target_id"]), (float(center[0]), float(center[1]))
    raise RuntimeError("no authored furniture group has usable geometry and a center")


def _artifact_self_check(run_dir: Path, report: Mapping[str, Any]) -> None:
    """Verify emitted JSON, SVG, and target-difference counts before reporting success."""
    for name in (
        "baseline_geometry_relation_envelopes.json",
        "rotated_geometry_relation_envelopes.json",
        "baseline_trend_alignment_envelopes.json",
        "rotated_trend_alignment_envelopes.json",
        "recompute_report.json",
    ):
        with (run_dir / name).open(encoding="utf-8") as stream:
            json.load(stream)
    for name in ("baseline_plan.svg", "rotated_plan.svg"):
        ET.parse(run_dir / name)
    for package in ("geometry_relation", "trend_alignment"):
        summary = report["comparisons"][package]
        assert summary["cache_identity_changed_target_ids"]
        assert summary["evidence_changed_target_ids"]
        assert len(summary["target_differences"]) == len(summary["evidence_changed_target_ids"])


def run(source_path: Path, output_root: Path) -> Path:
    """Recompute both packages around one 17-degree in-memory group rotation."""
    before_source = _fingerprint(source_path)
    if (
        before_source["byte_length"] != EXPECTED_SOURCE_BYTES
        or before_source["sha256"] != EXPECTED_SOURCE_SHA256
    ):
        raise RuntimeError("IFC source does not match the pinned recomputation input")

    baseline_scene, metadata, authored = _build_scene(source_path, group_limit=2)
    if len(authored) != 2:
        raise RuntimeError("the pinned IFC must contain at least two authored furniture groups")
    after_extract = _fingerprint(source_path)
    if after_extract != before_source:
        raise RuntimeError("pinned IFC changed during scene extraction")

    baseline_description = describe_group_relations(baseline_scene)
    selected_target, rotation_center = _select_target(baseline_description)
    rotated_scene = _rotate_scene_geometry(
        baseline_scene, selected_target, rotation_center, ROTATION_DEGREES
    )
    rotated_description = describe_group_relations(rotated_scene)
    geometry_query = FieldQuery(
        frame=baseline_scene.context.analysis_plane.name,
        plane=baseline_scene.context.analysis_plane,
        tolerance=baseline_scene.context.geometry_tolerance,
        revision=GEOMETRY_ALGORITHM,
    )
    trend_query = FieldQuery(
        frame=baseline_scene.context.analysis_plane.name,
        plane=baseline_scene.context.analysis_plane,
        tolerance=baseline_scene.context.geometry_tolerance,
        revision="group-trend-alignment-v1",
    )
    baseline_input = _scene_fingerprint(baseline_scene)
    rotated_input = _scene_fingerprint(rotated_scene)
    if baseline_input == rotated_input:
        raise AssertionError("in-memory rotation did not change the scene input fingerprint")

    # Keep source, query, recipe, and algorithm fixed so this isolates scene-content effects.
    baseline_envelopes = _build_envelopes(
        baseline_scene,
        geometry_query=geometry_query,
        trend_query=trend_query,
        source_sha256=str(before_source["sha256"]),
        input_fingerprint=baseline_input,
    )
    rotated_envelopes = _build_envelopes(
        rotated_scene,
        geometry_query=geometry_query,
        trend_query=trend_query,
        source_sha256=str(before_source["sha256"]),
        input_fingerprint=rotated_input,
    )
    if not baseline_envelopes["geometry_relation"] or not baseline_envelopes["trend_alignment"]:
        raise RuntimeError("one or both evidence builders returned no baseline envelopes")
    if selected_target not in {str(item.target["id"]) for item in baseline_envelopes["trend_alignment"]}:
        raise RuntimeError("selected rotation target is absent from trend evidence")

    comparisons = {
        package: _compare_envelopes(baseline_envelopes[package], rotated_envelopes[package])
        for package in ("geometry_relation", "trend_alignment")
    }
    run_dir = output_root / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%S.%fZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    for package, filename in (
        ("geometry_relation", "geometry_relation"),
        ("trend_alignment", "trend_alignment"),
    ):
        package_schema = (
            GEOMETRY_PACKAGE_SCHEMA if package == "geometry_relation" else TREND_PACKAGE_SCHEMA
        )
        for label, source_envelopes in (
            ("baseline", baseline_envelopes),
            ("rotated", rotated_envelopes),
        ):
            _write(
                run_dir / f"{label}_{filename}_envelopes.json",
                {
                    "schema": package_schema,
                    "source": before_source,
                    "scene_input_fingerprint": baseline_input if label == "baseline" else rotated_input,
                    "query": geometry_query if package == "geometry_relation" else trend_query,
                    "envelopes": source_envelopes[package],
                },
            )

    plane = _plain(baseline_scene.context.analysis_plane)
    note = "Actual geometry and trend envelope recomputation; IFC source read-only."
    for label, description, angle in (
        ("baseline", baseline_description, 0.0),
        ("rotated", rotated_description, ROTATION_DEGREES),
    ):
        svg = _plan_svg(
            description,
            source=before_source,
            plane=plane,
            state=label,
            selected_target=selected_target,
            rotation_degrees=angle,
            footer_note=note,
        )
        (run_dir / f"{label}_plan.svg").write_text(svg, encoding="utf-8")

    final_source = _fingerprint(source_path)
    if final_source != before_source:
        raise RuntimeError("pinned IFC changed during evidence recomputation or artifact writing")
    report = {
        "schema": SCHEMA,
        "source_before": before_source,
        "source_after_extraction": after_extract,
        "source_final": final_source,
        "source_unchanged": before_source == after_extract == final_source,
        "read_only_ifc": True,
        "synthetic_input": False,
        "authored_group_count": len(authored),
        "source_authored_group_count": metadata["source_authored_furniture_group_count"],
        "selected_group_ids": [group.id for group in authored],
        "scene_scope": "two stable-ID authored furniture groups and their direct members",
        "selection": metadata.get("selection"),
        "analysis_plane": plane,
        "rotation": {
            "target_id": selected_target,
            "degrees": ROTATION_DEGREES,
            "in_memory_only": True,
            "baseline_scene_input_fingerprint": baseline_input,
            "rotated_scene_input_fingerprint": rotated_input,
            "source_fingerprint_held_constant": str(before_source["sha256"]),
        },
        "recomputed_packages": {
            "geometry_relation": {
                "builder": "features.group_geometry_relation_field.build_group_geometry_relation_envelopes",
                "channels": ["boundary_gap", "contact", "positive_area_overlap"],
                "member_pair_role": "audit_only_group_aggregation_deferred",
            },
            "trend_alignment": {
                "builder": "features.group_trend_alignment_field.build_group_trend_alignment_envelopes",
                "channels": ["overall_group_axis", "layout_axis"],
                "suppressed_channels": ["member_frame", "member_axis"],
            },
        },
        "potential_or_strength_package": {
            "computed": False,
            "reason": "No potential/strength builder is present in this recomputation scope.",
        },
        "comparisons": comparisons,
        "artifacts": {
            "baseline_plan_svg": str((run_dir / "baseline_plan.svg").resolve()),
            "rotated_plan_svg": str((run_dir / "rotated_plan.svg").resolve()),
            "baseline_geometry_relation_envelopes": str(
                (run_dir / "baseline_geometry_relation_envelopes.json").resolve()
            ),
            "rotated_geometry_relation_envelopes": str(
                (run_dir / "rotated_geometry_relation_envelopes.json").resolve()
            ),
            "baseline_trend_alignment_envelopes": str(
                (run_dir / "baseline_trend_alignment_envelopes.json").resolve()
            ),
            "rotated_trend_alignment_envelopes": str(
                (run_dir / "rotated_trend_alignment_envelopes.json").resolve()
            ),
            "report": str((run_dir / "recompute_report.json").resolve()),
        },
    }
    _write(run_dir / "recompute_report.json", report)
    _artifact_self_check(run_dir, report)
    return run_dir


def main() -> None:
    """Run the pinned real-IFC recomputation and print its artifact directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--ifc", type=Path, default=DEFAULT_IFC)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "outputs/design/group_evidence_actual_recompute_ifc",
    )
    args = parser.parse_args()
    run_dir = run(args.ifc.resolve(), args.output_root.resolve())
    print(json.dumps({"status": "pass", "run_dir": str(run_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
