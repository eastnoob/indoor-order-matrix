# Package-Owned Parameters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add typed package-owned parameters and auditable receipts while reusing validated historical results wherever their calculated values can be proved.

**Architecture:** A small independent module defines ParameterSpec, ParameterSchema and immutable ParameterSnapshot. Snapshots save all effective values, but the calculation fingerprint projects only recompute_required fields; warning differences retain historical calculated values and expose current requested values. Each producer owns its schema, storage only verifies receipts, and downstream packages receive read-only upstream results.

**Tech Stack:** Python >=3.12,<3.13 through Pixi, frozen dataclasses, canonical JSON/SHA-256, pytest and Jujutsu.

**Spec:** docs/superpowers/specs/2026-11-15-parameter-owned-sidecar-cache-design.md

## Global Constraints

- Work in an isolated Plan A jj workspace from the accepted spec/plan commit. Do not edit the distance-potential owner workspace, push or merge.
- Use Pixi for Python and tests. Every new/modified function needs an English-first docstring and important identity/validation/serialization blocks need intent comments.
- Type hints do not provide runtime checks. Explicitly reject bool-as-number, nonfinite values, invalid bounds/units, unknown fields and missing required values.
- Every package owns its defaults, exposure and impact declarations. Downstream consumers may select immutable upstream results; they cannot rewrite upstream parameters.
- Save the full effective snapshot. Only recompute_required values enter calculation identity. Source labels, display metadata, requested values, paths and timestamps never enter identity.
- reuse_with_warning changes preserve calculated_parameters and report requested_parameters, warnings and exact_match=False. Geometry/topology tolerance currently affects calculation and stays recompute_required; use a contract-only warning fixture until a real package declares a justified warning parameter.
- Plane/slab/query/lattice context is required existing request input when applicable. Never fabricate geometry defaults. Existing AnalysisRequest validation remains authoritative.
- A typed request cannot report an old receipt with no verified snapshot as an exact typed hit. Keep legacy readers and validated old bytes. Receipt-only adoption requires full independent reconstruction of historical calculated values from validated old contract/payload and compatible current computation inputs.
- Avoid unnecessary recalculation: audit-only metadata changes must reuse existing results, and verified legacy adoption may reuse payload bytes without executing a producer.
- No formula changes, CacheStore, migration, locking, output-port split, SQLite or intermediate cache implementation in A.
- Before each checkpoint record workspace, accepted parent, dirty-file manifest and intended files. Edit, test, inspect diff, then jj commit. Never name an empty change as an implementation checkpoint.
- Installed jj lacks diff --check; inspect jj diff --git and scan touched files for trailing whitespace instead.

## File Map

| File | Responsibility |
| --- | --- |
| features/evidence_package_parameters.py | Independent schema, validation, immutable snapshots, projection and comparison |
| features/field_core.py | Optional typed contract and processed receipt fields, freshness status, legacy compatibility |
| features/evidence_package_storage.py | Verified lookup results retaining historical contracts/status and opt-in legacy adoption |
| features/group_distance_evidence_package.py | Clearance owner and constrained/unconstrained mode |
| features/free_space_evidence_package.py | Schema over already validated free-space request |
| features/group_axis_potential_field.py | Modulation switch owner and immutable dependency binding |
| features/group_distance_repair.py | Minimal input/policy/method checkpoint binding before A exposes variable CLI clearance |
| adapters/free_space_evidence_package.py | HMAC verification before snapshot reconstruction |
| test/test_evidence_package_parameters.py | Pure parameter tests |
| existing receipt/package tests below | Actual no-recompute and compatibility tests |
| docs/software-architecture.md | Synchronized implementation map |
| docs/superpowers/handoffs/2026-11-15-plan-a-accepted.md | Accepted commit, validation and Plan B seam |

---

### Preflight: Retain real receipts before changing parameter identities

- [ ] Record the workspace, accepted pre-A commit and dirty-file manifest before any A implementation. Create `test/fixtures/cache_migration/pre_parameter_sidecar/` from small, already calculated legacy raw, processed, authenticated free-space and Blender-wire test receipts. Prefer exact existing bytes; if a family has no suitable small test artifact, run the unchanged pre-A implementation once on an existing tiny test fixture with an independent test key before any source edit. This is a true pre-refactor baseline, and does not rerun a large model. Keep each receipt's old filename/key, relative artifact address and verification metadata. Save a `manifest.json` with SHA-256, original schema/key, producer/backend versions, implementation-file hashes, source bindings and test authentication domain for every retained file. Never copy a real user/production sidecar secret into the repository; use only established test-domain credentials or the independently created tiny-fixture test key, retained through the project's approved test fixture mechanism. Never include secret values in the manifest. Record unavailable families explicitly rather than presenting a post-refactor receipt as historical evidence. These fixtures are required for Plan B's no-recompute migration acceptance because A/B refactoring can change implementation-derived keys even when geometry/effective parameters are unchanged.
- [ ] Verify the retained digests and original readers before changing code, then retain the fixture and manifest in the first nonempty A checkpoint. The A handoff names this directory and the exact pre-A revision. This preservation step authorizes only tiny test baselines where necessary, not large-model recomputation or production credential copying.

### Task 1: Schema, immutable snapshot and impact projection

**Files:**
- Create: features/evidence_package_parameters.py
- Create: test/test_evidence_package_parameters.py

**Interfaces:**

~~~python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType

REQUIRED = object()

class ParameterImpact(str, Enum):
    RECOMPUTE_REQUIRED = "recompute_required"
    REUSE_WITH_WARNING = "reuse_with_warning"
    METADATA_ONLY = "metadata_only"

@dataclass(frozen=True, slots=True)
class ParameterSpec:
    name: str
    value_type: type
    default: object = REQUIRED
    unit: str = "dimensionless"
    exposed: bool = True
    impact: ParameterImpact = ParameterImpact.RECOMPUTE_REQUIRED
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[object, ...] | None = None
    nullable: bool = False

@dataclass(frozen=True, slots=True)
class ParameterSchema:
    package_id: str
    schema_version: str
    specs: tuple[ParameterSpec, ...]
    def resolve(self, values: Mapping[str, object] | None = None, *,
                sources: Mapping[str, str] | None = None) -> ParameterSnapshot:
        """Expand defaults and validate requested values before calculation."""
    def capture_calculated(self, values: Mapping[str, object], *,
                           sources: Mapping[str, str]) -> ParameterSnapshot:
        """Validate a complete historical value map without expanding defaults."""

@dataclass(frozen=True, slots=True)
class ParameterSnapshot:
    package_id: str
    config_schema_version: str
    effective_parameters: Mapping[str, object]
    calculated_parameters: Mapping[str, object]
    parameter_sources: Mapping[str, str]
    parameter_impacts: Mapping[str, str]
    parameter_value_contracts: Mapping[str, Mapping[str, object]]
    parameter_fingerprint: str
    def identity_payload(self) -> dict[str, object]:
        """Return only schema and computation-affecting values."""
    def to_json(self) -> dict[str, object]:
        """Return expanded historical values and audit metadata."""
    @classmethod
    def from_json(cls, payload: Mapping[str, object]) -> ParameterSnapshot:
        """Validate stored values without applying current defaults."""

def compare_parameter_snapshots(calculated: ParameterSnapshot,
                                requested: ParameterSnapshot) -> dict[str, object]:
    """Report exact, warning reuse or required recomputation with both value sets."""
~~~

REQUIRED is a module-owned sentinel. Requiredness, nullable and default are independent: a required nullable field must still be supplied explicitly, while its supplied value may be None. calculated_parameters equals all effective values actually used for that snapshot. Current requested_parameters is comparison status, never a rewrite of the historical receipt.

parameter_value_contracts stores only each field's restricted type tag, nullable boolean and canonical unit; it never stores today's default. The fixed tags are str, bool, int, float, dict, tuple and none. No class names, dynamic imports, arbitrary deserialization or global schema registry are introduced. Historical self-description is insufficient for current reuse: the requested snapshot is independently produced by the current owner schema, and comparison checks schema ID, complete field set, impacts and type/unit/nullable declarations before accepting the saved values.

- [ ] **Step 1: Record the checkpoint manifest and write these failing tests.**

~~~python
from dataclasses import replace
import json
import pytest
from features.evidence_package_parameters import (
    ParameterImpact, ParameterSchema, ParameterSnapshot, ParameterSpec,
    compare_parameter_snapshots,
)

def _schema() -> ParameterSchema:
    """Provide calculation, warning and display knobs for contract tests."""
    return ParameterSchema("contract-package", "contract-parameters/1", (
        ParameterSpec("width_m", float, 1.0, unit="m", minimum=0.0),
        ParameterSpec("review_m", float, 0.01, unit="m", minimum=0.0,
                      impact=ParameterImpact.REUSE_WITH_WARNING),
        ParameterSpec("label", str, "A", impact=ParameterImpact.METADATA_ONLY),
    ))

