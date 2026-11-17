"""Actual runners preserve historical publications through package-owned entries."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test.test_evidence_package_output import _package_context

from features.field_core import _json_value, deserialize_evidence_package_output, serialize_evidence_package_output
from features.group_axis_potential_field import build_group_axis_potential_package
from features.group_distance import calculate_group_pair_distances, group_distance_input_fingerprints
from features.group_distance_evidence_package import evaluate_group_distance_package
from features.cache_store import CacheStore
from features.scene_contract import AnalysisPlane
from scripts.design.group_level import run_group_axis_potential_ifc as potential_runner
from scripts.design.group_level import run_group_axis_potential_ifc_replay as replay_runner
from scripts.design.group_level import run_group_distance_evidence_package as distance_runner
from scripts.design.group_level import run_group_field_hierarchy_ifc as hierarchy_runner
from scripts.design.group_level import run_group_axis_distance_modulation_ifc as modulation_runner
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


def _cli_retained_source(tmp_path, runner, monkeypatch):
    """Keep location checks bounded while retaining the hierarchy's full-scope guard."""
    if runner is hierarchy_runner:
        result = deserialize_evidence_package_output(_read(
            modulation_runner.AXIS_REPLAY / "axis_potential_output.json"))

        def retained_package(envelopes, **kwargs):
            """Return accepted full hierarchy bytes at the package handoff for location checks."""
            assert {item.cache_identity["identity"] for item in envelopes} == {
                item.cache_identity["identity"] for item in result.source_envelopes}
            return {"raw_output": result}

        monkeypatch.setattr(hierarchy_runner, "run_group_axis_potential_package", retained_package)
        return RETAINED
    source, _ = _retained_subset(tmp_path)
    return source


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
    expected = serialize_evidence_package_output(evaluate_group_distance_package(bundle, repaired_result=repair, analysis_context=_package_context()))
    monkeypatch.setattr(distance_runner, "evaluate_group_distance_package", _forbidden_shortcut, raising=False)
    receipt = distance_runner.publish_saved_repair_result(input_path, repair_path, tmp_path / "published",
        analysis_context=_package_context())
    assert _read(Path(receipt["output"])) == expected
    assert receipt["distance_recomputed"] is False
    assert receipt["pair_count"] == 3 and receipt["channel_count"] == 6


def test_retained_potential_runner_uses_owned_entry_with_original_source_order(tmp_path, monkeypatch):
    """The replay's published raw channels must remain byte-equivalent to original-order evaluation."""
    source, envelopes = _retained_subset(tmp_path)
    expected = serialize_evidence_package_output(build_group_axis_potential_package().evaluate(envelopes, analysis_context=_package_context()))
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
    expected = serialize_evidence_package_output(build_group_axis_potential_package().evaluate(envelopes, analysis_context=_package_context()))
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


@pytest.mark.parametrize("runner", [replay_runner, hierarchy_runner])
def test_replay_cli_default_output_is_beside_explicit_model(tmp_path, monkeypatch, capsys, runner):
    """Parsed replay defaults publish under the supplied model's sidecar runs."""
    model = tmp_path / "relocated.ifc"
    source = _cli_retained_source(tmp_path, runner, monkeypatch)
    runner.main(["--retained-run", str(source), "--model-path", str(model)])
    receipt = json.loads(capsys.readouterr().out)
    output = Path(receipt.get("run_dir", receipt.get("output")))
    assert output.is_relative_to(model.with_suffix(".order_analyzer") / "runs")
    assert (output / "axis_potential_output.json").is_file()


@pytest.mark.parametrize("runner", [replay_runner, hierarchy_runner])
def test_replay_cli_explicit_output_contract_is_preserved(tmp_path, monkeypatch, capsys, runner):
    """An explicit parent or exact hierarchy output retains its historical meaning."""
    chosen = tmp_path / "chosen"
    source = _cli_retained_source(tmp_path, runner, monkeypatch)
    runner.main(["--retained-run", str(source), "--output-root", str(chosen)])
    receipt = json.loads(capsys.readouterr().out)
    output = Path(receipt.get("run_dir", receipt.get("output")))
    assert output == chosen if runner is hierarchy_runner else output.parent == chosen
    assert (output / "axis_potential_output.json").is_file()


