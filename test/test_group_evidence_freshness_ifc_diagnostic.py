"""Focused integration checks for the pinned IFC freshness visual diagnostic."""

from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET


def test_pinned_ifc_visual_freshness_round_trip(tmp_path: Path) -> None:
    """Render real IFC baseline/rotated plans and verify stale-to-fresh recovery."""
    from ..scripts.design.group_level import run_group_evidence_freshness_ifc_diagnostic as diagnostic

    repository = Path(__file__).resolve().parents[1]
    source = repository / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"
    run_dir = diagnostic.run(source, tmp_path / "diagnostic")
    manifest_path = run_dir / "freshness_diagnostic.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["source"]["byte_length"] == 408618044
    assert manifest["source"]["sha256"] == (
        "1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077"
    )
    assert manifest["source"] == manifest["source_after"]
    assert manifest["source"] == manifest["source_final"]
    assert manifest["analysis_plane"]["name"] == "ifc-world-plan"
    assert manifest["target_ids"]
    assert manifest["selected_target"] in manifest["target_ids"]
    assert manifest["read_only"] is True
    assert manifest["synthetic_input"] is False

    baseline_svg = Path(manifest["baseline_svg"])
    rotated_svg = Path(manifest["rotated_svg"])
    assert baseline_svg.is_file() and rotated_svg.is_file()
    baseline_bytes = baseline_svg.read_bytes()
    rotated_bytes = rotated_svg.read_bytes()
    assert baseline_bytes and rotated_bytes
    assert baseline_bytes != rotated_bytes
    baseline_root = ET.fromstring(baseline_bytes)
    rotated_root = ET.fromstring(rotated_bytes)
    svg_namespace = "{http://www.w3.org/2000/svg}"
    baseline_paths = [item.get("d") for item in baseline_root.findall(f".//{svg_namespace}path")]
    rotated_paths = [item.get("d") for item in rotated_root.findall(f".//{svg_namespace}path")]
    assert baseline_paths != rotated_paths

    statuses = manifest["statuses"]
    assert statuses["baseline"]["freshness"] == "fresh"
    assert statuses["baseline"]["recompute_required"] is False
    assert statuses["rotated"]["freshness"] == "stale"
    assert statuses["rotated"]["recompute_required"] is True
    assert statuses["rotated"]["invalidation_scope"] == "whole_package"
    assert set(statuses["rotated"]["affected_targets"]) == set(manifest["target_ids"])
    assert {reason["code"] for reason in statuses["rotated"]["reasons"]} & {
        "scene_changed",
        "model_changed",
    }
    assert statuses["rotated"]["algorithm"]["status"] == "same"
    assert statuses["restored"]["freshness"] == "fresh"
    assert statuses["restored"]["recompute_required"] is False
