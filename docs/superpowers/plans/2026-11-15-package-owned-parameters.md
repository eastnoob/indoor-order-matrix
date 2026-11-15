
# Package-Owned Parameters Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add typed package-owned parameter schemas, canonical effective-value fingerprints, and receipt snapshots while preserving existing cache behavior.

**Architecture:** Create features/evidence_package_parameters.py with immutable ParameterSpec, ParameterSchema, ParameterSnapshot, and ParameterImpact types. Bind optional snapshots to processor receipts and raw package contracts; identities use only effective values and schema version, while requested values and source labels remain audit metadata. CacheStore, sidecar migration, output-port splitting, and intermediate products are deferred.

**Tech Stack:** Python 3.12, frozen dataclasses, canonical JSON/SHA-256, pytest, Pixi, Jujutsu.

**Spec:** docs/superpowers/specs/2026-11-15-parameter-owned-sidecar-cache-design.md

## Global Constraints

- Python >=3.12,<3.13 via Pixi; run tests with pixi run pytest.
- English-first docstrings and intent comments for every new or modified project-owned function.
- Identity includes canonical effective parameters and config_schema_version only; source labels and requested values never change identity.
- Reject unknown/missing fields, bool-as-number, NaN/infinity, prohibited negatives, duplicate specs, and noncanonical unit forms.
- Preserve calculated parameters in historical receipts; requested parameters are current intent and may produce a warning.
- Do not implement CacheStore, migration, locking, output-port decomposition, or intermediate persistence.
- Do not touch the owner workspace or push/merge.

---

### Task 1: Typed parameter schema and snapshot

Files
- Create: features/evidence_package_parameters.py
- Create: test/test_evidence_package_parameters.py

Interfaces
- ParameterImpact is a string enum with recompute_required, reuse_with_warning, metadata_only.
- ParameterSpec is a frozen dataclass: name, value_type, default, unit, exposed, impact, minimum, maximum, choices.
- ParameterSchema is a frozen dataclass: package_id, schema_version, specs; method resolve(requested=None, *, sources=None) -> ParameterSnapshot.
- ParameterSnapshot is frozen and contains config_schema_version, effective_parameters, calculated_parameters, requested_parameters, parameter_sources, parameter_fingerprint, impacts.
- identity_payload() returns only schema version, effective values, and fingerprint; to_json() returns JSON-safe audit data.

- [ ] Write failing tests for default/CLI identity, invalid scalar rejection, and unknown/missing fields.

    def test_default_and_cli_same_fingerprint():
        schema = ParameterSchema(
            package_id="p", schema_version="p/parameters/1",
            specs=(ParameterSpec("width_m", float, 1.0, unit="m",
                                 minimum=0.0),))
        first = schema.resolve()
        second = schema.resolve({"width_m": 1.0}, sources={"width_m": "cli"})
        assert first.effective_parameters == second.effective_parameters
        assert first.parameter_fingerprint == second.parameter_fingerprint
        assert first.parameter_sources != second.parameter_sources

    @pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -1.0])
    def test_invalid_scalar_rejected(value):
        schema = ParameterSchema(
            package_id="p", schema_version="p/parameters/1",
            specs=(ParameterSpec("width_m", float, 1.0, unit="m",
                                 minimum=0.0),))
        with pytest.raises((TypeError, ValueError)):
            schema.resolve({"width_m": value})

- [ ] Run pixi run pytest test/test_evidence_package_parameters.py -q; expect collection or assertion failures because the module is absent.
- [ ] Implement frozen slot dataclasses, exact type checks (bool is never a number), finite/range/choice/unit validation, default expansion, source validation, deep immutability, stable ordering, and SHA-256 fingerprinting from schema version plus effective values. Reuse field_core canonical JSON helpers.
- [ ] Run the focused test file and add coverage for duplicate names, nested immutability, changed defaults retaining old snapshots, and deterministic key ordering.
- [ ] Commit with jj: feat: add typed evidence parameter snapshots.

---

### Task 2: Processed receipt metadata

Files
- Modify: features/field_core.py around EvidenceOutputProcessor, EvidenceProcessedOutput, process_output, and processed serialization/deserialization.
- Modify: features/evidence_package_storage.py processed_cache_key.
- Test: test/test_evidence_package_processing.py
- Test: test/test_evidence_package_processed_readback.py

