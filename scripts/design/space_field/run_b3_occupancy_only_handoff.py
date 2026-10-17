"""Promote accepted serialized B3 proxy sections to occupancy-only field evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import sys

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from features.discrete_space_field import load_discrete_space_field
from scripts.design.space_field import run_b3_proxy_eye_plane_comparison as COMP


PRIOR = COMP.PRIOR
SOURCE = ROOT / "outputs/design/b3_proxy_eye_plane_comparison/run_20261009T083535Z_c914e2"
OUTPUT = ROOT / "outputs/design/b3_occupancy_only_handoff"


def accepted_inputs():
    """Read accepted field and source sections without resectioning original meshes."""
    _, originals, metadata, declaration = COMP.accepted_inputs()
    load_discrete_space_field(SOURCE, spacing_m=.25, origin_offset_m=(0., 0.))
    field = PRIOR.read_json(SOURCE / "field_samples.json")
    sections = PRIOR.read_json(SOURCE / "source_sections.json")
    return originals, metadata, declaration, field, sections


def occupancy_only_field(originals, metadata, declaration, field, sections):
    """Require three qualified substitutes before retaining their occupied field."""
    original_records = originals["records"]
    records = sections["records"]
    proxies = records[len(original_records):]
    expected = {
        f"proxy:{group['id']}": [f"live-step-{source['step_id']}" for source in group["sources"]]
        for group in metadata["groups"]
    }
    if (len(expected) != 3 or records[:len(original_records)] != original_records
            or len(proxies) != len(expected) or {row["id"] for row in proxies} != set(expected)
            or field["scope_binding"] != declaration["scope_binding"]
            or field["domain_boundary_policy"]["boundary_member_source_ids"]
            != declaration["boundary_member_source_ids"]):
        raise ValueError("occupancy_handoff_source_or_scope_mismatch")
    represented = [source_id for proxy in proxies for source_id in proxy["represented_source_ids"]]
    original_by_id = {row["id"]: row for row in original_records}
    if (len(represented) != len(set(represented))
            or any(proxy["represented_source_ids"] != expected[proxy["id"]] for proxy in proxies)
            or not set(represented) <= set(original_by_id)
            or any(original_by_id[source_id].get("occupied_geometry") is not None for source_id in represented)
            or set(represented) & set(field["domain_boundary_policy"]["resolved_record_ids"])
            or len(field["scenario_overrides"]) != len(represented)
            or {row["source_id"] for row in field["scenario_overrides"]
                if row["scenario_uncertainty_omitted"]} != set(represented)):
        raise ValueError("occupancy_handoff_duplicate_or_unresolved_source_accounting")
    raw = shape(field["raw_qualified_occupied_geometry"])
    for proxy in proxies:
        geometry = proxy.get("occupied_geometry")
        if (proxy["status"] != "qualified_closed_section" or geometry is None
                or shape(geometry).area <= 0 or shape(geometry).difference(raw).area > 0):
            # Failed or missing substitute geometry must never relabel its source as free.
            raise ValueError("occupancy_handoff_proxy_unqualified")

    active_proxies = []
    for proxy in proxies:
        record = dict(proxy)
        record.pop("analysis_enrollment", None)
        record.pop("comparison_override", None)
        record["evidence_kind"] = "generated_3d_convex_mesh_section_occupancy_only"
        record["physical_occupancy_participation"] = "active_substitute"
        record["furniture_analysis_participation"] = "excluded"
        record["occupancy_substitution"] = "qualified proxy replaces represented original once"
        record["approximation_limit"] = (
            "User-selected 3D convex hull fills original gaps and concavities; "
            "no exact original material, furniture semantics, or complete physical clearance claim"
        )
        active_proxies.append(record)
    policy = {
        "authority": "explicit_user_instruction",
        "local_date": "2026-10-09",
        "scope_binding": field["scope_binding"],
        "source_package_ref": PRIOR.file_ref(SOURCE / "field_samples.json"),
        "source_sections_ref": PRIOR.file_ref(SOURCE / "source_sections.json"),
        "active_proxy_ids": sorted(expected),
        "represented_original_source_ids": sorted(represented),
        "physical_occupancy": "active_qualified_substitutes_independent_of_furniture_eligibility",
        "furniture_analysis": "excluded_including_groups_trends_orientation_and_affordances",
        "original_participation": "preserved_historical_furniture_analysis_fact_not_physical_absence",
    }
    handoff = {
        **field,
        "status": "design_only_occupancy_only_handoff_owner_review_required",
        "occupancy_only_policy": policy,
        "algorithm": {**field["algorithm"],
                      "identity": "accepted serialized qualified proxy sections enrolled as occupancy-only substitutes; no original or proxy resectioning",
                      "endpoint_policy": "Accepted indexed-edge section evidence is reused unchanged; no mesh or section recomputation",
                      "probe_policy": "Accepted parity and shell audits are inherited without rerunning geometry qualification",
                      "qualification": "All three substitutes were qualified in the accepted source package; this handoff checks and reuses those sections for active occupancy",
                      "limit": "Convex substitutes approximate original physical volume; complete material, inventory coverage, occupancy and clearance remain unavailable"},
        "scenario_overrides": [{**row, "reason": "qualified occupancy-only substitute; original uncertainty replaced"}
                               for row in field["scenario_overrides"]],
        "channel_contract": {**field["channel_contract"],
                             "occupancy_value": "Qualified original or active occupancy-only substitute interior; conditional empty only outside retained unknown support; null unknown/outside",
                             "unknown_propagation": "Three active qualified substitutes replace seven represented-original contributions once; missing or failed substitute refuses the handoff, exact boundary members are scoped out, and unrelated unknown remains",
                             "distance_to_raw_qualified_occupied_subset_m": "Unsigned metres to qualified original plus occupancy-only substitute subset; incomplete target, not physical clearance"},
        "sources": [*field["sources"], policy["source_package_ref"], policy["source_sections_ref"]],
        "code": [*field["code"], PRIOR.file_ref(Path(__file__))],
    }
    return handoff, {**sections, "records": [*original_records, *active_proxies]}


def main():
    """Write one versioned A-loadable occupancy-only package from accepted evidence."""
    originals, metadata, declaration, field, sections = accepted_inputs()
    handoff, source_sections = occupancy_only_field(originals, metadata, declaration, field, sections)
    out = OUTPUT / (datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ_") + uuid4().hex[:6])
    out.mkdir(parents=True, exist_ok=False)
    PRIOR.write_json(out / "source_sections.json", source_sections)
    handoff["source_sections"] = PRIOR.file_ref(out / "source_sections.json")
    PRIOR.write_json(out / "field_samples.json", handoff)
    domain = shape(handoff["domain_geometry"])
    occupied = shape(handoff["clipped_qualified_occupied_geometry"])
    unknown = shape(handoff["clipped_unknown_support_geometry"])
    execution = {
        "status": "exit_0", "output": str(out),
        "active_proxy_ids": handoff["occupancy_only_policy"]["active_proxy_ids"],
        "represented_original_count": len(handoff["occupancy_only_policy"]["represented_original_source_ids"]),
        "clipped_occupied_area_m2": occupied.area,
        "clipped_unknown_support_area_m2": unknown.area,
        "conditional_free_area_m2": domain.difference(occupied).difference(unknown).area,
        "counts_025_zero": handoff["variants"][2]["status_counts"],
        "complete_physical_clearance_m": None,
    }
    PRIOR.write_json(out / "execution.json", execution)
    PRIOR.write_json(out / "artifact_manifest.json", {
        "schema": "b3-primary-eye-artifacts/v1", "status": "exit_0",
        "artifacts": [PRIOR.file_ref(out / name)
                      for name in ("field_samples.json", "source_sections.json", "execution.json")],
        "execution": execution,
    })
    print(json.dumps(execution, indent=2), flush=True)


if __name__ == "__main__":
    main()
