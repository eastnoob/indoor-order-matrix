"""Package plane selection stays immutable and separate from computation identity."""

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from features.cache_store import CacheStore
from features.field_core import (
    EvidenceOutputProcessor, EvidencePackage, serialize_evidence_package_output,
    serialize_evidence_processed_output,
)
from features.output_port_cache import bind_raw_port, run_port_processor, save_raw_port
from features.package_analysis_context import (
    AnalysisPlaneCatalog, PackageAnalysisContext, resolve_package_analysis_context,
)
from features.scene_contract import AnalysisPlane
from .test_evidence_package_output import _package_output_function, _source_envelope
from .test_evidence_package_processing import _process
from .test_output_port_cache import _contract


def _plane(identity="plane:p1", *, revision=1, name="call selection"):
    """Provide a contract-only frame without constructing any scene geometry."""
    return AnalysisPlane(name=name, identity=identity, revision=revision, origin=(0, 0, 0),
        basis=((1, 0, 0), (0, 1, 0), (0, 0, 1)))


def _source(plane):
    """Present historical query facts directly to the compatibility resolver."""
    return SimpleNamespace(query=SimpleNamespace(plane=plane))


def _package(*, producer=_package_output_function, context_producer=None,
             processor=None, supports_multiple_planes=False):
    """Preserve the five existing positional constructor arguments in one fixture."""
    return EvidencePackage("contract-package", "contract-output", "1", producer,
        context_producer, output_processor=processor,
        supports_multiple_planes=supports_multiple_planes)


def test_context_detaches_ordered_planes_and_catalog_resolves_explicit_default():
    """Caller mutation cannot change a resolved default or package override."""
    first, second = _plane(), _plane("plane:p2")
    values = [first, second]
    catalog = AnalysisPlaneCatalog(values, first.identity)
    values.reverse()
    assert catalog.planes == (first, second)
    assert catalog.resolve().primary_plane is first
    assert catalog.resolve(package_plane_identity=second.identity).primary_plane is second
    assert catalog.resolve(package_plane_identity=None).primary_plane is first
    context = PackageAnalysisContext([second, first])
    assert context.planes == (second, first)
    with pytest.raises(FrozenInstanceError):
        context.planes = (first,)
    with pytest.raises(FrozenInstanceError):
        catalog.default_plane_identity = second.identity


@pytest.mark.parametrize("planes,default", [
    ((), "plane:p1"), ((_plane(), _plane()), "plane:p1"),
    ((_plane(),), "missing"), ((_plane(),), ""), ((_plane(),), None),
])
def test_catalog_rejects_empty_duplicate_and_dangling_configuration(planes, default):
    """Invalid configuration cannot silently select another available plane."""
    with pytest.raises(ValueError):
        AnalysisPlaneCatalog(planes, default)


@pytest.mark.parametrize("override", ["", "missing", 1])
def test_catalog_rejects_invalid_override(override):
    """An invalid package override cannot inherit the default accidentally."""
    catalog = AnalysisPlaneCatalog((_plane(),), "plane:p1")
    with pytest.raises(ValueError):
        catalog.resolve(package_plane_identity=override)


def test_unique_typed_or_complete_extended_query_plane_is_compatible():
    """Existing complete queries may supply selection without losing their extra facts."""
    plane = _plane()
    mapping = {**plane.to_dict(), "normal": [0, 0, 1], "units": "m"}
    context = resolve_package_analysis_context((_source(plane), _source(mapping),
        _source({**mapping, "name": "renamed display"})))
    assert context.planes == (plane,)
    assert mapping["normal"] == [0, 0, 1]


@pytest.mark.parametrize("missing", ["name", "identity", "revision", "origin", "basis"])
def test_partial_legacy_mapping_cannot_invent_plane_facts(missing):
    """AnalysisPlane defaults cannot manufacture a trusted historical call selection."""
    mapping = _plane().to_dict()
    del mapping[missing]
    with pytest.raises(ValueError, match="complete"):
        resolve_package_analysis_context((_source(mapping),))


@pytest.mark.parametrize("changes", [
    {"normal": None}, {"normal": [1, 0, 0]}, {"units": "cm"}, {"unknown": True},
    {"identity": None}, {"normal": [False, False, True]},
])
def test_query_extensions_are_validated_instead_of_silently_discarded(changes):
    """Malformed or unknown query facts cannot be accepted through compatibility inference."""
    with pytest.raises(ValueError):
        resolve_package_analysis_context((_source({**_plane().to_dict(), **changes}),))


def test_ambiguous_or_absent_source_plane_requires_explicit_context():
    """Conflicting identities or revisions cannot be reduced to one guessed frame."""
    for sources in ((), (_source(None),), (_source(_plane()), _source(_plane("plane:p2"))),
                    (_source(_plane()), _source(_plane(revision=2)))):
        with pytest.raises(ValueError, match="analysis_context"):
            resolve_package_analysis_context(sources)


