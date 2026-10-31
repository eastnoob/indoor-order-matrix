# Global Arrangement-Pattern Evidence Package (Draft v1)

**Status:** Draft retained for later review. Implementation is deferred until the furniture-group potential evidence and its direction channels are implemented and reviewed. No runtime implementation or IFC validation is claimed.

## Purpose and boundary

Describe arrangement-pattern evidence across all eligible authored furniture groups in one analysis plane/space under one common arrangement standard. The public unit remains one authored `furniture_group`; each group's result is queried against the whole-space group set. Region splitting, position scopes, and group-internal single-furniture arrangement are not semantic boundaries. Group-internal arrangement stays suppressed or audit-only.

This package describes a whole-space pattern. It does not select candidate groups, infer membership, partition the space, choose a winner, or assign potential, participation, strength, probability, or attribution. Position fit and position confidence are descriptive diagnostics only.

Future runtime input is the pinned real IFC only: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, subject to the existing source-identity gate in the group-attribution plan. Do not create synthetic furniture, layout, geometry, or preset readings. This draft does not require or claim an IFC run.

## Proposed contract

Reuse `FieldResultEnvelope` / `EvidenceChannelRecord`; do not add another field kernel or result registry.

| Contract part | Proposed minimum |
| --- | --- |
| Target | One eligible authored furniture group: canonical `target.kind=furniture_group`, `target.id=<authored group id>`, and stable `target.identity` as required by `FieldResultEnvelope` (for example `ifc-group:<GlobalId>`). Authored membership is source fact, not ground truth. |
| Query | One complete analysis-plane/space identity, one declared arrangement standard/version, and the sorted identity set of all eligible groups in that plane/space. Every target envelope uses the same query. Do not encode a region or `position_scope` as a query boundary. |
| Atomic observations | (1) per-group observed plan position/proxy and its source references; (2) a list of independent whole-space pattern hypotheses, each with class/description, participating group IDs, frame and basis, expected locations/slots when supportable, per-group assignment/residual records, coverage, and ambiguity/conflict references; (3) separate diagnostic fit/confidence fields if computed. Preserve multiple observations, including incompatible or overlapping hypotheses; no selected grammar field. |
| Active descriptive channels | `pattern_observations` carries all supported whole-space descriptions and their evidence; `position_fit` and `position_confidence` may be emitted only as diagnostic channels with explicit method/limits. No channel is an input to candidate membership or a strength/readout scalar. |
| Status and reason | Preserve raw envelope and per-channel status using the existing `FieldResultStatus` vocabulary: `computed` only for complete declared input/requirements; `partial` when some observations are usable but coverage is incomplete; `not_available` when the query is valid but evidence cannot support a reading; `not_evaluated` when intentionally suppressed/out of contract; `invalid` for malformed or unusable inputs; `outside` when the target/query is outside the declared domain; and `ambiguous` when competing interpretations prevent one determinate reading. Attach stable reason codes and explanation, including missing/invalid group geometry, unsupported plane/frame, incomplete group coverage, unresolved ambiguity or source conflict, and suppressed group-internal analysis. Never encode unavailable evidence as zero or silently drop competing observations. (`FieldStatus` sample states remain a separate projection concern.) |
| Provenance/source references | Record IFC path and verified source fingerprint, IFC project/schema identity, authored group GlobalIds and member/source IDs, geometry representation/placement references, source unit and conversion, analysis-plane ID/frame, query group-set identity, recipe/algorithm/schema versions, authored versus inferred frame/slot basis, and links from every atomic observation to its contributing group/source records. Keep lower-level member observations audit-only. |
| Cache identity | Derive from the complete envelope boundary: canonical target; whole-space query and sorted eligible group IDs; plane/frame and units; channel declarations; source IFC fingerprint and relevant group/member geometry identities; recipe, algorithm, and schema fingerprints. A rendered image, scalar sample, or manifest is not cache identity. A changed source, eligible set, plane, query standard, channel declaration, or algorithm invalidates the affected envelope. |
| Plane-local visualization | Render in the exact query analysis plane, with all eligible groups and all returned pattern observations visible/indexable. Distinguish pattern hypotheses, group positions, proposed descriptive slots/assignments, residuals, uncertainty/conflict, and suppressed audit data by layer/style and legend. Show the complete scope, including groups with unavailable observations; do not crop to a region or only show a representative hypothesis. Manifest maps every envelope/observation/group ID to its plane-local view and records source fingerprint, plane/frame, units, and diagnostic-only boundary. No projection/rendering from a different plane may be implied. |

Target envelopes are per authored group for stable public identity; the query is global and identical across that plane/space. Pattern observations are represented as an ordered list of independent hypotheses. They may reference many groups, overlap, or conflict; the runner records those relations and does not merge them, partition the scope, or select a winner. The same hypothesis may be repeated by each target envelope only as a stable query-local reference, with one canonical observation record in the package manifest.

