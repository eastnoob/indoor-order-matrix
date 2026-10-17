"""Focused integrity, missingness and ordinary-consumer checks for v1 delivery."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ..features.discrete_space_field import load_discrete_space_field


@pytest.fixture
def payloads():
    """Author compact points covering positive overlap, empty, unknown and outside."""
    samples = []
    for i, j, inside, positive, ids, boundary in (
        (0, 0, True, True, ["unresolved"], True),
        (0, 1, True, False, [], False),
        (1, 0, True, False, ["unresolved"], False),
        (1, 1, False, False, [], False),
    ):
        value = True if positive else None if not inside or ids or boundary else False
        samples.append({
            "cell_i": i, "cell_j": j, "x_m": i + 0.5, "y_m": j + 0.5, "world_z_m": 1.6,
            "domain_mask": inside, "qualified_occupied_subset_mask": positive,
            "unresolved_source_ids": ids, "unresolved_source_support_mask": bool(ids),
            "section_boundary_ambiguity_mask": boundary, "occupancy_value": value,
            "known_free_under_qualification": None if value is None else not value,
            "unknown_mask": inside and value is None,
            "status": ("outside_domain" if not inside else "established_occupied" if positive
                       else "unknown" if value is None else "established_empty_under_qualification"),
            "distance_to_domain_boundary_m": 0.5 if inside else None,
            "distance_to_raw_qualified_occupied_subset_m": 0.0 if positive else 1.25 if inside else None,
            "complete_physical_clearance_m": None,
        })
    variant = {"spacing_m": 1.0, "origin_offset_m": [0.0, 0.0], "sample_count": 4,
               "domain_sample_count": 3, "status_counts": dict(Counter(s["status"] for s in samples)),
               "samples": samples}
    shifted = deepcopy(variant)
    shifted["origin_offset_m"] = [0.25, 0.25]
    for sample in shifted["samples"]:
        sample["x_m"] += 0.25
        sample["y_m"] += 0.25
    external_ref = {"path": "unavailable/original.json", "bytes": 10, "sha256": "a" * 64}
    field = {
        "schema": "b3-primary-eye-plane-discrete-field/v1", "status": "design_only_partial",
        "plane_rule": "storey-bound datum plus eye offset", "units": "m", "storey_step": 13,
        "floor_datum": {"value_m": 0.0, "storey_step": 13, "source": "human confirmation",
                        "reference": "floor top surface", "storey_global_id": "fixture-storey"},
        "eye_height_offset_m": 1.6, "primary_plane_world_z_m": 1.6,
        "frame": {"units": "m", "datum_m": 0.0, "cut_height_m": 1.5,
                  "plane": {"name": "world XY", "origin": [0.0, 0.0, 0.0],
                            "basis": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}},
        "scope_binding": {k: "b" * 64 for k in ("source_revision", "frame_id", "request_id", "candidate_identity")},
        "domain_geometry": {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]},
        "sources": [external_ref], "code": [external_ref], "source_integrity": {"source_geometry_rescaled": False},
        "algorithm": {"identity": "original indexed-edge intersection"},
        "channel_contract": {"occupancy_value": "conditional tri-state"},
        "raw_qualified_occupied_area_m2": 1.0, "complete_occupancy_geometry": None,
        "variants": [variant, shifted],
    }
    sections = {"schema": "b3-primary-eye-source-sections/v1", "primary_plane_world_z_m": 1.6,
                "records": [{"id": "qualified", "status": "qualified_closed_section", "error": None},
                            {"id": "unresolved", "status": "invalid_mesh", "error": "Original missing support",
                             "unknown_support_geometry": None, "geometry": external_ref}]}
    return field, sections


def write_package(package: Path, field: dict, sections: dict) -> dict:
    """Serialize fixtures with fresh hashes so semantic mutations reach validation."""
    package.mkdir(exist_ok=True)
    refs = []
    for filename, payload in (("source_sections.json", sections), ("field_samples.json", field)):
        if filename == "field_samples.json":
            field["source_sections"] = refs[0]
        raw = json.dumps(payload, allow_nan=True).encode("utf-8")
        (package / filename).write_bytes(raw)
        refs.append({"path": f"historical/accepted-package/{filename}", "bytes": len(raw),
                     "sha256": hashlib.sha256(raw).hexdigest()})
    manifest = {"schema": "b3-primary-eye-artifacts/v1", "status": "original_status",
                "owner_ruling": "Original bounded acceptance", "artifacts": refs + [
                    {"path": "historical/accepted-package/unvisited.png", "bytes": 500, "sha256": "c" * 64}]}
    (package / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def load(package: Path, **choice) -> dict:
    """Select the fixture's explicit original lattice unless a test specifies one."""
    return load_discrete_space_field(package, **({"spacing_m": 1.0, "origin_offset_m": (0, 0)} | choice))


