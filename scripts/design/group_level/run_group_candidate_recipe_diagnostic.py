"""Compare geometry-only candidate proposal recipes on retained IFC artifacts.

The diagnostic keeps candidate proposal separate from attribution.  It reuses the
already validated seed profiles and projected group polygons, so it does not
reload IFC geometry or invent a synthetic scene.
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
    / "outputs/design/group_candidate_recipe_diagnostic/run_20261028T_parallel_v1"
)

RECIPES = (
    "nearest-neighbour-one-step",
    "contact-only-one-step",
)


def _read_json(path: Path) -> Any:
    """Read one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    """Write deterministic JSON for a diagnostic artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _proposal_extent(view: Mapping[str, Any], recipe: str) -> list[str]:
    """Select one-step proposal members from retained geometry observations."""
    seed_id = str(view["seed_group_id"])
    related = [item for item in view["members"] if item.get("role") == "scope_member"]
    if recipe == "nearest-neighbour-one-step":
        minimum = min(
            float(item["relation"]["normalized_boundary_gap"]["minimum"])
            for item in related
        )
        selected = [
            str(item["group_id"])
            for item in related
            if float(item["relation"]["normalized_boundary_gap"]["minimum"]) == minimum
        ]
    elif recipe == "contact-only-one-step":
        selected = [
            str(item["group_id"])
            for item in related
            if int(item["relation"]["contact_count"]) > 0
        ]
    else:
        raise ValueError(f"unsupported diagnostic recipe: {recipe}")
    return sorted([seed_id, *selected])


def _proposal_evidence(view: Mapping[str, Any], recipe: str, extent: list[str]) -> dict[str, Any]:
    """Record the observations that exposed the proposed one-step extent."""
    extent_set = set(extent)
    selected = []
    for item in view["members"]:
        if item.get("role") != "scope_member" or str(item["group_id"]) not in extent_set:
            continue
        relation = item["relation"]
        selected.append(
            {
                "pair_id": relation["pair_id"],
                "source_ids": list(relation["source_ids"]),
                "status": relation["status"],
                "normalized_boundary_gap": relation["normalized_boundary_gap"],
                "contact_count": relation["contact_count"],
                "overlap_count": relation["overlap_count"],
            }
        )
    return {
        "driver": recipe,
        "closure_status": "not_evaluated",
        "selected_relation_refs": selected,
        "selection_rule": (
            "all tied minimum normalized boundary-gap relations"
            if recipe == "nearest-neighbour-one-step"
            else "all scope relations with one or more computed contact observations"
        ),
    }


def build_recipe_diagnostic(seed_document: Mapping[str, Any]) -> dict[str, Any]:
    """Build two parallel proposal diagnostics without attribution readouts."""
    views_by_recipe: dict[str, list[dict[str, Any]]] = {recipe: [] for recipe in RECIPES}
    for source_view in seed_document["views"]:
        scope_ids = [str(group_id) for group_id in source_view["scope_group_ids"]]
        for recipe in RECIPES:
            extent = _proposal_extent(source_view, recipe)
            extent_set = set(extent)
            members = []
            for item in source_view["members"]:
                group_id = str(item["group_id"])
                if item.get("role") == "seed":
                    members.append(
                        {
                            "group_id": group_id,
                            "role": "seed",
                            "proposal_exposure": "seed",
                            "status": "computed",
                        }
                    )
                    continue
                relation = item["relation"]
                members.append(
                    {
                        "group_id": group_id,
                        "role": "scope_member",
                        "proposal_exposure": (
                            "proposal_extent" if group_id in extent_set else "scope_only"
                        ),
                        "boundary_gap": relation["normalized_boundary_gap"],
                        "contact": {"count": relation["contact_count"]},
                        "positive_area_overlap": {"count": relation["overlap_count"]},
                        "status": relation["status"],
                        "source_refs": relation["source_ids"],
                        "dependency_refs": relation["source_ids"],
                        "pair_id": relation["pair_id"],
                    }
                )
            views_by_recipe[recipe].append(
                {
                    "view_id": f"{recipe}-seed-{len(views_by_recipe[recipe]):04d}",
                    "recipe": recipe,
                    "seed_group_id": str(source_view["seed_group_id"]),
                    "scope_group_ids": scope_ids,
                    "proposal_extent": extent,
                    "closure_status": "not_evaluated",
                    "proposal_evidence": _proposal_evidence(source_view, recipe, extent),
                    "members": members,
                    "participation_formula": None,
                    "strength_formula": None,
                    "winner": None,
                }
            )
    return {
        "schema": "group-candidate-recipe-diagnostic/v1",
        "diagnostic_only": True,
        "recipe_selection": "parallel-unresolved",
        "recipes": list(RECIPES),
        "source": seed_document["source"],
        "analysis_plane": seed_document["analysis_plane"],
        "scope_group_count": seed_document["scope_group_count"],
        "group_pair_count": seed_document["group_pair_count"],
        "views_by_recipe": views_by_recipe,
        "prohibited_outputs": [
            "participation",
            "membership",
            "support",
            "potential",
            "strength",
            "winner",
        ],
    }


def _recipe_svg(view: Mapping[str, Any], groups_by_id: Mapping[str, Mapping[str, Any]], shapes: Mapping[str, Any], source: Mapping[str, Any], plane: Mapping[str, Any]) -> str:
    """Render one candidate proposal over the complete real scope."""
    selected_groups = [groups_by_id[group_id] for group_id in view["scope_group_ids"]]
    xmin, ymin, xmax, ymax = _bounds(selected_groups)
    width, height, margin, footer = 1500, 1050, 45, 165
    scale = min((width - 2 * margin) / (xmax - xmin), (height - footer - 2 * margin) / (ymax - ymin))

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map plane-local coordinates into the SVG viewport."""
        return margin + (point[0] - xmin) * scale, height - footer - margin - (point[1] - ymin) * scale

    seed_id = str(view["seed_group_id"])
    extent = set(view["proposal_extent"])
    markup = []
    for group in selected_groups:
        group_id = str(group["group_id"])
        if group_id == seed_id:
            fill, stroke, opacity = "#d1495b", "#8f1d2c", ".80"
        elif group_id in extent:
            fill, stroke, opacity = "#f2c14e", "#9a6b00", ".72"
        else:
            fill, stroke, opacity = "#d9e2e8", "#71808a", ".35"
        markup.append(
            f'<path d="{_path(shapes[group_id], project)}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="1.2" fill-rule="evenodd">'
            f'<title>{_xml(group.get("name", group_id))}</title></path>'
        )
    seed_centroid = shapes[seed_id].centroid
    for group_id in sorted(extent - {seed_id}):
        centroid = shapes[group_id].centroid
        x1, y1 = project((seed_centroid.x, seed_centroid.y))
        x2, y2 = project((centroid.x, centroid.y))
        markup.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#b06b00" stroke-width="2.5"><title>proposal extent; readout not evaluated</title></line>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<title>{_xml(view["view_id"])}</title><rect width="100%" height="100%" fill="white"/>'
        + "".join(markup)
        + f'<text x="{margin}" y="24" font-size="13">DIAGNOSTIC ONLY | recipe: {_xml(view["recipe"])} | '
        f'seed: {_xml(seed_id)} | sha256: {_xml(source["sha256"])} | plane: {_xml(plane["name"])}</text>'
        + f'<text x="{margin}" y="44" font-size="13">yellow = proposed one-step extent; grey = complete scope; '
        "no participation, membership, potential, strength or winner.</text>"
        + f'<line x1="{margin}" y1="{height-footer}" x2="{width-margin}" y2="{height-footer}" stroke="#bbb"/>'
        + f'<text x="{margin}" y="{height-55}" font-size="12">red = seed; yellow = proposal extent; grey = scope-only groups; '
        "closure = not_evaluated.</text>"
        + "</svg>"
    )


