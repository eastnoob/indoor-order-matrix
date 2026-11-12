"""Bounded real-retained-data checks for the optional pure-distance processed port."""

from dataclasses import replace
from itertools import combinations
import json
import math
import re
import statistics

import pytest

from features.field_core import EvidencePackageChannelReference, FieldResultStatus
from features import group_distance_evidence_package as distance_package
from features.group_distance_evidence_package import (
    build_euclidean_median_proximity_processor, build_group_distance_evidence_package,
)
from scripts.design.group_level import run_group_distance_processed_ifc as trial


@pytest.fixture(scope="module")
def retained_trial():
    """Authenticate and process the full actual IFC-derived scope once."""
    return trial.load_trial()


@pytest.fixture(scope="module")
def small_raw(retained_trial):
    """Retain three actual pair records for inexpensive contract fault injection."""
    _, raw, _ = retained_trial
    selected = tuple(item for item in raw.outputs if item.channel == "euclidean_distance")[:3]
    targets = {item.target["identity"] for item in selected}
    return replace(raw, outputs=selected,
                   source_envelopes=tuple(item for item in raw.source_envelopes if item.target["identity"] in targets))


def _configured(raw):
    """Explicitly bind the actual target set of a retained raw subset."""
    return build_group_distance_evidence_package(output_processor=
        build_euclidean_median_proximity_processor(expected_target_ids=
            [item.target["identity"] for item in raw.outputs if item.channel == "euclidean_distance"]))


def test_full_scope_preserves_raw_metres_and_has_common_median_lineage(retained_trial):
    """All 666 real pairs keep their raw readings and share the same complete ruler."""
    inputs, raw, processed = retained_trial
    rows = trial.build_processed_rows(raw, processed)
    assert raw.package_id == "group-walk-distance"
    assert inputs.package_id == "evidence-package-channel-readback"
    assert len(rows) == len(processed.outputs) == 666
    assert {(row["group_a_id"], row["group_b_id"]) for row in rows} == set(combinations(sorted(inputs.geometries), 2))
    originals = {item.target["identity"]: item for item in raw.outputs if item.channel == "euclidean_distance"}
    selected = {item.target["identity"]: item for item in inputs.outputs}
    median = statistics.median(item.observation["value"] for item in originals.values())
    identity = raw.output_identity
    expected_refs = {EvidencePackageChannelReference(raw.package_id, identity, target, "euclidean_distance")
                     for target in originals}
    for row, output in zip(rows, processed.outputs):
        original = originals[row["pair_id"]]
        assert row["distance_m"] == original.observation["value"] == selected[row["pair_id"]].observation["value"]
        assert row["median_distance_m"] == median
        assert row["proximity"] == output.observation == median / (median + row["distance_m"])
        assert 0 < row["proximity"] <= 1
        assert output.channel == "euclidean_relative_proximity"
        assert output.status is FieldResultStatus.COMPUTED
        assert output.scale.value_range == (0, 1) and "larger is closer" in output.scale.meaning
        assert set(output.derived_from) == expected_refs
        assert row["raw_channel_ref"] == trial.retained._plain_reference(next(
            ref for ref in expected_refs if ref.target_identity == row["pair_id"]))
    ordered = sorted(rows, key=lambda row: row["distance_m"])
    assert all(first["proximity"] >= second["proximity"] for first, second in zip(ordered, ordered[1:]))
    assert raw.output_identity == identity == processed.raw_output_identity
    assert len(raw.outputs) == 1332 and {item.channel for item in raw.outputs} == {"euclidean_distance", "path_distance"}


