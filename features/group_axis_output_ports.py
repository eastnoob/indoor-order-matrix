"""Independent pure-axis and distance-conditioned publications in the shared store."""

from __future__ import annotations

from itertools import combinations
import json

from . import group_axis_potential_field as potential
from .cache_paths import CacheAddress
from .evidence_package_parameters import REQUIRED, ParameterSnapshot
from .evidence_package_storage import processed_cache_key
from .field_core import (
    EvidencePackage, EvidencePackageChannelReference, EvidencePackageDependency,
    FieldResultEnvelope, _canonical_json, _normalize_evidence_package_dependency_graph,
    _validate_evidence_package_dependency_cycles, fingerprint_evidence_dependency,
)
from .package_analysis_context import resolve_package_analysis_context
from .group_distance_output_ports import project_port_parameters
from .output_port_cache import (
    OutputPortContract, PortRun, ProcessedPortPublication, RawPortPublication,
    _parameter_status, bind_raw_port, load_processed_port, load_raw_port,
    processed_port_key, save_raw_port, validate_port_payload,
)


_PROXIMITY = "euclidean_symmetric_reciprocal_relative_proximity"
_MODULATION = "distance_modulated_axis_support"


def bind_port_distance_modulation(
    raw_port, processed_port, *, store, processor, current_raw_contract,
    requested_raw_parameters, compatibility, dependency_graph,
):
    """Reopen independently current exact Euclidean bytes without producing upstreams."""
    if not isinstance(raw_port, RawPortPublication):
        raise TypeError("raw_port must be a RawPortPublication")
    if not isinstance(processed_port, ProcessedPortPublication):
        raise TypeError("processed_port must be a ProcessedPortPublication")
    if (raw_port.contract.package_id != "group-walk-distance"
            or raw_port.contract.output_port != "euclidean_distance"
            or raw_port.contract.channels != ("euclidean_distance",)
            or raw_port.contract.schema_version != "group-distance-semantic/v1"):
        raise ValueError("distance modulation requires the euclidean_distance semantic port")
    if not isinstance(current_raw_contract, OutputPortContract):
        raise TypeError("current_raw_contract must be an OutputPortContract")
    if _canonical_json(current_raw_contract) != _canonical_json(raw_port.contract):
        raise ValueError("selected publication does not match the current raw contract")
    # Cache hits require the same graph admission as evaluation; retain one-shot edges.
    graph = _normalize_evidence_package_dependency_graph(dependency_graph)
    _validate_evidence_package_dependency_cycles(graph)
    if potential.PACKAGE_ID not in graph:
        raise ValueError("dependency graph must contain the current package")
    if set(graph[potential.PACKAGE_ID]) != {raw_port.raw_view.package_id}:
        raise ValueError("current package graph edges must match declared dependencies")
    if set(graph[raw_port.raw_view.package_id]) != {
        item.package_id for item in raw_port.raw_view.dependencies
    }:
        raise ValueError("upstream graph edges must match declared dependencies")
    # Owner declarations are independent even when their selected value set is empty.
    _parameter_status(raw_port.parameter_snapshot, requested_raw_parameters,
                      raw_port.contract.parameter_projection["selected_names"])
    current = load_raw_port(store, current_raw_contract,
                            requested_parameters=requested_raw_parameters)
    if current is not None and current.ref != raw_port.ref:
        raise ValueError("current raw selected bytes differ from the supplied raw ref")
    if processed_port.raw_ref != raw_port.ref:
        raise ValueError("processed publication does not bind the exact Euclidean raw ref")
    if processed_port.identity != processed_port_key(raw_port, processor):
        raise ValueError("processed publication does not match the current processor recipe")
    if processed_port.processed_output.processing_identity != processed_cache_key(raw_port.raw_view, processor):
        raise ValueError("processed output does not match the current processing identity")

    saved_processed = None
    if current is not None:
        saved_processed = load_processed_port(store, processed_port.ref,
            current_raw_contract=current_raw_contract,
            requested_raw_parameters=requested_raw_parameters, processor=processor)
        if saved_processed is not None and saved_processed.ref != processed_port.ref:
            raise ValueError("current processed selected bytes differ from the supplied ref")
    raw = raw_port.raw_view if current is None else current.raw_view
    processed = (processed_port.processed_output if saved_processed is None
                 else saved_processed.processed_output)
    if processed.error_code is not None:
        raise ValueError("distance modulation requires a successful processed Euclidean publication")
    if {item.channel for item in processed.outputs} != {_PROXIMITY}:
        raise ValueError("distance modulation requires symmetric reciprocal Euclidean proximity")
    if {item.target["identity"] for item in processed.outputs} != set(raw_port.contract.target_ids):
        raise ValueError("processed Euclidean publication has an incomplete target scope")
    registrations = [item.provenance.get("geometry_registration") for item in raw.outputs]
    if (not registrations or registrations[0] is None
            or any(item != registrations[0] for item in registrations)
            or any(item.provenance.get("schema_version") != "group-distance-semantic/v1"
                   for item in raw.outputs)):
        raise ValueError("Euclidean publication requires one known geometry registration")
    registration = registrations[0]
    if fingerprint_evidence_dependency(registration) != current_raw_contract.input_fingerprints.get("registration"):
        raise ValueError("Euclidean geometry registration differs from current inputs")
    facts = potential.project_distance_geometry_registration(compatibility)
    if (potential.project_distance_geometry_registration({**compatibility,
            "distance_plane": registration.get("analysis_plane")})["distance_plane"]
            != facts["distance_plane"]):
        raise ValueError("distance projection plane differs from compatibility binding")
    # Member identity is order-independent; the producer uses digest order, legacy proof lexical order.
    if ({group: tuple(sorted(refs)) for group, refs in registration["members"].items()}
            != {group: tuple(sorted(refs)) for group, refs in facts["distance_member_refs"].items()}):
        raise ValueError("distance member refs differ from compatibility binding")
    if tuple(registration.get("origin_offset", ())) != (0.0, 0.0):
        raise ValueError("distance compatibility requires zero in-plane origin shift")
    facts["distance_geometry_registration"] = registration
    references = tuple(EvidencePackageChannelReference(raw.package_id,
        raw.output_identity, item.target["identity"], item.channel, port="processed",
        processing_identity=processed.processing_identity) for item in processed.outputs)
    dependency = EvidencePackageDependency(raw.package_id, raw.output_identity,
        references, raw, "fresh" if saved_processed is not None else "unavailable",
        source_processed_output=processed)
    return potential.DistanceModulationInput(dependency, processed.processing_identity,
                                              facts, graph)


