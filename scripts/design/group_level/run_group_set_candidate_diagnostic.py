"""Build multi-group candidate-set diagnostics from retained IFC relations.

This runner deliberately separates set-level proposal shape from membership,
strength, and winner selection. It reuses the pinned IFC-derived seed profile
and projected group geometry; it does not load IFC or create synthetic data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .run_seed_candidate_profile_experiment import _bounds, _group_shapes, _path, _xml


DEFAULT_SEED_RUN = (
    Path(__file__).resolve().parents[3]
    / "outputs/design/group_seed_candidate_experiment/run_20261027T_seed_profile_v1"
)
DEFAULT_GEOMETRY_RUN = (
    Path(__file__).resolve().parents[3]
    / "outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96"
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[3]
    / "outputs/design/group_set_candidate_diagnostic/run_20261028T_set_level_v1"
)

RECIPES = (
    "nearest-neighbour-components",
    "contact-components",
    "nearest-neighbour-complete-link",
    "contact-complete-link",
)
GRAPH_BASES = ("nearest-neighbour", "contact")


def _read_json(path: Path) -> Any:
    """Read one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    """Write deterministic JSON for a diagnostic artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _graphs(seed_document: Mapping[str, Any]) -> dict[str, dict[str, set[str]]]:
    """Build undirected nearest-neighbour and contact graphs from all seed views."""
    group_ids = sorted(str(group_id) for group_id in seed_document["views"][0]["scope_group_ids"])
    graphs = {base: {group_id: set() for group_id in group_ids} for base in GRAPH_BASES}
    for view in seed_document["views"]:
        seed_id = str(view["seed_group_id"])
        related = [item for item in view["members"] if item.get("role") == "scope_member"]
        minimum = min(float(item["relation"]["normalized_boundary_gap"]["minimum"]) for item in related)
        for item in related:
            group_id = str(item["group_id"])
            relation = item["relation"]
            if abs(float(relation["normalized_boundary_gap"]["minimum"]) - minimum) <= 1e-12:
                graphs["nearest-neighbour"][seed_id].add(group_id)
                graphs["nearest-neighbour"][group_id].add(seed_id)
            if int(relation["contact_count"]) > 0:
                graphs["contact"][seed_id].add(group_id)
                graphs["contact"][group_id].add(seed_id)
    return graphs


def _components(graph: Mapping[str, set[str]]) -> list[list[str]]:
    """Return deterministic connected components for an undirected graph."""
    unseen = set(graph)
    result: list[list[str]] = []
    while unseen:
        start = min(unseen)
        stack = [start]
        unseen.remove(start)
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in sorted(graph[node] & unseen, reverse=True):
                unseen.remove(neighbor)
                stack.append(neighbor)
        result.append(sorted(component))
    return sorted(result, key=lambda members: (members[0], len(members), members))


def _relation_lookup(seed_document: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Index each unordered pair relation from the retained seed profiles."""
    lookup: dict[str, dict[str, Any]] = {}
    for view in seed_document["views"]:
        for item in view["members"]:
            if item.get("role") != "scope_member":
                continue
            relation = item["relation"]
            lookup[str(relation["pair_id"])] = relation
    return lookup


def _maximal_cliques(graph: Mapping[str, set[str]]) -> list[list[str]]:
    """Return deterministic maximal cliques for a small diagnostic graph."""
    cliques: list[list[str]] = []

    def visit(current: set[str], possible: set[str], excluded: set[str]) -> None:
        """Enumerate maximal cliques with Bron-Kerbosch recursion."""
        if not possible and not excluded:
            if len(current) >= 2:
                cliques.append(sorted(current))
            return
        pivot_pool = possible | excluded
        pivot = max(pivot_pool, key=lambda node: (len(graph[node] & possible), node)) if pivot_pool else None
        blocked = graph[pivot] if pivot is not None else set()
        for node in sorted(possible - blocked):
            visit(current | {node}, possible & graph[node], excluded & graph[node])
            possible.remove(node)
            excluded.add(node)

    visit(set(), set(graph), set())
    return sorted(cliques, key=lambda members: (members[0], len(members), members))