def test_linear_full_scope_uses_actual_distances_floor_and_complete_lineage(retained_trial):
    """The requested linear recipe preserves all real distances and its common scope."""
    _, raw, reciprocal = retained_trial
    factory = getattr(distance_package, "build_euclidean_linear_proximity_processor", None)
    assert callable(factory), "the explicit linear-floor processor is not implemented"
    originals = {item.target["identity"]: item for item in raw.outputs if item.channel == "euclidean_distance"}
    before = distance_package.serialize_evidence_package_output(raw)
    processor = factory(expected_target_ids=tuple(originals))
    result = build_group_distance_evidence_package(output_processor=processor).process_output(raw, package_freshness="fresh")
    assert result.error_code is None and len(result.outputs) == 666
    d_min = min(item.observation["value"] for item in originals.values())
    d_max = max(item.observation["value"] for item in originals.values())
    expected_refs = {EvidencePackageChannelReference(raw.package_id, raw.output_identity, target, "euclidean_distance")
                     for target in originals}
    readings = []
    for item in result.outputs:
        distance = originals[item.target["identity"]].observation["value"]
        assert item.observation == 0.01 + 0.99 * (d_max - distance) / (d_max - d_min)
        assert item.channel == "euclidean_linear_relative_proximity" and item.status is FieldResultStatus.COMPUTED
        assert item.scale.value_range == (0, 1) and item.scale.scale_id == "euclidean-linear-relative-proximity/1"
        assert item.provenance["minimum_distance_m"] == d_min
        assert item.provenance["maximum_distance_m"] == d_max
        assert item.provenance["floor"] == processor.parameters["floor"] == 0.01
        assert set(item.derived_from) == expected_refs
        readings.append((distance, item.observation))
    readings.sort()
    assert readings[0][1] == 1 and readings[-1][1] == 0.01
    assert all(first[1] >= second[1] for first, second in zip(readings, readings[1:]))
    assert distance_package.serialize_evidence_package_output(raw) == before
    assert result.raw_output_identity == reciprocal.raw_output_identity
    assert result.raw_payload_fingerprint == reciprocal.raw_payload_fingerprint
    assert result.processing_identity != reciprocal.processing_identity


@pytest.mark.parametrize("scope", [[], ["same", "same"], [""], "not-a-sequence", None])
def test_linear_declared_scope_must_be_nonempty_unique_ids(scope):
    """The linear trial rejects malformed declarations before processing."""
    with pytest.raises(ValueError, match="nonempty unique"):
        distance_package.build_euclidean_linear_proximity_processor(expected_target_ids=scope)


@pytest.mark.parametrize("fault", ["missing", "foreign", "empty", "units", "scale-units", "raw-status", "status",
                                 "missing-value", "negative", "boolean"])
def test_linear_unusable_scope_fails_closed(small_raw, fault):
    """Contract fault injection cannot silently shrink or reinterpret the linear scope."""
    scope = [item.target["identity"] for item in small_raw.outputs]
    package = build_group_distance_evidence_package(output_processor=
        distance_package.build_euclidean_linear_proximity_processor(expected_target_ids=scope))
    original = small_raw.outputs[0]
    if fault in {"missing", "empty"}:
        changed = replace(small_raw, outputs=small_raw.outputs[1:] if fault == "missing" else
                          (replace(original, channel="path_distance"),))
    elif fault == "foreign":
        changed = replace(small_raw, outputs=(replace(original, target={**original.target, "identity": "foreign"}),
                                              *small_raw.outputs[1:]))
    else:
        observation = dict(original.observation)
        changes = {}
        if fault == "scale-units":
            changes["scale"] = replace(original.scale, units="mm")
        elif fault == "status":
            changes.update(status=FieldResultStatus.PARTIAL, explanation="contract fault injection")
        else:
            key, value = {"units": ("units", "mm"), "raw-status": ("raw_status", "unknown"),
                          "missing-value": ("value", None), "negative": ("value", -1), "boolean": ("value", True)}[fault]
            observation[key] = value
        changed = replace(small_raw, outputs=(replace(original, observation=observation, **changes), *small_raw.outputs[1:]))
    result = package.process_output(changed, package_freshness="fresh")
    assert result.error_code == "OUTPUT_PROCESSING_FAILED" and result.outputs == ()