def test_preserves_states_evidence_and_explicit_variant(tmp_path, payloads):
    """A copied package preserves records and requires no external sources or images."""
    field, sections = payloads
    manifest = write_package(tmp_path, field, sections)
    delivery = load(tmp_path)
    assert delivery["field"] == {k: v for k, v in field.items() if k != "variants"}
    assert delivery["source_sections"] == sections
    assert delivery["artifact_manifest"] == manifest
    assert delivery["variant"] == field["variants"][0]
    samples = delivery["variant"]["samples"]
    assert [s["occupancy_value"] for s in samples] == [True, False, None, None]
    assert samples[0]["unresolved_source_ids"] == ["unresolved"]
    assert samples[0]["section_boundary_ambiguity_mask"] and not samples[0]["unknown_mask"]
    assert samples[2]["unknown_mask"] and not samples[3]["unknown_mask"]
    assert samples[1]["distance_to_raw_qualified_occupied_subset_m"] != samples[1]["distance_to_domain_boundary_m"]
    assert load(tmp_path, origin_offset_m=[0.25, 0.25])["variant"] == field["variants"][1]


def test_plain_python_import_does_not_load_design_modules(tmp_path, payloads):
    """An ordinary Python process consumes the fixture through the public module."""
    write_package(tmp_path, *payloads)
    code = """import sys
from features.discrete_space_field import load_discrete_space_field
d = load_discrete_space_field(sys.argv[1], spacing_m=1, origin_offset_m=(0, 0))
assert len(d['variant']['samples']) == 4
assert not any(n == 'scripts.design' or n.startswith('scripts.design.') for n in sys.modules)
"""
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path)],
                            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("filename", ["artifact_manifest.json", "field_samples.json", "source_sections.json"])
def test_missing_file_is_unavailable(tmp_path, payloads, filename):
    """Missing evidence raises a file error rather than returning empty samples."""
    write_package(tmp_path, *payloads)
    (tmp_path / filename).unlink()
    with pytest.raises(FileNotFoundError):
        load(tmp_path)


@pytest.mark.parametrize("filename", ["field_samples.json", "source_sections.json"])
def test_hash_mismatch_is_rejected(tmp_path, payloads, filename):
    """A tampered sibling cannot pass even if its JSON remains valid."""
    write_package(tmp_path, *payloads)
    with (tmp_path / filename).open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        load(tmp_path)


@pytest.mark.parametrize("choice", [{"spacing_m": 0.5}, {"origin_offset_m": (0.1, 0.1)},
                                  {"spacing_m": True}, {"origin_offset_m": (0,) }])
def test_unavailable_or_invalid_choice_is_rejected(tmp_path, payloads, choice):
    """Choices are exact and never rounded to the nearest accepted lattice."""
    write_package(tmp_path, *payloads)
    with pytest.raises(ValueError):
        load(tmp_path, **choice)


def test_lattice_parameters_have_no_defaults(tmp_path):
    """Both lattice parameters must be provided before file access."""
    with pytest.raises(TypeError):
        load_discrete_space_field(tmp_path)
    with pytest.raises(TypeError):
        load_discrete_space_field(tmp_path, spacing_m=1)


@pytest.mark.parametrize("key,value", [
    ("occupancy_value", False), ("occupancy_value", 1), ("domain_mask", 1),
    ("known_free_under_qualification", True), ("unknown_mask", True),
    ("unresolved_source_support_mask", False), ("unresolved_source_ids", ["missing"]),
    ("world_z_m", 1.5), ("x_m", 0.6), ("x_m", float("nan")),
    ("distance_to_domain_boundary_m", None), ("distance_to_raw_qualified_occupied_subset_m", -1),
    ("complete_physical_clearance_m", 0), ("status", "computed_empty"), ("cell_i", False),
])
def test_rehashed_invalid_sample_is_rejected(tmp_path, payloads, key, value):
    """Fingerprint consistency cannot override state, height or coordinate errors."""
    field, sections = payloads
    field["variants"][0]["samples"][0][key] = value
    write_package(tmp_path, field, sections)
    with pytest.raises(ValueError):
        load(tmp_path)


