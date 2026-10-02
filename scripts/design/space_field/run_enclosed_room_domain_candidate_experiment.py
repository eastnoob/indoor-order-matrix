"""Run the bounded D6 enclosed-room / AnalysisDomain candidate experiment.

This probe is deliberately disposable.  It reads the existing IFC fixture and
adapter, adds only synthetic wall-topology cases, and writes evidence under the
experiment output directory.  It does not modify production code, source IFC,
formal tests, or Blender files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DATE = "2026-10-02"
ROOT = Path(__file__).resolve().parents[3]
LIVE_IFC = ROOT / "outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc"

# The probe is invoked as a file from the repository root; expose that root so
# it can reuse the existing adapter and fixture without packaging changes.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _json(value: object) -> object:
    """Convert tuples and nested mappings into deterministic JSON values."""
    if isinstance(value, Mapping):
        return {str(key): _json(nested) for key, nested in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    return value


def _write_json(path: Path, value: object) -> None:
    """Write one stable, human-readable JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fixture_counts(model: Any) -> dict[str, int]:
    """Count the IFC entities relevant to domain and opening evidence."""
    return {
        key: len(model.by_type(key))
        for key in (
            "IfcSpace",
            "IfcSpatialZone",
            "IfcOpeningElement",
            "IfcRelVoidsElement",
            "IfcRelFillsElement",
            "IfcDoor",
            "IfcWall",
            "IfcSlab",
        )
    }


def _adapter_summary(scene: Any) -> dict[str, object]:
    """Summarize adapter facts without serializing unrelated scene detail."""
    payload = scene.to_dict()
    domain = payload.get("analysis_domain")
    domain_geometry = None
    if isinstance(domain, Mapping):
        refs = list(domain.get("geometry_refs", ()))
        meshes = {item.get("id"): item for item in payload.get("geometries", ())}
        domain_geometry = {
            "geometry_refs": refs,
            "flags": [
                {
                    "id": ref,
                    "is_closed": meshes.get(ref, {}).get("is_closed"),
                    "is_manifold": meshes.get(ref, {}).get("is_manifold"),
                }
                for ref in refs
            ],
        }
    return {
        "analysis_domain": domain,
        "domain_geometry": domain_geometry,
        "opening_refs": [
            {
                "id": item.get("id"),
                "source_id": item.get("source_id"),
                "host_refs": item.get("host_refs", []),
                "geometry_refs": item.get("geometry_refs", []),
                "uncertainties": item.get("uncertainties", []),
            }
            for item in payload.get("openings", ())
        ],
        "uncertainty_codes": sorted({item.get("code") for item in payload.get("uncertainties", ())}),
        "source_geometry_refs": [item.get("id") for item in payload.get("geometries", ())],
        "source_objects": [
            {
                "id": item.get("id"),
                "source_class": item.get("source_class"),
                "source_role": item.get("source_role"),
                "geometry_refs": item.get("geometry_refs", []),
            }
            for item in payload.get("source_objects", ())
        ],
    }


def _adapter_source_geometry(summary: Mapping[str, object]) -> dict[str, object]:
    """Separate adapter source facts from candidate and future derived layers."""
    objects = list(summary.get("source_objects", ()))
    return {
        "scope_enclosure_geometry": {
            "geometry_refs": list((summary.get("domain_geometry") or {}).get("geometry_refs", ())),
            "status": "source_fact_only",
        },
        "wall_occupancy_geometry": [
            {
                "source_id": item.get("id"),
                "source_class": item.get("source_class"),
                "geometry_refs": item.get("geometry_refs", []),
            }
            for item in objects
            if item.get("source_class") in {"IfcWall", "IfcSlab", "IfcCurtainWall", "IfcColumn"}
        ],
        "opening_host_evidence": list(summary.get("opening_refs", ())),
        "derived_free_space_candidate": {
            "status": "not_available",
            "reason": "production_free_space_algorithm_out_of_scope",
        },
    }