def test_linear_equal_values_zero_median_and_zero_span(small_raw):
    """Contract faults prove ties and a zero median work whenever the observed span is positive."""
    package = build_group_distance_evidence_package(output_processor=
        distance_package.build_euclidean_linear_proximity_processor(expected_target_ids=
            [item.target["identity"] for item in small_raw.outputs]))
    for values, expected in (([0, 0, 8], [1, 1, 0.01]), ([0, 4, 8], [1, 0.505, 0.01]),
                             ([0, 0, 1e308], [1, 1, 0.01])):
        changed = replace(small_raw, outputs=tuple(replace(item, observation={**item.observation, "value": value})
                                                  for item, value in zip(small_raw.outputs, values)))
        result = package.process_output(changed, package_freshness="fresh")
        assert result.error_code is None and [item.observation for item in result.outputs] == expected
    for value in (0, 4):
        changed = replace(small_raw, outputs=tuple(replace(item, observation={**item.observation, "value": value})
                                                  for item in small_raw.outputs))
        failed = package.process_output(changed, package_freshness="fresh")
        assert failed.error_code == "OUTPUT_PROCESSING_FAILED" and failed.outputs == ()
        assert "no distance gradient" in failed.explanation


def test_linear_freshness_and_recipe_identity(small_raw):
    """The linear identity binds its declared floor/version while nonfresh inputs stay empty."""
    processor = distance_package.build_euclidean_linear_proximity_processor(expected_target_ids=
        [item.target["identity"] for item in small_raw.outputs])
    package = build_group_distance_evidence_package(output_processor=processor)
    first = package.process_output(small_raw, package_freshness="fresh")
    for freshness in ("stale", "unavailable"):
        failed = package.process_output(small_raw, package_freshness=freshness)
        assert failed.error_code == "OUTPUT_SOURCE_NOT_FRESH" and failed.outputs == ()
    changed_version = replace(package, output_processor=replace(processor, version="contract-fault-version"))
    assert changed_version.process_output(small_raw, package_freshness="fresh").processing_identity != first.processing_identity
    changed_floor = replace(first, parameters={**first.parameters, "floor": 0.02})
    assert changed_floor.processing_identity != first.processing_identity


def test_linear_comparison_renderer_consumes_supplied_values(retained_trial, tmp_path, monkeypatch):
    """Both static views consume supplied outputs and render the same retained reference group."""
    from scripts.design.group_level import run_group_distance_linear_comparison_ifc as comparison
    import matplotlib.pyplot as plt

    inputs, raw, reciprocal = retained_trial
    processor = distance_package.build_euclidean_linear_proximity_processor(expected_target_ids=
        [item.target["identity"] for item in raw.outputs if item.channel == "euclidean_distance"])
    linear = build_group_distance_evidence_package(output_processor=processor).process_output(raw, package_freshness="fresh")
    rows = comparison.build_comparison_rows(raw, reciprocal, linear)
    with pytest.raises(ValueError, match="same raw"):
        comparison.build_comparison_rows(raw, reciprocal, replace(linear, raw_payload_fingerprint="foreign"))
    # Presentation fault injection verifies the handoff; these values are never exported as IFC observations.
    rows = [{**row, "reciprocal_proximity": 0.123456789, "linear_proximity": 0.876543211} for row in rows]
    close = plt.close
    monkeypatch.setattr(plt, "close", lambda *args, **kwargs: None)
    comparison._write_curves(rows, tmp_path)
    curves = plt.gcf()
    assert list(curves.axes[0].lines[0].get_ydata()) == [0.123456789] * 666
    assert list(curves.axes[0].lines[1].get_ydata()) == [0.876543211] * 666
    comparison._write_overview(inputs, rows, tmp_path)
    overview = plt.gcf()
    for axis, value in zip(overview.axes[:2], (0.123456789, 0.876543211)):
        assert sum(patch.get_hatch() == "///" for patch in axis.patches) >= 1
        ordinary = next(patch for patch in axis.patches if patch.get_hatch() is None)
        assert ordinary.get_facecolor() == plt.get_cmap("cividis")(value)
    assert {path.name for path in tmp_path.iterdir()} == {"curves.png", "overview.png", "overview.svg"}
    close(curves)
    close(overview)


