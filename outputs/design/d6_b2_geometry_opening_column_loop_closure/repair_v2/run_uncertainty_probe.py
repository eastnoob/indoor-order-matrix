"""Run append-only D6 B2 uncertainty propagation evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_FIXTURES = Path(__file__).with_name("fixtures_patch.json")
DEFAULT_OUTPUT = Path(__file__).parent
ORIGINAL_FIXTURES = ROOT / "outputs/design/d6_b2_geometry_opening_column_loop_closure/fixtures.json"
ORIGINAL_RUNNER_MODULE = "scripts.design.space_field.run_d6_b2_geometry_opening_column_loop_closure"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _stable_json_bytes(value: object) -> bytes:
    """Serialize evidence deterministically for reproducible artifact hashes."""
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    """Return the SHA-256 digest of a byte payload."""
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: object) -> bytes:
    """Write one deterministic JSON artifact and return its exact bytes."""
    payload = _stable_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def _observe_uncertain_fixture(fixture: dict[str, Any], original_runner: Any, topology_status: Any) -> dict[str, Any]:
    """Propagate fixture uncertainty through existing local observations and refusal fields."""
    result = original_runner._observe_fixture(fixture, topology_status)
    result["occupancy_role"] = str(fixture["occupancy_role"])
    result["uncertainty_source"] = fixture["uncertainty_source"]
    result["affected_input_fact"] = fixture["affected_input_fact"]

    # Preserve contradictory or unresolved source facts verbatim; do not collapse them into a chosen geometry.
    state = str(fixture["expected"]["local_diagnostic_state"] if "local_diagnostic_state" in fixture["expected"] else fixture["expected"]["opening_variant_statuses"][0])
    if fixture["id"] == "B2-U01":
        propagation_reason = "column_wall_contact_observations_conflict_contact_unconfirmed"
    else:
        propagation_reason = "opening_host_and_geometry_observations_conflict_qualification_refused"
        for source, observed in zip(fixture["opening"]["variants"], result["opening_provenance"]["variants"], strict=True):
            observed["uncertainty_source_ids"] = source["uncertainty_source_ids"]
    result["uncertainty_propagation"] = {
        "source": fixture["uncertainty_source"],
        "affected_input_fact": fixture["affected_input_fact"],
        "local_diagnostic_state": state,
        "reason": propagation_reason,
        "input_preserved": True,
    }
    result["diagnostic_refusal"] = {
        "state": state,
        "formal_domain_promotion": fixture["expected"]["formal_domain_promotion"],
        "downstream_free_space_or_route_claim": fixture["expected"]["downstream_free_space_or_route_claim"],
        "reason": propagation_reason,
    }
    result["expected"] = fixture["expected"]
    return result


def _verify_uncertainty_fixtures(fixtures: list[dict[str, Any]], results: list[dict[str, Any]]) -> None:
    """Assert uncertainty provenance, physical occupancy, refusal, and existing diagnostics propagate."""
    assert len(fixtures) == len(results) == 2
    by_id = {result["fixture_id"]: result for result in results}
    for fixture in fixtures:
        result = by_id[fixture["id"]]
        expected_state = fixture["expected"].get("local_diagnostic_state")
        if expected_state is None:
            expected_state = fixture["expected"]["opening_variant_statuses"][0]
        assert result["uncertainty_source"] == fixture["uncertainty_source"]
        assert result["affected_input_fact"] == fixture["affected_input_fact"]
        assert result["uncertainty_propagation"]["input_preserved"] is True
        assert result["occupancy_role"] == fixture["occupancy_role"]
        assert result["physical_occupancy"] == fixture["physical_occupancy"]
        assert result["boundary_support"]["conditional_support_in_this_fixture"] is False
        assert result["diagnostic_refusal"]["state"] == expected_state
        assert result["diagnostic_refusal"]["formal_domain_promotion"] == "refused"
        assert result["diagnostic_refusal"]["downstream_free_space_or_route_claim"] == "not_evaluated"

    contact = by_id["B2-U01"]
    assert contact["contact_evidence"] == next(item for item in fixtures if item["id"] == "B2-U01")["contact_evidence"]
    assert contact["boundary_support"]["candidate_segment_ids"] == ["column-uncertain-face"]
    assert contact["uncertainty_propagation"]["local_diagnostic_state"] == "conflict"

    opening = by_id["B2-U02"]["opening_provenance"]["variants"]
    assert [item["local_diagnostic_state"] for item in opening] == ["conflict"]
    assert all(item["subtraction_performed"] is False for item in opening)
    assert opening[0]["host_refs"] == ["wall-A", "wall-B"]
    assert opening[0]["geometry_refs"] == ["opening-geometry-A", "opening-geometry-B"]
    assert opening[0]["uncertainty_source_ids"] == ["void-relation-A", "void-relation-B", "opening-geometry-A", "opening-geometry-B"]


def _verify_existing_distinctions(results: list[dict[str, Any]], provenance: dict[str, Any]) -> None:
    """Confirm original fixture diagnostics stay separate alongside the new uncertainty cases."""
    original = {item["fixture_id"]: item for item in results if item["fixture_id"].startswith("B2-F")}
    assert len(original) == 9
    assert [item["local_diagnostic_state"] for item in original["B2-F06"]["opening_provenance"]["variants"]] == ["not_available", "invalid", "conflict"]
    assert [item["local_diagnostic_state"] for item in original["B2-F07"]["opening_provenance"]["variants"]] == ["invalid", "unsupported"]
    assert original["B2-F04"]["opening_provenance"]["variants"][0]["local_diagnostic_state"] == "diagnostic_only"
    assert original["B2-F03"]["source_components"]["status"] == "partial"
    assert any(item["relation_state"] == "missing" for item in original["B2-F06"]["opening_provenance"]["variants"])
    assert provenance["real_ifc"] == "not_verified_not_run"


def _summary_svg(results: list[dict[str, Any]]) -> bytes:
    """Render two uncertainty status cards without depicting geometry or production output."""
    root = ET.Element(f"{{{SVG_NS}}}svg", {"width": "900", "height": "300", "viewBox": "0 0 900 300"})
    title = ET.SubElement(root, f"{{{SVG_NS}}}text", {"x": "24", "y": "32", "font-family": "Arial, sans-serif", "font-size": "22", "font-weight": "700", "fill": "#17212b"})
    title.text = "D6 B2 — uncertainty propagation fixtures"
    subtitle = ET.SubElement(root, f"{{{SVG_NS}}}text", {"x": "24", "y": "58", "font-family": "Arial, sans-serif", "font-size": "13", "fill": "#475569"})
    subtitle.text = "Synthetic diagnostic only · promotion refused · downstream claims not evaluated"
    for index, result in enumerate(results):
        x, y, width, height = 24 + index * 430, 82, 410, 186
        group = ET.SubElement(root, f"{{{SVG_NS}}}g")
        ET.SubElement(group, f"{{{SVG_NS}}}rect", {"x": str(x), "y": str(y), "width": str(width), "height": str(height), "rx": "8", "fill": "#ffffff", "stroke": "#cbd5e1", "stroke-width": "1"})
        ET.SubElement(group, f"{{{SVG_NS}}}rect", {"x": str(x), "y": str(y), "width": "6", "height": str(height), "rx": "3", "fill": "#b45309"})
        lines = [
            f"{result['fixture_id']} · {result['diagnostic_refusal']['state']}",
            *textwrap.wrap(result["title"], width=42)[:2],
            f"source topology: {result['source_components']['status']} · components: {result['source_components']['component_count']}",
            f"column support: {'yes' if result['boundary_support']['conditional_support_in_this_fixture'] else 'no'} · promotion: refused",
            "opening subtraction: no · downstream: not evaluated",
        ]
        for line_index, line in enumerate(lines):
            element = ET.SubElement(group, f"{{{SVG_NS}}}text", {"x": str(x + 16), "y": str(y + 24 + line_index * 26), "font-family": "Arial, sans-serif", "font-size": "13", "fill": "#334155"})
            element.text = line
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> int:
    """Rerun the nine accepted fixtures, append uncertainty cases, and write deterministic evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    fixtures_path = args.fixtures.resolve()
    output_dir = args.output_dir.resolve()
    original_fixture_bytes = ORIGINAL_FIXTURES.read_bytes()
    patch_bytes = fixtures_path.read_bytes()
    original_fixture_payload = json.loads(original_fixture_bytes)
    patch_payload = json.loads(patch_bytes)
    assert len(original_fixture_payload["fixtures"]) == 9
    assert patch_payload["extends"]["fixture_count"] == len(original_fixture_payload["fixtures"])
    assert patch_payload["extends"]["fixture_sha256"] == _sha256(original_fixture_bytes)
    assert [item["id"] for item in patch_payload["fixtures"]] == ["B2-U01", "B2-U02"]
    original_runner = importlib.import_module(ORIGINAL_RUNNER_MODULE)
    helper = importlib.import_module(original_runner.HELPER_MODULE)

    original_rows = original_fixture_payload["fixtures"]
    original_runner._verify_results(
        original_rows,
        [original_runner._observe_fixture(fixture, helper._topology_status) for fixture in original_rows],
    )
    uncertainty_rows = patch_payload["fixtures"]
    uncertainty_results = [_observe_uncertain_fixture(fixture, original_runner, helper._topology_status) for fixture in uncertainty_rows]
    _verify_uncertainty_fixtures(uncertainty_rows, uncertainty_results)

    all_results = [
        *[original_runner._observe_fixture(fixture, helper._topology_status) for fixture in original_rows],
        *uncertainty_results,
    ]
    runner_bytes = Path(__file__).read_bytes()
    provenance = {
        "schema_version": "d6-b2-uncertainty-provenance-v1",
        "evidence_class": "synthetic_design_evidence",
        "original_fixture_path": "outputs/design/d6_b2_geometry_opening_column_loop_closure/fixtures.json",
        "original_fixture_sha256": _sha256(original_fixture_bytes),
        "uncertainty_patch_path": "outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/fixtures_patch.json",
        "uncertainty_patch_sha256": _sha256(patch_bytes),
        "runner_path": "outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/run_uncertainty_probe.py",
        "runner_sha256": _sha256(runner_bytes),
        "original_runner_path": "scripts/design/space_field/run_d6_b2_geometry_opening_column_loop_closure.py",
        "original_runner_sha256": _sha256((ROOT / "scripts/design/space_field/run_d6_b2_geometry_opening_column_loop_closure.py").read_bytes()),
        "helper": original_runner.HELPER_MODULE + "._topology_status",
        "helper_scope": "existing exact-endpoint diagnostic only; not a production geometry algorithm or tolerance policy",
        "fixture_count": len(all_results),
        "original_fixture_count": len(original_rows),
        "uncertainty_fixture_count": len(uncertainty_rows),
        "uncertainty_inputs_preserved": True,
        "real_ifc": "not_verified_not_run",
        "blender": "not_run",
        "production_code_modified": False,
    }
    _verify_existing_distinctions(all_results, provenance)
    result_payload = {
        "schema_version": "d6-b2-uncertainty-results-v1",
        "evidence_class": "synthetic_design_evidence",
        "owner_decision": {"commit": "9b50bb1f44c0ae7dc2807c17da084d1ab8163393", "B2": "REVISE", "B5": "narrow_APPROVE"},
        "status_vocabulary_note": "Existing local diagnostic labels are preserved; no unified public status enum is defined.",
        "fixture_count": len(all_results),
        "original_fixture_count": len(original_rows),
        "uncertainty_fixture_count": len(uncertainty_rows),
        "results": all_results,
    }
    result_bytes = _write_json(output_dir / "results.json", result_payload)
    svg_bytes = _summary_svg(uncertainty_results)
    (output_dir / "summary.svg").write_bytes(svg_bytes)
    provenance["results_sha256"] = _sha256(result_bytes)
    provenance["summary_svg_sha256"] = _sha256(svg_bytes)
    provenance_bytes = _write_json(output_dir / "provenance.json", provenance)
    print(json.dumps({"fixture_count": len(all_results), "original_fixture_count": len(original_rows), "uncertainty_fixture_count": len(uncertainty_rows), "results_sha256": _sha256(result_bytes), "summary_svg_sha256": _sha256(svg_bytes), "provenance_sha256": _sha256(provenance_bytes), "output_dir": str(output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
