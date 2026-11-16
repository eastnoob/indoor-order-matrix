"""Package-owned independent centroid and route publications using the shared store."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from itertools import combinations

from . import group_distance as kernel
from . import group_distance_evidence_package as owner
from .cache_paths import CacheAddress
from .cache_store import CacheEntry, CacheStore
from .evidence_package_parameters import ParameterImpact, ParameterSnapshot
from .evidence_package_storage import load_raw_bytes
from .field_core import (
    EvidenceChannelRecord, EvidenceChannelReference, EvidenceOutputChannel,
    EvidenceOutputScale, EvidencePackageOutput, FieldQuery, FieldResultEnvelope,
    _json_value, build_field_result_cache_identity,
    fingerprint_evidence_dependency,
)
from .output_port_cache import (
    OutputPortContract, OutputPortRef, PortRun, _parameter_status,
    bind_raw_port, load_raw_port, run_port_processor, save_raw_port, validate_port_payload,
)

_PORTS = {"euclidean_distance": "center_to_center_euclidean", "path_distance": "centroid_free_space_hybrid"}
_PATH_PARAMETERS = ("grid", "query_context", "free_space_result_ref", "clearance_mode", "clearance_policy")
_SOURCE_CHANNEL = "selected_group_distance_observation"


def _current_parameters(bundle, parameters):
    """Require independently resolved owner declarations and actual bundle values."""
    if not isinstance(parameters, ParameterSnapshot):
        raise TypeError("parameters must be an independently resolved ParameterSnapshot")
    expected = owner.build_group_distance_parameter_snapshot(bundle)
    _parameter_status(parameters, expected, tuple(expected.effective_parameters))
    if fingerprint_evidence_dependency(parameters.effective_parameters) != fingerprint_evidence_dependency(expected.effective_parameters):
        raise ValueError("parameters differ from the current bundle")
    return parameters


def project_port_parameters(snapshot, *, names, schema):
    """Declare selected names while hashing only their recompute-required values."""
    names = tuple(sorted(set(names)))
    if not set(names) <= set(snapshot.effective_parameters):
        raise ValueError("unknown projected parameters")
    selected = tuple(name for name in names if snapshot.parameter_impacts[name] == ParameterImpact.RECOMPUTE_REQUIRED.value)
    return {"schema": schema, "selected_names": list(names),
            "values": {name: snapshot.effective_parameters[name] for name in selected},
            "value_contracts": {name: snapshot.parameter_value_contracts[name] for name in selected}}


def _source_facts(bundle):
    """Project recognized factual identities rather than guessing which strings are paths."""
    source = bundle.source_identity
    if not isinstance(source, Mapping):
        raise ValueError("source_identity needs an explicit factual identity mapping")
    if source.get("project_global_id") and source.get("frame"):
        identity = {name: source[name] for name in ("project_global_id", "frame")}
    elif isinstance(source.get("id"), str) and source["id"].strip():
        identity = {"id": source["id"]}
    elif (isinstance(source.get("sha256"), str) and len(source["sha256"]) == 64
          and all(character in "0123456789abcdef" for character in source["sha256"])
          and type(source.get("bytes")) is int and source["bytes"] >= 0):
        identity = {name: source[name] for name in ("sha256", "bytes")}
    else:
        raise ValueError("source_identity has no supported explicit factual identity")
    return {"identity": identity, "groups": tuple({
        "group_id": group.group_id, "components": kernel._ordered(group.components),
        "source_refs": kernel._ordered(group.source_refs), "status": group.status,
        "explanation": group.explanation,
    } for group in sorted(bundle.groups, key=lambda item: item.group_id))}


def geometry_registration(bundle):
    """Expose the member/plane/origin facts required to register centroid measurements."""
    plane = _json_value(bundle.analysis_plane)
    if plane is not None:
        if not isinstance(plane, Mapping):
            raise ValueError("analysis_plane must be a mapping or None")
        plane = {name: plane[name] for name in ("identity", "frame", "frame_id", "basis", "normal", "origin", "revision", "units") if name in plane}
    return {"source": _source_facts(bundle)["identity"], "analysis_plane": plane,
            "frame": bundle.query.frame, "origin_offset": bundle.origin_offset,
            "members": {group.group_id: kernel._ordered(group.source_refs)
                        for group in sorted(bundle.groups, key=lambda item: item.group_id)}}


def _pair_scope(bundle):
    """Keep historical kernel IDs outside the selected canonical target namespace."""
    ids = tuple(sorted(group.group_id for group in bundle.groups))
    if len(set(ids)) != len(ids) or any(type(identity) is not str or not identity for identity in ids):
        raise ValueError("group identities must be unique nonempty strings")
    source = _source_facts(bundle)["identity"]
    pairs = {pair: kernel._pair_id(pair, source) for pair in combinations(ids, 2)}
    return pairs or {(): "empty-scope:" + fingerprint_evidence_dependency(source)[:24]}


def _require_repair_policy(parameters, repaired_result):
    """Admit saved route policy only when its complete owner values match current intent."""
    if repaired_result is None:
        return
    if not isinstance(repaired_result, Mapping):
        raise TypeError("repaired_result must be a saved result mapping")
    policy = repaired_result.get("policy")
    if policy is not None:
        # Historical thresholds must be complete; capture never inserts today's defaults.
        policy = owner.GROUP_DISTANCE_CLEARANCE_SCHEMA.capture_calculated(
            policy, sources={name: "saved-repair" for name in policy},
        ).effective_parameters
    if policy != parameters.effective_parameters["clearance_policy"]:
        raise ValueError("saved repair clearance policy differs from current owner intent")


def _contract(bundle, parameters, port, *, repaired_result=None, free_space_ref=None):
    """Build selected input identity without evaluating geometry or route readings."""
    _current_parameters(bundle, parameters)
    if port == "path_distance":
        _require_repair_policy(parameters, repaired_result)
    source = _source_facts(bundle)
    registration = geometry_registration(bundle)
    inputs = {"geometry": fingerprint_evidence_dependency(source),
              "registration": fingerprint_evidence_dependency(registration)}
    upstreams = ()
    if port == "path_distance":
        if bundle.free_space_samples is not None:
            if not isinstance(free_space_ref, OutputPortRef) or free_space_ref.layer != "raw":
                raise ValueError("saved samples require an exact raw free_space_ref")
            upstreams = (free_space_ref,)
        actual = kernel.group_distance_input_fingerprints(bundle)
        if bundle.dependency_fingerprints and dict(bundle.dependency_fingerprints) != actual:
            raise ValueError("input bundle dependency fingerprints are stale")
        inputs.update({name: value for name, value in actual.items() if name not in {"source", "groups", "analysis_plane"}})
        inputs["repair"] = fingerprint_evidence_dependency(repaired_result)
        names = _PATH_PARAMETERS
        version = {"algorithm": kernel.CLEARANCE_ALGORITHM_VERSION if bundle.clearance_policy is not None else kernel.ALGORITHM_VERSION,
                   "edge": kernel.CLEARANCE_EDGE_SUPPORT_VERSION if bundle.clearance_policy is not None else kernel.EDGE_SUPPORT_VERSION,
                   "arithmetic": kernel.ARITHMETIC_VERSION, "networkx": kernel.nx.__version__}
        if repaired_result is not None:
            owner._run_contract(bundle, repaired_result)
            pairs = {tuple(row["group_ids"]) for row in owner._result_observations(repaired_result)}
            if pairs != set(combinations(sorted(group.group_id for group in bundle.groups), 2)):
                raise ValueError("saved repair must cover the complete bundle pair scope")
    else:
        names = ()
        version = {"algorithm": "group-union-centroid-euclidean/1", "shapely": kernel.shapely.__version__}
    inputs["recipe"] = fingerprint_evidence_dependency(version)
    return OutputPortContract(owner.PACKAGE_ID, port, fingerprint_evidence_dependency(source), inputs,
        project_port_parameters(parameters, names=names, schema=f"group-distance/{'euclidean' if not names else 'path'}-parameters/1"),
        upstreams, f"group-distance-{port}/1", "group-distance-semantic/v1",
        tuple((target, port) for target in _pair_scope(bundle).values()))


def euclidean_port_contract(bundle, *, parameters):
    """Build current centroid intent even when no route publication was selected."""
    return _contract(bundle, parameters, "euclidean_distance")


def distance_port_contracts(bundle, *, parameters, repaired_result=None, free_space_ref=None):
    """Declare both independently addressable semantic publications."""
    return {port: _contract(bundle, parameters, port, repaired_result=repaired_result, free_space_ref=free_space_ref)
            for port in _PORTS}


def _verify_free_space(bundle, store, reference, validator):
    """Require the exact owner-validated stored bytes before route reuse or evaluation."""
    if bundle.free_space_samples is None:
        return
    if not isinstance(store, CacheStore) or not isinstance(reference, OutputPortRef) or not callable(validator):
        raise ValueError("saved samples require store, free_space_ref and free_space_validator")
    def validate(payload, context):
        """Keep schema ownership in the adapter and bind its exact immutable payload."""
        validator(payload, context)
        if hashlib.sha256(payload).hexdigest() != reference.payload_fingerprint:
            raise ValueError("free_space_ref payload fingerprint differs")
    if store.get(reference.address, validator=validate) is None:
        raise ValueError("selected free-space publication is unavailable")


def _selected_publication(bundle, parameters, contract, rows):
    """Build fresh typed sources and lineage containing only the selected measurement."""
    port, raw_key = contract.output_port, _PORTS[contract.output_port]
    targets = _pair_scope(bundle)
    registration = geometry_registration(bundle)
    query = (FieldQuery("group-centroid-scope", frame=bundle.query.frame, plane=registration["analysis_plane"], revision="centroid/1")
             if port == "euclidean_distance" else bundle.query)
    if not rows:
        rows = ({"group_ids": (), raw_key: {"status": "not_available", "value": None, "units": "m", "reason": "pair scope is empty"}, "geometry_audit": {}},)
    sources, outputs = [], []
    for original in rows:
        ids = tuple(original["group_ids"])
        pair_id = targets[ids]
        raw = original[raw_key]
        audits = {identity: {**audit, **({"source_refs": kernel._ordered(audit["source_refs"])}
                  if "source_refs" in audit else {})} for identity, audit in original["geometry_audit"].items()}
        selected = {"pair_id": pair_id, "group_ids": ids, raw_key: raw, "geometry_audit": audits}
        if port == "path_distance":
            selected.update({name: original[name] for name in ("route", "lineage", "baseline_path_reading", "repair_diagnostics", "clearance_policy") if name in original})
            if "lineage" in selected and "group_source_refs" in selected["lineage"]:
                selected["lineage"] = {**selected["lineage"], "group_source_refs": {
                    identity: kernel._ordered(refs) for identity, refs in selected["lineage"]["group_source_refs"].items()}}
        target = {"kind": "furniture_group_pair", "id": pair_id, "identity": pair_id}
        status = owner._as_status(raw["status"])
        refs = tuple(sorted({str(ref) for group in bundle.groups if group.group_id in ids for ref in group.source_refs})) or ("group-distance-input",)
        provenance = {"method": "independent_group_distance", "algorithm_version": contract.algorithm_version,
            "schema_version": contract.schema_version, "analysis_plane": registration["analysis_plane"],
            "geometry_registration": registration, "dependency_fingerprints": contract.input_fingerprints}
        if port == "path_distance":
            provenance.update(query_context=bundle.query_context, free_space_result_ref=(bundle.free_space_samples or {}).get("result_ref"))
        identity = build_field_result_cache_identity(target=target, query=query,
            channel_declarations=({"channel": _SOURCE_CHANNEL, "polarity": "descriptive", "units": "m"},),
            input_fingerprint=fingerprint_evidence_dependency({"selected": selected, "inputs": contract.input_fingerprints}),
            source_fingerprint=contract.source_fingerprint, recipe_fingerprint=contract.input_fingerprints["recipe"],
            algorithm_version=contract.algorithm_version, schema_version=contract.schema_version)
        explanation = owner._status_explanation(status, raw)
        record = EvidenceChannelRecord(channel=_SOURCE_CHANNEL, required=True, polarity="descriptive",
            observation=selected, units="m", status=status, source_ids=refs,
            provenance=provenance, explanation=explanation)
        source = FieldResultEnvelope(target=target, query=query, raw_status=status,
            channel_set=(_SOURCE_CHANNEL,), value={"channels": (record,)}, source_ids=refs,
            provenance=provenance, cache_identity=identity, explanation=explanation)
        sources.append(source)
        outputs.append(EvidenceOutputChannel(target=target, channel=port,
            observation={"value": raw.get("value"), "units": raw.get("units", "m"), "raw_status": raw["status"],
                         "pair_id": pair_id, "group_ids": ids, "distance": raw}, status=status,
            scale=EvidenceOutputScale(meaning="Centroid-to-centroid Euclidean distance" if port == "euclidean_distance" else "Centroid offsets plus selected discrete free-space route length",
                                      units="m", normalization_method="identity; raw metric distance"),
            derived_from=(EvidenceChannelReference.from_envelope(source, _SOURCE_CHANNEL),),
            source_ids=refs, provenance=provenance, explanation=explanation))
    # Keep the existing processor admission contract; selected source/port identities carry the split.
    view = EvidencePackageOutput(owner.PACKAGE_ID, owner.OUTPUT_FUNCTION_ID, owner.OUTPUT_FUNCTION_VERSION, tuple(sources), tuple(outputs))
    return bind_raw_port(contract, view, parameter_snapshot=parameters)


def evaluate_euclidean_port(bundle, *, parameters):
    """Measure only group centroids and publish no route-dependent facts."""
    contract = euclidean_port_contract(bundle, parameters=parameters)
    rows = tuple({"group_ids": item.group_ids, "center_to_center_euclidean": item.reading,
                  "geometry_audit": item.geometry_audit} for item in kernel.calculate_euclidean_pairs(bundle))
    return _selected_publication(bundle, parameters, contract, rows)


def evaluate_path_port(bundle, *, parameters, repaired_result=None, store=None,
                       free_space_ref=None, free_space_validator=None):
    """Evaluate only route readings, preserving selected witness and uncertainty evidence."""
    contract = _contract(bundle, parameters, "path_distance", repaired_result=repaired_result, free_space_ref=free_space_ref)
    _verify_free_space(bundle, store, free_space_ref, free_space_validator)
    if repaired_result is None:
        result = kernel.calculate_group_pair_distances(bundle, include_euclidean=False)
        rows = tuple(_json_value(item) for item in result.observations)
    else:
        sources = owner.build_group_distance_source_envelopes(repaired_result, bundle)
        rows = tuple(next(record.observation for record in source.value["channels"] if record.channel == owner.SOURCE_CHANNEL) for source in sources)
    return _selected_publication(bundle, parameters, contract, rows)


def project_verified_distance_ports(entry: CacheEntry, *, bundle, parameters, store,
                                    repaired_result=None, free_space_ref=None, free_space_validator=None):
    """Reopen an original typed B publication before projecting it without calculation."""
    contracts = distance_port_contracts(bundle, parameters=parameters, repaired_result=repaired_result, free_space_ref=free_space_ref)
    _verify_free_space(bundle, store, free_space_ref, free_space_validator)
    contract, inputs = owner._run_contract(bundle, repaired_result)
    expected = CacheAddress(owner._distance_source_fingerprint(contract), owner.PACKAGE_ID, "combined", "raw", contract["package_identity"])
    if entry.address != expected:
        raise ValueError("combined entry differs from the original current contract")
    package = owner.build_group_distance_evidence_package()
    reopened = store.get(entry.address, validator=owner._distance_raw_validator(package, contract))
    if reopened is None:
        raise ValueError("combined entry is unavailable")
    lookup = load_raw_bytes(reopened.payload_paths[0].read_bytes(), cache_key=entry.address.identity, contract=contract, package=package)
    if lookup is None or not owner._cached_sources_match(lookup.raw_output, bundle, inputs, contract["target_ids"]):
        raise ValueError("combined source or parameters do not match current context")
    snapshot_data = lookup.cached_contract.get("parameter_snapshot")
    if snapshot_data is None:
        raise ValueError("combined publication has no original typed parameter snapshot")
    snapshot = ParameterSnapshot.from_json(snapshot_data)
    rows = tuple(next(record.observation for record in source.value["channels"] if record.channel == owner.SOURCE_CHANNEL)
                 for source in lookup.raw_output.source_envelopes)
    return {port: _selected_publication(bundle, snapshot, selected, rows) for port, selected in contracts.items()}


def _run_result(publication, entry, *, hit, parameters, reuse=None):
    """Return current reuse evidence without rewriting saved calculation provenance."""
    comparison = _parameter_status(publication.parameter_snapshot, parameters, publication.contract.parameter_projection["selected_names"])
    status = {"freshness": "fresh", "recompute_required": False, "exact_match": comparison is None or comparison["exact_match"],
              "reasons": (), "affected_targets": (), "parameter_status": comparison, "processed_parameter_status": None}
    mode = reuse or ({"local": "exact_hit", "migrated": "migrated_reuse", "legacy_adopted": "legacy_adopted"}[entry.reuse_origin] if hit else "computed")
    return PortRun(publication, hit, "fresh", status, mode, str(entry.payload_paths[0].parent))


def run_group_distance_ports(bundle, *, store, parameters, repaired_result=None, legacy_entry=None,
                             free_space_ref=None, free_space_validator=None):
    """Reuse and calculate each independent port under its existing B identity lock."""
    contracts = distance_port_contracts(bundle, parameters=parameters, repaired_result=repaired_result, free_space_ref=free_space_ref)
    _verify_free_space(bundle, store, free_space_ref, free_space_validator)
    legacy_checked = legacy_entry is not None
    adopted = None
    result = {}
    for port, contract in contracts.items():
        address = CacheAddress(contract.source_fingerprint, owner.PACKAGE_ID, port, "raw", contract.identity)
        with store.identity_lock(address):
            try:
                entry = store.get(address, validator=validate_port_payload)
                publication = None if entry is None else load_raw_port(store, contract, requested_parameters=parameters)
            except (ValueError, TypeError) as exc:
                store.quarantine(address, reason=str(exc))
                publication = None
            if publication is not None:
                result[port] = _run_result(publication, entry, hit=True, parameters=parameters)
                continue
            if not legacy_checked:
                legacy_checked = True
                # An optional combined candidate cannot veto independent hits or calculation.
                try:
                    original, _ = owner._run_contract(bundle, repaired_result)
                    old_address = CacheAddress(owner._distance_source_fingerprint(original), owner.PACKAGE_ID, "combined", "raw", original["package_identity"])
                    legacy_entry = store.get(old_address, validator=owner._distance_raw_validator(owner.build_group_distance_evidence_package(), original))
                    if legacy_entry is not None:
                        adopted = project_verified_distance_ports(legacy_entry, bundle=bundle, parameters=parameters, store=store,
                            repaired_result=repaired_result, free_space_ref=free_space_ref, free_space_validator=free_space_validator)
                except (ValueError, TypeError):
                    legacy_entry = None
            if legacy_entry is not None:
                if adopted is None:
                    adopted = project_verified_distance_ports(legacy_entry, bundle=bundle, parameters=parameters, store=store,
                        repaired_result=repaired_result, free_space_ref=free_space_ref, free_space_validator=free_space_validator)
                publication = adopted[port]
            else:
                publication = (evaluate_euclidean_port(bundle, parameters=parameters) if port == "euclidean_distance" else
                    evaluate_path_port(bundle, parameters=parameters, repaired_result=repaired_result, store=store,
                                       free_space_ref=free_space_ref, free_space_validator=free_space_validator))
            entry = save_raw_port(store, publication)
            if legacy_entry is not None:
                store.record_reuse_origin(address, "legacy_adopted")
                store.record_lookup_binding(address, legacy_entry.address, attestation={
                    "profile": "group-distance-semantic-adoption/1",
                    "payload_sha256": hashlib.sha256(legacy_entry.payload_paths[0].read_bytes()).hexdigest(),
                    "target_mapping": {kernel._pair_id(ids, bundle.source_identity): target for ids, target in _pair_scope(bundle).items()}})
            result[port] = _run_result(publication, entry, hit=legacy_entry is not None, parameters=parameters,
                                       reuse="legacy_adopted" if legacy_entry is not None else "computed")
    return result


def run_euclidean_processed_port(bundle, *, store, parameters, processor):
    """Process the independent centroid port without requesting route inputs or work."""
    contract = euclidean_port_contract(bundle, parameters=parameters)
    address = CacheAddress(contract.source_fingerprint, contract.package_id,
                           contract.output_port, "raw", contract.identity)
    with store.identity_lock(address):
        raw = load_raw_port(store, contract, requested_parameters=parameters)
        if raw is None:
            # Keep a rejected publication before rebuilding only this centroid version.
            store.quarantine(address, reason="selected Euclidean raw publication is unavailable")
            raw = evaluate_euclidean_port(bundle, parameters=parameters)
            save_raw_port(store, raw)
    package = owner.build_group_distance_evidence_package(output_processor=processor)
    return run_port_processor(raw, package, store=store,
        current_raw_contract=contract, requested_raw_parameters=parameters)