## Vocabulary and implementation boundary

`line`, `grid`, `pair`, `cluster`, and `unstructured` are existing diagnostic vocabulary, not approved semantic pattern classes or a complete taxonomy. `features/position_grammar.py` currently builds region-derived scopes (falling back to a room scope), excludes records by legacy flags, computes candidate grammars, and selects one candidate by position fit and tie-breaks for each scope. Its `position-fit` and heuristic `position-confidence` are legacy outputs, not calibrated probabilities or package authority. Group-internal assembly evidence is a separate debug helper.

Historical position specs proposed authored/line/pair/grid/multi-system grammars, selected simpler or best-fit grammars, and in places treated regions as scope boundaries. They document prior design and code history only; they do not override this draft's global query, non-selection boundary, or authored-group public unit. Historical material does not establish an OCTA ideal-slot mapping. That mapping remains open; do not invent one.

Known gaps before any implementation: legacy region-based scopes; one selected grammar; heuristic confidence; authored public slots are not wired at scope level; no pinned-IFC arrangement runner; and no multi-system handling. The current implementation must not be represented as satisfying the proposed package contract.

## Evidence ledger

| Classification | Evidence or claim | Consequence |
| --- | --- | --- |
| Existing fact | `position_grammar.py` groups furniture groups by `activity_region_id`/`region`, falls back to a room scope, and returns at most one selected grammar per scope; `line`, `pair`, `grid`, `cluster`, and `unstructured` candidates exist. | Legacy behavior only; it conflicts with global query and preservation of competing observations. |
| Existing fact | `group_assembly_grammar_evidence` describes extents within a furniture group as debug evidence. | Keep group-internal arrangement suppressed/audit-only. |
| Existing fact | Shared `FieldResultEnvelope` defines target/query/channels/status/provenance/projection and derives cache identity from complete input boundary fingerprints; existing group evidence packages use authored furniture-group units. | Reuse the envelope and source/provenance conventions. |
| Proposed contract | One common whole-space query over all eligible authored groups, with one group target per envelope and all pattern observations retained. | No semantic region boundary, pairwise candidate grouping, partition, membership, or winner. |
| Proposed contract | Fit/confidence remain descriptive diagnostics; status, reasons, source links, cache identity, and visualization stay attached to raw observations. | No missing-to-zero conversion and no hidden scalarization. |
| Not yet verified | The pinned IFC supports complete group positions, frames, authored slots, a stable global standard, or coexisting pattern observations. | Must be established from the real IFC when a future runtime task is authorized; this draft does not claim coverage. |
| Not yet verified | Appropriate pattern-class taxonomy, multi-pattern representation/aggregation, diagnostic-only class policy, and OCTA ideal-slot relation. | Owner decisions remain open; do not infer these from legacy names. |

## Owner decisions

1. **Owner ruling for v1:** represent multiple coexisting or overlapping patterns as a list of independently supported hypotheses under the same global query. Preserve overlap/conflict references; do not merge them or select a winner. A future `multi_system` representation remains open until real IFC evidence requires it.
2. Should any pattern class be diagnostic-only, especially `pair`, `cluster`, or `unstructured`, and what operational reading (if any) is allowed for it?
3. **Open pending the potential package:** “one standard” means one comparison rule and channel contract for all eligible groups, not one absolute horizontal/vertical frame. Arrangement direction must come from the reviewed furniture-group potential direction channels. Existing `overall_group_axis` and `layout_axis` are geometric trend descriptors, not a complete potential; they are not automatically interchangeable with its direction channels. Missing direction evidence yields `not_available` or `partial`; the package must not silently substitute world-XY or analysis-plane U/V as semantic direction.
4. Is an OCTA ideal-slot mapping wanted? If so, what historical/source evidence justifies the mapping? Until answered, it stays unspecified.
5. What is the minimum support/coverage needed to emit a pattern observation, and how should partial whole-space coverage be represented without selecting a winner? The first runner may emit hypotheses with explicit `partial` coverage and leave threshold calibration open.

## Self-check

- Design-only deliverable: no production implementation, tests, IFC, or adapter was modified by this spec; the owner separately updated the main plan to defer this package until the potential evidence is complete.
- No IFC was opened, run, or validated; no runtime result is claimed.
- No synthetic furniture/layout/geometry or preset reading was created or proposed as validation evidence.
- Global analysis-plane query, authored-group public unit, audit-only group-internal arrangement, non-selection boundary, uncertainty retention, position-diagnostic-only semantics, `target.identity`, and list-of-hypotheses representation are stated explicitly. Direction source remains deferred to the reviewed potential package.
