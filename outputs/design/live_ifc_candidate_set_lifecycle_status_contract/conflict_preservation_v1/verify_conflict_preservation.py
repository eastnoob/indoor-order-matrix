"""Verify bounded lifecycle conflict-preservation fixtures and evidence integrity."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE.parents[3]
DESIGN_RECORD = Path("docs/project/evidence/d6-space-field-candidate-set-lifecycle-conflict-preservation-v1.md")
INDEPENDENT_REVIEW_PROVENANCE = Path(
    "docs/project/evidence/d6-space-field-candidate-set-lifecycle-independent-review-provenance-v1.md"
)
FIXTURE_PATH = PACKAGE / "fixtures.json"
TRUTH_PATH = PACKAGE / "truth.json"
PROBE_PATH = PACKAGE / "probe.py"
REPORT_PATH = PACKAGE / "verification_report.json"
MANIFEST_PATH = PACKAGE / "artifact_manifest.json"
MANIFEST_INPUTS = [
    DESIGN_RECORD,
    FIXTURE_PATH.relative_to(REPO_ROOT),
    TRUTH_PATH.relative_to(REPO_ROOT),
    PROBE_PATH.relative_to(REPO_ROOT),
    Path(__file__).resolve().relative_to(REPO_ROOT),
]
PACKAGE_PREFIX = PACKAGE.relative_to(REPO_ROOT).as_posix() + "/"
SCOPED_EVIDENCE_PATHS = (DESIGN_RECORD, INDEPENDENT_REVIEW_PROVENANCE)
SCOPED_EVIDENCE_POSIX = {path.as_posix() for path in SCOPED_EVIDENCE_PATHS}
BASELINE_UNRELATED_STATUS_SHA256 = "3918d35e121070bfa39ff2bacc47d21094ff77ce9c10f6faa3aed406a3f03041"
BASELINE_UNRELATED_STATUS_ROWS = 46
EXPECTED_BRANCH = "codex/d6-analysis-domain-layout-handoff"
EXPECTED_HEAD = "fa942a788c08301c9cf1fdec881a40bed1882706"


def _reject_constant(value: str) -> None:
    """Reject non-standard NaN and infinity JSON constants."""
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate object keys instead of silently accepting the last value."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    """Parse UTF-8 JSON strictly, rejecting duplicate keys and non-finite values."""
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def _require(condition: bool, message: str) -> None:
    """Stop verification with a focused assertion message when a check fails."""
    if not condition:
        raise AssertionError(message)


def _canonical_bytes(value: Any) -> bytes:
    """Serialize evidence JSON deterministically with one final newline."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _run_probe() -> bytes:
    """Run the standalone reducer in a fresh process and return its exact output."""
    completed = subprocess.run(
        [sys.executable, "-B", str(PROBE_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    _require(completed.returncode == 0, f"probe failed: {completed.stderr.decode('utf-8', errors='replace')}")
    return completed.stdout


def _projection(result_case: dict[str, Any]) -> dict[str, Any]:
    """Project runtime outcomes onto the explicitly declared truth fields."""
    return {
        "case_id": result_case["case_id"],
        "ordered_event_ids": result_case["ordered_event_ids"],
        "relation_outcomes": [
            {
                key: relation[key]
                for key in (
                    "relation_key",
                    "outcome",
                    "conflict_class",
                    "event_ids",
                    "preserved_event_ids",
                    "effective_event_count",
                    "lexical_winner_event_id",
                    "downstream_promotion",
                )
            }
            for relation in result_case["relation_outcomes"]
        ],
    }


def _check_conflicts_and_provenance(actual: dict[str, Any], fixture: dict[str, Any]) -> dict[str, bool]:
    """Assert unresolved outcomes retain full events and duplicates stay idempotent."""
    fixtures = {case["case_id"]: case for case in fixture["cases"]}
    cases = {case["case_id"]: case for case in actual["cases"]}
    checks: dict[str, bool] = {}
    for case_id in (
        "contradictory_same_key_confirmation",
        "contradictory_same_key_authored_assignment",
        "stale_version_replacement_confirmation",
    ):
        outcome = cases[case_id]["relation_outcomes"][0]
        source_events = {event["event_id"]: event for event in fixtures[case_id]["events"]}
        checks[f"{case_id}_unresolved_no_lexical_winner"] = (
            outcome["outcome"] == "unresolved_conflict"
            and outcome["lexical_winner_event_id"] is None
            and outcome["effective_event_count"] == 0
            and outcome["downstream_promotion"] == "blocked_unresolved_conflict"
        )
        checks[f"{case_id}_all_provenance_records_retained"] = (
            outcome["preserved_event_records"] == [source_events[event_id] for event_id in outcome["event_ids"]]
            and outcome["preserved_event_ids"] == outcome["event_ids"]
            and len(outcome["preserved_event_records"]) == 2
        )

    duplicate = cases["duplicate_identical_event"]["relation_outcomes"][0]
    duplicate_events = fixtures["duplicate_identical_event"]["events"]
    checks["duplicate_identical_events_are_idempotent_and_separate"] = (
        duplicate["outcome"] == "applied_idempotently"
        and duplicate["conflict_class"] is None
        and duplicate["effective_event_count"] == 1
        and duplicate["event_ids"] == [event["event_id"] for event in duplicate_events]
        and duplicate["preserved_event_records"] == duplicate_events
        and len({event["provenance"]["source_record_id"] for event in duplicate["preserved_event_records"]}) == 2
    )
    nonconflicting = cases["non_conflicting_deterministic_tie"]
    checks["non_conflicting_tie_replays_by_event_id"] = (
        nonconflicting["ordered_event_ids"] == ["evt-a-assign-domain-d", "evt-z-confirm-candidate-d"]
        and all(item["outcome"] == "applied" for item in nonconflicting["relation_outcomes"])
        and len(nonconflicting["tie_order_groups"]) == 1
    )
    _require(all(checks.values()), "one or more conflict/provenance assertions failed")
    return checks


def _manifest_entries() -> list[dict[str, Any]]:
    """Compute stable byte counts and SHA-256 values for all non-cyclic inputs."""
    entries = []
    for relative_path in sorted(MANIFEST_INPUTS, key=lambda path: path.as_posix()):
        data = (REPO_ROOT / relative_path).read_bytes()
        entries.append(
            {
                "path": relative_path.as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return entries


def _check_manifest(manifest: dict[str, Any]) -> None:
    """Verify exact manifest coverage, byte counts, and SHA-256 values."""
    expected_paths = sorted(path.as_posix() for path in MANIFEST_INPUTS)
    _require(manifest["artifact_count"] == len(expected_paths), "manifest artifact count differs")
    _require([entry["path"] for entry in manifest["entries"]] == expected_paths, "manifest paths or order differ")
    for entry in manifest["entries"]:
        data = (REPO_ROOT / entry["path"]).read_bytes()
        _require(entry["bytes"] == len(data), f"manifest byte count mismatch: {entry['path']}")
        _require(entry["sha256"] == hashlib.sha256(data).hexdigest(), f"manifest digest mismatch: {entry['path']}")


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a read-only Git inspection from the repository root."""
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def _check_scope() -> dict[str, Any]:
    """Check branch/checkpoint, scoped diffs, and unchanged unrelated Git rows."""
    branch = _git(["branch", "--show-current"])
    head = _git(["rev-parse", "HEAD"])
    _require(branch.returncode == 0 and branch.stdout.strip() == EXPECTED_BRANCH, "current branch changed")
    _require(head.returncode == 0 and head.stdout.strip() == EXPECTED_HEAD, "amendment checkpoint changed")
    scoped_paths = [
        *(path.as_posix() for path in SCOPED_EVIDENCE_PATHS),
        *(path.as_posix() for path in MANIFEST_INPUTS if path not in SCOPED_EVIDENCE_PATHS),
        (PACKAGE.relative_to(REPO_ROOT) / "artifact_manifest.json").as_posix(),
        (PACKAGE.relative_to(REPO_ROOT) / "verification_report.json").as_posix(),
    ]
    for args in (
        ["diff", "--check", "--", *scoped_paths],
        ["diff", "--cached", "--check", "--", *scoped_paths],
    ):
        checked = _git(args)
        _require(checked.returncode == 0, f"scoped git diff check failed: {checked.stderr or checked.stdout}")

    status = _git(["status", "--porcelain=v1", "--untracked-files=all"])
    _require(status.returncode == 0, f"git status failed: {status.stderr}")
    rows = status.stdout.splitlines()
    unrelated = []
    new_scope_rows = []
    tracked_dirty = []
    for row in rows:
        path = row[3:].replace("\\", "/")
        if path in SCOPED_EVIDENCE_POSIX or path.startswith(PACKAGE_PREFIX):
            new_scope_rows.append(path)
            continue
        unrelated.append(row)
        if row[:2] != "??":
            tracked_dirty.append(path)
    unrelated_bytes = ("\n".join(unrelated) + "\n").encode("utf-8")
    unrelated_hash = hashlib.sha256(unrelated_bytes).hexdigest()
    _require(len(unrelated) == BASELINE_UNRELATED_STATUS_ROWS, "unrelated Git status row count changed")
    _require(unrelated_hash == BASELINE_UNRELATED_STATUS_SHA256, "pre-existing unrelated Git status changed")
    _require(not tracked_dirty, "unexpected tracked or staged changes exist")
    return {
        "status": "PASS",
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "unrelated_status_rows_preserved": len(unrelated),
        "unrelated_status_sha256": unrelated_hash,
        "new_scope_status_paths": sorted(new_scope_rows),
        "scoped_git_diff_check": "PASS",
    }


def _check_whitespace(paths: list[Path]) -> int:
    """Reject missing final newlines and trailing whitespace in scoped artifacts."""
    lines_checked = 0
    for path in paths:
        data = path.read_bytes()
        _require(data.endswith(b"\n"), f"missing final newline: {path}")
        for line_number, line in enumerate(data.splitlines(), start=1):
            lines_checked += 1
            _require(not line.endswith((b" ", b"\t")), f"trailing whitespace: {path}:{line_number}")
    return lines_checked


def main() -> int:
    """Run strict input checks, deterministic replay, truth, scope, and manifest checks."""
    fixture = _read_json(FIXTURE_PATH)
    truth = _read_json(TRUTH_PATH)
    _require(fixture["artifact_type"] == "d6_lifecycle_conflict_preservation_fixtures_v1", "unexpected fixture type")
    _require(truth["artifact_type"] == "d6_lifecycle_conflict_preservation_truth_v1", "unexpected truth type")
    first_run = _run_probe()
    second_run = _run_probe()
    _require(first_run == second_run, "probe subprocess output differed on deterministic rerun")
    actual = json.loads(first_run.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    _require(actual["artifact_type"] == "d6_lifecycle_conflict_preservation_probe_v1", "unexpected probe output type")
    expected_cases = truth["cases"]
    actual_cases = [_projection(case) for case in actual["cases"]]
    _require(actual_cases == expected_cases, "probe outcomes do not match declared truth")
    provenance_checks = _check_conflicts_and_provenance(actual, fixture)

    manifest = {
        "artifact_type": "d6_lifecycle_conflict_preservation_manifest_v1",
        "hash_algorithm": "sha256",
        "artifact_count": len(MANIFEST_INPUTS),
        "entries": _manifest_entries(),
        "excludes": [
            "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/conflict_preservation_v1/artifact_manifest.json",
            "outputs/design/live_ifc_candidate_set_lifecycle_status_contract/conflict_preservation_v1/verification_report.json",
        ],
    }
    MANIFEST_PATH.write_bytes(_canonical_bytes(manifest))
    saved_manifest = _read_json(MANIFEST_PATH)
    _require(saved_manifest == manifest, "serialized manifest differs from computed values")
    _check_manifest(saved_manifest)

    scope_audit = _check_scope()
    whitespace_files = [
        REPO_ROOT / DESIGN_RECORD,
        REPO_ROOT / INDEPENDENT_REVIEW_PROVENANCE,
        FIXTURE_PATH,
        TRUTH_PATH,
        PROBE_PATH,
        Path(__file__).resolve(),
        MANIFEST_PATH,
    ]
    whitespace_lines = _check_whitespace(whitespace_files)
    report = {
        "artifact_type": "d6_lifecycle_conflict_preservation_verification_v1",
        "status": "PASS",
        "checks": {
            "strict_json_fixture_truth_and_manifest": "PASS",
            "deterministic_probe_byte_rerun": "PASS",
            "fixture_truth_agreement": "PASS",
            "contradictory_events_unresolved_with_both_records": provenance_checks,
            "duplicate_identical_events_separate_and_idempotent": provenance_checks[
                "duplicate_identical_events_are_idempotent_and_separate"
            ],
            "non_conflicting_tie_deterministic": provenance_checks["non_conflicting_tie_replays_by_event_id"],
            "manifest_bytes_and_sha256": "PASS",
            "scoped_whitespace": {"status": "PASS", "lines_checked": whitespace_lines},
            "git_scope_and_unrelated_file_preservation": scope_audit,
        },
        "probe_stdout_bytes": len(first_run),
        "probe_stdout_sha256": hashlib.sha256(first_run).hexdigest(),
        "manifest_entries_verified": manifest["artifact_count"],
        "cases": actual_cases,
        "limitations": [
            "Synthetic relation scopes define incompatibility for review and do not define production selector semantics.",
            "Event ID ordering provides reproducibility only; this package defines no production conflict-resolution mechanism.",
            "No real-IFC behavior, AnalysisDomain/UI behavior, production status enum, or production integration is claimed.",
        ],
    }
    report_bytes = _canonical_bytes(report)
    REPORT_PATH.write_bytes(report_bytes)
    _check_whitespace([*whitespace_files, REPORT_PATH])
    _require(_read_json(REPORT_PATH) == report, "serialized verification report differs from computed report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
