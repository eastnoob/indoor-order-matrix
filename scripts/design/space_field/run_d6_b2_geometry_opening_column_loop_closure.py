"""Run the bounded synthetic D6 B2 geometry-contract probe."""

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

from shapely import __version__ as shapely_version
from shapely.geometry import Polygon
from shapely.validation import explain_validity


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURES = ROOT / "outputs/design/d6_b2_geometry_opening_column_loop_closure/fixtures.json"
DEFAULT_OUTPUT = ROOT / "outputs/design/d6_b2_geometry_opening_column_loop_closure/run_001"
HELPER_MODULE = "scripts.design.space_field.run_boundary_construction_experiment"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _stable_json_bytes(value: object) -> bytes:
    """Serialize evidence deterministically for byte-level rerun checks."""
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    """Return the SHA-256 digest for a byte payload."""
    return hashlib.sha256(payload).hexdigest()


def _polygon_observation(coordinates: list[list[float]] | None) -> dict[str, Any]:
    """Evaluate candidate polygon validity independently from source connectivity."""
    if coordinates is None:
        return {"status": "not_available", "valid": None, "reason": "candidate_polygon_not_supplied"}
    polygon = Polygon(coordinates)
    valid = bool(polygon.is_valid and polygon.area > 0)
    return {
        "status": "valid" if valid else "invalid",
        "valid": valid,
        "reason": "valid_positive_area_polygon" if valid else explain_validity(polygon),
        "area_in_fixture_units_squared": float(polygon.area),
    }


def _opening_variant_observation(variant: dict[str, Any]) -> dict[str, Any]:
    """Classify local opening evidence without performing subtraction."""
    relation_state = str(variant["relation_state"])
    host_refs = [str(value) for value in variant.get("host_refs", [])]
    known_hosts = {str(value) for value in variant.get("known_host_ids", [])}
    geometry_status = str(variant["geometry_status"])
    supported = bool(variant["representation_supported"])

    if relation_state == "missing":
        state, reason = "not_available", "opening_host_relation_missing"
    elif relation_state == "conflict":
        state, reason = "conflict", "opening_host_relations_conflict"
    elif relation_state != "present" or not host_refs or any(ref not in known_hosts for ref in host_refs):
        state, reason = "invalid", "opening_host_reference_unresolved_or_malformed"
    elif geometry_status == "malformed":
        state, reason = "invalid", "opening_geometry_malformed"
    elif not supported:
        state, reason = "unsupported", "opening_representation_unsupported"
    elif geometry_status != "valid":
        state, reason = "not_available", "usable_opening_geometry_missing"
    else:
        state, reason = "diagnostic_only", "host_and_geometry_refs_present_no_subtraction_performed"

    eligible = state == "diagnostic_only"
    return {
        "variant": str(variant["name"]),
        "local_diagnostic_state": state,
        "reason": reason,
        "relation_state": relation_state,
        "host_refs": host_refs,
        "known_host_ids": sorted(known_hosts),
        "geometry_refs": [str(value) for value in variant.get("geometry_refs", [])],
        "geometry_status": geometry_status,
        "representation_supported": supported,
        "eligible_for_opening_review_only": eligible,
        "subtraction_performed": False,
    }