def _axis_addresses(sources):
    """Declare actual output addresses without invoking the pure-axis numerical producer."""
    addresses = [(potential.AGGREGATE_TARGET["identity"], channel) for channel in (
        "aggregate_direction", "direction_coherence", "resultant_strength",
        "coverage", "excluded_axis_diagnostics")]
    for group_a, group_b in combinations(sorted(source.target["id"] for source in sources), 2):
        target = json.dumps([group_a, group_b], ensure_ascii=False, separators=(",", ":"))
        addresses.extend((target, channel) for channel in potential.RELATION_CHANNELS)
    anchors = tuple(source for source in sources if potential._axis_observation(source)[0] is not None)
    if not anchors:
        addresses.append((potential.AGGREGATE_TARGET["identity"], "source_axis_scope_diagnostics"))
    for anchor in anchors:
        field_id = potential._field_id(anchor)
        addresses.extend((potential._cell_target(field_id, target.target["identity"])["identity"],
                          "axis_field_support") for target in sources)
        addresses.extend((potential._field_target(field_id)["identity"], channel)
                         for channel in ("non_self_profile", "soft_view_direction"))
    return tuple(addresses)


def _axis_contract(sources, parameters):
    """Reuse the source owner's existing audit projection while selecting no switch values."""
    original = potential.build_group_axis_potential_package_contract(sources)
    inputs = {item["name"]: item["fingerprint"] for item in original["dependencies"]}
    return OutputPortContract(potential.PACKAGE_ID, "axis_potential", inputs["source"], inputs,
        project_port_parameters(parameters, names=(), schema="axis-potential/parameters/1"),
        (), potential.OUTPUT_FUNCTION_VERSION, potential.FIELD_OUTPUT_SCHEMA,
        _axis_addresses(sources))


def _run_result(publication, entry, *, hit, parameters, freshness="fresh"):
    """Report current reuse and availability separately from immutable channel history."""
    comparison = _parameter_status(publication.parameter_snapshot, parameters,
                                   publication.contract.parameter_projection["selected_names"])
    available = freshness == "fresh"
    status = {"freshness": freshness, "recompute_required": not available,
        "exact_match": available and (comparison is None or comparison["exact_match"]),
        "reasons": () if available else ({"code": "upstream_unavailable"},),
        "affected_targets": () if available else publication.contract.target_ids,
        "parameter_status": comparison, "processed_parameter_status": None}
    reuse = "computed" if not hit else {"local": "exact_hit", "migrated": "migrated_reuse",
                                       "legacy_adopted": "legacy_adopted"}[entry.reuse_origin]
    return PortRun(publication, hit, freshness, status, reuse,
                   None if entry is None else str(entry.payload_paths[0].parent))


