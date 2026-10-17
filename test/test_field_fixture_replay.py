"""Red subprocess contract tests for deterministic US3 fixture replay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPLAY_SCRIPT = PROJECT_ROOT / "scripts" / "design" / "group_level" / "run_field_fixture_replay.py"
FIXTURE_PATH = PROJECT_ROOT / "scripts" / "design" / "group_level" / "self_description_competition_fixtures.json"

EXPECTED_PERTURBATIONS = {
    "identifier_order",
    "translation",
    "supported_rotation",
    "opening_mutation",
    "missing_domain",
}
EXPECTED_BLOCKED_CASES = {
    "invalid_geometry_to_missing",
    "rotated_wall_representation",
    "section_vs_whole_height",
}


def _run_replay(output_path: Path) -> dict:
    """Run the planned replay script and return its JSON artifact."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPLAY_SCRIPT),
            "--fixtures",
            str(FIXTURE_PATH),
            "--output",
            str(output_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"fixture replay failed with exit {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def _canonical_bytes(report: dict) -> bytes:
    """Encode the replay's canonical observations deterministically."""
    return json.dumps(
        report["canonical_observations"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def test_fixture_replay_is_deterministic_and_design_only(tmp_path):
    """Two subprocess runs preserve eight fixtures and byte-identical evidence."""
    first = _run_replay(tmp_path / "replay-1.json")
    second = _run_replay(tmp_path / "replay-2.json")

    assert first["fixture_count"] == 8
    assert second["fixture_count"] == 8
    assert first["design_only"] is True
    assert first["formula_scope"] == "probe_only_not_production"
    assert second["formula_scope"] == "probe_only_not_production"
    assert _canonical_bytes(first) == _canonical_bytes(second)
    assert hashlib.sha256(_canonical_bytes(first)).hexdigest() == first["canonical_sha256"]
    assert first["canonical_sha256"] == second["canonical_sha256"]
    assert first["canonical_bytes"] == second["canonical_bytes"]


def test_fixture_replay_retains_status_provenance_and_channel_isolation(tmp_path):
    """Replay reports preserve audit metadata and the eight channel assertions."""
    report = _run_replay(tmp_path / "replay.json")

    assert len(report["fixtures"]) == 8
    assert report["status_matrix"]
    assert report["provenance"]
    assert report["channel_isolation"]["passed"] == 8
    assert report["channel_isolation"]["design_only"] is True
    assert EXPECTED_PERTURBATIONS <= {
        item["name"] for item in report["perturbations"] if item["passed"]
    }
    assert all(item["formula_scope"] == "probe_only_not_production"
               for item in report["perturbations"])


def test_fixture_replay_keeps_blocked_cases_explicitly_design_only(tmp_path):
    """Unsupported S3 transitions remain blocked rather than being inferred."""
    report = _run_replay(tmp_path / "replay.json")

    blocked = {item["name"]: item for item in report["blocked_cases"]}
    assert EXPECTED_BLOCKED_CASES <= blocked.keys()
    for name in EXPECTED_BLOCKED_CASES:
        assert blocked[name]["blocked"] is True
        assert blocked[name]["design_only"] is True
        assert blocked[name]["formula_scope"] == "probe_only_not_production"