def test_source_labels_do_not_change_identity():
    """An explicit default value denotes the same calculation."""
    first = _schema().resolve()
    gui = _schema().resolve({"width_m": 1}, sources={"width_m": "gui"})
    assert gui.effective_parameters["width_m"] == 1.0
    assert first.parameter_fingerprint == gui.parameter_fingerprint
    assert first.parameter_sources != gui.parameter_sources

def test_warning_projection_preserves_calculated_and_requested_values():
    """Warning reuse cannot pretend current intent was historically calculated."""
    first = _schema().resolve()
    requested = _schema().resolve({"review_m": 0.02, "label": "B"})
    status = compare_parameter_snapshots(first, requested)
    assert first.parameter_fingerprint == requested.parameter_fingerprint
    assert status["reuse"] == "reuse_with_warning"
    assert status["exact_match"] is False
    assert status["calculated_parameters"]["review_m"] == 0.01
    assert status["requested_parameters"]["review_m"] == 0.02
    assert [item["parameter"] for item in status["warnings"]] == ["review_m"]
    changed = _schema().resolve({"width_m": 2.0})
    assert changed.parameter_fingerprint != first.parameter_fingerprint
    assert compare_parameter_snapshots(first, changed)["recompute_required"]

@pytest.mark.parametrize("values", [
    {"width_m": True}, {"width_m": float("nan")}, {"width_m": float("inf")},
    {"width_m": -1.0}, {"width_m": {"value": 100, "unit": "cm"}},
    {"unknown": 1.0},
])
def test_invalid_values(values):
    """Malformed inputs never reach algorithms or fingerprinting."""
    with pytest.raises((TypeError, ValueError)):
        _schema().resolve(values)

def test_required_context_and_old_default_roundtrip():
    """Required geometry stays required and saved defaults stay expanded."""
    required = ParameterSchema("p", "p/1", (ParameterSpec("plane", dict),))
    with pytest.raises(ValueError, match="missing"):
        required.resolve()
    old = _schema().resolve()
    changed = replace(_schema(), specs=(
        replace(_schema().specs[0], default=2.0),
        _schema().specs[1], _schema().specs[2]))
    saved = ParameterSnapshot.from_json(json.loads(json.dumps(old.to_json())))
    assert saved == old
    assert saved.calculated_parameters["width_m"] == 1.0
    assert changed.resolve().effective_parameters["width_m"] == 2.0
    with pytest.raises(TypeError):
        saved.calculated_parameters["width_m"] = 3.0

def test_required_nullable_context_has_stable_schema_and_roundtrip():
    """An absent datum is explicit context, independent of requiredness/defaults."""
    schema = ParameterSchema("p", "p/1", (
        ParameterSpec("datum", dict, unit="request_context", nullable=True),))
    with pytest.raises(ValueError, match="missing"):
        schema.resolve()
    absent = schema.resolve({"datum": None})
    present = schema.resolve({"datum": {"kind": "slab", "z_m": 0.0}})
    assert absent.config_schema_version == present.config_schema_version == "p/1"
    assert absent.parameter_fingerprint != present.parameter_fingerprint
    assert ParameterSnapshot.from_json(absent.to_json()) == absent
    assert ParameterSnapshot.from_json(present.to_json()) == present
    assert absent.parameter_value_contracts["datum"] == {
        "type": "dict", "nullable": True, "unit": "request_context"}
    with pytest.raises((TypeError, ValueError)):
        ParameterSchema("p", "p/1", (ParameterSpec("datum", dict),)).resolve(
            {"datum": None})
    malformed = absent.to_json()
    malformed["parameter_value_contracts"]["datum"]["nullable"] = False
    with pytest.raises((TypeError, ValueError)):
        ParameterSnapshot.from_json(malformed)

def test_capture_calculated_never_fills_a_missing_saved_default():
    """Historical capture requires every field even when today's schema has defaults."""
    with pytest.raises(ValueError, match="missing"):
        _schema().capture_calculated({"width_m": 1.0}, sources={"width_m": "legacy"})

def test_saved_value_contract_cannot_reclassify_current_calculation_fields():
    """A receipt cannot self-attest a weaker impact/type contract for reuse."""
    current = _schema().resolve()
    weaker_schema = replace(_schema(), specs=(
        replace(_schema().specs[0], impact=ParameterImpact.METADATA_ONLY),
        _schema().specs[1], _schema().specs[2]))
    weaker = weaker_schema.resolve()
    assert compare_parameter_snapshots(weaker, current)["recompute_required"]
    malformed = current.to_json()
    malformed["parameter_value_contracts"]["width_m"]["type"] = "arbitrary.Class"
    with pytest.raises((TypeError, ValueError)):
        ParameterSnapshot.from_json(malformed)
~~~

- [ ] **Step 2: Run RED.** Run pixi run pytest test/test_evidence_package_parameters.py -q. Record the missing-module/type or failed assertion before implementation.

- [ ] **Step 3: Implement declaration validation, resolution, freeze and projection.**

Keep standard-library JSON/hash/freeze helpers inside this small module. It must not import field_core if field_core imports it. Reject arbitrary Python objects, nonstring map keys, nonfinite numbers and unit-bearing mappings supplied to numeric specs. Normalize int to float for a float specification and -0.0 to 0.0. Validate duplicate names, supported type declarations, finite bounds, nonempty units/choices and nonempty string source labels; never coerce a source with str().

Support value_type in str, bool, int, float, dict, tuple and type(None); dict/tuple declarations admit only deeply finite JSON. nullable must be an actual bool. Accept None only for nullable=True or value_type=type(None); do not change a schema's declared type based on the runtime value. Validate declared defaults with the same rules, independently of REQUIRED. Required geometric records are normalized by the existing typed request before schema resolution. The unit vocabulary is m, rad, dimensionless and request_context; reject noncanonical declaration units such as cm rather than applying an implicit conversion.

~~~python
def _json_value(value):
    """Convert frozen parameter JSON into ordinary finite JSON values."""
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return 0.0 if value == 0.0 else value
    raise TypeError("parameters must contain finite JSON values")

def _freeze(value):
    """Detach caller containers so downstream readers cannot edit history."""
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise TypeError("parameter mapping keys must be strings")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return _json_value(value)
~~~

Use this exact identity projection:

~~~python
def _identity_payload(package_id, schema_version, effective, impacts):
    """Project only values whose change requires a new computation."""
    return {
        "package_id": package_id,
        "config_schema_version": schema_version,
        "parameters": {
            name: _json_value(effective[name])
            for name in sorted(effective)
            if impacts[name] == ParameterImpact.RECOMPUTE_REQUIRED.value
        },
    }

def _fingerprint(payload):
    """Hash canonical finite JSON without source or request metadata."""
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
~~~

from_json requires the exact snapshot keys, identical effective/calculated/source/impact/value-contract key sets, recognized impact values, exactly the three value-contract keys type/nullable/unit, whitelist types/canonical units, values satisfying those historical declarations and a recomputed matching fingerprint. It never calls resolve or today's defaults. Require effective_parameters == calculated_parameters for a persisted calculation snapshot; requested differences belong only in status. Comparison rejects package/schema/field-set/impact/type/unit/nullable mismatches against the independently current owner snapshot conservatively and returns:

~~~python
{
    "reuse": "exact",
    "exact_match": True,
    "recompute_required": False,
    "calculated_parameters": calculated.to_json()["calculated_parameters"],
    "requested_parameters": requested.to_json()["effective_parameters"],
    "warnings": [],
}
~~~

Warning records contain parameter, calculated, requested and impact. Warning differences use reuse_with_warning/exact_match=False; computation differences use recompute_required=True. metadata_only differences neither warn nor rewrite historical values.

- [ ] **Step 4: Run GREEN.** Run the focused file. Add corruption, duplicate-name, choices, source-map, nested freeze and key-order tests. Expect PASS.
- [ ] **Step 5: Inspect jj status, jj diff --stat and jj diff --git; commit nonempty changes with jj commit -m "feat: add typed package parameter snapshots". Record the resulting accepted parent.**

---

### Task 2: Processor binding and processed receipt compatibility

**Files:**
- Modify: features/field_core.py EvidenceOutputProcessor, EvidenceProcessedOutput, EvidencePackage.process_output and processed JSON functions
- Modify: features/evidence_package_storage.py processed_cache_key and load_processed_output
- Modify: test/test_evidence_package_processing.py
- Modify: test/test_evidence_package_processed_readback.py

