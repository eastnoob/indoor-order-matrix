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
STATUS_MATRIX_FIXTURE = Path(__file__).with_name("inferred_group_candidate_field_status_matrix_fixture.json")


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
    """Return canonicalized space evidence with every source key and explicit conflicts."""
    canonical_pair_key = _pair_key(*pair_key.split("|", 1))
    sources = [(key, value) for key, value in fixture.get("space_relations", {}).items()
               if "|" in key and _pair_key(*key.split("|", 1)) == canonical_pair_key]
    source_records = [{"source_pair_id": key, "record": value} for key, value in sources]
    raw = sources[0][1] if sources else {}
    signatures = {json.dumps(value, sort_keys=True, separators=(",", ":")) for _, value in sources}
    conflict = len(signatures) > 1
    status = "conflict" if conflict else raw.get("status", "computed" if raw else "not_available")
    return {
        "status": status,
        "role_refs": sorted({str(item) for _, value in sources for item in value.get("role_refs", [])}) if not conflict else [],
        "profile": None if conflict else raw.get("profile"),
        "barrier": None if conflict else raw.get("barrier"),
        "source_refs": sorted({str(item) for _, value in sources for item in value.get("source_refs", [])}),
        "provenance": {"source": "fixture-space-field", "fixture_id": fixture["id"],
                       "pair_id": canonical_pair_key,
                       "source_pair_id": sources[0][0] if len(sources) == 1 else None,
                       "source_pair_ids": [key for key, _ in sources],
                       "source_records": source_records,
                       "key_normalized": any(key != canonical_pair_key for key, _ in sources),
                       "key_conflict": conflict},
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
        negative = []
        if space["status"] == "computed":
            positive.append({"channel": "space_field", **space})
        elif space["status"] == "conflict":
            negative.append({"channel": "space_field", **space})
        if relation["negative_evidence"]:
            negative.append({"channel": "semantic", "records": relation["negative_evidence"]})
        if space["barrier"] == "blocked":
            negative.append({"channel": "space_field", "status": "blocked", "source_refs": space["source_refs"], "role_refs": space["role_refs"]})
        vectors[pair_id] = {
            "relation_id": pair_id, "group_a": relation["group_a"], "group_b": relation["group_b"],
            "positive_support_vector": sorted(positive, key=lambda item: item["channel"]),
            "negative_evidence_vector": sorted(negative, key=lambda item: item["channel"]),
            "space_role_refs": space["role_refs"], "space_record": space,
            "missingness": sorted({item["reason"] for item in observations if item.get("reason")} | ({"space_field_conflict"} if space["status"] == "conflict" else {"space_field_unavailable"} if space["status"] != "computed" else set())),
            "status": relation["status"], "semantic_conflicts": relation["semantic_conflicts"],
            "raw_boundary_gaps": sorted(item["raw_boundary_gap"] for item in observations if item.get("raw_boundary_gap") is not None),
            "normalized_gaps": sorted(item["normalized_boundary_gap"] for item in observations if item.get("normalized_boundary_gap") is not None),
            "provenance": {"source": "describe_group_relations", "relation_source_provenance": relation["source_provenance"]},
        }
    return vectors


def _numeric_gap(vector: dict[str, Any]) -> float | None:
    """Return the minimum computed normalized gap for one group pair."""
    # ponytail: minimum member gap is a diagnostic shortcut; upgrade to an explicit
    # group-level gap definition before any production selector uses this value.
    gaps = vector["normalized_gaps"]
    return min(gaps) if gaps else None


def _edge_map(vectors: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Return pair keys and finite normalized gaps for scale recipes."""
    return {key: gap for key, vector in vectors.items()
            if vector.get("status") == "computed" and (gap := _numeric_gap(vector)) is not None and math.isfinite(gap)}


def _ranked_neighbors(ids: list[str], vectors: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Rank each group's computed neighbors by normalized gap and stable id."""
    # Equal gaps are deterministically ordered by neighbor id; this keeps output
    # reproducible while leaving tie semantics as an explicit design limitation.
    ranks = {group_id: {} for group_id in ids}
    for group_id in ids:
        neighbors = []
        for pair_id, vector in vectors.items():
            if group_id not in (vector["group_a"], vector["group_b"]):
                continue
            neighbor = vector["group_b"] if vector["group_a"] == group_id else vector["group_a"]
            gap = _numeric_gap(vector)
            if vector.get("status") == "computed" and gap is not None and math.isfinite(gap):
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
            # Only a computed finite profile can enter a profile rank; missing or
            # conflicting space evidence stays categorical in the relation vector.
            profiles = [space["profile"] for vector in vectors.values()
                        if (space := vector["space_record"])["status"] == "computed"
                        and space["profile"] is not None and math.isfinite(space["profile"])]
            for quantile in parameters["quantiles"]:
                bound = _quantile(profiles, quantile)
                selected = sorted(key for key, vector in vectors.items()
                                  if vector["space_record"]["status"] == "computed"
                                  and (profile := vector["space_record"]["profile"]) is not None
                                  and math.isfinite(profile) and bound is not None and profile >= bound)
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
                    if pair_id in vectors and vectors[pair_id].get("status") == "computed"
                    and vectors[pair_id]["normalized_gaps"]
                    and all(math.isfinite(value) for value in vectors[pair_id]["normalized_gaps"])]
            if len(gaps) != len(internal_ids):
                continue
            if max(gaps) > bound:
                continue
            components = _connected_components(list(combo), selected & internal_ids)
            if len(components) != 1 or set(components[0]) != members:
                continue
            candidates.append(sorted(members))
    return [candidate for candidate in candidates if not any(set(candidate) < set(other) for other in candidates)]


def _span_bound(scale_view: dict[str, Any], vectors: dict[str, dict[str, Any]]) -> float | None:
    """Use a gap bound in gap units, never a space-profile quantile as a gap."""
    if scale_view["recipe_id"] == "relative_gap_rank":
        return scale_view["parameters"].get("bound")
    gaps = [min(vectors[pair_id]["normalized_gaps"])
            for pair_id in scale_view["selected_relation_ids"]
            if pair_id in vectors and vectors[pair_id].get("status") == "computed"
            and vectors[pair_id]["normalized_gaps"]
            and all(math.isfinite(value) for value in vectors[pair_id]["normalized_gaps"])]
    # Other scales lack a gap bound; the largest selected gap is a diagnostic span reference.
    return max(gaps) if gaps else None


def _aggregation_membersets(ids: list[str], vectors: dict[str, dict[str, Any]], scale_view: dict[str, Any], recipe_id: str) -> list[list[str]]:
    """Apply one registered aggregation meaning without selecting a production rule."""
    selected = set(scale_view["selected_relation_ids"])
    if recipe_id == "selected_relation_connected":
        return _connected_components(ids, selected)
    if recipe_id == "all_internal_pairs":
        eligible = {key for key in selected if key in vectors and vectors[key].get("status") == "computed"
                    and vectors[key].get("normalized_gaps")
                    and all(math.isfinite(value) for value in vectors[key]["normalized_gaps"])}
        return _maximal_cliques(ids, eligible)
    if recipe_id == "complete_link_diagnostic":
        return _maximal_cliques(ids, selected)
    if recipe_id == "max_span":
        return _max_span_candidates(ids, vectors, selected, _span_bound(scale_view, vectors))
    if recipe_id == "min_gap":
        return [[vectors[key]["group_a"], vectors[key]["group_b"]] for key in sorted(selected) if key in vectors]
    return []


def _candidate_record(fixture: dict[str, Any], members: list[str], vectors: dict[str, dict[str, Any]], aggregation: dict[str, Any], scale_view: dict[str, Any], all_scale_selected: dict[str, int], candidate_index: int, relation_ids: list[str] | None = None) -> dict[str, Any]:
    """Create one auditable candidate record without producing a formal edge."""
    internal_ids = sorted(relation_ids if relation_ids is not None else (_pair_key(a, b) for a, b in itertools.combinations(members, 2)))
    internal = [vectors[key] for key in internal_ids if key in vectors]
    # A selected key without a relation record remains incomplete evidence;
    # graph connectivity alone cannot turn that absence into a valid pair.
    missing_ids = [key for key in internal_ids if key not in vectors]
    all_internal_ids = sorted(_pair_key(a, b) for a, b in itertools.combinations(members, 2))
    all_internal = [vectors[key] for key in all_internal_ids if key in vectors]
    missingness = sorted({reason for vector in internal for reason in vector["missingness"]} |
                         ({"required_relation_absent"} if missing_ids else set()))
    conflicts = sorted(
        (
            conflict
            for left, right in itertools.combinations(members, 2)
            for conflict in _vetoes(fixture, left, right)
        ),
        key=lambda item: (item["source_ref"], item["target_ref"]),
    )
    invalid = any(vector["status"] == "invalid" for vector in internal)
    partial = bool(missing_ids) or any(vector["status"] in {"missing", "partial", "not_available"} for vector in internal)
    if conflicts:
        status = "unassigned"
    elif invalid:
        status = "diagnostic_only"
    elif aggregation["id"] == "complete_link_diagnostic":
        status = "diagnostic_only"
    elif partial:
        status = "partial"
    elif len(members) > 1 and any(all_scale_selected.get(key, 0) < 2 for key in internal_ids):
        status = "ambiguous"
    else:
        status = "overlapping" if aggregation.get("overlap") else "weak"
    evidence_status = "invalid" if invalid else "partial" if partial else "computed" if internal else "not_available"
    semantic_role = {
        "selected_relation_connected": "selected_relation_connected_structure",
        "all_internal_pairs": "all_internal_pair_requirement",
        "max_span": "bounded_cohesion_candidate",
        "min_gap": "pair_witness_only",
        "complete_link_diagnostic": "maximal_clique_complete_link_diagnostic",
    }[aggregation["id"]]
    return {
        "candidate_id": f"{fixture['id']}:{scale_view['recipe_id']}:{aggregation['id']}:{candidate_index}", "members": sorted(members),
        "scale_descriptor": {"recipe_id": scale_view["recipe_id"], "parameters": scale_view["parameters"]},
        "co_membership_evidence": {
            "selected_pair_count": sum(pair_id in set(scale_view["selected_relation_ids"]) for pair_id in internal_ids),
            "computed_pair_count": sum(
                vector.get("status") == "computed"
                and vector.get("normalized_gaps")
                and all(math.isfinite(value) for value in vector["normalized_gaps"])
                for vector in internal
            ),
            "interpretation": "deterministic support; not probability",
        },
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
    ids = sorted(group["id"] for group in fixture["groups"])
    selected = set(scale_view["selected_relation_ids"])
    views = []
    for recipe in aggregation_recipes:
        membersets = _aggregation_membersets(ids, vectors, scale_view, recipe["id"])
        overlap_counts = {member: sum(member in candidate for candidate in membersets) for member in ids}
        records = []
        for index, members in enumerate(membersets):
            if recipe["id"] == "selected_relation_connected":
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
                "aggregation_semantics": {"role": {"selected_relation_connected": "selected_relation_connected_structure", "all_internal_pairs": "all_internal_pair_requirement", "max_span": "bounded_cohesion_candidate", "min_gap": "pair_witness_only", "complete_link_diagnostic": "maximal_clique_complete_link_diagnostic"}[recipe["id"]], "group_partition": False, "span_bound": _span_bound(scale_view, vectors) if recipe["id"] == "max_span" else None},
                "positive_support_vector": [], "negative_evidence_vector": [], "space_role_refs": [], "mutual_exclusion_conflicts": [], "missingness": [],
                "evidence_status": "not_available", "candidate_status": "unassigned", "aggregation_recipe": {"id": recipe["id"], "parameters": recipe["parameters"], "provenance": recipe["provenance"]}, "supporting_observations": [], "formal_membership_edge": False,
                "provenance": {"source": "d6-design-probe", "fixture_id": fixture["id"], "truth_consumed": False},
            })
        views.append({"aggregation_recipe": recipe, "selected_relation_ids": sorted(selected), "aggregation_semantics": {"selected_relation_connected": "selected_relation_connected_structure", "all_internal_pairs": "all_internal_pair_requirement", "max_span": "bounded_cohesion_candidate", "min_gap": "pair_witness_only", "complete_link_diagnostic": "maximal_clique_complete_link_diagnostic"}[recipe["id"]], "candidates": records, "overlapping_members": sorted(member for member, count in overlap_counts.items() if count > 1), "candidate_status": "ambiguous" if len({tuple(item["members"]) for item in records if len(item["members"]) > 1}) > 1 and any(item["candidate_status"] == "overlapping" for item in records) else "computed"})
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
        """Apply the declared frame transform to one fixture point."""
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
    """Assert five aggregation diagnostics, including strict all-internal variants."""
    fixture = json.loads(AGGREGATION_SEMANTICS_FIXTURE.read_text(encoding="utf-8"))
    observed_cases = []
    tie_vectors = {
        "A|B": {"group_a": "A", "group_b": "B", "status": "computed", "normalized_gaps": [1.0]},
        "A|C": {"group_a": "A", "group_b": "C", "status": "computed", "normalized_gaps": [1.0]},
    }
    tie_ranks = _ranked_neighbors(["A", "B", "C"], tie_vectors)
    assert tie_ranks["A"] == {"B": 1, "C": 2}
    renamed_ties = _ranked_neighbors(["A", "C", "Z"], {
        "A|Z": {"group_a": "A", "group_b": "Z", "status": "computed", "normalized_gaps": [1.0]},
        "A|C": tie_vectors["A|C"],
    })
    assert renamed_ties["A"] == {"C": 1, "Z": 2}
    minimum_gap_vector = {"normalized_gaps": [0.2, 0.8]}
    assert _numeric_gap(minimum_gap_vector) == 0.2
    disjoint_vectors = {
        "A|B": {"group_a": "A", "group_b": "B", "status": "computed", "normalized_gaps": [1.0]},
        "C|D": {"group_a": "C", "group_b": "D", "status": "computed", "normalized_gaps": [1.0]},
    }
    disjoint_scale = {"recipe_id": "relative_gap_rank", "selected_relation_ids": ["A|B", "C|D"], "parameters": {"bound": 1.0}}
    maximal_sets = _aggregation_membersets(["A", "B", "C", "D"], disjoint_vectors, disjoint_scale, "all_internal_pairs")
    assert maximal_sets == [["A", "B"], ["C", "D"]]
    for case in fixture["cases"]:
        vectors = {}
        for pair_id, status in case["relation_status"].items():
            left, right = pair_id.split("|", 1)
            vectors[pair_id] = {"group_a": left, "group_b": right, "status": status,
                                "normalized_gaps": [case["normalized_gaps"][pair_id]] if pair_id in case["normalized_gaps"] else [],
                                "missingness": [] if status == "computed" else [status],
                                "positive_support_vector": [], "negative_evidence_vector": [], "space_role_refs": []}
        scale_view = {"recipe_id": "relative_gap_rank", "selected_relation_ids": case["selected_relation_ids"], "parameters": {"bound": fixture["span_bound"]}}
        observed = {}
        for recipe_id, expected in case["expected"].items():
            membersets = [sorted(item) for item in _aggregation_membersets(fixture["group_ids"], vectors, scale_view, recipe_id)]
            relation_ids = []
            for members in membersets:
                if recipe_id in {"selected_relation_connected", "min_gap"}:
                    relation_ids.append(sorted(set(case["selected_relation_ids"]) & {_pair_key(a, b) for a, b in itertools.combinations(members, 2)}))
                else:
                    relation_ids.append(sorted(_pair_key(a, b) for a, b in itertools.combinations(members, 2)))
            diagnostic_fixture = {"id": case["id"], "groups": [{"id": item, "members": []} for item in fixture["group_ids"]]}
            statuses = [_candidate_record(diagnostic_fixture, members, vectors,
                                          {"id": recipe_id, "parameters": {}, "provenance": "self-check"},
                                          scale_view, {pair_id: 2 for pair_id in vectors}, index, ids_for_candidate)["candidate_status"]
                        for index, (members, ids_for_candidate) in enumerate(zip(membersets, relation_ids))]
            observed[recipe_id] = {"membersets": membersets, "relation_ids": relation_ids, "status": sorted(set(statuses))}
            assert membersets == expected["membersets"], (case["id"], recipe_id, membersets)
            assert relation_ids == expected["relation_ids"], (case["id"], recipe_id, relation_ids)
            assert observed[recipe_id]["status"] == sorted(expected["status"]), (case["id"], recipe_id, observed[recipe_id]["status"])
            assert expected["overlap_policy"] == "overlap_allowed"
        if "expected_all_internal_rejected_pair" in case:
            assert case["expected_all_internal_rejected_pair"] not in sum((item["relation_ids"] for item in [observed["all_internal_pairs"]]), [])
        selected_ineligible = [
            pair_id for pair_id, status in case["relation_status"].items()
            if pair_id in case["selected_relation_ids"] and status != "computed"
        ]
        if selected_ineligible:
            connected_ids = [pair for group in observed["selected_relation_connected"]["relation_ids"] for pair in group]
            strict_ids = [pair for group in observed["all_internal_pairs"]["relation_ids"] for pair in group]
            assert set(selected_ineligible) <= set(connected_ids)
            assert not (set(selected_ineligible) & set(strict_ids))
        observed_cases.append({"id": case["id"], "observed": observed,
                               "selected_but_ineligible": selected_ineligible})
    return {"fixture_id": fixture["id"], "cases": observed_cases, "passed": True,
            "tie_policy": "equal gaps are ordered by neighbor id for deterministic diagnostics",
            "tie_policy_is_not_invariance": True,
            "tie_rename_counterexample": {"before": tie_ranks["A"], "after_B_to_Z": renamed_ties["A"]},
            "numeric_gap_policy": "minimum member gap retained as diagnostic only",
            "disjoint_maximal_sets": maximal_sets,
            "truth_consumed": False}