def write_diagnostic(seed_run: Path, geometry_run: Path, output_dir: Path) -> Path:
    """Write JSON, manifest and plane-local SVGs for both parallel recipes."""
    seed_document = _read_json(seed_run / "seed_profiles.json")
    geometry_plan = _read_json(geometry_run / "plan_geometry.json")
    geometry_manifest = _read_json(geometry_run / "view_manifest.json")
    if seed_document["source"]["sha256"] != geometry_manifest["source_sha256"]:
        raise AssertionError("seed and geometry artifacts use different IFC fingerprints")
    if seed_document["analysis_plane"] != geometry_manifest["analysis_plane"]:
        raise AssertionError("seed and geometry artifacts use different analysis planes")
    diagnostic = build_recipe_diagnostic(seed_document)
    groups_by_id = {str(group["group_id"]): group for group in geometry_plan["groups"]}
    shapes = _group_shapes(geometry_plan)
    views_manifest = []
    for recipe, views in diagnostic["views_by_recipe"].items():
        recipe_dir = output_dir / "views" / recipe
        recipe_dir.mkdir(parents=True, exist_ok=True)
        for view in views:
            svg_name = f"{view['view_id']}.svg"
            (recipe_dir / svg_name).write_text(
                _recipe_svg(view, groups_by_id, shapes, seed_document["source"], diagnostic["analysis_plane"]),
                encoding="utf-8",
            )
            views_manifest.append(
                {
                    "view_id": view["view_id"],
                    "recipe": recipe,
                    "seed_group_id": view["seed_group_id"],
                    "svg": f"views/{recipe}/{svg_name}",
                    "proposal_extent": view["proposal_extent"],
                }
            )
    diagnostic["view_manifest"] = views_manifest
    _write_json(output_dir / "candidate_recipe_diagnostic.json", diagnostic)
    _write_json(
        output_dir / "manifest.json",
        {
            "schema": "group-candidate-recipe-diagnostic-manifest/v1",
            "diagnostic_only": True,
            "source": diagnostic["source"],
            "analysis_plane": diagnostic["analysis_plane"],
            "recipe_count": len(RECIPES),
            "view_count": len(views_manifest),
            "views": views_manifest,
        },
    )
    expected = len(seed_document["views"]) * len(RECIPES)
    if len(views_manifest) != expected:
        raise AssertionError(f"expected {expected} recipe views, found {len(views_manifest)}")
    return output_dir


def main() -> None:
    """Run the parallel candidate recipe diagnostic."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-run", type=Path, default=DEFAULT_SEED_RUN)
    parser.add_argument("--geometry-run", type=Path, default=DEFAULT_GEOMETRY_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = write_diagnostic(args.seed_run, args.geometry_run, args.output_dir)
    print(f"candidate recipe diagnostic: {output}")


if __name__ == "__main__":
    main()