**Interfaces:**
- Add keyword-only parameter_schema and parameter_sources to EvidenceOutputProcessor; resolved parameter_snapshot is immutable. parameters remains callback-visible complete effective values.
- Add optional keyword-only parameter_snapshot to EvidenceProcessedOutput.
- Keep callback signature unchanged. processing_identity and processed_cache_key use the same projection.
- Missing snapshot remains a legacy record. When None, omit the new serialized field and retain historical identity bytes.

- [ ] **Step 1: Record manifest and add failing tests using existing _raw, _package and _process in test_evidence_package_processing.py.**

~~~python
def test_typed_processor_sources_identity_and_roundtrip():
    """Receipts keep source labels while computation identity excludes them."""
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec
    schema = ParameterSchema("contract-package", "processor-parameters/1", (
        ParameterSpec("value", float, 0.25, minimum=0.0, maximum=1.0),))
    first_processor = core.EvidenceOutputProcessor(
        "typed-process", "1", _process, parameter_schema=schema)
    cli_processor = core.EvidenceOutputProcessor(
        "typed-process", "1", _process, {"value": 0.25},
        parameter_schema=schema, parameter_sources={"value": "cli"})
    raw = _raw()
    first = _package(first_processor).process_output(raw, package_freshness="fresh")
    cli = _package(cli_processor).process_output(raw, package_freshness="fresh")
    assert first.processing_identity == cli.processing_identity
    assert first.parameter_snapshot.parameter_sources != cli.parameter_snapshot.parameter_sources
    saved = core.serialize_evidence_processed_output(cli)
    restored = core.deserialize_evidence_processed_output(
        json.loads(json.dumps(saved)), raw_output=raw)
    assert restored == cli
    assert restored.parameter_snapshot.calculated_parameters["value"] == 0.25
~~~

In test_evidence_package_processed_readback.py use existing _raw and _processed:

~~~python
def test_legacy_processed_receipt_keeps_legacy_attestation():
    """Old receipts stay readable without inventing a typed parameter history."""
    raw = _raw()
    old = core.serialize_evidence_processed_output(_processed(raw))
    assert "parameter_snapshot" not in old
    restored = core.deserialize_evidence_processed_output(old, raw_output=raw)
    assert restored.parameter_snapshot is None
    assert core.serialize_evidence_processed_output(restored) == old
~~~

- [ ] **Step 2: Run RED.** Run pixi run pytest test/test_evidence_package_processing.py test/test_evidence_package_processed_readback.py -q.
- [ ] **Step 3: Resolve typed parameters once, pass full effective values to callbacks, bind the saved snapshot to success/error outcomes, and reject snapshot/package mismatch.**

Use identity_payload for typed processors and preserve the old parameters payload for legacy processors. Do not append a None key to old identity payloads.

~~~python
if processor.parameter_snapshot is not None:
    payload["parameter_identity"] = processor.parameter_snapshot.identity_payload()
else:
    payload["parameters"] = processor.parameters
~~~

The result property uses self.parameter_snapshot equivalently. Add a regression that processed_cache_key equals actual processing_identity without invoking the callback.

- [ ] **Step 4: Extend serialization/readback while preserving old bytes.**

~~~python
serialized = _json_value(result)
if result.parameter_snapshot is None:
    serialized.pop("parameter_snapshot", None)
else:
    serialized["parameter_snapshot"] = result.parameter_snapshot.to_json()
~~~

Do this before payload_fingerprint. Readback checks transport fingerprint before decoding optional ParameterSnapshot.from_json, verifies effective values equal the parameters field, and never expands defaults.

- [ ] **Step 5: Run GREEN.** Run pixi run pytest test/test_evidence_package_processing.py test/test_evidence_package_processed_readback.py test/test_evidence_package_saved_processed_consumer.py -q. Expect PASS including existing pinned legacy identities.
- [ ] **Step 6: Inspect diff and commit with jj commit -m "feat: record typed processor parameters in receipts".**

---

### Task 3: Owner schemas, raw contract identity and warning status

**Files:**
- Modify: features/field_core.py contract builder/validator, identity payload and freshness comparison
- Modify: features/group_distance_evidence_package.py _run_contract and owner schema
- Modify: features/free_space_evidence_package.py build_free_space_package_contract and owner schema
- Modify: features/group_axis_potential_field.py build_group_axis_potential_package_contract and owner schema
- Modify: features/group_distance_repair.py checkpoint reader/writers in global_repair_result
- Modify: scripts/design/group_level/run_group_distance_global_source.py parser and clearance handoff
- Modify: test/test_evidence_package_freshness.py
- Modify: test/test_free_space_evidence_package.py
- Modify: test/test_group_distance_evidence_package.py
- Modify: test/test_group_axis_distance_modulation.py
- Modify: test/test_group_distance_route_repair.py for the real CLI clearance handoff

**Interfaces:**
- build_evidence_package_contract adds optional parameter_snapshot: ParameterSnapshot | None.
- Add a new optional raw contract key parameter_snapshot containing snapshot.to_json(); identity includes only snapshot.identity_payload(). The inspected current build_evidence_package_contract builds schema/package_id/package_schema/producer/target_ids/dependencies/algorithm_version/schema_version/invalidation_scope/artifacts/package_identity and has no existing parameters field. Do not overwrite arbitrary parameters or confuse this new raw contract field with the existing EvidenceOutputProcessor.parameters/EvidenceProcessedOutput.parameters callback mapping. Legacy missing-field contracts retain their old identity and serialization shape.
- Add build_group_distance_parameter_snapshot(bundle, *, parameter_sources=None), build_free_space_parameter_snapshot(request_values, *, parameter_sources=None), build_group_axis_parameter_snapshot(*, distance_modulation_enabled, parameter_sources=None), each returning ParameterSnapshot.
- Add parameter_status only for typed freshness comparisons, preserving legacy status shape.
- Existing public entry calls remain valid; new source metadata is keyword-only.
- run_group_distance_package(bundle, *, repaired_result=None, cache_directory=None, output_processor=None, parameter_sources=None) preserves all existing arguments and forwards only owner metadata.
- GROUP_DISTANCE_CLEARANCE_SCHEMA belongs to features/group_distance_evidence_package.py and owns defaults min_left_m=.225, min_right_m=.225, min_total_m=.55, all finite nonnegative metres.
- scripts/design/group_level/run_group_distance_global_source.py adds build_parser() -> argparse.ArgumentParser and resolve_clearance_cli_parameters(args: argparse.Namespace) -> ParameterSnapshot. The CLI flags default to None; the package schema supplies omitted values.
- features/group_distance_repair.py adds _checkpoint_fingerprint(bundle, baseline, policy, *, pair_limit=None) -> str and _checkpoint_matches(payload, *, fingerprint, source_index, source_id, wanted_pairs) -> bool. All checkpoint writer branches include the same schema and input/policy/method binding; absent/foreign bindings are never resumed.

- [ ] **Step 1: Record manifest and add failing tests using existing _contract in test_evidence_package_freshness.py.**

~~~python
def test_contract_warning_retains_historical_calculated_values():
    """Usable evidence can warn without claiming exact requested parameters."""
    from features.evidence_package_parameters import (
        ParameterImpact, ParameterSchema, ParameterSpec)
    schema = ParameterSchema("group-geometry-relation", "contract-parameters/1", (
        ParameterSpec("width_m", float, 1.0, unit="m", minimum=0.0),
        ParameterSpec("review_m", float, 0.01, unit="m", minimum=0.0,
                      impact=ParameterImpact.REUSE_WITH_WARNING)))
    base = _contract()
    arguments = {name: base[name] for name in (
        "package_id", "package_schema", "producer", "target_ids",
        "dependencies", "algorithm_version", "schema_version")}
    old = build_evidence_package_contract(
        **arguments, parameter_snapshot=schema.resolve())
    current = build_evidence_package_contract(
        **arguments, parameter_snapshot=schema.resolve(
            {"review_m": 0.02}, sources={"review_m": "gui"}))
    assert old["package_identity"] == current["package_identity"]
    status = evaluate_evidence_package_freshness(
        cached_contract=old, current_contract=current)
    assert status["recompute_required"] is False
    assert status["parameter_status"]["reuse"] == "reuse_with_warning"
    assert status["parameter_status"]["exact_match"] is False
    assert status["parameter_status"]["calculated_parameters"]["review_m"] == 0.01
    assert status["parameter_status"]["requested_parameters"]["review_m"] == 0.02
~~~

In test_free_space_evidence_package.py use existing _compact_document and package_module:

~~~python
def test_free_space_snapshot_captures_required_request_geometry():
    """Required context comes from the validated request without new defaults."""
    _, document = _compact_document()
    request = document["tables"]["snapshot"]["request"]
    snapshot = package_module.build_free_space_parameter_snapshot(request)
    values = snapshot.to_json()["effective_parameters"]
    assert values["analysis_plane"] == {
        key: value for key, value in request["plane"].items()
        if key not in {"name", "revision"}}
    assert values["plane_publication_metadata"] == {
        key: request["plane"][key] for key in ("name", "revision")
        if key in request["plane"]}
    assert values["grid_spacing_m"] == request["sampling"]["spacing"]
    assert values["geometry_query"] == request["geometry_query"]
    assert values["height_band_datum"] == request.get("height_band_datum")
    incomplete = dict(request)
    incomplete.pop("plane")
    with pytest.raises((KeyError, TypeError, ValueError)):
        package_module.build_free_space_parameter_snapshot(incomplete)
