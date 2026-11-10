"""Concrete saved-package consumption without introducing a new metric."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib
import importlib.util
import json

import pytest

from features.field_core import (
    EvidenceChannelReference, EvidencePackageChannelReference, EvidencePackageDependency,
    FieldResultStatus, serialize_evidence_package_output,
)
from features.group_axis_potential_field import build_group_axis_potential_package
from test.test_evidence_package_freshness import _contract
from test.test_evidence_package_output import _output, _source_envelope


MODULE = "scripts.design.group_level.replay_evidence_package_readback"


def _adapter():
    """Require the concrete adapter before exercising its saved-byte boundary."""
    assert importlib.util.find_spec(MODULE) is not None, "saved-package readback adapter is missing"
    return importlib.import_module(MODULE)


def _saved(tmp_path, *, statuses=(FieldResultStatus.COMPUTED,)):
    """Persist actual core records; no layout or IFC is fabricated by this fixture."""
    source = _source_envelope()
    result = _output(source, channel="path_distance")
    outputs = tuple(replace(
        result.outputs[0],
        target={"kind": "contract_target", "id": f"target-{index}", "identity": f"target-{index}"},
        observation=2.5 if status is not FieldResultStatus.NOT_AVAILABLE else None,
        status=status,
        explanation="bounded source status" if status is not FieldResultStatus.COMPUTED else "",
    ) for index, status in enumerate(statuses))
    result = replace(result, outputs=outputs)
    path = tmp_path / "saved.json"
    data = json.dumps(serialize_evidence_package_output(result), allow_nan=False).encode()
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest(), result


def _consume(tmp_path, *, statuses=(FieldResultStatus.COMPUTED,), current_changes=None,
             unavailable=False, graph=None):
    """Call the production readback with independently constructed contract inputs."""
    adapter = _adapter()
    path, digest, original = _saved(tmp_path, statuses=statuses)
    targets = tuple(item.target["identity"] for item in original.outputs)
    cached = _contract(package_id=original.package_id, target_ids=targets)
    current = None if unavailable else _contract(package_id=original.package_id, target_ids=targets,
                                                 changes=current_changes)
    result = adapter.consume_saved_evidence_package(
        path, expected_sha256=digest, cached_contract=cached, current_contract=current,
        current_source_envelopes=original.source_envelopes,
        selections=tuple((item.target["identity"], item.channel) for item in original.outputs),
        dependency_graph=graph if graph is not None else {
            adapter.PACKAGE_ID: (original.package_id,), original.package_id: (),
        },
    )
    return result, original, path, digest


def test_saved_bytes_become_typed_selected_outputs_in_another_package(tmp_path):
    """Losing a same-named channel on another target breaks faithful readback."""
    result, original, path, digest = _consume(
        tmp_path, statuses=(FieldResultStatus.COMPUTED, FieldResultStatus.PARTIAL))

    assert result.package_id != original.package_id
    assert result.source_envelopes == original.source_envelopes
    assert [(item.target["identity"], item.channel, item.observation, item.status.value)
            for item in result.outputs] == [
        ("target-0", "path_distance", 2.5, "computed"),
        ("target-1", "path_distance", 2.5, "partial"),
    ]
    assert result.outputs[0].scale == original.outputs[0].scale
    assert result.outputs[0].provenance == original.outputs[0].provenance
    assert result.outputs[0].source_ids == original.outputs[0].source_ids
    assert result.outputs[0].derived_from[0].output_identity == original.output_identity
    assert result.dependencies[0].package_freshness == "fresh"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("changes,unavailable,reason", [
    ({"plane": {"origin": [0, 0, 1.6]}}, False, "plane_changed"),
    ({"query": {"scope": "different-domain"}}, False, "query_changed"),
    (None, True, "package_invalid"),
])
def test_noncurrent_contracts_keep_audit_but_expose_no_observation(tmp_path, changes, unavailable, reason):
    """A saved computed status cannot override independently established freshness."""
    result, original, _, _ = _consume(tmp_path, current_changes=changes, unavailable=unavailable)
    output = result.outputs[0]
    assert output.observation is None
    assert output.status is FieldResultStatus.NOT_AVAILABLE
    assert reason in output.explanation
    assert output.provenance == original.outputs[0].provenance
    assert result.source_envelopes == original.source_envelopes


def test_unavailable_and_partial_source_statuses_are_preserved(tmp_path):
    """Freshness cannot turn uncertain source evidence into a computed reading."""
    result, _, _, _ = _consume(tmp_path, statuses=(FieldResultStatus.NOT_AVAILABLE, FieldResultStatus.PARTIAL))
    assert [(item.status.value, item.observation, item.explanation) for item in result.outputs] == [
        ("not_available", None, "bounded source status"),
        ("partial", 2.5, "bounded source status"),
    ]


def test_unknown_domain_status_remains_partial_without_a_numeric_value(tmp_path):
    """The free-space convention carries raw unknown as a partial null observation."""
    adapter = _adapter()
    path, _, original = _saved(tmp_path, statuses=(FieldResultStatus.PARTIAL,))
    unknown = replace(original, outputs=(replace(
        original.outputs[0], observation={"raw_status": "unknown", "value": None},
    ),))
    data = json.dumps(serialize_evidence_package_output(unknown)).encode()
    path.write_bytes(data)
    contract = _contract(package_id=unknown.package_id, target_ids=("target-0",))
    result = adapter.consume_saved_evidence_package(
        path, expected_sha256=hashlib.sha256(data).hexdigest(), cached_contract=contract,
        current_contract=contract, selections=(("target-0", "path_distance"),),
        current_source_envelopes=unknown.source_envelopes,
        dependency_graph={adapter.PACKAGE_ID: (unknown.package_id,), unknown.package_id: ()},
    )
    assert result.outputs[0].status is FieldResultStatus.PARTIAL
    assert dict(result.outputs[0].observation) == {"raw_status": "unknown", "value": None}


def test_unused_stale_dependency_preserves_independent_potential_outputs():
    """An optional dependency cannot gate a pure-axis output that does not read it."""
    envelope = _source_envelope()
    upstream = _output(envelope)
    record = replace(envelope.value["channels"][0], channel="overall_group_axis",
                     observation={"descriptor": {"direction_status": "computed", "angle": 20.0, "strength": 0.5}})
    envelope = replace(envelope, channel_set=("overall_group_axis",), value={"channels": (record,)})
    upstream = replace(upstream, source_envelopes=(envelope,), outputs=(replace(
        upstream.outputs[0], derived_from=(EvidenceChannelReference.from_envelope(envelope, "overall_group_axis"),),
    ),))
    reference = EvidencePackageChannelReference(upstream.package_id, upstream.output_identity,
                                              upstream.outputs[0].target["identity"], upstream.outputs[0].channel)
    dependency = EvidencePackageDependency(upstream.package_id, upstream.output_identity, (reference,),
                                           source_output=upstream, package_freshness="stale")
    package = build_group_axis_potential_package()
    baseline = package.evaluate((envelope,))
    strength = next(item for item in baseline.outputs if item.channel == "resultant_strength")
    assert strength.status is FieldResultStatus.COMPUTED
    assert strength.observation["value"] == pytest.approx(0.5)
    optional = package.evaluate((envelope,), dependencies=(dependency,), dependency_graph={
        package.package_id: (upstream.package_id,), upstream.package_id: (),
    })
    assert optional.outputs == baseline.outputs
    assert optional.source_envelopes == baseline.source_envelopes


def test_sha_mismatch_rejects_bytes_before_decode(tmp_path):
    """Byte-integrity failure must not be mistaken for an unavailable channel."""
    adapter = _adapter()
    path = tmp_path / "untrusted.json"
    path.write_text("not JSON", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        adapter.consume_saved_evidence_package(
            path, expected_sha256="0" * 64, cached_contract=None, current_contract=None,
            current_source_envelopes=None,
            selections=(("target-0", "path_distance"),),
            dependency_graph={adapter.PACKAGE_ID: ()},
        )


@pytest.mark.parametrize("graph", [
    {"evidence-package-channel-readback": ("contract-package",)},
    {"evidence-package-channel-readback": (), "contract-package": ()},
    {"evidence-package-channel-readback": ("contract-package",),
     "contract-package": ("evidence-package-channel-readback",)},
])
def test_incomplete_or_cyclic_explicit_graph_is_rejected(tmp_path, graph):
    """Missing graph nodes or edges must fail before a readback callback runs."""
    with pytest.raises(ValueError, match="graph|cycle|depend"):
        _consume(tmp_path, graph=graph)


def test_missing_selection_and_wrong_contract_package_are_rejected(tmp_path):
    """Explicit selection and contract binding cannot silently choose another input."""
    adapter = _adapter()
    path, digest, original = _saved(tmp_path)
    contract = _contract(package_id=original.package_id, target_ids=("target-0",))
    arguments = dict(expected_sha256=digest, cached_contract=contract, current_contract=contract,
                     current_source_envelopes=original.source_envelopes,
                     selections=(("absent-target", "path_distance"),),
                     dependency_graph={adapter.PACKAGE_ID: (original.package_id,), original.package_id: ()})
    with pytest.raises(ValueError, match="channel|target|reference"):
        adapter.consume_saved_evidence_package(path, **arguments)
    arguments.update(cached_contract=_contract(package_id="wrong-package"),
                     selections=(("target-0", "path_distance"),))
    with pytest.raises(ValueError, match="contract.*package|package.*contract"):
        adapter.consume_saved_evidence_package(path, **arguments)


@pytest.mark.parametrize("change", ["query", "plane", "source", "value", "status", "channel_status", "scope"])
def test_current_source_mismatch_cannot_be_enabled_by_equal_contracts(tmp_path, change):
    """Matching caller contracts cannot authorize a different complete source context."""
    adapter = _adapter()
    path, digest, original = _saved(tmp_path)
    source = original.source_envelopes[0]
    if change == "query":
        current = replace(source, query=replace(source.query, revision="changed-query"))
    elif change == "plane":
        current = replace(source, query=replace(source.query, plane={"origin": [0, 0, 1.6]}))
    elif change == "source":
        current = replace(source, source_ids=(*source.source_ids, "another-source"))
    elif change in {"value", "channel_status"}:
        record = source.value["channels"][0]
        record = replace(record, observation={"same_identity_tampered_value": True}) if change == "value" else replace(
            record, status=FieldResultStatus.INVALID, explanation="current channel became invalid")
        current = replace(source, value={"channels": (record, *source.value["channels"][1:])})
    elif change == "status":
        current = replace(source, raw_status=FieldResultStatus.INVALID)
    else:
        current = replace(source, target={"kind": "contract_target", "id": "other", "identity": "other"})
    assert current.cache_identity == source.cache_identity
    contract = _contract(package_id=original.package_id, target_ids=("target-0",))
    with pytest.raises(ValueError, match="source context"):
        adapter.consume_saved_evidence_package(
            path, expected_sha256=digest, cached_contract=contract, current_contract=contract,
            current_source_envelopes=(current,), selections=(("target-0", "path_distance"),),
            dependency_graph={adapter.PACKAGE_ID: (original.package_id,), original.package_id: ()},
        )


def test_missing_current_sources_redacts_even_matching_contracts(tmp_path):
    """A contract alone cannot establish saved-to-current source correspondence."""
    adapter = _adapter()
    path, digest, original = _saved(tmp_path)
    contract = _contract(package_id=original.package_id, target_ids=("target-0",))
    result = adapter.consume_saved_evidence_package(
        path, expected_sha256=digest, cached_contract=contract, current_contract=contract,
        current_source_envelopes=None, selections=(("target-0", "path_distance"),),
        dependency_graph={adapter.PACKAGE_ID: (original.package_id,), original.package_id: ()},
    )
    assert result.outputs[0].status is FieldResultStatus.NOT_AVAILABLE
    assert result.outputs[0].observation is None
    assert "current_source_context_missing" in result.outputs[0].explanation


def test_current_source_audit_labels_do_not_change_observation_reuse(tmp_path):
    """Historical/current labels and visualization refs carry no numerical input."""
    adapter = _adapter()
    path, digest, original = _saved(tmp_path)
    source = original.source_envelopes[0]
    current = replace(source, provenance={**source.provenance, "source_freshness": "current"},
                      visualization_ref={"audit_only": "current-view"})
    contract = _contract(package_id=original.package_id, target_ids=("target-0",))
    result = adapter.consume_saved_evidence_package(
        path, expected_sha256=digest, cached_contract=contract, current_contract=contract,
        current_source_envelopes=(current,), selections=(("target-0", "path_distance"),),
        dependency_graph={adapter.PACKAGE_ID: (original.package_id,), original.package_id: ()},
    )
    assert result.outputs[0].status is FieldResultStatus.COMPUTED
    assert result.outputs[0].observation == 2.5
    assert result.source_envelopes == original.source_envelopes


def test_unrelated_cached_contract_target_scope_is_rejected(tmp_path):
    """Equal contracts for another scope cannot unlock a matching source snapshot."""
    adapter = _adapter()
    path, digest, original = _saved(tmp_path)
    unrelated = _contract(package_id=original.package_id, target_ids=("a-target-not-in-this-saved-output",))
    with pytest.raises(ValueError, match="target scope"):
        adapter.consume_saved_evidence_package(
            path, expected_sha256=digest, cached_contract=unrelated, current_contract=unrelated,
            current_source_envelopes=original.source_envelopes, selections=(("target-0", "path_distance"),),
            dependency_graph={adapter.PACKAGE_ID: (original.package_id,), original.package_id: ()},
        )
