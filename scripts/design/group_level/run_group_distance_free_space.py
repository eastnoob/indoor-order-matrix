"""Calculate group distances from one exact, externally accepted free-space result."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict
from pathlib import Path
import math
import shutil
import time

from adapters import blender_analysis_result_wire as wire
from adapters.free_space_distance import distance_input_from_free_space
from features.field_core import _json_value
from features.group_distance import calculate_group_pair_distances, serialize_group_distance_result
from scripts.design.group_level.run_group_distance_ifc import (
    file_hash, normalized_hash, process_memory, read_json, retained_input, validate_result, write_json,
)


def load_json(path: Path) -> dict:
    """Read finite JSON through the same public wire loader as downstream consumers."""
    return wire.load_json(path.read_text(encoding="utf-8"))


def retained_read_context(native_request: dict, receipt: dict) -> tuple:
    """Bind the exact reference using producer inputs and external publication evidence.

    A retained receipt proves its recorded native publication instant. This
    diagnostic deliberately reads historical data; it cannot observe the live
    Blender session or upgrade a saved publication to current.
    """
    request = native_request["request"]
    original_binding = native_request["job_binding"]
    observation = receipt["current_observation"]
    binding = observation["binding"]
    reference = receipt["result_ref"]
    if (native_request["kind"] != reference["kind"] or reference["kind"] != "free_space_run"
            or receipt["lifecycle"] != "complete" or receipt["freshness"] != "current"
            or observation["verified"] is not True or observation["digest"] != reference["digest"]
            or receipt["binding"] != original_binding
            or any(binding.get(key) != value for key, value in original_binding.items())
            or reference["result_id"] != original_binding["job_id"]
            or request["plane"] != receipt["plane"]
            or request.get("height_band_datum") != receipt["datum"]):
        raise ValueError("retained publication receipt does not match the producing inputs")
    expected = {key: binding[key] for key in (
        "project_source_identity", "canonical_structural_fingerprint", "canonical_full_fingerprint",
        "semantic_key", "domain_request_id", "domain_session_revision")}
    plane = request["plane"]
    expected.update(domain_identity=request["domain"], plane_uuid=plane["identity"],
        plane_revision=plane["revision"], frame_key=f"analysis-plane:{plane['identity']}:{plane['revision']}",
        query_key=request["geometry_query"], request_identity=request["request_id"],
        operation=request["operation"])
    return wire.ResultRef(**reference), wire.ResultReadContext(
        expected=expected, backend_versions=binding["backend_versions"],
        require_confirmed_domain=True, allow_historical=True)


def retained_distance_input(directory: Path, before: dict, reference: wire.ResultRef) -> tuple:
    """Authenticate a completed real run before reusing its immutable adapter bytes."""
    audit = read_json(directory / "adapter_audit.json")
    coverage = read_json(directory / "coverage_report.json")
    manifest = read_json(directory / "run_manifest.json")
    if audit["input_files"] != before or manifest["input_files_after"] != {
            name: record["sha256"] for name, record in before.items()}:
        raise ValueError("retained input does not match the original producing inputs")
    expected_ref = asdict(reference)
    if audit["result_ref"] != expected_ref or manifest["free_space_result"]["result_ref"] != expected_ref:
        raise ValueError("retained input does not match the exact result reference")
    names = ("input_bundle.json", "scene_geometry.json", "adapter_audit.json", "run_manifest.json")
    hashes = {name: file_hash(directory / name) for name in names}
    if (coverage["source_inputs_unchanged"] is not True or coverage["same_bundle_replay_equal"] is not True
            or any(coverage["output_hashes"].get(name) != value for name, value in hashes.items())):
        raise ValueError("retained input artifacts differ from the completed run hashes")
    bundle = retained_input(directory / "input_bundle.json")
    if (bundle.free_space_samples is None or _json_value(bundle.free_space_samples["result_ref"]) != expected_ref
            or _json_value(bundle.dependency_fingerprints) != audit["dependency_fingerprints"]
            or _json_value(bundle.source_identity) != manifest["source_identity"]
            or _json_value(bundle.analysis_plane) != manifest["analysis_plane"]
            or _json_value(bundle.query_context) != manifest["query_context"]):
        raise ValueError("retained adapter handoff differs from its authenticated source bindings")
    return bundle, {**audit, "retained_input": {"directory": str(directory.resolve()),
        "input_bundle_sha256": hashes["input_bundle.json"], "artifact_sha256": hashes,
        "scope": "same authenticated immutable input; no projection or free-space generation"}}


def write_comparison(baseline: Path, current: dict, output: Path) -> dict:
    """Compare exact stored numbers from the authenticated compact baseline preview."""
    coverage = read_json(baseline / "coverage_report.json")
    preview_coverage = read_json(baseline / "preview/coverage_report.json")
    manifest = read_json(baseline / "run_manifest.json")
    paths = {"preview": baseline / "preview/index.html", "observations": baseline / "observations.json"}
    hashes = {name: file_hash(path) for name, path in paths.items()}
    if (hashes["preview"] != preview_coverage["output_hashes"]["index.html"]
            or hashes["observations"] != coverage["output_hashes"]["observations.json"]
            or manifest["free_space_result"]["result_ref"] != current["manifest"]["free_space_result"]["result_ref"]
            or file_hash(baseline / "input_bundle.json") != file_hash(output / "input_bundle.json")
            or file_hash(baseline / "scene_geometry.json") != file_hash(output / "scene_geometry.json")):
        raise ValueError("comparison baseline bytes or immutable input/result bindings differ")
    html = paths["preview"].read_text(encoding="utf-8")
    previous = wire.load_json(html.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0])["observations"]
    old = {row["pair_id"]: row for row in previous}
    if (len(old) != len(previous) or set(old) != set(manifest["expected_pair_ids"])
            or set(old) != set(current["manifest"]["expected_pair_ids"])):
        raise ValueError("comparison pair identities differ")
    rows = []
    for row in current["observations"]:
        prior = old[row["pair_id"]]
        if (row["group_ids"] != prior["group_ids"]
                or row["center_to_center_euclidean"] != prior["center_to_center_euclidean"]
                or row["geometry_audit"] != prior["geometry_audit"]):
            raise ValueError("comparison group, Euclidean or centroid evidence differs")
        before_value, after_value = prior["centroid_free_space_hybrid"]["value"], row["centroid_free_space_hybrid"]["value"]
        improvement = before_value - after_value if before_value is not None and after_value is not None else None
        tau = max(math.ulp(value) for value in (before_value, after_value, current["manifest"]["grid"]["spacing"]) if value is not None)
        rows.append({"pair_id": row["pair_id"], "group_a": row["group_ids"][0], "group_b": row["group_ids"][1],
            "euclidean_m": row["center_to_center_euclidean"]["value"], "v3_hybrid_m": before_value,
            "v4_hybrid_m": after_value, "improvement_m": improvement,
            "improvement_percent": 100 * improvement / before_value if improvement is not None and before_value else None,
            "v3_status": prior["centroid_free_space_hybrid"]["status"], "v4_status": row["centroid_free_space_hybrid"]["status"],
            "comparison": "unavailable" if improvement is None else "improved" if improvement > tau else "worsened" if improvement < -tau else "equal"})
    fixed_report = baseline / "native_route_board_v2/preview_report.json"
    fixed_pair = read_json(fixed_report)["pair_id"] if fixed_report.exists() else previous[0]["pair_id"]
    comparable = [row for row in rows if row["improvement_m"] is not None]
    maximum = max(comparable, key=lambda row: (row["improvement_m"], row["pair_id"])) if comparable else None
    summary = {"baseline_directory": str(baseline.resolve()), "current_directory": str(output.resolve()),
        "baseline_model": manifest["algorithm_version"], "current_model": current["manifest"]["algorithm_version"],
        "comparison_source": "accepted compact baseline HTML payload; exact unrounded JSON numbers",
        "baseline_files": {name: {"path": str(path.resolve()), "sha256": hashes[name], "bytes": path.stat().st_size} for name, path in paths.items()},
        "result_ref": manifest["free_space_result"]["result_ref"], "pair_count": len(rows),
        "pair_ids_groups_euclidean_centroids_unchanged": True, "input_bundle_and_scene_geometry_byte_identical": True,
        "counts": dict(Counter(row["comparison"] for row in rows)),
        "mean_improvement_m": math.fsum(row["improvement_m"] for row in comparable) / len(comparable) if comparable else None,
        "max_absolute_improvement": maximum, "fixed_pair": next(row for row in rows if row["pair_id"] == fixed_pair),
        "visual_pair_ids": list(dict.fromkeys([fixed_pair, maximum["pair_id"]] if maximum else [fixed_pair]))}
    with (output / "comparison_rows.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(output / "comparison_summary.json", summary)
    return summary


def run(result_path: Path, native_request_path: Path, receipt_path: Path, output: Path,
        retained_run_dir: Path | None = None) -> dict:
    """Retain a reproducible distance run and all exact-result and route evidence."""
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    paths = {"free_space_result": result_path, "native_request": native_request_path,
             "publication_receipt": receipt_path}
    before = {name: {"path": str(path.resolve()), "sha256": file_hash(path), "bytes": path.stat().st_size}
              for name, path in paths.items()}
    try:
        print("Opening retained exact free-space result with independent consumer expectations", flush=True)
        receipt = load_json(receipt_path)
        if retained_run_dir is not None:
            reference = wire.ResultRef(**receipt["result_ref"])
            print("Reusing authenticated retained group/domain/lattice bytes without projection", flush=True)
            bundle, audit = retained_distance_input(retained_run_dir, before, reference)
            freshness = bundle.free_space_samples["freshness"]
        else:
            native_request = load_json(native_request_path)
            reference, context = retained_read_context(native_request, receipt)
            snapshot = wire.open_analysis_result([load_json(result_path)], result_ref=reference, context=context)
            print("Projecting authenticated group/domain geometry; saved lattice and samples remain exact", flush=True)
            bundle = distance_input_from_free_space(snapshot, native_request)
            freshness = snapshot.freshness
        sample_counts = Counter((sample["status"], sample["value"]) for sample in bundle.free_space_samples["cells"])
        audit = audit if retained_run_dir is not None else {"adapter": "exact-free-space-distance/1", "result_ref": asdict(reference),
            "freshness": freshness, "freshness_scope": "retained publication; no live Blender observation",
            "input_files": before, "origin_offset": bundle.origin_offset,
            "sample_source": "exact opened result cells; FreeSpaceField is not invoked",
            "group_source": "whole-group projections from authenticated producing native capture",
            "group_count": len(bundle.groups), "physical_record_count": len(bundle.physical_occupancy),
            "sample_count": sum(sample_counts.values()), "sample_counts": [
                {"status": status, "value": value, "count": count}
                for (status, value), count in sorted(sample_counts.items(), key=lambda item: str(item[0]))],
            "dependency_fingerprints": _json_value(bundle.dependency_fingerprints)}
        if retained_run_dir is not None:
            for name in ("input_bundle.json", "scene_geometry.json"):
                shutil.copyfile(retained_run_dir / name, output / name)
        else:
            write_json(output / "input_bundle.json", _json_value(bundle))
            write_json(output / "scene_geometry.json", {"analysis_plane": _json_value(bundle.analysis_plane),
            "origin_offset": bundle.origin_offset, "domain": _json_value(bundle.domain),
            "groups": _json_value(bundle.groups), "physical_occupancy": _json_value(bundle.physical_occupancy),
            "unresolved_source_ids": _json_value(bundle.unresolved_source_ids),
                "unresolved_supports": _json_value(bundle.unresolved_supports)})
        write_json(output / "adapter_audit.json", audit)
        memory_before = process_memory()
        pairs = len(bundle.groups) * (len(bundle.groups) - 1) // 2
        print(f"Calculating {len(bundle.groups)} groups / {pairs} pairs on {bundle.grid.n_rows} x {bundle.grid.n_cols}", flush=True)
        first = serialize_group_distance_result(calculate_group_pair_distances(bundle))
        if first["diagnostics"]["global_status"] is not None:
            raise ValueError("kernel rejected exact-result handoff: " + first["diagnostics"]["global_explanation"])
        coverage = validate_result(first, bundle)
        first_hash = normalized_hash(first)
        print(f"Validated {coverage['selected_paths_checked']} actual routes; replaying immutable bundle", flush=True)
        repeated = serialize_group_distance_result(calculate_group_pair_distances(bundle))
        second_hash = normalized_hash(repeated)
        if first_hash != second_hash:
            raise ValueError("same-bundle replay normalized result differs")
        del repeated
        after = {name: file_hash(path) for name, path in paths.items()}
        if any(after[name] != info["sha256"] for name, info in before.items()):
            raise ValueError("producing input/result/evidence bytes changed during distance execution")
        for item in first["pair_index"]:
            item["observation_locator"] = f"observations.json#/{item['observation_index']}"
            item["route_view_locator"] = f"preview/index.html#{item['pair_id']}"
        write_json(output / "observations.json", first["observations"])
        write_json(output / "pair_index.json", first["pair_index"])
        if retained_run_dir is not None:
            write_comparison(retained_run_dir, first, output)
        write_json(output / "run_manifest.json", {**first["manifest"], "adapter_audit": audit,
            "input_files_after": after, "kernel_diagnostics": first["diagnostics"],
            "selected_candidate_id": bundle.domain["selected_candidate_id"],
            "same_bundle_replay": {"performed": True, "equal": True,
                "normalized_sha256": first_hash, "repeated_normalized_sha256": second_hash,
                "scope": "same immutable exact-result input; runtime/allocation diagnostics excluded"},
            "resources": {"runner_runtime_s": time.perf_counter() - started,
                "before_kernel": memory_before, "after_second_kernel": process_memory(),
                "kernel_memory_scope": "kernel tracemalloc only; process records include both runs",
                "adapter_memory_scope": "same process including authenticated retained input decoding" if retained_run_dir else "same process including retained request/result decoding"}})
        coverage.update(group_count=len(bundle.groups), result_ref=asdict(reference), freshness=freshness,
            exact_saved_sample_count=len(bundle.free_space_samples["cells"]),
            same_bundle_replay_equal=True, normalized_result_sha256=first_hash,
            source_inputs_unchanged=True, output_hashes={name: file_hash(output / name) for name in (
                "observations.json", "pair_index.json", "run_manifest.json", "scene_geometry.json",
                "input_bundle.json", "adapter_audit.json")})
        write_json(output / "coverage_report.json", coverage)
        return coverage
    except Exception as error:
        write_json(output / "failure.json", {"type": type(error).__name__, "message": str(error),
            "elapsed_s": time.perf_counter() - started, "input_files_before": before})
        raise


def main() -> None:
    """Require an exact publication and explicit historical replay acknowledgement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--free-space-result", type=Path, required=True)
    parser.add_argument("--native-request", type=Path, required=True)
    parser.add_argument("--publication-receipt", type=Path, required=True)
    parser.add_argument("--allow-historical", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--retained-run-dir", type=Path)
    args = parser.parse_args()
    if not args.allow_historical:
        parser.error("retained-publication distance replay requires explicit --allow-historical")
    print(run(args.free_space_result, args.native_request, args.publication_receipt, args.output_dir, args.retained_run_dir))


if __name__ == "__main__":
    main()
