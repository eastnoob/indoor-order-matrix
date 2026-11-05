"""Run and persist global directional repair for one source furniture group."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from features.group_distance_repair import global_repair_result
from scripts.design.group_level.run_group_distance_ifc import retained_input


def main() -> None:
    """Compute one source group's pairs so completed work is independently reusable."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-bundle", type=Path, required=True)
    parser.add_argument("--baseline-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-index", type=int, required=True)
    args = parser.parse_args()
    bundle = retained_input(args.input_bundle)
    if not 0 <= args.source_index < len(bundle.groups) - 1:
        raise SystemExit("source-index is outside the available pair sources")
    source_id = bundle.groups[args.source_index].group_id
    baseline_dir = args.baseline_run_dir
    observations = json.loads((baseline_dir / "observations.json").read_text(encoding="utf-8"))
    subset = [row for row in observations if row["group_ids"][0] == source_id]
    baseline = {
        "manifest": json.loads((baseline_dir / "run_manifest.json").read_text(encoding="utf-8")),
        "observations": subset,
    }
    # Use a per-run checkpoint directory so an interrupted process can resume
    # without repeating completed source groups or losing their exact routes.
    checkpoint_dir = args.output_dir / "checkpoints"
    result = global_repair_result(
        bundle, baseline,
        {"min_left_m": .225, "min_right_m": .225, "min_total_m": .55},
        checkpoint_dir=checkpoint_dir,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    temporary = args.output_dir / "repair_result.json.tmp"
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    temporary.replace(args.output_dir / "repair_result.json")
    print(json.dumps({"source_index": args.source_index, "source_id": source_id,
                      "pair_count": result["pair_count"],
                      "quality_counts": result["quality_counts"],
                      "geometry_checks": result["geometry_checks"]}, sort_keys=True))


if __name__ == "__main__":
    main()
