"""Tests for the read-only live Rhino MassPatch acceptance runner."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from .bim.run_live_mass_patch_generation import run_generation


def _source_payload() -> dict[str, object]:
    """Return one compact Rhino-style mesh extraction payload."""
    return {
        "source_mutation_check": True,
        "objects": [
            {
                "id": "rhino-box",
                "layer": "furniture",
                "vertices": [
                    [0.0, 0.0, 0.0],
                    [2.0, 0.0, 0.0],
                    [2.0, 2.0, 0.0],
                    [0.0, 2.0, 0.0],
                    [0.0, 0.0, 1.0],
                    [2.0, 0.0, 1.0],
                    [2.0, 2.0, 1.0],
                    [0.0, 2.0, 1.0],
                ],
                "faces": [
                    [0, 1, 2], [0, 0, 2], [0, 2, 3],
                    [4, 6, 5], [4, 7, 6],
                    [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2],
                    [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0],
                ],
                "is_closed": True,
                "is_manifold": True,
                "linear_tolerance": 0.01,
            }
        ],
    }


def test_live_runner_rejects_missing_source(tmp_path: Path):
    """A live run fails clearly when Rhino extraction is absent."""
    with pytest.raises(FileNotFoundError):
        run_generation(tmp_path / "missing.json", tmp_path / "result.json")


def test_live_runner_writes_generation_result_and_read_only_evidence(tmp_path: Path):
    """A source extraction becomes an auditable backend result."""
    source_path = tmp_path / "source.json"
    result_path = tmp_path / "result.json"
    source_path.write_text(json.dumps(_source_payload()), encoding="utf-8")

    summary = run_generation(source_path, result_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert summary["source_mutation_check"] is True
    assert result["source_mesh_id"] == "rhino-box"
    assert result["patches"]
    assert result["component_reports"]
    assert result["source_mutation_check"] is True
    assert result["patches"][0]["provenance"]["validation_config"]["linear_tolerance"] == 0.01


def test_live_runner_supports_direct_script_execution(tmp_path: Path):
    """The acceptance runner works when launched by its documented CLI path."""
    source_path = tmp_path / "source.json"
    result_path = tmp_path / "result.json"
    source_path.write_text(json.dumps(_source_payload()), encoding="utf-8")
    script_path = Path(__file__).parent / "bim" / "run_live_mass_patch_generation.py"

    completed = subprocess.run(
        [sys.executable, str(script_path), str(source_path), str(result_path)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert result_path.exists()