@pytest.mark.parametrize("runner", [replay_runner, hierarchy_runner])
def test_replay_requires_a_verified_model_or_explicit_location(tmp_path, runner):
    """A retained artifact directory is never guessed to be a model locator."""
    source = tmp_path / "retained"
    source.mkdir()
    _write(source / "source_manifest.json", {
        "source": {"path": str(tmp_path / "missing.ifc"), "sha256": replay_runner.PINNED_SHA256},
        "source_after": {"sha256": replay_runner.PINNED_SHA256},
    })
    with pytest.raises(ValueError, match="model.*temporary.*output"):
        runner.main(["--retained-run", str(source)])
    assert not source.with_suffix(".order_analyzer").exists()


def test_hierarchy_keeps_existing_and_source_containment_refusals(tmp_path):
    """Default location support cannot create an export inside its retained inputs."""
    retained = tmp_path / "retained"
    retained.mkdir()
    with pytest.raises(FileExistsError):
        hierarchy_runner.run(retained, retained)
    with pytest.raises(ValueError, match="outside"):
        hierarchy_runner.run(retained, retained / "new")
    with pytest.raises(ValueError, match="outside"):
        hierarchy_runner.run(retained, model_path=retained / "model.ifc")
    assert list(retained.iterdir()) == []


def test_manifest_model_locator_requires_current_pinned_bytes(tmp_path, monkeypatch):
    """A retained display path authorizes a default location only after byte verification."""
    model = tmp_path / "model.ifc"
    model.write_bytes(b"independently checked source")
    fingerprint = hashlib.sha256(model.read_bytes()).hexdigest()
    monkeypatch.setattr(replay_runner, "PINNED_SHA256", fingerprint)
    manifest = {"source": {"path": str(model), "sha256": fingerprint, "byte_length": model.stat().st_size},
                "source_after": {"sha256": fingerprint}}
    assert replay_runner._verified_model_locator(manifest) == model
    model.write_bytes(b"changed source bytes")
    with pytest.raises(ValueError, match="verified model"):
        replay_runner._verified_model_locator(manifest)


def test_replay_cli_temporary_root_is_session_local(tmp_path, capsys):
    """An explicit temporary session root permits replay without an inferred model."""
    source, _ = _retained_subset(tmp_path)
    temporary = tmp_path / "temporary-session"
    replay_runner.main(["--retained-run", str(source), "--temporary-cache-root", str(temporary)])
    output = Path(json.loads(capsys.readouterr().out)["run_dir"])
    assert output.parent == temporary / "runs"


def test_distance_cli_default_and_explicit_exact_outputs(tmp_path, monkeypatch, capsys):
    """Saved distance publication parses a model default while keeping exact exports."""
    run_package = distance_runner.run_group_distance_package

    def run_contract_package(*args, **kwargs):
        """Supply call selection for this nonspatial fixture at the CLI package handoff."""
        return run_package(*args, **{**kwargs, "analysis_context": _package_context()})

    monkeypatch.setattr(distance_runner, "run_group_distance_package", run_contract_package)
    bundle = _missing_bundle()
    fingerprints = group_distance_input_fingerprints(bundle)
    bundle = replace(bundle, grid=replace(bundle.grid, domain_fingerprint=fingerprints["domain"],
        occupancy_fingerprint=fingerprints["occupancy"]))
    bundle = replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
    input_path, repair_path = tmp_path / "input.json", tmp_path / "repair.json"
    _write(input_path, _json_value(bundle))
    _write(repair_path, _unresolved_repair(calculate_group_pair_distances(bundle)))
    model = tmp_path / "layout.ifc"
    arguments = ["--input-bundle", str(input_path), "--repair-result", str(repair_path),
                 "--model-path", str(model)]
    distance_runner.main(arguments)
    output = Path(json.loads(capsys.readouterr().out)["output"])
    assert output.parent.is_relative_to(model.with_suffix(".order_analyzer") / "runs")
    chosen = tmp_path / "exact-distance"
    distance_runner.main([*arguments, "--output-dir", str(chosen)])
    assert Path(json.loads(capsys.readouterr().out)["output"]).parent == chosen