@pytest.mark.parametrize("case", ["schema", "units", "datum", "section_height", "revision", "code",
                                "count", "domain_count", "states", "duplicate_index", "duplicate_variant",
                                "duplicate_source", "missing_samples", "boundary_empty", "outside_empty",
                                "empty_target_distance", "overflow_json"])
def test_rehashed_invalid_contract_is_rejected(tmp_path, payloads, case):
    """Malformed or promoted packages cannot be mistaken for conditional evidence."""
    field, sections = payloads
    variant = field["variants"][0]
    if case == "schema":
        field["schema"] = "unknown/v2"
    elif case == "units":
        field["units"] = "mm"
    elif case == "datum":
        field["floor_datum"]["value_m"] = 0.1
    elif case == "section_height":
        sections["primary_plane_world_z_m"] = 1.5
    elif case == "revision":
        del field["scope_binding"]["source_revision"]
    elif case == "code":
        field["code"] = []
    elif case == "count":
        variant["sample_count"] = 0
    elif case == "domain_count":
        variant["domain_sample_count"] = 0
    elif case == "states":
        variant["status_counts"] = {}
    elif case == "duplicate_index":
        variant["samples"][1] = deepcopy(variant["samples"][0])
    elif case == "duplicate_variant":
        field["variants"].append(deepcopy(variant))
    elif case == "duplicate_source":
        sections["records"].append(deepcopy(sections["records"][0]))
    elif case == "missing_samples":
        variant["samples"] = []
    elif case == "boundary_empty":
        variant["samples"][1]["section_boundary_ambiguity_mask"] = True
    elif case == "outside_empty":
        variant["samples"][3]["occupancy_value"] = False
    elif case == "empty_target_distance":
        field["raw_qualified_occupied_area_m2"] = 0
    elif case == "overflow_json":
        field["unconsumed_diagnostic"] = float("inf")
    write_package(tmp_path, field, sections)
    with pytest.raises(ValueError):
        load(tmp_path)


def test_boundary_unknown_and_empty_raw_distance_are_supported(tmp_path, payloads):
    """Boundary-only ambiguity and unavailable empty-target distance survive delivery."""
    field, sections = payloads
    field["raw_qualified_occupied_area_m2"] = 0
    for variant in field["variants"]:
        for sample in variant["samples"]:
            sample["distance_to_raw_qualified_occupied_subset_m"] = None
        first = variant["samples"][0]
        first.update(qualified_occupied_subset_mask=False, occupancy_value=None, unknown_mask=True,
                     known_free_under_qualification=None, status="unknown",
                     unresolved_source_ids=[], unresolved_source_support_mask=False)
        variant["status_counts"] = dict(Counter(s["status"] for s in variant["samples"]))
    write_package(tmp_path, field, sections)
    assert load(tmp_path)["variant"] == field["variants"][0]


@pytest.mark.parametrize("case", ["schema", "duplicate", "different_parent", "traversal", "section_ref"])
def test_manifest_binding_is_checked(tmp_path, payloads, case):
    """A sibling hash must also bind to the field's declared source-section package."""
    field, sections = payloads
    manifest = write_package(tmp_path, field, sections)
    if case == "schema":
        manifest["schema"] = "unsupported/v2"
    elif case == "duplicate":
        manifest["artifacts"].append(deepcopy(manifest["artifacts"][0]))
    elif case == "different_parent":
        manifest["artifacts"][0]["path"] = "different/source_sections.json"
    elif case == "traversal":
        manifest["artifacts"][0]["path"] = "../source_sections.json"
    elif case == "section_ref":
        field["source_sections"] = dict(field["source_sections"], sha256="d" * 64)
        raw = json.dumps(field).encode("utf-8")
        (tmp_path / "field_samples.json").write_bytes(raw)
        manifest["artifacts"][1].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    (tmp_path / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        load(tmp_path)