def diagnostic_regression_assertion() -> dict[str, Any]:
    """Assert the three controller-review counterexamples stay repaired."""
    base_scale = {"recipe_id": "relative_gap_rank", "parameters": {"bound": 1.0}, "selected_relation_ids": ["A|B"]}
    aggregation = {"id": "selected_relation_connected", "parameters": {}, "provenance": "self-check"}

    span_fixture = {"id": "repair_r1", "groups": [{"id": item, "members": []} for item in ("A", "B", "C")]}
    span_vectors = {
        pair_id: {"group_a": pair_id.split("|", 1)[0], "group_b": pair_id.split("|", 1)[1], "status": "computed", "normalized_gaps": [1.0],
                  "missingness": [], "positive_support_vector": [], "negative_evidence_vector": [], "space_role_refs": []}
        for pair_id in ("A|B", "A|C", "B|C")
    }
    span_membersets = _max_span_candidates(["A", "B", "C"], span_vectors, {"A|B"}, 1.0)
    span_views = _aggregate(span_fixture, span_vectors, base_scale, [{"id": "max_span", "parameters": {}, "provenance": "self-check"}], {"A|B": 1})
    span_candidates = span_views[0]["candidates"]
    assert span_membersets == [["A", "B"]]
    assert any(item["members"] == ["C"] and item["candidate_status"] == "unassigned" for item in span_candidates)

    def vector(pair_id: str, status: str = "computed", gaps: list[float] | None = None) -> dict[str, Any]:
        left, right = pair_id.split("|", 1)
        return {"group_a": left, "group_b": right, "status": status, "normalized_gaps": [1.0] if gaps is None else gaps,
                "missingness": [], "positive_support_vector": [], "negative_evidence_vector": [], "space_role_refs": []}

    counter_fixture = {"id": "repair_r2", "groups": [{"id": item, "members": []} for item in ("A", "B", "C")]}
    counter_vectors = {"A|B": vector("A|B", "invalid"), "A|C": vector("A|C"), "B|C": vector("B|C")}
    counter = _candidate_record(counter_fixture, ["A", "B", "C"], counter_vectors, aggregation, base_scale, {"A|B": 1}, 0)
    nonfinite_vectors = {**counter_vectors, "B|C": vector("B|C", gaps=[math.nan])}
    nonfinite = _candidate_record(counter_fixture, ["A", "B", "C"], nonfinite_vectors, aggregation, base_scale, {"A|B": 1}, 0)
    assert counter["co_membership_evidence"] == {"selected_pair_count": 1, "computed_pair_count": 2, "interpretation": "deterministic support; not probability"}
    assert nonfinite["co_membership_evidence"]["computed_pair_count"] == 1

    veto_fixture = {"id": "repair_r3", "groups": [
        {"id": "A", "members": [{"id": "a", "factual_properties": {"mutual_exclusion": ["C"]}}]},
        {"id": "B", "members": [{"id": "b", "factual_properties": {}}]},
        {"id": "C", "members": [{"id": "c", "factual_properties": {}}]},
    ]}
    veto_vectors = {"A|B": vector("A|B"), "B|C": vector("B|C")}
    veto = _candidate_record(veto_fixture, ["A", "B", "C"], veto_vectors, aggregation,
                             {"recipe_id": "relative_gap_rank", "parameters": {}, "selected_relation_ids": ["A|B", "B|C"]},
                             {"A|B": 2, "B|C": 2}, 0, ["A|B", "B|C"])
    assert veto["mutual_exclusion_conflicts"] == [{"source_ref": "a", "target_ref": "C", "kind": "mutual_exclusion"}]
    assert veto["candidate_status"] == "unassigned"
    return {"passed": True, "truth_consumed": False,
            "r1": {"max_span_membersets": span_membersets, "aggregate_members": [item["members"] for item in span_candidates]},
            "r2": {"finite": counter["co_membership_evidence"], "nonfinite_computed_pair_count": nonfinite["co_membership_evidence"]["computed_pair_count"]},
            "r3": {"mutual_exclusion_conflicts": veto["mutual_exclusion_conflicts"], "candidate_status": veto["candidate_status"]}}