~~~

- [ ] **Step 2: Run RED.** Run pixi run pytest test/test_evidence_package_freshness.py test/test_free_space_evidence_package.py -q.
- [ ] **Step 3: Add optional snapshot validation and typed status.**

~~~python
if parameter_snapshot is not None:
    if not isinstance(parameter_snapshot, ParameterSnapshot):
        raise TypeError("parameter_snapshot must be a ParameterSnapshot or None")
    if parameter_snapshot.package_id != package_id:
        raise ValueError("parameter snapshot must belong to this package")
    normalized["parameter_snapshot"] = parameter_snapshot.to_json()
~~~

Validate saved snapshots through from_json. Missing snapshot on one side reports parameter_snapshot_missing, exact_match=False and no typed hit. Warning mismatch keeps evidence usable but explicitly warns; computation/schema mismatch reports parameters_changed and recompute_required=True.

- [ ] **Step 4: Declare each owner's exact semantics.**

Distance keeps clearance_policy=None as unconstrained mode; do not silently replace it with .225/.225/.55. For explicitly constrained mode a frozen owner config exposes defaults min_left_m=.225, min_right_m=.225, min_total_m=.55, validates exact key set and finite nonnegative numbers, then uses actual bundle or validated repair values. Snapshot includes mode; unconstrained thresholds do not become hidden effective algorithm inputs. Upstream saved repair policy stays immutable.

Free space captures request plane, geometry_query, applicable height_band_datum, complete lattice, geometry/topology tolerance and source rules from the validated request/document. Split plane audit fields from calculation: analysis_plane is the validated plane mapping with name/revision removed, retaining the existing real identity/origin/basis/unit semantics. plane_publication_metadata is a required dict with impact=METADATA_ONLY containing those present name/revision fields. The full actual audit values are still saved, while unchanged plane geometry keeps the existing content-reuse behavior. Preserve test_free_space_plane_publication_revision_reuses_with_current_metadata and add its name-only counterpart. Declare height_band_datum as ParameterSpec("height_band_datum", dict, unit="request_context", nullable=True), with REQUIRED unchanged; the builder explicitly supplies request.get("height_band_datum"), whether None or a validated datum mapping. Never dynamically switch its schema type to type(None). Grid spacing comes from required GridSampling. Only current tolerance defaults are .001 m. Slab/plane are captured required context, not hardcoded 1.6 m or invented geometry.

Potential owns this boolean declaration:

~~~python
GROUP_AXIS_PARAMETER_SCHEMA = ParameterSchema(
    PACKAGE_ID, "group-axis-potential/parameters/1",
    (ParameterSpec("distance_modulation_enabled", bool, False),))

def build_group_axis_parameter_snapshot(*, distance_modulation_enabled,
                                        parameter_sources=None):
    """Resolve this package's own optional distance-modulation switch."""
    return GROUP_AXIS_PARAMETER_SCHEMA.resolve(
        {"distance_modulation_enabled": distance_modulation_enabled},
        sources=parameter_sources)
~~~

Enabled modulation still requires existing DistanceModulationInput, current processed reference, compatibility facts and dependency graph. Keep _validate_distance_modulation. Do not expose fixed epsilon/floor trial constants.

Expose clearance at the actual global-source runner, which currently hardcodes .225/.225/.55. The parser adds --min-left-m, --min-right-m and --min-total-m, each with type=float and default=None. The script builds override/source maps and resolves the package-owned schema, then passes snapshot.effective_parameters to global_repair_result. Do not keep a second set of CLI defaults. This runner is an explicitly constrained repair action, so these defaults do not change the unconstrained bundle API.

~~~python
def resolve_clearance_cli_parameters(args):
    """Resolve CLI overrides with the evidence owner's defaults and validation."""
    names = ("min_left_m", "min_right_m", "min_total_m")
    overrides = {name: getattr(args, name) for name in names
                 if getattr(args, name) is not None}
    return GROUP_DISTANCE_CLEARANCE_SCHEMA.resolve(
        overrides, sources={name: "cli" for name in overrides})
~~~

Add this parser/schema test to test_group_distance_route_repair.py; it uses only parser values and never reads a model:

~~~python
def test_global_source_cli_uses_owner_clearance_defaults_and_overrides():
    """The external entry resolves package defaults without copying constants."""
    from scripts.design.group_level.run_group_distance_global_source import (
        build_parser, resolve_clearance_cli_parameters)
    from features.group_distance_evidence_package import GROUP_DISTANCE_CLEARANCE_SCHEMA
    base = ["--input-bundle", "input.json", "--baseline-run-dir", "baseline",
            "--output-dir", "result", "--source-index", "0"]
    default = resolve_clearance_cli_parameters(build_parser().parse_args(base))
    assert default.parameter_fingerprint == GROUP_DISTANCE_CLEARANCE_SCHEMA.resolve().parameter_fingerprint
    changed = resolve_clearance_cli_parameters(build_parser().parse_args(
        base + ["--min-left-m", "0.3", "--min-total-m", "0.8"]))
    assert changed.effective_parameters["min_left_m"] == 0.3
    assert changed.effective_parameters["min_total_m"] == 0.8
    assert changed.parameter_sources["min_left_m"] == "cli"
    with pytest.raises((TypeError, ValueError)):
        resolve_clearance_cli_parameters(build_parser().parse_args(
            base + ["--min-left-m", "nan"]))
~~~

Before the CLI overrides are considered usable, add the minimal checkpoint guard in A. Existing global_repair_result currently reads every source_*.json and trusts source_index/results without any input, policy or method binding; changing a CLI threshold must not reuse such a checkpoint. Plan B still owns checkpoint migration, richer recovery and lifecycle management.

Define the checkpoint fingerprint from current facts rather than a stored digest assertion: the ordinary/unconstrained bundle's recomputed group_distance_input_fingerprints, original free-space result reference, ordered group IDs, the exact wanted group-pair set after pair_limit, the normalized effective clearance policy, GLOBAL_METHOD_VERSION and checkpoint schema version. Include a fingerprint of the retained baseline observations used by this invocation, so a source-index-only file cannot attest another baseline scope. Paths, output directory and source labels do not enter this fingerprint.

Use an additive schema marker such as directional-repair-checkpoint/1 and record checkpoint_fingerprint, source_index, source_id and results in all four writer branches (empty target set, missing source access, missing target accesses, completed search). Validate the fingerprint and schema before reading any results or adding completed_sources. Check source index is a real nonnegative int in the current groups range (not bool), index/id agree, each result key is unique and belongs to the exact source/wanted pair scope, and route/exact records have every field the final observation assembler reads. A passed route has finite nonnegative value, nonempty cell_keys and state_keys, source_access/target_access mappings, and exact passed/edge_witnesses/turn_witnesses/minimum_m; a failed exact record has a failure mapping. Never admit route=None or use a matching fingerprint as evidence of completion.

For A, accept a source as completed only when loaded result keys equal that source's complete wanted-pair set; empty results are valid only for an empty wanted set. Existing checkpoints with unreachable or partial pairs may safely be ignored and searched again; A does not invent a terminal protocol. Keep those original files. New writers use source_<index>-<checkpoint_fingerprint>.json so changed-policy and unbound source_<index>.json files remain in place. If an invalid file already occupies the new exact filename, retain its bytes under a digest-qualified rejected filename before publishing the replacement. Plan B owns richer recovery/migration. No rejected or unbound file may add completed_sources.

Add these actual guard tests to test_group_distance_route_repair.py; the fingerprint tests use the existing _missing_bundle factory from test_group_distance and do not invent geometry:

~~~python
def test_checkpoint_fingerprint_changes_with_policy_input_and_method(monkeypatch):
    """Checkpoint identity binds real computation inputs independently of its path."""
    from dataclasses import replace
    from features import group_distance_repair as repair
    from .test_group_distance import _missing_bundle
    bundle = _missing_bundle()
    baseline = {"observations": [{"group_ids": ["a", "b"]}]}
    policy = {"min_left_m": 0.225, "min_right_m": 0.225, "min_total_m": 0.55}
    first = repair._checkpoint_fingerprint(bundle, baseline, policy)
    assert repair._checkpoint_fingerprint(bundle, baseline, dict(policy)) == first
    changed_policy = {**policy, "min_total_m": 0.8}
    assert repair._checkpoint_fingerprint(bundle, baseline, changed_policy) != first
    changed_input = replace(bundle, source_identity={"id": "other-source"})
    assert repair._checkpoint_fingerprint(changed_input, baseline, policy) != first
    changed_pairs = {"observations": [{"group_ids": ["a", "c"]}]}
    assert repair._checkpoint_fingerprint(bundle, changed_pairs, policy) != first
    monkeypatch.setattr(repair, "GLOBAL_METHOD_VERSION", "changed-method")
    assert repair._checkpoint_fingerprint(bundle, baseline, policy) != first

