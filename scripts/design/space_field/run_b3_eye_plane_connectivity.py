"""Compare accepted PRIMARY eye-plane geometry with sampled connectivity."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from shapely.geometry import GeometryCollection, LineString, Point, box, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3"
PRIOR_PATH = Path(__file__).with_name("run_b3_real_field_diagnostic.py")
SPEC = importlib.util.spec_from_file_location("b3_connectivity_prior", PRIOR_PATH)
PRIOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PRIOR
SPEC.loader.exec_module(PRIOR)
EMPTY = GeometryCollection()


def attempt(operation):
    """Retain an original geometry failure without a repair or numeric retry."""
    try:
        return {"status": "computed", "value": operation(), "error": None}
    except Exception as error:
        return {"status": "not_available", "value": None, "error": f"{type(error).__name__}: {error}"}


def geometric_reference(domain, occupied, unknown, source_boundaries):
    """Compute open polygon interiors or retain the reason that they are unavailable."""
    def calculate():
        """Check inputs before differences so invalid data cannot become computed empty."""
        if any(item is None for item in (domain, occupied, unknown)):
            raise ValueError("Missing geometry input; not computed empty")
        if any(not item.is_valid for item in (domain, occupied, unknown)):
            raise ValueError("Invalid geometry input; no repair")
        reference = area_view(domain.difference(occupied).difference(unknown))
        if not reference.is_valid:
            raise ValueError("Invalid derived conditional-empty geometry")
        if reference.is_empty:
            return reference
        # Polygon differences cannot represent an excluded line inside an open interior.
        residuals = [index for index, boundary in enumerate(source_boundaries)
                     if boundary.intersection(reference).difference(reference.boundary).length > 0]
        if residuals:
            raise ValueError(f"Unresolved interior section-boundary linework at source-boundary indices {residuals}")
        return reference
    return attempt(calculate)


def area_view(geometry):
    """Retain every positive-area polygon without repair or tolerance deletion."""
    parts = PRIOR.ACCEPTED._polygon_parts(geometry)
    return unary_union(parts) if parts else EMPTY


def sample_id(variant_id, sample):
    """Retain the accepted lattice identity in a stable readable form."""
    return f"{variant_id}:{sample['cell_i']}:{sample['cell_j']}"


def build_sample_graph(variant, variant_id, diagonal):
    """Build one accepted conditional-empty graph and retain component memberships."""
    keys = [(sample["cell_i"], sample["cell_j"]) for sample in variant["samples"]]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate accepted lattice identity")
    if any(not math.isfinite(sample[key]) for sample in variant["samples"] for key in ("x_m", "y_m")):
        raise ValueError("Nonfinite accepted sample coordinates")
    vertices = {
        (sample["cell_i"], sample["cell_j"]): sample
        for sample in variant["samples"]
        if sample["domain_mask"] is True
        and sample["occupancy_value"] is False
        and sample["known_free_under_qualification"] is True
    }
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonal:
        offsets += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    unseen = set(vertices)
    components = []
    edges = set()
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        queue = deque([start])
        members = []
        while queue:
            key = queue.popleft()
            members.append(key)
            for di, dj in offsets:
                neighbor = (key[0] + di, key[1] + dj)
                if neighbor in vertices:
                    edges.add(tuple(sorted((key, neighbor))))
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        queue.append(neighbor)
        components.append(sorted(members))
    components.sort(key=lambda members: (-len(members), members[0]))
    return {
        "adjacency": "unrestricted_8_neighbor" if diagonal else "4_neighbor",
        "vertex_count": len(vertices),
        "edge_count": len(edges),
        "components": [
            {"id": f"{variant_id}:{'8' if diagonal else '4'}c{index}", "size": len(members),
             "sample_ids": [sample_id(variant_id, vertices[key]) for key in members]}
            for index, members in enumerate(components)
        ],
    }, vertices, sorted(edges)


def map_components(graph, vertices, geometric_components, variant_id):
    """Map graph memberships to open geometric interiors without reclassifying boundaries."""
    sample_geometry = {}
    unassigned = []
    by_sample = {sample_id(variant_id, sample): sample for sample in vertices.values()}
    for identifier, sample in by_sample.items():
        point = Point(sample["x_m"], sample["y_m"])
        matches = [index for index, polygon in enumerate(geometric_components) if polygon.contains(point)]
        sample_geometry[identifier] = matches
        if not matches:
            unassigned.append({"sample_id": identifier, "x_m": sample["x_m"], "y_m": sample["y_m"],
                               "section_boundary_ambiguity_mask": sample["section_boundary_ambiguity_mask"]})
    graph_to_geometry = []
    geometry_to_graph = {index: [] for index in range(len(geometric_components))}
    for component in graph["components"]:
        matched = sorted({index for identifier in component["sample_ids"] for index in sample_geometry[identifier]})
        graph_to_geometry.append({"graph_component_id": component["id"], "geometric_component_ids": matched})
        for index in matched:
            geometry_to_graph[index].append(component["id"])
    missed = [index for index, graph_ids in geometry_to_graph.items() if not graph_ids]
    return {
        "sample_to_geometric_component_ids": sample_geometry,
        "unassigned_boundary_or_reference_samples": unassigned,
        "graph_to_geometry": graph_to_geometry,
        "geometry_to_graph": [{"geometric_component_id": key, "graph_component_ids": value}
                               for key, value in geometry_to_graph.items()],
        "missed_geometric_component_ids": missed,
        "merged_graph_components": [item for item in graph_to_geometry if len(item["geometric_component_ids"]) > 1],
        "split_geometric_components": [{"geometric_component_id": key, "graph_component_ids": value}
                                        for key, value in geometry_to_graph.items() if len(value) > 1],
    }


def edge_diagnostics(edges, vertices, domain, unknown, occupied, source_boundaries, sample_mapping, variant_id):
    """Diagnose graph edges that cross excluded area or change reference membership."""
    affected = []
    counts = Counter()
    affected_count = 0
    # Zero-area clipping contacts stay in source-boundary diagnostics, never in positive mass interiors.
    mass_area = area_view(occupied)
    holes = [shape({"type": "Polygon", "coordinates": [list(ring.coords)]})
             for polygon in PRIOR.ACCEPTED._polygon_parts(domain) for ring in polygon.interiors]
    for first, second in edges:
        left, right = vertices[first], vertices[second]
        line = LineString([(left["x_m"], left["y_m"]), (right["x_m"], right["y_m"])])
        left_id, right_id = sample_id(variant_id, left), sample_id(variant_id, right)
        reasons = []
        if line.intersection(unknown).length > 0:
            reasons.append("unknown_support")
        if not mass_area.is_empty and line.intersection(mass_area).difference(mass_area.boundary).length > 0:
            reasons.append("qualified_mass")
        if line.difference(domain).length > 0:
            reasons.append("outside_domain_or_hole")
        if any(line.intersection(hole).length > 0 for hole in holes):
            reasons.append("domain_hole")
        if line.intersects(domain.boundary):
            reasons.append("domain_boundary_contact")
        if line.intersects(unknown.boundary):
            reasons.append("unknown_boundary_contact")
        if any(line.intersects(boundary) for boundary in source_boundaries):
            reasons.append("section_boundary_contact")
        if sample_mapping is not None and sample_mapping[left_id] != sample_mapping[right_id]:
            reasons.append("different_geometric_membership")
        if reasons:
            affected_count += 1
            counts.update(reasons)
            if len(affected) < 8:
                affected.append({"sample_ids": [left_id, right_id], "coordinates_m": list(line.coords), "reasons": reasons})
    return {"affected_edge_count": affected_count,
            "reason_edge_counts": dict(counts), "examples": affected,
            "note": "Diagnostics do not filter graph edges."}


def reconstruction(variant, vertices, reference, domain):
    """Compare clipped center-labelled cells with the reference as a diagnostic only."""
    spacing = variant["spacing_m"]
    cells = [box(sample["x_m"] - spacing / 2, sample["y_m"] - spacing / 2,
                 sample["x_m"] + spacing / 2, sample["y_m"] + spacing / 2) for sample in vertices.values()]
    all_domain_cells = [box(sample["x_m"] - spacing / 2, sample["y_m"] - spacing / 2,
                            sample["x_m"] + spacing / 2, sample["y_m"] + spacing / 2)
                        for sample in variant["samples"] if sample["domain_mask"]]
    rebuilt = unary_union(cells).intersection(domain) if cells else EMPTY
    coverage = unary_union(all_domain_cells).intersection(domain) if all_domain_cells else EMPTY
    # Directional operations are independent: one GEOS error must not erase unrelated area evidence.
    operations = {"clipped_reconstructed_area_m2": lambda: rebuilt.area,
                  "false_empty_area_m2": lambda: rebuilt.difference(reference).area,
                  "missed_empty_area_m2": lambda: reference.difference(rebuilt).area,
                  "symmetric_difference_area_m2": lambda: rebuilt.symmetric_difference(reference).area,
                  "uncovered_domain_area_m2": lambda: domain.difference(coverage).area}
    checked = {key: attempt(operation) for key, operation in operations.items()}
    return {"point_center_area_estimate_m2": len(vertices) * spacing * spacing,
            "point_center_area_error_m2": len(vertices) * spacing * spacing - reference.area,
            **{key: value["value"] for key, value in checked.items()},
            "operation_statuses": checked,
            "meaning": "Nonconservative sample-center and clipped-cell diagnostics; no cell-coverage claim."}


def compare_variant(variant, reference, domain, occupied, unknown, source_boundaries, variant_id):
    """Create both graph comparisons and their independent correspondence evidence."""
    result = {"id": variant_id, "spacing_m": variant["spacing_m"], "origin_offset_m": variant["origin_offset_m"]}
    geometric_components = None if reference is None else PRIOR.ACCEPTED._polygon_parts(reference)
    for diagonal, key in ((False, "four_neighbor"), (True, "eight_neighbor")):
        graph, vertices, edges = build_sample_graph(variant, variant_id, diagonal)
        mapped = attempt(lambda: map_components(graph, vertices, geometric_components, variant_id)) if geometric_components is not None else {
            "status": "not_available", "value": None, "error": "Geometric reference unavailable"}
        graph["correspondence"] = mapped["value"]
        graph["correspondence_status"] = {key: mapped[key] for key in ("status", "error")}
        diagnosed = attempt(lambda: edge_diagnostics(
            edges, vertices, domain, unknown, occupied, source_boundaries,
            None if mapped["value"] is None else mapped["value"]["sample_to_geometric_component_ids"], variant_id))
        graph["edge_diagnostics"] = diagnosed["value"]
        graph["edge_diagnostics_status"] = {key: diagnosed[key] for key in ("status", "error")}
        result[key] = graph
    areas = attempt(lambda: reconstruction(variant, vertices, reference, domain)) if reference is not None else {
        "status": "not_available", "value": None, "error": "Geometric reference unavailable"}
    result["area_diagnostics"] = areas["value"]
    result["area_diagnostics_status"] = {key: areas[key] for key in ("status", "error")}
    result["point_center_area_estimate_m2"] = len(vertices) * variant["spacing_m"] ** 2
    return result


def render(out, field, domain, occupied, unknown, reference, comparisons):
    """Render geometry, samples and decisive unrestricted-eight-neighbor disagreements."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
    for ax, variant, comparison in zip(axes.flat, field["variants"], comparisons):
        PRIOR.draw_geometry(ax, domain, "#e7eeee", fill=True)
        PRIOR.draw_geometry(ax, reference, "#c8e3d5", fill=True)
        PRIOR.draw_geometry(ax, unknown, "#d97706", fill=True, hatch="///", alpha=.42)
        PRIOR.draw_geometry(ax, occupied, "#9f245f", fill=True)
        PRIOR.draw_geometry(ax, domain, "#176b70", linewidth=1.1)
        points = [(sample["x_m"], sample["y_m"]) for sample in variant["samples"]
                  if sample["occupancy_value"] is False and sample["known_free_under_qualification"] is True]
        if points:
            ax.scatter(*zip(*points), s=4, color="#176b70", alpha=.65)
        diagnostics = comparison["eight_neighbor"]["edge_diagnostics"]
        examples = [] if diagnostics is None else diagnostics["examples"]
        for example in examples:
            ax.plot(*zip(*example["coordinates_m"]), color="#dc2626", linewidth=1.8)
        ax.set_aspect("equal", adjustable="box")
        xmin, ymin, xmax, ymax = domain.bounds
        ax.set_xlim(xmin - .4, xmax + .4)
        ax.set_ylim(ymin - .4, ymax + .4)
        ax.set_title(f"{variant['spacing_m']} m / shift {variant['origin_offset_m'][0]} m | "
                     f"G={len(PRIOR.ACCEPTED._polygon_parts(reference))}, "
                     f"4={len(comparison['four_neighbor']['components'])}, "
                     f"8={len(comparison['eight_neighbor']['components'])}")
        ax.grid(alpha=.15)
        ax.set_xlabel("World X (m)")
        ax.set_ylabel("World Y (m)")
    fig.legend(handles=[Patch(color="#c8e3d5", label="Conditional-empty geometric interior"),
                        Patch(color="#176b70", label="Accepted known-empty samples"),
                        Patch(facecolor="#d97706", hatch="///", alpha=.42, label="Unknown support"),
                        Patch(color="#9f245f", label="Qualified mass"),
                        Patch(color="#dc2626", label="Example diagnostic edge disagreement")], loc="lower center", ncol=3)
    fig.suptitle("PRIMARY eye-plane conditional connectivity comparison (world z = 1.6 m)")
    fig.tight_layout(rect=(0, .08, 1, .96), h_pad=3.2)
    fig.savefig(out / "connectivity_comparison.png", dpi=170)
    plt.close(fig)