@pytest.mark.parametrize("scope", [[], ["same", "same"], [""], "not-a-sequence", None])
def test_declared_scope_must_be_nonempty_unique_ids(scope):
    """Contract fault injection rejects malformed configuration before processing."""
    with pytest.raises(ValueError, match="nonempty unique"):
        build_euclidean_median_proximity_processor(expected_target_ids=scope)


@pytest.mark.parametrize("change", ["missing", "extra", "foreign"])
def test_bad_scope_has_no_numeric_output(small_raw, change):
    """Contract fault injection rejects missing and extra declared Euclidean members."""
    scope = [item.target["identity"] for item in small_raw.outputs]
    scope = scope[:-1] if change == "missing" else [*scope, "foreign"] if change == "extra" else [*scope[:-1], "foreign"]
    package = build_group_distance_evidence_package(output_processor=
        build_euclidean_median_proximity_processor(expected_target_ids=scope))
    result = package.process_output(small_raw, package_freshness="fresh")
    assert result.error_code == "OUTPUT_PROCESSING_FAILED" and result.outputs == ()


@pytest.mark.parametrize("fault", ["units", "scale-units", "raw-status", "status", "missing-value", "negative", "boolean"])
def test_unusable_member_fails_entire_scope(small_raw, fault):
    """Contract fault injection never filters an unusable member out of the median."""
    original = small_raw.outputs[0]
    observation = dict(original.observation)
    changes = {}
    if fault == "units":
        observation["units"] = "mm"
    elif fault == "scale-units":
        changes["scale"] = replace(original.scale, units="mm")
    elif fault == "raw-status":
        observation["raw_status"] = "unknown"
    elif fault == "status":
        changes.update(status=FieldResultStatus.PARTIAL, explanation="contract fault injection")
    else:
        observation["value"] = {"missing-value": None, "negative": -1, "boolean": True}[fault]
    changed = replace(original, observation=observation, **changes)
    injected = replace(small_raw, outputs=(changed, *small_raw.outputs[1:]))
    result = _configured(small_raw).process_output(injected, package_freshness="fresh")
    assert result.error_code == "OUTPUT_PROCESSING_FAILED" and result.outputs == ()


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_contract_fault_rejected_without_any_processed_value(small_raw, value):
    """Contract fault injection excludes nonfinite metres at the immutable raw boundary."""
    original = small_raw.outputs[0]
    # The shared immutable record rejects nonfinite content before a processor can receive it.
    with pytest.raises(ValueError):
        replace(original, observation={**original.observation, "value": value})


def test_duplicate_member_contract_fault_is_rejected(small_raw):
    """Contract fault injection cannot construct a duplicate raw target/channel member."""
    with pytest.raises(ValueError, match="duplicate"):
        replace(small_raw, outputs=(*small_raw.outputs, small_raw.outputs[0]))


def test_large_finite_contract_values_keep_the_reciprocal_ratio(small_raw):
    """Contract fault injection checks finite distances whose naive sum would overflow."""
    injected = replace(small_raw, outputs=tuple(replace(item, observation={**item.observation, "value": 1e308})
                                               for item in small_raw.outputs))
    result = _configured(small_raw).process_output(injected, package_freshness="fresh")
    assert result.error_code is None
    assert all(item.observation == 0.5 for item in result.outputs)


