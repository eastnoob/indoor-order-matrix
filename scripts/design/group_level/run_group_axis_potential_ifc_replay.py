"""Replay axis-potential aggregation from a verified real-IFC trend artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from features.field_core import (
    FieldResultEnvelope,
    deserialize_field_result_envelope,
    evaluate_evidence_package_freshness,
    serialize_evidence_package_output,
)
from features.group_axis_potential_field import build_group_axis_potential_package
from scripts.design.group_level.run_group_axis_potential_ifc import (
    _aggregate_svg,
    _artifacts_readable,
    _field_metadata,
    _field_svg,
    _package_contract,
)
from scripts.design.group_level.run_group_trend_alignment_field_ifc import _plain


ROOT = Path(__file__).resolve().parents[3]
PINNED_SHA256 = "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"
PINNED_IFC = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
RETAINED_RUN = ROOT / "outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z"


def _load_envelope(payload: dict[str, Any]) -> FieldResultEnvelope:
    """Reconstruct one immutable envelope from the retained JSON contract."""
    return deserialize_field_result_envelope(payload)


def run(retained_run: Path, output_root: Path) -> Path:
    """Validate retained IFC identity, aggregate its envelopes, and render one SVG."""
    source_manifest = json.loads((retained_run / "source_manifest.json").read_text(encoding="utf-8"))
    view_manifest = json.loads((retained_run / "view_manifest.json").read_text(encoding="utf-8"))
    envelopes_payload = json.loads((retained_run / "envelopes.json").read_text(encoding="utf-8"))
    description = json.loads((retained_run / "description.json").read_text(encoding="utf-8"))
    source = source_manifest["source"]
    if source["sha256"] != PINNED_SHA256 or source_manifest["source_after"]["sha256"] != PINNED_SHA256:
        raise RuntimeError("retained artifact does not match the pinned IFC fingerprint")
    if source_manifest["analysis_plane"]["name"] != "ifc-world-plan":
        raise RuntimeError("retained artifact uses an unexpected analysis plane")
    if view_manifest["source"]["sha256"] != PINNED_SHA256:
        raise RuntimeError("retained visualization manifest has a mismatched source fingerprint")
    if envelopes_payload.get("schema") != "group-trend-alignment-envelopes/v1":
        raise RuntimeError("retained envelope schema is not the verified IFC trend schema")
    envelopes = tuple(_load_envelope(item) for item in envelopes_payload["envelopes"])
    result = build_group_axis_potential_package().evaluate(envelopes)
    cell_outputs = [
        output for output in result.outputs if output.target["kind"] == "furniture_group_axis_field_cell"
    ]
    expected_cell_count = len(envelopes) * sum(
        output.channel == "soft_view_direction" for output in result.outputs
    )
    if len(cell_outputs) != expected_cell_count:
        raise AssertionError("source-axis support matrix is not complete for every anchor and scope group")
    relation_outputs = [
        output for output in result.outputs if output.target["kind"] == "furniture_group_pair"
    ]
    relation_pair_ids = {output.target["identity"] for output in relation_outputs}
    source_by_identity = {
        envelope.cache_identity["identity"]: envelope for envelope in envelopes
    }
    if len(result.source_envelopes) != len(envelopes) or any(
        source_by_identity.get(envelope.cache_identity["identity"]) != envelope
        for envelope in result.source_envelopes
    ):
        raise AssertionError("package output did not preserve every source envelope")
    expected_relation_outputs = len(relation_pair_ids) * 4
    if len(relation_outputs) != expected_relation_outputs:
        raise AssertionError("each relation address must expose exactly four channels")
    if any("combined_relation" in output.observation for output in relation_outputs):
        raise AssertionError("combined relation output is outside the reviewed package scope")
    run_dir = output_root / datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "source_reuse.json").write_text(json.dumps({
        "mode": "replay",
        "retained_run": str(retained_run.resolve()),
        "pinned_ifc": str(PINNED_IFC.resolve()),
        "source": source,
        "analysis_plane": source_manifest["analysis_plane"],
        "envelope_count": len(envelopes),
        "note": "Reused verified IFC-derived source envelopes; did not rerun IFC geometry extraction.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name in ("source_manifest.json", "description.json"):
        (run_dir / name).write_bytes((retained_run / name).read_bytes())
    (run_dir / "envelopes.json").write_text(json.dumps({
        "schema": envelopes_payload["schema"],
        "query": envelopes[0].query,
        "envelopes": envelopes,
    }, indent=2, sort_keys=True, default=lambda value: _plain(value)) + "\n", encoding="utf-8")
    (run_dir / "axis_potential_output.json").write_text(json.dumps(serialize_evidence_package_output(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    aggregate = next(output for output in result.outputs if output.channel == "aggregate_direction")
    svg_path = run_dir / "aggregate_axis.svg"
    svg_path.write_text(_aggregate_svg(description, aggregate.observation.get("angle"), source, source_manifest["analysis_plane"]), encoding="utf-8")
    field_views_dir = run_dir / "field_views"
    field_views_dir.mkdir()
    field_cells: dict[str, list[dict[str, Any]]] = {}
    for output in result.outputs:
        if output.target["kind"] != "furniture_group_axis_field_cell":
            continue
        field_cells.setdefault(output.observation["field_id"], []).append(dict(output.observation))
    field_artifacts = []
    profile_by_field = {output.observation["field_id"]: output for output in result.outputs if output.channel == "non_self_profile"}
    direction_by_field = {output.observation["field_id"]: output for output in result.outputs if output.channel == "soft_view_direction"}
    for index, (field_id, cells) in enumerate(sorted(field_cells.items())):
        field_path = field_views_dir / f"field_{index:03d}.svg"
        field_path.write_text(_field_svg(description, field_id, tuple(cells), source, source_manifest["analysis_plane"]), encoding="utf-8")
        statuses = {status: sum(cell["status"] == status for cell in cells) for status in ("computed", "partial", "not_available", "invalid", "ambiguous")}
        field_artifacts.append({
            "field_id": field_id,
            "path": str(field_path.resolve()),
            "anchor_group_id": cells[0]["anchor_group_id"],
            "cell_count": len(cells),
            "cell_status_counts": statuses,
            "profile_status": profile_by_field[field_id].status.value,
            "direction_status": direction_by_field[field_id].status.value,
        })
    (run_dir / "field_view_manifest.json").write_text(json.dumps({
        "schema": "group-axis-potential-field-view-manifest/v1",
        "source": source,
        "analysis_plane": source_manifest["analysis_plane"],
        "fields": field_artifacts,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    matrix, profiles, directions = _field_metadata(result)
    for name, payload in (("field_matrix.json", matrix), ("field_profiles.json", profiles), ("field_directions.json", directions)):
        (run_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (run_dir / "view_manifest.json").write_text(json.dumps({
        "schema": "group-axis-potential-view-manifest/v1",
        "source": source,
        "analysis_plane": source_manifest["analysis_plane"],
        "artifacts": [str(svg_path.resolve())],
        "channel": "aggregate_direction",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    coverage = next(output for output in result.outputs if output.channel == "coverage")
    relation_status_counts = {
        channel: {
            status: sum(
                output.channel == channel and output.status.value == status
                for output in relation_outputs
            )
            for status in ("computed", "not_available")
        }
        for channel in ("axis_angle_gap", "direction_similarity", "clarity_similarity", "clarity_support")
    }
    report = {
        "schema": "group-axis-potential-ifc-replay/v1",
        "output_kind": "axis_potential_evidence_package_output",
        "source": source,
        "retained_run": str(retained_run.resolve()),
        "source_envelopes": len(envelopes),
        "derived_outputs": len(result.outputs),
        "output_channels": [output.channel for output in result.outputs],
        "relation_pair_count": len(relation_pair_ids),
        "relation_output_count": len(relation_outputs),
        "relation_channel_status_counts": relation_status_counts,
        "source_channels_preserved": all(
            "overall_group_axis" in envelope.channel_set
            and tuple(record.channel for record in envelope.value["channels"]) == envelope.channel_set
            for envelope in result.source_envelopes
        ),
        "relation_output_scope": "additive_package_channels",
        "combined_relation_emitted": False,
        "global_resultant_vote": False,
        "aggregate_direction_status": aggregate.status.value,
        "aggregate_direction": aggregate.observation.get("angle"),
        "coverage": _plain(coverage.observation),
        "visualization": str(svg_path.resolve()),
        "field_view_count": len(field_artifacts),
        "field_view_manifest": str((run_dir / "field_view_manifest.json").resolve()),
        "field_cell_count": len(field_cells) * len(envelopes),
        "field_cell_expected_count": expected_cell_count,
        "field_matrix": "field_matrix.json",
        "field_profiles": "field_profiles.json",
        "field_directions": "field_directions.json",
        "package_contract": "package_contract.json",
        "package_status": "package_status.json",
        "scope_status": "diagnostic_scope_replay",
        "package_output_active": True,
        "synthetic_input": False,
        "layout_axis_used": False,
        "ifc_extraction_rerun": False,
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    visualizations = tuple(sorted(
        str(Path(item["path"]).relative_to(run_dir.resolve())) for item in field_artifacts
    )) + ("aggregate_axis.svg",)
    contract = _package_contract(
        description,
        envelopes,
        envelopes[0].query,
        source_manifest["analysis_plane"],
        str(source["sha256"]),
        visualizations,
        result,
    )
    (run_dir / "package_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_paths = [
        path for value in contract["artifacts"].values()
        for path in (value if isinstance(value, list) else [value])
    ] + ["package_contract.json"]
    package_status = evaluate_evidence_package_freshness(
        cached_contract=contract,
        current_contract=contract,
        artifacts_available=_artifacts_readable(run_dir, artifact_paths),
    )
    (run_dir / "package_status.json").write_text(json.dumps(package_status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run_dir


def main() -> None:
    """Replay the verified pinned-IFC artifact and print its output directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--retained-run", type=Path, default=RETAINED_RUN)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/design/group_axis_potential_ifc")
    args = parser.parse_args()
    run_dir = run(args.retained_run.resolve(), args.output_root.resolve())
    print(json.dumps({"status": "pass", "run_dir": str(run_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
