"""Verify the bounded AnalysisDomain/UI handoff probe and its artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from run_probe import load_json, run


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
TRUTH_PATH = ROOT / "truth.json"


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one artifact."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_load(path: Path) -> dict[str, Any]:
    """Load a JSON object through the probe's duplicate-key guard."""

    return load_json(path)


def candidate_maps(case: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Index candidate result rows by candidate and version identity."""

    by_candidate = {row["candidate_id"]: row for row in case["candidate_states"]}
    by_version = {row["version_id"]: row for row in case["candidate_states"]}
    return by_candidate, by_version


def verify_truth(result: dict[str, Any], truth: dict[str, Any]) -> list[str]:
    """Check every declared fixture expectation and return failure messages."""

    failures: list[str] = []
    truth_cases = truth["cases"]
    result_cases = {case["case_id"]: case for case in result["cases"]}
    if set(result_cases) != set(truth_cases):
        failures.append("result/truth case IDs differ")
        return failures

    for case_id, expected in truth_cases.items():
        case = result_cases[case_id]
        selection = case["selection"]
        for field in ("domain_status", "selected_candidate_id", "active_candidate_ids"):
            if selection[field] != expected[field]:
                failures.append(f"{case_id}: selection.{field}={selection[field]!r}, expected {expected[field]!r}")
        downstream_values = set(case["downstream"].values())
        if downstream_values != {expected["downstream_status"]}:
            failures.append(f"{case_id}: downstream statuses {sorted(downstream_values)!r}")

        by_candidate, by_version = candidate_maps(case)
        actual_visuals = {}
        for key, expected_visual in expected["visual_states"].items():
            row = by_version.get(key) or by_candidate.get(key)
            if row is None:
                failures.append(f"{case_id}: missing candidate key {key}")
                continue
            actual_visuals[key] = row["visual_state"]
            if row["visual_state"] != expected_visual:
                failures.append(f"{case_id}: {key} visual={row['visual_state']!r}, expected {expected_visual!r}")

        if case_id == "replacement_lineage":
            if len(case["lineage"]) != 1:
                failures.append("replacement_lineage: expected one retained lineage relation")
            else:
                relation = case["lineage"][0]
                if relation["from_version_id"].endswith("@v1") is False or relation["to_version_id"].endswith("@v2") is False:
                    failures.append("replacement_lineage: lineage does not connect v1 to v2")
                replacement = by_version.get("candidate:user:replace-room@v2")
                if replacement and (replacement["user_confirmed"] or replacement["accepted"] or replacement["assignment"] != "unassigned"):
                    failures.append("replacement_lineage: replacement inherited confirmation or assignment")

        if case_id in {"authored_auto_conflict", "unresolved_conflict_blocks_promotion"}:
            if not case["conflicts"]:
                failures.append(f"{case_id}: expected retained conflict provenance")
            for conflict in case["conflicts"]:
                if conflict["status"] != "unresolved":
                    failures.append(f"{case_id}: conflict was not unresolved")
                if not conflict.get("provenance"):
                    failures.append(f"{case_id}: conflict provenance missing")
            if selection["selected_candidate_id"] is not None:
                failures.append(f"{case_id}: unresolved conflict selected a winner")

        if case_id == "multi_closed_shell_ambiguous" and selection["selected_candidate_id"] is not None:
            failures.append("multi_closed_shell_ambiguous: ambiguous candidates selected a winner")

        if case_id == "hover_only_highlight":
            before = case.get("pre_hover_projection")
            if before is None:
                failures.append("hover_only_highlight: missing pre-hover projection")
            else:
                if before["selection"] != case["selection"] or before["downstream"] != case["downstream"]:
                    failures.append("hover_only_highlight: hover changed lifecycle or downstream state")
            if case.get("hover_candidate_id") != expected.get("hover_candidate_id"):
                failures.append("hover_only_highlight: hover candidate identity mismatch")

        if case_id == "role_separation":
            role_map = {role["kind"]: role for role in case["roles"]}
            for role_kind, role_expectation in expected.get("role_expectations", {}).items():
                actual = role_map.get(role_kind)
                if actual is None:
                    failures.append(f"role_separation: missing role {role_kind}")
                    continue
                for field, value in role_expectation.items():
                    if actual.get(field) != value:
                        failures.append(f"role_separation: {role_kind}.{field}={actual.get(field)!r}")

    return failures


def compare_bytes(primary: Path, reproduction: Path) -> dict[str, Any]:
    """Compare the deterministic output bytes from two probe runs."""

    comparisons = {}
    for name in ("result.json", "handoff.svg"):
        left = (primary / name).read_bytes()
        right = (reproduction / name).read_bytes()
        comparisons[name] = {
            "byte_equal": left == right,
            "primary_bytes": len(left),
            "reproduction_bytes": len(right),
            "primary_sha256": sha256(primary / name),
            "reproduction_sha256": sha256(reproduction / name),
        }
    return comparisons


def scope_audit(baseline_status_path: Path | None) -> dict[str, Any]:
    """Audit that the pre-existing untracked paths remain present."""

    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    current_untracked = sorted(line[3:] for line in status if line.startswith("?? "))
    baseline: list[str] = []
    if baseline_status_path is not None:
        baseline_payload = strict_load(baseline_status_path)
        baseline = sorted(baseline_payload["untracked"])
    missing = sorted(set(baseline) - set(current_untracked))
    forbidden_prefixes = ("features/", "adapters/", "test/", "tests/", "analyzer.py", "__init__.py", "pixi.toml", "pixi.lock")
    forbidden_status_rows = [line for line in status if line[3:] .replace("\\", "/").startswith(forbidden_prefixes)]
    return {
        "baseline_untracked_count": len(baseline),
        "current_untracked_count": len(current_untracked),
        "baseline_untracked_preserved": not missing,
        "missing_baseline_untracked": missing,
        "forbidden_scope_status_rows": forbidden_status_rows,
        "allowed_new_paths": sorted(set(current_untracked) - set(baseline)),
        "production_adapter_used": False,
        "real_ifc_status": "not_verified",
    }


def manifest_entry(path: Path, role: str, command: str, exit_code: int, provenance: dict[str, Any]) -> dict[str, Any]:
    """Create one manifest entry with bytes and SHA-256."""

    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "role": role,
        "producer_command": command,
        "exit_code": exit_code,
        "provenance": provenance,
    }


def write_manifest(
    output_dir: Path,
    verification_report_path: Path,
    scope_audit_path: Path,
    commands: list[dict[str, Any]],
) -> None:
    """Write a non-cyclic artifact manifest for the design evidence package."""

    provenance = {
        "kind": "bounded_design_evidence",
        "generated_on": "2026-10-06",
        "production_adapter_used": False,
        "real_ifc_status": "not_verified",
        "source_identity": "synthetic fixtures only; no IFC geometry adapter",
    }
    compile_command = "pixi run python -B -m py_compile scripts/design/analysis_domain_ui/run_probe.py scripts/design/analysis_domain_ui/verify_probe.py"
    primary_command = "pixi run python -B scripts/design/analysis_domain_ui/run_probe.py --fixtures scripts/design/analysis_domain_ui/fixtures.json --output scripts/design/analysis_domain_ui/artifacts/run_001"
    reproduction_command = "pixi run python -B scripts/design/analysis_domain_ui/run_probe.py --fixtures scripts/design/analysis_domain_ui/fixtures.json --output scripts/design/analysis_domain_ui/artifacts/run_002"
    verify_command = "pixi run python -B scripts/design/analysis_domain_ui/verify_probe.py --primary scripts/design/analysis_domain_ui/artifacts/run_001 --reproduction scripts/design/analysis_domain_ui/artifacts/run_002 --baseline-status C:/Users/tianf/AppData/Local/Temp/d6_ui_baseline_git.json --report scripts/design/analysis_domain_ui/artifacts/run_001/verification_report.json --scope-audit scripts/design/analysis_domain_ui/artifacts/run_001/scope_audit.json --manifest scripts/design/analysis_domain_ui/artifacts/run_001/artifact_manifest.json"
    files = [
        (ROOT / "fixtures.json", "fixture", primary_command),
        (ROOT / "truth.json", "truth", verify_command),
        (ROOT / "run_probe.py", "probe", compile_command),
        (ROOT / "verify_probe.py", "verifier", compile_command),
        (output_dir / "result.json", "result", primary_command),
        (output_dir / "handoff.svg", "visualization", primary_command),
        (output_dir.parent / "run_002" / "result.json", "reproduction_result", reproduction_command),
        (output_dir.parent / "run_002" / "handoff.svg", "reproduction_visualization", reproduction_command),
        (verification_report_path, "verification_report", verify_command),
        (scope_audit_path, "git_scope_audit", verify_command),
        (REPO_ROOT / "docs/project/evidence/d6-analysis-domain-ui-handoff-design.md", "design_record", "design evidence authoring step"),
    ]
    entries = [manifest_entry(path, role, command, 0, provenance) for path, role, command in files]
    manifest = {
        "schema_version": "d6.analysis_domain_ui.artifact_manifest.v1",
        "manifest_excludes_itself": True,
        "provenance": provenance,
        "commands": commands,
        "artifacts": entries,
    }
    output_path = output_dir / "artifact_manifest.json"
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    """Run fresh verification and return non-zero when any assertion fails."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--reproduction", type=Path, required=True)
    parser.add_argument("--baseline-status", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--scope-audit", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    args.primary = args.primary.resolve()
    args.reproduction = args.reproduction.resolve()
    args.report = args.report.resolve()
    args.scope_audit = args.scope_audit.resolve()
    args.manifest = args.manifest.resolve()
    if args.baseline_status is not None:
        args.baseline_status = args.baseline_status.resolve()

    truth = strict_load(TRUTH_PATH)
    primary_result = strict_load(args.primary / "result.json")
    reproduction_result = strict_load(args.reproduction / "result.json")
    failures = verify_truth(primary_result, truth)
    if primary_result != reproduction_result:
        failures.append("primary and reproduction result JSON differ semantically")
    comparisons = compare_bytes(args.primary, args.reproduction)
    for name, comparison in comparisons.items():
        if not comparison["byte_equal"]:
            failures.append(f"{name} differs byte-for-byte")
    try:
        ET.parse(args.primary / "handoff.svg")
    except ET.ParseError as exc:
        failures.append(f"handoff.svg is not well-formed XML: {exc}")
    svg_text = (args.primary / "handoff.svg").read_text(encoding="utf-8")
    required_labels = [
        "automatic singleton/provisional",
        "active green",
        "ambiguous or unassigned",
        "conflict: promotion disabled",
        "hover-only focus",
        "not_available",
    ]
    for label in required_labels:
        if label not in svg_text:
            failures.append(f"handoff.svg missing label: {label}")

    audit = scope_audit(args.baseline_status)
    if not audit["baseline_untracked_preserved"]:
        failures.append("baseline untracked paths were not preserved")
    if audit["forbidden_scope_status_rows"]:
        failures.append("forbidden production scope has Git status rows")

    report = {
        "schema_version": "d6.analysis_domain_ui.verification_report.v1",
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "truth_cases": len(truth["cases"]),
        "byte_comparisons": comparisons,
        "svg_xml_parse": "pass" if not any("well-formed XML" in failure for failure in failures) else "fail",
        "scope_audit_path": args.scope_audit.relative_to(REPO_ROOT).as_posix(),
        "real_ifc_status": "not_verified",
        "production_adapter_used": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    with args.scope_audit.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    commands = [
        {"command": "pixi run python -B -m py_compile scripts/design/analysis_domain_ui/run_probe.py scripts/design/analysis_domain_ui/verify_probe.py", "exit_code": 0},
        {"command": "pixi run python -B scripts/design/analysis_domain_ui/run_probe.py --fixtures scripts/design/analysis_domain_ui/fixtures.json --output scripts/design/analysis_domain_ui/artifacts/run_001", "exit_code": 0},
        {"command": "pixi run python -B scripts/design/analysis_domain_ui/run_probe.py --fixtures scripts/design/analysis_domain_ui/fixtures.json --output scripts/design/analysis_domain_ui/artifacts/run_002", "exit_code": 0},
        {"command": "pixi run python -B scripts/design/analysis_domain_ui/verify_probe.py --primary scripts/design/analysis_domain_ui/artifacts/run_001 --reproduction scripts/design/analysis_domain_ui/artifacts/run_002 --baseline-status C:/Users/tianf/AppData/Local/Temp/d6_ui_baseline_git.json --report scripts/design/analysis_domain_ui/artifacts/run_001/verification_report.json --scope-audit scripts/design/analysis_domain_ui/artifacts/run_001/scope_audit.json --manifest scripts/design/analysis_domain_ui/artifacts/run_001/artifact_manifest.json", "exit_code": 0 if not failures else 1},
    ]
    write_manifest(args.primary, args.report, args.scope_audit, commands)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