def _run_pure(sources, store, parameters, analysis_context, allow_multiple_planes=False):
    """Run the existing pure producer only after a miss under the shared identity lock."""
    contract = _axis_contract(sources, parameters)
    address = CacheAddress(contract.source_fingerprint, potential.PACKAGE_ID,
                            contract.output_port, "raw", contract.identity)
    with store.identity_lock(address):
        try:
            entry = store.get(address, validator=validate_port_payload)
            publication = (None if entry is None else load_raw_port(
                store, contract, requested_parameters=parameters))
        except (ValueError, TypeError) as exc:
            # Preserve the rejected bytes before the owning producer replaces this address.
            store.quarantine(address, reason=str(exc))
            publication = None
        if publication is not None:
            return _run_result(publication, entry, hit=True, parameters=parameters)
        raw = potential.build_group_axis_potential_package().evaluate(
            sources, analysis_context=analysis_context,
            allow_multiple_planes=allow_multiple_planes)
        publication = bind_raw_port(contract, raw, parameter_snapshot=parameters)
        entry = save_raw_port(store, publication)
        return _run_result(publication, entry, hit=False, parameters=parameters)


def run_group_axis_output_ports(
    envelopes, *, store, parameters, distance_raw=None, distance_processed=None,
    distance_processor=None, current_distance_contract=None,
    requested_distance_parameters=REQUIRED, compatibility=None, dependency_graph=None,
    analysis_context=None, package_planes=None, allow_multiple_planes=False,
):
    """Reuse pure-axis evidence independently and optionally consume exact Euclidean processing."""
    if not isinstance(parameters, ParameterSnapshot):
        raise TypeError("parameters must be a group-axis ParameterSnapshot")
    expected = potential.build_group_axis_parameter_snapshot(
        distance_modulation_enabled=parameters.effective_parameters.get("distance_modulation_enabled"))
    _parameter_status(parameters, expected, tuple(expected.effective_parameters))
    sources = tuple(envelopes)
    if not sources or any(not isinstance(source, FieldResultEnvelope) for source in sources):
        raise TypeError("envelopes must contain FieldResultEnvelope values")
    analysis_context = resolve_package_analysis_context(sources, analysis_context=analysis_context,
        package_planes=package_planes, allow_multiple_planes=allow_multiple_planes)
    enabled = parameters.effective_parameters["distance_modulation_enabled"]
    modulation = None
    if enabled:
        if requested_distance_parameters is REQUIRED:
            raise ValueError("requested_distance_parameters is required when modulation is enabled")
        modulation = bind_port_distance_modulation(distance_raw, distance_processed,
            store=store, processor=distance_processor, current_raw_contract=current_distance_contract,
            requested_raw_parameters=requested_distance_parameters, compatibility=compatibility,
            dependency_graph=dependency_graph)
        potential._validate_distance_modulation(sources, modulation)
    pure = _run_pure(sources, store, parameters, analysis_context, allow_multiple_planes)
    result = {"axis_potential": pure}
    if modulation is None:
        return result
    available = modulation.dependency.package_freshness == "fresh"
    contract = OutputPortContract(potential.PACKAGE_ID, _MODULATION,
        pure.publication.contract.source_fingerprint,
        {"axis": pure.publication.ref.identity,
         "distance_registration": fingerprint_evidence_dependency(modulation.compatibility)},
        project_port_parameters(parameters, names=("distance_modulation_enabled",),
                                schema="distance-modulated-axis-support/parameters/1"),
        (pure.publication.ref, distance_processed.ref), "distance-modulated-axis-support/1",
        potential.FIELD_OUTPUT_SCHEMA,
        tuple((item.target["identity"], _MODULATION) for item in pure.publication.raw_view.outputs
              if item.channel == "axis_field_support"))
    address = CacheAddress(contract.source_fingerprint, potential.PACKAGE_ID,
                            _MODULATION, "raw", contract.identity)

    def produce(context):
        """Reuse cached pure outputs so a modulation-only miss never recalculates axes."""
        return potential._distance_modulated_outputs(context, modulation, pure.publication.raw_view.outputs)

    with store.identity_lock(address):
        publication = None
        if available:
            try:
                entry = store.get(address, validator=validate_port_payload)
                publication = (None if entry is None else load_raw_port(
                    store, contract, requested_parameters=parameters))
            except (ValueError, TypeError) as exc:
                # The modulation owner retains corruption without touching reusable pure axes.
                store.quarantine(address, reason=str(exc))
                publication = None
        if publication is not None:
            result[_MODULATION] = _run_result(publication, entry, hit=True, parameters=parameters)
            return result
        package = EvidencePackage(potential.PACKAGE_ID, _MODULATION,
            "distance-modulated-axis-support/1", None, context_output_function=produce)
        raw = package.evaluate(sources, dependencies=(modulation.dependency,),
                                dependency_graph=modulation.dependency_graph,
                                analysis_context=analysis_context,
                                allow_multiple_planes=allow_multiple_planes)
        publication = bind_raw_port(contract, raw, parameter_snapshot=parameters)
        # Availability is transient: never publish a redacted result as a complete cache entry.
        entry = save_raw_port(store, publication) if available else None
        result[_MODULATION] = _run_result(publication, entry, hit=False, parameters=parameters,
                                           freshness="fresh" if available else "unavailable")
    return result
