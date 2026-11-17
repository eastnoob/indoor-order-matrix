"""Immutable semantic publications stored through the shared CacheStore."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Literal

from .cache_paths import CacheAddress
from .cache_store import (
    CacheStore, CacheValidationContext, CacheValidationError,
    _reject_constant, _unique_object,
)
from .evidence_package_parameters import (
    ParameterImpact, ParameterSnapshot, compare_parameter_snapshots,
)
from .field_core import (
    EvidenceOutputProcessor, EvidencePackage, EvidencePackageOutput, EvidenceProcessedOutput,
    _canonical_json, _freeze, _json_value, _snapshot_record, _validate_snapshot_json,
    deserialize_evidence_package_output, deserialize_evidence_processed_output,
    fingerprint_evidence_dependency, serialize_evidence_package_output,
    serialize_evidence_processed_output,
)
from .package_analysis_context import resolve_package_analysis_context


def _nonblank(value, name):
    """Require an explicit identifier without silently normalizing identity inputs."""
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _digest(value, name):
    """Require the lowercase SHA-256 representation used by payload references."""
    if (type(value) is not str or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"{name} must be a SHA-256 digest")


@dataclass(frozen=True, slots=True)
class OutputPortRef:
    """Address one immutable semantic publication and its exact selected bytes."""

    source_fingerprint: str
    package_id: str
    output_port: str
    identity: str
    layer: str
    payload_fingerprint: str
    processing_identity: str | None = None

    def __post_init__(self):
        """Reject unsafe addresses and ambiguous raw/processed reference bindings."""
        self.address
        _digest(self.payload_fingerprint, "payload_fingerprint")
        if self.layer == "processed":
            _nonblank(self.processing_identity, "processing_identity")
        elif self.processing_identity is not None:
            raise ValueError("raw references cannot carry processing_identity")

    @property
    def address(self) -> CacheAddress:
        """Preserve all five address fields for storage, dependencies and deletion."""
        return CacheAddress(self.source_fingerprint, self.package_id,
                            self.output_port, self.layer, self.identity)


@dataclass(frozen=True, slots=True)
class OutputPortContract:
    """Declare only inputs that can affect this semantic output."""

    package_id: str
    output_port: str
    source_fingerprint: str
    input_fingerprints: Mapping[str, str]
    parameter_projection: Mapping[str, Any]
    upstream_refs: tuple[OutputPortRef, ...]
    algorithm_version: str
    schema_version: str
    addresses: tuple[tuple[str, str], ...]

    def __post_init__(self):
        """Detach identity inputs and require an exact declared publication scope."""
        CacheAddress(self.source_fingerprint, self.package_id, self.output_port, "raw", "contract")
        for name in ("algorithm_version", "schema_version"):
            _nonblank(getattr(self, name), name)
        if not isinstance(self.input_fingerprints, Mapping):
            raise TypeError("input_fingerprints must be a mapping")
        for name, value in self.input_fingerprints.items():
            _nonblank(name, "input name")
            _nonblank(value, "input fingerprint")
        projection = self.parameter_projection
        if (not isinstance(projection, Mapping) or set(projection) != {
                "schema", "selected_names", "values", "value_contracts"}):
            raise ValueError("parameter projection fields do not match")
        _nonblank(projection["schema"], "parameter projection schema")
        names = projection["selected_names"]
        if not isinstance(names, (list, tuple)):
            raise TypeError("selected_names must be an array")
        for name in names:
            _nonblank(name, "selected parameter")
        if list(names) != sorted(set(names)):
            raise ValueError("selected_names must be sorted and distinct")
        values, contracts = projection["values"], projection["value_contracts"]
        if not isinstance(values, Mapping) or not isinstance(contracts, Mapping):
            raise TypeError("projected values and value_contracts must be mappings")
        if set(values) != set(contracts) or not set(values) <= set(names):
            raise ValueError("parameter projection value names do not match")
        refs = tuple(self.upstream_refs)
        if any(not isinstance(ref, OutputPortRef) for ref in refs):
            raise TypeError("upstream_refs must contain OutputPortRef values")
        if len({ref.address for ref in refs}) != len(refs):
            raise ValueError("duplicate upstream refs")
        addresses = []
        for pair in self.addresses:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise ValueError("addresses must contain target/channel pairs")
            for value in pair:
                _nonblank(value, "target/channel address")
            addresses.append(tuple(pair))
        if not addresses or len(set(addresses)) != len(addresses):
            raise ValueError("addresses must be nonempty and cannot duplicate target/channel pairs")
        object.__setattr__(self, "input_fingerprints", _freeze(self.input_fingerprints))
        object.__setattr__(self, "parameter_projection", _freeze(projection))
        object.__setattr__(self, "upstream_refs", tuple(sorted(refs, key=_canonical_json)))
        object.__setattr__(self, "addresses", tuple(sorted(addresses)))

    @property
    def identity(self) -> str:
        """Hash declared computation inputs while excluding full parameter audit."""
        return fingerprint_evidence_dependency(self)

    @property
    def target_ids(self) -> tuple[str, ...]:
        """Return the distinct target identifiers represented by exact addresses."""
        return tuple(sorted({target for target, _ in self.addresses}))

    @property
    def channels(self) -> tuple[str, ...]:
        """Return the distinct selected channels without assuming a Cartesian scope."""
        return tuple(sorted({channel for _, channel in self.addresses}))


def _validated_snapshot(snapshot):
    """Validate complete calculated metadata through A without applying defaults."""
    if snapshot is None:
        return None
    if not isinstance(snapshot, ParameterSnapshot):
        raise TypeError("parameter_snapshot must be a ParameterSnapshot or None")
    return ParameterSnapshot.from_json(snapshot.to_json())


def _validate_projection(contract, snapshot):
    """Bind selected recompute declarations and values to their package-owned audit."""
    projection = contract.parameter_projection
    names = projection["selected_names"]
    if snapshot is None:
        if names:
            raise ValueError("selected parameters require a parameter_snapshot")
        return
    if snapshot.package_id != contract.package_id:
        raise ValueError("parameter snapshot belongs to a foreign package")
    if not set(names) <= set(snapshot.effective_parameters):
        raise ValueError("unknown selected parameter")
    recompute = {name for name in names if snapshot.parameter_impacts[name]
                 == ParameterImpact.RECOMPUTE_REQUIRED.value}
    expected = {"values": {name: snapshot.effective_parameters[name] for name in recompute},
                "value_contracts": {name: snapshot.parameter_value_contracts[name] for name in recompute}}
    actual = {key: projection[key] for key in expected}
    if fingerprint_evidence_dependency(actual) != fingerprint_evidence_dependency(expected):
        raise ValueError("parameter projection does not match selected recompute values/contracts")


@dataclass(frozen=True, slots=True)
class RawPortPublication:
    """Keep a package-projected typed view beside its semantic contract."""

    contract: OutputPortContract
    raw_view: EvidencePackageOutput
    parameter_snapshot: ParameterSnapshot | None = None

    def __post_init__(self):
        """Require exact package, scope and historical parameter projection binding."""
        if not isinstance(self.contract, OutputPortContract):
            raise TypeError("contract must be an OutputPortContract")
        if not isinstance(self.raw_view, EvidencePackageOutput):
            raise TypeError("raw_view must be an EvidencePackageOutput")
        if self.raw_view.package_id != self.contract.package_id:
            raise ValueError("raw view belongs to a foreign package")
        addresses = tuple((item.target["identity"], item.channel) for item in self.raw_view.outputs)
        if addresses != self.contract.addresses:
            raise ValueError("selected target/channel addresses do not match contract")
        snapshot = _validated_snapshot(self.parameter_snapshot)
        _validate_projection(self.contract, snapshot)
        object.__setattr__(self, "parameter_snapshot", snapshot)

    @property
    def ref(self) -> OutputPortRef:
        """Expose the input identity separately from the selected payload digest."""
        return raw_port_ref(self)


@dataclass(frozen=True, slots=True)
class PortRun:
    """Report reuse separately from immutable publication content."""

    publication: RawPortPublication | ProcessedPortPublication
    cache_hit: bool
    status: str
    cache_status: Mapping[str, Any]
    cache_reuse: Literal["computed", "exact_hit", "migrated_reuse", "legacy_adopted"]
    cache_location: str | None

    def __post_init__(self):
        """Detach nested status maps without changing historical publication data."""
        if type(self.cache_hit) is not bool or not isinstance(self.cache_status, Mapping):
            raise TypeError("cache_hit must be bool and cache_status must be a mapping")
        if self.cache_reuse not in {"computed", "exact_hit", "migrated_reuse", "legacy_adopted"}:
            raise ValueError("unknown cache_reuse")
        _nonblank(self.status, "status")
        if self.cache_location is not None and type(self.cache_location) is not str:
            raise TypeError("cache_location must be a string or None")
        object.__setattr__(self, "cache_status", _freeze(self.cache_status))


def bind_raw_port(contract, raw_view, *, parameter_snapshot=None) -> RawPortPublication:
    """Bind a package-selected standalone raw view without modifying legacy data."""
    return RawPortPublication(contract, raw_view, parameter_snapshot)


def selected_raw_bytes(raw_view: EvidencePackageOutput) -> bytes:
    """Serialize only the package-selected standalone raw view."""
    return _canonical_json(serialize_evidence_package_output(raw_view)).encode("utf-8")


def raw_port_ref(publication: RawPortPublication) -> OutputPortRef:
    """Bind semantic input identity to exact immutable selected payload bytes."""
    contract = publication.contract
    return OutputPortRef(contract.source_fingerprint, contract.package_id, contract.output_port,
                         contract.identity, "raw",
                         hashlib.sha256(selected_raw_bytes(publication.raw_view)).hexdigest())


def _storage_contract(publication):
    """Keep B's opaque contract bound to the complete semantic declaration/audit."""
    return {"port_contract": _json_value(publication.contract),
            "parameter_snapshot": (None if publication.parameter_snapshot is None
                                   else publication.parameter_snapshot.to_json())}


