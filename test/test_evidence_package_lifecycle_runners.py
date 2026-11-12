"""Actual runners preserve historical publications through package-owned entries."""

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

from features.field_core import _json_value, serialize_evidence_package_output
from features.group_axis_potential_field import build_group_axis_potential_package
from features.group_distance import calculate_group_pair_distances, group_distance_input_fingerprints
from features.group_distance_evidence_package import evaluate_group_distance_package
from features.scene_contract import AnalysisPlane
from scripts.design.group_level import run_group_axis_potential_ifc as potential_runner
from scripts.design.group_level import run_group_axis_potential_ifc_replay as replay_runner
from scripts.design.group_level import run_group_distance_evidence_package as distance_runner
from scripts.design.group_level import run_group_field_hierarchy_ifc as hierarchy_runner
from .test_group_distance import _missing_bundle
from .test_group_distance_evidence_package import _unresolved_repair


ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / "outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z"


def _read(path):
    """Read retained JSON using its historical schema and source order."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path, payload):
    """Write a controlled input artifact for the actual runner."""
    path.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")


def _forbidden_shortcut(*args, **kwargs):
    """Expose a runner that bypasses the public package-owned lifecycle boundary."""
    raise AssertionError("runner bypassed package-owned entry")


def _retained_subset(tmp_path):
    """Keep three real IFC source records in the original producer order without IFC extraction."""
    payload = _read(RETAINED / "envelopes.json")
    payload["envelopes"] = payload["envelopes"][:3]
    source = tmp_path / "retained"
    source.mkdir()
    for name in ("source_manifest.json", "description.json", "view_manifest.json"):
        (source / name).write_bytes((RETAINED / name).read_bytes())
    _write(source / "envelopes.json", payload)
    envelopes = tuple(replay_runner._load_envelope(item) for item in payload["envelopes"])
    return source, envelopes


def test_saved_distance_runner_uses_owned_entry_and_preserves_raw_bytes(tmp_path, monkeypatch):
    """The saved-repair runner must delegate while retaining its no-kernel and historical JSON contract."""
    bundle = _missing_bundle()
    fingerprints = group_distance_input_fingerprints(bundle)
    bundle = replace(bundle, grid=replace(bundle.grid, domain_fingerprint=fingerprints["domain"],
        occupancy_fingerprint=fingerprints["occupancy"]))
    bundle = replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
    input_path, repair_path = tmp_path / "input.json", tmp_path / "repair.json"
    _write(input_path, _json_value(bundle))
    repair = _unresolved_repair(calculate_group_pair_distances(bundle))
    _write(repair_path, repair)
    repair["retained_result_ref"] = {"path": str(repair_path.resolve()),
        "sha256": distance_runner.file_hash(repair_path), "observation_lookup": "observations[*].pair_id"}
    expected = serialize_evidence_package_output(evaluate_group_distance_package(bundle, repaired_result=repair))
    monkeypatch.setattr(distance_runner, "evaluate_group_distance_package", _forbidden_shortcut, raising=False)
    receipt = distance_runner.publish_saved_repair_result(input_path, repair_path, tmp_path / "published")
    assert _read(Path(receipt["output"])) == expected
    assert receipt["distance_recomputed"] is False
    assert receipt["pair_count"] == 3 and receipt["channel_count"] == 6


def test_retained_potential_runner_uses_owned_entry_with_original_source_order(tmp_path, monkeypatch):
    """The replay's published raw channels must remain byte-equivalent to original-order evaluation."""
    source, envelopes = _retained_subset(tmp_path)
    expected = serialize_evidence_package_output(build_group_axis_potential_package().evaluate(envelopes))
    monkeypatch.setattr(replay_runner, "build_group_axis_potential_package", _forbidden_shortcut, raising=False)
    output = replay_runner.run(source, tmp_path / "replayed")
    assert _read(output / "axis_potential_output.json") == expected
    assert _read(output / "package_contract.json")["producer"] == (
        "features.group_axis_potential_field.build_group_axis_potential_package")
    assert _read(output / "package_status.json")["freshness"] == "fresh"


def test_extraction_potential_runner_hands_retained_envelopes_to_owned_entry(tmp_path, monkeypatch):
    """Only the external IFC extraction is substituted; entry evaluation and saved publication are real."""
    retained, envelopes = _retained_subset(tmp_path)
    manifest = _read(retained / "source_manifest.json")
    description = _read(retained / "description.json")
    scene = SimpleNamespace(context=SimpleNamespace(
        analysis_plane=AnalysisPlane.from_dict(manifest["analysis_plane"]), geometry_tolerance=0.001))

    def source_scene(path, *, group_limit=None):
        """Substitute the external IFC extraction with already retained source facts."""
        return scene, manifest, envelopes

    def source_description(value):
        """Reuse the retained description instead of reopening IFC geometry."""
        return description

    def source_envelopes(value, **kwargs):
        """Keep the original retained producer order at the entry boundary."""
        return envelopes

    monkeypatch.setattr(potential_runner, "_build_scene", source_scene)
    monkeypatch.setattr(potential_runner, "describe_group_relations", source_description)
    monkeypatch.setattr(potential_runner, "build_group_trend_alignment_envelopes", source_envelopes)
    monkeypatch.setattr(potential_runner, "build_group_axis_potential_package", _forbidden_shortcut, raising=False)
    source_path = tmp_path / "retained-source-marker"
    source_path.write_bytes(b"retained extraction handoff")
    expected = serialize_evidence_package_output(build_group_axis_potential_package().evaluate(envelopes))
    output = potential_runner.run(source_path, tmp_path / "extracted")
    assert _read(output / "axis_potential_output.json") == expected
    assert _read(output / "package_contract.json")["producer"] == (
        "features.group_axis_potential_field.build_group_axis_potential_package")


def test_hierarchy_runner_uses_owned_entry_without_changing_retained_legacy_channels(tmp_path, monkeypatch):
    """The actual full retained hierarchy runner must delegate and preserve every legacy row."""
    original = _read(RETAINED / "axis_potential_output.json")
    monkeypatch.setattr(hierarchy_runner, "build_group_axis_potential_package", _forbidden_shortcut, raising=False)
    output = hierarchy_runner.run(RETAINED, tmp_path / "hierarchy")
    result = _read(output / "axis_potential_output.json")
    actual = {(row["target"]["identity"], row["channel"]): row for row in result["outputs"]}
    assert all(actual[(row["target"]["identity"], row["channel"])] == row for row in original["outputs"])
    assert result["source_envelopes"] == original["source_envelopes"]
    assert _read(output / "package_status.json")["freshness"] == "fresh"