def test_unbound_or_foreign_checkpoint_never_marks_source_complete():
    """A retained old JSON file cannot silently skip the current source search."""
    from features import group_distance_repair as repair
    unbound = {"source_index": 0, "source_id": "a", "results": []}
    assert not repair._checkpoint_matches(
        unbound, fingerprint="current", source_index=0, source_id="a",
        wanted_pairs=(("a", "b"),))
    policy = {"min_left_m": .2, "min_right_m": .2, "min_total_m": .5}
    context = repair._clearance_context(_bundle(), policy)
    cells = ((1, 1), (1, 2))
    route = {"value": 1.0, "cell_keys": cells,
             "state_keys": ((cells[0], None), (cells[1], (1.0, 0.0))),
             "source_access": {"free_cell": cells[0], "offset": 0.0},
             "target_access": {"free_cell": cells[1], "offset": 0.0}}
    exact = repair._exact_path(cells, context)
    assert exact["passed"]
    bound = {**unbound, "schema": "directional-repair-checkpoint/1",
             "checkpoint_fingerprint": "current", "results": [
                 {"key": ["a", "b"], "route": route, "exact": exact}]}
    assert repair._checkpoint_matches(
        bound, fingerprint="current", source_index=0, source_id="a",
        wanted_pairs=(("a", "b"),))
    assert not repair._checkpoint_matches(
        bound, fingerprint="changed-policy", source_index=0, source_id="a",
        wanted_pairs=(("a", "b"),))
    assert not repair._checkpoint_matches(
        {**bound, "results": []}, fingerprint="current", source_index=0,
        source_id="a", wanted_pairs=(("a", "b"),))
    assert not repair._checkpoint_matches(
        {**bound, "results": bound["results"] * 2}, fingerprint="current",
        source_index=0, source_id="a", wanted_pairs=(("a", "b"),))
    assert not repair._checkpoint_matches(
        {**bound, "source_index": True}, fingerprint="current", source_index=0,
        source_id="a", wanted_pairs=(("a", "b"),))
~~~

Add this reader integration test; it counts actual source searches and uses the existing small geometry fixture only for exact witness validation:

~~~python
def test_global_checkpoint_guard_controls_actual_source_search(tmp_path, monkeypatch):
    """Only complete, matching receipts skip a source after policy changes."""
    from dataclasses import replace
    import json
    from features import group_distance_repair as repair
    from .test_group_distance import _missing_bundle
    geometry = _bundle()
    original = _missing_bundle()
    bundle = replace(original, grid=geometry.grid, domain=geometry.domain,
                     physical_occupancy=())
    source, target = (group.group_id for group in bundle.groups[:2])
    baseline = {"observations": [{"group_ids": [source, target]}]}
    policy = {"min_left_m": .2, "min_right_m": .2, "min_total_m": .5}
    cells = ((1, 1), (1, 2))
    access = {"free_cell": cells[0], "offset": 0.0}
    calls = []
    monkeypatch.setattr(repair.kernel, "_graphs",
                        lambda *args: ({}, nx.Graph(), nx.Graph(), {}))
    monkeypatch.setattr(repair, "_access_candidates_for_group",
                        lambda *args: (access,))

    def search(graph, source_accesses, target_accesses, context):
        """Return one fully shaped route without invoking a graph search."""
        calls.append(tuple(context["thresholds"]))
        return {target: {"value": 1.0, "cell_keys": cells,
                        "state_keys": ((cells[0], None), (cells[1], (1.0, 0.0))),
                        "source_access": access, "target_access": access}}

    monkeypatch.setattr(repair, "_global_source_search", search)
    old = tmp_path / "source_000.json"
    old.write_text(json.dumps({"source_index": 0, "source_id": source,
                               "results": []}), encoding="utf-8")
    retained = old.read_bytes()
    repair.global_repair_result(bundle, baseline, policy, checkpoint_dir=tmp_path)
    assert len(calls) == 1 and old.read_bytes() == retained
    repair.global_repair_result(bundle, baseline, policy, checkpoint_dir=tmp_path)
    assert len(calls) == 1
    repair.global_repair_result(bundle, baseline, {**policy, "min_total_m": .8},
                                checkpoint_dir=tmp_path)
    assert len(calls) == 2 and old.read_bytes() == retained
~~~

- [ ] **Step 5: Run GREEN.** Run pixi run pytest test/test_evidence_package_freshness.py test/test_group_distance_evidence_package.py test/test_group_distance_clearance.py test/test_group_distance_route_repair.py test/test_free_space_evidence_package.py test/test_group_axis_distance_modulation.py -q. Expect PASS.
- [ ] **Step 6: Inspect diff and commit with jj commit -m "feat: bind package contracts to owned parameter snapshots".**

---

### Task 4: Parameter-aware cache reuse and strict legacy adoption

**Files:**
- Modify: features/evidence_package_storage.py lookup results, verified receipt matching and opt-in adoption
- Modify: features/group_distance_evidence_package.py run entry and owner legacy reconstruction
- Modify: features/group_axis_potential_field.py run entry and owner legacy reconstruction
- Modify: adapters/free_space_evidence_package.py _read_cache and run_free_space_package
- Modify: test/test_evidence_package_lifecycle.py
- Modify: test/test_evidence_package_freshness.py
- Modify: test/test_free_space_evidence_package.py
- Modify: test/test_evidence_package_processing.py and test/test_evidence_package_processed_readback.py

**Interfaces:**
- Add compare_receipt_parameters(cached_contract, current_contract) -> dict[str, object], delegating parameter semantics to Task 1 comparison.
- Introduce the frozen lookup objects and exact signatures below. Frozen dataclasses alone are insufficient: __post_init__ detaches and recursively freezes every mapping with the Task 1 _freeze helper. The historical objects never alias a caller's mutable dictionaries.

~~~python
@dataclass(frozen=True, slots=True)
class RawCacheLookup:
    raw_output: EvidencePackageOutput
    cached_contract: Mapping[str, object]
    parameter_status: Mapping[str, object] | None
    reuse_origin: Mapping[str, object]
    def __post_init__(self):
        """Detach and freeze receipt audit containers before exposing them."""
        object.__setattr__(self, "cached_contract", _freeze(self.cached_contract))
        object.__setattr__(self, "reuse_origin", _freeze(self.reuse_origin))
        if self.parameter_status is not None:
            object.__setattr__(self, "parameter_status", _freeze(self.parameter_status))

@dataclass(frozen=True, slots=True)
class ProcessedCacheLookup:
    processed_output: EvidenceProcessedOutput
    parameter_status: Mapping[str, object] | None
    reuse_origin: Mapping[str, object]
    def __post_init__(self):
        """Retain immutable saved processing status and origin metadata."""
        object.__setattr__(self, "reuse_origin", _freeze(self.reuse_origin))
        if self.parameter_status is not None:
            object.__setattr__(self, "parameter_status", _freeze(self.parameter_status))

def load_raw_entry(path, *, cache_key, contract, package,
                   legacy_adopter=None) -> RawCacheLookup | None:
    """Return validated output together with its historical calculation receipt."""

def load_processed_entry(path, *, raw_output, processor, legacy_path=None,
                         legacy_processed_adopter=None) -> ProcessedCacheLookup | None:
    """Retain saved calculated parameters and adoption origin on processed reuse."""

def load_raw_output(path, *, cache_key, contract, package):
    """Preserve the existing bare-output API for legacy callers."""
    entry = load_raw_entry(path, cache_key=cache_key, contract=contract, package=package)
    return None if entry is None else entry.raw_output

def load_processed_output(path, *, raw_output, processor):
    """Preserve the existing processed-output API for legacy callers."""
    entry = load_processed_entry(path, raw_output=raw_output, processor=processor)
    return None if entry is None else entry.processed_output
~~~

