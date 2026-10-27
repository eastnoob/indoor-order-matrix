"""Build a diagnostic seed relation profile from one completed IFC run.

This experiment tests whether a seed-labelled organization view can carry a
complete scope of group-to-group observations. It deliberately stops before
mapping distance to participation or strength.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean, median
from typing import Any, Mapping

from .render_group_geometry_relation_field_ifc import _bounds, _path, _polygon, _xml


DEFAULT_RUN = (
    Path(__file__).resolve().parents[3]
    / "outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96"
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[3]
    / "outputs/design/group_seed_candidate_experiment/run_20261027T_seed_profile_v1"
)


def _read_json(path: Path) -> Any:
    """Read one UTF-8 JSON artifact from the retained IFC run."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    """Write deterministic JSON for the diagnostic artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _pair_ids(envelope: Mapping[str, Any]) -> tuple[str, str]:
    """Decode the canonical unordered group-pair target."""
    pair = json.loads(str(envelope["target"]["id"]))
    if not isinstance(pair, list) or len(pair) != 2:
        raise ValueError("envelope target must encode two group IDs")
    return str(pair[0]), str(pair[1])


def _channels(envelope: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Index the immutable channel records by channel name."""
    return {
        str(record["channel"]): record
        for record in envelope["value"]["channels"]
    }


def _summary(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize one real group pair without deriving participation."""
    channels = _channels(envelope)
    gaps = [
        observation["values"]
        for observation in channels["boundary_gap"]["observation"]["member_pairs"]
        if observation["status"] == "computed"
    ]
    contacts = [
        observation["values"].get("contact") is True
        for observation in channels["contact"]["observation"]["member_pairs"]
        if observation["status"] == "computed"
    ]
    overlaps = [
        observation["values"].get("overlap") is True
        for observation in channels["positive_area_overlap"]["observation"]["member_pairs"]
        if observation["status"] == "computed"
    ]
    raw = [float(item["raw_boundary_gap"]) for item in gaps]
    normalized = [float(item["normalized_boundary_gap"]) for item in gaps]
    if not raw or not normalized:
        raise ValueError("seed experiment requires computed gap observations")
    return {
        "pair_id": str(envelope["target"]["id"]),
        "status": str(envelope["raw_status"]),
        "member_pair_count": len(gaps),
        "raw_boundary_gap": {
            "minimum": min(raw),
            "median": median(raw),
            "mean": fmean(raw),
        },
        "normalized_boundary_gap": {
            "minimum": min(normalized),
            "median": median(normalized),
            "mean": fmean(normalized),
        },
        "contact_count": sum(contacts),
        "overlap_count": sum(overlaps),
        "source_ids": list(envelope["source_ids"]),
    }


def _relation_index(envelopes: list[Mapping[str, Any]]) -> dict[frozenset[str], dict[str, Any]]:
    """Index all unordered relations from the completed IFC envelope set."""
    relations: dict[frozenset[str], dict[str, Any]] = {}
    for envelope in envelopes:
        group_a, group_b = _pair_ids(envelope)
        key = frozenset((group_a, group_b))
        if len(key) != 2 or key in relations:
            raise ValueError("group-pair relation IDs must be unique")
        relation = _summary(envelope)
        relation["group_a"] = group_a
        relation["group_b"] = group_b
        relations[key] = relation
    return relations


def build_seed_profiles(
    envelopes_document: Mapping[str, Any],
    plan_document: Mapping[str, Any],
    source_document: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one full-scope diagnostic profile for every real group seed."""
    envelopes = list(envelopes_document["envelopes"])
    groups = sorted(
        plan_document["groups"],
        key=lambda group: str(group["group_id"]),
    )
    group_ids = [str(group["group_id"]) for group in groups]
    if plan_document["source_sha256"] != source_document["sha256"]:
        raise AssertionError("plan and retained run must use the same IFC fingerprint")
    if plan_document["analysis_plane"] != source_document["analysis_plane"]:
        raise AssertionError("plan and retained run must use the same analysis plane")
    group_id_set = set(group_ids)
    for envelope in envelopes:
        pair_ids = _pair_ids(envelope)
        if not set(pair_ids) <= group_id_set:
            raise AssertionError("relation pair contains a group outside the retained scope")
        if envelope["query"]["plane"] != plan_document["analysis_plane"]:
            raise AssertionError("relation query plane differs from the retained plan plane")
        if envelope["provenance"]["source_fingerprint"] != source_document["sha256"]:
            raise AssertionError("relation source fingerprint differs from the retained IFC")
        if not envelope["source_ids"]:
            raise AssertionError("every relation must retain at least one source reference")
    relations = _relation_index(envelopes)
    expected_pair_count = len(group_ids) * (len(group_ids) - 1) // 2
    if len(relations) != expected_pair_count:
        raise AssertionError(
            f"expected {expected_pair_count} group pairs, found {len(relations)}"
        )

    views = []
    for seed_index, seed_id in enumerate(group_ids):
        related = []
        for group_id in group_ids:
            if group_id == seed_id:
                related.append(
                    {
                        "group_id": group_id,
                        "role": "seed",
                        "participation_status": "not_evaluated",
                    }
                )
                continue
            relation = relations[frozenset((seed_id, group_id))]
            related.append(
                {
                    "group_id": group_id,
                    "role": "scope_member",
                    "participation_status": "not_evaluated",
                    "relation": relation,
                }
            )
        ranked = sorted(
            (item for item in related if "relation" in item),
            key=lambda item: (
                item["relation"]["normalized_boundary_gap"]["minimum"],
                item["group_id"],
            ),
        )
        for rank, item in enumerate(ranked, start=1):
            item["relative_distance_rank"] = rank
        if len(ranked) != len(group_ids) - 1:
            raise AssertionError("every seed must expose one relation to every other scope group")
        views.append(
            {
                "view_id": f"seed-profile-{seed_index:04d}",
                "seed_group_id": seed_id,
                "scope_group_ids": group_ids,
                "proposal_extent": [seed_id],
                "closure_status": "not_evaluated",
                "participation_status": "not_evaluated",
                "members": related,
            }
        )

    return {
        "schema": "group-seed-relation-profile-experiment/v1",
        "diagnostic_only": True,
        "source": source_document,
        "analysis_plane": plan_document["analysis_plane"],
        "scope_group_count": len(group_ids),
        "group_pair_count": len(relations),
        "participation_formula": None,
        "strength_formula": None,
        "candidate_closure": "not_evaluated",
        "views": views,
    }


def _group_shapes(plan_document: Mapping[str, Any]) -> dict[str, Any]:
    """Build one unioned projected footprint for each real group."""
    from shapely.ops import unary_union

    return {
        str(group["group_id"]): unary_union(
            [
                _polygon(polygon)
                for member in group["members"]
                for polygon in member["polygons"]
            ]
        )
        for group in plan_document["groups"]
    }


def _seed_svg(
    view: Mapping[str, Any],
    groups_by_id: Mapping[str, Mapping[str, Any]],
    shapes: Mapping[str, Any],
    source_sha256: str,
    plane: Mapping[str, Any],
) -> str:
    """Render one seed profile with relative-distance lines only."""
    seed_id = str(view["seed_group_id"])
    selected_groups = [groups_by_id[group_id] for group_id in view["scope_group_ids"]]
    xmin, ymin, xmax, ymax = _bounds(selected_groups)
    width, height, margin, footer = 1500, 1050, 45, 150
    scale = min(
        (width - 2 * margin) / (xmax - xmin),
        (height - footer - 2 * margin) / (ymax - ymin),
    )

    def project(point: tuple[float, float]) -> tuple[float, float]:
        """Map plane-local coordinates into the seed profile viewport."""
        return (
            margin + (point[0] - xmin) * scale,
            height - footer - margin - (point[1] - ymin) * scale,
        )

    seed_shape = shapes[seed_id]
    seed_centroid = seed_shape.centroid
    markup = []
    for group in selected_groups:
        group_id = str(group["group_id"])
        shape = shapes[group_id]
        fill = "#d1495b" if group_id == seed_id else "#d9e2e8"
        stroke = "#8f1d2c" if group_id == seed_id else "#354a59"
        markup.append(
            f'<path d="{_path(shape, project)}" fill="{fill}" fill-opacity=".65" '
            f'stroke="{stroke}" stroke-width="1.2" fill-rule="evenodd">'
            f'<title>{_xml(group.get("name", group_id))}</title></path>'
        )

    for member in view["members"]:
        if member.get("role") != "scope_member":
            continue
        group_id = str(member["group_id"])
        centroid = shapes[group_id].centroid
        x1, y1 = project((seed_centroid.x, seed_centroid.y))
        x2, y2 = project((centroid.x, centroid.y))
        rank = int(member["relative_distance_rank"])
        opacity = max(0.18, 1.0 - (rank - 1) / max(1, len(view["members"])))
        markup.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#365f91" stroke-opacity="{opacity:.3f}" stroke-width="2">'
            f'<title>relative normalized-gap rank {rank}; participation not evaluated</title></line>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<title>{_xml(view["view_id"])}</title><rect width="100%" height="100%" fill="white"/>'
        + "".join(markup)
        + f'<text x="{margin}" y="24" font-size="13">DIAGNOSTIC ONLY | seed: {_xml(seed_id)} | '
        f'sha256: {_xml(source_sha256)} | plane: {_xml(plane.get("name"))}</text>'
        + f'<text x="{margin}" y="44" font-size="13">Lines show relative normalized-gap order only; '
        "no participation, membership, support, strength or winner.</text>"
        + f'<line x1="{margin}" y1="{height-footer}" x2="{width-margin}" y2="{height-footer}" stroke="#bbb"/>'
        + f'<text x="{margin}" y="{height-55}" font-size="12">red = seed footprint; grey = full scope footprints; '
        "blue opacity = relative distance rank.</text>"
        + "</svg>"
    )


def write_experiment(run_dir: Path, output_dir: Path) -> Path:
    """Write the seed profiles, manifest, and one plane-local SVG per seed."""
    envelopes = _read_json(run_dir / "envelopes.json")
    plan = _read_json(run_dir / "plan_geometry.json")
    view_manifest = _read_json(run_dir / "view_manifest.json")
    source = {
        "sha256": view_manifest["source_sha256"],
        "analysis_plane": view_manifest["analysis_plane"],
        "run_dir": str(run_dir.resolve()),
    }
    experiment = build_seed_profiles(envelopes, plan, source)
    groups_by_id = {str(group["group_id"]): group for group in plan["groups"]}
    shapes = _group_shapes(plan)
    svg_dir = output_dir / "views"
    svg_dir.mkdir(parents=True, exist_ok=True)
    manifest_views = []
    for view in experiment["views"]:
        svg_name = f"{view['view_id']}.svg"
        (svg_dir / svg_name).write_text(
            _seed_svg(view, groups_by_id, shapes, source["sha256"], plan["analysis_plane"]),
            encoding="utf-8",
        )
        manifest_views.append(
            {
                "view_id": view["view_id"],
                "seed_group_id": view["seed_group_id"],
                "svg": f"views/{svg_name}",
            }
        )
    experiment["view_manifest"] = manifest_views
    _write_json(output_dir / "seed_profiles.json", experiment)
    _write_json(
        output_dir / "manifest.json",
        {
            "schema": "group-seed-relation-profile-experiment-manifest/v1",
            "diagnostic_only": True,
            "source": source,
            "analysis_plane": plan["analysis_plane"],
            "view_count": len(manifest_views),
            "views": manifest_views,
        },
    )
    if len(manifest_views) != len(plan["groups"]):
        raise AssertionError("every real group must produce one seed view")
    return output_dir


def main() -> None:
    """Run the seed relation profile experiment against saved IFC artifacts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = write_experiment(args.run_dir, args.output_dir)
    print(f"seed relation profile experiment: {output}")


if __name__ == "__main__":
    main()
