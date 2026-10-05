"""Verify the bounded, repaired D6 lifecycle status-contract design package."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_INPUT = REPO_ROOT / "outputs/design/live_ifc_candidate_set_lifecycle_experiment"
DEFAULT_OUTPUT = REPO_ROOT / "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/repair_v1"
REPORT = "verification_report.json"
MANIFEST = "artifact_manifest.json"
DESIGN = "status_contract_design.md"
CORE_FILES = (
    "status_contract_matrix.json",
    "lifecycle_transition_fixtures.json",
    "lifecycle_transition_truth.json",
    "provenance.json",
    "lifecycle_transition_diagram.mmd",
)
STABLE_FILES = CORE_FILES + (DESIGN, "run_contract_design.py", "verify_contract_design.py")
REQUIRED_TERMS = {
    "unassigned",
    "ambiguous",
    "singleton",
    "provisional_diagnostic_only",
    "user_confirmed",
    "rejected",
    "replaced",
    "conflict",
    "not_available",
    "partial",
    "invalid",
    "unsupported",
    "diagnostic_only",
}
LIFECYCLE_STATES = {"provisional", "user_confirmed", "rejected", "replaced"}
EVIDENCE_STATES = {"diagnostic_only", "partial", "invalid", "unsupported"}
REQUIRED_EVENT_FIELDS = {
    "event_id",
    "event_type",
    "target_ids",
    "event_sequence",
    "recorded_at",
    "actor",
    "reason_code",
    "is_production_action",
    "provenance_required",
}
FORBIDDEN_PRODUCTION_PREFIXES = (
    "analyzer.py",
    "adapters/",
    "features/",
    "tests/",
    "OCTA_toolbox-master/",
    "pixi.toml",
    "pixi.lock",
)


def load_json(path: Path) -> Any:
    """Load one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    """Write one deterministic, newline-terminated JSON artifact."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_status() -> list[str]:
    """Return short status lines for the bounded scope audit."""
    result = subprocess.run(
        ["git", "status", "--short"], cwd=REPO_ROOT, check=False, capture_output=True, text=True
    )
    return result.stdout.splitlines()


def outside_scope(lines: list[str], allowed_prefix: str) -> list[str]:
    """Return status lines outside the ignored repair output directory."""
    return sorted(line for line in lines if allowed_prefix not in line)


def status_path(line: str) -> str:
    """Extract a path from a short Git status line."""
    return line[3:].strip() if len(line) >= 4 else line.strip()


def check_json_schema(output_root: Path) -> dict[str, Any]:
    """Parse required JSON objects and check the minimum repaired shape."""
    required = {
        "status_contract_matrix.json": {"proposal_only", "layers", "concepts", "contract_shapes"},
        "lifecycle_transition_fixtures.json": {"proposal_only", "real_ifc_context", "synthetic_controls"},
        "lifecycle_transition_truth.json": {"proposal_only", "transition_truth", "invariants", "required_event_fields"},
        "provenance.json": {"proposal_only", "repair_of", "scope", "git_facts"},
    }
    parsed: dict[str, Any] = {}
    failures: list[str] = []
    for name, keys in required.items():
        try:
            value = load_json(output_root / name)
            missing = sorted(keys - set(value)) if isinstance(value, dict) else sorted(keys)
            parsed[name] = {"pass": isinstance(value, dict) and not missing, "top_level_type": type(value).__name__, "missing_keys": missing}
            if missing or not isinstance(value, dict):
                failures.append(f"{name}: invalid top-level shape")
        except Exception as exc:
            parsed[name] = {"pass": False, "error": str(exc)}
            failures.append(name)
    return {"pass": not failures, "files": parsed, "failures": failures}


def bad_independent_labels(value: Any, path: str = "$") -> list[str]:
    """Find serialized lifecycle/evidence fields that use the derived label as state."""
    failures: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "provisional_diagnostic_only":
                failures.append(child_path)
            if key in {"lifecycle_state", "evidence_state", "status", "state", "action_state"} and child == "provisional_diagnostic_only":
                failures.append(child_path)
            failures.extend(bad_independent_labels(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            failures.extend(bad_independent_labels(child, f"{path}[{index}]"))
    return failures


def check_event_sequences(controls: list[dict[str, Any]], required_types: set[str]) -> list[str]:
    """Check ordered event fields and event types in every synthetic control."""
    failures: list[str] = []
    seen_ids: set[str] = set()
    seen_types: set[str] = set()
    for control in controls:
        sequences: list[int] = []
        for event in control.get("events", []):
            missing = REQUIRED_EVENT_FIELDS - set(event)
            if missing:
                failures.append(f"{control.get('fixture_id')}: event missing {sorted(missing)}")
            sequence = event.get("event_sequence")
            if not isinstance(sequence, int):
                failures.append(f"{control.get('fixture_id')}: event_sequence is not an integer")
            else:
                sequences.append(sequence)
            event_id = event.get("event_id")
            if event_id in seen_ids:
                failures.append(f"duplicate event_id: {event_id}")
            seen_ids.add(event_id)
            seen_types.add(event.get("event_type"))
            if event.get("is_production_action") is not False:
                failures.append(f"{event_id}: marked as production action")
            if event.get("provenance_required") is not True:
                failures.append(f"{event_id}: provenance_required is not true")
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            failures.append(f"{control.get('fixture_id')}: event_sequence is not strictly increasing")
    missing_types = sorted(required_types - seen_types)
    if missing_types:
        failures.append(f"required event types missing: {missing_types}")
    return failures


def check_semantics(output_root: Path) -> dict[str, Any]:
    """Check layer separation, transitions, provenance, and fixture invariants."""
    matrix = load_json(output_root / "status_contract_matrix.json")
    fixtures = load_json(output_root / "lifecycle_transition_fixtures.json")
    truth = load_json(output_root / "lifecycle_transition_truth.json")
    provenance = load_json(output_root / "provenance.json")
    failures: list[str] = []

    concepts = {row.get("term") for row in matrix.get("concepts", [])}
    missing_terms = sorted(REQUIRED_TERMS - concepts)
    if missing_terms:
        failures.append(f"required concept terms missing: {missing_terms}")
    layers = matrix.get("layers", {})
    if "not_available" in layers.get("evidence_state", []):
        failures.append("not_available is incorrectly serialized as evidence_state")
    if "not_available" not in layers.get("downstream_availability", []):
        failures.append("downstream_availability does not contain not_available")
    derived = layers.get("derived_display_labels", [])
    if derived != ["provisional_diagnostic_only"]:
        failures.append("derived display layer is not limited to provisional_diagnostic_only")
    if not matrix.get("proposal_only") or not fixtures.get("proposal_only") or not truth.get("proposal_only") or not provenance.get("proposal_only"):
        failures.append("a core artifact claims a frozen production contract")

    serialized = [matrix, fixtures, truth, provenance]
    independent_label_paths = [path for value in serialized for path in bad_independent_labels(value)]
    if independent_label_paths:
        failures.append(f"derived label serialized as an independent state: {independent_label_paths}")

    real = fixtures.get("real_ifc_context", {})
    if real.get("record_class") != "real_ifc":
        failures.append("real context is not tagged real_ifc")
    if real.get("candidate_count") != 8 or len(real.get("candidate_ids", [])) != 8 or len(set(real.get("candidate_ids", []))) != 8:
        failures.append("real context does not contain eight unique candidates")
    facts = real.get("candidate_set_facts", {})
    relation = facts.get("selection_relation", {})
    if facts.get("selection_relation_present") is not True or facts.get("explicit_selection_state") != "none":
        failures.append("real context does not record explicit no-selection")
    if relation.get("selection_state") != "none" or relation.get("selected_candidate_id", "missing") is not None:
        failures.append("real context no-selection relation is malformed")
    if real.get("qualified_authored_domain") or real.get("automatic_candidate_promoted") or not real.get("evidence_only"):
        failures.append("real context claims authored domain, promotion, or non-evidence use")
    for record in real.get("candidates", []):
        if record.get("lifecycle_state") not in LIFECYCLE_STATES or record.get("evidence_state") not in EVIDENCE_STATES:
            failures.append(f"real candidate has mixed or missing layers: {record.get('candidate_id')}")
        if "provisional_diagnostic_only" in record:
            failures.append("real candidate serializes provisional_diagnostic_only as a source field")

    controls = fixtures.get("synthetic_controls", [])
    if not controls or any(control.get("record_class") != "synthetic_control" for control in controls):
        failures.append("synthetic controls are not uniformly tagged synthetic_control")
    for control in controls:
        for record in control.get("candidate_records", []):
            if record.get("record_class") == "real_ifc":
                failures.append(f"synthetic control mixes real_ifc record: {control.get('fixture_id')}")
            if "lifecycle_state" in record and record.get("lifecycle_state") not in LIFECYCLE_STATES:
                failures.append(f"invalid lifecycle state in {control.get('fixture_id')}")
            if "evidence_state" in record and record.get("evidence_state") not in EVIDENCE_STATES:
                failures.append(f"invalid evidence state in {control.get('fixture_id')}")

    by_id = {control.get("fixture_id"): control for control in controls}
    no_selection = by_id.get("explicit_no_selection", {})
    absent = by_id.get("selection_relation_absent", {})
    if no_selection.get("candidate_set", {}).get("selection_relation_present") is not True:
        failures.append("explicit no-selection fixture lacks relation-present flag")
    if no_selection.get("candidate_set", {}).get("selection_relation", {}).get("selected_candidate_id", "missing") is not None:
        failures.append("explicit no-selection fixture selected a candidate")
    if absent.get("candidate_set", {}).get("selection_relation_present") is not False or "selection_relation" in absent.get("candidate_set", {}):
        failures.append("absent-selection fixture does not omit the selection relation")
    if absent.get("expected_after_events", {}).get("meaning") != "selection_not_recorded":
        failures.append("absent-selection meaning is not explicit")

    confirmation = by_id.get("explicit_confirmation_preserves_diagnostic_evidence", {})
    if confirmation.get("expected_after_events", {}).get("lifecycle_state") != "user_confirmed" or confirmation.get("expected_after_events", {}).get("evidence_state") != "diagnostic_only":
        failures.append("confirmation does not preserve diagnostic evidence")
    rejection = by_id.get("explicit_rejection_preserves_evidence", {})
    if rejection.get("expected_after_events", {}).get("evidence_retained") is not True:
        failures.append("rejection does not preserve evidence")
    replacement = by_id.get("replacement_preserves_history_and_evidence", {})
    if replacement.get("expected_after_events", {}).get("prior_version_retained") is not True:
        failures.append("replacement does not retain prior version")
    if not any(record.get("prior_candidate_version_refs") for record in replacement.get("candidate_records", [])):
        failures.append("replacement lacks prior version references")
    edit = by_id.get("manual_boundary_edit_is_ordered_replacement", {})
    if edit.get("expected_after_events", {}).get("old_geometry_mutated") is not False:
        failures.append("manual boundary edit permits mutation of old geometry")
    authored = by_id.get("authored_domain_precedence_retains_automatic", {})
    if authored.get("expected_after_events", {}).get("automatic_candidates_retained") is not True or authored.get("expected_after_events", {}).get("automatic_winner"):
        failures.append("authored precedence does not retain automatic provenance")
    conflict = by_id.get("unresolved_conflict_defers_resolution", {})
    conflict_expected = conflict.get("expected_after_events", {})
    if conflict_expected.get("unresolved") is not True or conflict_expected.get("downstream_availability") != "not_available" or conflict_expected.get("future_resolution_event") != "deferred":
        failures.append("conflict is not unresolved and unavailable")
    if any(event.get("event_type") == "resolve_conflict" for event in conflict.get("events", [])):
        failures.append("conflict fixture invents a resolution event")
    evidence = by_id.get("evidence_quality_does_not_create_winner", {})
    if evidence.get("expected_after_events", {}).get("automatic_winner"):
        failures.append("evidence quality creates an automatic winner")
    missing = by_id.get("missing_domain_propagates_not_available", {})
    if missing.get("expected_after_events", {}).get("selected_candidate_id", "missing") is not None or missing.get("expected_after_events", {}).get("downstream_availability") != "not_available":
        failures.append("missing-domain null/not_available propagation is wrong")

    required_types = {"confirm", "reject", "replace", "assign_authored_domain", "record_conflict", "manual_boundary_edit"}
    failures.extend(check_event_sequences(controls, required_types))
    truth_allowed = [item for item in truth.get("transition_truth", []) if item.get("allowed") is True]
    truth_forbidden = [item for item in truth.get("transition_truth", []) if item.get("allowed") is False]
    if not truth_allowed or not truth_forbidden:
        failures.append("transition truth lacks both allowed and forbidden rows")
    required_truth = {("singleton", "auto_promote"), ("diagnostic_only", "promote_domain"), ("conflict", "silent_resolve")}
    if not required_truth.issubset({(row.get("from"), row.get("event")) for row in truth_forbidden}):
        failures.append("required forbidden transitions are missing")

    return {
        "pass": not failures,
        "failures": failures,
        "synthetic_control_count": len(controls),
        "concept_count": len(concepts),
        "missing_concept_terms": missing_terms,
        "independent_label_paths": independent_label_paths,
    }


def check_diagram(output_root: Path) -> dict[str, Any]:
    """Inspect Mermaid labels, layer nodes, edges, and bounded readability."""
    text = (output_root / "lifecycle_transition_diagram.mmd").read_text(encoding="utf-8")
    required = sorted(REQUIRED_TERMS | {"Candidate-set facts", "evidence_state", "downstream_availability", "explicit no-selection", "selection not recorded", "conflict unresolved"})
    missing = [term for term in required if term not in text]
    lines = text.splitlines()
    failures: list[str] = []
    if len([line for line in lines if line.strip()]) < 20:
        failures.append("diagram has too few non-empty lines")
    if "flowchart TD" not in text or "-->" not in text or "-." not in text or "|confirm event|" not in text:
        failures.append("diagram lacks required flow or relation edges")
    if missing:
        failures.append(f"diagram missing labels: {missing}")
    if any(len(line) > 180 for line in lines):
        failures.append("diagram contains an overlong line")
    return {"pass": not failures, "failures": failures, "nonempty_lines": len([line for line in lines if line.strip()]), "missing_labels": missing}


def check_whitespace(output_root: Path, include_generated: bool = False) -> dict[str, Any]:
    """Check bounded file size, trailing whitespace, and blank-line runs."""
    failures: list[str] = []
    checked: list[str] = []
    for path in sorted(output_root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".mmd", ".py"}:
            continue
        if not include_generated and path.name in {REPORT, MANIFEST}:
            continue
        checked.append(path.name)
        data = path.read_text(encoding="utf-8")
        if path.stat().st_size > 200_000:
            failures.append(f"{path.name} exceeds 200000 bytes")
        if any(re.search(r"[ \t]+$", line) for line in data.splitlines()):
            failures.append(f"{path.name} has trailing whitespace")
        if re.search(r"\n{4,}", data):
            failures.append(f"{path.name} has an unbounded blank-line run")
    return {"pass": not failures, "failures": failures, "checked_files": checked}


def compute_manifest(output_root: Path) -> dict[str, Any]:
    """Record byte counts for stable artifacts without self-reference."""
    entries = [{"path": name, "bytes": (output_root / name).stat().st_size} for name in STABLE_FILES]
    return {"artifact_count": len(entries), "entries": entries, "manifest_excludes": [MANIFEST, REPORT], "hashes": "not used by this bounded verifier"}


def check_manifest(output_root: Path) -> dict[str, Any]:
    """Recompute and compare the manifest byte counts."""
    path = output_root / MANIFEST
    if not path.exists():
        return {"pass": False, "failures": ["manifest missing"]}
    try:
        actual = load_json(path)
        expected = compute_manifest(output_root)
    except Exception as exc:
        return {"pass": False, "failures": [str(exc)]}
    failures = [] if actual == expected else ["manifest entries or byte counts do not match stable artifacts"]
    return {"pass": not failures, "failures": failures, "artifact_count": actual.get("artifact_count")}


def deterministic_repeat(output_root: Path, input_root: Path) -> dict[str, Any]:
    """Rerun the design generator in a temporary directory and compare core bytes."""
    runner = output_root / "run_contract_design.py"
    comparisons: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="d6_status_contract_") as temp:
        temp_root = Path(temp)
        result = subprocess.run(
            [sys.executable, str(runner), "--input", str(input_root), "--output", str(temp_root)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {"pass": False, "failures": ["deterministic rerun failed", result.stderr[-1000:]]}
        for name in CORE_FILES:
            left = (output_root / name).read_bytes()
            right = (temp_root / name).read_bytes()
            comparisons.append({"path": name, "byte_identical": left == right, "bytes": len(left)})
    return {"pass": all(row["byte_identical"] for row in comparisons), "comparisons": comparisons}


def check_production_scope(lines: list[str]) -> dict[str, Any]:
    """Reject tracked or untracked changes in production-owned paths."""
    changed = [status_path(line).replace("\\", "/") for line in lines if line and not line.startswith("?? outputs/")]
    forbidden = [path for path in changed if path.startswith(FORBIDDEN_PRODUCTION_PREFIXES)]
    return {"pass": not forbidden, "forbidden_paths": sorted(forbidden), "checked_paths": sorted(changed)}


def main() -> None:
    """Run bounded checks and write the repaired verification report and manifest."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    input_root = args.input.resolve()
    output_root = args.output.resolve()
    before = git_status()

    parse = check_json_schema(output_root)
    semantics = check_semantics(output_root)
    diagram = check_diagram(output_root)
    whitespace = check_whitespace(output_root)
    repeat = deterministic_repeat(output_root, input_root)
    design_exists = (output_root / DESIGN).exists() and (output_root / DESIGN).read_text(encoding="utf-8").rstrip().endswith("STOP FOR LIFECYCLE STATUS-CONTRACT REPAIR REVIEW")
    scope_before = outside_scope(before, "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/")
    production_scope = check_production_scope(before)
    initial_checks = {
        "json_schema_parsing": parse,
        "transition_invariants": semantics,
        "diagram_inspection": diagram,
        "bounded_whitespace": whitespace,
        "deterministic_rerun": repeat,
        "design_report_ending": {"pass": design_exists},
        "production_scope": production_scope,
        "scope_before_report": {"pass": True, "outside_scope_status": scope_before},
        "production_implementation": {"pass": not production_scope["forbidden_paths"], "implemented": False},
        "full_live_ifc_adapter_rerun": {"pass": True, "performed": False},
        "full_test_suite_rerun": {"pass": True, "performed": False},
    }
    report = {
        "date": "2026-10-05",
        "artifact": "d6_candidate_set_lifecycle_status_contract_repair_v1_design_only",
        "status": "pending_manifest",
        "checks": initial_checks,
        "limitations": [
            "No SHA-256 or other digest check is claimed; the bounded manifest records byte counts only.",
            "The real-IFC case is serialized evidence context; synthetic controls are not real-IFC conclusions.",
            "Production enum names, public APIs, selectors, and conflict resolution remain deferred.",
        ],
    }
    write_json(output_root / REPORT, report)
    write_json(output_root / MANIFEST, compute_manifest(output_root))
    manifest_check = check_manifest(output_root)
    after = git_status()
    scope_after = outside_scope(after, "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/")
    scope_ok = scope_before == scope_after
    final_whitespace = check_whitespace(output_root, include_generated=True)
    report["checks"]["manifest_byte_counts"] = manifest_check
    report["checks"]["git_scope"] = {"pass": scope_ok, "outside_scope_before": scope_before, "outside_scope_after": scope_after}
    report["checks"]["bounded_whitespace_final"] = final_whitespace
    checks = report["checks"]
    report["status"] = "pass" if all(check.get("pass", False) for check in checks.values() if isinstance(check, dict) and "pass" in check) and scope_ok else "fail"
    write_json(output_root / REPORT, report)
    print(json.dumps({"status": report["status"], "report": str(output_root / REPORT), "manifest": str(output_root / MANIFEST)}, sort_keys=True))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
