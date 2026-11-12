"""Compare actual reciprocal and fixed-floor linear processed outputs on retained IFC evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from features.field_core import EvidencePackageOutput, EvidenceProcessedOutput, _json_value
from features.group_distance_evidence_package import (
    build_euclidean_linear_proximity_processor, build_group_distance_evidence_package,
)
from scripts.design.group_level import run_group_distance_processed_ifc as trial


ROOT = Path(__file__).resolve().parents[3]
LIMITS = ("Scope-relative trial, sensitive to observed extrema; 0.01 is a chosen convention. "
          "No physical attenuation, cross-scene calibration or potential integration. "
          "Freshness covers authenticated retained context; live scene currentness was not observed.")


def build_comparison_rows(
    raw: EvidencePackageOutput, reciprocal: EvidenceProcessedOutput, linear: EvidenceProcessedOutput,
) -> list[dict[str, Any]]:
    """Join both actual processed ports to unchanged raw metres and reject foreign bindings."""
    if (linear.error_code is not None or linear.package_id != reciprocal.package_id
            or linear.raw_output_identity != reciprocal.raw_output_identity
            or linear.raw_payload_fingerprint != reciprocal.raw_payload_fingerprint):
        raise ValueError("both processed results must bind the same raw producer payload")
    # The existing row adapter authenticates raw identity and content before any plotting handoff.
    reciprocal_rows = trial.build_processed_rows(raw, reciprocal)
    outputs = {item.target["identity"]: item for item in linear.outputs}
    if (set(outputs) != {row["pair_id"] for row in reciprocal_rows}
            or any(item.channel != "euclidean_linear_relative_proximity" for item in linear.outputs)):
        raise ValueError("both processed results must cover the same raw Euclidean target scope")
    rows = []
    for original in reciprocal_rows:
        item = outputs[original["pair_id"]]
        rows.append({"pair_id": original["pair_id"], "group_a_id": original["group_a_id"],
                     "group_b_id": original["group_b_id"], "distance_m": original["distance_m"],
                     "reciprocal_proximity": original["proximity"], "linear_proximity": item.observation,
                     "median_distance_m": original["median_distance_m"],
                     "minimum_distance_m": item.provenance["minimum_distance_m"],
                     "maximum_distance_m": item.provenance["maximum_distance_m"],
                     "floor": item.provenance["floor"], "status": item.status.value,
                     "raw_channel_ref": original["raw_channel_ref"], "lineage_scope": original["lineage_scope"]})
    return rows


def _write_curves(rows: list[dict[str, Any]], output_dir: Path) -> None:
    """Plot all supplied processed observations against their actual raw distances."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ordered = sorted(rows, key=lambda row: row["distance_m"])
    figure, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
    for key, label, color in (("reciprocal_proximity", "Reciprocal: m/(m+d)", "#2166ac"),
                              ("linear_proximity", "Linear: floor 0.01", "#b2182b")):
        axis.plot([row["distance_m"] for row in ordered], [row[key] for row in ordered],
                  color=color, linewidth=1, marker=".", markersize=3, label=label)
    axis.set(xlabel="Raw Euclidean distance (m)", ylabel="Processed relative proximity [0,1]",
             xlim=(0, max(row["distance_m"] for row in rows) * 1.02), ylim=(0, 1),
             title="Actual processed ports: all 666 retained IFC pairs")
    axis.grid(color="#dddddd", linewidth=0.5)
    axis.legend()
    figure.savefig(output_dir / "curves.png", dpi=160)
    plt.close(figure)