def _observe_fixture(fixture: dict[str, Any], topology_status: Any) -> dict[str, Any]:
    """Build one result while keeping source topology, occupancy, and polygon facts separate."""
    segments = fixture.get("topology_segments", [])
    topology_input = [
        {
            "id": str(segment["id"]),
            "a": segment["a"],
            "b": segment["b"],
            "level": str(segment.get("level", "synthetic-L0")),
        }
        for segment in segments
    ]
    topology, topology_reason, component_count, degree_histogram = topology_status(topology_input)
    polygon = _polygon_observation(fixture.get("candidate_polygon"))
    column_ids = {str(value) for value in fixture.get("column_boundary_segment_ids", [])}
    contact = fixture["contact_evidence"]
    has_column_support_segment = any(str(segment["id"]) in column_ids for segment in segments)
    conditional_support = bool(
        has_column_support_segment
        and contact.get("exact_contact") is True
        and topology == "computed"
        and component_count == 1
    )

    opening = fixture["opening"]
    opening_variants = [_opening_variant_observation(item) for item in opening.get("variants", [])]
    if opening.get("kind") == "door_scenario":
        opening_observation: dict[str, Any] = {
            "kind": "door_scenario",
            "door_ref": opening["door_ref"],
            "fill_relation_host_ref": opening["fill_relation_host_ref"],
            "assumed_closed": bool(opening["assumed_closed"]),
            "assumption_is_source_fact": bool(opening["assumption_is_source_fact"]),
            "local_diagnostic_state": "diagnostic_only",
            "reason": "door_fill_and_closed_scenario_are_not_void_opening_evidence",
            "subtraction_performed": False,
        }
    elif opening_variants:
        opening_observation = {"kind": opening["kind"], "variants": opening_variants}
    else:
        opening_observation = {
            "kind": "none",
            "local_diagnostic_state": "not_available",
            "reason": "no_opening_source_record_in_fixture",
            "subtraction_performed": False,
        }

    result = {
        "fixture_id": str(fixture["id"]),
        "title": str(fixture["title"]),
        "evidence_class": "synthetic_design_evidence",
        "source_components": {
            "source_segment_ids": [str(segment["id"]) for segment in segments],
            "component_count": int(component_count),
            "status": str(topology),
            "reason": str(topology_reason),
            "degree_histogram": {str(key): int(value) for key, value in sorted(degree_histogram.items())},
            "method": "existing run_boundary_construction_experiment._topology_status exact endpoint diagnostic",
        },
        "physical_occupancy": fixture.get("physical_occupancy", []),
        "contact_evidence": contact,
        "boundary_support": {
            "candidate_segment_ids": sorted(column_ids),
            "conditional_support_in_this_fixture": conditional_support,
            "reason": "exact contact plus one closed diagnostic component" if conditional_support else "support not established by this fixture",
            "production_policy_selected": False,
        },
        "opening_provenance": opening_observation,
        "candidate_polygon_validity": polygon,
        "diagnostic_refusal": {
            "state": "diagnostic_only",
            "formal_domain_promotion": "refused",
            "downstream_free_space_or_route_claim": "not_evaluated",
            "reason": "synthetic B2 contract evidence only; production implementation is not approved",
        },
        "oracle_rationale": str(fixture["oracle_rationale"]),
        "expected": fixture["expected"],
    }
    return result


def _verify_results(fixtures: list[dict[str, Any]], results: list[dict[str, Any]]) -> None:
    """Check every fixture against its independent expected distinctions."""
    if len(fixtures) != 9 or len(results) != 9:
        raise AssertionError(f"expected exactly 9 fixtures/results, got {len(fixtures)}/{len(results)}")
    for fixture, result in zip(fixtures, results, strict=True):
        expected = fixture["expected"]
        observed = result["source_components"]
        polygon = result["candidate_polygon_validity"]
        boundary = result["boundary_support"]
        actual_polygon_status = "valid" if polygon["valid"] is True else "invalid" if polygon["valid"] is False else "not_available"
        assert observed["status"] == expected["topology_status"], fixture["id"]
        assert observed["component_count"] == expected["source_component_count"], fixture["id"]
        assert actual_polygon_status == expected["candidate_polygon_status"], fixture["id"]
        assert boundary["conditional_support_in_this_fixture"] is expected["conditional_column_boundary_support"], fixture["id"]
        opening_statuses = [variant["local_diagnostic_state"] for variant in result["opening_provenance"].get("variants", [])]
        assert opening_statuses == expected["opening_variant_statuses"], fixture["id"]
        assert all(variant["subtraction_performed"] is False for variant in result["opening_provenance"].get("variants", [])), fixture["id"]


