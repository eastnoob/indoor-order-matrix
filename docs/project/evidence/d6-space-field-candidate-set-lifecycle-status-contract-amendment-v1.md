# D6 Candidate-Set Lifecycle Status-Contract Amendment v1

- Date: 2026-10-05
- Branch: `codex/d6-analysis-domain-layout-handoff`
- Status: bounded design evidence; not implementation-ready
- Package: `outputs/design/live_ifc_candidate_set_lifecycle_status_contract/amendment_v1/`
- Review input: the user-provided summary of three independent-review findings; no lifecycle-specific independent-review record was found in this repository.

## Amendment

This package resolves three gaps in the repaired lifecycle contract at the design-evidence level. Names and records here are fixture vocabulary, not frozen production schema.

1. **Candidate lineage.** A logical `candidate_id` remains stable. Every replacement receives a distinct `candidate_version_id` and a strictly increasing `version_ordinal` scoped to that candidate. The replaced version stays in the record, retains its confirmation and source provenance, and links to its successor. A replacement starts provisional and unconfirmed; confirmation does not transfer to it.
2. **Event order.** Replay uses `(occurred_at, sequence, event_id)` ascending. Timestamps are canonical UTC strings; `event_id` is a non-empty ASCII stable tie-breaker for equal timestamps and sequences. Empty and duplicate event IDs are invalid. This establishes reproducible replay order only; it does not infer causal priority or resolve conflicting authority. The fixture has multiple events and an equal-timestamp/equal-sequence pair.
3. **Authored-domain assignment.** The assignment record is separate from candidate lifecycle and evidence state. `absent` means no assignment relation was recorded; `unresolved` means an explicit assignment record exists but does not identify one domain; `assigned` names an authored `AnalysisDomain`. Assignment alone never confirms or selects a candidate. `user_confirmed` changes from false to true only on an explicit user `confirm_candidate` event targeting the active candidate version. Confirmation leaves `evidence_state` unchanged, so `diagnostic_only` can remain true after confirmation.

## Fixture scope and verification

The synthetic fixtures cover stable logical identity across replacement, preserved prior-version provenance, deterministic multi-event reduction and tie ordering, independent assignment and confirmation, diagnostic evidence after confirmation, and absent versus unresolved assignment. They make no claim about real-IFC behavior or production integration.

Run the bounded checks with:

```powershell
pixi run python -B outputs/design/live_ifc_candidate_set_lifecycle_status_contract/amendment_v1/verify_amendment.py
```

The verifier uses Python standard-library structural schema assertions, strict JSON parsing, two subprocess probe runs compared byte-for-byte, transition invariants, and SHA-256/byte-count checks for the source artifacts. The manifest excludes itself and the generated report to avoid cyclic hashes; the report records the verified manifest result. No full IFC adapter, full pytest, Blender, or production code is involved.

## Boundary

This amendment does not design an AnalysisDomain selector, UI, space-field behavior, Bayesian/ML method, adapter handoff, public API, or production lifecycle schema. It does not promote any automatic candidate or establish production readiness. Conflict resolution and reversal/undo semantics remain outside this bounded fixture.

STOP FOR LIFECYCLE AMENDMENT REVIEW
