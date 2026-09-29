"""Run the D6 inferred-group candidate-field design probe.

The probe is deliberately outside the production feature layer. It expands a
small JSON fixture manifest, reuses describe_group_relations for authored group
evidence, and writes parallel deterministic diagnostic views.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from features.group_self_description import describe_group_relations


ROOT = Path(__file__).resolve().parents[3]
AGGREGATION_SEMANTICS_FIXTURE = Path(__file__).with_name("inferred_group_candidate_field_aggregation_semantics_fixture.json")
CANONICAL_SPACE_KEY_FIXTURE = Path(__file__).with_name("inferred_group_candidate_field_canonical_space_key_fixture.json")


def _polygon(center: list[float], size: list[float]) -> list[list[float]]:
    """Return a deterministic counter-clockwise rectangle ring."""
    cx, cy = center
    width, height = size
    hx, hy = width / 2.0, height / 2.0
    return [[cx - hx, cy - hy], [cx + hx, cy - hy], [cx + hx, cy + hy], [cx - hx, cy + hy]]


def _scene(fixture: dict[str, Any]) -> dict[str, Any]:
    """Expand compact fixture records into the legacy scene input contract."""
    objects: list[dict[str, Any]] = []
    for group in fixture["groups"]:
        for member in group["members"]:
            record = {
                "id": member["id"],
                "furniture_group": group["id"],
                "type_ref": member.get("type"),
                "factual_properties": dict(member.get("factual_properties", {})),
                "geometry_refs": [f"geometry:{member['id']}"],
            }
            if member.get("status", "computed") == "computed":
                points = member.get("points") or _polygon(member["center"], member["size"])
                record["geometry_components"] = [{"exterior": points, "holes": []}]
            else:
                record["geometry_refs"] = []
            objects.append(record)
    for item in fixture.get("context", []):
        record = {"id": item["id"], "role": item.get("role", "context"), "geometry_refs": [f"geometry:{item['id']}"]}
        record["geometry_components"] = [{"exterior": _polygon(item["center"], item["size"]), "holes": []}]
        objects.append(record)
    settings = {"analysis_plane": "xy", "analysis_length_unit": fixture.get("unit", "m"), "geometry_tolerance": 1e-9, "topology_tolerance": 1e-9}
    scene = {"source": "d6-candidate-field-fixture", "adapter_version": "design-probe/1", "input_mode": "synthetic", "settings": settings, "objects": objects}
    if fixture.get("analysis_domain") == "explicit":
        scene["analysis_domain"] = {"id": f"domain:{fixture['id']}", "status": "computed"}
    return scene


def _pair_key(left: str, right: str) -> str:
    """Return a stable unordered group-pair key."""
    return "|".join(sorted((str(left), str(right))))


def _quantile(values: list[float], quantile: float) -> float | None:
    """Compute an inclusive linear quantile without choosing a hidden default."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = quantile * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def _space_record(fixture: dict[str, Any], pair_key: str) -> dict[str, Any]:
    """Return explicit space-field evidence while preserving unavailable state."""
    canonical_pair_key = _pair_key(*pair_key.split("|", 1))
    raw = fixture.get("space_relations", {}).get(canonical_pair_key)
    source_pair_key = canonical_pair_key
    if raw is None:
        # Preserve legacy fixture bytes while accepting noncanonical key order at the design boundary.
        for candidate_key, candidate_value in fixture.get("space_relations", {}).items():
            if "|" in candidate_key and _pair_key(*candidate_key.split("|", 1)) == canonical_pair_key:
                raw, source_pair_key = candidate_value, candidate_key
                break
    raw = raw or {}
    return {
        "status": raw.get("status", "computed" if raw else "not_available"),
        "role_refs": sorted(str(item) for item in raw.get("role_refs", [])),
        "profile": raw.get("profile"),
        "barrier": raw.get("barrier"),
        "source_refs": sorted(str(item) for item in raw.get("source_refs", [])),
        "provenance": {"source": "fixture-space-field", "fixture_id": fixture["id"],
                       "pair_id": canonical_pair_key, "source_pair_id": source_pair_key,
                       "key_normalized": source_pair_key != canonical_pair_key},
    }


