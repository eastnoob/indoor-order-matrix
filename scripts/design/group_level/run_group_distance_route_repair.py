"""Run bounded route-first directional-clearance repair over an ordinary result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from features.group_distance_repair import repair_result, write_repair_result
from scripts.design.group_level.run_group_distance_ifc import retained_input


def main() -> None:
    """Load an authenticated ordinary run and write the repair package."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-bundle", type=Path, required=True)
    parser.add_argument("--baseline-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidate-budget", type=int, default=4)
    parser.add_argument("--corridor-margin-cells", type=int, default=3)
    parser.add_argument("--pair-limit", type=int)
    parser.add_argument("--min-left-m", type=float, default=.225)
    parser.add_argument("--min-right-m", type=float, default=.225)
    parser.add_argument("--min-total-m", type=float, default=.55)
    args = parser.parse_args()
    bundle = retained_input(args.input_bundle)
    baseline = {
        "manifest": json.loads((args.baseline_run_dir / "run_manifest.json").read_text(encoding="utf-8")),
        "observations": json.loads((args.baseline_run_dir / "observations.json").read_text(encoding="utf-8")),
    }
    result = repair_result(
        bundle,
        baseline,
        {"min_left_m": args.min_left_m, "min_right_m": args.min_right_m, "min_total_m": args.min_total_m},
        candidate_budget=args.candidate_budget,
        corridor_margin_cells=args.corridor_margin_cells,
        pair_limit=args.pair_limit,
    )
    write_repair_result(result, args.output_dir)
    print(json.dumps({key: result[key] for key in ("method", "pair_count", "quality_counts", "geometry_checks", "cache_sizes")},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