def test_zero_and_median_boundaries_and_nonpositive_scope(small_raw):
    """Contract fault injection proves zero→one, median→half and all-zero refusal."""
    values = [0, 4, 8]
    injected = replace(small_raw, outputs=tuple(replace(item, observation={**item.observation, "value": value})
                                               for item, value in zip(small_raw.outputs, values)))
    result = _configured(small_raw).process_output(injected, package_freshness="fresh")
    assert [item.observation for item in result.outputs] == [1, 0.5, 1 / 3]
    zeros = replace(small_raw, outputs=tuple(replace(item, observation={**item.observation, "value": 0})
                                            for item in small_raw.outputs))
    failed = _configured(small_raw).process_output(zeros, package_freshness="fresh")
    assert failed.error_code == "OUTPUT_PROCESSING_FAILED" and failed.outputs == ()


def test_disabled_and_nonfresh_ports_stay_empty(small_raw):
    """Configured freshness and disabled configuration retain their separate empty errors."""
    disabled = build_group_distance_evidence_package().process_output(small_raw, package_freshness="fresh")
    assert disabled.error_code == "OUTPUT_FUNCTION_NOT_CONFIGURED" and disabled.outputs == ()
    for freshness in ("stale", "unavailable"):
        result = _configured(small_raw).process_output(small_raw, package_freshness=freshness)
        assert result.error_code == "OUTPUT_SOURCE_NOT_FRESH" and result.outputs == ()


def test_processing_identity_binds_recipe_and_raw_content(small_raw):
    """Actual retained records preserve raw identity while processed identity binds value bytes."""
    package = _configured(small_raw)
    first = package.process_output(small_raw, package_freshness="fresh")
    original = small_raw.outputs[0]
    changed = replace(small_raw, outputs=(replace(original, observation={**original.observation,
                      "value": original.observation["value"] * 2}), *small_raw.outputs[1:]))
    second = package.process_output(changed, package_freshness="fresh")
    assert first.raw_output_identity == second.raw_output_identity
    assert first.processing_identity != second.processing_identity
    assert first.raw_payload_fingerprint != second.raw_payload_fingerprint
    with pytest.raises(ValueError, match="belong to the supplied raw producer"):
        trial.build_processed_rows(changed, first)
    with pytest.raises(ValueError, match="belong to the supplied raw producer"):
        trial.build_processed_rows(small_raw, replace(first, package_id="foreign-package"))
    revised = replace(package, output_processor=replace(package.output_processor, version="contract-fault-version"))
    assert revised.process_output(small_raw, package_freshness="fresh").processing_identity != first.processing_identity
    reversed_scope = build_euclidean_median_proximity_processor(expected_target_ids=
        reversed(package.output_processor.parameters["expected_target_ids"]))
    assert reversed_scope.parameters == package.output_processor.parameters


def test_viewer_uses_supplied_processed_values_and_complete_real_unions(retained_trial, tmp_path):
    """A marked presentation fault injection proves the viewer reads supplied values directly."""
    inputs, raw, processed = retained_trial
    rows = trial.build_processed_rows(raw, processed)
    # Contract fault injection is for renderer wiring only and is never exported as scene evidence.
    rows = [{**row, "proximity": 0.123456789} for row in rows]
    trial._write_viewer(inputs, rows, tmp_path)
    document = (tmp_path / "index.html").read_text(encoding="utf-8")
    embedded = json.loads(re.search(r'<script id="rows" type="application/json">(.*?)</script>', document, re.S)[1])
    assert len(embedded) == 666 and all(row["proximity"] == 0.123456789 for row in embedded)
    assert len(re.findall(r'<g data-group=', document)) == 37
    assert len(re.findall(r'<option value=', document)) == 37
    assert 'fill-rule="evenodd"' in document and "source-hatch" in document
    assert "row.proximity.toPrecision(12)" in document and "row.fill" in document
    assert "changing scope can change all values" in document and "retained context only" in document
    assert "there is no self-distance observation" in document
    assert "median /" not in document and "Math.exp" not in document
