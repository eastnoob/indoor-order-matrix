"""Generate fresh, model-neutral synthetic inputs for Stage B validation."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = "stage-b-fixtures/v1"
SCENARIO_TYPES = ("linear_pattern", "grid_pattern", "overlap_nested", "bridge_chain", "semantic_conflict", "shared_source_dependence", "missing_invalid_conflict", "scale_perturbation")
SEEDS = (1101, 1202, 1303, 1404, 1505, 1606)
SPLITS = {1101: "development", 1202: "development", 1303: "development", 1404: "validation", 1505: "holdout", 1606: "holdout"}

def _digest(value: Any) -> str:
    """Return deterministic provenance for a frozen object."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def fixture_split(source_family_id: str) -> Literal["development", "validation", "holdout"]:
    """Return the frozen source-family partition from its declared seed."""
    try:
        return SPLITS[int(source_family_id.rsplit(":", 1)[1])]
    except (KeyError, ValueError, IndexError) as error:
        raise ValueError(f"unknown Stage B source family: {source_family_id}") from error

def candidate_universe_for_scene(scene_skeleton: dict[str, Any], policy: str) -> dict[str, Any]:
    """Freeze primary candidates from the skeleton before evidence is generated."""
    if policy != "external_skeleton":
        raise ValueError(f"unsupported primary candidate policy: {policy}")
    nodes = [node["id"] for node in scene_skeleton["nodes"]]
    if len(nodes) != 6 or len(set(nodes)) != 6:
        raise ValueError("Stage B fixture skeletons require six unique authored nodes")
    candidates = [
        {"candidate_set_id": f"{scene_skeleton['scene_id']}:core", "node_ids": nodes[:4], "labels": ["primary", "overlap"]},
        {"candidate_set_id": f"{scene_skeleton['scene_id']}:nested", "node_ids": nodes[1:4], "labels": ["nested", "overlap"]},
        {"candidate_set_id": f"{scene_skeleton['scene_id']}:diagnostic", "node_ids": [nodes[4]], "labels": ["singleton_diagnostic"]},
    ]
    return {"generator": {"name": "stage_b_external_skeleton", "version": SCHEMA_VERSION}, "conditioning_policy": "external_skeleton_frozen_before_evidence", "candidates": candidates, "uncovered_node_ids": [nodes[5]], "fingerprint": _digest(candidates)}

def _status(scenario: str, index: int) -> str:
    """Schedule categorical states without assigning them numerical values."""
    if scenario == "missing_invalid_conflict" and index == 0: return "invalid"
    if scenario == "missing_invalid_conflict" and index == 1: return "not_available"
    if scenario == "bridge_chain" and index == 5: return "partial"
    if scenario == "semantic_conflict" and index == 3: return "ambiguous"
    return "computed"

def _family(scenario: str, seed: int, global_seed: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Generate separated model inputs, labels, split row, and candidate universe."""
    family, scene_id, split = f"{scenario}:{seed}", f"scene:{scenario}:{seed}", fixture_split(f"{scenario}:{seed}")
    nodes = [{"id": f"{scene_id}:node:{i}", "authored_group_id": f"{family}:group:{i}"} for i in range(6)]
    skeleton = {"scene_id": scene_id, "source_family_id": family, "scenario_type": scenario, "seed": seed + global_seed, "nodes": nodes}
    primary = candidate_universe_for_scene(skeleton, "external_skeleton")
    incidences = [{"source_incidence_id": f"{family}:incidence:{i // 2}", "physical_source_id": f"{family}:source:{i // 2}", "node_id": node["id"], "correlation_scope": "shared_source_node_target"} for i, node in enumerate(nodes)]
    targets = []
    for candidate in primary["candidates"]:
        for node_id in candidate["node_ids"]:
            index = next(i for i, node in enumerate(nodes) if node["id"] == node_id)
            status, target_id, incidence = _status(scenario, index), f"{candidate['candidate_set_id']}|{node_id}", f"{family}:incidence:{index // 2}"
            pattern_id = f"{target_id}:pattern"
            channels = [
              {"channel": "geometry", "kind": "continuous", "value": round((index + 1) / 10, 3)},
              {"channel": "direction", "kind": "continuous", "value": round(1 - index / 10, 3)},
              {"channel": "clearance", "kind": "continuous", "value": round(.4 + index / 20, 3)},
              {"channel": "semantic_compatibility", "kind": "boolean", "value": (index + seed) % 3 != 0},
              {"channel": "pattern_conformity", "kind": "descriptive", "value": round(.9 - index / 20, 3), "measurement_id": pattern_id},
              {"channel": "pattern_residual", "kind": "continuous", "value": round(index / 20, 3), "measurement_id": pattern_id},
            ]
            for channel in channels:
                channel.setdefault("measurement_id", f"{target_id}:{channel['channel']}")
                channel.update({"observation_id": f"{target_id}:{channel['channel']}", "status": status, "source_incidence_id": incidence})
            targets.append({"target_id": target_id, "node_id": node_id, "candidate_set_id": candidate["candidate_set_id"], "status": status, "source_incidence_ids": [incidence], "channels": channels})
    observations = {"scene_id": scene_id, "source_family_id": family, "scenario_type": scenario, "split": split, "skeleton": skeleton, "source_incidences": incidences, "targets": targets}
    truth = {"scene_id": scene_id, "source_family_id": family, "split": split, "latent_membership": [{"target_id": row["target_id"], "Z": row["node_id"] != nodes[3]["id"]} for row in targets], "organization_truth": {"overlap": True, "nesting": True, "singleton_diagnostic": nodes[4]["id"], "uncovered_node_ids": [nodes[5]["id"]]}}
    split_row = {"scene_id": scene_id, "source_family_id": family, "scenario_type": scenario, "seed": seed, "split": split, "source_ids": sorted({item["physical_source_id"] for item in incidences})}
    candidate_row = {"scene_id": scene_id, "source_family_id": family, "split": split, "primary": primary, "selection_sensitivity": {"status": "not_run", "conditioning_policy": "observation_selected_sensitivity_only", "reason": "Task 1 does not execute Stage A proposal policies."}}
    return observations, truth, split_row, candidate_row

def generate_stage_b_manifests(output_dir: Path, seed: int = 20261022) -> dict[str, Path]:
    """Write separated fixture manifests without fitting, calibration, or scoring."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [_family(scenario, family_seed, seed) for scenario in SCENARIO_TYPES for family_seed in SEEDS]
    documents = {"observations": {"schema": "group-clustering-stage-b-observations/v1", "fixtures": [row[0] for row in rows]}, "truth": {"schema": "group-clustering-stage-b-truth/v1", "fixtures": [row[1] for row in rows]}, "splits": {"schema": "group-clustering-stage-b-splits/v1", "source_families": [row[2] for row in rows]}, "candidate_universes": {"schema": "group-clustering-stage-b-candidate-universes/v1", "fixtures": [row[3] for row in rows]}}
    paths = {name: output_dir / f"{name}.json" for name in documents}
    for name, document in documents.items(): paths[name].write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return paths

def load_stage_b_manifests(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load manifests in observations, truth, splits, candidates order."""
    return tuple(json.loads((root / f"{name}.json").read_text(encoding="utf-8")) for name in ("observations", "truth", "splits", "candidate_universes")) # type: ignore[return-value]

def main() -> None:
    """Generate manifests from the command line."""
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); parser.add_argument("--seed", type=int, default=20261022)
    args = parser.parse_args(); print(json.dumps({name: str(path) for name, path in generate_stage_b_manifests(args.output, args.seed).items()}, sort_keys=True))
if __name__ == "__main__": main()