def _synthetic_geometry() -> dict[str, object]:
    """Return topology-only fixture geometry used for candidate classification."""
    return {
        "single_large_room": {
            "levels": ["L1"],
            "walls": [
                {"id": "wall-n", "a": [0, 0], "b": [8, 0], "thickness": 0.20, "level": "L1"},
                {"id": "wall-e", "a": [8, 0], "b": [8, 6], "thickness": 0.20, "level": "L1"},
                {"id": "wall-s", "a": [8, 6], "b": [0, 6], "thickness": 0.20, "level": "L1"},
                {"id": "wall-w", "a": [0, 6], "b": [0, 0], "thickness": 0.20, "level": "L1"},
            ],
            "openings": [{"id": "opening-door", "host_refs": ["wall-s"], "scenario": "closed_by_assumption"}],
            "objects": [
                {"id": "table-crossing", "kind": "furniture", "polygon": [[7.5, 5.5], [8.5, 5.5], [8.5, 6.5], [7.5, 6.5]]}
            ],
        },
        "automatic_closed_wall_shell": {
            "levels": ["L1"],
            "walls": [
                {"id": "wall-a", "a": [0, 0], "b": [5, 0], "thickness": 0.18, "level": "L1"},
                {"id": "wall-b", "a": [5, 0], "b": [5, 4], "thickness": 0.18, "level": "L1"},
                {"id": "wall-c", "a": [5, 4], "b": [0, 4], "thickness": 0.18, "level": "L1"},
                {"id": "wall-d", "a": [0, 4], "b": [0, 0], "thickness": 0.18, "level": "L1"},
            ],
            "openings": [{"id": "opening-a", "host_refs": ["wall-b"], "scenario": "closed_by_assumption"}],
            "objects": [],
        },
        "multi_shell_conflict": {
            "levels": ["L1"],
            "walls": [
                {"id": "shell1-a", "a": [0, 0], "b": [4, 0], "thickness": 0.20, "level": "L1"},
                {"id": "shell1-b", "a": [4, 0], "b": [4, 3], "thickness": 0.20, "level": "L1"},
                {"id": "shell1-c", "a": [4, 3], "b": [0, 3], "thickness": 0.20, "level": "L1"},
                {"id": "shell1-d", "a": [0, 3], "b": [0, 0], "thickness": 0.20, "level": "L1"},
                {"id": "shell2-a", "a": [2, 1], "b": [6, 1], "thickness": 0.20, "level": "L1"},
                {"id": "shell2-b", "a": [6, 1], "b": [6, 4], "thickness": 0.20, "level": "L1"},
                {"id": "shell2-c", "a": [6, 4], "b": [2, 4], "thickness": 0.20, "level": "L1"},
                {"id": "shell2-d", "a": [2, 4], "b": [2, 1], "thickness": 0.20, "level": "L1"},
            ],
            "openings": [],
            "objects": [],
        },
        "open_boundary": {
            "levels": ["L1"],
            "walls": [
                {"id": "open-a", "a": [0, 0], "b": [5, 0], "thickness": 0.20, "level": "L1"},
                {"id": "open-b", "a": [5, 0], "b": [5, 4], "thickness": 0.20, "level": "L1"},
                {"id": "open-c", "a": [5, 4], "b": [0, 4], "thickness": 0.20, "level": "L1"},
            ],
            "openings": [],
            "objects": [],
        },
        "cross_floor": {
            "levels": ["L1", "L2"],
            "walls": [
                {"id": "cross-a", "a": [0, 0], "b": [5, 0], "thickness": 0.20, "level": "L1"},
                {"id": "cross-b", "a": [5, 0], "b": [5, 4], "thickness": 0.20, "level": "L2"},
                {"id": "cross-c", "a": [5, 4], "b": [0, 4], "thickness": 0.20, "level": "L2"},
                {"id": "cross-d", "a": [0, 4], "b": [0, 0], "thickness": 0.20, "level": "L1"},
            ],
            "openings": [],
            "objects": [],
        },
    }