def _candidate_sets(recipe: str, graph: Mapping[str, set[str]]) -> list[list[str]]:
    """Build component or complete-link candidate sets for one graph."""
    if recipe.endswith("-components"):
        return _components(graph)
    cliques = _maximal_cliques(graph)
    covered = {group_id for clique in cliques for group_id in clique}
    singleton_sets = [[group_id] for group_id in sorted(set(graph) - covered)]
    return cliques + singleton_sets


def build_set_candidate_diagnostic(seed_document: Mapping[str, Any]) -> dict[str, Any]:
    """Build multi-group candidate proposals from two graph constructions."""
    graphs = _graphs(seed_document)
    relations = _relation_lookup(seed_document)
    scope = sorted(str(group_id) for group_id in seed_document["views"][0]["scope_group_ids"])
    candidates_by_recipe: dict[str, list[dict[str, Any]]] = {}
    for recipe in RECIPES:
        base = "nearest-neighbour" if recipe.startswith("nearest-neighbour") else "contact"
        candidates = []
        for index, members in enumerate(_candidate_sets(recipe, graphs[base])):
            member_set = set(members)
            relation_ids = []
            for pair_id, relation in relations.items():
                if {relation["group_a"], relation["group_b"]} <= member_set:
                    relation_ids.append(pair_id)
            candidates.append(
                {
                    "candidate_id": f"{recipe}-candidate-{index:04d}",
                    "recipe": recipe,
                    "scope_group_ids": scope,
                    "proposal_extent": members,
                    "closure_status": "not_evaluated",
                    "candidate_status": "diagnostic_singleton" if len(members) == 1 else "diagnostic_only",
                    "proposal_evidence": {
                        "graph_rule": recipe,
                        "relation_ids": sorted(relation_ids),
                        "edge_count": len(relation_ids),
                        "source_ids": sorted(
                            {
                                source_id
                                for relation_id in relation_ids
                                for source_id in relations[relation_id]["source_ids"]
                            }
                        ),
                    },
                    "participation": None,
                    "strength": None,
                    "winner": None,
                }
            )
        candidates_by_recipe[recipe] = candidates
    return {
        "schema": "group-set-candidate-diagnostic/v1",
        "diagnostic_only": True,
        "candidate_selection": "parallel-unresolved",
        "recipes": list(RECIPES),
        "source": seed_document["source"],
        "analysis_plane": seed_document["analysis_plane"],
        "scope_group_count": len(scope),
        "group_pair_count": seed_document["group_pair_count"],
        "candidates_by_recipe": candidates_by_recipe,
        "prohibited_outputs": ["authored_membership", "participation", "potential", "strength", "winner"],
    }


