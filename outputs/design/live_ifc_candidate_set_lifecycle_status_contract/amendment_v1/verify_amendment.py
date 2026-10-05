"""Verify and report the bounded lifecycle amendment evidence package."""

from __future__ import annotations

import copy
import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE.parents[3]
DESIGN_RECORD = Path("docs/project/evidence/d6-space-field-candidate-set-lifecycle-status-contract-amendment-v1.md")
FIXTURE_PATH = PACKAGE / "fixtures.json"
TRUTH_PATH = PACKAGE / "truth.json"
PROBE_PATH = PACKAGE / "probe.py"
REPORT_PATH = PACKAGE / "verification_report.json"
MANIFEST_PATH = PACKAGE / "artifact_manifest.json"
MANIFEST_PATHS = [DESIGN_RECORD, FIXTURE_PATH.relative_to(REPO_ROOT), TRUTH_PATH.relative_to(REPO_ROOT), PROBE_PATH.relative_to(REPO_ROOT), Path(__file__).resolve().relative_to(REPO_ROOT)]
PACKAGE_RELATIVE_PATH = PACKAGE.relative_to(REPO_ROOT)
SCOPE_PATHS = sorted(set(MANIFEST_PATHS + [
    PACKAGE_RELATIVE_PATH / "artifact_manifest.json",
    PACKAGE_RELATIVE_PATH / "verification_report.json",
]))


def _reject_constant(value: str) -> None:
    """Reject JSON NaN and infinity tokens, which are not standard JSON."""
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON object keys rather than silently keeping one."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    """Parse strict UTF-8 JSON and reject duplicate keys and non-finite values."""
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def _require(condition: bool, message: str) -> None:
    """Raise a focused verification error when a contract assertion fails."""
    if not condition:
        raise AssertionError(message)


def _run_git(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a Git inspection command from the repository root."""
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _check_git_diff_and_scope() -> tuple[str, dict[str, Any]]:
    """Check scoped diff whitespace and report the current Git scope state."""
    scope_args = ["--", *(path.as_posix() for path in SCOPE_PATHS)]
    for arguments in (["diff", "--check", *scope_args], ["diff", "--cached", "--check", *scope_args]):
        completed = _run_git(arguments)
        _require(completed.returncode == 0, f"Git whitespace check failed: {completed.stderr or completed.stdout}")

    status = _run_git(["status", "--porcelain=v1", "--untracked-files=all"])
    _require(status.returncode == 0, f"Git scope status failed: {status.stderr}")
    status_rows = [(line[:2], line[3:]) for line in status.stdout.splitlines()]
    scope_set = {path.as_posix() for path in SCOPE_PATHS}
    tracked_dirty = sorted(path for code, path in status_rows if code not in {"??", "!!", "  "})
    staged = sorted(path for code, path in status_rows if code not in {"??", "!!", "  "} and code[0] != " ")
    in_scope_untracked = sorted(path for code, path in status_rows if code == "??" and path in scope_set)
    out_of_scope_tracked = sorted(path for path in tracked_dirty if path not in scope_set)
    out_of_scope_staged = sorted(path for path in staged if path not in scope_set)
    _require(not out_of_scope_tracked and not out_of_scope_staged, "tracked Git changes exist outside the amendment scope")

    package_paths = [path for path in SCOPE_PATHS if path != DESIGN_RECORD]
    ignored_count = 0
    for path in package_paths:
        ignored = _run_git(["check-ignore", "--quiet", "--no-index", "--", path.as_posix()])
        _require(ignored.returncode in {0, 1}, f"Git ignore audit failed for {path.as_posix()}: {ignored.stderr}")
        ignored_count += ignored.returncode == 0

    branch = _run_git(["branch", "--show-current"])
    _require(branch.returncode == 0, f"Git branch query failed: {branch.stderr}")
    audit = {
        "branch": branch.stdout.strip(),
        "ignored_outputs_package_paths": ignored_count,
        "in_scope_untracked_paths": in_scope_untracked,
        "scope_paths": [path.as_posix() for path in SCOPE_PATHS],
        "staged_paths": staged,
        "status": "PASS",
        "tracked_dirty_paths": tracked_dirty,
    }
    return "PASS", audit


def _check_scoped_whitespace(generated_files: dict[Path, bytes]) -> None:
    """Reject trailing spaces and missing final newlines in scoped artifacts."""
    for relative_path in SCOPE_PATHS:
        data = generated_files.get(relative_path, (REPO_ROOT / relative_path).read_bytes())
        _require(data.endswith(b"\n"), f"scoped artifact lacks a final newline: {relative_path.as_posix()}")
        for line_number, line in enumerate(data.splitlines(), start=1):
            _require(not line.endswith((b" ", b"\t")), f"scoped artifact has trailing whitespace: {relative_path.as_posix()}:{line_number}")