def _component_count(walls: Sequence[Mapping[str, object]]) -> tuple[list[list[str]], dict[tuple[float, float], int]]:
    """Return endpoint-connected wall components and endpoint degrees.

    Exact endpoint identity is intentional: this probe tests the contract and
    evidence shape, not a production geometric tolerance or backend.
    """
    endpoint_to_walls: dict[tuple[float, float], list[str]] = defaultdict(list)
    wall_by_id = {str(wall["id"]): wall for wall in walls}
    for wall in walls:
        for endpoint in (wall["a"], wall["b"]):
            endpoint_to_walls[tuple(float(value) for value in endpoint)].append(str(wall["id"]))
    adjacency: dict[str, set[str]] = defaultdict(set)
    for ids in endpoint_to_walls.values():
        for left in ids:
            for right in ids:
                if left != right:
                    adjacency[left].add(right)
    components: list[list[str]] = []
    remaining = set(wall_by_id)
    while remaining:
        root = remaining.pop()
        group = [root]
        queue = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    group.append(neighbor)
                    queue.append(neighbor)
        components.append(sorted(group))
    degrees = {point: len(ids) for point, ids in endpoint_to_walls.items()}
    return sorted(components), degrees


def _automatic_candidate(case_id: str, fixture: Mapping[str, object]) -> dict[str, object]:
    """Classify a synthetic wall shell without selecting a production backend."""
    walls = list(fixture.get("walls", ()))
    components, degrees = _component_count(walls)
    levels = sorted({str(wall.get("level")) for wall in walls})
    closed_components = [component for component in components if all(
        sum(1 for wall in walls if wall["id"] in component and point in (tuple(wall["a"]), tuple(wall["b"]))) == 2
        for point in {tuple(wall["a"]) for wall in walls if wall["id"] in component} | {tuple(wall["b"]) for wall in walls if wall["id"] in component}
    )]
    if len(levels) > 1:
        status = "invalid"
        reason = "cross_analysis_plane_or_level"
    elif not walls:
        status = "not_available"
        reason = "missing_wall_geometry"
    elif len(closed_components) == 1 and len(components) == 1:
        status = "computed"
        reason = "single_connected_closed_wall_shell"
    elif len(closed_components) > 1:
        status = "ambiguous"
        reason = "multiple_closed_shells"
    else:
        status = "partial"
        reason = "open_or_disconnected_wall_boundary"
    wall_refs = [str(wall["id"]) for wall in walls]
    opening_refs = [str(opening["id"]) for opening in fixture.get("openings", ())]
    return {
        "candidate_id": f"candidate:auto:{case_id}",
        "source_ids": wall_refs,
        "geometry_refs": wall_refs,
        "source_kind": "automatic_candidate" if status == "computed" else "diagnostic_only",
        "priority": "automatic candidate" if status == "computed" else "diagnostic-only",
        "closure_scenario": "doors_windows_default_closed_scenario_assumption",
        "analysis_plane": "synthetic-world-plan",
        "units": "m",
        "wall_refs": wall_refs,
        "opening_refs": opening_refs,
        "domain_geometry_status": status,
        "field_geometry_status": "available" if walls else "missing",
        "provenance": {
            "method": "bounded_endpoint_topology_probe",
            "source_case": case_id,
            "wall_thickness_preserved": True,
            "production_backend_selected": False,
        },
        "uncertainty_status": "low" if status == "computed" else "high",
        "status": status,
        "evidence_status": "partial" if any(not opening.get("host_refs") for opening in fixture.get("openings", ())) else "available",
        "status_reason": reason,
        "user_confirmed": False,
        "accepted": False,
        "diagnostic_only": status != "computed",
        "shell_component_count": len(components),
        "endpoint_degree_histogram": {
            str(degree): sum(1 for value in degrees.values() if value == degree)
            for degree in sorted(set(degrees.values()))
        },
    }


def _explicit_candidate(candidate_id: str, source_kind: str, source_ids: Iterable[str], geometry_refs: Iterable[str], *, closure: str, confirmed: bool, status: str = "computed", wall_refs: Iterable[str] = (), opening_refs: Iterable[str] = (), field_status: str = "available") -> dict[str, object]:
    """Build one explicit candidate record with an auditable precedence class."""
    return {
        "candidate_id": candidate_id,
        "source_ids": list(source_ids),
        "geometry_refs": list(geometry_refs),
        "source_kind": source_kind,
        "priority": "user-authored" if source_kind == "user_authored" else "explicit IFC",
        "closure_scenario": closure,
        "analysis_plane": "ifc-world-plan" if source_kind == "explicit_ifc" else "authored-world-plan",
        "units": "m",
        "wall_refs": list(wall_refs),
        "opening_refs": list(opening_refs),
        "domain_geometry_status": status,
        "field_geometry_status": field_status,
        "provenance": {"method": "explicit_source_selection", "source_kind": source_kind},
        "uncertainty_status": "low" if status == "computed" else "high",
        "status": status,
        "evidence_status": "available",
        "status_reason": "explicit_closed_geometry" if status == "computed" else "missing_or_invalid_geometry",
        "user_confirmed": confirmed,
        "accepted": bool(confirmed and status == "computed"),
        "diagnostic_only": False,
    }