def _candidate_svg(candidate: Mapping[str, Any], groups_by_id: Mapping[str, Mapping[str, Any]], shapes: Mapping[str, Any], source: Mapping[str, Any], plane: Mapping[str, Any]) -> str:
    """Render one set-level candidate over the complete frozen scope."""
    selected_groups = [groups_by_id[group_id] for group_id in candidate["scope_group_ids"]]
    xmin, ymin, xmax, ymax = _bounds(selected_groups)
    width, height, margin, footer = 1500, 1050, 45, 165
    scale = min((width - 2 * margin) / (xmax - xmin), (height - footer - 2 * margin) / (ymax - ymin))

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map plane-local coordinates into the SVG viewport."""
        return margin + (point[0] - xmin) * scale, height - footer - margin - (point[1] - ymin) * scale

    proposal = set(candidate["proposal_extent"])
    markup = []
    for group in selected_groups:
        group_id = str(group["group_id"])
        if group_id in proposal:
            fill, stroke, opacity = "#f2c14e", "#9a6b00", ".78"
        else:
            fill, stroke, opacity = "#d9e2e8", "#71808a", ".35"
        markup.append(
            f'<path d="{_path(shapes[group_id], project)}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="1.2" fill-rule="evenodd"><title>{_xml(group.get("name", group_id))}</title></path>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<title>{_xml(candidate["candidate_id"])}</title><rect width="100%" height="100%" fill="white"/>'
        + "".join(markup)
        + f'<text x="{margin}" y="24" font-size="13">DIAGNOSTIC ONLY | recipe: {_xml(candidate["recipe"])} | '
        f'candidate: {_xml(candidate["candidate_id"])} | members: {len(proposal)} | '
        f'sha256: {_xml(source["sha256"])} | plane: {_xml(plane["name"])}</text>'
        + f'<text x="{margin}" y="44" font-size="13">yellow = proposed multi-group set; grey = complete scope; '
        "no authored membership, participation, potential, strength or winner.</text>"
        + f'<line x1="{margin}" y1="{height-footer}" x2="{width-margin}" y2="{height-footer}" stroke="#bbb"/>'
        + f'<text x="{margin}" y="{height-55}" font-size="12">closure = not_evaluated; candidate selection = parallel-unresolved.</text>'
        + "</svg>"
    )


def write_diagnostic(seed_run: Path, geometry_run: Path, output_dir: Path) -> Path:
    """Write set-level candidate JSON, manifest and plane-local SVGs."""
    seed_document = _read_json(seed_run / "seed_profiles.json")
    geometry_manifest = _read_json(geometry_run / "view_manifest.json")
    if seed_document["source"]["sha256"] != geometry_manifest["source_sha256"]:
        raise AssertionError("seed and geometry artifacts use different IFC fingerprints")
    if seed_document["analysis_plane"] != geometry_manifest["analysis_plane"]:
        raise AssertionError("seed and geometry artifacts use different analysis planes")
    geometry_plan = _read_json(geometry_run / "plan_geometry.json")
    diagnostic = build_set_candidate_diagnostic(seed_document)
    groups_by_id = {str(group["group_id"]): group for group in geometry_plan["groups"]}
    shapes = _group_shapes(geometry_plan)
    manifest_views = []
    for recipe, candidates in diagnostic["candidates_by_recipe"].items():
        recipe_dir = output_dir / "views" / recipe
        recipe_dir.mkdir(parents=True, exist_ok=True)
        for candidate in candidates:
            svg_name = f"{candidate['candidate_id']}.svg"
            (recipe_dir / svg_name).write_text(
                _candidate_svg(candidate, groups_by_id, shapes, seed_document["source"], diagnostic["analysis_plane"]),
                encoding="utf-8",
            )
            manifest_views.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "recipe": recipe,
                    "proposal_extent": candidate["proposal_extent"],
                    "svg": f"views/{recipe}/{svg_name}",
                }
            )
    diagnostic["view_manifest"] = manifest_views
    _write_json(output_dir / "candidate_sets.json", diagnostic)
    _write_json(
        output_dir / "manifest.json",
        {
            "schema": "group-set-candidate-diagnostic-manifest/v1",
            "diagnostic_only": True,
            "source": diagnostic["source"],
            "analysis_plane": diagnostic["analysis_plane"],
            "recipe_count": len(RECIPES),
            "candidate_count": len(manifest_views),
            "views": manifest_views,
        },
    )
    return output_dir


def main() -> None:
    """Run the set-level candidate diagnostic."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-run", type=Path, default=DEFAULT_SEED_RUN)
    parser.add_argument("--geometry-run", type=Path, default=DEFAULT_GEOMETRY_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = write_diagnostic(args.seed_run, args.geometry_run, args.output_dir)
    print(f"set candidate diagnostic: {output}")


if __name__ == "__main__":
    main()
