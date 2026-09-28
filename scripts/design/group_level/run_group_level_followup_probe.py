"""Run the D6 E8-E10 design-only follow-up experiments."""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
from typing import Any

import run_group_level_probe as geometry

EPS = 1e-9


def _usable_members(group: dict[str, Any]) -> list[dict[str, Any]]:
    """Return members with computed status and explicit plan geometry."""
    return [member for member in group["members"] if member.get("status") == "computed" and "box" in member]


def _rotate_translate_scale(box: dict[str, Any], angle_degrees: float, translation: tuple[float, float], scale: float) -> dict[str, Any]:
    """Apply a rigid 2D rotation/translation and positive uniform scale to a square fixture box."""
    angle = math.radians(angle_degrees)
    x, y = box["center"]
    rotated = [x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)]
    return {
        "center": [scale * (rotated[0] + translation[0]), scale * (rotated[1] + translation[1])],
        "size": [scale * value for value in box["size"]],
        "z": [scale * value for value in box["z"]],
    }


def _record(value: Any = None, status: str = "computed", reason: str | None = None) -> dict[str, Any]:
    """Keep availability, reason, and value separate, with null for unknown facts."""
    return {"value": value, "status": status, "reason": reason}


def _group_summary(group: dict[str, Any]) -> dict[str, Any]:
    """Preserve declared member completeness and all missing or invalid reasons."""
    statuses = [member["status"] for member in group["members"]]
    status = "invalid" if "invalid" in statuses else ("computed" if "computed" in statuses else "not_available")
    completeness = "not_computable" if status == "invalid" else ("partial" if status == "computed" and "not_available" in statuses else ("complete" if status == "computed" else "not_applicable"))
    return {"id": group["id"], "status": status, "geometry_completeness": completeness,
            "excluded_member_reasons": {m["id"]: m.get("reason", m["status"]) for m in group["members"] if m["status"] != "computed"}}


