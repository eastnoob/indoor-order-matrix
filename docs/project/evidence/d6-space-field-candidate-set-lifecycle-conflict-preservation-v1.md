# D6 Lifecycle Conflict-Preservation — Bounded Design Evidence v1

- Date: 2026-10-05
- Branch: codex/d6-analysis-domain-layout-handoff
- Status: proposal for contract review only
- Package: outputs/design/live_ifc_candidate_set_lifecycle_status_contract/conflict_preservation_v1/
- Predecessor: lifecycle amendment v1, checkpoint fa942a788c08301c9cf1fdec881a40bed1882706

## Basis and boundary

The amendment v1 contract orders events by (occurred_at, sequence, event_id). The final owner decision says conflicts have no automatic resolution and downstream domain promotion remains unavailable until explicit resolution. The D6 Space Field First Slice final independent review accepted limited diagnostic evidence and explicitly did not authorize production implementation; it is context, not a lifecycle conflict-policy approval.

Independent-review provenance for the amendment and conflict-preservation reviews is recorded in [`d6-space-field-candidate-set-lifecycle-independent-review-provenance-v1.md`](d6-space-field-candidate-set-lifecycle-independent-review-provenance-v1.md).

This package proposes the minimum conflict-preservation semantics needed to review that gap. Fixtures are synthetic contract examples. This package is only for contract review. It changes no production code, adapter, NeutralSceneV2, public API, formal test, dependency, IFC file, Blender file, amendment-v1 artifact, or repair-v1 artifact. It does not choose production status enums, a production conflict policy implementation, a selector, Bayesian/ML behavior, or AnalysisDomain/UI behavior.

## Proposed contract for review

1. Preserve the existing deterministic audit order (occurred_at, sequence, event_id ascending). Event ID order makes replay output reproducible; it does not establish authority or resolve semantic disagreement.
2. Compare events sharing an ordering key and relation scope before applying any event in that tie group. If their meanings are incompatible, retain each complete event and provenance record, mark the affected relation unresolved conflict, and block downstream promotion. Do not record a lexical event-ID winner as truth.
3. Review these conflict classes:
   - same-key confirmations of incompatible candidate versions within the same explicitly identified confirmation relation;
   - same-key assignments of incompatible authored domains within the same assignment relation;
   - replacement/confirmation events targeting a stale or inactive candidate version;
   - repeated identical semantic events versus contradictory events.
4. Distinct event IDs carrying the same semantic event are duplicate provenance records: retain all records and IDs, but allow one idempotent relation effect. Different semantic payloads within one relation are contradictory and remain unresolved.
5. A non-conflicting tie remains replayable in deterministic order. Assignment or confirmation in these examples does not itself promote downstream availability.

The relation scopes in the fixtures are supplied synthetic facts used to define each example. They do not establish a production selector or general exclusivity rule.

## Fixtures and verification

The package has synthetic truth for contradictory same-key confirmation, contradictory same-key authored-domain assignment, duplicate identical events, stale-version replacement/confirmation, and a non-conflicting deterministic tie. The standard-library probe records ordered IDs and relation outcomes. The verifier strictly parses JSON, runs the probe twice and compares bytes, checks expected truth and event provenance, asserts conflicts block promotion, keeps duplicate handling distinct, checks source hashes and byte counts, checks scoped whitespace and Git diffs, and verifies unrelated Git status rows remain unchanged.

Run:

```powershell
pixi run python -B outputs/design/live_ifc_candidate_set_lifecycle_status_contract/conflict_preservation_v1/verify_conflict_preservation.py
```

The manifest covers the design record and package inputs, excluding the generated report and manifest to avoid cyclic hashes. The report records the verified manifest. No real-IFC behavior or production integration is claimed.

## Owner decision table

No owner choice is recorded here. Select one response per row during contract review.

| Review item | APPROVE | REVISE | DEFER | Owner notes |
|---|---|---|---|---|
| Tie order is deterministic audit order only | [ ] | [ ] | [ ] | |
| Incompatible same-key confirmation and authored-assignment records remain unresolved with both provenances | [ ] | [ ] | [ ] | |
| Stale/inactive replacement or confirmation targets remain unresolved | [ ] | [ ] | [ ] | |
| Identical duplicate events retain provenance while applying one idempotent effect | [ ] | [ ] | [ ] | |
| Unresolved conflicts block downstream promotion | [ ] | [ ] | [ ] | |
| Overall contract package | [ ] | [ ] | [ ] | |

STOP FOR LIFECYCLE CONFLICT-PRESERVATION DESIGN REVIEW