def _validate_assignment_schema(assignment: dict[str, Any]) -> None:
    """Check the structural schema and semantics for assignment state records."""
    _require(set(assignment) == {"status", "domain_id", "source_domain_ids", "reason"}, "assignment keys do not match schema")
    _require(assignment["status"] in {"absent", "unresolved", "assigned"}, "unknown assignment status")
    _require(type(assignment["source_domain_ids"]) is list, "source_domain_ids must be an array")
    _require(all(type(value) is str and value for value in assignment["source_domain_ids"]), "source domain IDs must be non-empty strings")
    if assignment["status"] == "absent":
        _require(assignment["domain_id"] is None and not assignment["source_domain_ids"] and bool(assignment["reason"]), "absent assignment shape is invalid")
    elif assignment["status"] == "unresolved":
        _require(assignment["domain_id"] is None and len(assignment["source_domain_ids"]) > 1 and bool(assignment["reason"]), "unresolved assignment shape is invalid")
    else:
        _require(type(assignment["domain_id"]) is str and assignment["domain_id"], "assigned state requires a domain ID")
        _require(assignment["source_domain_ids"] == [assignment["domain_id"]] and assignment["reason"] is None, "assigned assignment shape is invalid")


def _validate_version_schema(version: dict[str, Any]) -> None:
    """Check candidate-version fields and provenance structure."""
    required = {
        "candidate_id", "candidate_version_id", "version_ordinal", "lifecycle_state",
        "user_confirmed", "evidence_state", "provenance",
    }
    _require(set(version) == required, "candidate-version keys do not match schema")
    _require(type(version["candidate_id"]) is str and bool(version["candidate_id"]), "candidate_id must be a non-empty string")
    _require(type(version["candidate_version_id"]) is str and bool(version["candidate_version_id"]), "candidate_version_id must be a non-empty string")
    _require(type(version["version_ordinal"]) is int and version["version_ordinal"] > 0, "version_ordinal must be a positive integer")
    _require(version["candidate_version_id"] == f"{version['candidate_id']}@{version['version_ordinal']}", "candidate version ID and ordinal disagree")
    _require(version["lifecycle_state"] in {"provisional", "user_confirmed", "replaced"}, "unknown lifecycle state")
    _require(type(version["user_confirmed"]) is bool, "user_confirmed must be boolean")
    if version["lifecycle_state"] == "user_confirmed":
        _require(version["user_confirmed"], "user_confirmed lifecycle requires the confirmation fact")
    if version["lifecycle_state"] == "provisional":
        _require(not version["user_confirmed"], "provisional lifecycle cannot already be confirmed")
    _require(version["evidence_state"] == "diagnostic_only", "fixture evidence state must remain diagnostic_only")
    provenance = version["provenance"]
    _require(set(provenance) == {
        "origin", "source_ref", "prior_candidate_version_id", "replacement_event_id", "replaced_by_candidate_version_id",
    }, "provenance keys do not match schema")
    _require(provenance["origin"] in {"automatic_candidate", "replacement"}, "unknown provenance origin")
    _require(type(provenance["source_ref"]) is str and bool(provenance["source_ref"]), "source_ref must be non-empty")