def _write_overview(inputs, rows: list[dict[str, Any]], output_dir: Path) -> None:
    """Compare the same retained reference group on one absolute color ruler."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    group_ids = sorted(inputs.geometries)
    source = group_ids[0]
    selected = {row["group_b_id"] if row["group_a_id"] == source else row["group_a_id"]: row
                for row in rows if source in (row["group_a_id"], row["group_b_id"])}
    figure, axes = plt.subplots(1, 2, figsize=(15, 8), constrained_layout=True)
    cmap = plt.get_cmap("cividis")
    for axis, key, label in zip(axes, ("reciprocal_proximity", "linear_proximity"),
                                ("Reciprocal: m/(m+d)", "Linear: fixed trial floor 0.01")):
        for number, identity in enumerate(group_ids, 1):
            # Reuse the retained hole-aware union renderer; color only supplied processed outputs.
            trial._draw_union(axis, inputs.geometries[identity],
                              fill="white" if identity == source else cmap(selected[identity][key]),
                              source=identity == source)
            center = inputs.geometries[identity].centroid
            axis.text(center.x, center.y, f"{number:02d}", fontsize=8, ha="center", va="center",
                      color="#c62828" if identity == source else "white",
                      bbox={"facecolor": "white" if identity == source else "#333333", "alpha": 0.8,
                            "pad": 1, "edgecolor": "none"})
        axis.autoscale_view()
        axis.margins(0.05)
        axis.set(aspect="equal", xlabel="Analysis-plane X (m)", ylabel="Analysis-plane Y (m)", title=label)
    figure.colorbar(ScalarMappable(norm=Normalize(0, 1), cmap=cmap), ax=list(axes), fraction=0.025,
                    pad=0.02, label="Relative proximity [0,1]; larger is closer")
    figure.suptitle("Same actual IFC reference group 01 (red hatch), 36 observed targets\n"
                   f"Common complete scope: 37 groups / 666 pairs; d_min={rows[0]['minimum_distance_m']:.6f} m, "
                   f"d_max={rows[0]['maximum_distance_m']:.6f} m", fontsize=12)
    figure.text(0.5, -0.025, "Linear: s(d)=0.01+0.99*(d_max-d)/(d_max-d_min). Scope-relative and sensitive to extrema.\n"
                "The 0.01 floor is a trial convention; no physical attenuation or cross-scene calibration is claimed.",
                ha="center", fontsize=9)
    figure.savefig(output_dir / "overview.png", dpi=160, bbox_inches="tight")
    figure.savefig(output_dir / "overview.svg", bbox_inches="tight")
    plt.close(figure)


def run_trial(output_dir: Path) -> dict[str, Any]:
    """Authenticate retained inputs once and write a new static comparison directory."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"comparison directory already exists: {output_dir}")
    inputs, raw, reciprocal = trial.load_trial()
    processor = build_euclidean_linear_proximity_processor(expected_target_ids=
        [item.target["identity"] for item in raw.outputs if item.channel == "euclidean_distance"])
    linear = build_group_distance_evidence_package(output_processor=processor).process_output(
        raw, package_freshness=inputs.package_freshness)
    rows = build_comparison_rows(raw, reciprocal, linear)
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "pairs.json").write_text(json.dumps(rows, indent=2, allow_nan=False), encoding="utf-8")
    with (output_dir / "pairs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows({**row, "raw_channel_ref": json.dumps(row["raw_channel_ref"])} for row in rows)
    _write_curves(rows, output_dir)
    _write_overview(inputs, rows, output_dir)
    # Compact shared lineage authenticates the full scope without repeating 666 refs in every export row.
    manifest = {
        "trial": "euclidean-linear-floor-comparison/1", "limits": LIMITS,
        "group_count": len(inputs.geometries), "pair_count": len(rows), "reference_group_id": sorted(inputs.geometries)[0],
        "raw_package_id": raw.package_id, "raw_output_identity": linear.raw_output_identity,
        "raw_payload_fingerprint": linear.raw_payload_fingerprint,
        "retained_context_freshness": inputs.package_freshness,
        "input_hashes": dict(inputs.input_hashes), "source_binding": trial.retained._json_safe(inputs.source_binding),
        "analysis_plane": trial.retained._json_safe(inputs.bundle.analysis_plane),
        "query": _json_value(inputs.bundle.query),
        "query_context": trial.retained._json_safe(inputs.bundle.query_context),
        "minimum_distance_m": rows[0]["minimum_distance_m"], "maximum_distance_m": rows[0]["maximum_distance_m"],
        "floor": 0.01, "median_distance_m": rows[0]["median_distance_m"],
        "runner_sha256": trial.retained.file_hash(Path(__file__)),
        "all_euclidean_raw_channel_refs": [trial.retained._plain_reference(ref) for ref in linear.outputs[0].derived_from],
        "processors": {name: {
            "processing_identity": processed.processing_identity, "processor_id": processed.processor_id,
            "processor_version": processed.processor_version, "parameters": trial.retained._json_safe(processed.parameters),
            "raw_output_identity": processed.raw_output_identity, "raw_payload_fingerprint": processed.raw_payload_fingerprint,
            "channel": processed.outputs[0].channel,
            "scale": {"range": list(processed.outputs[0].scale.value_range), "meaning": processed.outputs[0].scale.meaning,
                      "normalization_method": processed.outputs[0].scale.normalization_method},
        } for name, processed in (("reciprocal", reciprocal), ("linear", linear))},
        "artifacts": {name: trial.retained.file_hash(output_dir / name) for name in
                      ("pairs.json", "pairs.csv", "curves.png", "overview.png", "overview.svg")},
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    return manifest


def main() -> None:
    """Run the bounded comparison in the existing Pixi environment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT /
                        "outputs/design/group_distance_processed_ifc/run_20261112_linear_floor_001_v1")
    args = parser.parse_args()
    manifest = run_trial(args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir), "pair_count": manifest["pair_count"],
                      "minimum_distance_m": manifest["minimum_distance_m"], "maximum_distance_m": manifest["maximum_distance_m"],
                      "processing_identities": {key: value["processing_identity"] for key, value in manifest["processors"].items()}}))


if __name__ == "__main__":
    main()