def _vetoes(fixture: dict[str, Any], group_a: str, group_b: str) -> list[dict[str, str]]:
    """Collect explicit mutual-exclusion references for one candidate pair."""
    ids = {group_a, group_b}
    conflicts: list[dict[str, str]] = []
    for group in fixture["groups"]:
        if group["id"] not in ids:
            continue
        other = group_b if group["id"] == group_a else group_a
        other_member_ids = {member["id"] for item in fixture["groups"] if item["id"] == other for member in item["members"]}
        for member in group["members"]:
            values = member.get("factual_properties", {}).get("mutual_exclusion", [])
            if isinstance(values, str):
                values = [values]
            for value in values:
                if str(value) in {other, *other_member_ids}:
                    conflicts.append({"source_ref": member["id"], "target_ref": str(value), "kind": "mutual_exclusion"})
    return sorted(conflicts, key=lambda item: (item["source_ref"], item["target_ref"]))


def _relation_vectors(fixture: dict[str, Any], evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build stable channel vectors from the shared relation evidence output."""
    vectors: dict[str, dict[str, Any]] = {}
    for relation in evidence["group_relations"]:
        pair_id = relation["target_id"]
        space = _space_record(fixture, _pair_key(relation["group_a"], relation["group_b"]))
        observations = sorted(relation["member_pair_observations"], key=lambda item: (item["member_a"], item["member_b"]))
        geometry = {"channel": "relation_geometry", "status": relation["status"], "observations": observations, "source_refs": [item["witness"] for item in observations]}
        semantic = {"channel": "semantic", "status": relation["semantic_channel_status"], "negative": relation["negative_evidence"], "conflicts": relation["semantic_conflicts"], "source_refs": sorted(item.get("source", "") for item in relation["semantic_conflicts"])}
        positive = [geometry]
        if space["status"] == "computed":
            positive.append({"channel": "space_field", **space})
        negative = []
        if relation["negative_evidence"]:
            negative.append({"channel": "semantic", "records": relation["negative_evidence"]})
        if space["barrier"] == "blocked":
            negative.append({"channel": "space_field", "status": "blocked", "source_refs": space["source_refs"], "role_refs": space["role_refs"]})
        vectors[pair_id] = {
            "relation_id": pair_id, "group_a": relation["group_a"], "group_b": relation["group_b"],
            "positive_support_vector": sorted(positive, key=lambda item: item["channel"]),
            "negative_evidence_vector": sorted(negative, key=lambda item: item["channel"]),
            "space_role_refs": space["role_refs"], "space_record": space,
            "missingness": sorted({item["reason"] for item in observations if item.get("reason")} | ({"space_field_unavailable"} if space["status"] != "computed" else set())),
            "status": relation["status"], "semantic_conflicts": relation["semantic_conflicts"],
            "raw_boundary_gaps": sorted(item["raw_boundary_gap"] for item in observations if item.get("raw_boundary_gap") is not None),
            "normalized_gaps": sorted(item["normalized_boundary_gap"] for item in observations if item.get("normalized_boundary_gap") is not None),
            "provenance": {"source": "describe_group_relations", "relation_source_provenance": relation["source_provenance"]},
        }
    return vectors


def _numeric_gap(vector: dict[str, Any]) -> float | None:
    """Return the minimum computed normalized gap for one group pair."""
    gaps = vector["normalized_gaps"]
    return min(gaps) if gaps else None


def _edge_map(vectors: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Return pair keys and finite normalized gaps for scale recipes."""
    return {key: gap for key, vector in vectors.items() if (gap := _numeric_gap(vector)) is not None}


def _ranked_neighbors(ids: list[str], vectors: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Rank each group's computed neighbors by normalized gap and stable id."""
    ranks = {group_id: {} for group_id in ids}
    for group_id in ids:
        neighbors = []
        for pair_id, vector in vectors.items():
            if group_id not in (vector["group_a"], vector["group_b"]):
                continue
            neighbor = vector["group_b"] if vector["group_a"] == group_id else vector["group_a"]
            gap = _numeric_gap(vector)
            if gap is not None:
                neighbors.append((gap, neighbor))
        for rank, (_, neighbor) in enumerate(sorted(neighbors), start=1):
            ranks[group_id][neighbor] = rank
    return ranks


def _scale_views(fixture: dict[str, Any], vectors: dict[str, dict[str, Any]], recipes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run every pre-registered relative-scale recipe side by side."""
    ids = sorted({vector["group_a"] for vector in vectors.values()} | {vector["group_b"] for vector in vectors.values()})
    edges = _edge_map(vectors)
    views: list[dict[str, Any]] = []
    for recipe in recipes:
        recipe_id = recipe["id"]
        parameters = recipe["parameters"]
        if recipe_id == "relative_gap_rank":
            for quantile in parameters["quantiles"]:
                bound = _quantile(list(edges.values()), quantile)
                selected = sorted(key for key, value in edges.items() if bound is not None and value <= bound)
                views.append(_scale_view(fixture, vectors, recipe, {"quantile": quantile, "bound": bound}, selected))
        elif recipe_id == "local_persistence_window":
            ranks = _ranked_neighbors(ids, vectors)
            for window in parameters["windows"]:
                for persistence in parameters["persistence"]:
                    selected = []
                    for key, vector in vectors.items():
                        a, b = vector["group_a"], vector["group_b"]
                        if key in edges and max(ranks[a].get(b, 10**6), ranks[b].get(a, 10**6)) <= window:
                            persistent_windows = sum(1 for candidate_window in parameters["windows"] if max(ranks[a].get(b, 10**6), ranks[b].get(a, 10**6)) <= candidate_window)
                            if persistent_windows >= persistence:
                                selected.append(key)
                    views.append(_scale_view(fixture, vectors, recipe, {"window": window, "persistence": persistence}, sorted(selected)))
        elif recipe_id == "space_profile_rank":
            profiles = [vector["space_record"]["profile"] for vector in vectors.values() if vector["space_record"]["profile"] is not None]
            for quantile in parameters["quantiles"]:
                bound = _quantile(profiles, quantile)
                selected = sorted(key for key, vector in vectors.items() if vector["space_record"]["profile"] is not None and bound is not None and vector["space_record"]["profile"] >= bound)
                views.append(_scale_view(fixture, vectors, recipe, {"quantile": quantile, "bound": bound}, selected))
    return views


def _scale_view(fixture: dict[str, Any], vectors: dict[str, dict[str, Any]], recipe: dict[str, Any], parameters: dict[str, Any], selected: list[str]) -> dict[str, Any]:
    """Serialize one scale view with its complete supporting observations."""
    selected_set = set(selected)
    return {
        "recipe_id": recipe["id"], "parameters": parameters, "provenance": recipe["provenance"],
        "selected_relation_ids": selected, "excluded_relation_ids": sorted(set(vectors) - selected_set),
        "supporting_observations": [vectors[key] for key in selected],
        "space_field": fixture.get("space_field", {"status": "computed" if fixture.get("analysis_domain") else "not_available", "role_candidates": []}),
    }


def _maximal_cliques(ids: list[str], edge_ids: set[str]) -> list[list[str]]:
    """Enumerate finite maximal cliques for a diagnostic candidate view."""
    candidates: list[list[str]] = []
    for size in range(2, len(ids) + 1):
        for combo in itertools.combinations(ids, size):
            if all(_pair_key(a, b) in edge_ids for a, b in itertools.combinations(combo, 2)):
                candidates.append(list(combo))
    return [candidate for candidate in candidates if not any(set(candidate) < set(other) for other in candidates)]


def _connected_components(ids: list[str], edge_ids: set[str]) -> list[list[str]]:
    """Return connected candidate structures while retaining selected pair relations."""
    adjacency = {item: set() for item in ids}
    for pair_id in edge_ids:
        left, right = pair_id.split("|", 1)
        if left in adjacency and right in adjacency:
            adjacency[left].add(right)
            adjacency[right].add(left)
    components = []
    unseen = set(ids)
    while unseen:
        root = min(unseen)
        stack, component = [root], []
        unseen.remove(root)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in sorted(adjacency[current], reverse=True):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        if len(component) > 1:
            components.append(sorted(component))
    return sorted(components)


def _max_span_candidates(ids: list[str], vectors: dict[str, dict[str, Any]], selected: set[str], bound: float | None) -> list[list[str]]:
    """Enumerate maximal connected candidates whose every available pair fits span bound."""
    if bound is None:
        return []
    candidates = []
    for size in range(2, len(ids) + 1):
        for combo in itertools.combinations(ids, size):
            members = set(combo)
            internal_ids = {_pair_key(left, right) for left, right in itertools.combinations(combo, 2)}
            gaps = [min(vectors[pair_id]["normalized_gaps"]) for pair_id in internal_ids
                    if pair_id in vectors and vectors[pair_id]["normalized_gaps"]]
            if len(gaps) != len(internal_ids):
                continue
            if max(gaps) > bound:
                continue
            if len(_connected_components(list(combo), selected & internal_ids)) != 1:
                continue
            candidates.append(sorted(members))
    return [candidate for candidate in candidates if not any(set(candidate) < set(other) for other in candidates)]


def _span_bound(scale_view: dict[str, Any], vectors: dict[str, dict[str, Any]]) -> float | None:
    """Use a gap bound in gap units, never a space-profile quantile as a gap."""
    if scale_view["recipe_id"] == "relative_gap_rank":
        return scale_view["parameters"].get("bound")
    gaps = [min(vectors[pair_id]["normalized_gaps"])
            for pair_id in scale_view["selected_relation_ids"]
            if pair_id in vectors and vectors[pair_id]["normalized_gaps"]]
    # Other scales lack a gap bound; the largest selected gap is a diagnostic span reference.
    return max(gaps) if gaps else None


def _aggregation_membersets(ids: list[str], vectors: dict[str, dict[str, Any]], scale_view: dict[str, Any], recipe_id: str) -> list[list[str]]:
    """Apply one registered aggregation meaning without selecting a production rule."""
    selected = set(scale_view["selected_relation_ids"])
    if recipe_id == "all_pairs":
        return _connected_components(ids, selected)
    if recipe_id == "complete_link_diagnostic":
        return _maximal_cliques(ids, selected)
    if recipe_id == "max_span":
        return _max_span_candidates(ids, vectors, selected, _span_bound(scale_view, vectors))
    if recipe_id == "min_gap":
        return [[vectors[key]["group_a"], vectors[key]["group_b"]] for key in sorted(selected)]
    return []


def _candidate_record(fixture: dict[str, Any], members: list[str], vectors: dict[str, dict[str, Any]], aggregation: dict[str, Any], scale_view: dict[str, Any], all_scale_selected: dict[str, int], candidate_index: int, relation_ids: list[str] | None = None) -> dict[str, Any]:
    """Create one auditable candidate record without producing a formal edge."""
    internal_ids = sorted(relation_ids if relation_ids is not None else (_pair_key(a, b) for a, b in itertools.combinations(members, 2)))
    internal = [vectors[key] for key in internal_ids if key in vectors]
    all_internal_ids = sorted(_pair_key(a, b) for a, b in itertools.combinations(members, 2))
    all_internal = [vectors[key] for key in all_internal_ids if key in vectors]
    missingness = sorted({reason for vector in internal for reason in vector["missingness"]})
    conflicts = sorted((conflict for vector in all_internal for conflict in _vetoes(fixture, vector["group_a"], vector["group_b"])), key=lambda item: (item["source_ref"], item["target_ref"]))
    invalid = any(vector["status"] == "invalid" for vector in internal)
    partial = any(vector["status"] in {"partial", "not_available"} for vector in internal)
    if conflicts:
        status = "unassigned"
    elif invalid:
        status = "diagnostic_only"
    elif aggregation["id"] == "complete_link_diagnostic":
        status = "diagnostic_only"
    elif partial:
        status = "weak"
    elif len(members) > 1 and any(all_scale_selected.get(key, 0) < 2 for key in internal_ids):
        status = "ambiguous"
    else:
        status = "overlapping" if aggregation.get("overlap") else "weak"
    evidence_status = "invalid" if invalid else "partial" if partial else "computed" if internal else "not_available"
    semantic_role = {
        "all_pairs": "selected_relation_connected_structure",
        "max_span": "bounded_cohesion_candidate",
        "min_gap": "pair_witness_only",
        "complete_link_diagnostic": "maximal_clique_complete_link_diagnostic",
    }[aggregation["id"]]
    return {
        "candidate_id": f"{fixture['id']}:{scale_view['recipe_id']}:{aggregation['id']}:{candidate_index}", "members": sorted(members),
        "scale_descriptor": {"recipe_id": scale_view["recipe_id"], "parameters": scale_view["parameters"]},
        "co_membership_evidence": {"selected_pair_count": len(internal_ids), "computed_pair_count": sum(bool(vector["normalized_gaps"]) for vector in internal), "interpretation": "deterministic support; not probability"},
        "candidate_relation_ids": internal_ids,
        "aggregation_semantics": {"role": semantic_role,
                                   "group_partition": False,
                                   "span_bound": _span_bound(scale_view, vectors) if aggregation["id"] == "max_span" else None},
        "positive_support_vector": sorted([item for vector in internal for item in vector["positive_support_vector"]], key=lambda item: item["channel"]),
        "negative_evidence_vector": sorted([item for vector in internal for item in vector["negative_evidence_vector"]], key=lambda item: item["channel"]),
        "space_role_refs": sorted({role for vector in internal for role in vector["space_role_refs"]}), "mutual_exclusion_conflicts": conflicts,
        "missingness": missingness, "evidence_status": evidence_status, "candidate_status": status,
        "aggregation_recipe": {"id": aggregation["id"], "parameters": aggregation["parameters"], "provenance": aggregation["provenance"]},
        "supporting_observations": internal, "formal_membership_edge": False,
        "provenance": {"source": "d6-design-probe", "fixture_id": fixture["id"], "mechanism": "D1-multi-scale-relation-field", "truth_consumed": False},
    }


def _aggregate(fixture: dict[str, Any], vectors: dict[str, dict[str, Any]], scale_view: dict[str, Any], aggregation_recipes: list[dict[str, Any]], all_scale_selected: dict[str, int]) -> list[dict[str, Any]]:
    """Emit parallel aggregation views and explicit unassigned records."""
    ids = sorted({vector["group_a"] for vector in vectors.values()} | {vector["group_b"] for vector in vectors.values()})
    selected = set(scale_view["selected_relation_ids"])
    views = []
    for recipe in aggregation_recipes:
        membersets = _aggregation_membersets(ids, vectors, scale_view, recipe["id"])
        overlap_counts = {member: sum(member in candidate for candidate in membersets) for member in ids}
        records = []
        for index, members in enumerate(membersets):
            if recipe["id"] == "all_pairs":
                relation_ids = sorted(selected & {_pair_key(left, right) for left, right in itertools.combinations(members, 2)})
            elif recipe["id"] == "min_gap":
                relation_ids = [_pair_key(members[0], members[1])]
            else:
                relation_ids = sorted(_pair_key(left, right) for left, right in itertools.combinations(members, 2))
            records.append(_candidate_record(fixture, members, vectors, {**recipe, "overlap": any(overlap_counts[item] > 1 for item in members)}, scale_view, all_scale_selected, index, relation_ids))
        assigned = {member for candidate in membersets for member in candidate}
        for member in sorted(set(ids) - assigned):
            records.append({
                "candidate_id": f"{fixture['id']}:{scale_view['recipe_id']}:{recipe['id']}:unassigned:{member}", "members": [member],
                "scale_descriptor": {"recipe_id": scale_view["recipe_id"], "parameters": scale_view["parameters"]},
                "co_membership_evidence": {"selected_pair_count": 0, "computed_pair_count": 0, "interpretation": "deterministic support; not probability"},
                "candidate_relation_ids": [],
                "aggregation_semantics": {"role": {"all_pairs": "selected_relation_connected_structure", "max_span": "bounded_cohesion_candidate", "min_gap": "pair_witness_only", "complete_link_diagnostic": "maximal_clique_complete_link_diagnostic"}[recipe["id"]], "group_partition": False, "span_bound": _span_bound(scale_view, vectors) if recipe["id"] == "max_span" else None},
                "positive_support_vector": [], "negative_evidence_vector": [], "space_role_refs": [], "mutual_exclusion_conflicts": [], "missingness": [],
                "evidence_status": "not_available", "candidate_status": "unassigned", "aggregation_recipe": {"id": recipe["id"], "parameters": recipe["parameters"], "provenance": recipe["provenance"]}, "supporting_observations": [], "formal_membership_edge": False,
                "provenance": {"source": "d6-design-probe", "fixture_id": fixture["id"], "truth_consumed": False},
            })
        views.append({"aggregation_recipe": recipe, "selected_relation_ids": sorted(selected), "aggregation_semantics": {"all_pairs": "selected_relation_connected_structure", "max_span": "bounded_cohesion_candidate", "min_gap": "pair_witness_only", "complete_link_diagnostic": "maximal_clique_complete_link_diagnostic"}[recipe["id"]], "candidates": records, "overlapping_members": sorted(member for member, count in overlap_counts.items() if count > 1), "candidate_status": "ambiguous" if len({tuple(item["members"]) for item in records if len(item["members"]) > 1}) > 1 and any(item["candidate_status"] == "overlapping" for item in records) else "computed"})
    return views


def _fixture_result(fixture: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Run D0 and D1 for one fixture using no truth-file input."""
    # Reuse the repository evidence contract so this design probe cannot create
    # a second, silently divergent definition of authored group relations.
    evidence = describe_group_relations(_scene(fixture))
    vectors = _relation_vectors(fixture, evidence)
    scale_views = _scale_views(fixture, vectors, manifest["recipes"]["scale"])
    all_scale_selected: dict[str, int] = {}
    for view in scale_views:
        for relation_id in view["selected_relation_ids"]:
            all_scale_selected[relation_id] = all_scale_selected.get(relation_id, 0) + 1
    d1_views = [{**view, "aggregation_views": _aggregate(fixture, vectors, view, manifest["recipes"]["aggregation"], all_scale_selected)} for view in scale_views]
    return {
        "fixture_id": fixture["id"], "family": fixture["family"],
        "truth_ref": f"scripts/design/group_level/inferred_group_candidate_field_truth.json#/fixtures/{fixture['id']}",
        "d0": {"evidence": evidence, "relation_vectors": [vectors[key] for key in sorted(vectors)], "formal_membership_edge": False},
        "d1": {"candidate_views": d1_views, "formal_membership_edge": False},
        "audit": {"truth_consumed": False, "authored_group_ids": sorted(item["eligible_group_id"] for item in evidence["eligibility"]), "context_object_ids": evidence["space_observations"]["context_references"]},
    }


def _transform_fixture(source: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    """Apply a declared invariance transform to fixture geometry and identifiers."""
    fixture = copy.deepcopy(source)
    scale = float(variant.get("scale", 1.0))
    angle = math.radians(float(variant.get("rotation_degrees", 0.0)))
    tx, ty = variant.get("translation", [0.0, 0.0])

    def transform(point: list[float]) -> list[float]:
        # Apply the same positive scale, frame rotation, and translation to
        # every vertex; normalized relations should therefore be invariant.
        x, y = point[0] * scale, point[1] * scale
        return [x * math.cos(angle) - y * math.sin(angle) + tx, x * math.sin(angle) + y * math.cos(angle) + ty]

    for group in fixture["groups"]:
        for member in group["members"]:
            member["center"] = transform(member["center"])
            member["size"] = [value * scale for value in member.get("size", [1.0, 1.0])]
            if "points" in member:
                member["points"] = [transform(point) for point in member["points"]]
    if variant.get("rename_prefix"):
        prefix = str(variant["rename_prefix"])
        group_mapping = {group["id"]: prefix + group["id"] for group in fixture["groups"]}
        for group in fixture["groups"]:
            group["id"] = group_mapping[group["id"]]
            for member in group["members"]:
                member["id"] = prefix + member["id"]
        fixture["space_relations"] = {
            _pair_key(group_mapping.get(left, left), group_mapping.get(right, right)): value
            for pair_id, value in fixture.get("space_relations", {}).items()
            for left, right in [pair_id.split("|", 1)]
        }
    if variant.get("reverse_groups"):
        fixture["groups"].reverse()
    if variant.get("reverse_members"):
        for group in fixture["groups"]:
            group["members"].reverse()
    fixture["unit"] = variant.get("unit", fixture.get("unit", "m"))
    return fixture


def _signature(result: dict[str, Any]) -> list[tuple[str, str, float | None]]:
    """Return an ID-order-independent relation signature for invariance checks."""
    values = []
    for vector in result["d0"]["relation_vectors"]:
        gap = _numeric_gap(vector)
        values.append((vector["status"], "|".join(sorted(vector["missingness"])), round(gap, 8) if gap is not None else None))
    return sorted(values)


def _invariance(manifest: dict[str, Any], fixture_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Run declared transforms and compare canonical relation signatures."""
    source = next(item for item in manifest["fixtures"] if item["id"] == manifest["invariance"]["source_fixture"])
    baseline = _signature(fixture_results[source["id"]])
    checks = []
    for variant in manifest["invariance"]["variants"]:
        transformed = _fixture_result(_transform_fixture(source, variant), manifest)
        checks.append({"variant": variant["id"], "passed": _signature(transformed) == baseline, "signature": _signature(transformed), "frame_id": variant["frame_id"], "truth_consumed": False})
    return {"baseline_fixture": source["id"], "checks": checks, "all_passed": all(item["passed"] for item in checks)}


def _context_check(manifest: dict[str, Any], fixture_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Verify context perturbation changes references without changing node eligibility."""
    source = next(item for item in manifest["fixtures"] if item["id"] == "context_perturbation")
    perturbed = copy.deepcopy(source)
    perturbed.setdefault("context", []).append(source["context_perturbation"]["add"])
    baseline = fixture_results[source["id"]]
    changed = _fixture_result(perturbed, manifest)
    baseline_ids = baseline["audit"]["authored_group_ids"]
    changed_ids = changed["audit"]["authored_group_ids"]
    baseline_context = baseline["audit"]["context_object_ids"]
    changed_context = changed["audit"]["context_object_ids"]
    return {"fixture": source["id"], "node_eligibility_unchanged": baseline_ids == changed_ids, "context_refs_changed": baseline_context != changed_context, "baseline_context": baseline_context, "perturbed_context": changed_context, "truth_consumed": False}


def aggregation_semantics_assertion() -> dict[str, Any]:
    """Assert three aggregation recipes retain distinct design meanings."""
    fixture = json.loads(AGGREGATION_SEMANTICS_FIXTURE.read_text(encoding="utf-8"))
    vectors = {}
    for pair_id, gap in fixture["normalized_gaps"].items():
        left, right = pair_id.split("|", 1)
        vectors[pair_id] = {"group_a": left, "group_b": right, "normalized_gaps": [gap]}
    scale_view = {"recipe_id": "relative_gap_rank", "selected_relation_ids": fixture["selected_relation_ids"], "parameters": {"bound": fixture["span_bound"]}}
    ids = fixture["group_ids"]
    outputs = {recipe_id: _aggregation_membersets(ids, vectors, scale_view, recipe_id)
               for recipe_id in ("all_pairs", "max_span", "complete_link_diagnostic")}
    canonical = {recipe_id: [sorted(candidate) for candidate in outputs[recipe_id]] for recipe_id in outputs}
    assert canonical == fixture["expected_membersets"]
    assert len({json.dumps(value, sort_keys=True) for value in canonical.values()}) == 3
    return {"fixture_id": fixture["id"], "selected_relation_ids": fixture["selected_relation_ids"],
            "span_bound": fixture["span_bound"], "observed_membersets": canonical,
            "passed": True, "truth_consumed": False}


def canonical_space_key_assertion(manifest: dict[str, Any]) -> dict[str, Any]:
    """Assert legacy unordered space keys resolve to one canonical pair key."""
    fixture = json.loads(CANONICAL_SPACE_KEY_FIXTURE.read_text(encoding="utf-8"))
    result = _fixture_result(fixture, manifest)
    vector = next(item for item in result["d0"]["relation_vectors"] if item["relation_id"] == fixture["expected"]["canonical_pair_id"])
    space = vector["space_record"]
    assert space["status"] == "computed"
    assert space["profile"] == fixture["expected"]["profile"]
    assert space["provenance"]["pair_id"] == fixture["expected"]["canonical_pair_id"]
    assert space["provenance"]["source_pair_id"] == fixture["expected"]["source_pair_id"]
    assert space["provenance"]["key_normalized"] is True
    return {"fixture_id": fixture["id"], "canonical_pair_id": space["provenance"]["pair_id"],
            "source_pair_id": space["provenance"]["source_pair_id"], "profile": space["profile"],
            "passed": True, "truth_consumed": False}


def design_semantics_assertions(manifest: dict[str, Any]) -> dict[str, Any]:
    """Run repair-specific assertions without reading evaluation truth."""
    return {"aggregation_semantics": aggregation_semantics_assertion(),
            "canonical_space_key": canonical_space_key_assertion(manifest)}


def _assertions(results: dict[str, dict[str, Any]], invariance: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Run the smallest assertions that fail if design semantics regress."""
    bridge = results["bridge_chain"]
    assert bridge["d0"]["evidence"]["candidate_view_status"] == "deferred"
    assert bridge["d1"]["formal_membership_edge"] is False
    assert any(view["aggregation_views"] for view in bridge["d1"]["candidate_views"])
    veto = results["space_conflict"]["d1"]["candidate_views"]
    # The veto must remain visible even when geometry would otherwise support
    # the pair; this guards precedence without selecting a production policy.
    assert any(candidate["candidate_status"] == "unassigned" and candidate["mutual_exclusion_conflicts"] for view in veto for aggregation in view["aggregation_views"] for candidate in aggregation["candidates"])
    missing = results["missing_invalid"]["d0"]["evidence"]
    statuses = {item["target_id"]: item["geometry_status"] for item in missing["group_geometry"]}
    assert statuses["PARTIAL"] == "partial" and statuses["INVALID"] == "invalid" and statuses["MISSING_GEOMETRY"] == "not_available"
    assert invariance["all_passed"]
    repair = design_semantics_assertions(manifest)
    assert repair["aggregation_semantics"]["passed"] and repair["canonical_space_key"]["passed"]
    return ["D0 candidate view remains deferred", "D1 emits parallel recipes with no formal edge", "hard veto wins and retains source refs", "partial/invalid/missing remain categorical", "declared invariance transforms preserve canonical relation signature", "context perturbation preserves authored node eligibility", "aggregation recipes produce distinct design outputs", "unordered space keys resolve through canonical lookup"]


def run(manifest: dict[str, Any]) -> dict[str, Any]:
    """Execute the complete design-only probe and return JSON-safe evidence."""
    fixture_results = {fixture["id"]: _fixture_result(fixture, manifest) for fixture in manifest["fixtures"]}
    invariance = _invariance(manifest, fixture_results)
    context_check = _context_check(manifest, fixture_results)
    assert context_check["node_eligibility_unchanged"] and context_check["context_refs_changed"]
    return {
        "schema": "d6-inferred-group-candidate-field-experiment/v1", "design_only": True,
        "truth_input": {"consumed": False, "reason": "probe CLI accepts fixture manifest only; computational truth is external"},
        "membership_estimand": manifest["membership_estimand"],
        "synthetic_holdout": manifest["synthetic_holdout"],
        "fixture_count": len(fixture_results), "fixtures": fixture_results, "invariance": invariance, "context_perturbation": context_check,
        "design_semantics_assertions": design_semantics_assertions(manifest),
        "assertions": _assertions(fixture_results, invariance, manifest),
        "mechanisms": {
            "D0": {"status": "computed", "description": "describe_group_relations evidence plus local relation vectors"},
            "D1": {"status": "computed", "description": "parallel relative-scale and aggregation diagnostics"},
            "B1": {"status": "not_run", "reason": "estimand, prior, likelihood, spatial dependence, identifiability and calibration are not owner-approved"},
            "M1": {"status": "not_run", "reason": "feature representation, algorithm, hyperparameters, seed and validation target are not pre-registered; no dependency installation"},
        },
        "limitations": [
            "Fixtures are complete synthetic computational units; members and pairs within a fixture are not independent samples.",
            "co_membership_evidence is deterministic support, not probability.",
            "No candidate view writes formal_membership_edge, authored membership, route path, or public model state.",
            "Space role records are separate from relation evidence and remain unavailable when the domain is missing.",
            "No absolute distance threshold is used; relative recipes are reported side by side.",
            "The external truth manifest is not read by the probe and is not evidence of psychological validity.",
        ],
    }


def main() -> None:
    """Load a pre-registered manifest, run assertions, and write evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.fixtures.read_bytes()
    manifest = json.loads(raw)
    evidence = run(manifest)
    evidence["fixture_manifest"] = str(args.fixtures).replace("\\", "/")
    evidence["fixture_manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    evidence["recipe_registry"] = manifest["recipes"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"schema": evidence["schema"], "fixture_count": evidence["fixture_count"], "fixture_manifest_sha256": evidence["fixture_manifest_sha256"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