def _validate_fixture_schema(fixture: dict[str, Any]) -> None:
    """Check required fields, types, enumerations, and event-specific shapes."""
    _require(set(fixture) == {"artifact_type", "ordering", "cases"}, "fixture root keys do not match schema")
    _require(fixture["artifact_type"] == "d6_lifecycle_status_contract_amendment_fixtures_v1", "unexpected fixture artifact type")
    ordering = fixture["ordering"]
    _require(ordering == {
        "sort_keys": ["occurred_at", "sequence", "event_id"],
        "timestamp_format": "YYYY-MM-DDTHH:MM:SSZ",
        "tie_break": "event_id_ascending_ascii",
    }, "ordering declaration does not match the amendment contract")
    _require(type(fixture["cases"]) is list and len(fixture["cases"]) == 2, "fixture must contain exactly two bounded cases")
    case_ids = []
    base_event_keys = {"event_id", "sequence", "occurred_at", "event_type", "actor_type"}
    event_fields = {
        "assign_authored_domain": {"domain_id"},
        "confirm_candidate": {"candidate_version_id"},
        "replace_candidate_version": {"prior_candidate_version_id", "replacement_version"},
        "record_unresolved_authored_domain_assignment": {"source_domain_ids", "reason"},
    }
    for case in fixture["cases"]:
        _require(set(case) == {"case_id", "initial_state", "events"}, "case keys do not match schema")
        case_ids.append(case["case_id"])
        state = case["initial_state"]
        _require(set(state) == {"candidate_id", "active_candidate_version_id", "candidate_versions", "authored_domain_assignment"}, "initial state keys do not match schema")
        _require(type(state["candidate_versions"]) is list and state["candidate_versions"], "candidate_versions must be non-empty")
        for version in state["candidate_versions"]:
            _validate_version_schema(version)
        ordinals = [version["version_ordinal"] for version in state["candidate_versions"]]
        _require(ordinals == list(range(1, len(ordinals) + 1)), "initial version ordinals must be unique and monotonic")
        _require(all(version["candidate_id"] == state["candidate_id"] for version in state["candidate_versions"]), "initial versions must retain one candidate_id")
        _require(state["active_candidate_version_id"] in {version["candidate_version_id"] for version in state["candidate_versions"]}, "active initial version is missing")
        _validate_assignment_schema(state["authored_domain_assignment"])
        _require(type(case["events"]) is list and case["events"], "each fixture case requires events")
        event_ids = []
        for event in case["events"]:
            event_type = event.get("event_type")
            _require(event_type in event_fields, f"unsupported event type in fixture schema: {event_type}")
            _require(set(event) == base_event_keys | event_fields[event_type], f"event keys do not match schema for {event_type}")
            _require(type(event["event_id"]) is str and bool(event["event_id"]), "event_id must be a non-empty string")
            _require(event["event_id"].isascii(), "event_id must be ASCII text")
            event_ids.append(event["event_id"])
            _require(type(event["sequence"]) is int, "event sequence must be an integer")
            _require(event["actor_type"] == "user", "fixture lifecycle events must have explicit user actor")
            if event_type == "replace_candidate_version":
                _validate_version_schema(event["replacement_version"])
        _require(len(event_ids) == len(set(event_ids)), "event IDs must be unique within each case")
    _require(case_ids == ["lineage_and_authored_assignment", "unresolved_assignment"], "fixture case IDs/order changed")


def _validate_truth_schema(truth: dict[str, Any]) -> None:
    """Check the bounded expected-output structure before comparison."""
    _require(set(truth) == {"artifact_type", "cases"}, "truth root keys do not match schema")
    _require(truth["artifact_type"] == "d6_lifecycle_status_contract_amendment_truth_v1", "unexpected truth artifact type")
    _require(type(truth["cases"]) is list and len(truth["cases"]) == 2, "truth must contain two cases")
    for case in truth["cases"]:
        _require(set(case) == {"case_id", "ordered_event_ids", "tie_groups", "after_each_event", "final_state"}, "truth case keys do not match schema")
        _require(type(case["ordered_event_ids"]) is list and type(case["tie_groups"]) is list, "truth event outputs must be arrays")
        _require(type(case["after_each_event"]) is list and type(case["final_state"]) is dict, "truth state outputs have invalid types")
        _require(case["final_state"]["candidate_versions"], "truth final state must retain candidate versions")
        _validate_assignment_schema(case["final_state"]["authored_domain_assignment"])
    _require([case["case_id"] for case in truth["cases"]] == ["lineage_and_authored_assignment", "unresolved_assignment"], "truth case IDs/order changed")