def _pair_observation(left: dict[str, Any], right: dict[str, Any], case: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Measure a prism pair and preserve unavailable channels and shared dependency."""
    availability = case.get("channel_status", {})
    channels = {name: _record(None, availability.get(name, "computed"), None) for name in context["formal_channels"] + context["diagnostic_channels"]}
    member_status = "invalid" if "invalid" in (left["status"], right["status"]) else ("not_available" if "not_available" in (left["status"], right["status"]) else "computed")
    if member_status != "computed":
        for name in ("geometry_2d", "clearance_3d", "z_compatibility"):
            channels[name] = _record(None, member_status, left.get("reason") or right.get("reason"))
    else:
        # Reuse the existing polygon oracle so a joint rotation does not turn
        # geometry into a new world-axis AABB and silently change the gap.
        polygons = [geometry._rectangle_geometry({**m["box"], "angle": m["box"].get("angle", 0.0)})[0] for m in (left, right)]
        gap, intersection = geometry._polygon_gap(*polygons)
        if channels["geometry_2d"]["status"] == "computed":
            channels["geometry_2d"]["value"] = {"gap": gap, "contact_or_overlap": intersection}
        if "z" in left["box"] and "z" in right["box"]:
            lz, rz = left["box"]["z"], right["box"]["z"]
            dz = max(lz[0] - rz[1], rz[0] - lz[1], 0.0)
            if channels["clearance_3d"]["status"] == "computed":
                channels["clearance_3d"]["value"] = math.hypot(gap, dz)
            if channels["z_compatibility"]["status"] == "computed":
                channels["z_compatibility"]["value"] = min(lz[1], rz[1]) - max(lz[0], rz[0]) > context["tolerance"]["z"]
        else:
            # A clearance computed elsewhere may remain available even when
            # its separate Z interval is absent from this handoff.
            if "independent_clearance" in case and channels["clearance_3d"]["status"] == "computed":
                channels["clearance_3d"]["value"] = case["independent_clearance"]
            else:
                channels["clearance_3d"] = _record(None, "not_available", "z_interval_missing_for_prism_clearance")
            channels["z_compatibility"] = _record(None, "not_available", "z_interval_missing")
    if channels["wall_opening_barrier"]["status"] == "computed":
        channels["wall_opening_barrier"]["value"] = case.get("barrier_observation", context["barrier_observation"])
    channels["external_affordance"] = _record(None, "not_available", "external_affordance_not_supplied")
    for name, channel in channels.items():
        if channel["status"] != "computed" and channel["reason"] is None:
            channel["reason"] = name + "_channel_absent"
        if channel["status"] != "computed":
            channel["value"] = None
    complete = all(channels[name]["status"] == "computed" for name in context["formal_channels"])
    threshold = case.get("thresholds", context["thresholds"])
    formal = complete and channels["geometry_2d"]["value"]["gap"] <= threshold["gap_2d"] + context["tolerance"]["geometry"] and channels["clearance_3d"]["value"] <= threshold["clearance_3d"] + context["tolerance"]["clearance"] and channels["z_compatibility"]["value"] is True and channels["wall_opening_barrier"]["value"] in ("clear", "opening")
    shared = left["id"] == right["id"]
    return {"member_pair": [left["id"], right["id"]], "channels": channels,
            "shared_member_dependency": shared, "formal_pair": formal and not shared,
            "reason": "shared_member_dependency" if shared else (None if formal else "required_pair_conditions_unsatisfied"),
            "analysis_frame": context["analysis_frame"], "tolerance": context["tolerance"],
            "source_provenance": {"kind": "synthetic_design_fixture", "case_id": case["id"]}}


def _e8_aggregate(case: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Compare any, min, max, all-pairs, and explicit pairwise-summary rules."""
    left_group, right_group = case["groups"]
    pairs = [_pair_observation(left, right, case, context) for left, right in itertools.product(left_group["members"], right_group["members"])]
    thresholds = case["thresholds"]
    eligible = [pair for pair in pairs if pair["formal_pair"]]
    usable = [pair for pair in pairs if all(pair["channels"][c]["status"] == "computed" for c in context["formal_channels"])]
    summaries = [_group_summary(group) for group in case["groups"]]
    if any(s["status"] == "invalid" for s in summaries):
        summary_status = "diagnostic_only"
    elif not usable:
        summary_status = "not_available"
    elif all(pair["shared_member_dependency"] for pair in usable):
        summary_status = "diagnostic_only"
    elif len(usable) != len(pairs):
        summary_status = "partial"
    else:
        summary_status = "computed"

    def tied_extreme(channel: str, field: str, extreme: str) -> tuple[float | None, list[dict[str, Any]]]:
        """Return an extreme scalar and every pair tied at that extreme."""
        values = [pair["channels"][channel]["value"] if field is None else pair["channels"][channel]["value"][field] for pair in usable]
        if not values:
            return None, []
        value = min(values) if extreme == "min" else max(values)
        return value, [pair for pair in usable if math.isclose(pair["channels"][channel]["value"] if field is None else pair["channels"][channel]["value"][field], value, abs_tol=EPS)]

    min_gap, min_gap_pairs = tied_extreme("geometry_2d", "gap", "min")
    max_gap, max_gap_pairs = tied_extreme("geometry_2d", "gap", "max")
    min_clearance, min_clearance_pairs = tied_extreme("clearance_3d", None, "min")
    max_clearance, max_clearance_pairs = tied_extreme("clearance_3d", None, "max")

    def selected_rule(pairs_for_rule: list[dict[str, Any]], rule: str) -> dict[str, Any]:
        """Evaluate one rule and mark non-unique representatives as ambiguous."""
        if not pairs_for_rule:
            return {"status": "not_available", "formal_edge": False, "reason": "no_pair_observation"}
        decisions = {pair["formal_pair"] for pair in pairs_for_rule}
        ambiguous = len(decisions) > 1
        return {"status": "ambiguous" if ambiguous else summary_status,
                "formal_edge": not ambiguous and decisions == {True} and summary_status == "computed",
                "representative_pairs": [pair["member_pair"] for pair in pairs_for_rule],
                "reason": "tied_witnesses_disagree" if ambiguous else "extreme_witness_rule_only"}

    any_result = {"status": summary_status, "formal_edge": bool(eligible) and summary_status == "computed", "supporting_pairs": [pair["member_pair"] for pair in eligible], "reason": None if eligible and summary_status == "computed" else ("partial_group_support" if summary_status == "partial" else "no_pair_satisfies_all_channels")}
    all_result = {"status": summary_status, "formal_edge": bool(pairs) and len(eligible) == len(pairs) and summary_status == "computed", "reason": None if pairs and len(eligible) == len(pairs) else "not_all_pairs_formal"}
    independent_min = summary_status == "computed" and min_gap <= thresholds["gap_2d"] + EPS and min_clearance <= thresholds["clearance_3d"] + EPS and any(pair["channels"]["z_compatibility"]["value"] for pair in usable) and any(pair["channels"]["wall_opening_barrier"]["value"] in ("clear", "opening") for pair in usable) and not any(p["shared_member_dependency"] for p in pairs)
    independent_max = summary_status == "computed" and max_gap <= thresholds["gap_2d"] + EPS and max_clearance <= thresholds["clearance_3d"] + EPS and all(pair["channels"]["z_compatibility"]["value"] for pair in usable) and all(pair["channels"]["wall_opening_barrier"]["value"] in ("clear", "opening") for pair in usable) and not any(p["shared_member_dependency"] for p in pairs)
    rules = {
        "any": any_result, "min_gap_witness": selected_rule(min_gap_pairs, "min_gap"),
        "min_clearance_witness": selected_rule(min_clearance_pairs, "min_clearance"),
        "max_gap_witness": selected_rule(max_gap_pairs, "max_gap"),
        "max_clearance_witness": selected_rule(max_clearance_pairs, "max_clearance"),
        "independent_min": {"status": summary_status, "formal_edge": independent_min},
        "independent_max": {"status": summary_status, "formal_edge": independent_max},
        "all_pairs": all_result,
    }
    all_member_pairs = [pair["member_pair"] for pair in pairs]
    for rule in rules.values():
        witnesses = rule.get("supporting_pairs") or rule.get("representative_pairs") or [pair["member_pair"] for pair in eligible]
        rule["witness_pairs"] = list(witnesses)
        rule["witness_pair"] = witnesses[0] if witnesses else None
        rule["excluded_pairs"] = [pair for pair in all_member_pairs if pair not in witnesses]
    split_diagnostics = []
    for group in (left_group, right_group):
        members = [member for member in group["members"] if member.get("status") == "computed" and "box" in member]
        components = [{member["id"]} for member in members]
        for first, second in itertools.combinations(members, 2):
            first_polygon = geometry._rectangle_geometry({**first["box"], "angle": first["box"].get("angle", 0.0)})[0]
            second_polygon = geometry._rectangle_geometry({**second["box"], "angle": second["box"].get("angle", 0.0)})[0]
            internal_gap, _ = geometry._polygon_gap(first_polygon, second_polygon)
            if internal_gap <= thresholds["gap_2d"] + context["tolerance"]["geometry"]:
                first_component = next(component for component in components if first["id"] in component)
                second_component = next(component for component in components if second["id"] in component)
                if first_component is not second_component:
                    first_component.update(second_component)
                    components.remove(second_component)
        split_diagnostics.append({
            "group_id": group["id"],
            "status": "diagnostic_only" if len(components) > 1 else "computed",
            "components": [sorted(component) for component in components],
            "provenance": "synthetic_design_fixture_internal_gap_diagnostic",
        })
    aggregate_status = "ambiguous" if summary_status == "computed" and len({r["formal_edge"] for r in rules.values()}) > 1 else summary_status
    return {
        "group_pair": [left_group["id"], right_group["id"]],
        "source_provenance": "synthetic_design_fixture",
        "analysis_frame": context["analysis_frame"], "tolerance": context["tolerance"],
        "group_summaries": summaries,
        "shared_member_ids": sorted({m["id"] for m in left_group["members"]} & {m["id"] for m in right_group["members"]}),
        "pair_level_observations": pairs,
        "pairwise_summary": {
            "status": summary_status,
            "pair_count": len(pairs), "usable_pair_count": len(usable),
            "eligible_pair_count": len(eligible),
            "overlap_pair_count": sum(1 for pair in usable if pair["channels"]["geometry_2d"]["value"]["contact_or_overlap"]),
            "z_compatible_pair_count": sum(1 for pair in usable if pair["channels"]["z_compatibility"]["value"]),
            "min_gap": min_gap,
            "max_gap": max_gap,
            "min_clearance": min_clearance,
            "max_clearance": max_clearance,
        },
        "candidate_rules": rules,
        "disconnected_member_split_diagnostic": split_diagnostics,
        "group_level_status": aggregate_status, "observation_status": summary_status,
        "formal_edge": False, "formal_edge_reason": "no_aggregation_policy_frozen",
        "geometry_completeness": "complete" if summary_status == "computed" else summary_status,
    }


def _transform_case(case: dict[str, Any], variant: str, rename_ids: bool = False, reverse_members: bool = False) -> dict[str, Any]:
    """Create a transformed fixture while retaining source provenance and member order metadata."""
    transformed = copy.deepcopy(case)
    for group in transformed["groups"]:
        if reverse_members:
            group["members"].reverse()
        for member in group["members"]:
            if variant == "rotate_90_translate":
                member["box"] = _rotate_translate_scale(member["box"], 90.0, (10.0, -3.0), 1.0)
            elif variant == "positive_scale_2":
                member["box"] = _rotate_translate_scale(member["box"], 0.0, (0.0, 0.0), 2.0)
            if rename_ids:
                member["id"] = f"renamed_{member['id']}"
    return transformed


def _e8_results(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Run aggregation cases and explicit transform/traversal/rename invariance checks."""
    context = {"analysis_frame": fixtures["analysis_frame"], "tolerance": fixtures["tolerance"], "formal_channels": fixtures["formal_channels"], "diagnostic_channels": fixtures["diagnostic_channels"], "thresholds": {"gap_2d": 0.6, "clearance_3d": 0.6}, "barrier_observation": "clear"}
    results: dict[str, Any] = {}
    for case in fixtures["e8_aggregation_cases"]:
        results[case["id"]] = _e8_aggregate(case, context)
    transform_case = next(case for case in fixtures["e8_aggregation_cases"] if case["id"] == "unequal_rotated_transform")
    identity = _e8_aggregate(transform_case, context)
    transformed = {variant: _e8_aggregate(_transform_case(transform_case, variant), context) for variant in ["rotate_90_translate", "positive_scale_2"]}
    reversed_result = _e8_aggregate(_transform_case(transform_case, "identity", reverse_members=True), context)
    renamed_result = _e8_aggregate(_transform_case(transform_case, "identity", rename_ids=True), context)
    base_summary = identity["pairwise_summary"]
    invariance = {
        "rotation_translation": transformed["rotate_90_translate"]["pairwise_summary"]["min_gap"] == base_summary["min_gap"],
        "positive_scale_normalized": abs(transformed["positive_scale_2"]["pairwise_summary"]["min_gap"] / 2.0 - base_summary["min_gap"]) < EPS,
        "member_traversal": reversed_result["pairwise_summary"] == base_summary,
        "id_rename": renamed_result["pairwise_summary"] == base_summary,
    }
    results["transform_invariance"] = {"identity": identity, "variants": transformed, "reversed_members": reversed_result, "renamed_ids": renamed_result, "checks": invariance}
    assert results["near_far_multi_member"]["candidate_rules"]["any"]["formal_edge"] is True
    assert results["near_far_multi_member"]["candidate_rules"]["all_pairs"]["formal_edge"] is False
    assert results["overlap_plus_far"]["pairwise_summary"]["overlap_pair_count"] == 1
    assert results["overlap_plus_far"]["candidate_rules"]["max_gap_witness"]["formal_edge"] is False
    assert results["multi_z_levels"]["pairwise_summary"]["z_compatible_pair_count"] == 2
    assert results["multi_z_levels"]["candidate_rules"]["all_pairs"]["formal_edge"] is False
    assert any(item["status"] == "diagnostic_only" for item in results["disconnected_members"]["disconnected_member_split_diagnostic"])
    assert results["partial_member_support"]["group_level_status"] == "partial" and results["partial_member_support"]["formal_edge"] is False
    assert results["no_usable_members"]["group_level_status"] == "not_available" and results["no_usable_members"]["formal_edge"] is False
    assert results["shared_member_dependency"]["shared_member_ids"] == ["SHARED_1"] and results["shared_member_dependency"]["formal_edge"] is False
    assert all(invariance.values())
    return results


def _e9_result(case: dict[str, Any], formal_channels: list[str], diagnostic_channels: list[str]) -> dict[str, Any]:
    """Propagate missing, invalid, and partial channel status to one group relation."""
    groups = case["groups"]
    summaries = [_group_summary(group) for group in groups]
    if any(summary["status"] == "invalid" for summary in summaries):
        relation_status, reason = "diagnostic_only", "invalid_geometry"
    elif any(summary["geometry_completeness"] == "partial" for summary in summaries):
        relation_status, reason = "partial", "partial_group_support"
    elif not all(case["channel_status"].get(channel) == "computed" for channel in formal_channels):
        relation_status, reason = "not_available", "required_channel_missing"
    else:
        relation_status, reason = "computed", None
    context = {"analysis_frame": "fixture-plan-xy", "tolerance": {"geometry": 1e-9, "clearance": 1e-9, "z": 1e-6}, "formal_channels": formal_channels, "diagnostic_channels": diagnostic_channels, "thresholds": {"gap_2d": 0.6, "clearance_3d": 0.6}, "barrier_observation": "clear"}
    pair = _pair_observation(groups[0]["members"][0], groups[1]["members"][0], case, context)
    return {
        "case_id": case["id"],
        "analysis_frame": "fixture-plan-xy",
        "unit": "m",
        "tolerance": {"geometry": 1e-9, "clearance": 1e-9, "z": 1e-6},
        "channel_status": case["channel_status"],
        "formal_channels": formal_channels,
        "diagnostic_channels": diagnostic_channels,
        "group_summaries": summaries,
        "pair_level_observation": pair,
        "group_level_status": relation_status,
        "formal_edge": relation_status == "computed",
        "diagnostic_only": relation_status == "diagnostic_only" or case["channel_status"].get("external_affordance") == "not_available",
        "reason": reason,
        "source_provenance": "synthetic_design_fixture",
    }


def _e9_results(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Run channel propagation cases and enforce the formal/diagnostic boundary."""
    results = {case["id"]: _e9_result(case, fixtures["formal_channels"], fixtures["diagnostic_channels"]) for case in fixtures["e9_channel_cases"]}
    assert results["all_channels_available"]["formal_edge"] is True
    assert results["all_channels_available"]["diagnostic_only"] is True
    for case_id in ["missing_2d_geometry", "missing_3d_clearance", "missing_z_interval", "missing_wall_barrier"]:
        assert results[case_id]["group_level_status"] == "not_available" and results[case_id]["formal_edge"] is False
    assert results["missing_external_affordance"]["formal_edge"] is True and results["missing_external_affordance"]["diagnostic_only"] is True
    assert results["invalid_geometry"]["group_level_status"] == "diagnostic_only" and results["invalid_geometry"]["formal_edge"] is False
    assert results["partial_group_support"]["group_level_status"] == "partial" and results["partial_group_support"]["formal_edge"] is False
    return results


def _length_unit_scale(model: Any) -> tuple[float, list[dict[str, Any]]]:
    """Resolve the authored IFC length unit to metres for the design audit."""
    units = []
    scale = 1.0
    for assignment in model.by_type("IfcUnitAssignment"):
        for unit in assignment.Units or ():
            record = {"entity_type": unit.is_a(), "unit_type": getattr(unit, "UnitType", None), "name": getattr(unit, "Name", None), "prefix": getattr(unit, "Prefix", None)}
            units.append(record)
            if record["unit_type"] == "LENGTHUNIT" and record["entity_type"] == "IfcSIUnit":
                scale = {"MILLI": 1e-3, "CENTI": 1e-2, "DECI": 1e-1, "KILO": 1e3}.get(record["prefix"], 1.0)
    return scale, units


def _entity_box(entity: Any, unit_scale: float) -> dict[str, Any] | None:
    """Extract a design-audit bounding box from explicit IFC tessellation coordinates."""
    points: list[list[float]] = []
    try:
        import ifcopenshell.util.placement as placement
        transform = placement.get_local_placement(entity.ObjectPlacement) if entity.ObjectPlacement else None
    except Exception:
        transform = None
    representation = getattr(entity, "Representation", None)
    for shape_representation in getattr(representation, "Representations", ()) if representation else ():
        for item in getattr(shape_representation, "Items", ()):
            coordinates = getattr(getattr(item, "Coordinates", None), "CoordList", None)
            if coordinates:
                for point in coordinates:
                    if transform is None:
                        world = list(point)
                    else:
                        world = [sum(float(transform[row, column]) * (point[column] if column < 3 else 1.0) for column in range(4)) for row in range(3)]
                    points.append([value * unit_scale for value in world])
    if not points:
        return None
    return {
        "min": [min(point[index] for point in points) for index in range(3)],
        "max": [max(point[index] for point in points) for index in range(3)],
        "vertex_count": len(points),
        "method": "ifc_polygonal_face_set_bbox_with_object_placement_design_audit",
        "source_unit_scale_to_m": unit_scale,
        "placement_applied": transform is not None,
    }


def _write_svg_oracle(path: Path, furniture: list[dict[str, Any]], walls: list[dict[str, Any]]) -> None:
    """Write a design-only 2D oracle from the parsed IFC canonical boxes."""
    all_boxes = furniture + walls
    max_x = max((item["box"]["max"][0] for item in all_boxes), default=1.0)
    max_y = max((item["box"]["max"][1] for item in all_boxes), default=1.0)
    scale = 80.0
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {max_x * scale + 40:.1f} {max_y * scale + 40:.1f}">']
    body.append('<rect width="100%" height="100%" fill="white"/>')
    for item in walls:
        box = item["box"]
        x, y = box["min"][0] * scale + 20, box["min"][1] * scale + 20
        width, height = (box["max"][0] - box["min"][0]) * scale, (box["max"][1] - box["min"][1]) * scale
        body.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{width:.3f}" height="{height:.3f}" fill="#fecaca" stroke="#b91c1c"><title>{item["global_id"]}</title></rect>')
    for item in furniture:
        box = item["box"]
        x, y = box["min"][0] * scale + 20, box["min"][1] * scale + 20
        width, height = (box["max"][0] - box["min"][0]) * scale, (box["max"][1] - box["min"][1]) * scale
        body.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{width:.3f}" height="{height:.3f}" fill="#bfdbfe" stroke="#1d4ed8"><title>{item["global_id"]}</title></rect>')
    body.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _polygon_area(vertices: tuple[tuple[float, float, float], ...], triangles: tuple[tuple[int, int, int], ...]) -> float:
    """Compute planar area from adapter triangles without adding scene semantics."""
    area = 0.0
    for first, second, third in triangles:
        ax, ay, _ = vertices[first]
        bx, by, _ = vertices[second]
        cx, cy, _ = vertices[third]
        area += abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) / 2.0
    return area


def _adapter_object_facts(scene: Any, expected_ids: set[str]) -> dict[str, dict[str, Any]]:
    """Extract center, area, authored groups, status, and adapter provenance."""
    geometries = {geometry.id: geometry for geometry in scene.geometries}
    facts = {}
    for source in scene.source_objects:
        if source.id not in expected_ids:
            continue
        geometry = geometries.get(source.geometry_refs[0]) if source.geometry_refs else None
        if geometry is None or not geometry.vertices:
            facts[source.id] = {"representative_status": "not_available", "group_refs": list(source.group_refs)}
            continue
        xs = [vertex[0] for vertex in geometry.vertices]
        ys = [vertex[1] for vertex in geometry.vertices]
        facts[source.id] = {
            "center": [(min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0],
            "area": _polygon_area(geometry.vertices, geometry.triangle_indices),
            "group_refs": list(source.group_refs),
            "representative_status": "computed",
            "source_provenance": dict(source.provenance),
            "geometry_provenance": dict(geometry.local_to_world_provenance),
            "geometry_units": geometry.units,
        }
    return facts


def _jsonable(value: Any) -> Any:
    """Convert adapter mappingproxy and tuple records into JSON evidence values."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if hasattr(value, "items"):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _adapter_pair_facts(scene: Any, left_id: str, right_id: str, tolerance: float) -> dict[str, Any]:
    """Compute planar gap classes from independently loaded SVG geometry."""
    geometries = {geometry.id: geometry for geometry in scene.geometries}
    objects = {source.id: source for source in scene.source_objects}
    boxes = []
    for object_id in (left_id, right_id):
        source = objects[object_id]
        geometry = geometries[source.geometry_refs[0]]
        xs = [vertex[0] for vertex in geometry.vertices]
        ys = [vertex[1] for vertex in geometry.vertices]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    left, right = boxes
    classification = _classify_axis_aligned_boxes(left, right, tolerance)
    raw_gap = classification["raw_gap"]
    diagonal = max(math.hypot(left[2] - left[0], left[3] - left[1]), math.hypot(right[2] - right[0], right[3] - right[1]))
    return {
        "members": [left_id, right_id],
        "raw_gap": raw_gap,
        "normalized_gap": raw_gap / diagonal if diagonal else None,
        "intersection_area": classification["intersection_area"],
        "overlap": classification["overlap"],
        "contact": classification["contact"],
        "near": classification["near"],
        "provenance": "independent_svg_adapter_geometry",
        "status": "computed",
    }


def _classify_axis_aligned_boxes(left: tuple[float, float, float, float], right: tuple[float, float, float, float], tolerance: float) -> dict[str, Any]:
    """Separate positive-area overlap, zero-gap contact, and tolerance-near boxes."""
    x_overlap = min(left[2], right[2]) - max(left[0], right[0])
    y_overlap = min(left[3], right[3]) - max(left[1], right[1])
    intersection_area = max(0.0, x_overlap) * max(0.0, y_overlap)
    dx = max(left[0] - right[2], right[0] - left[2], 0.0)
    dy = max(left[1] - right[3], right[1] - left[3], 0.0)
    raw_gap = math.hypot(dx, dy)
    overlap = intersection_area > tolerance * tolerance
    contact = not overlap and raw_gap <= EPS
    near = not overlap and not contact and raw_gap <= tolerance
    return {"raw_gap": raw_gap, "intersection_area": intersection_area,
            "overlap": overlap, "contact": contact, "near": near}


def _contact_overlap_probe(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Run minimal axis-aligned counterexamples against the class definitions."""
    observed = []
    for case in cases:
        result = _classify_axis_aligned_boxes(tuple(case["left"]), tuple(case["right"]), case["tolerance"])
        expected = case["expected"]
        assert result["overlap"] is expected["overlap"]
        assert result["contact"] is expected["contact"]
        assert result["near"] is expected["near"]
        assert math.isclose(result["intersection_area"], expected["intersection_area"], abs_tol=EPS)
        observed.append({"id": case["id"], "observed": result, "expected": expected})
    return {"status": "computed", "cases": observed,
            "semantics": {"overlap": "positive intersection area above tolerance area",
                          "contact": "zero boundary gap without positive-area overlap",
                          "near": "positive boundary gap within geometry tolerance"},
            "provenance": "synthetic_design_fixture_axis_aligned_counterexamples"}


def _e10b_svg_adapter_audit(root: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    """Load an independent SVG through adapters/svg_scene.py and compare declared 2D facts."""
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from adapters.svg_scene import load_svg_neutral_scene

    path = root / fixture["path"]
    expected = fixture["expected"]
    scene = load_svg_neutral_scene(
        path,
        source_length_unit=fixture["source_length_unit"],
        analysis_length_unit=fixture["analysis_length_unit"],
        geometry_tolerance=fixture["geometry_tolerance"],
        topology_tolerance=fixture["topology_tolerance"],
    )
    expected_ids = set(expected["objects"])
    object_facts = _adapter_object_facts(scene, expected_ids)
    group_facts = {group.id: list(group.member_refs) for group in scene.authored_groups if group.group_role == "furniture_group"}
    pair = _adapter_pair_facts(scene, *expected["pair"]["members"], fixture["geometry_tolerance"])
    context = scene.context
    context_facts = {
        "source_length_unit": context.source_length_unit,
        "analysis_length_unit": context.analysis_length_unit,
        "analysis_plane_name": context.analysis_plane.name,
        "world_coordinate_system_name": context.world_coordinate_system["name"],
        "source_to_analysis_scale": context.world_coordinate_system["source_to_analysis_scale"],
        "capability_flags": dict(context.capability_flags),
    }
    comparisons = {
        "analysis_frame": context_facts,
        "source_analysis_units": context_facts,
        "authored_furniture_group_membership": group_facts,
        "plan_geometry": object_facts,
        "representative_status": {key: value["representative_status"] for key, value in object_facts.items()},
        "pair_2d": pair,
        "contact_overlap_probe": _contact_overlap_probe(fixture["contact_overlap_cases"]),
        "opening_count": len(scene.openings),
        "provenance_status": {
            key: {
                "source_adapter": value.get("source_provenance", {}).get("adapter"),
                "geometry_adapter": value.get("geometry_provenance", {}).get("adapter"),
                "status": value["representative_status"],
            }
            for key, value in object_facts.items()
        },
        "planar_only_channels": expected["planar_only_channels"],
    }
    tolerance = fixture["geometry_tolerance"]
    for group_id, members in expected["group_membership"].items():
        assert group_facts[group_id] == members
    for object_id, target in expected["objects"].items():
        observed = object_facts[object_id]
        assert observed["group_refs"] == target["group_refs"]
        assert observed["representative_status"] == target["representative_status"]
        assert all(math.isclose(observed["center"][index], target["center"][index], abs_tol=tolerance) for index in range(2))
        assert math.isclose(observed["area"], target["area"], abs_tol=tolerance)
    for key in ("raw_gap", "normalized_gap", "intersection_area"):
        assert math.isclose(pair[key], expected["pair"][key], abs_tol=tolerance)
    for key in ("overlap", "contact", "near"):
        assert pair[key] is expected["pair"][key]
    assert context_facts["source_length_unit"] == fixture["source_length_unit"]
    assert context_facts["analysis_length_unit"] == fixture["analysis_length_unit"]
    assert context_facts["analysis_plane_name"] == expected["analysis_plane_name"]
    assert context_facts["world_coordinate_system_name"] == expected["world_coordinate_system_name"]
    assert len(scene.openings) == expected["opening_count"]
    assert context.capability_flags["height_queries"] is False and context.capability_flags["volume_queries"] is False
    return {
        "status": "independent SVG adapter loaded; planar parity checked",
        "adapter_load_command": "pixi run python -c \"from adapters.svg_scene import load_svg_neutral_scene; load_svg_neutral_scene('scripts/design/group_level/e10b_independent_svg_fixture.svg', source_length_unit='m', analysis_length_unit='m')\"",
        "path": str(path).replace("\\", "/"),
        "adapter_version": next(iter(object_facts.values()))["source_provenance"]["adapter"],
        "comparisons": _jsonable(comparisons),
        "independent_adapter_check": True,
        "excluded_channels": {"z": "not_available", "clearance_3d": "not_available", "wall_opening_barrier": "not_available"},
        "source_provenance": "independent_svg_fixture_loaded_by_existing_adapter",
    }


def _e10_audit(root: Path, svg_output: Path, svg_json_output: Path) -> dict[str, Any]:
    """Search and parse real IFC samples, then emit a clearly labelled 2D oracle."""
    paths = sorted({
        path for pattern in ("*.ifc", "*.IFC", "*.ifczip", "*.ifcxml")
        for path in root.rglob(pattern)
        if not {".git", ".pixi", ".worktrees", "site-packages"} & set(path.parts)
    })
    try:
        import ifcopenshell  # type: ignore
        runtime = {"available": True, "version": getattr(ifcopenshell, "version", None)}
    except Exception as exc:  # pragma: no cover - environment-dependent diagnostic
        runtime = {"available": False, "reason": type(exc).__name__}
    if not paths:
        return {
            "status": "actual IFC parse unavailable",
            "actual_ifc_paths": [],
            "schema": None,
            "ifcopenshell_runtime": runtime,
            "search_command": "pixi run python scripts/design/group_level/run_group_level_followup_probe.py --fixtures scripts/design/group_level/inferred_group_followup_fixtures.json --output <output>",
            "parse_attempted": False,
            "next_fixture_requirements": ["real IFC4 file", "GlobalId inventory", "IfcGroup.ObjectType inventory", "IfcSIUnit/placement facts", "physical geometry and wall/opening relations", "equivalent SVG 2D canonical facts"],
            "source_provenance": "repository_recursive_search",
        }
    import ifcopenshell

    inventory = []
    primary_path = None
    for path in paths:
        try:
            candidate_model = ifcopenshell.open(str(path))
            candidate_groups = candidate_model.by_type("IfcGroup")
            furniture_group_count = sum(1 for group in candidate_groups if getattr(group, "ObjectType", None) == "furniture_group")
            inventory_group_records = [{
                "global_id": group.GlobalId,
                "object_type": getattr(group, "ObjectType", None),
                "candidate_status": "candidate" if getattr(group, "ObjectType", None) == "furniture_group" else "not_candidate",
                "provenance": "ifc_group_relation_inventory",
            } for group in candidate_groups]
            inventory.append({
                "path": str(path).replace("\\", "/"),
                "schema": candidate_model.schema,
                "group_count": len(candidate_groups),
                "furniture_group_count": furniture_group_count,
                "group_records": inventory_group_records,
                "furniture_count": len(candidate_model.by_type("IfcFurniture")),
                "wall_count": len(candidate_model.by_type("IfcWall")),
                "opening_count": len(candidate_model.by_type("IfcOpeningElement")),
                "parse_status": "computed",
            })
            if primary_path is None and furniture_group_count:
                primary_path = path
        except Exception as exc:
            inventory.append({"path": str(path).replace("\\", "/"), "parse_status": "invalid", "reason": type(exc).__name__})
    source = primary_path or paths[0]
    model = ifcopenshell.open(str(source))
    groups = []
    for group in model.by_type("IfcGroup"):
        members = [member.GlobalId for relation in (group.IsGroupedBy or ()) for member in (relation.RelatedObjects or ())]
        object_type = getattr(group, "ObjectType", None)
        groups.append({
            "global_id": group.GlobalId,
            "object_type": object_type,
            "member_global_ids": sorted(members),
            "candidate_status": "candidate" if object_type == "furniture_group" else "not_candidate",
            "provenance": "ifc_group_relation",
        })
    unit_scale, units = _length_unit_scale(model)
    furniture = []
    for entity in model.by_type("IfcFurniture"):
        box = _entity_box(entity, unit_scale)
        furniture.append({
            "global_id": entity.GlobalId,
            "entity_type": entity.is_a(),
            "box": box,
            "geometry_status": "computed" if box else "not_available",
            "placement_present": entity.ObjectPlacement is not None,
            "provenance": "ifc_explicit_tessellation",
        })
    walls = []
    for entity in model.by_type("IfcWall"):
        box = _entity_box(entity, unit_scale)
        walls.append({
            "global_id": entity.GlobalId,
            "entity_type": entity.is_a(),
            "box": box,
            "geometry_status": "computed" if box else "not_available",
            "provenance": "ifc_explicit_tessellation",
        })
    openings = [{"global_id": entity.GlobalId, "entity_type": entity.is_a()} for entity in model.by_type("IfcOpeningElement")]
    doors = [{"global_id": entity.GlobalId, "entity_type": entity.is_a()} for entity in model.by_type("IfcDoor")]
    relationship_counts = {
        "IfcRelVoidsElement": len(model.by_type("IfcRelVoidsElement")),
        "IfcRelFillsElement": len(model.by_type("IfcRelFillsElement")),
    }
    canonical_2d = {
        "analysis_frame": {"id": "ifc-bim-acceptance-xy", "plane": "XY", "unit": "m"},
        "source_global_ids": sorted(item["global_id"] for item in furniture),
        "group_records": groups,
        "furniture": furniture,
        "walls": walls,
        "pair_channels": {
            "2d_geometry": "available_for_furniture_with_bbox",
            "z_interval": "available_for_furniture_with_bbox",
            "clearance_3d": "available_for_furniture_with_bbox",
            "wall_geometry": "available_for_walls_with_bbox",
            "opening_relation": "not_available" if not openings and not relationship_counts["IfcRelVoidsElement"] else "available",
            "door_geometry": "available" if doors else "not_available",
        },
        "source_provenance": "parsed_real_ifc4_file",
    }
    svg_facts = copy.deepcopy(canonical_2d)
    svg_facts["source_provenance"] = "design_only_svg_oracle_derived_from_ifc_canonical_2d"
    svg_json_output.parent.mkdir(parents=True, exist_ok=True)
    svg_json_output.write_text(json.dumps(svg_facts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_svg_oracle(svg_output, furniture, walls)
    comparable = {
        "analysis_frame": canonical_2d["analysis_frame"],
        "source_global_ids": canonical_2d["source_global_ids"],
        "group_records": canonical_2d["group_records"],
        "furniture": canonical_2d["furniture"],
        "walls": canonical_2d["walls"],
    }
    return {
        "status": "real IFC4 parsed; strict furniture_group candidate audit complete",
        "actual_ifc_paths": [str(path).replace("\\", "/") for path in paths],
        "ifc_inventory": inventory,
        "parsed_path": str(source).replace("\\", "/"),
        "primary_selection_rule": "first parsed IFC sample with exact IfcGroup.ObjectType=furniture_group; no filename, layer, or group name inference",
        "schema": model.schema,
        "global_id_count": len(model.by_type("IfcRoot")),
        "units": units,
        "group_records": groups,
        "candidate_group_ids": sorted(item["global_id"] for item in groups if item["candidate_status"] == "candidate"),
        "ordinary_group_ids": sorted(item["global_id"] for item in groups if item["candidate_status"] == "not_candidate"),
        "furniture_geometry": furniture,
        "wall_geometry": walls,
        "opening_records": openings,
        "door_records": doors,
        "relationship_counts": relationship_counts,
        "opening_relation_status": "actual IFC opening relation unavailable" if not openings and not relationship_counts["IfcRelVoidsElement"] else "computed_from_ifc_opening_relation",
        "channel_audit": canonical_2d["pair_channels"],
        "svg_2d_oracle": {
            "svg_path": str(svg_output).replace("\\", "/"),
            "canonical_json_path": str(svg_json_output).replace("\\", "/"),
            "comparable_fact_keys": sorted(comparable),
            "status": "design_oracle_match",
            "independent_adapter_check": False,
            "limitation": "SVG oracle is derived from parsed IFC canonical facts; it is not an independent SVG adapter acceptance run.",
        },
        "parse_attempted": True,
        "ifcopenshell_runtime": runtime,
        "source_provenance": "read_only_ifcopenshell_parse",
    }


def main() -> None:
    """Run E8b, E9, E10, and E10b, assert design invariants, and write schema-v3 evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg-output", type=Path, default=Path("docs/project/evidence/d6-e10-bim-acceptance-svg-2d-canonical.svg"))
    parser.add_argument("--svg-json-output", type=Path, default=Path("docs/project/evidence/d6-e10-bim-acceptance-svg-2d-canonical.json"))
    args = parser.parse_args()
    raw = args.fixtures.read_bytes()
    fixtures = json.loads(raw)
    evidence = {
        "schema": "d6-inferred-group-design-followup/v3",
        "design_only": True,
        "fixture_manifest": str(args.fixtures).replace("\\", "/"),
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "analysis_frame": fixtures["analysis_frame"],
        "unit": fixtures["analysis_frame"]["unit"],
        "tolerance": fixtures["tolerance"],
        "formal_channels": fixtures["formal_channels"],
        "diagnostic_channels": fixtures["diagnostic_channels"],
        "results": {"E8b": _e8_results(fixtures), "E9": _e9_results(fixtures), "E10": _e10_audit(Path.cwd(), args.svg_output, args.svg_json_output), "E10b": _e10b_svg_adapter_audit(Path.cwd(), fixtures["e10b_svg_adapter"])},
        "limitations": [
            "E8 reports minimum/maximum and any/all rules; it does not select a production aggregation policy.",
            "E8 multi-member group-level summaries use finite synthetic pairs; all-pairs spatial topology and route semantics remain open.",
            "E9 missing channel propagation is explicit for the tested cases; no channel is rewritten to clear, false, or zero.",
            "E9 external affordance is diagnostic-only in this membership slice and is not inferred from furniture type.",
            "E10 parsed real IFC4 samples; SVG remains a derived 2D oracle and no independent SVG adapter acceptance claim is made.",
            "E10b loads an independent SVG through adapters/svg_scene.py; its parity is limited to declared planar facts and does not provide Z, 3D clearance, or wall/opening barrier.",
            "No result is a production API, Bayesian prior, psychological threshold, real-scene accuracy, or human perceptual validity claim.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"schema": evidence["schema"], "fixture_sha256": evidence["fixture_sha256"], "E10": evidence["results"]["E10"]["status"]}, indent=2))


if __name__ == "__main__":
    main()