def _write_json(path: Path, value: object) -> bytes:
    """Write one deterministic JSON artifact and return the exact bytes."""
    payload = _stable_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def _summary_svg(results: list[dict[str, Any]]) -> bytes:
    """Render a compact status summary without depicting geometry or production output."""
    root = ET.Element(f"{{{SVG_NS}}}svg", {"width": "1140", "height": "650", "viewBox": "0 0 1140 650"})
    title = ET.SubElement(root, f"{{{SVG_NS}}}text", {"x": "24", "y": "32", "font-family": "Arial, sans-serif", "font-size": "22", "font-weight": "700", "fill": "#17212b"})
    title.text = "D6 B2 — synthetic geometry contract fixtures"
    subtitle = ET.SubElement(root, f"{{{SVG_NS}}}text", {"x": "24", "y": "58", "font-family": "Arial, sans-serif", "font-size": "13", "fill": "#475569"})
    subtitle.text = "Diagnostic summary only · no IFC result · no production tolerance or opening policy"

    colors = {"computed": "#15803d", "partial": "#b45309", "invalid": "#b91c1c", "not_available": "#64748b"}
    card_width, card_height, gap = 350, 166, 14
    for index, result in enumerate(results):
        row, column = divmod(index, 3)
        x, y = 24 + column * (card_width + gap), 88 + row * (card_height + gap)
        status = result["source_components"]["status"]
        color = colors.get(status, "#475569")
        group = ET.SubElement(root, f"{{{SVG_NS}}}g")
        ET.SubElement(group, f"{{{SVG_NS}}}rect", {"x": str(x), "y": str(y), "width": str(card_width), "height": str(card_height), "rx": "8", "fill": "#ffffff", "stroke": "#cbd5e1", "stroke-width": "1"})
        ET.SubElement(group, f"{{{SVG_NS}}}rect", {"x": str(x), "y": str(y), "width": "6", "height": str(card_height), "rx": "3", "fill": color})

        def add_text(text: str, offset_y: int, size: int = 13, weight: str = "400", fill: str = "#334155") -> None:
            """Add one escaped SVG text line to the current fixture card."""
            element = ET.SubElement(group, f"{{{SVG_NS}}}text", {"x": str(x + 16), "y": str(y + offset_y), "font-family": "Arial, sans-serif", "font-size": str(size), "font-weight": weight, "fill": fill})
            element.text = text

        add_text(result["fixture_id"], 22, 12, "700", color)
        title_lines = textwrap.wrap(result["title"], width=44)[:2]
        add_text(title_lines[0] if title_lines else "", 43, 14, "700", "#17212b")
        if len(title_lines) > 1:
            add_text(title_lines[1], 60, 14, "700", "#17212b")
        polygon_status = result["candidate_polygon_validity"]["status"]
        opening_kind = result["opening_provenance"]["kind"]
        add_text(f"source topology: {status} · components: {result['source_components']['component_count']}", 86)
        add_text(f"column boundary support: {'yes (diagnostic)' if result['boundary_support']['conditional_support_in_this_fixture'] else 'no'}", 108)
        add_text(f"candidate polygon: {polygon_status}", 130)
        add_text(f"opening source: {opening_kind} · subtraction: no", 152)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> int:
    """Run the nine-fixture probe and write deterministic results plus run provenance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    fixtures_path = args.fixtures.resolve()
    output_dir = args.output_dir.resolve()
    fixture_bytes = fixtures_path.read_bytes()
    fixture_payload = json.loads(fixture_bytes)
    helper = importlib.import_module(HELPER_MODULE)
    fixture_rows = fixture_payload["fixtures"]
    results = [_observe_fixture(fixture, helper._topology_status) for fixture in fixture_rows]
    _verify_results(fixture_rows, results)
    result_payload = {
        "schema_version": "d6-b2-synthetic-results-v1",
        "evidence_class": "synthetic_design_evidence",
        "owner_decision": {"commit": "9b50bb1f44c0ae7dc2807c17da084d1ab8163393", "B2": "REVISE", "B5": "narrow_APPROVE"},
        "status_vocabulary_note": "Local diagnostic observations reuse existing labels; this file does not define a unified public status enum.",
        "geometry_library": {"name": "Shapely", "version": shapely_version},
        "fixture_count": len(results),
        "results": results,
    }
    result_bytes = _write_json(output_dir / "results.json", result_payload)
    svg_bytes = _summary_svg(results)
    (output_dir / "summary.svg").write_bytes(svg_bytes)
    provenance = {
        "schema_version": "d6-b2-run-provenance-v1",
        "evidence_class": "synthetic_design_evidence",
        "fixture_path": str(fixtures_path),
        "fixture_sha256": _sha256(fixture_bytes),
        "runner_path": str(Path(__file__).resolve()),
        "runner_sha256": _sha256(Path(__file__).read_bytes()),
        "result_path": str(output_dir / "results.json"),
        "result_sha256": _sha256(result_bytes),
        "summary_svg_path": str(output_dir / "summary.svg"),
        "summary_svg_sha256": _sha256(svg_bytes),
        "output_dir": str(output_dir),
        "argv": [str(value) for value in sys.argv],
        "helper": HELPER_MODULE + "._topology_status",
        "helper_scope": "existing exact-endpoint diagnostic only; not a production geometry algorithm or tolerance policy",
        "real_ifc": "not_verified_not_run",
        "blender": "not_run",
        "production_code_modified": False,
    }
    provenance_bytes = _write_json(output_dir / "provenance.json", provenance)
    print(json.dumps({"fixture_count": len(results), "results_sha256": _sha256(result_bytes), "summary_svg_sha256": _sha256(svg_bytes), "provenance_sha256": _sha256(provenance_bytes), "output_dir": str(output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
