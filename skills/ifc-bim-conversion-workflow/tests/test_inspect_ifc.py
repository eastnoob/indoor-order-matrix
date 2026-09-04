"""Tests for the standalone IFC inspection script."""

from __future__ import annotations

import hashlib
import json
import gc
import sys
from builtins import __import__
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import inspect_ifc as inspect_ifc_module
from inspect_ifc import inspect_ifc


@pytest.fixture
def valid_ifc_path() -> Path:
    """Return the repository's repaired IFC fixture."""
    path = Path(__file__).parents[3] / "test" / "output" / "4chair1table-bim-test.ifc"
    if not path.is_file():
        pytest.skip(f"valid IFC fixture is unavailable: {path}")
    return path


def test_inspect_reports_schema_counts_and_unique_guids(valid_ifc_path: Path) -> None:
    """Report the repaired fixture's schema, entity counts, and GUID status."""
    report = inspect_ifc(valid_ifc_path)

    assert report["status"] == "passed"
    assert report["reason"] is None
    assert report["schema"] == "IFC4"
    assert {
        name: report["entity_counts"][name]
        for name in ("IfcProject", "IfcFurniture", "IfcFurnitureType", "IfcGroup")
    } == {
        "IfcProject": 1,
        "IfcFurniture": 5,
        "IfcFurnitureType": 2,
        "IfcGroup": 1,
    }
    assert report["global_id_duplicates"] == []
    json.dumps(report)


def test_inspect_reports_requested_relationship_sections(valid_ifc_path: Path) -> None:
    """Expose the inspection sections needed for import-gating evidence."""
    report = inspect_ifc(valid_ifc_path)

    assert report["type_relations"]
    assert report["spatial_containment"]
    assert report["group_membership"]
    assert report["representations"]
    assert report["units"]
    assert report["source_header_filename"] == ""


def test_inspect_reports_missing_file_without_import_side_effects(tmp_path: Path) -> None:
    """Return an explicit unavailable status for a missing IFC path."""
    report = inspect_ifc(tmp_path / "missing.ifc")

    assert report["status"] == "not_available"
    assert report["path"] == str(tmp_path / "missing.ifc")
    assert report["reason"] == "IFC file does not exist"


def test_inspect_reports_malformed_file_reason(tmp_path: Path) -> None:
    """Return a failed status and actionable reason for an unreadable IFC."""
    path = tmp_path / "malformed.ifc"
    path.write_bytes(b"")

    report = inspect_ifc(path)

    assert report["status"] == "failed"
    assert "Unable to open IFC file" in report["reason"]


def test_inspect_malformed_file_emits_no_unraisable_warning(monkeypatch, tmp_path: Path) -> None:
    """Keep known malformed input isolated from strict unraisable-warning checks."""
    path = tmp_path / "malformed.ifc"
    path.write_bytes(b"")
    unraisable = []

    def capture_unraisable(event) -> None:
        """Capture interpreter-level unraisable exceptions for strict assertions."""
        unraisable.append(event)

    monkeypatch.setattr(sys, "unraisablehook", capture_unraisable)
    report = inspect_ifc(path)
    gc.collect()

    assert report["status"] == "failed"
    assert unraisable == []


def test_inspect_headered_truncated_file_emits_no_unraisable_warning(monkeypatch, tmp_path: Path) -> None:
    """Reject a truncated STEP file before IfcOpenShell sees it."""
    path = tmp_path / "truncated.ifc"
    path.write_bytes(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n")
    unraisable = []

    def capture_unraisable(event) -> None:
        """Capture interpreter-level unraisable exceptions for strict assertions."""
        unraisable.append(event)

    monkeypatch.setattr(sys, "unraisablehook", capture_unraisable)
    report = inspect_ifc(path)
    gc.collect()

    assert report["status"] == "failed"
    assert report["reason"] == (
        "Unable to open IFC file: missing ISO-10303-21 header or "
        "END-ISO-10303-21 marker"
    )
    assert unraisable == []


def test_inspect_reports_post_open_failure_with_stable_shape(monkeypatch, valid_ifc_path: Path) -> None:
    """Report a helper failure after opening with the normal report contract intact."""
    def fail_relations(model):
        """Simulate a failure at the post-open inspection boundary."""
        raise RuntimeError("test: relation scan failed")

    monkeypatch.setattr(inspect_ifc_module, "_relations", fail_relations)
    report = inspect_ifc(valid_ifc_path)

    assert report["status"] == "failed"
    assert report["reason"] == "Unable to inspect opened IFC file: test: relation scan failed"
    assert set(report) == {
        "status",
        "path",
        "reason",
        "schema",
        "validator_version",
        "entity_counts",
        "global_id_duplicates",
        "type_relations",
        "spatial_containment",
        "group_membership",
        "representations",
        "units",
        "source_header_filename",
    }


def test_inspect_reports_missing_ifcopenshell_reason(monkeypatch, tmp_path: Path) -> None:
    """Return an actionable unavailable reason when IfcOpenShell cannot load."""
    path = tmp_path / "model.ifc"
    path.write_text("ISO-10303-21;", encoding="ascii")
    original_import = __import__

    def blocked_import(name, *args, **kwargs):
        """Block only the optional IfcOpenShell import for this test."""
        if name == "ifcopenshell":
            raise ImportError("test: unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocked_import)
    report = inspect_ifc(path)

    assert report["status"] == "not_available"
    assert report["reason"] == "ifcopenshell is not installed"


def test_inspect_preserves_ifc_file_hash(valid_ifc_path: Path) -> None:
    """Confirm inspection leaves the source IFC bytes unchanged."""
    before = hashlib.sha256(valid_ifc_path.read_bytes()).hexdigest()

    inspect_ifc(valid_ifc_path)

    after = hashlib.sha256(valid_ifc_path.read_bytes()).hexdigest()
    assert after == before