- legacy_adopter(receipt, current_contract) returns a verified reconstructed historical typed contract or None. Its returned contract is never replaced with the current requested contract.
- Add legacy_candidate_contract(current_contract) -> dict[str, object] as a lookup hint built through the existing builder with only the new raw parameter_snapshot omitted. Existing processed parameters mappings stay intact. Try its exact legacy filename after a typed-key miss; this hint does not attest historical values.
- Add legacy_processed_cache_key(raw_output, processor) -> str using the original full-parameters key payload. It locates only an exact known old parameter set. load_processed_entry may also receive an explicitly supplied legacy_path; A does not scan every old processed warning variant.
- legacy_processed_adopter(saved_output, processor) returns a complete historical ParameterSnapshot or None. The owner's current schema must independently authorize the field/type/unit/nullable/impact contract; complete saved values are validated through capture_calculated, never resolve/default expansion.
- The three run entries opt in to reconstruct_legacy_processed_snapshot only for an explicitly typed processor and derive its one exact old filename through legacy_processed_cache_key. Free space uses the authenticated _read_processed_cache_entry for this lookup. Unknown old warning keys are not scanned in A; the explicit legacy_path loader argument is sufficient for targeted importer/test use and B extends discovery.
- Preserve every public top-level runner result key. Put raw status under cache_status["parameter_status"], processed status under cache_status["processed_parameter_status"], and origin under cache_status["reuse_origin"] / cache_status["processed_reuse_origin"]. Adoption origin uses mode="adopted_legacy" and forces exact_match=False while retaining any warning records.
- Free space retains its authenticated adapters: add AuthenticatedFreeSpaceLookup(document, cached_contract, parameter_status, reuse_origin), _read_cache_entry(path, cache_key, secret, *, expected_parameter_snapshot=None, legacy_adopter=None), and _read_processed_cache_entry(path, *, raw_output, processor, secret, legacy_path=None, legacy_processed_adopter=None). Existing _read_cache/_read_processed_cache wrappers continue returning the old document/output shape. The new adapter entries authenticate the complete existing HMAC envelope before document decoding, historical reconstruction or shared parameter comparison. They must not pass an authenticated path directly to the ordinary unsigned JSON loader. Freeze the historical document/contract; the runner uses a detached wire.plain copy for publication-revision rebinding and retains the original receipt in cache_status. Ordinary raw lookup cannot replace this document-based storage boundary.

- [ ] **Step 1: Record manifest and add failing no-recompute tests with existing _missing_bundle and _forbidden in test_evidence_package_lifecycle.py.**

~~~python
def test_parameter_source_change_does_not_recalculate_distance(tmp_path, monkeypatch):
    """A source label changes audit information while preserving the calculation."""
    bundle = _missing_bundle()
    first = distance.run_group_distance_package(bundle, cache_directory=tmp_path)
    monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    again = distance.run_group_distance_package(
        bundle, cache_directory=tmp_path,
        parameter_sources={"clearance_mode": "gui"})
    assert again["cache_key"] == first["cache_key"]
    assert again["cache_hit"] is True
    assert again["raw_output"] == first["raw_output"]

def test_runner_retains_historical_raw_warning_values(tmp_path, monkeypatch):
    """The runner must compare the saved contract with current requested values."""
    from features.evidence_package_parameters import (
        ParameterImpact, ParameterSchema, ParameterSpec)
    schema = ParameterSchema(distance.PACKAGE_ID, "contract-warning/1", (
        ParameterSpec("review_m", float, 0.01, unit="m",
                      impact=ParameterImpact.REUSE_WITH_WARNING),))
    monkeypatch.setattr(distance, "build_group_distance_parameter_snapshot",
                        lambda *args, **kwargs: schema.resolve())
    first = distance.run_group_distance_package(_missing_bundle(), cache_directory=tmp_path)
    monkeypatch.setattr(distance, "build_group_distance_parameter_snapshot",
                        lambda *args, **kwargs: schema.resolve({"review_m": 0.02}))
    monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    again = distance.run_group_distance_package(_missing_bundle(), cache_directory=tmp_path)
    status = again["cache_status"]["parameter_status"]
    assert again["raw_output"] == first["raw_output"] and again["cache_hit"]
    assert status["calculated_parameters"]["review_m"] == 0.01
    assert status["requested_parameters"]["review_m"] == 0.02
    assert status["exact_match"] is False
    assert [item["parameter"] for item in status["warnings"]] == ["review_m"]

def test_runner_retains_historical_processed_warning_values(tmp_path, monkeypatch):
    """Warning reuse preserves actual transform parameters and skips both callbacks."""
    from features.evidence_package_parameters import (
        ParameterImpact, ParameterSchema, ParameterSpec)
    schema = ParameterSchema(potential.PACKAGE_ID, "processed-warning/1", (
        ParameterSpec("review_m", float, 0.01, unit="m",
                      impact=ParameterImpact.REUSE_WITH_WARNING),))
    base = _processor()
    old = field_core.EvidenceOutputProcessor(base.function_id, base.version,
        base.function, parameter_schema=schema)
    first = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path, output_processor=old)
    current = field_core.EvidenceOutputProcessor(base.function_id, base.version,
        _forbidden, {"review_m": 0.02}, parameter_schema=schema)
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    again = potential.run_group_axis_potential_package(
        _potential_sources(), cache_directory=tmp_path, output_processor=current)
    status = again["cache_status"]["processed_parameter_status"]
    assert again["processed_output"] == first["processed_output"]
    assert status["calculated_parameters"]["review_m"] == 0.01
    assert status["requested_parameters"]["review_m"] == 0.02
    assert status["exact_match"] is False and status["warnings"]
~~~

In freshness tests construct a typed contract with the builder rather than editing package_identity:

~~~python
def test_missing_snapshot_cannot_attest_exact_typed_match():
    """Legacy readability does not imply typed provenance."""
    from features.evidence_package_parameters import ParameterSchema
    legacy = _contract()
    arguments = {name: legacy[name] for name in (
        "package_id", "package_schema", "producer", "target_ids",
        "dependencies", "algorithm_version", "schema_version")}
    typed = build_evidence_package_contract(
        **arguments, parameter_snapshot=ParameterSchema(
            legacy["package_id"], "legacy-check/1", ()).resolve())
    status = evaluate_evidence_package_freshness(
        cached_contract=legacy, current_contract=typed)
    assert status["recompute_required"] is True
    assert status["parameter_status"]["exact_match"] is False
    assert "parameter_snapshot_missing" in {
        item["code"] for item in status["reasons"]}
~~~

- [ ] **Step 2: Run RED.** Run pixi run pytest test/test_evidence_package_lifecycle.py test/test_evidence_package_freshness.py -q.
- [ ] **Step 3: Implement verified identity-bearing matching, retaining full audit receipts.**

Keep current producer/version, source-content, query/dependency and payload validation. First verify each receipt fingerprint and declared key against its own saved contract/legacy identity. A typed hit additionally requires the independently requested computation key to match. Full contract dict equality must not gate reuse because source/audit metadata can differ. Delegate snapshot comparison to the independently current owner declaration; do not trust saved impacts to omit current calculation fields. The legacy branch is opt-in and owner-specific:

~~~python
parameter_status = compare_receipt_parameters(receipt["contract"], contract)
historical_contract = receipt["contract"]
origin = {"mode": "cache_hit", "origin_cache_key": receipt["cache_key"],
          "origin_contract": receipt["contract"],
          "origin_payload_fingerprint": receipt["raw_output"]["payload_fingerprint"]}
if parameter_status["recompute_required"]:
    if legacy_adopter is None:
        return None
    adopted = legacy_adopter(receipt, contract)
    if adopted is None:
        return None
    verified_status = compare_receipt_parameters(adopted, contract)
    if verified_status["recompute_required"]:
        return None
    historical_contract = adopted
    parameter_status = {**verified_status, "exact_match": False}
    origin = {**origin, "mode": "adopted_legacy",
              "verification_mode": "owner_reconstructed_parameters"}
return RawCacheLookup(output, historical_contract, parameter_status, origin)
~~~

An adopter reconstructs every calculated field from old validated raw sources/query/policy, dependencies and versions. Today's defaults, filenames, mtime or the current requested object alone cannot prove historical values. A supplied current fact may support reconstruction only after its complete historical input binding is independently recomputed and matches the validated old dependency fingerprint under the known historical algorithm; the old hash is not itself treated as decoded parameter data. If evidence is insufficient, preserve the old file as readable legacy and miss for the typed request; missing metadata alone is not corruption. For free space verify HMAC/document before reading historical parameter evidence and preserve its authentication domain/material for B. Keep existing _cached_sources_match and equivalent owner guards after lookup; a reconstructed parameter map cannot bypass current source-content validation.

Update all three runners to consume lookup objects, not the bare-output wrappers. Their precomputation status uses the historical contract and saved lookup status:

~~~python
raw = None if lookup is None else lookup.raw_output
cache_status = evaluate_evidence_package_freshness(
    cached_contract=None if lookup is None else lookup.cached_contract,
    current_contract=contract)
if lookup is not None:
    if lookup.parameter_status is not None:
        cache_status["parameter_status"] = dict(lookup.parameter_status)
    cache_status["reuse_origin"] = dict(lookup.reuse_origin)
