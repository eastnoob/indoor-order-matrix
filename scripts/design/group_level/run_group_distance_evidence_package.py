"""Publish a saved group-distance repair as a two-channel evidence package.

The runner has two modes: publish a saved ``global_repair_result`` directly,
or bind an already serialized package output to existing visual artifacts.
Neither mode invokes the distance kernel or regenerates free-space samples.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time
from typing import Any

from features.field_core import evaluate_evidence_package_freshness
from features.group_distance_evidence_package import (
    build_group_distance_package_contract,
    build_group_distance_visualization_manifest,
    evaluate_group_distance_package,
    serialize_group_distance_package_output,
)
from scripts.design.group_level.run_group_distance_ifc import file_hash, retained_input


def _write_json(path: Path, value: Any) -> None:
    """Replace an output only after its complete strict JSON has been written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_package_output(path: Path) -> dict[str, Any]:
    """Read one serialized evidence-package output from disk."""
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    return json.loads(path.read_text(encoding="utf-8"))


def write_visualization_manifest(
    package_output: dict[str, Any],
    output: Path,
    *,
    overview: str | None = None,
    blender: str | None = None,
    preview: str | None = None,
) -> dict[str, Any]:
    """Write artifact bindings for a saved package without recalculating distance."""
    if not isinstance(output, Path):
        raise TypeError("output must be a Path")
    manifest = build_group_distance_visualization_manifest(
        package_output,
        overview=overview,
        blender=blender,
        preview=preview,
    )
    _write_json(output, manifest)
    return manifest


def publish_saved_repair_result(
    input_bundle: Path,
    repair_result: Path,
    output_dir: Path,
    *,
    overview: str | None = None,
    blender: str | None = None,
    preview: str | None = None,
    pair_view_index: Path | None = None,
) -> dict[str, Any]:
    """Adapt one saved repair run and write package, contract, status, and manifest."""
    started = time.perf_counter()
    input_hashes = {str(path.resolve()): file_hash(path) for path in (input_bundle, repair_result)}
    bundle = retained_input(input_bundle)
    repair = json.loads(repair_result.read_text(encoding="utf-8"))
    repair["retained_result_ref"] = {
        "path": str(repair_result.resolve()), "sha256": input_hashes[str(repair_result.resolve())],
        "observation_lookup": "observations[*].pair_id",
    }
    package = evaluate_group_distance_package(bundle, repaired_result=repair)
    serialized = serialize_group_distance_package_output(package)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / "group_distance_package_output.json"
    manifest = build_group_distance_visualization_manifest(
        serialized, overview=overview, blender=blender, preview=preview)
    if pair_view_index is not None:
        index = json.loads(pair_view_index.read_text(encoding="utf-8"))
        pairs = index["pairs"]
        pair_ids = [row["pair_id"] for row in pairs]
        if sorted(pair_ids) != manifest["pair_ids"] or len(set(pair_ids)) != len(pair_ids):
            raise ValueError("Blender pair-view index differs from the package target set")
        if any(index.get("input_hashes", {}).get(path) != expected
               for path, expected in input_hashes.items()):
            raise ValueError("Blender pair-view inputs differ from the retained package inputs")
        # Bind the depicted readings as well as pair names to the actual output.
        by_pair = {pair["pair_id"]: pair for pair in pairs}
        for item in serialized["outputs"]:
            depicted = by_pair[item["target"]["identity"]][item["channel"] + "_m"]
            actual = item["observation"]["value"]
            matches = depicted is None if actual is None else (
                not isinstance(depicted, bool) and isinstance(depicted, (int, float))
                and math.isclose(depicted, actual, rel_tol=1e-12, abs_tol=1e-12))
            if not matches:
                raise ValueError("Blender pair-view distance differs from its package channel")
        manifest["pair_views"] = pairs
        manifest["pair_view_index"] = str(pair_view_index.resolve())
        manifest["visual_input_hashes"] = index["input_hashes"]
    visual_paths = [Path(value) for value in (overview, blender, preview) if value]
    if pair_view_index is not None:
        visual_paths.append(pair_view_index)
    manifest["artifact_hashes"] = {str(path.resolve()): file_hash(path) for path in visual_paths}
    manifest["input_hashes"] = input_hashes
    contract = build_group_distance_package_contract(
        repair, bundle, visualization_manifest=manifest)
    if any(file_hash(Path(path)) != expected for path, expected in input_hashes.items()):
        raise ValueError("retained input bytes changed while preparing the distance package")
    manifest_path = output_dir / "visualization_manifest.json"
    contract_path = output_dir / "package_contract.json"
    _write_json(package_path, serialized)
    _write_json(manifest_path, manifest)
    _write_json(contract_path, contract)
    artifacts = [package_path, manifest_path, contract_path]
    for value in manifest.get("artifact_bindings", {}).values():
        if value:
            artifacts.append(Path(value))
    artifacts_available = all(path.exists() and path.stat().st_size > 0 for path in artifacts)
    status = evaluate_evidence_package_freshness(
        cached_contract=contract, current_contract=contract, artifacts_available=artifacts_available)
    status["freshness_scope"] = "retained input publication; live scene not observed"
    _write_json(output_dir / "package_status.json", status)
    receipt = {
        "output": str(package_path),
        "visualization_manifest": str(manifest_path),
        "package_contract": str(contract_path),
        "package_status": str(output_dir / "package_status.json"),
        "output_identity": serialized.get("output_identity"),
        "pair_count": len({item.get("target", {}).get("identity") for item in serialized.get("outputs", ())}),
        "channel_count": len(serialized.get("outputs", ())),
        "freshness": status.get("freshness"),
        "distance_recomputed": False,
        "publication_seconds": time.perf_counter() - started,
        "input_hashes": input_hashes,
    }
    if any(file_hash(Path(path)) != expected for path, expected in input_hashes.items()):
        raise ValueError("retained input bytes changed while publishing the distance package")
    _write_json(output_dir / "publication_receipt.json", receipt)
    return receipt


def main() -> None:
    """Bind an existing serialized package output to named visual artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-output", type=Path)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--input-bundle", type=Path)
    parser.add_argument("--repair-result", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--overview")
    parser.add_argument("--blender")
    parser.add_argument("--preview")
    parser.add_argument("--pair-view-index", type=Path)
    args = parser.parse_args()
    if args.input_bundle and args.repair_result and args.output_dir:
        print(json.dumps(publish_saved_repair_result(
            args.input_bundle, args.repair_result, args.output_dir,
            overview=args.overview, blender=args.blender, preview=args.preview,
            pair_view_index=args.pair_view_index),
            indent=2, ensure_ascii=False))
        return
    if not args.package_output or not args.manifest_output:
        parser.error("either --input-bundle/--repair-result/--output-dir or --package-output/--manifest-output is required")
    manifest = write_visualization_manifest(
        load_package_output(args.package_output), args.manifest_output,
        overview=args.overview, blender=args.blender, preview=args.preview)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