def build(out):
    """Read immutable accepted evidence and serialize one bounded comparison."""
    field = PRIOR.read_json(SOURCE / "field_samples.json")
    sections = PRIOR.read_json(SOURCE / "source_sections.json")
    accepted_manifest = PRIOR.read_json(SOURCE / "artifact_manifest.json")
    refs = {item["path"]: item for item in accepted_manifest["artifacts"]}
    for name in ("field_samples.json", "source_sections.json"):
        expected = refs[(SOURCE / name).relative_to(ROOT).as_posix()]
        actual = PRIOR.file_ref(SOURCE / name)
        assert (actual["bytes"], actual["sha256"]) == (expected["bytes"], expected["sha256"])
    assert field["schema"] == "b3-primary-eye-plane-discrete-field/v1"
    assert field["units"] == "m" and field["primary_plane_world_z_m"] == 1.6
    assert field["domain_area_m2"] == 206.5209234821732 and field["domain_holes"] == 2
    assert len(field["variants"]) == 4 and sum(len(v["samples"]) for v in field["variants"]) == 9648
    domain = shape(field["domain_geometry"])
    # The accepted clipped geometries define this S3 comparison; do not repeat raw clipping.
    occupied = shape(field["clipped_qualified_occupied_geometry"])
    unknown = shape(field["clipped_unknown_support_geometry"])
    boundaries = []
    for record in sections["records"]:
        if record.get("occupied_geometry") is None:
            continue
        source_geometry = shape(record["occupied_geometry"])
        if not source_geometry.is_empty:
            boundaries.append(source_geometry.boundary)
    checked = geometric_reference(domain, occupied, unknown, boundaries)
    reference = checked["value"]
    geometric_components = None if reference is None else PRIOR.ACCEPTED._polygon_parts(reference)
    comparisons = [compare_variant(variant, reference, domain, occupied, unknown, boundaries, f"v{index}")
                   for index, variant in enumerate(field["variants"])]
    result = {
        "schema": "b3-primary-eye-plane-connectivity/v1", "status": "design_only_owner_review_required",
        "geometric_reference_status": checked["status"], "geometric_reference_error": checked["error"],
        "primary_plane_world_z_m": field["primary_plane_world_z_m"],
        "units": field["units"], "frame": field["frame"], "domain_area_m2": domain.area,
        "conditional_empty_geometry": None if reference is None else mapping(reference),
        "conditional_empty_area_m2": None if reference is None else reference.area,
        "geometric_components": None if geometric_components is None else [
            {"id": index, "area_m2": polygon.area, "geometry": mapping(polygon)}
            for index, polygon in enumerate(geometric_components)],
        "geometric_component_count": None if geometric_components is None else len(geometric_components),
        "input_geometry_audits": {"domain": PRIOR.geometry_audit(domain), "accepted_clipped_qualified_mass": PRIOR.geometry_audit(occupied),
                                  "accepted_clipped_unknown_support": PRIOR.geometry_audit(unknown)},
        "sample_records": {"reference": PRIOR.file_ref(SOURCE / "field_samples.json"),
                           "id_rule": "v<accepted variant index>:<cell_i>:<cell_j>; masks, positions, unresolved IDs and both distance channels stay in the referenced samples"},
        "comparisons": comparisons,
        "contract": {"target": "conditional empty under accepted qualification only",
                     "geometric_connectivity": "positive-area floating-point open polygon interiors; contacts do not connect",
                     "graph_vertices": "accepted in-domain samples with occupancy_value false and known_free_under_qualification true",
                     "four_neighbor": "axis neighbors only", "eight_neighbor": "all axis and diagonal neighbors; no corner-cut filter",
                     "unknown": "excluded and never relabelled", "positive_override": "preserved from accepted samples",
                     "limits": "No complete physical occupancy, route, visibility, walkability, exact-arithmetic or production claim."},
        "inputs": [PRIOR.file_ref(SOURCE / name) for name in ("field_samples.json", "source_sections.json", "artifact_manifest.json")],
        "code": PRIOR.file_ref(Path(__file__)),
    }
    PRIOR.write_json(out / "connectivity.json", result)
    if reference is not None:
        render(out, field, domain, occupied, unknown, reference, comparisons)
    PRIOR.write_json(out / "artifact_manifest.json", {"schema": "b3-primary-eye-plane-connectivity-artifacts/v1",
                     "status": result["status"], "artifacts": [PRIOR.file_ref(path) for path in out.iterdir()]})
    return result


def main():
    """Create one unique comparison run without replacing prior evidence."""
    out = ROOT / "outputs/design/b3_eye_plane_connectivity" / (
        datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ_") + uuid4().hex[:6])
    out.mkdir(parents=True, exist_ok=False)
    result = build(out)
    print(json.dumps({"out": str(out), "geometric_component_count": result["geometric_component_count"],
                      "conditional_empty_area_m2": result["conditional_empty_area_m2"],
                      "variants": [{"id": item["id"], "four": len(item["four_neighbor"]["components"]),
                                    "eight": len(item["eight_neighbor"]["components"])}
                                   for item in result["comparisons"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