if processed_lookup is not None:
    if processed_lookup.parameter_status is not None:
        cache_status["processed_parameter_status"] = dict(processed_lookup.parameter_status)
    cache_status["processed_reuse_origin"] = dict(processed_lookup.reuse_origin)
~~~

The public publication status can still describe the fresh current publication. cache_status is the historical reuse decision and must never be recalculated as current-contract versus itself. On misses record the existing recompute reasons. On warning hits the returned original output keeps its historical snapshot; no new current requested values are written into calculated_parameters.

Legacy discovery occurs before scheduling calculation: after the typed filename misses, derive the prior raw contract identity without parameter_snapshot, try that exact filename, verify its old declared key against its own contract, then invoke the owner adopter. A never requires an old receipt to carry the new typed key. For free-space implementation-hash changes or unknown historical processed warning keys, retain explicit old-path support and record the family for B's verified scanning importer. Do not promise automatic discovery of every retained cache in A.

For processed adoption, first deserialize/verify the legacy receipt and its original payload digest, original processing_identity, complete raw_output_identity/raw_payload_fingerprint binding, processor id/version and complete saved parameters map. The adopter validates every saved value against the current owner schema through capture_calculated with exact field equality, then compare_parameter_snapshots must return recompute_required=False. Missing parameters cannot be filled with defaults. Return an in-memory typed attestation using dataclasses.replace(saved_output, parameter_snapshot=historical_snapshot), with the same original numeric channels and full parameters. Its computed typed identity uses the historical projection. Store the original legacy processing identity/payload digest in reuse_origin, mode adopted_legacy, exact_match=False; preserve warning differences. No transform is called.

Provide this restricted helper for the opt-in ordinary and authenticated processed loaders. The caller has already verified the original payload and raw binding; unchanged explicit recipe id/version is the owner's compatibility declaration. Schema IDs, shape and field contracts still undergo the Task 1 comparison after reconstruction:

~~~python
def reconstruct_legacy_processed_snapshot(saved_output, processor):
    """Capture complete saved recipe values without borrowing current defaults."""
    schema = processor.parameter_schema
    if (schema is None or saved_output.processor_id != processor.function_id
            or saved_output.processor_version != processor.version
            or set(saved_output.parameters) != {item.name for item in schema.specs}):
        return None
    try:
        return schema.capture_calculated(saved_output.parameters,
            sources={name: "legacy-receipt" for name in saved_output.parameters})
    except (TypeError, ValueError):
        return None
~~~

A leaves adopted legacy files unchanged and repeats their verified lookup on later calls; do not persist an unaudited typed copy that loses adoption origin. Typed ordinary misses may use the existing writers. B owns durable migrated receipt shells and discovery of old variants whose exact keys cannot be derived. It must exercise the pre-A real fixtures retained at preflight.

- [ ] **Step 4: Add actual 1 -> 2 -> 1 and adoption regressions.**

Add these lifecycle tests using the existing _processor factory and actual run entries:

~~~python
def test_processed_parameter_versions_restore_without_transform(tmp_path, monkeypatch):
    """A restored effective value selects its original processed version."""
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec
    schema = ParameterSchema(potential.PACKAGE_ID, "processed-versions/1", (
        ParameterSpec("value", float, 1.0),))
    base = _processor()

    def configured(value, function):
        """Create the same owned recipe at a chosen effective value."""
        return field_core.EvidenceOutputProcessor(base.function_id, base.version,
            function, {"value": value}, parameter_schema=schema)

    first = potential.run_group_axis_potential_package(_potential_sources(),
        cache_directory=tmp_path, output_processor=configured(1.0, base.function))
    second = potential.run_group_axis_potential_package(_potential_sources(),
        cache_directory=tmp_path, output_processor=configured(2.0, base.function))
    assert first["processed_output"].processing_identity != second["processed_output"].processing_identity
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    restored = potential.run_group_axis_potential_package(_potential_sources(),
        cache_directory=tmp_path, output_processor=configured(1.0, _forbidden))
    assert restored["processed_output"] == first["processed_output"]

def test_verified_distance_legacy_receipt_reuses_and_reports_origin(tmp_path, monkeypatch):
    """A known old raw key is adopted before the producer can run."""
    from features import evidence_package_storage as storage
    bundle = _missing_bundle()
    first = distance.run_group_distance_package(bundle, cache_directory=tmp_path)
    legacy = storage.legacy_candidate_contract(first["contract"])
    old_path = tmp_path / (legacy["package_identity"] + ".json")
    storage.save_raw_output(old_path, cache_key=legacy["package_identity"],
                            contract=legacy, raw_output=first["raw_output"])
    retained = old_path.read_bytes()
    (tmp_path / (first["cache_key"] + ".json")).unlink()
    monkeypatch.setattr(distance, "calculate_group_pair_distances", _forbidden)
    again = distance.run_group_distance_package(bundle, cache_directory=tmp_path)
    assert again["cache_hit"] and again["raw_output"] == first["raw_output"]
    assert old_path.read_bytes() == retained
    assert again["cache_status"]["reuse_origin"]["mode"] == "adopted_legacy"
    assert again["cache_status"]["parameter_status"]["exact_match"] is False

def test_exact_known_legacy_processed_receipt_skips_transform(tmp_path, monkeypatch):
    """Complete saved parameters permit opt-in adoption without today's defaults."""
    from features.evidence_package_parameters import ParameterSchema
    base = _processor()
    first = potential.run_group_axis_potential_package(_potential_sources(),
        cache_directory=tmp_path, output_processor=base)
    typed = field_core.EvidenceOutputProcessor(base.function_id, base.version,
        _forbidden, parameter_schema=ParameterSchema(
            potential.PACKAGE_ID, "complete-empty-parameters/1", ()))
    monkeypatch.setattr(potential, "aggregate_group_axis_potential_outputs", _forbidden)
    adopted = potential.run_group_axis_potential_package(_potential_sources(),
        cache_directory=tmp_path, output_processor=typed)
    assert adopted["processed_output"].outputs == first["processed_output"].outputs
    status = adopted["cache_status"]["processed_parameter_status"]
    assert status["exact_match"] is False and not status["recompute_required"]
    assert adopted["cache_status"]["processed_reuse_origin"]["mode"] == "adopted_legacy"
~~~

Add this direct rejection test in the lifecycle file:

~~~python
@pytest.mark.parametrize("impact,accepted", [
    ("recompute_required", False), ("reuse_with_warning", True)])
def test_legacy_adopter_must_match_and_preserve_historical_values(tmp_path, impact, accepted):
    """The post-adopter gate rejects changes or retains warning values and origin."""
    from features import evidence_package_storage as storage
    from features.evidence_package_parameters import (
        ParameterImpact, ParameterSchema, ParameterSpec)
    first = distance.run_group_distance_package(_missing_bundle(), cache_directory=tmp_path)
    schema = ParameterSchema(distance.PACKAGE_ID, "adoption-guard/1", (
        ParameterSpec("review_m", float, 0.01, unit="m",
                      impact=ParameterImpact(impact)),))
    arguments = {name: first["contract"][name] for name in (
        "package_id", "package_schema", "producer", "target_ids", "dependencies",
        "algorithm_version", "schema_version")}
    calculated = field_core.build_evidence_package_contract(
        **arguments, parameter_snapshot=schema.resolve())
    current = field_core.build_evidence_package_contract(
        **arguments, parameter_snapshot=schema.resolve({"review_m": 0.02}))
    legacy = storage.legacy_candidate_contract(calculated)
    old_path = tmp_path / "retained-legacy.json"
    storage.save_raw_output(old_path, cache_key=legacy["package_identity"],
                            contract=legacy, raw_output=first["raw_output"])
    retained = old_path.read_bytes()
    lookup = storage.load_raw_entry(old_path, cache_key=current["package_identity"],
        contract=current, package=distance.build_group_distance_evidence_package(),
        legacy_adopter=lambda receipt, wanted: calculated)
    if accepted:
        assert lookup is not None
        assert lookup.cached_contract["parameter_snapshot"]["calculated_parameters"]["review_m"] == 0.01
        assert lookup.parameter_status["calculated_parameters"]["review_m"] == 0.01
        assert lookup.parameter_status["requested_parameters"]["review_m"] == 0.02
        assert lookup.parameter_status["warnings"] and not lookup.parameter_status["exact_match"]
        assert lookup.reuse_origin["mode"] == "adopted_legacy"
    else:
        assert lookup is None
    assert old_path.read_bytes() == retained
~~~

Add these processed readback tests using its existing _raw/_package/_process helpers:

