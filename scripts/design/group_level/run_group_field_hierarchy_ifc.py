"""Replay the retained real-IFC axis package with its direction hierarchy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from features.field_core import evaluate_evidence_package_freshness, serialize_evidence_package_output
from features.group_axis_potential_field import build_group_axis_potential_package
from scripts.design.group_level.run_group_axis_potential_ifc import (
    _aggregate_svg,
    _artifacts_readable,
    _field_metadata,
    _field_svg,
    _package_contract,
)
from scripts.design.group_level.run_group_axis_potential_ifc_replay import _load_envelope
from scripts.design.group_level.run_group_trend_alignment_field_ifc import _plain


ROOT = Path(__file__).resolve().parents[3]
PINNED_SHA256 = "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"
SCHEMA = "group-axis-field-hierarchy-ifc-replay/v1"
HIERARCHY_RECIPE = "source-axis-circular-arc-lt90-v1"
HIERARCHY_SCHEMA = "group-axis-field-hierarchy-output/v1"
RETAINED_RUN = ROOT / "outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z"


def _read(path: Path) -> Any:
    """Read one retained JSON artifact without rewriting its source bytes."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    """Write deterministic strict JSON for a replay artifact."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=_plain) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    """Return the SHA-256 of the bytes consumed or emitted by the runner."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _output_rows(result: Any, channel: str) -> list[dict[str, Any]]:
    """Serialize all package rows for one hierarchy channel."""
    return [_plain(output.observation) for output in result.outputs if output.channel == channel]