def status_matrix_assertion() -> dict[str, Any]:
    """Assert actual candidate propagation keeps missingness categorical."""
    fixture = json.loads(STATUS_MATRIX_FIXTURE.read_text(encoding="utf-8"))
    assert _edge_map({"A|B": {"status": "invalid", "normalized_gaps": [0.0]},
                      "A|C": {"status": "computed", "normalized_gaps": [1.0]}}) == {"A|C": 1.0}
    profile_vectors = {
        "A|B": {"group_a": "A", "group_b": "B", "status": "computed", "normalized_gaps": [1.0],
                "space_record": {"status": "computed", "profile": 0.8}},
        "A|C": {"group_a": "A", "group_b": "C", "status": "computed", "normalized_gaps": [1.0],
                "space_record": {"status": "conflict", "profile": 0.9}},
    }
    profile_recipe = {"id": "space_profile_rank", "parameters": {"quantiles": [0.5]}, "provenance": "self-check"}
    assert _scale_views({"id": "status_probe"}, profile_vectors, [profile_recipe])[0]["selected_relation_ids"] == ["A|B"]
    for case in fixture["cases"]:
        assert case["numeric_gap"] is None
        assert case["relation_missingness"]
        if case["id"] == "selected_invalid_relation":
            assert case["relation_status"] == case["evidence_status"] == "invalid"
            assert case["candidate_status"] == "diagnostic_only"
        elif case["id"] in {"selected_missing_relation", "selected_unavailable_relation"} or case["relation_status"] == "partial":
            assert case["evidence_status"] == case["candidate_status"] == "partial"
        else:
            assert case["evidence_status"] == "not_available"
            assert case["candidate_status"] == "unassigned"
    groups = [{"id": group_id, "members": []} for group_id in ("A", "B")]
    recipe = {"id": "selected_relation_connected", "parameters": {}, "provenance": "self-check"}
    strict_recipe = {**recipe, "id": "all_internal_pairs"}
    scale_view = {"recipe_id": "relative_gap_rank", "parameters": {}, "selected_relation_ids": ["A|B"]}
    propagated = {}
    for relation_status, expected_candidate in (("missing", "partial"), ("invalid", "diagnostic_only"), ("partial", "partial"), ("not_available", "partial")):
        vector = {"group_a": "A", "group_b": "B", "status": relation_status,
                  "normalized_gaps": [], "missingness": [relation_status],
                  "positive_support_vector": [], "negative_evidence_vector": [], "space_role_refs": []}
        # A selected but ineligible relation stays visible in connected diagnostics,
        # while strict all-internal aggregation cannot promote it into a group.
        vectors = {} if relation_status == "missing" else {"A|B": vector}
        connected, strict = _aggregate({"id": "status_probe", "groups": groups}, vectors,
                                       scale_view, [recipe, strict_recipe], {})
        candidate = connected["candidates"][0]
        assert candidate["members"] == ["A", "B"]
        expected_evidence = "invalid" if relation_status == "invalid" else "partial"
        assert candidate["evidence_status"] == expected_evidence
        assert candidate["candidate_status"] == expected_candidate
        assert candidate["missingness"] == (["required_relation_absent"] if relation_status == "missing" else [relation_status])
        assert all(item["candidate_status"] == "unassigned" for item in strict["candidates"])
        propagated[relation_status] = {"evidence_status": candidate["evidence_status"],
                                       "candidate_status": candidate["candidate_status"]}
    singleton = _aggregate(
        {"id": "singleton_probe", "groups": [{"id": "A"}]}, {},
        {"recipe_id": "relative_gap_rank", "parameters": {}, "selected_relation_ids": []},
        [{"id": "selected_relation_connected", "parameters": {}, "provenance": "self-check"}], {},
    )[0]["candidates"]
    assert singleton[0]["members"] == ["A"] and singleton[0]["candidate_status"] == "unassigned"
    return {"fixture_id": fixture["id"], "case_count": len(fixture["cases"]),
            "selected_ineligible_propagation": propagated,
            "singleton_output": singleton[0], "passed": True, "truth_consumed": False}

