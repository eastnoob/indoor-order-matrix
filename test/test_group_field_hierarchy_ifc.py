"""Verify the hierarchy replay against the retained real-IFC artifact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.design.group_level.run_group_field_hierarchy_ifc import run


ROOT = Path(__file__).parents[1]
RETAINED_RUN = ROOT / "outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z"
PROJECT_GLOBAL_ID = "2uGd6yom9GZe5$z7LfbGW0"
PINNED_SHA256 = "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"
OUTPUTS = (
    "axis_potential_output.json",
    "envelopes.json",
    "description.json",
    "source_manifest.json",
    "source_reuse.json",
    "field_matrix.json",
    "field_profiles.json",
    "field_directions.json",
    "field_view_manifest.json",
    "view_manifest.json",
    "hierarchy.json",
    "family_matrix.json",
    "family_profiles.json",
    "family_directions.json",
    "family_view_manifest.json",
    "package_contract.json",
    "package_status.json",
    "report.json",
)


def _tree_hashes(root: Path) -> dict[str, str]:
    """Fingerprint every retained artifact to prove the replay stays read-only."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _json(root: Path, name: str):
    """Load one generated JSON artifact for structural assertions."""
    return json.loads((root / name).read_text(encoding="utf-8"))


def test_runner_replays_complete_retained_hierarchy_without_source_drift(tmp_path: Path) -> None:
    """Preserve retained inputs and legacy outputs while indexing all hierarchy targets."""
    source_hashes = _tree_hashes(RETAINED_RUN)
    retained_manifest = _json(RETAINED_RUN, "source_manifest.json")
    retained_output = _json(RETAINED_RUN, "axis_potential_output.json")
    output = run(RETAINED_RUN, tmp_path / "hierarchy_run")

    assert {path.name for path in output.iterdir() if path.is_file()} >= set(OUTPUTS)
    source_manifest = _json(output, "source_manifest.json")
    source_reuse = _json(output, "source_reuse.json")
    field_matrix = _json(output, "field_matrix.json")
    family_matrix = _json(output, "family_matrix.json")
    hierarchy = _json(output, "hierarchy.json")
    report = _json(output, "report.json")
    view_manifest = _json(output, "view_manifest.json")
    package = _json(output, "axis_potential_output.json")

    assert source_manifest["project_global_id"] == PROJECT_GLOBAL_ID == retained_manifest["project_global_id"]
    assert source_manifest["source"]["sha256"] == source_manifest["source_after"]["sha256"] == PINNED_SHA256
    assert source_reuse["ifc_extraction_rerun"] is False
    assert source_reuse["synthetic_input"] is False
    assert {item["path"]: item["sha256"] for item in source_reuse["retained_inputs"]} == source_hashes
    assert package["source_envelopes"] == retained_output["source_envelopes"]
    legacy_keys = {(row["target"]["identity"], row["channel"]): row for row in retained_output["outputs"]}
    actual_keys = {(row["target"]["identity"], row["channel"]): row for row in package["outputs"]}
    assert all(actual_keys[key] == row for key, row in legacy_keys.items())
    assert len(field_matrix["fields"]) == report["source_scope_count"] == 37
    assert sum(len(field["cells"]) for field in field_matrix["fields"].values()) == 1369
    assert len(family_matrix["families"]) == len(hierarchy["families"]) == report["family_count"]
    assert sum(len(family["cells"]) for family in family_matrix["families"].values()) == report["family_cell_count"]
    assert report["legacy_output_count"] == len(retained_output["outputs"]) == 4112
    assert report["derived_output_count"] == len(package["outputs"])
    assert report["ifc_extraction_rerun"] is False and report["real_world_cluster_validity"] is False
    assert {item["target_identity"] for item in view_manifest["target_index"]} == {row["target"]["identity"] for row in package["outputs"]}
    assert len(view_manifest["target_index"]) == report["target_index_count"]
    assert len(_json(output, "field_view_manifest.json")["fields"]) == 37
    assert len(_json(output, "family_view_manifest.json")["families"]) == report["family_count"]
    assert _tree_hashes(RETAINED_RUN) == source_hashes


def test_runner_refuses_to_overwrite_an_existing_output_root(tmp_path: Path) -> None:
    """Reject an existing destination before creating or replacing any artifact."""
    with pytest.raises(FileExistsError):
        run(RETAINED_RUN, tmp_path)