def test_live_cli_default_and_explicit_parent_outputs(tmp_path, monkeypatch, capsys):
    """Actual parsed live extraction defaults use the input IFC as model anchor."""
    retained, envelopes = _retained_subset(tmp_path)
    manifest, description = _read(retained / "source_manifest.json"), _read(retained / "description.json")
    scene = SimpleNamespace(context=SimpleNamespace(
        analysis_plane=AnalysisPlane.from_dict(manifest["analysis_plane"]), geometry_tolerance=0.001))

    def source_scene(path, *, group_limit=None):
        """Reuse the retained source facts at the external extraction boundary."""
        return scene, manifest, envelopes

    def source_description(value):
        """Reuse the retained group description for the real publication path."""
        return description

    def source_envelopes(value, **kwargs):
        """Retain the small real source set in producer order."""
        return envelopes

    monkeypatch.setattr(potential_runner, "_build_scene", source_scene)
    monkeypatch.setattr(potential_runner, "describe_group_relations", source_description)
    monkeypatch.setattr(potential_runner, "build_group_trend_alignment_envelopes", source_envelopes)
    model = tmp_path / "layout.ifc"
    model.write_bytes(b"retained extraction handoff")
    potential_runner.main(["--ifc", str(model)])
    output = Path(json.loads(capsys.readouterr().out)["run_dir"])
    assert output.parent == model.with_suffix(".order_analyzer") / "runs"
    chosen = tmp_path / "explicit-live"
    potential_runner.main(["--ifc", str(model), "--output-root", str(chosen)])
    assert Path(json.loads(capsys.readouterr().out)["run_dir"]).parent == chosen
    temporary = tmp_path / "temporary-session"
    potential_runner.main(["--ifc", str(model), "--temporary-cache-root", str(temporary)])
    assert Path(json.loads(capsys.readouterr().out)["run_dir"]).parent == temporary / "runs"