def canonical_space_key_assertion(manifest: dict[str, Any]) -> dict[str, Any]:
    """Assert reverse-only normalization and explicit multi-source conflict provenance."""
    fixture = json.loads(CANONICAL_SPACE_KEY_FIXTURE.read_text(encoding="utf-8"))
    result = _fixture_result(fixture, manifest)
    vectors = {item["relation_id"]: item for item in result["d0"]["relation_vectors"]}
    reverse = vectors[fixture["expected"]["reverse_only"]["canonical_pair_id"]]["space_record"]
    conflict = vectors[fixture["expected"]["conflict"]["canonical_pair_id"]]["space_record"]
    assert reverse["status"] == "computed" and reverse["profile"] == 0.6
    assert reverse["provenance"]["source_pair_ids"] == ["TALL|PLAIN"]
    assert conflict["status"] == "conflict" and conflict["profile"] is None
    assert conflict["provenance"]["key_conflict"] is True
    assert conflict["provenance"]["source_pair_ids"] == ["TALL|ROUNDISH", "ROUNDISH|TALL"]
    assert len(conflict["provenance"]["source_records"]) == 2
    return {"fixture_id": fixture["id"], "reverse_only": reverse["provenance"], "conflict": conflict["provenance"], "passed": True, "truth_consumed": False}

def design_semantics_assertions(manifest: dict[str, Any]) -> dict[str, Any]:
    """Run repair-specific assertions without reading evaluation truth."""
    return {"aggregation_semantics": aggregation_semantics_assertion(),
            "diagnostic_regressions": diagnostic_regression_assertion(),
            "status_matrix": status_matrix_assertion(),
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
    assert repair["aggregation_semantics"]["passed"] and repair["diagnostic_regressions"]["passed"] and repair["status_matrix"]["passed"] and repair["canonical_space_key"]["passed"]
    return ["D0 candidate view remains deferred", "D1 emits parallel recipes with no formal edge", "hard veto wins and retains source refs", "partial/invalid/missing remain categorical", "declared invariance transforms preserve canonical relation signature", "context perturbation preserves authored node eligibility", "aggregation recipes preserve distinct design meanings", "R1/R2/R3 diagnostic regressions remain repaired", "status matrix forbids numeric missingness imputation", "unordered space keys preserve provenance and conflicts"]


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
            "Canonical-equivalent multi-source space keys remain explicit conflicts; no source is silently selected.",
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