def _not_available_candidate(case_id: str, reason: str) -> dict[str, object]:
    """Represent a diagnostic view bound without promoting it to a domain."""
    return {
        "candidate_id": f"candidate:diagnostic:{case_id}",
        "source_ids": [f"diagnostic-bbox:{case_id}"],
        "geometry_refs": [],
        "source_kind": "diagnostic_only",
        "priority": "diagnostic-only",
        "closure_scenario": "none",
        "analysis_plane": "unknown",
        "units": "m",
        "wall_refs": [],
        "opening_refs": [],
        "domain_geometry_status": "not_available",
        "field_geometry_status": "not_available",
        "provenance": {"method": "scene_extent_only", "reason": reason},
        "uncertainty_status": "high",
        "status": "not_available",
        "evidence_status": "missing",
        "status_reason": reason,
        "user_confirmed": False,
        "accepted": False,
        "diagnostic_only": True,
    }


def _resolve_precedence(candidates: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Honor explicit intent before automatic candidates and gate auto acceptance."""
    rank = {"user-authored": 0, "explicit IFC": 1, "automatic candidate": 2, "diagnostic-only": 3}
    ordered = sorted(candidates, key=lambda candidate: (rank.get(str(candidate.get("priority")), 9), str(candidate.get("candidate_id"))))
    # Preserve explicit user/source intent even when geometry is partial or invalid;
    # silently falling through to an automatic shell would hide the evidence gap.
    selected = next((item for item in ordered if item.get("priority") in {"user-authored", "explicit IFC"}), None)
    if selected is None:
        selected = next((item for item in ordered if item.get("priority") == "automatic candidate" and item.get("status") == "computed"), None)
    return {
        "priority_order": ["user-authored", "explicit IFC", "automatic candidate", "diagnostic-only", "not_available"],
        "selected_candidate_id": selected.get("candidate_id") if selected else None,
        "selected_candidate_is_default_only": bool(selected and selected.get("source_kind") == "automatic_candidate" and not selected.get("user_confirmed")),
        "user_confirmation_required": bool(selected and selected.get("source_kind") == "automatic_candidate"),
        "domain_status": selected.get("status") if selected else "not_available",
        "automatic_candidate_suppressed_by_explicit_intent": bool(
            selected and selected.get("priority") in {"user-authored", "explicit IFC"}
            and any(item.get("priority") == "automatic candidate" for item in ordered)
        ),
    }


def _svg_poly(points: Sequence[Sequence[float]], x0: float, y0: float, scale: float, color: str, width: float, *, fill: str = "none", opacity: float = 1.0, dash: str = "") -> str:
    """Render one 2D polyline/polygon element for the static interaction figure."""
    tokens = " ".join(f"{x0 + float(point[0]) * scale:.1f},{y0 - float(point[1]) * scale:.1f}" for point in points)
    return f"<polyline points='{tokens}' fill='{fill}' fill-opacity='{opacity}' stroke='{color}' stroke-width='{width}' {'stroke-dasharray=' + repr(dash) if dash else ''}/>"


def _write_svg(path: Path, synthetic: Mapping[str, Mapping[str, object]]) -> None:
    """Write a static plan-view interaction contract with source/candidate layers."""
    width, height = 1240, 760
    panels = [
        ("single large room", "single_large_room", 40, 35, 245),
        ("authored / explicit", "automatic_closed_wall_shell", 330, 45, 245),
        ("ambiguous multi-shell", "multi_shell_conflict", 640, 45, 245),
        ("no qualified domain", "open_boundary", 950, 45, 245),
    ]
    layers = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' role='img' aria-label='D6 enclosed room domain candidate interaction states'>"]
    layers.append("<rect width='100%' height='100%' fill='#ffffff'/>")
    for title, key, x0, scale, y0 in panels:
        fixture = synthetic[key]
        layers.append(f"<rect x='{x0}' y='55' width='250' height='220' fill='#fafafa' stroke='#d4d4d4'/>")
        layers.append(f"<text x='{x0}' y='40' font-family='Arial' font-size='14' font-weight='bold'>{title}</text>")
        for wall in fixture.get("walls", ()):
            layers.append(_svg_poly([wall["a"], wall["b"]], x0 + 10, y0, scale, "#525252", 7))
            # The thicker stroke is deliberate evidence of physical wall field geometry.
        for opening in fixture.get("openings", ()):
            layers.append(f"<circle cx='{x0 + 125}' cy='{y0 - 8}' r='5' fill='#dc2626'/>")
        if key in {"single_large_room", "automatic_closed_wall_shell"}:
            walls = fixture.get("walls", ())
            boundary = [wall["a"] for wall in walls] + [walls[0]["a"]]
            layers.append(_svg_poly(boundary, x0 + 10, y0, scale, "#f59e0b", 3, fill="#fef3c7", opacity=0.25))
            if key == "single_large_room":
                # Blue is the authored override; green is the selected/hovered state.
                layers.append(_svg_poly(boundary, x0 + 10, y0, scale, "#2563eb", 3, fill="none", opacity=0.9))
            layers.append(_svg_poly(boundary, x0 + 10, y0, scale, "#22c55e", 5, fill="none", opacity=0.8, dash="8 5"))
            layers.append(f"<text x='{x0 + 8}' y='295' font-family='Arial' font-size='11' fill='#15803d'>hover/selected candidate</text>")
        elif key == "multi_shell_conflict":
            for component in ([fixture["walls"][:4], fixture["walls"][4:]]):
                boundary = [wall["a"] for wall in component] + [component[0]["a"]]
                layers.append(_svg_poly(boundary, x0 + 10, y0, scale, "#f59e0b", 3, fill="#fef3c7", opacity=0.25))
            layers.append(f"<text x='{x0 + 8}' y='295' font-family='Arial' font-size='11' fill='#92400e'>candidate not accepted: ambiguous</text>")
        else:
            layers.append(f"<text x='{x0 + 8}' y='190' font-family='Arial' font-size='12' fill='#b91c1c'>NOT AVAILABLE — NO QUALIFIED</text>")
            layers.append(f"<text x='{x0 + 8}' y='208' font-family='Arial' font-size='12' fill='#b91c1c'>ANALYSIS DOMAIN</text>")
    legend_y = 350
    legend = [
        ("#f59e0b", "automatic candidate"),
        ("#2563eb", "authored candidate"),
        ("#22c55e", "hover/selected"),
        ("#525252", "physical wall field"),
        ("#dc2626", "opening evidence"),
    ]
    for index, (color, label) in enumerate(legend):
        y = legend_y + index * 32
        layers.append(f"<line x1='55' y1='{y}' x2='95' y2='{y}' stroke='{color}' stroke-width='8'/><text x='110' y='{y + 5}' font-family='Arial' font-size='14'>{label}</text>")
    layers.append("<line x1='410' y1='350' x2='450' y2='350' stroke='#2563eb' stroke-width='6'/><text x='465' y='355' font-family='Arial' font-size='14'>candidate not accepted</text>")
    layers.append("<text x='55' y='560' font-family='Arial' font-size='14' font-weight='bold'>Interaction contract (static state only)</text>")
    interaction = [
        "hover candidate → highlight green + show source kind, closure, wall/opening refs, uncertainty/status",
        "accept / reject → record user-confirmed and accepted fields; automatic stays pending until accepted",
        "edit / redraw → replace scope geometry while preserving source geometry and provenance",
        "split / merge → create explicit user-authored candidates; keep original automatic candidate diagnostic",
    ]
    for index, line in enumerate(interaction):
        layers.append(f"<text x='55' y='{590 + index * 24}' font-family='Arial' font-size='13'>{line}</text>")
    layers.append("</svg>")
    path.write_text("".join(layers), encoding="utf-8")


def _run(output: Path) -> dict[str, object]:
    """Run all fixture probes and materialize the bounded evidence bundle."""
    output.mkdir(parents=True, exist_ok=True)
    import ifcopenshell
    from adapters.ifc_bonsai import load_ifc_neutral_scene
    from test.fixtures.ifc4_description_fixture import write_ifc4_description_fixture

    fixture_path = output / "fixture_workspace" / "ifc4_description_fixture.ifc"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_ids = write_ifc4_description_fixture(fixture_path)
    fixture = ifcopenshell.open(str(fixture_path))
    base_counts = _fixture_counts(fixture)

    cases: list[dict[str, object]] = []
    explicit_domain = load_ifc_neutral_scene(fixture_path, analysis_domain_source_id=fixture_ids["room"])
    explicit_summary = _adapter_summary(explicit_domain)
    explicit_flags = list((explicit_summary.get("domain_geometry") or {}).get("flags", ()))
    explicit_status = (
        "computed"
        if explicit_flags and all(flag.get("is_closed") is True and flag.get("is_manifold") is True for flag in explicit_flags)
        else "partial"
        if explicit_flags
        else "not_available"
    )
    explicit_field_status = "available" if explicit_flags else "missing"
    cases.append({
        "case_id": "positive_ifc4_explicit_ifcspace",
        "class": "A",
        "fixture_kind": "existing_ifc4_positive_fixture",
        "ifc_observed": {"schema": fixture.schema, "counts": base_counts},
        "candidate_records": [_explicit_candidate(
            "candidate:ifcspace:room",
            "explicit_ifc",
            [f"ifc-object:{fixture_ids['room']}"],
            explicit_summary.get("domain_geometry", {}).get("geometry_refs", []) if explicit_summary.get("domain_geometry") else [],
            closure="observed_explicit_ifcspace_geometry",
            confirmed=True,
            status=explicit_status,
            field_status=explicit_field_status,
            wall_refs=[f"ifc-object:{fixture_ids['wall']}"],
            opening_refs=[f"ifc-opening:{fixture_ids['opening']}"],
        )],
        "source_geometry": _adapter_source_geometry(explicit_summary),
        "adapter_observation": explicit_summary,
        "selection": _resolve_precedence([_explicit_candidate(
            "candidate:ifcspace:room", "explicit_ifc", [f"ifc-object:{fixture_ids['room']}"],
            explicit_summary.get("domain_geometry", {}).get("geometry_refs", []) if explicit_summary.get("domain_geometry") else [],
            closure="observed_explicit_ifcspace_geometry", confirmed=True,
            status=explicit_status, field_status=explicit_field_status,
            wall_refs=[f"ifc-object:{fixture_ids['wall']}"], opening_refs=[f"ifc-opening:{fixture_ids['opening']}"],
        )]),
    })

    missing_domain = load_ifc_neutral_scene(fixture_path)
    cases.append({
        "case_id": "negative_missing_domain",
        "class": "C",
        "fixture_kind": "existing_ifc4_positive_fixture_without_selection",
        "ifc_observed": {"schema": fixture.schema, "counts": base_counts},
        "candidate_records": [_not_available_candidate("negative_missing_domain", "no_explicit_domain_selected")],
        "source_geometry": _adapter_source_geometry(_adapter_summary(missing_domain)),
        "adapter_observation": _adapter_summary(missing_domain),
        "selection": _resolve_precedence([_not_available_candidate("negative_missing_domain", "no_explicit_domain_selected")]),
    })

    missing_geometry_model = ifcopenshell.open(str(fixture_path))
    missing_geometry_model.by_guid(fixture_ids["room"]).Representation = None
    missing_geometry_scene = load_ifc_neutral_scene(missing_geometry_model, analysis_domain_source_id=fixture_ids["room"])
    missing_geometry_candidate = _explicit_candidate(
        "candidate:ifcspace:missing-geometry", "explicit_ifc", [f"ifc-object:{fixture_ids['room']}"], [],
        closure="explicit_record_without_geometry", confirmed=True, status="not_available", field_status="missing",
    )
    missing_geometry_candidate["evidence_status"] = "missing"
    cases.append({
        "case_id": "negative_domain_missing_geometry",
        "class": "C",
        "fixture_kind": "existing_ifc4_negative_in_memory_variant",
        "ifc_observed": {"schema": missing_geometry_model.schema, "counts": _fixture_counts(missing_geometry_model)},
        "candidate_records": [missing_geometry_candidate],
        "source_geometry": _adapter_source_geometry(_adapter_summary(missing_geometry_scene)),
        "adapter_observation": _adapter_summary(missing_geometry_scene),
        "selection": _resolve_precedence([missing_geometry_candidate]),
    })

    broken_relation_model = ifcopenshell.open(str(fixture_path))
    for relation in list(broken_relation_model.by_type("IfcRelVoidsElement")):
        broken_relation_model.remove(relation)
    broken_relation_scene = load_ifc_neutral_scene(broken_relation_model, analysis_domain_source_id=fixture_ids["room"])
    broken_candidate = _explicit_candidate(
        "candidate:ifcspace:broken-opening-host", "explicit_ifc", [f"ifc-object:{fixture_ids['room']}"],
        explicit_summary.get("domain_geometry", {}).get("geometry_refs", []) if explicit_summary.get("domain_geometry") else [],
        closure="observed_explicit_ifcspace_geometry", confirmed=True,
        status=explicit_status, field_status=explicit_field_status,
        wall_refs=[f"ifc-object:{fixture_ids['wall']}"], opening_refs=[f"ifc-opening:{fixture_ids['opening']}"],
    )
    broken_candidate["uncertainty_status"] = "medium"
    broken_candidate["evidence_status"] = "partial"
    broken_candidate["status_reason"] = "domain_computed_opening_host_relation_missing"
    cases.append({
        "case_id": "negative_opening_host_relation_broken",
        "class": "A/B evidence conflict",
        "fixture_kind": "existing_ifc4_negative_in_memory_variant",
        "ifc_observed": {"schema": broken_relation_model.schema, "counts": _fixture_counts(broken_relation_model)},
        "candidate_records": [broken_candidate],
        "source_geometry": _adapter_source_geometry(_adapter_summary(broken_relation_scene)),
        "adapter_observation": _adapter_summary(broken_relation_scene),
        "selection": _resolve_precedence([broken_candidate]),
    })

    synthetic = _synthetic_geometry()
    auto_cases = [
        ("automatic_closed_wall_shell", "B"),
        ("single_large_room", "B"),
        ("multi_shell_conflict", "B"),
        ("open_boundary", "B"),
        ("cross_floor", "B"),
    ]
    for case_id, group in auto_cases:
        candidate = _automatic_candidate(case_id, synthetic[case_id])
        if case_id == "single_large_room":
            authored = _explicit_candidate(
                "candidate:user:closed-curve", "user_authored", ["user:closed-curve:single-room"], ["user-curve:single-room"],
                closure="authored_closed_curve", confirmed=True,
                wall_refs=[wall["id"] for wall in synthetic[case_id]["walls"]],
                opening_refs=[opening["id"] for opening in synthetic[case_id]["openings"]],
            )
            records = [candidate, authored]
        else:
            records = [candidate]
        cases.append({
            "case_id": case_id,
            "class": group,
            "fixture_kind": "synthetic_topology_fixture",
            "ifc_observed": None,
            "candidate_records": records,
            "source_geometry": {
                "scope_enclosure_geometry": [
                    {"id": wall["id"], "kind": "wall_segment", "a": wall["a"], "b": wall["b"], "level": wall["level"]}
                    for wall in synthetic[case_id]["walls"]
                ],
                "wall_occupancy_geometry": [
                    {"id": wall["id"], "kind": "physical_wall_field", "thickness": wall["thickness"], "a": wall["a"], "b": wall["b"], "level": wall["level"]}
                    for wall in synthetic[case_id]["walls"]
                ],
                "other_source_geometry": [
                    {
                        "id": item["id"],
                        "kind": item["kind"],
                        "geometry": item["polygon"],
                        "source_geometry_retained": True,
                        "domain_overlap_status": "partial" if case_id == "single_large_room" else "unknown",
                    }
                    for item in synthetic[case_id].get("objects", ())
                ],
                "opening_host_evidence": synthetic[case_id]["openings"],
                "derived_free_space_candidate": {"status": "not_available", "reason": "production_free_space_algorithm_out_of_scope"},
            },
            "selection": _resolve_precedence(records),
        })

    live_inventory = None
    if LIVE_IFC.exists():
        live = ifcopenshell.open(str(LIVE_IFC))
        live_inventory = {
            "path": str(LIVE_IFC.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(LIVE_IFC),
            "schema": live.schema,
            "counts": _fixture_counts(live),
            "geometry_adapter": "not_verified",
            "native_inventory_only": True,
        }

    candidate_results = {
        "schema": "d6-enclosed-room-domain-candidate-experiment-v1",
        "date": DATE,
        "owner_directions": {
            "single_large_room_auto_candidate": "hypothesis_to_test",
            "explicit_inputs_long_term_primary": "owner_direction",
            "explicit_overrides_automatic": "owner_direction",
            "ui_confirmation_required": "owner_direction",
        },
        "priority_order": ["user-authored", "explicit IFC", "automatic candidate", "diagnostic-only", "not_available"],
        "cases": cases,
        "live_ifc_inventory": live_inventory,
        "global_constraints": {
            "wall_thickness_retained_as_physical_field_geometry": True,
            "source_scope_field_derived_separated": True,
            "door_state_is_scenario_assumption": True,
            "opening_relation_not_inferred_from_door_geometry": True,
            "free_space_connectivity_path_not_computed": True,
            "production_threshold_backend_resolution_not_selected": True,
        },
        "next_gate": "boundary/free-space design remains blocked until owner review of candidate semantics",
    }
    _write_json(output / "candidate_results.json", candidate_results)
    _write_json(output / "fixture_manifest.json", {
        "existing_ifc4_positive_fixture": {
            "path": str(fixture_path.relative_to(output)).replace("\\", "/"),
            "schema": fixture.schema,
            "ids": fixture_ids,
            "counts": base_counts,
        },
        "negative_variants": [
            "negative_missing_domain",
            "negative_domain_missing_geometry",
            "negative_opening_host_relation_broken",
        ],
        "synthetic_variants": sorted(synthetic),
    })
    _write_json(output / "source_geometry.json", {
        "cases": {
            case["case_id"]: case.get("source_geometry", {})
            for case in cases if case.get("source_geometry")
        },
        "separation_rule": "scope_enclosure_geometry, wall_occupancy_geometry, opening_host_evidence, and derived_free_space_candidate are separate records",
    })
    _write_json(output / "provenance.json", {
        "read_only_sources": [
            "AGENTS.md",
            "docs/indoor_layout_evaluation_matrix_architecture_memory.md",
            "docs/project/space-field-ifc-neutral-scene-input-contract.md",
            "docs/project/evidence/d6-space-field-input-contract-owner-decision.md",
            "docs/project/evidence/d6-space-field-ifc-input-contract-experiment-repair-v1-independent-review.md",
            "docs/project/evidence/d6-space-field-closed-open-independent-review.md",
            "features/scene_contract.py",
            "features/scene_loader.py",
            "features/scene_inference.py",
            "features/neutral_scene_views.py",
            "features/boundary_evidence.py",
            "adapters/ifc_bonsai.py",
            "adapters/blender_geometry.py",
            "adapters/blender_preview.py",
            "test/fixtures/ifc4_description_fixture.py",
        ],
        "observed": ["IFC entity counts", "adapter domain/opening/geometry facts", "source file SHA-256"],
        "derived": ["synthetic wall topology statuses", "precedence resolution", "static interaction states"],
        "assumptions": ["default door/window closure is a scenario assumption", "exact endpoint identity is probe-only and not a production tolerance", "automatic candidate is not accepted without user confirmation"],
    })
    _write_svg(output / "interaction_states.svg", synthetic)
    command_log = {
        "runner": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
        "argv": sys.argv,
        "exit_code": 0,
        "scope": "bounded read-only candidate experiment",
    }
    _write_json(output / "command_log.json", command_log)
    artifact_paths = [
        path
        for path in output.rglob("*")
        if path.is_file()
        and path.name != "artifact_manifest.json"
        and not any(part.startswith("tmp_reproduction_") for part in path.relative_to(output).parts)
    ]
    manifest = {
        "schema": "d6-enclosed-room-domain-candidate-artifact-manifest-v1",
        "artifacts": [
            {"path": str(path.relative_to(output)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(artifact_paths)
        ],
    }
    _write_json(output / "artifact_manifest.json", manifest)
    return {
        "case_count": len(cases),
        "artifact_count": len(artifact_paths) + 1,
        "output": str(output),
        "live_ifc_inventory": live_inventory,
    }


def main() -> int:
    """Parse the output path and run the bounded experiment."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = _run(args.output.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
