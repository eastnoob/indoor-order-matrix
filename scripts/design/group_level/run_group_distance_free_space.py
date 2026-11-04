"""Calculate group distances from one exact, externally accepted free-space result."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import time

from adapters import blender_analysis_result_wire as wire
from adapters.free_space_distance import distance_input_from_free_space
from features.field_core import _json_value
from features.group_distance import calculate_group_pair_distances, serialize_group_distance_result
from scripts.design.group_level.run_group_distance_ifc import (
    file_hash, normalized_hash, process_memory, validate_result, write_json,
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


def run(result_path: Path, native_request_path: Path, receipt_path: Path, output: Path) -> dict:
    """Retain a reproducible distance run and all exact-result and route evidence."""
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    paths = {"free_space_result": result_path, "native_request": native_request_path,
             "publication_receipt": receipt_path}
    before = {name: {"path": str(path.resolve()), "sha256": file_hash(path), "bytes": path.stat().st_size}
              for name, path in paths.items()}
    try:
        print("Opening retained exact free-space result with independent consumer expectations", flush=True)
        native_request, receipt = load_json(native_request_path), load_json(receipt_path)
        reference, context = retained_read_context(native_request, receipt)
        snapshot = wire.open_analysis_result([load_json(result_path)], result_ref=reference, context=context)
        print("Projecting authenticated group/domain geometry; saved lattice and samples remain exact", flush=True)
        bundle = distance_input_from_free_space(snapshot, native_request)
        sample_counts = Counter((sample["status"], sample["value"]) for sample in bundle.free_space_samples["cells"])
        audit = {"adapter": "exact-free-space-distance/1", "result_ref": asdict(reference),
            "freshness": snapshot.freshness, "freshness_scope": "retained publication; no live Blender observation",
            "input_files": before, "origin_offset": bundle.origin_offset,
            "sample_source": "exact opened result cells; FreeSpaceField is not invoked",
            "group_source": "whole-group projections from authenticated producing native capture",
            "group_count": len(bundle.groups), "physical_record_count": len(bundle.physical_occupancy),
            "sample_count": sum(sample_counts.values()), "sample_counts": [
                {"status": status, "value": value, "count": count}
                for (status, value), count in sorted(sample_counts.items(), key=lambda item: str(item[0]))],
            "dependency_fingerprints": _json_value(bundle.dependency_fingerprints)}
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
        after = {name: file_hash(path) for name, path in paths.items()}
        if any(after[name] != info["sha256"] for name, info in before.items()):
            raise ValueError("producing input/result/evidence bytes changed during distance execution")
        for item in first["pair_index"]:
            item["observation_locator"] = f"observations.json#/{item['observation_index']}"
            item["route_view_locator"] = f"preview/index.html#{item['pair_id']}"
        write_json(output / "observations.json", first["observations"])
        write_json(output / "pair_index.json", first["pair_index"])
        write_json(output / "run_manifest.json", {**first["manifest"], "adapter_audit": audit,
            "input_files_after": after, "kernel_diagnostics": first["diagnostics"],
            "selected_candidate_id": bundle.domain["selected_candidate_id"],
            "same_bundle_replay": {"performed": True, "equal": True,
                "normalized_sha256": first_hash, "repeated_normalized_sha256": second_hash,
                "scope": "same immutable exact-result input; runtime/allocation diagnostics excluded"},
            "resources": {"runner_runtime_s": time.perf_counter() - started,
                "before_kernel": memory_before, "after_second_kernel": process_memory(),
                "kernel_memory_scope": "kernel tracemalloc only; process records include both runs",
                "adapter_memory_scope": "same process including retained request/result decoding"}})
        coverage.update(group_count=len(bundle.groups), result_ref=asdict(reference), freshness=snapshot.freshness,
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
    args = parser.parse_args()
    if not args.allow_historical:
        parser.error("retained-publication distance replay requires explicit --allow-historical")
    print(run(args.free_space_result, args.native_request, args.publication_receipt, args.output_dir))


if __name__ == "__main__":
    main()