def serialize_raw_port_publication(publication: RawPortPublication) -> bytes:
    """Serialize the semantic envelope separately from its unchanged inner view."""
    if not isinstance(publication, RawPortPublication):
        raise TypeError("publication must be a RawPortPublication")
    return _canonical_json({
        "schema": "semantic-output-receipt/v1", "layer": "raw",
        "contract": publication.contract, "ref": publication.ref,
        "parameter_snapshot": _storage_contract(publication)["parameter_snapshot"],
        "upstream_refs": publication.contract.upstream_refs,
        "raw_view": serialize_evidence_package_output(publication.raw_view),
    }).encode("utf-8")


def _decode_ref(value):
    """Decode only the fixed semantic reference fields, never a receipt-named type."""
    return OutputPortRef(**_snapshot_record(value, OutputPortRef))


def _decode_raw_port(payload):
    """Check original inner digests before constructing the selected typed view."""
    if type(payload) is not bytes:
        raise TypeError("semantic payload must be bytes")
    document = json.loads(payload, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    _validate_snapshot_json(document)
    if type(document) is not dict or set(document) != {
            "schema", "layer", "contract", "ref", "parameter_snapshot", "upstream_refs", "raw_view"}:
        raise ValueError("semantic envelope fields do not match")
    if document["schema"] != "semantic-output-receipt/v1":
        raise ValueError("schema must be semantic-output-receipt/v1")
    if document["layer"] != "raw":
        raise ValueError("semantic envelope layer must be raw")
    contract_data = _snapshot_record(document["contract"], OutputPortContract)
    if type(contract_data["upstream_refs"]) is not list or type(document["upstream_refs"]) is not list:
        raise TypeError("upstream_refs must be arrays")
    contract_data["upstream_refs"] = tuple(_decode_ref(ref) for ref in contract_data["upstream_refs"])
    contract = OutputPortContract(**contract_data)
    if tuple(_decode_ref(ref) for ref in document["upstream_refs"]) != contract.upstream_refs:
        raise ValueError("semantic upstream refs do not match contract")
    raw_data = document["raw_view"]
    if type(raw_data) is not dict or "payload_fingerprint" not in raw_data:
        raise ValueError("selected raw view requires its original payload_fingerprint")
    raw = deserialize_evidence_package_output(raw_data)
    snapshot = document["parameter_snapshot"]
    publication = bind_raw_port(contract, raw, parameter_snapshot=(
        None if snapshot is None else ParameterSnapshot.from_json(snapshot)))
    reference = _decode_ref(document["ref"])
    if reference != publication.ref:
        raise ValueError("semantic ref does not match contract or selected payload fingerprint")
    return publication


def _validated_raw_port(payload, context):
    """Bind the validated package envelope to B's full address and opaque contract."""
    publication = _decode_raw_port(payload)
    if not isinstance(context, CacheValidationContext):
        raise TypeError("context must be a CacheValidationContext")
    if context.address != publication.ref.address:
        raise ValueError("semantic address does not match storage address")
    if fingerprint_evidence_dependency(context.contract) != fingerprint_evidence_dependency(
            _storage_contract(publication)):
        raise ValueError("semantic storage contract does not match envelope")
    return publication


def validate_port_payload(payload: bytes, context: CacheValidationContext, *, raw_publication=None) -> None:
    """Validate saved structure/integrity without treating history as current intent."""
    if context.address.layer == "raw":
        _validated_raw_port(payload, context)
    else:
        _validated_processed_port(payload, context, raw_publication)


def save_raw_port(store: CacheStore, publication: RawPortPublication):
    """Publish selected bytes through the sole authoritative cache store."""
    return store.put(
        publication.ref.address, contract=_storage_contract(publication),
        payload=serialize_raw_port_publication(publication), payload_format="json",
        upstream_refs=tuple(ref.address for ref in publication.contract.upstream_refs),
        validator=validate_port_payload,
    )


def _parameter_status(calculated, requested, selected_names):
    """Compare full owner declarations while limiting reuse decisions to selected names."""
    if calculated is None:
        if requested is not None:
            raise ValueError("owner schema is absent from historical raw publication")
        return None
    if requested is None:
        raise ValueError("typed raw history requires independent requested_parameters")
    if (calculated.package_id != requested.package_id
            or calculated.config_schema_version != requested.config_schema_version
            or set(calculated.effective_parameters) != set(requested.effective_parameters)
            or calculated.parameter_impacts != requested.parameter_impacts
            or calculated.parameter_value_contracts != requested.parameter_value_contracts):
        raise ValueError("raw parameter owner schema declarations do not match")
    status = compare_parameter_snapshots(calculated, requested)
    # Full audit remains visible, but unrelated owner knobs cannot invalidate this port.
    warnings = [item for item in status["warnings"] if item["parameter"] in selected_names]
    recompute = any(
        calculated.parameter_impacts[name] == ParameterImpact.RECOMPUTE_REQUIRED.value
        and fingerprint_evidence_dependency(calculated.effective_parameters[name])
        != fingerprint_evidence_dependency(requested.effective_parameters[name])
        for name in selected_names
    )
    return {**status, "warnings": warnings, "recompute_required": recompute,
            "exact_match": not (recompute or warnings),
            "reuse": "recompute_required" if recompute else "reuse_with_warning" if warnings else "exact"}


def _validate_upstream_payload(payload, context, reference, *, store):
    """Verify exact referenced bytes without imposing a semantic codec on native entries."""
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        document = None
    schema = document.get("schema") if isinstance(document, dict) else None
    if isinstance(schema, str) and schema.startswith("semantic-output-receipt/"):
        if reference.layer == "raw":
            publication = _validated_raw_port(payload, context)
        else:
            raw_ref = _decode_ref(document.get("raw_ref"))
            raw = _load_referenced_raw(store, raw_ref)
            if raw is None:
                raise ValueError("processed upstream raw publication is unavailable")
            publication = _validated_processed_port(payload, context, raw)
        if publication.ref != reference:
            raise ValueError("upstream semantic ref does not match selected payload")
    elif hashlib.sha256(payload).hexdigest() != reference.payload_fingerprint:
        raise ValueError("upstream payload fingerprint does not match referenced bytes")


def load_raw_port(store: CacheStore, contract: OutputPortContract, *,
                  requested_parameters: ParameterSnapshot | None) -> RawPortPublication | None:
    """Admit a hit only against an independently supplied current contract and owner."""
    if not isinstance(contract, OutputPortContract):
        raise TypeError("contract must be an OutputPortContract")
    requested = _validated_snapshot(requested_parameters)
    publication = None

    def validate(payload, context):
        """Keep the exact bytes B validated rather than rereading a mutable filesystem path."""
        nonlocal publication
        publication = _validated_raw_port(payload, context)

    address = CacheAddress(contract.source_fingerprint, contract.package_id,
                           contract.output_port, "raw", contract.identity)
    try:
        entry = store.get(address, validator=validate)
    except CacheValidationError:
        return None
    if entry is None:
        return None
    if _canonical_json(publication.contract) != _canonical_json(contract):
        raise ValueError("saved semantic contract does not match current contract")
    expected_refs = tuple(ref.address for ref in contract.upstream_refs)
    if _canonical_json(entry.receipt["upstream_refs"]) != _canonical_json(expected_refs):
        raise ValueError("storage upstream refs do not match semantic contract")
    status = _parameter_status(publication.parameter_snapshot, requested,
                               contract.parameter_projection["selected_names"])
    _validate_projection(contract, requested)
    for reference in contract.upstream_refs:
        def validate_upstream(payload, context):
            """Bind this exact upstream ref; numerical currentness stays with its owner."""
            _validate_upstream_payload(payload, context, reference, store=store)

        try:
            upstream = store.get(reference.address, validator=validate_upstream)
        except CacheValidationError:
            return None
        if upstream is None:
            return None
    return None if status is not None and status["recompute_required"] else publication


def _processing_contract(raw_ref, processor_id, processor_version, parameters, snapshot):
    """Keep semantic recipe identity independent of processor audit-only values."""
    return {"schema": "semantic-output-processing/1", "raw_ref": _json_value(raw_ref),
            "processor_id": processor_id, "processor_version": processor_version,
            "parameters": parameters if snapshot is None else snapshot.identity_payload()}


def processed_port_key(raw: RawPortPublication, processor: EvidenceOutputProcessor) -> str:
    """Bind semantic address, exact selected raw bytes and effective processor recipe."""
    if not isinstance(raw, RawPortPublication) or not isinstance(processor, EvidenceOutputProcessor):
        raise TypeError("processed_port_key requires a raw publication and processor")
    return fingerprint_evidence_dependency(_processing_contract(
        raw.ref, processor.function_id, processor.version,
        processor.parameters, processor.parameter_snapshot))


def selected_processed_bytes(processed_output: EvidenceProcessedOutput) -> bytes:
    """Retain the existing processed serializer and its distinct inner digest."""
    return _canonical_json(serialize_evidence_processed_output(processed_output)).encode("utf-8")


@dataclass(frozen=True, slots=True)
class ProcessedPortPublication:
    """Bind one explicit transformation to its immutable selected raw reference."""

    raw_ref: OutputPortRef
    processed_output: EvidenceProcessedOutput
    identity: str

    def __post_init__(self):
        """Require an exact recipe identity while preserving the core processing identity."""
        if not isinstance(self.raw_ref, OutputPortRef) or self.raw_ref.layer != "raw":
            raise ValueError("processed publication requires a raw reference")
        if not isinstance(self.processed_output, EvidenceProcessedOutput):
            raise TypeError("processed_output must be an EvidenceProcessedOutput")
        if self.processed_output.package_id != self.raw_ref.package_id:
            raise ValueError("processed package does not match raw reference")
        if self.identity != fingerprint_evidence_dependency(_processed_storage_contract(self)):
            raise ValueError("processed semantic identity does not match recipe")

    @property
    def ref(self) -> OutputPortRef:
        """Expose the semantic processed address and unchanged inner processing identity."""
        raw = self.raw_ref
        return OutputPortRef(raw.source_fingerprint, raw.package_id, raw.output_port,
            self.identity, "processed", hashlib.sha256(selected_processed_bytes(
                self.processed_output)).hexdigest(), self.processed_output.processing_identity)


def _processed_storage_contract(publication):
    """Rebuild the canonical recipe from the historical processed publication."""
    output = publication.processed_output
    return _processing_contract(publication.raw_ref, output.processor_id,
        output.processor_version, output.parameters, output.parameter_snapshot)


def serialize_processed_port_publication(publication: ProcessedPortPublication) -> bytes:
    """Wrap the existing processed wire format without copying raw geometry."""
    if not isinstance(publication, ProcessedPortPublication):
        raise TypeError("publication must be a ProcessedPortPublication")
    return _canonical_json({"schema": "semantic-output-receipt/v1", "layer": "processed",
        "raw_ref": publication.raw_ref, "ref": publication.ref,
        "processed_view": serialize_evidence_processed_output(publication.processed_output),
    }).encode("utf-8")


def _validated_processed_port(payload, context, raw):
    """Decode original processed bytes against an independently reopened raw publication."""
    if not isinstance(raw, RawPortPublication):
        raise TypeError("processed validation requires a verified raw publication")
    if type(payload) is not bytes:
        raise TypeError("semantic payload must be bytes")
    document = json.loads(payload, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    _validate_snapshot_json(document)
    if type(document) is not dict or set(document) != {
            "schema", "layer", "raw_ref", "ref", "processed_view"}:
        raise ValueError("processed semantic envelope fields do not match")
    if document["schema"] != "semantic-output-receipt/v1":
        raise ValueError("schema must be semantic-output-receipt/v1")
    if document["layer"] != "processed":
        raise ValueError("semantic envelope layer must be processed")
    if _decode_ref(document["raw_ref"]) != raw.ref:
        raise ValueError("processed raw ref does not match selected raw publication")
    output = deserialize_evidence_processed_output(document["processed_view"], raw_output=raw.raw_view)
    raw_targets = set(raw.contract.target_ids)
    if any(item.target["identity"] not in raw_targets for item in output.outputs):
        raise ValueError("processed target address is outside the selected raw scope")
    contract = _processing_contract(raw.ref, output.processor_id, output.processor_version,
                                   output.parameters, output.parameter_snapshot)
    publication = ProcessedPortPublication(raw.ref, output, fingerprint_evidence_dependency(contract))
    if _decode_ref(document["ref"]) != publication.ref:
        raise ValueError("processed ref does not match recipe or selected bytes")
    if context.address != publication.ref.address:
        raise ValueError("processed address does not match storage address")
    if fingerprint_evidence_dependency(context.contract) != fingerprint_evidence_dependency(contract):
        raise ValueError("processed storage contract does not match recipe")
    return publication


def _load_referenced_raw(store, reference):
    """Resolve raw bytes for integrity validation; currentness stays with the caller's owner."""
    publication = None

    def validate(payload, context):
        """Retain exactly the raw bytes validated by B for this immutable reference."""
        nonlocal publication
        publication = _validated_raw_port(payload, context)
        if publication.ref != reference:
            raise ValueError("processed upstream raw ref does not match stored selected bytes")

    entry = store.get(reference.address, validator=validate)
    return None if entry is None else publication


def _current_raw(store, contract, requested, *, expected_ref=None):
    """Require independent current owner intent before processed reads or callbacks."""
    raw = load_raw_port(store, contract, requested_parameters=requested)
    if raw is None or (expected_ref is not None and raw.ref != expected_ref):
        raise ValueError("selected publication does not match the current raw contract")
    return raw


def _processor_status(output, processor):
    """Reuse A's complete processor comparison without treating saved intent as current."""
    saved, requested = output.parameter_snapshot, processor.parameter_snapshot
    if saved is None and requested is None:
        return None
    if saved is None or requested is None:
        raise ValueError("processed parameter owner schema declarations do not match")
    return compare_parameter_snapshots(saved, requested)


def _load_processed_port(store, raw, processor, *, reference=None, quarantine_invalid=False):
    """Read an exact selected recipe with zero producer or processor execution."""
    identity = processed_port_key(raw, processor)
    address = CacheAddress(raw.ref.source_fingerprint, raw.ref.package_id,
                           raw.ref.output_port, "processed", identity)
    if reference is not None and reference.address != address:
        return None, None
    publication = None

    def validate(payload, context):
        """Use the verified selected raw view for the existing strict inner decoder."""
        nonlocal publication
        publication = _validated_processed_port(payload, context, raw)

    try:
        entry = store.get(address, validator=validate)
    except CacheValidationError as exc:
        if quarantine_invalid:
            # Retain rejected bytes before allowing the owning runner to replace this version.
            store.quarantine(address, reason=str(exc))
        return None, None
    if entry is None:
        return None, None
    if reference is not None and publication.ref != reference:
        return None, None
    if _canonical_json(entry.receipt["upstream_refs"]) != _canonical_json((raw.ref.address,)):
        raise ValueError("processed storage upstream refs do not match selected raw address")
    output = publication.processed_output
    if (publication.identity != identity or output.processor_id != processor.function_id
            or output.processor_version != processor.version):
        return None, None
    status = _processor_status(output, processor)
    if output.error_code is not None or (status is not None and status["recompute_required"]):
        return None, None
    return publication, entry


def load_processed_port(store: CacheStore, reference: OutputPortRef, *,
                        current_raw_contract: OutputPortContract,
                        requested_raw_parameters: ParameterSnapshot | None,
                        processor: EvidenceOutputProcessor) -> ProcessedPortPublication | None:
    """Reopen one selected processed reference without ever calculating a missing result."""
    if not isinstance(reference, OutputPortRef) or reference.layer != "processed":
        raise ValueError("a processed reference is required")
    raw = _current_raw(store, current_raw_contract, requested_raw_parameters)
    publication, _ = _load_processed_port(store, raw, processor, reference=reference)
    return publication


def _processed_run(publication, entry, raw, requested_raw, processor, *, hit):
    """Report full historical/current audits separately from immutable result bytes."""
    raw_status = _parameter_status(raw.parameter_snapshot, requested_raw,
                                  raw.contract.parameter_projection["selected_names"])
    processed_status = None if processor is None else _processor_status(publication.processed_output, processor)
    error = publication.processed_output.error_code
    exact = all(item is None or item["exact_match"] for item in (raw_status, processed_status))
    status = {"freshness": "fresh", "recompute_required": error is not None,
              "exact_match": exact and error is None, "reasons": (), "affected_targets": (),
              "parameter_status": raw_status, "processed_parameter_status": processed_status}
    reuse = "computed" if not hit else {
        "local": "exact_hit", "migrated": "migrated_reuse", "legacy_adopted": "legacy_adopted"}[entry.reuse_origin]
    return PortRun(publication, hit, "fresh" if error is None else "unavailable", status,
                   reuse, None if entry is None else str(entry.payload_paths[0].parent))


def run_port_processor(raw, package: EvidencePackage, *, store: CacheStore,
                       current_raw_contract: OutputPortContract,
                       requested_raw_parameters: ParameterSnapshot | None,
                       analysis_context=None, allow_multiple_planes=False) -> PortRun:
    """Process verified current selected bytes only after an exact processed-cache miss."""
    if not isinstance(raw, RawPortPublication) or not isinstance(package, EvidencePackage):
        raise TypeError("run_port_processor requires a raw publication and package")
    # A stored processed result still requires the same call selection as a cache miss.
    analysis_context = resolve_package_analysis_context(raw.raw_view.source_envelopes,
        analysis_context=analysis_context, supports_multiple_planes=package.supports_multiple_planes,
        allow_multiple_planes=allow_multiple_planes)
    verified = _current_raw(store, current_raw_contract, requested_raw_parameters, expected_ref=raw.ref)
    processor = package.output_processor
    if (verified.raw_view.package_id != package.package_id.strip()
            or verified.raw_view.output_function != package.output_function_id.strip()
            or verified.raw_view.output_function_version != package.output_function_version.strip()):
        raise ValueError("selected raw producer must match the processing package")
    if (processor is not None and processor.parameter_snapshot is not None
            and processor.parameter_snapshot.package_id != verified.raw_view.package_id):
        raise ValueError("processor parameter snapshot must belong to the selected raw package")
    if processor is None:
        output = package.process_output(verified.raw_view, package_freshness="fresh",
            analysis_context=analysis_context, allow_multiple_planes=allow_multiple_planes)
        identity = fingerprint_evidence_dependency(_processing_contract(verified.ref,
            output.processor_id, output.processor_version, output.parameters, output.parameter_snapshot))
        return _processed_run(ProcessedPortPublication(verified.ref, output, identity), None,
                              verified, requested_raw_parameters, None, hit=False)
    identity = processed_port_key(verified, processor)
    address = CacheAddress(verified.ref.source_fingerprint, verified.ref.package_id,
                           verified.ref.output_port, "processed", identity)
    with store.identity_lock(address):
        publication, entry = _load_processed_port(store, verified, processor, quarantine_invalid=True)
        if publication is not None:
            return _processed_run(publication, entry, verified, requested_raw_parameters, processor, hit=True)
        output = package.process_output(verified.raw_view, package_freshness="fresh",
            analysis_context=analysis_context, allow_multiple_planes=allow_multiple_planes)
        publication = ProcessedPortPublication(verified.ref, output, identity)
        if output.error_code is not None:
            return _processed_run(publication, None, verified, requested_raw_parameters, processor, hit=False)

        def validate(payload, context):
            """Bind B publication and competing writers to this exact selected raw view."""
            _validated_processed_port(payload, context, verified)

        entry = store.put(address, contract=_processed_storage_contract(publication),
            payload=serialize_processed_port_publication(publication), payload_format="json",
            upstream_refs=(verified.ref.address,), validator=validate)
        return _processed_run(publication, entry, verified, requested_raw_parameters, processor, hit=False)