def _family_artifacts(result: Any, description: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build family matrices and the hierarchy view index from one package evaluation."""
    definitions = {row["family_id"]: row for row in _output_rows(result, "axis_family_definition")}
    supports = _output_rows(result, "axis_family_support")
    profiles = {row["family_id"]: row for row in _output_rows(result, "axis_family_profile")}
    directions = {row["family_id"]: row for row in _output_rows(result, "axis_family_direction")}
    residuals = _output_rows(result, "axis_family_residual")
    groups = sorted(item["target_id"] for item in description.get("group_geometry", ()))
    cells: dict[str, list[dict[str, Any]]] = {family_id: [] for family_id in definitions}
    for row in supports:
        cells.setdefault(row["family_id"], []).append(row)
    family_matrix = {
        "schema": "group-axis-potential-family-matrix/v1",
        "groups": groups,
        "families": {
            family_id: {
                "family_id": family_id,
                "anchor_group_ids": definition["anchor_group_ids"],
                "leaf_field_ids": definition["leaf_field_ids"],
                "birth": definition["birth"],
                "death": definition["death"],
                "birth_exact": definition["birth_exact"],
                "death_exact": definition["death_exact"],
                "scale_persistence": definition["scale_persistence"],
                "cells": sorted(cells.get(family_id, ()), key=lambda row: row["group_id"]),
            }
            for family_id, definition in sorted(definitions.items())
        },
    }
    hierarchy = {
        "schema": HIERARCHY_SCHEMA,
        "recipe": HIERARCHY_RECIPE,
        "families": [definitions[key] for key in sorted(definitions)],
        "direction_aliases": _output_rows(result, "axis_direction_aliases"),
        "residuals": residuals,
        "scope": _output_rows(result, "axis_family_scope_diagnostics"),
    }
    family_views = {
        "schema": "group-axis-family-view-manifest/v1",
        "families": [
            {
                "family_id": family_id,
                "family_index": index,
                "view_id": f"family-{hashlib.sha256(family_id.encode()).hexdigest()[:16]}",
                "view_ref": f"index.html#family={quote(family_id, safe='')}",
                "anchor_group_ids": family_matrix["families"][family_id]["anchor_group_ids"],
                "leaf_field_ids": family_matrix["families"][family_id]["leaf_field_ids"],
                "birth": family_matrix["families"][family_id]["birth"],
                "death": family_matrix["families"][family_id]["death"],
                "cell_count": len(family_matrix["families"][family_id]["cells"]),
            }
            for index, family_id in enumerate(sorted(definitions))
        ],
    }
    return hierarchy, family_matrix, profiles, directions, family_views


def _tree_hashes(root: Path) -> dict[str, str]:
    """Fingerprint every retained artifact without opening the source IFC."""
    return {path.relative_to(root).as_posix(): _sha(path) for path in sorted(root.rglob("*")) if path.is_file()}


def _target_index(result: Any, field_indexes: dict[str, int], family_views: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Map every package output target to its leaf, family, or overview view."""
    rows: list[dict[str, Any]] = []
    for output in result.outputs:
        observation = _plain(output.observation)
        target = dict(output.target)
        row = {"target_identity": target["identity"], "target_kind": target["kind"], "channel": output.channel}
        if output.channel == "axis_field_support":
            field_id, group_id = observation["field_id"], observation["target_group_id"]
            row.update({"view_kind": "leaf", "field_id": field_id, "group_id": group_id, "field_index": field_indexes[field_id], "view_ref": f"index.html#leaf={quote(field_id, safe='')}&group={quote(group_id, safe='')}"})
        elif output.channel == "axis_family_support":
            family_id, group_id = observation["family_id"], observation["group_id"]
            row.update({"view_kind": "family", "family_id": family_id, "family_index": family_views[family_id]["family_index"], "group_id": group_id, "view_ref": f"index.html#family={quote(family_id, safe='')}&group={quote(group_id, safe='')}"})
        elif "family_id" in observation:
            family_id = observation["family_id"]
            row.update({"view_kind": "family", "family_id": family_id, "family_index": family_views[family_id]["family_index"], "view_ref": family_views[family_id]["view_ref"]})
        elif "field_id" in observation:
            field_id = observation["field_id"]
            row.update({"view_kind": "leaf", "field_id": field_id, "field_index": field_indexes[field_id], "view_ref": f"index.html#leaf={quote(field_id, safe='')}"})
        else:
            row.update({"view_kind": "overview", "view_ref": "index.html#overview"})
        rows.append(row)
    return rows


def run(retained_run: Path, output_root: Path) -> Path:
    """Replay retained envelopes into a new hierarchy directory without loading IFC."""
    if output_root.exists():
        raise FileExistsError(f"output root already exists: {output_root}")
    retained_abs, output_abs = retained_run.resolve(), output_root.resolve()
    if output_abs.is_relative_to(retained_abs):
        raise ValueError("output root must be outside the retained source run")
    required = (
        "source_manifest.json",
        "description.json",
        "envelopes.json",
        "axis_potential_output.json",
        "field_matrix.json",
        "field_profiles.json",
        "field_directions.json",
        "field_view_manifest.json",
        "view_manifest.json",
        "source_reuse.json",
    )
    if any(not (retained_run / name).is_file() for name in required):
        raise FileNotFoundError("retained axis replay is missing a required artifact")
    source_manifest = _read(retained_run / "source_manifest.json")
    source = source_manifest["source"]
    if source["sha256"] != PINNED_SHA256 or source_manifest["source_after"]["sha256"] != PINNED_SHA256:
        raise RuntimeError("retained artifact does not match the pinned IFC fingerprint")
    if not source_manifest.get("project_global_id"):
        raise RuntimeError("retained source manifest has no top-level project_global_id")
    if source_manifest["analysis_plane"].get("name") != "ifc-world-plan":
        raise RuntimeError("retained artifact uses an unexpected analysis plane")
    before = _tree_hashes(retained_run)
    envelope_payload = _read(retained_run / "envelopes.json")
    if envelope_payload.get("schema") != "group-trend-alignment-envelopes/v1":
        raise RuntimeError("retained envelope schema is not the verified IFC trend schema")
    envelopes = tuple(_load_envelope(item) for item in envelope_payload["envelopes"])
    namespace = f"ifc-project:{source_manifest['project_global_id']}"
    result = build_group_axis_potential_package(scene_namespace=namespace).evaluate(envelopes)
    description = _read(retained_run / "description.json")
    original_output = _read(retained_run / "axis_potential_output.json")
    original_matrix = _read(retained_run / "field_matrix.json")
    original_profiles = _read(retained_run / "field_profiles.json")
    original_directions = _read(retained_run / "field_directions.json")
    original_field_manifest = _read(retained_run / "field_view_manifest.json")
    original_view_manifest = _read(retained_run / "view_manifest.json")
    original_reuse = _read(retained_run / "source_reuse.json")
    plane = source_manifest["analysis_plane"]
    if original_reuse["source"]["sha256"] != PINNED_SHA256 or original_reuse["analysis_plane"] != plane:
        raise RuntimeError("retained source-reuse metadata does not match the pinned source and plane")
    if original_view_manifest["source"]["sha256"] != PINNED_SHA256 or original_view_manifest["analysis_plane"] != plane:
        raise RuntimeError("retained aggregate view does not match the pinned source and plane")
    if original_field_manifest["source"]["sha256"] != PINNED_SHA256 or original_field_manifest["analysis_plane"] != plane:
        raise RuntimeError("retained field views do not match the pinned source and plane")
    group_ids = {item["target_id"] for item in description.get("group_geometry", ())}
    if len(envelopes) != 37 or len(group_ids) != 37 or description.get("analysis_frame") is None:
        raise RuntimeError("retained description and envelopes do not contain the complete 37-group scope")
    if any(_plain(envelope.query.plane) != plane or envelope.query.frame != description["analysis_frame"]["plane"] for envelope in envelopes):
        raise RuntimeError("retained envelopes do not share the description analysis frame and plane")
    if {cell["target_group_id"] for field in original_matrix["fields"].values() for cell in field["cells"]} != group_ids:
        raise RuntimeError("retained leaf matrix and geometry do not have the same full scope")
    original_ids = {item["cache_identity"]["identity"] for item in original_output["source_envelopes"]}
    if original_ids != {envelope.cache_identity["identity"] for envelope in envelopes}:
        raise RuntimeError("retained package output does not preserve the envelope identities")
    serialized_result = serialize_evidence_package_output(result)
    original_rows = {(item["target"]["identity"], item["channel"]): item for item in original_output["outputs"]}
    replayed_rows = {(item["target"]["identity"], item["channel"]): item for item in serialized_result["outputs"]}
    if any(replayed_rows.get(key) != value for key, value in original_rows.items()):
        raise RuntimeError("hierarchy mode changed a retained legacy output")
    field_matrix, field_profiles, field_directions = _field_metadata(result)
    if field_matrix != original_matrix or field_profiles != original_profiles or field_directions != original_directions:
        raise RuntimeError("hierarchy mode changed a retained leaf matrix, profile, or direction")
    hierarchy, family_matrix, family_profiles, family_directions, family_view_manifest = _family_artifacts(result, description)
    output_root.mkdir(parents=True, exist_ok=False)
    (output_root / "source_manifest.json").write_bytes((retained_run / "source_manifest.json").read_bytes())
    (output_root / "description.json").write_bytes((retained_run / "description.json").read_bytes())
    (output_root / "envelopes.json").write_bytes((retained_run / "envelopes.json").read_bytes())
    _write(output_root / "axis_potential_output.json", serialized_result)
    _write(output_root / "hierarchy.json", hierarchy)
    _write(output_root / "family_matrix.json", family_matrix)
    _write(output_root / "family_profiles.json", {"schema": "group-axis-potential-family-profiles/v1", "profiles": family_profiles})
    _write(output_root / "family_directions.json", {"schema": "group-axis-potential-family-directions/v1", "directions": family_directions})

    aggregate = next(output for output in result.outputs if output.channel == "aggregate_direction")
    aggregate_path = output_root / "aggregate_axis.svg"
    aggregate_path.write_text(_aggregate_svg(description, aggregate.observation.get("angle"), source, plane), encoding="utf-8")
    field_views = output_root / "field_views"
    field_views.mkdir()
    field_entries = []
    for index, (field_id, payload) in enumerate(sorted(field_matrix["fields"].items())):
        path = field_views / f"field_{index:03d}.svg"
        path.write_text(_field_svg(description, field_id, tuple(payload["cells"]), source, plane), encoding="utf-8")
        field_entries.append({"field_id": field_id, "path": str(path.resolve()), "anchor_group_id": payload["anchor_group_id"], "cell_count": len(payload["cells"])})
    family_entries = family_view_manifest["families"]
    _write(output_root / "field_matrix.json", field_matrix)
    _write(output_root / "field_profiles.json", field_profiles)
    _write(output_root / "field_directions.json", field_directions)
    _write(output_root / "field_view_manifest.json", {"schema": "group-axis-potential-field-view-manifest/v1", "source": source, "analysis_plane": plane, "fields": field_entries})
    _write(output_root / "family_view_manifest.json", {**family_view_manifest, "source": source, "analysis_plane": plane, "families": family_entries})

    targets = []
    for entry in field_entries:
        targets.append({"kind": "leaf", "id": entry["field_id"], "path": entry["path"], "cell_count": entry["cell_count"]})
    for entry in family_entries:
        targets.append({"kind": "family", "id": entry["family_id"], "family_index": entry["family_index"], "view_id": entry["view_id"], "view_ref": entry["view_ref"], "cell_count": entry["cell_count"]})
    field_indexes = {entry["field_id"]: index for index, entry in enumerate(field_entries)}
    family_by_id = {entry["family_id"]: entry for entry in family_entries}
    target_index = _target_index(result, field_indexes, family_by_id)
    view_manifest = {
        "schema": "group-axis-field-hierarchy-view-manifest/v1",
        "source": source,
        "analysis_plane": plane,
        "scene_namespace": namespace,
        "targets": targets,
        "target_index": target_index,
        "leaf_count": len(field_entries),
        "family_count": len(family_entries),
        "cell_count": sum(item["cell_count"] for item in field_entries) + sum(item["cell_count"] for item in family_entries),
        "artifacts": ["aggregate_axis.svg", "field_views", "index.html"],
    }
    _write(output_root / "view_manifest.json", view_manifest)
    _write(output_root / "source_reuse.json", {
        "schema": "group-axis-field-hierarchy-source-reuse/v1",
        "mode": "retained-replay",
        "retained_run": str(retained_run.resolve()),
        "project_global_id": source_manifest["project_global_id"],
        "source": source,
        "analysis_plane": plane,
        "scene_namespace": namespace,
        "retained_inputs": [{"path": name, "sha256": digest} for name, digest in sorted(before.items())],
        "retained_source_reuse": original_reuse,
        "ifc_extraction_rerun": False,
        "synthetic_input": False,
    })
    report = {
        "schema": SCHEMA,
        "retained_run": str(retained_run.resolve()),
        "project_global_id": source_manifest["project_global_id"],
        "source": source,
        "source_after": source_manifest["source_after"],
        "analysis_plane": plane,
        "scene_namespace": namespace,
        "source_scope_count": len(envelopes),
        "leaf_field_count": len(field_entries),
        "leaf_cell_count": sum(item["cell_count"] for item in field_entries),
        "legacy_output_count": len(original_output["outputs"]),
        "derived_output_count": len(result.outputs),
        "family_count": len(family_entries),
        "family_cell_count": sum(len(item["cells"]) for item in family_matrix["families"].values()),
        "hierarchy_output_count": len(result.outputs) - len(original_output["outputs"]),
        "axis_direction_class_count": len(hierarchy["direction_aliases"]),
        "residual_edge_count": len(hierarchy["residuals"]),
        "scope_diagnostics_count": len(hierarchy["scope"]),
        "output_channels": sorted({output.channel for output in result.outputs}),
        "ifc_extraction_rerun": False,
        "synthetic_input": False,
        "real_world_cluster_validity": False,
        "live_ui": False,
        "observed_status_counts": {
            channel: {
                status: sum(output.channel == channel and output.status.value == status for output in result.outputs)
                for status in ("computed", "partial", "not_available", "invalid", "ambiguous")
            }
            for channel in sorted({output.channel for output in result.outputs})
        },
        "exact_event_pairs": sorted({tuple(row[key]) for row in hierarchy["families"] for key in ("birth_exact", "death_exact")}),
        "uncovered_scenarios": ["unseen singleton/two-anchor shapes, missing or invalid source axes, zero clarity, direction cancellation, exact event ties, and other analysis planes require separate observed data or algebraic tests"],
        "target_index_count": len(target_index),
        "package_contract": "package_contract.json",
        "package_status": "package_status.json",
    }
    _write(output_root / "report.json", report)
    visualizations = tuple(
        ["aggregate_axis.svg"]
        + [str(Path(item["path"]).relative_to(output_root.resolve())) for item in field_entries]
    )
    contract = _package_contract(description, envelopes, envelopes[0].query, plane, source["sha256"], visualizations, result, scene_namespace=namespace)
    contract["artifacts"].update({
        "source_reuse": "source_reuse.json",
        "hierarchy": "hierarchy.json",
        "family_matrix": "family_matrix.json",
        "family_profiles": "family_profiles.json",
        "family_directions": "family_directions.json",
        "family_view_manifest": "family_view_manifest.json",
    })
    _write(output_root / "package_contract.json", contract)
    artifact_paths = [
        path
        for value in contract["artifacts"].values()
        for path in ([value] if isinstance(value, str) else value if isinstance(value, list) else ())
        if isinstance(path, str)
    ] + ["package_contract.json"]
    _write(output_root / "package_status.json", evaluate_evidence_package_freshness(
        cached_contract=contract,
        current_contract=contract,
        artifacts_available=_artifacts_readable(output_root, artifact_paths),
    ))
    if _sha(retained_run / "source_manifest.json") != before["source_manifest.json"]:
        raise RuntimeError("retained source changed during hierarchy replay")
    return output_root


def main() -> None:
    """Run the retained hierarchy replay and print its exact output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retained-run", type=Path, default=RETAINED_RUN)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({"status": "pass", "output": str(run(args.retained_run.resolve(), args.output_root.resolve()))}, sort_keys=True))


if __name__ == "__main__":
    main()