def test_missing_context_fails_before_the_output_callback():
    """A no-plane contract needs explicit context before any package work can run."""
    calls = []

    def produce(sources):
        """Record any callback entry so rejected admission remains observable."""
        calls.append(sources)
        return _package_output_function(sources)

    with pytest.raises(ValueError, match="analysis_context"):
        _package(producer=produce).evaluate((_source_envelope(),))
    assert calls == []


@pytest.mark.parametrize("capability,permission", [(False, False), (False, True), (True, False), (True, True)])
def test_multiple_planes_require_package_capability_and_call_permission(capability, permission):
    """Only the declared package plus an explicit caller can admit multiple frames."""
    context = PackageAnalysisContext((_plane(), _plane("plane:p2")))
    received = []

    def produce(value):
        """Capture the immutable complete context received by the existing callback API."""
        received.append(value.analysis_context)
        return _package_output_function(value.source_envelopes)

    package = _package(producer=None, context_producer=produce, supports_multiple_planes=capability)
    if capability and permission:
        package.evaluate((_source_envelope(),), analysis_context=context, allow_multiple_planes=permission)
        assert received == [context]
    else:
        with pytest.raises(ValueError, match="multiple planes"):
            package.evaluate((_source_envelope(),), analysis_context=context, allow_multiple_planes=permission)
        assert received == []


@pytest.mark.parametrize("field", ["supports_multiple_planes", "allow_multiple_planes"])
def test_plane_permission_flags_require_booleans(field):
    """Truthy values cannot accidentally grant permission to a multi-plane call."""
    with pytest.raises(TypeError, match="boolean"):
        resolve_package_analysis_context(analysis_context=PackageAnalysisContext((_plane(),)), **{field: 1})


def test_ignored_context_preserves_raw_processed_bytes_and_never_reruns_producer():
    """A selected P1 may process unchanged P2 raw when the processor does not use planes."""
    first = PackageAnalysisContext((_plane(),))
    second = PackageAnalysisContext((_plane("plane:p2"),))
    source = _source_envelope()
    source = replace(source, query=replace(source.query, plane=second.primary_plane.to_dict()))
    calls = []

    def produce(sources):
        """Count producer calls independently from the optional processing stage."""
        calls.append(sources)
        return _package_output_function(sources)

    package = _package(producer=produce, processor=EvidenceOutputProcessor("selection-ignored", "1", _process, {}))
    raw_p1 = package.evaluate((source,), analysis_context=first)
    raw_p2 = package.evaluate((source,), analysis_context=second)
    saved = serialize_evidence_package_output(raw_p1)
    assert serialize_evidence_package_output(raw_p2) == saved
    assert raw_p1.source_envelopes[0].query.plane == source.query.plane
    processed_p1 = package.process_output(raw_p1, package_freshness="fresh", analysis_context=first)
    processed_p2 = package.process_output(raw_p1, package_freshness="fresh", analysis_context=second)
    assert serialize_evidence_processed_output(processed_p1) == serialize_evidence_processed_output(processed_p2)
    assert serialize_evidence_package_output(raw_p1) == saved
    assert len(calls) == 2
    assert "analysis_context" not in json.dumps(saved)


def test_processed_warm_cache_gate_rejects_missing_context_before_storage(tmp_path, monkeypatch):
    """Warm cache reuse must not bypass the same call-context admission as a miss."""
    context = PackageAnalysisContext((_plane(),))
    package = _package(processor=EvidenceOutputProcessor("warm-context", "1", _process, {}))
    raw = package.evaluate((_source_envelope(),), analysis_context=context)
    selected = bind_raw_port(_contract(raw), raw)
    store = CacheStore(tmp_path)
    save_raw_port(store, selected)
    arguments = {"store": store, "current_raw_contract": selected.contract,
                 "requested_raw_parameters": None}
    first = run_port_processor(selected, package, analysis_context=context, **arguments)
    second = run_port_processor(selected, package, analysis_context=context, **arguments)
    assert not first.cache_hit and second.cache_hit

    def forbidden(*args, **kwargs):
        """Reject storage access after admission should already have failed."""
        pytest.fail("missing call context reached storage")

    monkeypatch.setattr(store, "get", forbidden)
    with pytest.raises(ValueError, match="analysis_context"):
        run_port_processor(selected, package, **arguments)


def test_context_contract_imports_under_both_namespaces_without_heavy_engines():
    """Selecting frozen plane facts must not initialize numerical or native engines."""
    root = Path(__file__).resolve().parents[1]
    script = """import importlib, json, sys
sys.path.insert(0, sys.argv[1])
for name in ('features.package_analysis_context', 'order_analyzer.features.package_analysis_context'):
    module = importlib.import_module(name)
    assert module.PackageAnalysisContext and module.AnalysisPlaneCatalog
print(json.dumps(sorted(name for name in sys.modules if name.split('.')[0] in
    {'bpy', 'ifcopenshell', 'octa', 'numpy', 'scipy', 'shapely'})))
"""
    result = subprocess.run([sys.executable, "-c", script, str(root.parent)], cwd=root,
                            check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == []
