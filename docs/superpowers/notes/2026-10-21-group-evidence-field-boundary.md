# Group Evidence Field Boundary Note

- Date: 2026-10-21
- Scope: group-inference design only; no production implementation.

## Decision

For inferred furniture-group membership, the canonical object is a multi-channel evidence field over `object × candidate_group`.

A Gaussian distance or influence kernel is not the membership model. It may remain as one declared geometry/space evidence channel or as a diagnostic visualization channel. Existing free-space Gaussian support remains separate and must not be treated as probability or evidence fusion.

The generic `Field` contract can carry a structured/vector value with status, support, source ids, provenance, and explanation. A scalar membership-strength field is therefore a later projection of the evidence field, not the canonical evidence itself.

Any scalar projection must be a named, versioned aggregation layer with explicit parameters and calibration provenance. No uncalibrated equal-weight or hand-written weighted sum is approved as the default.

## Next design slice

Discuss and freeze these four sections with the owner before writing the full architectural spec or implementation plan:

1. channel definitions;
2. positive and negative evidence semantics;
3. evidence/status state machine;
4. minimum output structure.

The first slice does not implement a selector, unique partition, Bayesian posterior, or scalar weighting formula.

## Project-verified facts

The following facts are confirmed by the current repository and existing design records:

### Channel sources

- **Geometry**: group/member geometry, additive support area, centers, covariance, boundary gap, contact, positive-area overlap, and member-pair witnesses are already represented in `features/group_self_description.py`.
- **Pattern**: `features/position_grammar.py` provides authored, line, pair, grid, cluster, and unstructured grammar evidence. Its `position-fit` and `position-confidence` are diagnostic evidence, not membership strength; its confidence currently contains the legacy `0.5/0.3/0.2` heuristic and cannot be reused as a final group score.
- **Semantic**: ordinary type mismatch is recorded as `soft_negative`; explicit mutual exclusion is preserved as a conflict/veto candidate in the existing D6 design.
- **Space/context**: space observations depend on an explicit `AnalysisDomain`; missing domain/channel remains `not_available`. Context geometry may support boundary, barrier, or alignment observations but does not become a furniture-group node.
- **Status/provenance**: `features/field_core.py` supports generic structured values plus status, support, source ids, provenance, and explanation. Its status vocabulary is `established`, `conditional`, `unknown`, `outside`, `invalid`, and `not_available`. Group self-description additionally uses `computed`, `partial`, `not_available`, `invalid`, and `not_evaluated` in its evidence mapping.

### Existing boundary

- `features/group_self_description.py` currently exposes authored groups, group geometry, pair observations, space observations, and local-neighborhood diagnostics.
- `candidate_views` is explicitly `null` with `candidate_view_status="deferred"`.
- No current production field maps `object × candidate_group` to a member-level support/against record.
- `strength`, `support_area`, `coherence`, and `uncertainty` are distinct concepts. Existing group `strength` is deferred; directional strength/coherence describes geometry/orientation concentration and is not membership strength.
- The relation field must remain separate from physical occupancy/free-space semantics. Existing Gaussian group support is diagnostic only and is not probability or evidence fusion.

## Owner decision 1

**Resolved:** Pattern evidence is a first-class member evidence channel in the first slice. It records per-member residual, fit, model type, and provenance; it does not become a total membership score.

## Earlier open questions

The initial open-question list was superseded by the project audit below. Context separation, the candidate-source boundary, diagnostic aggregation recipes, and the shared Field transport are now resolved from the existing implementation and D6 decision records. The remaining unresolved items are listed under `Remaining owner questions`.

## Owner architectural principle: open Evidence → Field core

The group design is one consumer of a more general evidence-to-field inference framework. The core accepts an open set of typed evidence channels; future channels may be added or removed without changing the field contract.

Each channel contributes an evidence record with its own observation, polarity or relation, applicability, status, source references, and provenance. The field layer derives the current field value/status from the currently admitted evidence set. It must not retain stale influence from a channel that was removed.

Adding a channel may add support, opposition, uncertainty, or conflict. Removing a channel recomputes the field from the remaining channels. Evidence status is derived from availability, validity, and conflict rules; it is not a hidden numeric penalty and it is not required to be monotone with the number of channels.

The common rule is the evidence contract and status/provenance semantics, not one universal numeric transform. A channel-specific normalization or a later scalar projection must be explicitly named and versioned. If a new channel has no approved calibration, it remains visible in the structured evidence field without silently receiving a weight.

The group membership field, free-space field, and future fields may share this core contract while keeping their target domains and meanings separate.

## Project audit resolution

A second review of the implementation and D6 records resolves more of the earlier questions:

- **Context vs space**: keep them semantically separate. Context geometry is an evidence source/reference (wall, column, counter, lamp, alignment, barrier); the space field describes roles and observations inside an explicit `AnalysisDomain`. Context may feed a space/barrier observation, but it does not become a furniture node and must keep its own provenance.
- **Candidate source boundary**: the first production slice does not generate or select candidate groups. Candidate views are design-only diagnostics from declared scale/aggregation recipes; `candidate_views=null` and `candidate_view_status="deferred"` remain the production boundary. The candidate estimand is a member set and may overlap, be ambiguous, singleton, or unassigned.
- **Aggregation diagnostics**: the existing D6 owner decision already freezes the design-only recipe ids `selected_relation_connected`, `all_internal_pairs`, `max_span`, `complete_link_diagnostic`, and `min_gap`, alongside the parallel scale recipes. None is a production selector or winner.
- **Field transport**: the architecture maps relation fields through the shared `Field` core with exact lookup/batch lookup and structured `FieldSample` values. The existing `group_self_description` mapping remains an internal/diagnostic evidence record until a relation-field adapter is separately approved.
- **Known polarity rules**: ordinary semantic mismatch is soft negative; explicit mutual exclusion is a candidate-level hard veto; missing, invalid, and not-available are categorical states; geometry and space observations remain visible as evidence rather than being silently converted to a score.

## Grill-me self-check: corrected output boundary

The earlier suggestion to map every group `computed` result to `FieldStatus.ESTABLISHED`, and every `partial` result to `UNKNOWN`, was too coarse. The current group record contains usable diagnostics even when one channel or member is incomplete, while `FieldSample` deliberately forbids a value for `UNKNOWN`, `NOT_AVAILABLE`, `OUTSIDE`, and `INVALID`. That direct mapping would either claim more certainty than the evidence supports or discard useful evidence.

The smallest complete contract for the second project is therefore a generic immutable **evidence-field output envelope**. It is a transport and audit boundary, not a new job system or a universal scoring framework. It must carry:

- target/query identity, domain/frame, revision, channel set, and source fingerprint;
- a JSON-safe structured evidence value, including positive, negative, conflict, and missing channel records;
- the raw domain status (`computed`, `partial`, `not_evaluated`, `not_available`, `invalid`, `outside`, or `ambiguous`) without collapsing it;
- algorithm/schema versions, source ids, provenance, explanation, and cache identity;
- optional visualization/manifest metadata.

`FieldSample` remains the compatibility projection for consumers that require the shared `Field` API. A relation-field adapter may project to `ESTABLISHED`, `CONDITIONAL`, `UNKNOWN`, `OUTSIDE`, `INVALID`, or `NOT_AVAILABLE` only when the mapping is semantically justified, and it must retain the raw status plus a mapping reason in the envelope. `CONDITIONAL` stays reserved for an accepted substitute or representation limitation; it is not a synonym for group `partial`. `not_evaluated` must remain distinguishable from `not_available` and `unknown` until its cause is known.

The UI, cache, analysis, and visualization path is:

`evidence computation -> immutable envelope -> cache/artifact manifest -> FieldSample or field-layer-manifest projection -> UI/analysis/rendering`

Adding or removing a channel changes the source fingerprint and recomputes the envelope; no removed channel may leave stale influence in a cached result. The existing `build_field_layer_manifest` is the visualization shape to reuse, extended only by preserving raw channel/status metadata where a relation result cannot be represented by a six-state `FieldSample` alone.

This correction keeps the user-requested parity with the free-space field—UI handoff, cache identity, analysis access, and visualization—without creating a second field kernel or prematurely choosing a scalar membership score.

## Remaining owner questions

Only these design details still lack a project-level decision:

1. The final field names and requiredness rules for the generic envelope (`raw_status`, channel statuses, source fingerprint, and optional `FieldStatus` projection).
2. Whether the first relation-field adapter exposes the envelope directly to UI/analysis and creates `FieldSample` only at compatibility boundaries, or exposes both views as equal public outputs.

Scalar projection, fixed weights, selector choice, Bayesian/ML, and psychological calibration remain later-stage questions by design.

## Production-readiness audit

This design is sufficient to begin a bounded production slice for the shared output boundary: an immutable result envelope, deterministic cache identity, a compatibility projection to the existing `FieldSample`, and a visualization-manifest adapter. It is not sufficient to implement the complete group-inference field, candidate selector, or scalar membership aggregation. Those still require the candidate estimand, aggregation/status gates, and a reviewed implementation plan.

The branch is therefore ready for envelope-contract implementation only after the envelope field names and public-view boundary are frozen. The full group algorithm remains design-only.


## Owner decision 2: ideal-pattern availability

When a candidate has an explicit or otherwise admitted ideal pattern, the pattern channel emits two separate observations for each evaluable member:

- `pattern_conformity` as positive observation;
- `pattern_residual` as negative observation.

They are retained with model id, expected structure, status, and provenance. They are not thresholded or fused into a total score.

When no ideal pattern is defined or admitted for the candidate, the pattern polarity channel is **not available/not evaluated**. It contributes neither positive evidence nor negative evidence. Any built-in grammar fit retained for diagnostics is descriptive metadata only; it is not a zero-valued observation and it is not evidence that the member failed the pattern.

If an ideal pattern exists but required member data are missing or invalid, the pattern channel reports the corresponding missing/invalid state. It is never replaced by numeric zero.


