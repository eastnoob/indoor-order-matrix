"""Tests for read-only Bonsai mapping verification."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_bonsai_mapping import collect_bonsai_mapping


SCRIPT = SCRIPTS / "verify_bonsai_mapping.py"


class FakeObject:
    """Represent a Blender object with optional Bonsai mapping properties."""

    def __init__(self, name: str, definition_id: int) -> None:
        """Initialize a fake object with a name and Bonsai definition ID."""
        self.name = name
        self.BIMObjectProperties = type(
            "BIMObjectProperties", (), {"ifc_definition_id": definition_id}
        )()


class FakeAdapter:
    """Expose the read-only scene facts consumed by the verifier."""

    def __init__(
        self,
        *,
        file: object = True,
        ids: tuple[object, ...] = (101, 102),
        schema: object = "IFC4",
        counts: dict[str, object] | None = None,
        failing_method: str | None = None,
        tool_version: object = None,
    ) -> None:
        """Initialize the fake adapter with an optional active file and IDs."""
        self.file = file
        self.ids = ids
        self.schema = schema
        self.counts = {
            "IfcProject": 1,
            "IfcFurniture": 2,
            "IfcFurnitureType": 1,
            "IfcGroup": 1,
        }
        if counts is not None:
            self.counts.update(counts)
        self.failing_method = failing_method
        self.tool_version = tool_version
        self.calls: list[str] = []

    def _check_failure(self, method: str) -> None:
        """Raise the configured adapter error for exception-path tests."""
        if self.failing_method == method:
            raise RuntimeError(f"{method} failed")

    def get_ifc_store_file(self) -> object:
        """Return the active IFC file without changing scene state."""
        self.calls.append("get_ifc_store_file")
        self._check_failure("get_ifc_store_file")
        return self.file

    def get_schema(self, ifc_file: object) -> object:
        """Return the active IFC schema."""
        self.calls.append("get_schema")
        self._check_failure("get_schema")
        return self.schema

    def count_entities(self, ifc_file: object, entity_type: str) -> int:
        """Return deterministic entity counts for the fake IFC file."""
        self.calls.append(f"count:{entity_type}")
        self._check_failure("count_entities")
        if self.counts is not None:
            return self.counts[entity_type]
        return self.counts[entity_type]

    def iter_relevant_objects(self) -> list[FakeObject]:
        """Return objects whose IFC mapping should be checked."""
        self.calls.append("iter_relevant_objects")
        self._check_failure("iter_relevant_objects")
        return [FakeObject(f"IfcFurniture/chair_{index}", value) for index, value in enumerate(self.ids)]

    def get_tool_version(self) -> object:
        """Return the optional Blender/Bonsai version exposed by the adapter."""
        return self.tool_version


def test_named_mesh_without_ifc_store_is_not_bim() -> None:
    """Reject name-based BIM claims when Bonsai has no active IFC file."""
    report = collect_bonsai_mapping(FakeAdapter(file=None))

    assert report["status"] == "failed"
    assert report["ifc_store_file"] is False
    assert report["path"] is None
    assert report["tool_version"] is None
    assert "active IfcStore file" in report["reason"]


def test_bonsai_imported_objects_require_nonzero_definition_ids() -> None:
    """Pass only when every relevant object has a non-zero IFC definition ID."""
    report = collect_bonsai_mapping(FakeAdapter(tool_version="Blender 4.3.2 / Bonsai 0.9"))

    assert report["status"] == "passed"
    assert report["unmapped_objects"] == []
    assert report["schema"] == "IFC4"
    assert report["path"] is None
    assert report["tool_version"] == "Blender 4.3.2 / Bonsai 0.9"
    assert report["entity_counts"] == {
        "IfcProject": 1,
        "IfcFurniture": 2,
        "IfcFurnitureType": 1,
        "IfcGroup": 1,
    }
    json.dumps(report)


def test_walls_only_mapping_passes_generically_and_custom_counts_are_enforced() -> None:
    """Allow generic walls-only verification while honoring explicit entity requirements."""
    adapter = FakeAdapter(
        counts={"IfcFurniture": 0, "IfcFurnitureType": 0, "IfcGroup": 0, "IfcWall": 3}
    )

    generic_report = collect_bonsai_mapping(adapter)
    required_report = collect_bonsai_mapping(adapter, required_entity_counts={"IfcWall": 3})
    unmet_report = collect_bonsai_mapping(adapter, required_entity_counts={"IfcWall": 4})

    assert generic_report["status"] == "passed"
    assert required_report["status"] == "passed"
    assert required_report["entity_counts"]["IfcWall"] == 3
    assert unmet_report["status"] == "failed"
    assert "IfcWall" in unmet_report["reason"]


def test_zero_definition_id_fails_even_when_name_looks_like_ifc() -> None:
    """Treat an IFC-looking object name as insufficient identity evidence."""
    report = collect_bonsai_mapping(FakeAdapter(ids=(101, 0)))

    assert report["status"] == "failed"
    assert report["unmapped_objects"] == [
        {"name": "IfcFurniture/chair_1", "ifc_definition_id": 0}
    ]
    assert "ifc_definition_id" in report["reason"]


def test_active_store_with_empty_relevant_object_evidence_fails() -> None:
    """Require at least one relevant object as evidence for an active store."""
    report = collect_bonsai_mapping(FakeAdapter(ids=()))

    assert report["status"] == "failed"
    assert "no relevant Blender object mapping evidence" in report["reason"]


@pytest.mark.parametrize("definition_id", [True, False, -1, 0, 1.5, "101"])
def test_definition_ids_must_be_positive_integers(definition_id: object) -> None:
    """Reject non-integer, boolean, zero, and negative IFC definition IDs."""
    report = collect_bonsai_mapping(FakeAdapter(ids=(definition_id,)))

    assert report["status"] == "failed"
    assert report["unmapped_objects"] == [
        {"name": "IfcFurniture/chair_0", "ifc_definition_id": definition_id}
    ]
    assert "positive integer" in report["reason"]


@pytest.mark.parametrize(
    ("schema", "counts"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("IFC-custom", {"IfcProject": -1}),
        ("IFC-custom", {"IfcProject": True}),
        ("IFC-custom", {"IfcProject": 1.5}),
    ],
)
def test_schema_and_counts_are_validated_generically(
    schema: object, counts: dict[str, object] | None
) -> None:
    """Reject malformed schema and entity count values without fixture assumptions."""
    report = collect_bonsai_mapping(FakeAdapter(schema=schema, counts=counts))

    assert report["status"] == "failed"
    assert report["reason"]


@pytest.mark.parametrize(
    "failing_method",
    ["get_ifc_store_file", "get_schema", "count_entities", "iter_relevant_objects"],
)
def test_active_store_adapter_errors_fail_with_actionable_reason(failing_method: str) -> None:
    """Treat active-store inspection errors as verification failures."""
    report = collect_bonsai_mapping(FakeAdapter(failing_method=failing_method))

    assert report["status"] == "failed"
    assert failing_method in report["reason"] or "IfcStore" in report["reason"]


def test_missing_adapter_capability_is_not_available() -> None:
    """Distinguish an unusable adapter from a failed BIM mapping."""
    report = collect_bonsai_mapping(object())

    assert report["status"] == "not_available"
    assert report["path"] is None
    assert report["tool_version"] is None
    assert "adapter" in report["reason"].lower()


def test_verifier_only_calls_read_operations() -> None:
    """Keep mutation operators outside the verifier's adapter contract."""
    adapter = FakeAdapter()

    collect_bonsai_mapping(adapter)

    assert set(adapter.calls) <= {
        "get_ifc_store_file",
        "get_schema",
        "count:IfcProject",
        "count:IfcFurniture",
        "count:IfcFurnitureType",
        "count:IfcGroup",
        "iter_relevant_objects",
    }


def test_cli_without_snapshot_returns_actionable_not_available_report() -> None:
    """Make the verifier useful without Blender or an MCP connection."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=True
    )

    report = json.loads(result.stdout)
    assert report["status"] == "not_available"
    assert report["path"] is None
    assert report["tool_version"] is None
    assert "Bonsai adapter" in report["reason"]
    assert "Blender namespace" in report["reason"]
    assert "MCP" not in result.stdout


def test_cli_snapshot_runs_the_same_read_only_mapping_checks(tmp_path: Path) -> None:
    """Verify a JSON adapter snapshot without importing Blender or mutating state."""
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "ifc_store_file": True,
                "schema": "IFC4",
                "tool_version": "Bonsai 0.9 / Blender 4.3.2",
                "entity_counts": {
                    "IfcProject": 1,
                    "IfcFurniture": 2,
                    "IfcFurnitureType": 1,
                    "IfcGroup": 1,
                },
                "mapped_objects": [
                    {"name": "chair_01", "ifc_definition_id": 101},
                    {"name": "chair_02", "ifc_definition_id": 102},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--snapshot", str(snapshot)],
        capture_output=True,
        text=True,
        check=True,
    )

    report = json.loads(result.stdout)
    assert report["status"] == "passed"
    assert report["path"] == str(snapshot)
    assert report["tool_version"] == "Bonsai 0.9 / Blender 4.3.2"
    assert report["mapped_objects"] == [
        {"name": "chair_01", "ifc_definition_id": 101},
        {"name": "chair_02", "ifc_definition_id": 102},
    ]
