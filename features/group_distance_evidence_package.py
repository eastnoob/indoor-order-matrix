"""Expose group-distance readings through the shared evidence-package contract.

The distance kernel remains the owner of geometry, route search, and status
semantics.  This module only adapts its immutable pair observations into the
additive ``EvidencePackageOutput`` shape; it does not calculate a second
distance or turn free-space provenance into a third evidence channel.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import nullcontext
from itertools import combinations, pairwise
import json
import math
from pathlib import Path
from typing import Any

from .field_core import (
    EvidenceChannelRecord,
    EvidenceChannelReference,
    EvidenceOutputChannel,
    EvidenceOutputProcessor,
    EvidenceOutputScale,
    EvidencePackage,
    EvidencePackageChannelReference,
    EvidencePackageOutput,
    FieldResultEnvelope,
    FieldResultStatus,
    _json_value,
    build_evidence_package_contract,
    build_field_result_cache_identity,
    fingerprint_evidence_dependency,
    evaluate_evidence_package_freshness,
    serialize_evidence_package_output,
)
from .evidence_package_parameters import ParameterSchema, ParameterSnapshot, ParameterSpec
from . import group_distance as distance_kernel
from .evidence_package_storage import (
    adopt_legacy_store_payload,
    legacy_candidate_contract,
    legacy_processed_cache_key,
    load_processed_entry,
    load_processed_bytes,
    load_raw_entry,
    load_raw_bytes,
    load_bound_store_entry,
    reconstruct_legacy_processed_snapshot,
    save_processed_output,
    save_raw_output,
    serialize_processed_output_bytes,
    serialize_raw_output_bytes,
    processed_cache_key,
)
from .cache_paths import CacheAddress, SourceBinding, resolve_sidecar_path
from .cache_store import CacheStore
from .group_distance import (
    GroupDistanceInput,
    GroupDistanceResult,
    GroupPairDistanceObservation,
    _pair_id,
    calculate_group_pair_distances,
    group_distance_input_fingerprints,
)


PACKAGE_ID = "group-walk-distance"
PACKAGE_SCHEMA = "group-walk-distance/v1"
PRODUCER = "features.group_distance_evidence_package"
OUTPUT_FUNCTION_ID = "group_walk_distance"
OUTPUT_FUNCTION_VERSION = "group-walk-distance-output/2"
SOURCE_CHANNEL = "group_distance_observation"
SOURCE_ALGORITHM_VERSION = "group-distance-source/1"
SOURCE_SCHEMA_VERSION = "group-distance-source/v1"
VISUALIZATION_MANIFEST_SCHEMA = "group-walk-distance-visualization-manifest/v1"

GROUP_DISTANCE_CLEARANCE_SCHEMA = ParameterSchema(
    PACKAGE_ID,
    "group-distance-clearance/1",
    (
        ParameterSpec("min_left_m", float, .225, unit="m", minimum=0.0),
        ParameterSpec("min_right_m", float, .225, unit="m", minimum=0.0),
        ParameterSpec("min_total_m", float, .55, unit="m", minimum=0.0),
    ),
)
GROUP_DISTANCE_PARAMETER_SCHEMA = ParameterSchema(
    PACKAGE_ID,
    "group-distance-parameters/1",
    (
        ParameterSpec("grid", dict, unit="request_context"),
        ParameterSpec("query_context", dict, unit="request_context"),
        ParameterSpec("free_space_result_ref", dict, unit="request_context", nullable=True),
        ParameterSpec("clearance_mode", str, choices=("unconstrained", "constrained")),
        ParameterSpec("clearance_policy", dict, unit="request_context", nullable=True),
    ),
)


def build_group_distance_parameter_snapshot(
    bundle: GroupDistanceInput, *, parameter_sources: Mapping[str, str] | None = None,
) -> ParameterSnapshot:
    """Capture the exact distance input context and opt-in clearance policy."""
    if not isinstance(bundle, GroupDistanceInput):
        raise TypeError("bundle must be a GroupDistanceInput")
    policy = bundle.clearance_policy
    if policy is None:
        mode, policy_value = "unconstrained", None
    else:
        # Constrained repair accepts exactly the owner defaults/keys; no hidden
        # thresholds are inserted into an unconstrained ordinary calculation.
        policy_snapshot = GROUP_DISTANCE_CLEARANCE_SCHEMA.capture_calculated(
            dict(policy), sources={name: "bundle" for name in (
                "min_left_m", "min_right_m", "min_total_m")},
        )
        mode, policy_value = "constrained", dict(policy_snapshot.effective_parameters)
    free_space_ref = None
    if isinstance(bundle.free_space_samples, Mapping):
        free_space_ref = bundle.free_space_samples.get("result_ref")
        if free_space_ref is not None and not isinstance(free_space_ref, Mapping):
            # Legacy fixtures used scalar publication tokens; retain their
            # identity inside a typed mapping without changing the raw contract.
            free_space_ref = {"value": free_space_ref}
    values = {
        "grid": _json_value(bundle.grid),
        "query_context": _json_value(bundle.query_context),
        "free_space_result_ref": _json_value(free_space_ref),
        "clearance_mode": mode,
        "clearance_policy": policy_value,
    }
    source_map = dict(parameter_sources or {})
    resolved_sources = {name: source_map.get(name, "bundle") for name in values}
    return GROUP_DISTANCE_PARAMETER_SCHEMA.resolve(values, sources=resolved_sources)

_DISTANCE_CHANNELS = (
    ("euclidean_distance", "center_to_center_euclidean", "Centroid-to-centroid Euclidean distance"),
    ("path_distance", "centroid_free_space_hybrid", "Centroid offsets plus selected discrete free-space route length"),
)
_STATUS_MAP = {
    "computed": FieldResultStatus.COMPUTED,
    "partial": FieldResultStatus.PARTIAL,
    "unknown": FieldResultStatus.PARTIAL,
    "invalid": FieldResultStatus.INVALID,
    "outside": FieldResultStatus.OUTSIDE,
    "not_available": FieldResultStatus.NOT_AVAILABLE,
    # The kernel uses unreachable for a valid, covered graph with no route.
    # The shared envelope has no unreachable enum, so keep the completed
    # computation status and preserve the exact raw status in the observation.
    "unreachable": FieldResultStatus.COMPUTED,
}


def _as_status(raw_status: Any) -> FieldResultStatus:
    """Map one group-distance status into the shared envelope status set."""
    try:
        return _STATUS_MAP[str(raw_status)]
    except KeyError as exc:
        raise ValueError(f"unsupported group-distance status: {raw_status!r}") from exc


def _status_for_pair(statuses: Iterable[FieldResultStatus]) -> FieldResultStatus:
    """Choose one envelope status while retaining channel-specific statuses."""
    values = tuple(statuses)
    if not values:
        return FieldResultStatus.NOT_EVALUATED
    if any(value is FieldResultStatus.INVALID for value in values):
        return FieldResultStatus.INVALID
    if any(value is FieldResultStatus.AMBIGUOUS for value in values):
        return FieldResultStatus.AMBIGUOUS
    if all(value is FieldResultStatus.OUTSIDE for value in values):
        return FieldResultStatus.OUTSIDE
    if all(value is FieldResultStatus.NOT_AVAILABLE for value in values):
        return FieldResultStatus.NOT_AVAILABLE
    if all(value is FieldResultStatus.COMPUTED for value in values):
        return FieldResultStatus.COMPUTED
    return FieldResultStatus.PARTIAL


def _status_explanation(status: FieldResultStatus, raw: Mapping[str, Any]) -> str:
    """Provide a required explanation for every non-computed shared status."""
    if status is FieldResultStatus.COMPUTED:
        return ""
    reason = raw.get("reason")
    if isinstance(reason, str) and reason.strip():
        return reason
    return f"distance kernel status is {raw.get('status', 'unknown')}"


def _source_ids(observation: Any, bundle: GroupDistanceInput) -> tuple[str, ...]:
    """Collect stable group and geometry source identifiers for one pair."""
    values: set[str] = set()
    if isinstance(observation, Mapping):
        for group_id, audit in (observation.get("geometry_audit") or {}).items():
            values.add(str(group_id))
            if isinstance(audit, Mapping):
                refs = audit.get("source_refs", ())
                if isinstance(refs, (str, bytes)):
                    refs = (refs,)
                if isinstance(refs, Iterable):
                    values.update(str(value) for value in refs)
    for group in bundle.groups:
        if isinstance(observation, Mapping) and group.group_id not in tuple(observation.get("group_ids", ())):
            continue
        values.add(group.group_id)
        refs = group.source_refs
        if isinstance(refs, (str, bytes)):
            refs = (refs,)
        if isinstance(refs, Iterable):
            values.update(str(value) for value in refs)
    if not values:
        values.add("group-distance-input")
    return tuple(sorted(values))


def _free_space_result_ref(result: GroupDistanceResult | Mapping[str, Any], bundle: GroupDistanceInput) -> Any:
    """Bind the retained free-space reference without accepting a foreign audit ref."""
    saved = _result_manifest(result).get("free_space_result") or {}
    if not isinstance(saved, Mapping):
        raise ValueError("distance manifest free_space_result must be a mapping")
    supplied = bundle.free_space_samples or {}
    if not isinstance(supplied, Mapping):
        raise ValueError("input free_space_samples must be a mapping or None")
    saved_ref, supplied_ref = saved.get("result_ref"), supplied.get("result_ref")
    if saved_ref is not None and supplied_ref is not None and saved_ref != supplied_ref:
        raise ValueError("saved distance free-space reference differs from the input bundle")
    return supplied_ref if supplied_ref is not None else saved_ref


def _result_observations(result: GroupDistanceResult | Mapping[str, Any]) -> tuple[Any, ...]:
    """Detach the saved pair sequence and reject malformed record containers."""
    rows = result.observations if isinstance(result, GroupDistanceResult) else result.get("observations", ())
    if isinstance(rows, (str, bytes, Mapping)) or not isinstance(rows, Iterable):
        raise TypeError("result observations must be an iterable of pair records")
    rows = tuple(rows)
    if any(not isinstance(row, (GroupPairDistanceObservation, Mapping)) for row in rows):
        raise ValueError("distance observations must be pair records or mappings")
    return rows


def _dependencies(
    result: GroupDistanceResult | Mapping[str, Any], bundle: GroupDistanceInput,
    *, observations: tuple[Any, ...] | None = None, actual_dependencies: Mapping[str, str] | None = None,
) -> Mapping[str, Any]:
    """Require one consistent saved dependency binding across every pair."""
    manifest = _result_manifest(result)
    dependencies = manifest.get("dependency_fingerprints")
    if dependencies is not None and not isinstance(dependencies, Mapping):
        raise ValueError("distance manifest dependency_fingerprints must be a mapping")
    dependencies = dict(dependencies or {})
    observations = _result_observations(result) if observations is None else observations
    for observation in observations:
        row_dependencies = observation.dependencies if isinstance(observation, GroupPairDistanceObservation) else observation.get("dependencies")
        if not isinstance(row_dependencies, Mapping) or not row_dependencies:
            raise ValueError("every distance pair requires dependency fingerprints")
        if not dependencies:
            dependencies = dict(row_dependencies)
        elif dict(row_dependencies) != dependencies:
            raise ValueError("distance pair dependencies differ from the result binding")
    if not dependencies:
        # An empty scope still binds the actual input used by its unavailable output.
        dependencies = dict(actual_dependencies) if actual_dependencies is not None else group_distance_input_fingerprints(bundle)
    if actual_dependencies is not None and dependencies != dict(actual_dependencies):
        raise ValueError("saved distance dependencies differ from the current input bundle")
    # Numerical versions and retained publication refs affect the meaning of the
    # same raw inputs, so they must also change source-envelope cache identity.
    dependencies["distance_model"] = fingerprint_evidence_dependency({
        **{key: manifest.get(key) for key in (
            "algorithm_version", "schema_version", "edge_support_version", "arithmetic_version",
            "clearance_policy_version")},
        "clearance_policy": manifest.get("clearance_policy", bundle.clearance_policy),
        "free_space_result_ref": _free_space_result_ref(result, bundle),
    })
    if isinstance(result, Mapping) and result.get("schema_version") == "route-repair/2":
        if any(not isinstance(row, Mapping) or not isinstance(row.get("directional_repair"), Mapping)
               for row in observations):
            raise ValueError("repaired_result does not contain directional repair observations")
        retained_ref = result.get("retained_result_ref")
        if retained_ref is not None and not isinstance(retained_ref, Mapping):
            raise ValueError("retained_result_ref must be a mapping")
        # Hash selected evidence one pair at a time. The original baseline route,
        # frontier, and lineage can be hundreds of MB and do not belong in this
        # compact outcome binding; the complete selected witness still participates.
        outcomes = tuple(sorted(
            ((row.get("pair_id"), fingerprint_evidence_dependency({
                "euclidean_distance": row.get("center_to_center_euclidean"),
                "baseline_path_distance": row.get("centroid_free_space_hybrid"),
                "repair": {key: row["directional_repair"].get(key) for key in (
                    "quality", "candidate_distance_m", "method", "exact_witness")},
            })) for row in observations),
            key=lambda item: str(item[0]),
        ))
        dependencies["repair_result"] = fingerprint_evidence_dependency({
            "schema_version": result.get("schema_version"),
            "method": result.get("method"),
            "policy": result.get("policy"),
            "checkpoint_fingerprint": result.get("checkpoint_fingerprint"),
            "pair_outcomes": outcomes,
            "retained_result_sha256": (retained_ref or {}).get("sha256"),
        })
    return dependencies


def _validated_result_scope(
    result: GroupDistanceResult | Mapping[str, Any], bundle: GroupDistanceInput,
    *, actual_dependencies: Mapping[str, str],
) -> tuple[tuple[Any, ...], Mapping[str, Any], set[tuple[str, str]]]:
    """Validate actual dependency content and a unique, canonical saved pair scope."""
    observations = _result_observations(result)
    dependencies = _dependencies(result, bundle, observations=observations, actual_dependencies=actual_dependencies)
    saved_inputs = {key: value for key, value in dependencies.items() if key not in {"repair_result", "distance_model"}}
    if saved_inputs != dict(actual_dependencies):
        raise ValueError("saved distance dependencies differ from the current input bundle")
    if bundle.dependency_fingerprints and dict(bundle.dependency_fingerprints) != dict(actual_dependencies):
        raise ValueError("input bundle dependency fingerprints are stale")
    known_groups = {group.group_id for group in bundle.groups}
    if len(known_groups) != len(bundle.groups):
        raise ValueError("input bundle contains duplicate group identities")
    pair_ids, group_pairs = set(), set()
    for observation in observations:
        ids = observation.group_ids if isinstance(observation, GroupPairDistanceObservation) else observation.get("group_ids", ())
        if isinstance(ids, (str, bytes, Mapping)) or not isinstance(ids, Iterable):
            raise ValueError("distance pair requires two canonical group identities")
        ids = tuple(ids)
        if (len(ids) != 2 or any(not isinstance(group_id, str) or not group_id for group_id in ids)
                or ids != tuple(sorted(set(ids))) or not set(ids).issubset(known_groups)):
            raise ValueError("distance pair contains invalid or foreign group identities")
        pair_id = observation.pair_id if isinstance(observation, GroupPairDistanceObservation) else observation.get("pair_id")
        if pair_id != _pair_id(ids, bundle.source_identity):
            raise ValueError("distance pair_id does not match its groups and source")
        if pair_id in pair_ids or ids in group_pairs:
            raise ValueError("distance result contains duplicate pair identities")
        pair_ids.add(pair_id)
        group_pairs.add(ids)
    expected_ids = _result_manifest(result).get("expected_pair_ids")
    if expected_ids is not None:
        if (isinstance(expected_ids, (str, bytes, Mapping)) or not isinstance(expected_ids, Iterable)):
            raise ValueError("distance manifest expected_pair_ids must be a pair sequence")
        expected_ids = tuple(expected_ids)
        if (any(not isinstance(pair_id, str) for pair_id in expected_ids)
                or len(expected_ids) != len(pair_ids) or set(expected_ids) != pair_ids):
            raise ValueError("distance result pair scope differs from its manifest")
    expected_count = _result_manifest(result).get("expected_pair_count")
    if expected_count is not None and expected_count != len(pair_ids):
        raise ValueError("distance result pair count differs from its manifest")
    return observations, dependencies, group_pairs


def _result_manifest(result: GroupDistanceResult | Mapping[str, Any]) -> Mapping[str, Any]:
    """Read manifest metadata from typed kernel or repaired JSON results."""
    if isinstance(result, GroupDistanceResult):
        return result.manifest
    manifest = result.get("manifest", {}) if isinstance(result, Mapping) else {}
    if isinstance(manifest, Mapping) and manifest:
        return manifest
    if isinstance(result, Mapping):
        return {
            "algorithm_version": result.get("method"),
            "schema_version": result.get("schema_version"),
            "query_context": result.get("query_context"),
            "analysis_plane": result.get("analysis_plane"),
            "dependency_fingerprints": result.get("dependency_fingerprints", {}),
        }
    return {}


def _validate_repair_witness(
    observation: Mapping[str, Any], witness: Mapping[str, Any], cells: tuple[tuple[int, int], ...],
    bundle: GroupDistanceInput, policy: Mapping[str, Any] | None,
) -> None:
    """Check retained clearance records and endpoint bindings without geometry replay."""
    def finite_number(value: Any) -> bool:
        """Recognize finite nonnegative measurements while excluding Boolean values."""
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value) and value >= 0)

    def point(value: Any) -> tuple[float, float]:
        """Read a finite two-dimensional coordinate from a retained endpoint record."""
        if (not isinstance(value, (tuple, list)) or len(value) != 2
                or any(isinstance(number, bool) or not isinstance(number, (int, float))
                       or not math.isfinite(number) for number in value)):
            raise ValueError("verified repair endpoint coordinates must be finite pairs")
        return tuple(value)

    names = ("left", "right", "total")
    if not isinstance(policy, Mapping) or any(not finite_number(policy.get(f"min_{name}_m")) for name in names):
        raise ValueError("verified repair requires a finite nonnegative clearance policy")
    edges, turns = witness.get("edge_witnesses"), witness.get("turn_witnesses")
    if (not isinstance(edges, (tuple, list)) or len(edges) != len(cells) - 1
            or not isinstance(turns, (tuple, list)) or len(turns) != (len(cells) if len(cells) > 1 else 1)):
        raise ValueError("verified repair requires every route edge, internal turn, and endpoint turn witness")
    minimum = witness.get("minimum_m")
    if not isinstance(minimum, Mapping) or any(not finite_number(minimum.get(name)) for name in names):
        raise ValueError("verified repair requires complete finite clearance minima")
    records = tuple(edges) + tuple(turns)
    for record in records:
        if not isinstance(record, Mapping) or any(not finite_number(record.get(f"min_{name}_m")) for name in names):
            raise ValueError("verified repair clearance records require finite nonnegative minima")
        if any(record[f"min_{name}_m"] + 1e-12 < policy[f"min_{name}_m"] for name in names):
            raise ValueError("verified repair clearance witness does not satisfy its policy")
    if any(not math.isclose(minimum[name], min(record[f"min_{name}_m"] for record in records),
                            rel_tol=0, abs_tol=1e-12) for name in names):
        raise ValueError("verified repair aggregate minima differ from its exact records")
    # Current exact records contain positional minima rather than endpoint refs.
    # Their sequence counts bind them to the saved route; validate the retained
    # scalar positions when present without inventing new geometry witnesses.
    for record, (first, second) in zip(edges, pairwise(cells)):
        position = record.get("limiting_position_m")
        if position is not None and (not finite_number(position)
                or position > math.dist(first, second) * bundle.grid.spacing + 1e-12):
            raise ValueError("verified repair edge witness position is outside its route segment")
    for record in turns:
        fraction = record.get("limiting_angle_fraction")
        if fraction is not None and (not finite_number(fraction) or fraction > 1 + 1e-12):
            raise ValueError("verified repair turn witness angle fraction is invalid")
    accesses = (witness["source_access"], witness["target_access"])
    if {access.get("group_id") for access in accesses} != set(observation.get("group_ids", ())):
        raise ValueError("verified repair endpoints do not bind the observed group pair")
    for access, route_cell in zip(accesses, (cells[0], cells[-1])):
        free, footprint = access.get("free_cell"), access.get("footprint_cell")
        if (not isinstance(free, (tuple, list)) or not isinstance(footprint, (tuple, list))
                or len(free) != 2 or len(footprint) != 2
                or any(isinstance(value, bool) or not isinstance(value, int) for value in (*free, *footprint))
                or tuple(free) != route_cell or sum(abs(a - b) for a, b in zip(free, footprint)) != 1):
            raise ValueError("verified repair endpoint cells do not match its route and cardinal interface")
        expected_heading = (free[1] - footprint[1], free[0] - footprint[0])
        for key, direction in (("heading", 1), ("target_heading", -1)):
            if key in access and any(not math.isclose(actual, direction * expected, rel_tol=0, abs_tol=1e-12)
                                     for actual, expected in zip(point(access[key]), expected_heading)):
                raise ValueError("verified repair endpoint heading differs from its cardinal interface")
        access_key = access.get("access_key")
        expected_key = (access["group_id"], footprint, free, access.get("shared_edge"))
        if (not isinstance(access_key, (tuple, list)) or len(access_key) != 4
                or fingerprint_evidence_dependency(access_key) != fingerprint_evidence_dependency(expected_key)):
            raise ValueError("verified repair access_key differs from its endpoint binding")
        center = (bundle.grid.origin[0] + (free[1] + .5) * bundle.grid.spacing,
                  bundle.grid.origin[1] + (free[0] + .5) * bundle.grid.spacing)
        if any(not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
               for actual, expected in zip(point(access.get("cell_center")), center)):
            raise ValueError("verified repair endpoint center differs from its free cell")
        proxy = point(access.get("proxy_point"))
        expected_proxy = (center[0] - expected_heading[0] * bundle.grid.spacing / 2,
                          center[1] - expected_heading[1] * bundle.grid.spacing / 2)
        if any(not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
               for actual, expected in zip(proxy, expected_proxy)):
            raise ValueError("verified repair proxy point differs from its cardinal interface")
        shared = access.get("shared_edge")
        if not isinstance(shared, (tuple, list)) or len(shared) != 2:
            raise ValueError("verified repair requires the retained shared cell edge")
        tangent = (-expected_heading[1], expected_heading[0])
        expected_shared = sorted(tuple(proxy[axis] + sign * tangent[axis] * bundle.grid.spacing / 2
                                       for axis in range(2)) for sign in (-1, 1))
        if any(not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
               for actual_point, expected_point in zip(sorted(point(value) for value in shared), expected_shared)
               for actual, expected in zip(actual_point, expected_point)):
            raise ValueError("verified repair shared edge differs from its cardinal interface")
        audit = (observation.get("geometry_audit") or {}).get(access["group_id"], {})
        centroid = point(audit.get("centroid"))
        expected_offset = math.dist(centroid, proxy) + math.dist(proxy, center)
        if not math.isclose(access["offset"], expected_offset, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("verified repair endpoint offset differs from its saved centroid and interface")


def _repair_path_distance(
    observation: Mapping[str, Any], repair: Mapping[str, Any], bundle: GroupDistanceInput,
    policy: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Measure the saved feasible route without inventing a shortest-path bound."""
    quality = str(repair.get("quality", "unresolved_unknown"))
    candidate = repair.get("candidate_distance_m")
    raw = {
        "status": "unknown", "value": None, "units": "m",
        "reason": f"global repair quality: {quality}", "repair_quality": quality,
        "discrete_approximation": True, "shortest_path_guaranteed": False,
        "optimality_gap_m": None,
    }
    if quality == "exact_route_verified":
        witness = repair.get("exact_witness") or {}
        if not isinstance(witness, Mapping):
            raise ValueError("verified repair requires a retained exact witness mapping")
        source_access = witness.get("source_access") or {}
        target_access = witness.get("target_access") or {}
        raw_cells = witness.get("cell_keys", ())
        if (not isinstance(raw_cells, (tuple, list)) or not raw_cells
                or not isinstance(source_access, Mapping) or not isinstance(target_access, Mapping)
                or "offset" not in source_access or "offset" not in target_access):
            raise ValueError("verified repair requires route cells and both endpoint offsets")
        if any(not isinstance(cell, (tuple, list)) or len(cell) != 2
               or any(isinstance(value, bool) or not isinstance(value, int) for value in cell)
               for cell in raw_cells):
            raise ValueError("verified repair route cells must be integer lattice pairs")
        cells = tuple(tuple(cell) for cell in raw_cells)
        numbers = (candidate, source_access["offset"], target_access["offset"])
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) or value < 0 for value in numbers):
            raise ValueError("verified repair distances must be finite nonnegative numbers")
        source_offset, target_offset = float(numbers[1]), float(numbers[2])
        _validate_repair_witness(observation, witness, cells, bundle, policy)
        # Recompute only the stored polyline length, never search a route here.
        centers = tuple((bundle.grid.origin[0] + (col + .5) * bundle.grid.spacing,
                         bundle.grid.origin[1] + (row + .5) * bundle.grid.spacing)
                        for row, col in cells)
        route_distance = math.fsum(math.dist(first, second) for first, second in pairwise(centers))
        recomposed = math.fsum((source_offset, route_distance, target_offset))
        if not math.isclose(float(candidate), recomposed, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("verified repair distance differs from its stored route and offsets")
        support = set(cells)
        for first, second in pairwise(cells):
            dr, dc = second[0] - first[0], second[1] - first[1]
            if max(abs(dr), abs(dc)) != 1:
                raise ValueError("verified repair contains a non-neighbor route step")
            if dr and dc:
                support.update(((first[0], second[1]), (second[0], first[1])))
        samples = {tuple(cell["cell_key"]): cell
                   for cell in (bundle.free_space_samples or {}).get("cells", ())}
        statuses = []
        for key in support:
            sample = samples.get(key)
            if sample is None or sample.get("status") not in {"established", "conditional"} or sample.get("value") is not False:
                raise ValueError("verified repair requires available free route and diagonal guard cells")
            statuses.append(sample["status"])
        for access in (source_access, target_access):
            sample = samples[tuple(access["free_cell"])]
            if access.get("status") != sample.get("status") or (
                    sample.get("query_ref") is not None and access.get("query_ref") != sample["query_ref"]):
                raise ValueError("verified repair endpoint status or query differs from its free-space sample")
        statuses.extend(access.get("status") for access in (source_access, target_access))
        if any(status not in {"established", "conditional"} for status in statuses):
            raise ValueError("verified repair requires available endpoint access queries")
        status = "partial" if "conditional" in statuses else "computed"
        raw.update(
            status=status,
            value=float(candidate),
            reason="selected discrete route verified; global shortestness is not established",
            source_centroid_to_access_offset=source_offset,
            target_access_to_centroid_offset=target_offset,
            free_space_route_distance=route_distance,
            recomposed_distance=recomposed,
            distance_residual_m=float(candidate) - recomposed,
            conditional_support_cell_count=statuses.count("conditional"),
            route_ref={"source_channel": SOURCE_CHANNEL, "pair_id": observation["pair_id"], "field": "route"},
        )
    elif quality == "infeasible_observed":
        raw.update(status="unreachable", value=None, reason=f"global repair quality: {quality}")
    return raw


def _pair_source_envelope(
    observation: Any,
    result: GroupDistanceResult | Mapping[str, Any],
    bundle: GroupDistanceInput,
    repair: Mapping[str, Any] | None = None,
    dependencies: Mapping[str, Any] | None = None,
    repair_policy: Mapping[str, Any] | None = None,
) -> FieldResultEnvelope:
    """Create one immutable source envelope for one pair observation."""
    serialized = dict(observation) if isinstance(observation, Mapping) else _json_value(observation)
    if repair is not None:
        # Baseline search frontiers and input free-space samples stay in their
        # retained artifacts; keep the selected witness once in this package.
        serialized = {
            **{key: serialized[key] for key in (
                "pair_id", "group_ids", "center_to_center_euclidean", "geometry_audit", "dependencies")},
            "centroid_free_space_hybrid": _repair_path_distance(serialized, repair, bundle, repair_policy),
            "route": repair.get("exact_witness"),
            "baseline_path_reading": serialized["centroid_free_space_hybrid"],
            "repair_diagnostics": {key: value for key, value in repair.items()
                                   if key not in {"exact_witness", "lower_bound_m"}},
            "clearance_policy": repair_policy,
            "retained_result_ref": result.get("retained_result_ref") if isinstance(result, Mapping) else None,
        }
    pair_id = str(serialized["pair_id"])
    target = {"kind": "furniture_group_pair", "id": pair_id, "identity": pair_id}
    dependencies = dependencies if dependencies is not None else _dependencies(result, bundle)
    channel_payloads = tuple(serialized[key] for _, key, _ in _DISTANCE_CHANNELS)
    statuses = tuple(_as_status(payload["status"]) for payload in channel_payloads)
    raw_status = _status_for_pair(statuses)
    source_ids = _source_ids(serialized, bundle)
    manifest = _result_manifest(result)
    free_space_result = manifest.get("free_space_result") or {}
    if not free_space_result and isinstance(bundle.free_space_samples, Mapping):
        free_space_result = {"result_ref": bundle.free_space_samples.get("result_ref")}
    source_fingerprint = str(dependencies.get("source", fingerprint_evidence_dependency(bundle.source_identity)))
    input_fingerprint = fingerprint_evidence_dependency({
        "pair_observation": serialized,
        "dependency_fingerprints": dependencies,
    })
    recipe_fingerprint = fingerprint_evidence_dependency({
        "package_id": PACKAGE_ID,
        "source_channel": SOURCE_CHANNEL,
        "output_channels": tuple(name for name, _, _ in _DISTANCE_CHANNELS),
        "output_version": OUTPUT_FUNCTION_VERSION,
    })
    identity = build_field_result_cache_identity(
        target=target,
        query=bundle.query,
        channel_declarations=({"channel": SOURCE_CHANNEL, "polarity": "descriptive", "units": "m"},),
        input_fingerprint=input_fingerprint,
        source_fingerprint=source_fingerprint,
        recipe_fingerprint=recipe_fingerprint,
        algorithm_version=SOURCE_ALGORITHM_VERSION,
        schema_version=SOURCE_SCHEMA_VERSION,
    )
    record = EvidenceChannelRecord(
        channel=SOURCE_CHANNEL,
        required=True,
        polarity="descriptive",
        observation=serialized,
        units="m",
        status=raw_status,
        source_ids=source_ids,
        provenance={
            "inherits_top_level": True,
            "method": "group_distance_kernel_observation",
            "distance_algorithm_version": manifest.get("algorithm_version"),
            "distance_schema_version": manifest.get("schema_version"),
            "dependency_fingerprints": dependencies,
            "free_space_dependency_fingerprint": dependencies.get("occupancy"),
            "free_space_result_ref": free_space_result.get("result_ref"),
        },
        explanation=(
            "The source observation contains the two raw distance readings."
            if raw_status is FieldResultStatus.COMPUTED
            else "The source observation retains channel-specific distance statuses."
        ),
    )
    provenance = {
        "algorithm_version": SOURCE_ALGORITHM_VERSION,
        "schema_version": SOURCE_SCHEMA_VERSION,
        "method": "group_distance_kernel_observation",
        "distance_algorithm_version": manifest.get("algorithm_version"),
        "distance_schema_version": manifest.get("schema_version"),
        "dependency_fingerprints": dependencies,
        "free_space_dependency_fingerprint": dependencies.get("occupancy"),
        "free_space_result_ref": free_space_result.get("result_ref"),
        "analysis_plane": manifest.get("analysis_plane") or bundle.analysis_plane,
        "query_context": manifest.get("query_context") or bundle.query_context,
    }
    return FieldResultEnvelope(
        target=target,
        query=bundle.query,
        raw_status=raw_status,
        channel_set=(SOURCE_CHANNEL,),
        value={"channels": (record,)},
        source_ids=source_ids,
        provenance=provenance,
        cache_identity=identity,
        explanation=(
            ""
            if raw_status is FieldResultStatus.COMPUTED
            else "Pair distance source retains unavailable, ambiguous, outside, or invalid readings."
        ),
    )


def build_group_distance_source_envelopes(
    result: GroupDistanceResult | Mapping[str, Any],
    bundle: GroupDistanceInput,
    *,
    repaired_result: Mapping[str, Any] | None = None,
) -> tuple[FieldResultEnvelope, ...]:
    """Adapt kernel or saved repair observations into source envelopes.

    ``repaired_result`` is a saved ``global_repair_result`` mapping.  Its
    directional route decisions replace only the path-distance raw channel;
    Euclidean readings and pair scope remain those of the supplied result.
    """
    if not isinstance(result, (GroupDistanceResult, Mapping)):
        raise TypeError("result must be a GroupDistanceResult or result mapping")
    if not isinstance(bundle, GroupDistanceInput):
        raise TypeError("bundle must be a GroupDistanceInput")
    if repaired_result is None and isinstance(result, Mapping) and result.get("schema_version") == "route-repair/2":
        repaired_result = result
    if repaired_result is not None and not isinstance(repaired_result, Mapping):
        raise TypeError("repaired_result must be a saved result mapping")
    # Hash the retained free-space payload once, then share the validated binding
    # across all pair envelopes rather than hashing or scanning it for each pair.
    actual_dependencies = group_distance_input_fingerprints(bundle)
    observations, dependencies, group_pairs = _validated_result_scope(
        result, bundle, actual_dependencies=actual_dependencies,
    )
    repair_by_pair = {}
    if repaired_result is not None:
        if repaired_result.get("schema_version") != "route-repair/2":
            raise ValueError("repaired_result requires the route-repair/2 schema")
        if repaired_result is result:
            repair_rows, repair_dependencies, repair_pairs = observations, dependencies, group_pairs
        else:
            repair_rows, repair_dependencies, repair_pairs = _validated_result_scope(
                repaired_result, bundle, actual_dependencies=actual_dependencies,
            )
        if repair_pairs != group_pairs:
            raise ValueError("repaired_result pair scope does not match distance observations")
        for row in repair_rows:
            ids = tuple(row.get("group_ids", ()))
            repair_by_pair[ids] = row["directional_repair"]
        # A separate repaired result must participate in identity just as the
        # direct saved-result adapter does, while retaining baseline model refs.
        dependencies = {**dependencies, "repair_result": repair_dependencies["repair_result"]}
    envelopes = tuple(
        _pair_source_envelope(
            observation,
            result,
            bundle,
            repair_by_pair.get(tuple(observation.get("group_ids", ())) if isinstance(observation, Mapping)
                               else tuple(observation.group_ids))
            if repaired_result is not None else None,
            dependencies=dependencies,
            repair_policy=repaired_result.get("policy") if repaired_result is not None else None,
        )
        for observation in observations
    )
    identities = [envelope.target["identity"] for envelope in envelopes]
    if len(set(identities)) != len(identities):
        raise ValueError("distance result contains duplicate pair identities")
    return tuple(sorted(envelopes, key=lambda item: item.target["identity"]))


def _empty_scope_source_envelope(
    result: GroupDistanceResult | Mapping[str, Any],
    bundle: GroupDistanceInput,
) -> FieldResultEnvelope:
    """Represent an empty pair scope as an explicit unavailable package target."""
    dependencies = _dependencies(result, bundle)
    target_id = "empty-scope:" + fingerprint_evidence_dependency({"groups": (), "dependencies": dependencies})[:24]
    target = {"kind": "furniture_group_pair_scope", "id": target_id, "identity": target_id}
    raw = {
        "pair_id": target_id,
        "group_ids": (),
        "center_to_center_euclidean": {
            "status": "not_available",
            "value": None,
            "units": "m",
            "reason": "distance package has no target group pairs",
        },
        "centroid_free_space_hybrid": {
            "status": "not_available",
            "value": None,
            "units": "m",
            "reason": "distance package has no target group pairs",
        },
        "geometry_audit": {},
        "route": None,
        "lineage": {},
        "dependencies": dependencies,
    }
    identity = build_field_result_cache_identity(
        target=target,
        query=bundle.query,
        channel_declarations=({"channel": SOURCE_CHANNEL, "polarity": "descriptive", "units": "m"},),
        input_fingerprint=fingerprint_evidence_dependency(raw),
        source_fingerprint=str(dependencies.get("source", fingerprint_evidence_dependency(bundle.source_identity))),
        recipe_fingerprint=fingerprint_evidence_dependency({"package_id": PACKAGE_ID, "empty_scope": True}),
        algorithm_version=SOURCE_ALGORITHM_VERSION,
        schema_version=SOURCE_SCHEMA_VERSION,
    )
    record = EvidenceChannelRecord(
        channel=SOURCE_CHANNEL,
        required=True,
        polarity="descriptive",
        observation=raw,
        units="m",
        status=FieldResultStatus.NOT_AVAILABLE,
        source_ids=("group-distance-input",),
        provenance={"inherits_top_level": True, "method": "empty_group_distance_scope", "dependency_fingerprints": dependencies},
        explanation="distance package has no target group pairs",
    )
    return FieldResultEnvelope(
        target=target,
        query=bundle.query,
        raw_status=FieldResultStatus.NOT_AVAILABLE,
        channel_set=(SOURCE_CHANNEL,),
        value={"channels": (record,)},
        source_ids=("group-distance-input",),
        provenance={"algorithm_version": SOURCE_ALGORITHM_VERSION, "schema_version": SOURCE_SCHEMA_VERSION,
                    "method": "empty_group_distance_scope", "dependency_fingerprints": dependencies},
        cache_identity=identity,
        explanation="distance package has no target group pairs",
    )


def _output_status(raw: Mapping[str, Any]) -> FieldResultStatus:
    """Map a raw kernel channel status for an additive package output."""
    return _as_status(raw.get("status"))


def _output_records(source_envelopes: tuple[FieldResultEnvelope, ...]) -> tuple[EvidenceOutputChannel, ...]:
    """Project exactly the two declared distance readings from source envelopes."""
    outputs = []
    for envelope in source_envelopes:
        record = next(item for item in envelope.value["channels"] if item.channel == SOURCE_CHANNEL)
        observation = record.observation
        lineage = (EvidenceChannelReference.from_envelope(envelope, SOURCE_CHANNEL),)
        for channel, raw_key, meaning in _DISTANCE_CHANNELS:
            raw = observation[raw_key]
            status = _output_status(raw)
            outputs.append(
                EvidenceOutputChannel(
                    target=envelope.target,
                    channel=channel,
                    observation={
                        "value": raw.get("value"),
                        "units": raw.get("units", "m"),
                        "raw_status": raw.get("status"),
                        "pair_id": observation["pair_id"],
                        "group_ids": observation["group_ids"],
                        "distance": raw,
                    },
                    status=status,
                    scale=EvidenceOutputScale(
                        meaning=meaning,
                        units="m",
                        normalization_method="identity; raw metric distance",
                    ),
                    derived_from=lineage,
                    source_ids=record.source_ids,
                    provenance={
                        "method": "group_distance_evidence_package",
                        "algorithm_version": OUTPUT_FUNCTION_VERSION,
                        "schema_version": PACKAGE_SCHEMA,
                        "raw_distance_status": raw.get("status"),
                        "distance_algorithm_version": envelope.provenance.get("distance_algorithm_version"),
                        "distance_schema_version": envelope.provenance.get("distance_schema_version"),
                        "dependency_fingerprints": envelope.provenance.get("dependency_fingerprints", {}),
                        "free_space_dependency_fingerprint": envelope.provenance.get("free_space_dependency_fingerprint"),
                        "free_space_result_ref": envelope.provenance.get("free_space_result_ref"),
                        "analysis_plane": envelope.provenance.get("analysis_plane"),
                        "query_context": envelope.provenance.get("query_context"),
                    },
                    explanation=_status_explanation(status, raw),
                )
            )
    return tuple(outputs)


def build_group_distance_evidence_package(*, output_processor: EvidenceOutputProcessor | None = None) -> EvidencePackage:
    """Return raw distance publication with explicitly optional runtime processing."""
    return EvidencePackage(
        package_id=PACKAGE_ID,
        output_function_id=OUTPUT_FUNCTION_ID,
        output_function_version=OUTPUT_FUNCTION_VERSION,
        output_function=_output_records,
        output_processor=output_processor,
    )


def _euclidean_proximity_scope(
    raw: EvidencePackageOutput, parameters: Mapping[str, Any],
) -> tuple[tuple[EvidenceOutputChannel, ...], list[float], tuple[EvidencePackageChannelReference, ...], tuple[str, ...]]:
    """Validate one complete metre scope and retain its shared raw-channel lineage."""
    expected = parameters["expected_target_ids"]
    members = tuple(item for item in raw.outputs if item.channel == "euclidean_distance")
    identities = tuple(item.target["identity"] for item in members)
    if not members:
        raise ValueError("the complete Euclidean scope has no distance gradient: no members")
    if len(identities) != len(expected) or set(identities) != set(expected):
        raise ValueError("Euclidean members must match the complete declared target scope exactly")
    values = []
    for item in members:
        observation = item.observation
        if (item.status is not FieldResultStatus.COMPUTED or not isinstance(observation, Mapping)
                or observation.get("raw_status") != "computed" or observation.get("units") != "m"
                or item.scale.units != "m"):
            raise ValueError("every Euclidean scope member must be computed in metres")
        value = observation.get("value")
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValueError("every Euclidean scope value must be finite and nonnegative")
        values.append(value)
    raw_identity = raw.output_identity
    # Every output depends on every member of the common ruler, including its own distance.
    lineage = tuple(EvidencePackageChannelReference(raw.package_id, raw_identity, identity, "euclidean_distance")
                    for identity in sorted(identities))
    source_ids = tuple(sorted({identity for item in members for identity in item.source_ids}))
    return members, values, lineage, source_ids


def _median_euclidean_proximity(
    raw: EvidencePackageOutput, parameters: Mapping[str, Any],
) -> tuple[EvidenceOutputChannel, ...]:
    """Transform the complete declared Euclidean scope using one common median."""
    members, values, lineage, source_ids = _euclidean_proximity_scope(raw, parameters)
    ordered = sorted(values)
    middle = len(ordered) // 2
    # This nonnegative midpoint avoids overflow without filtering inputs or adding epsilon.
    median = (ordered[middle] if len(ordered) % 2 else
              ordered[middle - 1] + (ordered[middle] - ordered[middle - 1]) / 2)
    if not math.isfinite(median) or median <= 0:
        raise ValueError("the complete Euclidean scope median must be finite and positive")
    scale = EvidenceOutputScale(
        meaning="Scope-relative Euclidean proximity; larger is closer",
        scale_id="euclidean-median-relative-proximity/1", units="dimensionless",
        normalization_method="n=m/(m+d); m=median of complete declared Euclidean target scope",
        value_range=(0, 1), endpoint_meanings=("infinite-distance limit", "zero Euclidean distance"),
    )
    outputs = []
    for item, distance in zip(members, values):
        denominator = median + distance
        # The scaled equivalent retains the same ratio when two finite metres overflow on addition.
        proximity = (median / denominator if math.isfinite(denominator) else
                     (median / 2) / (median / 2 + distance / 2))
        outputs.append(EvidenceOutputChannel(
            target=item.target, channel="euclidean_relative_proximity", observation=proximity,
            status=FieldResultStatus.COMPUTED, scale=scale, derived_from=lineage, source_ids=source_ids,
            provenance={"method": "euclidean_median_relative_proximity",
                        "algorithm_version": "euclidean-median-relative-proximity/1",
                        "median_distance_m": median, "scope_pair_count": len(members)},
            explanation="Experimental scope-relative proximity; changing scope can change every value.",
        ))
    return tuple(outputs)


def _proximity_target_scope(expected_target_ids: Iterable[str]) -> tuple[str, ...]:
    """Require an explicit nonempty set of distinct target identities for either ruler."""
    if isinstance(expected_target_ids, (str, bytes, Mapping)) or not isinstance(expected_target_ids, Iterable):
        raise ValueError("expected_target_ids must be a nonempty unique target-ID sequence")
    scope = tuple(expected_target_ids)
    if (not scope or any(not isinstance(identity, str) or not identity.strip() for identity in scope)
            or len(set(scope)) != len(scope)):
        raise ValueError("expected_target_ids must be a nonempty unique target-ID sequence")
    return tuple(sorted(scope))


def build_euclidean_median_proximity_processor(*, expected_target_ids: Iterable[str]) -> EvidenceOutputProcessor:
    """Explicitly opt into an experimental pure-distance, complete-scope ruler."""
    return EvidenceOutputProcessor(
        function_id="euclidean_median_relative_proximity", version="euclidean-median-relative-proximity/1",
        function=_median_euclidean_proximity, parameters={"expected_target_ids": _proximity_target_scope(expected_target_ids)},
    )


def _linear_euclidean_proximity(
    raw: EvidencePackageOutput, parameters: Mapping[str, Any],
) -> tuple[EvidenceOutputChannel, ...]:
    """Apply the fixed trial floor using the observed extrema of the complete scope."""
    members, values, lineage, source_ids = _euclidean_proximity_scope(raw, parameters)
    d_min, d_max = min(values), max(values)
    if d_min == d_max:
        raise ValueError("the complete Euclidean scope has no distance gradient: minimum equals maximum")
    scale = EvidenceOutputScale(
        meaning="Scope-relative linear Euclidean proximity; larger is closer; fixed trial floor 0.01",
        scale_id="euclidean-linear-relative-proximity/1", units="dimensionless",
        normalization_method="s(d)=0.01+0.99*(d_max-d)/(d_max-d_min); complete declared Euclidean target scope",
        value_range=(0, 1), endpoint_meanings=("unused below trial floor 0.01", "nearest observed scope distance"),
    )
    # The common extrema preserve distance-gap ratios; a flat scope has no inferable gradient.
    return tuple(EvidenceOutputChannel(
        target=item.target, channel="euclidean_linear_relative_proximity",
        observation=0.01 + 0.99 * (d_max - distance) / (d_max - d_min),
        status=FieldResultStatus.COMPUTED, scale=scale, derived_from=lineage, source_ids=source_ids,
        provenance={"method": "euclidean_linear_relative_proximity",
                    "algorithm_version": "euclidean-linear-relative-proximity/1",
                    "minimum_distance_m": d_min, "maximum_distance_m": d_max,
                    "floor": 0.01, "scope_pair_count": len(members)},
        explanation="Experimental scope-relative linear proximity; extrema and the chosen 0.01 floor define the ruler.",
    ) for item, distance in zip(members, values))


def build_euclidean_linear_proximity_processor(*, expected_target_ids: Iterable[str]) -> EvidenceOutputProcessor:
    """Explicitly opt into the fixed 0.01-floor linear complete-scope experiment."""
    return EvidenceOutputProcessor(
        function_id="euclidean_linear_relative_proximity", version="euclidean-linear-relative-proximity/1",
        function=_linear_euclidean_proximity,
        parameters={"expected_target_ids": _proximity_target_scope(expected_target_ids), "floor": 0.01},
    )


def _symmetric_reciprocal_euclidean_proximity(
    raw: EvidencePackageOutput, parameters: Mapping[str, Any],
) -> tuple[EvidenceOutputChannel, ...]:
    """Normalize the retained reciprocal between symmetric observed endpoint margins."""
    members, values, lineage, source_ids = _euclidean_proximity_scope(raw, parameters)
    ordered = sorted(values)
    minimum, maximum = ordered[0], ordered[-1]
    middle = len(ordered) // 2
    # The nonnegative midpoint preserves the common median without overflowing its sum.
    median = (ordered[middle] if len(ordered) % 2 else
              ordered[middle - 1] + (ordered[middle] - ordered[middle - 1]) / 2)
    if minimum == maximum or median <= 0:
        raise ValueError("the symmetric reciprocal requires a positive median and nonconstant scope")
    numerator = median + minimum
    denominators = [median + distance for distance in values]
    if not math.isfinite(numerator) or any(not math.isfinite(value) for value in denominators):
        raise ValueError("symmetric reciprocal arithmetic is not representable")
    epsilon = parameters["epsilon"]
    # This equivalent form avoids subtracting almost-equal reciprocal values at the endpoints.
    proximities = [epsilon + (1 - 2 * epsilon) * ((maximum - distance) / (maximum - minimum))
                   * (numerator / denominator) for distance, denominator in zip(values, denominators)]
    distinct = sorted(set(zip(values, proximities)))
    if (any(not math.isfinite(value) or not 0 < value < 1 for value in proximities)
            or any(first[1] <= second[1] for first, second in pairwise(distinct))):
        raise ValueError("symmetric reciprocal bounds or distance ordering are not representable")
    scale = EvidenceOutputScale(
        meaning="Scope-relative symmetric reciprocal Euclidean proximity; larger is closer; endpoints 0.99/0.01",
        scale_id="euclidean-symmetric-reciprocal-relative-proximity/1", units="dimensionless",
        normalization_method="s=0.01+0.98*((b-d)/(b-a))*((m+a)/(m+d)); a=min(D), b=max(D), m=median(D)",
        value_range=(0, 1), endpoint_meanings=("unused below trial margin 0.01", "unused above trial margin 0.99"),
    )
    return tuple(EvidenceOutputChannel(
        target=item.target, channel="euclidean_symmetric_reciprocal_relative_proximity", observation=proximity,
        status=FieldResultStatus.COMPUTED, scale=scale, derived_from=lineage, source_ids=source_ids,
        provenance={"method": "euclidean_symmetric_reciprocal_relative_proximity",
                    "algorithm_version": "euclidean-symmetric-reciprocal-relative-proximity/1",
                    "minimum_distance_m": minimum, "maximum_distance_m": maximum,
                    "median_distance_m": median, "epsilon": epsilon, "scope_pair_count": len(members)},
        explanation="Experimental scope-relative endpoint-normalized reciprocal; changing scope requires reprocessing.",
    ) for item, proximity in zip(members, proximities))


def build_euclidean_symmetric_reciprocal_proximity_processor(
    *, expected_target_ids: Iterable[str],
) -> EvidenceOutputProcessor:
    """Explicitly opt into the fixed 0.01/0.99 symmetric reciprocal scope trial."""
    return EvidenceOutputProcessor(
        function_id="euclidean_symmetric_reciprocal_relative_proximity",
        version="euclidean-symmetric-reciprocal-relative-proximity/1",
        function=_symmetric_reciprocal_euclidean_proximity,
        parameters={"expected_target_ids": _proximity_target_scope(expected_target_ids), "epsilon": 0.01},
    )


def evaluate_group_distance_package(
    bundle: GroupDistanceInput,
    *,
    repaired_result: Mapping[str, Any] | None = None,
) -> EvidencePackageOutput:
    """Evaluate ordinary distances or adapt a saved global repair result.

    Supplying ``repaired_result`` is an output-adapter path: the ordinary
    distance kernel is not called, so a saved 666-pair repair run can be
    published without repeating graph construction or route search.
    """
    if not isinstance(bundle, GroupDistanceInput):
        raise TypeError("bundle must be a GroupDistanceInput")
    if repaired_result is None:
        result: GroupDistanceResult | Mapping[str, Any] = calculate_group_pair_distances(bundle)
    elif not isinstance(repaired_result, Mapping):
        raise TypeError("repaired_result must be a saved result mapping")
    else:
        result = repaired_result
    sources = build_group_distance_source_envelopes(
        result,
        bundle,
        repaired_result=repaired_result,
    )
    if not sources:
        sources = (_empty_scope_source_envelope(result, bundle),)
    return build_group_distance_evidence_package().evaluate(sources)


def _run_contract(bundle, repaired_result, *, parameter_sources=None):
    """Return the current contract and actual input fingerprints before any kernel work."""
    if not isinstance(bundle, GroupDistanceInput):
        raise TypeError("bundle must be a GroupDistanceInput")
    inputs = group_distance_input_fingerprints(bundle)
    if bundle.dependency_fingerprints and dict(bundle.dependency_fingerprints) != inputs:
        raise ValueError("input bundle dependency fingerprints are stale")
    groups = tuple(sorted(group.group_id for group in bundle.groups))
    if len(groups) != len(set(groups)):
        raise ValueError("input bundle contains duplicate group identities")
    if repaired_result is not None:
        if not isinstance(repaired_result, Mapping):
            raise TypeError("repaired_result must be a saved result mapping")
        # Preserve the existing saved-result trust boundary before admitting a hit.
        saved_contract = build_group_distance_package_contract(repaired_result, bundle)
    recipe = {"function": OUTPUT_FUNCTION_ID, "function_version": OUTPUT_FUNCTION_VERSION,
              "source_algorithm": SOURCE_ALGORITHM_VERSION, "source_schema": SOURCE_SCHEMA_VERSION,
              "kernel_versions": {name: getattr(distance_kernel, name) for name in (
                  "ALGORITHM_VERSION", "SCHEMA_VERSION", "EDGE_SUPPORT_VERSION", "ARITHMETIC_VERSION",
                  "CLEARANCE_ALGORITHM_VERSION", "CLEARANCE_SCHEMA_VERSION", "CLEARANCE_EDGE_SUPPORT_VERSION",
                  "CLEARANCE_POLICY_VERSION")},
              "networkx_version": distance_kernel.nx.__version__,
              "shapely_version": distance_kernel.shapely.__version__}
    dependencies = {"scene": inputs["source"], "model": inputs["groups"],
        "source": fingerprint_evidence_dependency({"inputs": inputs, "repaired_result": repaired_result}),
        "plane": inputs["analysis_plane"], "query": inputs["query"],
        "recipe": fingerprint_evidence_dependency(recipe),
        "channels": fingerprint_evidence_dependency(tuple(name for name, _, _ in _DISTANCE_CHANNELS))}
    # An accepted saved repair may publish a subset, including an empty-scope
    # diagnostic. Its already-validated contract owns those actual target IDs.
    targets = (tuple(saved_contract["target_ids"]) if repaired_result is not None else
               tuple(_pair_id(ids, bundle.source_identity) for ids in combinations(groups, 2)))
    if not targets:
        constrained = bundle.clearance_policy is not None
        manifest = {"algorithm_version": distance_kernel.CLEARANCE_ALGORITHM_VERSION if constrained else distance_kernel.ALGORITHM_VERSION,
            "schema_version": distance_kernel.CLEARANCE_SCHEMA_VERSION if constrained else distance_kernel.SCHEMA_VERSION,
            "edge_support_version": distance_kernel.CLEARANCE_EDGE_SUPPORT_VERSION if constrained else distance_kernel.EDGE_SUPPORT_VERSION,
            "arithmetic_version": distance_kernel.ARITHMETIC_VERSION, "dependency_fingerprints": inputs}
        if constrained:
            manifest.update(clearance_policy_version=distance_kernel.CLEARANCE_POLICY_VERSION, clearance_policy=bundle.clearance_policy)
        empty_dependencies = _dependencies(repaired_result if repaired_result is not None else {"manifest": manifest}, bundle)
        targets = ("empty-scope:" + fingerprint_evidence_dependency({"groups": (), "dependencies": empty_dependencies})[:24],)
    parameter_snapshot = build_group_distance_parameter_snapshot(
        bundle, parameter_sources=parameter_sources,
    )
    return build_evidence_package_contract(package_id=PACKAGE_ID, package_schema=PACKAGE_SCHEMA,
        producer=PRODUCER, target_ids=targets, dependencies=dependencies,
        algorithm_version=OUTPUT_FUNCTION_VERSION, schema_version=PACKAGE_SCHEMA,
        parameter_snapshot=parameter_snapshot), inputs


def _cached_sources_match(raw, bundle, inputs, targets):
    """Cross-check retained source bindings independently of a receipt's claimed contract."""
    if ({source.target["identity"] for source in raw.source_envelopes} != set(targets)
            or {output.target["identity"] for output in raw.outputs} != set(targets)):
        return False
    for source in raw.source_envelopes:
        dependencies = source.provenance.get("dependency_fingerprints")
        if (source.query != bundle.query or source.channel_set != (SOURCE_CHANNEL,)
                or not isinstance(dependencies, Mapping)
                or any(dependencies.get(name) != value for name, value in inputs.items())
                or source.provenance.get("algorithm_version") != SOURCE_ALGORITHM_VERSION
                or source.provenance.get("schema_version") != SOURCE_SCHEMA_VERSION):
            return False
    return True


def reconstruct_legacy_group_distance_contract(receipt, current_contract, bundle, *, parameter_sources=None):
    """Rebuild typed distance evidence from the validated current bundle context."""
    if not isinstance(receipt, Mapping) or not isinstance(current_contract, Mapping):
        return None
    try:
        snapshot = build_group_distance_parameter_snapshot(
            bundle, parameter_sources=parameter_sources,
        )
        return build_evidence_package_contract(
            package_id=receipt["contract"]["package_id"],
            package_schema=receipt["contract"]["package_schema"],
            producer=receipt["contract"]["producer"],
            target_ids=receipt["contract"]["target_ids"],
            dependencies=receipt["contract"]["dependencies"],
            algorithm_version=receipt["contract"]["algorithm_version"],
            schema_version=receipt["contract"]["schema_version"],
            artifacts=receipt["contract"].get("artifacts", {}),
            parameter_snapshot=snapshot,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _distance_cache_root(cache_directory, model_path, temporary_cache_root):
    """Resolve explicit, model-side, or temporary storage without changing identities."""
    if cache_directory is not None:
        return Path(cache_directory)
    if model_path is not None:
        return resolve_sidecar_path(Path(model_path))
    if temporary_cache_root is not None:
        return Path(temporary_cache_root)
    return None


def _distance_store_lock(store, address):
    """Use the shared identity lock when the optional model-side store is active."""
    if store is None:
        return nullcontext()
    lock = getattr(store, "identity_lock", None)
    return nullcontext() if lock is None else lock(address)


def _distance_dependency_fingerprint(contract, name):
    """Read one normalized dependency fingerprint from the package contract."""
    for dependency in contract["dependencies"]:
        if dependency["name"] == name:
            return dependency["fingerprint"]
    raise KeyError(f"missing package dependency: {name}")


def _distance_bind_source(store, contract, *, model_path, cache_root):
    """Record the verified source namespace while allowing its display locator to move."""
    if store is None:
        return
    source_fingerprint = _distance_source_fingerprint(contract)
    locator = str(Path(model_path).resolve()) if model_path is not None else str(Path(cache_root).resolve())
    store.put_source_binding(SourceBinding(
        source_fingerprint=source_fingerprint,
        canonical_source_identity=f"evidence-source:{source_fingerprint}",
        content_fingerprint=source_fingerprint,
        external_dependencies={},
        current_locator=locator,
    ))


def _distance_source_fingerprint(contract):
    """Keep request parameters out of the factual scene and group namespace."""
    # The historical `source` contract dependency also includes query and repair inputs.
    return fingerprint_evidence_dependency({
        name: _distance_dependency_fingerprint(contract, name) for name in ("scene", "model")
    })


def _distance_raw_validator(package, contract, legacy_adopter=None):
    """Validate Store payloads through the unchanged package receipt codec."""
    def validate(payload, context):
        """Reject bytes that do not pass current package and parameter admission."""
        if load_raw_bytes(payload, cache_key=context.address.identity, contract=contract,
                          package=package, legacy_adopter=legacy_adopter) is None:
            raise ValueError("stored distance receipt is not a current package hit")
    return validate


def _distance_processed_validator(raw, processor):
    """Validate processed Store payloads against the current raw and processor identity."""
    def validate(payload, _context):
        """Reject stale, malformed, or processor-mismatched bytes."""
        if load_processed_bytes(payload, raw_output=raw, processor=processor,
                                legacy_processed_adopter=reconstruct_legacy_processed_snapshot) is None:
            raise ValueError("stored processed distance receipt is not a current hit")
    return validate


def run_group_distance_package(bundle, *, repaired_result=None, cache_directory=None,
                               model_path: Path | None = None,
                               temporary_cache_root: Path | None = None,
                               output_processor=None, parameter_sources=None):
    """Own distance computation and independently cached optional processed results."""
    package = build_group_distance_evidence_package(output_processor=output_processor)
    contract, inputs = _run_contract(
        bundle, repaired_result, parameter_sources=parameter_sources,
    )
    cache_key = contract["package_identity"]
    cache_root = _distance_cache_root(cache_directory, model_path, temporary_cache_root)
    # Locator context opts into Store semantics even when the caller overrides its root.
    store_enabled = model_path is not None or temporary_cache_root is not None
    store = None if cache_root is None or not store_enabled else CacheStore(cache_root)
    _distance_bind_source(store, contract, model_path=model_path, cache_root=cache_root)
    path = None if cache_root is None else cache_root / (cache_key + ".json")
    legacy_path = None
    if path is not None:
        legacy_key = legacy_candidate_contract(contract)["package_identity"]
        if legacy_key != cache_key:
            legacy_path = path.parent / (legacy_key + ".json")
    adopter = lambda receipt, wanted: reconstruct_legacy_group_distance_contract(
        receipt, wanted, bundle, parameter_sources=parameter_sources,
    )
    raw_address = None if store is None else CacheAddress(
        _distance_source_fingerprint(contract), PACKAGE_ID,
        "combined", "raw", cache_key,
    )
    with _distance_store_lock(store, raw_address) if raw_address is not None else nullcontext():
        lookup = None
        store_reuse_origin = None
        loaded_path = None
        raw_storage_address = raw_address
        if path is not None:
            # Prefer a valid old flat receipt when present for compatibility callers.
            lookup = load_raw_entry(path, cache_key=cache_key, contract=contract, package=package)
            if lookup is not None:
                loaded_path = path
            if lookup is None and legacy_path is not None:
                lookup = load_raw_entry(
                    legacy_path, cache_key=legacy_path.stem, contract=contract,
                    package=package, legacy_adopter=adopter,
                )
                if lookup is not None:
                    loaded_path = legacy_path
            if lookup is None and store is not None:
                entry = load_bound_store_entry(
                    store, raw_address, validator=_distance_raw_validator(package, contract, adopter),
                    profile="evidence-package-raw/v1",
                )
                if entry is not None:
                    store_reuse_origin = entry.reuse_origin
                    raw_storage_address = entry.address
                    lookup = load_raw_bytes(
                        entry.payload_paths[0].read_bytes(), cache_key=entry.address.identity,
                        contract=contract, package=package, legacy_adopter=adopter,
                    )
        raw = None if lookup is None else lookup.raw_output
        if raw is not None and not _cached_sources_match(raw, bundle, inputs, contract["target_ids"]):
            lookup = None
            raw = None
        if lookup is not None and store is not None and loaded_path is not None:
            entry = adopt_legacy_store_payload(
                store, raw_address, original_identity=loaded_path.stem,
                payload=loaded_path.read_bytes(), contract=lookup.cached_contract,
                payload_format="evidence-package-cache/v1",
                validator=_distance_raw_validator(package, contract, adopter),
                profile="evidence-package-raw/v1",
            )
            raw_storage_address = entry.address
            store_reuse_origin = entry.reuse_origin
        hit = lookup is not None
        cache_status = evaluate_evidence_package_freshness(
            cached_contract=None if lookup is None else lookup.cached_contract,
            current_contract=contract,
        )
        if lookup is not None:
            cache_status["parameter_status"] = dict(lookup.parameter_status)
            cache_status["reuse_origin"] = dict(lookup.reuse_origin)
        cache_reuse = "exact_hit" if hit else "computed"
        if store_reuse_origin == "migrated":
            cache_reuse = "migrated_reuse"
        if store_reuse_origin != "migrated" and (store_reuse_origin == "legacy_adopted"
                or lookup is not None and lookup.reuse_origin.get("mode") == "adopted_legacy"):
            cache_reuse = "legacy_adopted"
        if raw is None:
            raw = evaluate_group_distance_package(bundle, repaired_result=repaired_result)
            if path is not None:
                payload = serialize_raw_output_bytes(
                    cache_key=cache_key, contract=contract, raw_output=raw,
                )
                if store is not None:
                    store.put(raw_address, contract=contract, payload=payload,
                              payload_format="evidence-package-cache/v1",
                              validator=_distance_raw_validator(package, contract))
                if not store_enabled:
                    save_raw_output(path, cache_key=cache_key, contract=contract, raw_output=raw)
        processed_path = (None if path is None or output_processor is None else
                          path.parent / ("processed-" + processed_cache_key(raw, output_processor) + ".json"))
        processed_legacy_path = None
        processed_identity = None
        processed_address = None
        if processed_path is not None and output_processor is not None:
            processed_identity = processed_cache_key(raw, output_processor)
            old_key = legacy_processed_cache_key(raw, output_processor)
            if old_key != processed_identity:
                processed_legacy_path = processed_path.parent / ("processed-" + old_key + ".json")
            if store is not None:
                processed_address = CacheAddress(
                    _distance_source_fingerprint(contract), PACKAGE_ID,
                    "combined", "processed",
                    processed_identity,
                )
        processed_lookup = None if processed_path is None else load_processed_entry(
            processed_path, raw_output=raw, processor=output_processor,
            legacy_path=processed_legacy_path,
            legacy_processed_adopter=reconstruct_legacy_processed_snapshot,
        )
        if processed_lookup is not None and processed_address is not None:
            saved_path = processed_path if processed_path.exists() else processed_legacy_path
            payload = saved_path.read_bytes()
            adopt_legacy_store_payload(
                store, processed_address, original_identity=json.loads(payload)["processing_identity"],
                payload=payload, contract={"processing_identity": processed_identity},
                payload_format="evidence-package-processed/v1",
                validator=_distance_processed_validator(raw, output_processor),
                profile="evidence-package-processed/v1", upstream_refs=(raw_storage_address,),
            )
        if processed_lookup is None and processed_address is not None:
            entry = load_bound_store_entry(
                store, processed_address,
                validator=_distance_processed_validator(raw, output_processor),
                profile="evidence-package-processed/v1",
            )
            if entry is not None:
                processed_lookup = load_processed_bytes(
                    entry.payload_paths[0].read_bytes(), raw_output=raw,
                    processor=output_processor,
                    legacy_processed_adopter=reconstruct_legacy_processed_snapshot,
                )
        processed = None if processed_lookup is None else processed_lookup.processed_output
        if processed_lookup is None:
            processed = package.process_output(raw, package_freshness="fresh")
            if processed_path is not None:
                payload = serialize_processed_output_bytes(processed)
                if payload is not None:
                    if store is not None:
                        store.put(
                            processed_address,
                            contract={"raw_output_identity": raw.output_identity,
                                      "processing_identity": processed_identity,
                                      "processor_id": output_processor.function_id,
                                      "processor_version": output_processor.version},
                            payload=payload, payload_format="evidence-package-processed/v1",
                            validator=_distance_processed_validator(raw, output_processor),
                            upstream_refs=(raw_storage_address,),
                        )
                    if not store_enabled:
                        save_processed_output(processed_path, processed)
        if processed_lookup is not None:
            cache_status["processed_parameter_status"] = (
                None if processed_lookup.parameter_status is None else dict(processed_lookup.parameter_status))
            cache_status["processed_reuse_origin"] = dict(processed_lookup.reuse_origin)
        result = {"raw_output": raw, "processed_output": processed, "contract": contract,
                  "status": evaluate_evidence_package_freshness(cached_contract=contract, current_contract=contract),
                  "cache_key": cache_key, "cache_hit": hit, "cache_status": cache_status}
        if store_enabled:
            result.update(cache_reuse=cache_reuse, cache_location=str(Path(cache_root).resolve()))
        return result


def serialize_group_distance_package_output(result: EvidencePackageOutput) -> dict[str, Any]:
    """Serialize the additive package output using the shared JSON contract."""
    if not isinstance(result, EvidencePackageOutput):
        raise TypeError("result must be an EvidencePackageOutput")
    return serialize_evidence_package_output(result)


def build_group_distance_package_contract(
    result: GroupDistanceResult | Mapping[str, Any],
    bundle: GroupDistanceInput,
    *,
    visualization_manifest: Mapping[str, Any] | None = None,
    parameter_snapshot: ParameterSnapshot | None = None,
) -> dict[str, Any]:
    """Declare package dependencies and stable output channels for one result."""
    if not isinstance(result, (GroupDistanceResult, Mapping)):
        raise TypeError("result must be a GroupDistanceResult or result mapping")
    if not isinstance(bundle, GroupDistanceInput):
        raise TypeError("bundle must be a GroupDistanceInput")
    if parameter_snapshot is None:
        parameter_snapshot = build_group_distance_parameter_snapshot(bundle)
    actual_dependencies = group_distance_input_fingerprints(bundle)
    observations, dependencies, _ = _validated_result_scope(
        result, bundle, actual_dependencies=actual_dependencies,
    )
    recipe = fingerprint_evidence_dependency({
        "package_id": PACKAGE_ID,
        "package_schema": PACKAGE_SCHEMA,
        "output_function": OUTPUT_FUNCTION_ID,
        "output_function_version": OUTPUT_FUNCTION_VERSION,
        "source_channel": SOURCE_CHANNEL,
        "source_algorithm_version": SOURCE_ALGORITHM_VERSION,
        "source_schema_version": SOURCE_SCHEMA_VERSION,
        "distance_model": dependencies["distance_model"],
        "repair_result": dependencies.get("repair_result"),
    })
    named_dependencies = {
        "scene": actual_dependencies["source"],
        "model": actual_dependencies["groups"],
        # The common contract has seven fixed dependency names. Bind the entire
        # kernel dependency set under source so domain/grid/occupancy cannot alias.
        "source": fingerprint_evidence_dependency(dependencies),
        "plane": actual_dependencies["analysis_plane"],
        "query": actual_dependencies["query"],
        "recipe": recipe,
        "channels": fingerprint_evidence_dependency(tuple(name for name, _, _ in _DISTANCE_CHANNELS)),
    }
    artifacts = {
        "source_channel": SOURCE_CHANNEL,
        "output_channels": [name for name, _, _ in _DISTANCE_CHANNELS],
        "dependency_fingerprints": dict(dependencies),
        "free_space_result_ref": _free_space_result_ref(result, bundle),
        "visualization_manifest": dict(visualization_manifest or {}),
    }
    target_ids = tuple(observation.pair_id if isinstance(observation, GroupPairDistanceObservation)
                       else observation["pair_id"] for observation in observations)
    if not target_ids:
        target_ids = ("empty-scope:" + fingerprint_evidence_dependency({"groups": (), "dependencies": dependencies})[:24],)
    return build_evidence_package_contract(
        package_id=PACKAGE_ID,
        package_schema=PACKAGE_SCHEMA,
        producer=PRODUCER,
        target_ids=target_ids,
        dependencies=named_dependencies,
        algorithm_version=OUTPUT_FUNCTION_VERSION,
        schema_version=PACKAGE_SCHEMA,
        artifacts=artifacts,
        parameter_snapshot=parameter_snapshot,
    )


def build_group_distance_visualization_manifest(
    package_output: EvidencePackageOutput | Mapping[str, Any],
    *,
    overview: str | None = None,
    blender: str | None = None,
    preview: str | None = None,
) -> dict[str, Any]:
    """Bind package identities to existing visual artifacts without recomputation."""
    if isinstance(package_output, EvidencePackageOutput):
        serialized = serialize_evidence_package_output(package_output)
        output_identity = package_output.output_identity
        outputs = serialized["outputs"]
        source_identities = [item.cache_identity["identity"] for item in package_output.source_envelopes]
    elif isinstance(package_output, Mapping):
        serialized = package_output
        output_identity = serialized.get("output_identity")
        outputs = serialized.get("outputs", ())
        source_identities = [item.get("cache_identity", {}).get("identity") for item in serialized.get("source_envelopes", ())]
    else:
        raise TypeError("package_output must be an EvidencePackageOutput or serialized mapping")
    if not isinstance(output_identity, str) or not output_identity:
        raise ValueError("package output identity is required")
    pair_ids = sorted({item.get("target", {}).get("identity") for item in outputs if isinstance(item, Mapping)})
    pair_ids = [item for item in pair_ids if item]
    repair_quality_counts: dict[str, int] = {}
    for item in outputs:
        if not isinstance(item, Mapping) or item.get("channel") != "path_distance":
            continue
        distance = item.get("observation", {}).get("distance", {})
        quality = distance.get("repair_quality") if isinstance(distance, Mapping) else None
        if quality:
            repair_quality_counts[str(quality)] = repair_quality_counts.get(str(quality), 0) + 1
    return {
        "schema": VISUALIZATION_MANIFEST_SCHEMA,
        "package_id": PACKAGE_ID,
        "package_output_identity": output_identity,
        "source_result_identities": sorted(item for item in source_identities if item),
        "pair_ids": pair_ids,
        "channels": [name for name, _, _ in _DISTANCE_CHANNELS],
        "route_source": "global_repair_result" if repair_quality_counts else "group_distance_kernel",
        "repair_quality_counts": repair_quality_counts,
        "artifact_bindings": {
            "overview": overview,
            "blender": blender,
            "preview": preview,
        },
        "distance_recomputed": False,
        "visualization_role": "existing group-distance overview/Blender artifacts",
    }


__all__ = [
    "PACKAGE_ID",
    "PACKAGE_SCHEMA",
    "GROUP_DISTANCE_CLEARANCE_SCHEMA",
    "build_group_distance_parameter_snapshot",
    "OUTPUT_FUNCTION_ID",
    "OUTPUT_FUNCTION_VERSION",
    "SOURCE_CHANNEL",
    "build_group_distance_evidence_package",
    "build_euclidean_median_proximity_processor",
    "build_euclidean_linear_proximity_processor",
    "build_euclidean_symmetric_reciprocal_proximity_processor",
    "build_group_distance_source_envelopes",
    "evaluate_group_distance_package",
    "serialize_group_distance_package_output",
    "build_group_distance_package_contract",
    "run_group_distance_package",
    "build_group_distance_visualization_manifest",
]