def test_modulation_cli_uses_unique_runs_and_run_local_scratch(tmp_path, monkeypatch, capsys):
    """Parsed modulation defaults and exports use unique leaves with local scratch."""
    _, envelopes = _retained_subset(tmp_path)
    scratches = []

    def retained_inputs(*, scratch_directory=None):
        """Keep the actual runner while bounding unrelated retained package loading."""
        scratches.append(scratch_directory)
        return None, envelopes, None, None, None, {}

    def rows(*args):
        """Bypass matrix formatting after the real package-owned entry ran."""
        return []

    def write_outputs(output_dir, *args):
        """Expose the actual allocated publication directory without rendering."""
        (output_dir / "published.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(modulation_runner, "load_modulation_inputs", retained_inputs)
    monkeypatch.setattr(modulation_runner, "_rows", rows)
    monkeypatch.setattr(modulation_runner, "_write_outputs", write_outputs)
    model = tmp_path / "layout.ifc"
    arguments = ["--model-path", str(model)]
    outputs = []
    for _ in range(2):
        modulation_runner.main(arguments)
        outputs.append(Path(json.loads(capsys.readouterr().out)["run_dir"]))
    assert len(set(outputs)) == 2
    assert all(path.parent == model.with_suffix(".order_analyzer") / "runs" for path in outputs)
    chosen = tmp_path / "explicit-modulation"
    modulation_runner.main([*arguments, "--output-root", str(chosen)])
    outputs.append(Path(json.loads(capsys.readouterr().out)["run_dir"]))
    assert outputs[-1].parent == chosen
    temporary = tmp_path / "temporary-session"
    modulation_runner.main(["--temporary-cache-root", str(temporary)])
    outputs.append(Path(json.loads(capsys.readouterr().out)["run_dir"]))
    assert outputs[-1].parent == temporary / "runs"
    assert scratches == [path / "scratch" for path in outputs]


def _journal_cli_case(tmp_path, monkeypatch, kind, failure):
    """Keep real retained inputs and publication paths while bounding package calculation."""
    root = tmp_path / "sidecar"

    def enter_package(*args, **kwargs):
        """Observe the active journal before returning accepted output or raising the exact error."""
        run, = (root / "runs").iterdir()
        assert _read(run / "run.json") == {"schema": "cache-run/v1", "state": "running"}
        if failure is not None:
            raise failure
        return {"raw_output": result}

    if kind == "distance":
        bundle = _missing_bundle()
        fingerprints = group_distance_input_fingerprints(bundle)
        bundle = replace(bundle, grid=replace(bundle.grid, domain_fingerprint=fingerprints["domain"],
            occupancy_fingerprint=fingerprints["occupancy"]))
        bundle = replace(bundle, dependency_fingerprints=group_distance_input_fingerprints(bundle))
        input_path, repair_path = tmp_path / "input.json", tmp_path / "repair.json"
        _write(input_path, _json_value(bundle))
        repair = _unresolved_repair(calculate_group_pair_distances(bundle))
        _write(repair_path, repair)
        result = evaluate_group_distance_package(bundle, repaired_result=repair, analysis_context=_package_context())
        monkeypatch.setattr(distance_runner, "run_group_distance_package", enter_package)
        return distance_runner, ["--input-bundle", str(input_path), "--repair-result", str(repair_path)], root

    if kind == "hierarchy":
        source = RETAINED
        result = (None if failure is not None else deserialize_evidence_package_output(_read(
            modulation_runner.AXIS_REPLAY / "axis_potential_output.json")))
        monkeypatch.setattr(hierarchy_runner, "run_group_axis_potential_package", enter_package)
        return hierarchy_runner, ["--retained-run", str(source)], root

    source, envelopes = _retained_subset(tmp_path)
    result = build_group_axis_potential_package().evaluate(envelopes, analysis_context=_package_context())
    runner = {"live": potential_runner, "replay": replay_runner, "modulation": modulation_runner}[kind]
    monkeypatch.setattr(runner, "run_group_axis_potential_package", enter_package)
    if kind == "replay":
        return runner, ["--retained-run", str(source)], root
    if kind == "live":
        manifest, description = _read(source / "source_manifest.json"), _read(source / "description.json")
        scene = SimpleNamespace(context=SimpleNamespace(
            analysis_plane=AnalysisPlane.from_dict(manifest["analysis_plane"]), geometry_tolerance=0.001))

        def source_scene(path, *, group_limit=None):
            """Reuse the actual retained IFC extraction boundary."""
            return scene, manifest, envelopes

        def source_description(value):
            """Reuse the retained group geometry and description."""
            return description

        def source_envelopes(value, **kwargs):
            """Preserve the retained producer order at the package handoff."""
            return envelopes

        monkeypatch.setattr(runner, "_build_scene", source_scene)
        monkeypatch.setattr(runner, "describe_group_relations", source_description)
        monkeypatch.setattr(runner, "build_group_trend_alignment_envelopes", source_envelopes)
        model = tmp_path / "model.ifc"
        model.write_bytes(b"retained extraction handoff")
        return runner, ["--ifc", str(model)], root

    def retained_inputs(*, scratch_directory=None):
        """Retain real envelopes while bypassing unrelated modulation loading."""
        (scratch_directory / "temporary.json").write_text("{}", encoding="utf-8")
        return None, envelopes, None, None, None, {}

    def rows(*args):
        """Bound formatting after the actual package handoff."""
        return []

    def write_outputs(directory, *args):
        """Leave a real publication artifact to verify closed-run copying."""
        (directory / "published.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(runner, "load_modulation_inputs", retained_inputs)
    monkeypatch.setattr(runner, "_rows", rows)
    monkeypatch.setattr(runner, "_write_outputs", write_outputs)
    return runner, [], root


@pytest.mark.parametrize("kind", ["distance", "live", "replay", "hierarchy", "modulation"])
@pytest.mark.parametrize("failed", [False, True])
def test_cli_terminal_run_journals_allow_closed_artifact_migration(tmp_path, monkeypatch, capsys, kind, failed):
    """All five real CLI paths close their journal and migrate artifacts without active scratch."""
    failure = RuntimeError("publication failure sentinel") if failed else None
    runner, arguments, root = _journal_cli_case(tmp_path, monkeypatch, kind, failure)
    arguments += ["--temporary-cache-root", str(root)]
    if failed:
        with pytest.raises(RuntimeError, match="publication failure sentinel") as observed:
            runner.main(arguments)
        assert observed.value is failure
    else:
        runner.main(arguments)
        capsys.readouterr()
    run, = (root / "runs").iterdir()
    assert _read(run / "run.json") == {
        "schema": "cache-run/v1", "state": "failed" if failed else "complete"}
    before = {path.relative_to(root): path.read_bytes() for path in run.rglob("*")
              if path.is_file() and "scratch" not in path.relative_to(run).parts}
    if not failed:
        assert len(before) > 1
    destination = tmp_path / "migrated"
    report = CacheStore(root).migrate_to(destination, validators={})
    assert report.failed == ()
    assert report.old_directory_retained is True
    assert all((destination / name).read_bytes() == payload for name, payload in before.items())
    assert all((root / name).read_bytes() == payload for name, payload in before.items())
    assert not any(path.name == "scratch" for path in (destination / "runs").rglob("*"))