Interfaces
- EvidenceOutputProcessor gains optional parameter_schema, parameter_sources, requested_parameters; parameters remains the callback-visible effective mapping.
- EvidenceProcessedOutput gains optional parameter_snapshot: ParameterSnapshot.
- resolve_parameter_snapshot() returns the typed snapshot or None for legacy processors.
- processing_identity includes snapshot.identity_payload() when present; source labels are excluded.
- Serialized v1 receipts include parameter_snapshot when present; missing field remains valid for legacy receipts.

- [ ] Add failing tests asserting calculated/requested/source metadata, equal effective values sharing identity, and JSON round-trip preserving the snapshot.
- [ ] Run the two focused files; expect failures for the new fields.
- [ ] Implement resolution once in the processor, retain immutable effective callback parameters, attach the snapshot to success and error results, and keep legacy processor behavior unchanged.
- [ ] Extend snapshot record decoding and processed_cache_key to use the same effective snapshot; reject malformed snapshots and accept absent legacy snapshots.
- [ ] Run pixi run pytest test/test_evidence_package_processing.py test/test_evidence_package_processed_readback.py test/test_evidence_package_saved_processed_consumer.py -q; expect PASS.
- [ ] Commit with jj: feat: persist typed processor parameter snapshots.

---

### Task 3: Raw package contract snapshots

Files
- Modify: features/field_core.py around build_evidence_package_contract and freshness validation.
- Modify: features/group_distance_evidence_package.py run/contract path.
- Modify: features/group_axis_potential_field.py run/contract path.
- Modify: adapters/free_space_evidence_package.py run/contract path.
- Test: test/test_evidence_package_freshness.py
- Test: test/test_group_distance_evidence_package.py
- Test: test/test_free_space_evidence_package.py

Interfaces
- build_evidence_package_contract accepts parameter_snapshot: ParameterSnapshot | None.
- Contract parameters contains the full snapshot audit object.
- package_identity payload contains only config_schema_version and parameter_fingerprint, when a snapshot is present.
- Existing callers without snapshots retain the current identity.
- Package schemas expose only already-validated SI values: group_distance clearance thresholds, free_space request plane/grid/height/tolerances, and group_axis_potential distance_modulation enabled state.

- [ ] Add failing tests proving source labels do not change identity and invalid clearance values are rejected.
- [ ] Run focused contract tests; expect failures.
- [ ] Implement contract normalization/validation and a parameters_changed freshness reason while keeping invalidation_scope whole_package.
- [ ] Add package-local schema builders and pass snapshots through current contract builders without changing mathematical formulas, callbacks, or filenames.
- [ ] Run pixi run pytest test/test_evidence_package_freshness.py test/test_group_distance_evidence_package.py test/test_free_space_evidence_package.py test/test_group_axis_distance_modulation.py -q; expect PASS.
- [ ] Commit with jj: feat: bind package contracts to effective parameters.

---

### Task 4: Acceptance and Plan B handoff

Files
- Modify: test/test_evidence_package_lifecycle.py
- Modify: test/test_evidence_package_freshness.py
- Create: docs/superpowers/handoffs/2026-11-15-plan-a-accepted.md

- [ ] Add tests for 1 -> 2 -> 1 reuse, historical calculated values versus current requested values, and immutable downstream dependency references.
- [ ] Run the Plan A focused set:
      pixi run pytest test/test_evidence_package_parameters.py test/test_evidence_package_processing.py test/test_evidence_package_processed_readback.py test/test_evidence_package_freshness.py test/test_evidence_package_lifecycle.py -q
      Expected: PASS.
- [ ] Run jj diff --check and scan the plan for TODO, TBD, and vague validation placeholders; audit docstrings/comments in modified project files.
- [ ] Write the handoff with workspace, accepted jj commit, changed files, focused test results, unresolved risks, and Plan B entry point: CacheStore sidecar resolution, migration, locking, and free-space authentication-key preservation. Explicitly state that output-port splitting and intermediate persistence are deferred.
- [ ] Commit with jj: docs: record Plan A acceptance and Plan B handoff.

## Plan A Self-Review

Spec coverage: Tasks 1-4 cover typed schemas, defaults, validation, canonical identity, source-independent receipts, package contract snapshots, edit/restore reuse, and downstream immutability. CacheStore/migration, output-port decomposition, and intermediate products are explicit non-goals.

Placeholder scan: no TODO or TBD remains in executable steps; all tests name concrete files and commands.

Type consistency: ParameterSnapshot is introduced in Task 1, consumed by Tasks 2-3, serialized by current v1 readers with an optional backward-compatible field, and recorded in the Task 4 handoff.

Handoff: docs/superpowers/handoffs/2026-11-15-plan-a-accepted.md names the accepted commit and exact Plan B entry point.