def _canonical_bytes(value: Any) -> bytes:
    """Serialize JSON in the same stable form used for rerun comparison."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _run_probe() -> bytes:
    """Run the deterministic probe in a fresh interpreter and return its bytes."""
    completed = subprocess.run(
        [sys.executable, "-B", str(PROBE_PATH), str(FIXTURE_PATH)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _check_event_id_rejections(fixture: dict[str, Any]) -> dict[str, bool]:
    """Check both fixture validation and probe ordering reject invalid event IDs."""
    probe_event_order = runpy.run_path(str(PROBE_PATH))["_event_order"]
    invalid_kinds = {
        "empty": ("", "non-empty", "non-empty"),
        "duplicate": (None, "unique", "duplicate"),
        "non_ascii": ("evt-é", "ASCII", "ASCII"),
    }
    checks = {}
    for kind, (replacement_id, verifier_text, probe_text) in invalid_kinds.items():
        invalid_fixture = copy.deepcopy(fixture)
        invalid_events = invalid_fixture["cases"][0]["events"]
        if kind == "duplicate":
            invalid_events[1]["event_id"] = invalid_events[0]["event_id"]
        else:
            invalid_events[0]["event_id"] = replacement_id

        try:
            _validate_fixture_schema(invalid_fixture)
        except AssertionError as error:
            _require(verifier_text in str(error), f"verifier rejected {kind} event_id for the wrong reason")
        else:
            raise AssertionError(f"verifier accepted {kind} event_id")
        checks[f"verifier_rejects_{kind}_event_id"] = True

        try:
            probe_event_order(invalid_events)
        except ValueError as error:
            _require(probe_text in str(error), f"probe rejected {kind} event_id for the wrong reason")
        else:
            raise AssertionError(f"probe accepted {kind} event_id")
        checks[f"probe_rejects_{kind}_event_id"] = True
    return checks


def _check_stale_version_rejection(fixture: dict[str, Any]) -> bool:
    """Assert stale confirmation fails before changing the replay state."""
    module = runpy.run_path(str(PROBE_PATH))
    apply_event = module["_apply_event"]
    event_order = module["_event_order"]
    case = copy.deepcopy(fixture["cases"][0])
    state = copy.deepcopy(case["initial_state"])
    ordered_events = event_order(case["events"])
    for event in ordered_events[:3]:
        apply_event(state, event)
    stale_event = copy.deepcopy(ordered_events[3])
    stale_event["candidate_version_id"] = "candidate-west-01@1"
    before = copy.deepcopy(state)
    try:
        apply_event(state, stale_event)
    except ValueError as error:
        _require("active candidate version" in str(error), "stale confirmation was rejected for the wrong reason")
    else:
        raise AssertionError("stale confirmation was accepted")
    _require(state == before, "stale confirmation mutated state before rejection")
    return True


def _check_transition_invariants(result: dict[str, Any], fixture: dict[str, Any]) -> dict[str, bool]:
    """Verify lineage, confirmation, evidence, tie ordering, and assignment separation."""
    cases = {case["case_id"]: case for case in result["cases"]}
    lineage = cases["lineage_and_authored_assignment"]
    initial = fixture["cases"][0]["initial_state"]
    checks = {
        "same_logical_candidate_id_across_versions": lineage["final_state"]["candidate_id"] == initial["candidate_id"] and all(
            version["candidate_id"] == initial["candidate_id"] for version in fixture["cases"][0]["initial_state"]["candidate_versions"]
        ),
        "version_ids_distinct_and_monotonic": [version["version_ordinal"] for version in lineage["final_state"]["candidate_versions"]] == [1, 2]
        and len({version["candidate_version_id"] for version in lineage["final_state"]["candidate_versions"]}) == 2,
        "prior_version_provenance_retained": lineage["final_state"]["candidate_versions"][0]["lifecycle_state"] == "replaced"
        and lineage["final_state"]["candidate_versions"][0]["provenance"]["replaced_by_candidate_version_id"] == "candidate-west-01@2"
        and lineage["final_state"]["candidate_versions"][1]["provenance"]["prior_candidate_version_id"] == "candidate-west-01@1",
        "tie_uses_stable_event_id_order": lineage["ordered_event_ids"][:2] == ["evt-10-assign-authored-domain", "evt-20-confirm-v1"]
        and lineage["tie_groups"][0]["event_ids"] == ["evt-10-assign-authored-domain", "evt-20-confirm-v1"],
        "assignment_does_not_confirm_candidate": lineage["after_each_event"][0]["assignment"]["status"] == "assigned"
        and lineage["after_each_event"][0]["active_user_confirmed"] is False,
        "explicit_confirmation_sets_user_confirmed": lineage["after_each_event"][1]["active_user_confirmed"] is True
        and lineage["after_each_event"][1]["active_lifecycle_state"] == "user_confirmed",
        "diagnostic_evidence_survives_confirmation": all(
            step["active_evidence_state"] == "diagnostic_only"
            for step in lineage["after_each_event"] if step["active_user_confirmed"]
        ),
        "replacement_confirmation_does_not_transfer": lineage["after_each_event"][2]["active_candidate_version_id"] == "candidate-west-01@2"
        and lineage["after_each_event"][2]["active_user_confirmed"] is False,
        "stale_version_confirmation_rejected_before_mutation": _check_stale_version_rejection(fixture),
        "absent_and_unresolved_assignment_are_distinct": initial["authored_domain_assignment"]["status"] == "absent"
        and cases["unresolved_assignment"]["final_state"]["authored_domain_assignment"]["status"] == "unresolved",
    }
    _require(all(checks.values()), "one or more lifecycle transition invariants failed")
    return checks


def _manifest_entries() -> list[dict[str, Any]]:
    """Compute byte counts and SHA-256 hashes for the non-cyclic source set."""
    entries = []
    for relative_path in sorted(MANIFEST_PATHS, key=lambda item: item.as_posix()):
        path = REPO_ROOT / relative_path
        data = path.read_bytes()
        entries.append({
            "path": relative_path.as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return entries


def _verify_manifest(manifest: dict[str, Any]) -> None:
    """Recheck manifest coverage, byte counts, and SHA-256 values from disk."""
    expected_paths = sorted(path.as_posix() for path in MANIFEST_PATHS)
    _require(manifest["artifact_count"] == len(expected_paths), "manifest artifact_count does not match its path set")
    entries = manifest["entries"]
    _require([entry["path"] for entry in entries] == expected_paths, "manifest path completeness/order check failed")
    _require(len({entry["path"] for entry in entries}) == len(entries), "manifest has duplicate paths")
    for entry in entries:
        data = (REPO_ROOT / entry["path"]).read_bytes()
        _require(entry["bytes"] == len(data), f"manifest byte count mismatch: {entry['path']}")
        _require(entry["sha256"] == hashlib.sha256(data).hexdigest(), f"manifest SHA-256 mismatch: {entry['path']}")


def main() -> int:
    """Run all bounded checks and write deterministic report and manifest files."""
    fixture = _read_json(FIXTURE_PATH)
    truth = _read_json(TRUTH_PATH)
    _validate_fixture_schema(fixture)
    _validate_truth_schema(truth)
    event_id_checks = _check_event_id_rejections(fixture)

    first_run = _run_probe()
    second_run = _run_probe()
    _require(first_run == second_run, "fresh probe subprocess outputs differ byte-for-byte")
    actual = json.loads(first_run.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    _require(actual.get("artifact_type") == "d6_lifecycle_status_contract_amendment_result_v1", "unexpected probe result type")
    _require(actual["cases"] == truth["cases"], "probe output differs from declared truth")
    invariants = _check_transition_invariants(actual, fixture)

    manifest = {
        "artifact_type": "d6_lifecycle_status_contract_amendment_manifest_v1",
        "hash_algorithm": "sha256",
        "artifact_count": len(MANIFEST_PATHS),
        "entries": _manifest_entries(),
        "manifest_excludes": [
            "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/amendment_v1/artifact_manifest.json",
            "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/amendment_v1/verification_report.json",
        ],
    }
    MANIFEST_PATH.write_bytes(_canonical_bytes(manifest))
    saved_manifest = _read_json(MANIFEST_PATH)
    _require(saved_manifest == manifest, "serialized manifest differs from generated manifest")
    _verify_manifest(saved_manifest)

    git_diff_check, git_scope_audit = _check_git_diff_and_scope()
    scoped_whitespace_check = "PASS"
    _check_scoped_whitespace({})

    report = {
        "artifact_type": "d6_lifecycle_status_contract_amendment_verification_v1",
        "status": "PASS",
        "checks": {
            "strict_json_parse_fixture_and_truth": "PASS",
            "structural_schema_fixture_and_truth": "PASS",
            "deterministic_probe_subprocess_rerun_byte_comparison": "PASS",
            "probe_matches_bounded_truth": "PASS",
            "event_id_rejection_checks": event_id_checks,
            "transition_invariants": invariants,
            "manifest_completeness_byte_counts_sha256": "PASS",
            "truth_matches_report_cases": "PASS",
            "scoped_whitespace_check": scoped_whitespace_check,
            "git_diff_check_relevant_scope": git_diff_check,
            "git_scope_audit": git_scope_audit,
        },
        "probe_stdout_bytes": len(first_run),
        "probe_stdout_sha256": hashlib.sha256(first_run).hexdigest(),
        "manifest_entries_verified": manifest["artifact_count"],
        "manifest_excludes": manifest["manifest_excludes"],
        "cases": actual["cases"],
        "limitations": [
            "Structural schema assertions are local to this bounded fixture; no external JSON Schema package was invoked.",
            "Tie ordering is deterministic serialization only and does not resolve semantic conflicts.",
            "No production readiness or real-IFC behavior is claimed; this verifier covers only the amendment package.",
        ],
        "verification_counts": {
            "event_id_rejection_assertions": len(event_id_checks),
            "fixture_cases": len(fixture["cases"]),
            "invalid_event_id_classes": len(event_id_checks) // 2,
            "manifest_entries_verified": manifest["artifact_count"],
        },
    }
    report_bytes = _canonical_bytes(report)
    _require(report["cases"] == truth["cases"], "generated report cases differ from declared truth")
    _check_scoped_whitespace({REPORT_PATH.relative_to(REPO_ROOT): report_bytes})
    REPORT_PATH.write_bytes(report_bytes)
    _require(_read_json(REPORT_PATH) == report, "serialized report differs from generated report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