~~~python
def test_legacy_processed_warning_keeps_origin_without_transform(tmp_path):
    """An explicitly located old warning version preserves its historical values."""
    from features import evidence_package_storage as storage
    from features.evidence_package_parameters import (
        ParameterImpact, ParameterSchema, ParameterSpec)
    raw = _raw()
    old_processor = core.EvidenceOutputProcessor("saved-process", "1", _process,
                                                {"review_m": 0.01})
    saved = _package(old_processor).process_output(raw, package_freshness="fresh")
    old_path = tmp_path / "known-legacy-processed.json"
    storage.save_processed_output(old_path, saved)
    retained = old_path.read_bytes()
    schema = ParameterSchema(raw.package_id, "review-parameters/1", (
        ParameterSpec("review_m", float, 0.02, unit="m",
                      impact=ParameterImpact.REUSE_WITH_WARNING),))

    def forbidden(*args, **kwargs):
        """Expose an accidental callback while the loader is verifying bytes."""
        pytest.fail("legacy readback executed a transform")

    processor = core.EvidenceOutputProcessor("saved-process", "1", forbidden,
                                            parameter_schema=schema)
    lookup = storage.load_processed_entry(tmp_path / "typed-missing.json",
        raw_output=raw, processor=processor, legacy_path=old_path,
        legacy_processed_adopter=storage.reconstruct_legacy_processed_snapshot)
    assert lookup is not None and lookup.processed_output.outputs == saved.outputs
    assert lookup.parameter_status["calculated_parameters"]["review_m"] == 0.01
    assert lookup.parameter_status["requested_parameters"]["review_m"] == 0.02
    assert lookup.parameter_status["warnings"] and not lookup.parameter_status["exact_match"]
    assert lookup.reuse_origin["mode"] == "adopted_legacy"
    assert old_path.read_bytes() == retained

def test_legacy_processed_missing_parameters_cannot_inherit_defaults(tmp_path):
    """An incomplete historical map remains a miss even with today's defaults."""
    from features import evidence_package_storage as storage
    from features.evidence_package_parameters import ParameterSchema, ParameterSpec
    raw = _raw()
    saved = _processed(raw)
    old_path = tmp_path / "incomplete-legacy.json"
    storage.save_processed_output(old_path, saved)
    schema = ParameterSchema(raw.package_id, "incomplete/1", (
        ParameterSpec("nested", dict), ParameterSpec("added", float, 1.0)))

    def forbidden(*args, **kwargs):
        """Make transform execution observable during a read-only lookup."""
        pytest.fail("loader executed a transform")

    processor = core.EvidenceOutputProcessor(saved.processor_id,
        saved.processor_version, forbidden, {"nested": {"items": [1, 2]}},
        parameter_schema=schema)
    assert storage.load_processed_entry(tmp_path / "typed-missing.json",
        raw_output=raw, processor=processor, legacy_path=old_path,
        legacy_processed_adopter=storage.reconstruct_legacy_processed_snapshot) is None
~~~

Also damage saved source/query/version and assert a preserved-byte miss; the existing source guard still executes. In free-space tests use the authenticated preflight fixture, its original declared key and its matching .free_space_cache_key to exercise _read_cache_entry at the known old path; prove HMAC/document validation and complete historical snapshot reconstruction without calling execute_analysis_request. A foreign key domain or altered authenticated document must miss. The fixture's pre-A implementation hash may prevent normal current-key runner discovery; record that limit explicitly. B owns verified cross-implementation compatibility mapping and must prove current runner no-recompute reuse with this true old fixture. JSON-only receipts cannot establish authenticated reuse.

- [ ] **Step 5: Run GREEN.** Run pixi run pytest test/test_evidence_package_lifecycle.py test/test_evidence_package_readback.py test/test_evidence_package_processing.py test/test_evidence_package_processed_readback.py test/test_evidence_package_saved_processed_consumer.py test/test_free_space_evidence_package.py -q. Expect PASS.
- [ ] **Step 6: Inspect diff and commit with jj commit -m "feat: verify parameter-aware receipt reuse and legacy adoption".**

---

### Task 5: Acceptance, architecture synchronization and Plan B handoff

**Files:**
- Modify: docs/software-architecture.md
- Modify: docs/project/parameter-and-cache-ownership-note.md
- Create: docs/superpowers/handoffs/2026-11-15-plan-a-accepted.md

- [ ] **Step 1: Record final manifest and audit ownership/immutability.**

Add to test_evidence_package_parameters.py:

~~~python
def test_downstream_cannot_mutate_historical_parameters():
    """Consumers can inspect the owner snapshot without changing its values."""
    snapshot = _schema().resolve()
    before = snapshot.to_json()
    with pytest.raises(TypeError):
        snapshot.calculated_parameters["width_m"] = 2.0
    with pytest.raises(TypeError):
        snapshot.parameter_sources["width_m"] = "downstream"
    assert snapshot.to_json() == before
~~~

Retain existing EvidencePackageDependency and raw output immutability tests. Audit every touched function for docstrings and important blocks for intent comments.

- [ ] **Step 2: Run the acceptance set once after fixes.**

Run: pixi run pytest test/test_evidence_package_parameters.py test/test_evidence_package_processing.py test/test_evidence_package_readback.py test/test_evidence_package_processed_readback.py test/test_evidence_package_saved_processed_consumer.py test/test_evidence_package_freshness.py test/test_evidence_package_lifecycle.py test/test_free_space_evidence_package.py test/test_group_distance_evidence_package.py test/test_group_distance_clearance.py test/test_group_distance_route_repair.py test/test_group_axis_distance_modulation.py -q

Expected: PASS. Record actual counts/duration; do not claim a full repository suite or real-model replay unless executed.

- [ ] **Step 3: Update architecture and handoff.**

Record workspace, accepted parent and nonempty commits; changed files; exact tests/results; snapshot schema, nullable/value contracts and impact projection; warning behavior; lookup return types and authenticated wrappers; legacy adoption rules and any family with insufficient provenance; unresolved risks. Record the retained `test/fixtures/cache_migration/pre_parameter_sidecar/` fixture manifest and original pre-A implementation/backend hashes. Plan B starts from the accepted A commit and consumes these exact snapshots and fixtures in CacheStore. Its entry point is model-side resolution, locks, migration and authentication preservation, without inventing another parameter identity. Output-port split and intermediate persistence remain deferred to the fresh C review.

- [ ] **Step 4: Inspect and commit handoff.**

~~~powershell
jj status
jj diff --stat
jj diff --git
jj commit -m "docs: accept Plan A and hand off parameter receipts to Plan B"
jj --ignore-working-copy log -r "@-" -n 1 --no-graph
~~~

## Self-Review and Grill Dispositions

| Challenge | Resolution |
| --- | --- |
| source="gui" changes version or causes full-contract miss | Tasks 1 and 4 exclude source labels from identity and reuse matching |
| warning knobs secretly affect identity | Task 1 projects only recompute_required; Task 2 shares projection |
| warning reuse rewrites calculated values | Historical snapshot immutable; requested values live in status with exact_match=False |
| hints admit bool or nonfinite input | Task 1 explicit runtime validation |
| absent height-band datum changes schema type | Task 1 nullable is independent of REQUIRED/default; Task 3 uses one stable nullable dict declaration |
| file weakens impacts to omit calculation fields | Compare saved declarations against the independently current owner schema |
| changed defaults invent old values | Readback never resolves defaults; Task 4 requires historical evidence |
| all old caches unnecessarily recalculated | Legacy readers survive and strict receipt-only adoption reuses verified bytes |
| old receipt falsely becomes exact typed evidence | Missing snapshot blocks exact typed match; adoption is separately reported |
| adopter returns an incompatible typed contract | Task 4 performs a mandatory second comparison and rejects recompute_required |
| cache loader erases warnings/origin before runner publication | RawCacheLookup/ProcessedCacheLookup carry historical contracts, status and origin to cache_status |
| unsigned lookup replaces authenticated free space | Adapter-specific lookup entries verify HMAC before shared comparison |
| fingerprint-only checkpoint skips missing work | Complete result-key scope and valid route/exact records are required before completed_sources |
| CLI threshold reuses a prior policy's checkpoint | Task 3 binds actual inputs, baseline scope, policy and method before exposing overrides |
| source refactor strands all legacy implementation-derived keys | Preflight retains true pre-A fixtures; A records discovery limits; B verifies explicit compatibility mapping |
| arbitrary plane/slab defaults | Task 3 captures validated required request context |
| downstream edits upstream knobs | Owner-local schemas and immutable result/snapshot boundary |
| circular import | Parameter module uses standard-library helpers, never field_core |
| failure pollutes owner workspace | Isolated A workspace, recorded parents and nonempty checkpoints |
| A silently implements B/C | Handoff explicitly defers storage migration/output split/intermediates |

Coverage: Tasks 1-2 define parameters/receipts, Task 3 wires existing owners, Task 4 protects reuse/legacy evidence, Task 5 verifies and hands off. New symbols are declared above and tests use existing fixture helpers at their actual files.

