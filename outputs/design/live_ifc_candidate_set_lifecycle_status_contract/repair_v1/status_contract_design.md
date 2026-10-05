# D6 Candidate-Set Lifecycle Status-Contract Repair v1

- Date: 2026-10-05
- Status: design-only repair package; production names, fields, APIs, and selectors remain unfrozen
- Repair target: `outputs/design/live_ifc_candidate_set_lifecycle_status_contract/`
- Repair output: `outputs/design/live_ifc_candidate_set_lifecycle_status_contract/repair_v1/`

## Repair decision and branch handling

The repaired package stays on the existing branch `codex/d6-pairwise-channel-run2-repair-v2`. A new branch is not useful for this bounded documentation and fixture repair because the worktree already contains the D6 evidence set and the repair output is ignored under `outputs/`. The earlier branch should be organized before a later implementation-design branch is created:

1. Review the existing 46 pre-existing untracked paths and classify accepted evidence, logs, and disposable outputs.
2. Keep this repair record as the auditable evidence checkpoint; stage only the named record when the owner wants it tracked. Do not use `git add .`.
3. Remove or ignore disposable logs only after confirming that no evidence artifact depends on them.
4. Recheck a clean or intentionally scoped worktree, then branch from that checkpoint only after a later owner approval for implementation design.

This repair changes only the disposable design package and the named evidence record. It does not modify production code, adapters, NeutralSceneV2, public APIs, tests, dependencies, source IFC, or user Blender files.

## Why a repair was required

The original status-contract package used `provisional_diagnostic_only` as if it were both a lifecycle state and an evidence-quality state. That shape could not represent an explicit confirmation that leaves the evidence diagnostic, and it encouraged an overloaded status enum. The repair separates the source-of-truth layers and makes `provisional_diagnostic_only` a derived display label only.

The repaired package also makes two distinctions explicit:

- Explicit no-selection is a recorded relation: `selection_relation_present=true`, `selection_state=none`, and `selected_candidate_id=null`.
- An absent selection relation is different: `selection_relation_present=false`, with no selection relation object, meaning selection was not recorded.

Conflict is represented as a retained, unresolved relation between automatic and authored/user records. The package does not invent a production conflict-resolution rule.

## Evidence ledger

| Category | Evidence or proposal | Boundary |
|---|---|---|
| Observed evidence | The serialized real-IFC case contains eight retained automatic candidates in one candidate set, no authored domain, explicit no-selection, and no production promotion. | This package reuses serialized evidence and does not reopen the source IFC or rerun the adapter. |
| Observed evidence | The repaired lifecycle artifacts keep real-IFC context separate from synthetic controls. | Synthetic controls demonstrate contract relationships only. |
| Approved owner principles | Automatic candidates remain retained; there is no automatic winner; singleton does not confirm; authored/user domain takes downstream precedence; automatic candidates remain provenance; conflict is visible and unresolved; rejection preserves evidence; replacement preserves prior versions; evidence limits do not become winners. | These principles are taken from the final owner decision and are the governing input to this proposal. |
| Corrected proposal | Lifecycle, evidence, set facts, relations/events, authored assignment, and downstream availability are orthogonal layers. | Design proposal only; no production enum or public API is frozen. |
| Unresolved decision | Exact names, serialization, conflict authority, availability policy while conflict is visible, active-count rules, and formal AnalysisDomain promotion remain open. | Requires a later owner decision. |
| Assumption requiring validation | The recommended strict conflict view keeps downstream availability `not_available` until an explicit resolution event; authored precedence orders authority but does not erase disagreement. | This is a proposed interpretation, not an observed production behavior. |

The real case does not establish that any candidate was confirmed, rejected, replaced, manually edited, or conflict-resolved. Those actions appear only in synthetic controls.

## Corrected layer model

1. **Candidate-set facts.** Retained membership, retained count, active-version count, cardinality, assignment presence, ambiguity description, and selection relation state describe the set. They do not choose a candidate.
2. **Candidate-level evidence.** Geometry and source references, units, coordinate frame, analysis plane, uncertainty, and evidence quality describe a candidate version. `diagnostic_only`, `partial`, `invalid`, and `unsupported` belong here or to an explicitly scoped set-level evidence summary.
3. **Lifecycle actions and relations.** `confirm`, `reject`, `replace`, `assign_authored_domain`, `record_conflict`, and `manual_boundary_edit` are explicit events or relations with stable IDs, actor, time, reason, ordering, and provenance.
4. **Authored/user domain assignment.** An explicit authored or user relation identifies intended downstream domain input. Automatic candidates remain retained provenance when this relation takes precedence.
5. **Downstream availability.** Each consumer evaluates its required dependencies and returns a derived availability result. `not_available` is a dependency result, not a lifecycle action and not an automatic winner.

The recommended source of truth is the immutable facts plus explicit relations/events. Any compact status fields are derived read views.

## Proposed semantics of the requested terms

These are review vocabulary only. They are not production enum commitments.

| Term | Classification | Proposed semantics | Explicit non-meaning |
|---|---|---|---|
| `unassigned` | Set-level assignment fact / derived label | No authored or user assignment relation is recorded for the set. | Does not delete, hide, or reject candidates. |
| `ambiguous` | Set-level diagnostic descriptor / derived label | Multiple plausible active candidates or unresolved interpretations remain without a selection. | Is not a ranking or a winner. |
| `singleton` | Set-level cardinality fact | Exactly one active, non-replaced candidate version remains. | Does not imply confirmation or domain promotion. |
| `provisional_diagnostic_only` | Derived display label | Derived only from `lifecycle_state=provisional` and `evidence_state=diagnostic_only`. | Is never an independent source-of-truth state. |
| `user_confirmed` | Candidate-level lifecycle state | An explicit actor confirmed a stable candidate version or authored domain through a recorded event. | Cannot be inferred from singleton, score, geometry, or display order. |
| `rejected` | Candidate-level lifecycle state | An explicit actor rejected a candidate version for a recorded reason. | Does not erase evidence or source references. |
| `replaced` | Candidate-level lifecycle state / version relation result | A prior version was superseded by a new version through an explicit replacement relation. | Does not mutate or delete the prior version. |
| `conflict` | Cross-source relation and set/candidate display label | Automatic and authored/user records disagree and the disagreement remains unresolved. | Does not silently resolve by precedence. |
| `not_available` | Downstream availability state / derived label | A consumer evaluated dependencies and cannot produce the requested downstream result. | Is not zero, empty geometry, rejection, or a candidate winner. |
| `partial` | Candidate- or set-level evidence-quality state | Some required evidence is present while other evidence is missing or incomplete. | Does not mean complete availability. |
| `invalid` | Candidate- or set-level evidence-quality state | A present record fails an applicable validity check. | Does not authorize an unqualified fallback. |
| `unsupported` | Candidate- or set-level evidence-quality state | A representation or operation is outside the supported evidence contract. | Does not authorize fabrication. |
| `diagnostic_only` | Candidate- or set-level evidence-quality state | Evidence may be displayed and audited but cannot promote a formal domain or downstream result. | Does not claim the source fact is false. |

Evidence-quality values remain orthogonal to lifecycle actions. A confirmed candidate may still have `evidence_state=diagnostic_only`; confirmation records who chose it and does not improve evidence automatically.

## Contract-shape comparison

### Shape A: status fields

A snapshot can expose fields such as `candidate_set.status`, `candidate.status`, `selected_candidate_id`, `replaced_by`, and reason fields. This is easy to query and bind to a first UI. It also encourages one overloaded enum to carry cardinality, assignment, evidence quality, action history, conflict, and availability. Without an event log it loses ordering, makes replacement look destructive, and makes unresolved conflict difficult to preserve.

Status fields are therefore suitable only as a derived read model generated from explicit records.

### Shape B: explicit relations/events plus derived views

This shape stores immutable candidate-set and candidate-version facts, append-only evidence and lifecycle events, authored assignment relations, replacement references, and conflict relations. Candidate and set labels are deterministic views over those records.

It preserves provenance and history, keeps set and candidate scopes separate, permits visible unresolved conflict, and avoids freezing production names before owner review. It requires event validation and deterministic aggregation.

### Design-only recommendation

Use Shape B as the source of truth and derive compact status fields for display or query convenience. This is a design recommendation only. It does not freeze production enum names, serialization fields, public APIs, selectors, or downstream behavior.

## Transition contract

### Allowed transitions and relations

- `provisional` → `user_confirmed` only through an explicit `confirm` event naming a stable candidate version, actor, reason, ordered event, and provenance. Evidence may remain `diagnostic_only`.
- `provisional` → `rejected` only through an explicit `reject` event with actor, reason, ordered event, and provenance. Evidence remains retained.
- An active candidate version → `replaced` through an explicit `replace` relation that creates a new version and retains prior-version references.
- Candidate set → authored/user assignment through `assign_authored_domain`; automatic candidates remain provenance.
- Candidate set → `conflict` through `record_conflict`, retaining both sides and reason codes. `resolve_conflict` is deferred.
- An active version → a new version through `manual_boundary_edit`, retaining before/after geometry references, actor, reason, and ordered provenance. The old geometry is not mutated.

The proposal uses monotonic `event_sequence` per candidate-set lineage as the primary event order. A later owner decision may instead choose full timestamps plus a stable event-ID tie-break. Date-only values are not an ordering key.

### Forbidden transitions

- `singleton` → `user_confirmed` by automatic promotion.
- `diagnostic_only` → `user_confirmed` by relabeling or evidence limitation.
- `partial` → complete `available` without required evidence.
- `invalid` → available by substituting a bounding box or other unqualified fallback.
- `rejected` → absent by deleting evidence.
- `replaced` → absent by deleting the prior version.
- `conflict` → resolved by silently applying precedence.

No resurrection rule is proposed for rejected versions. Reuse after later review should create a new version or receive a separate explicit owner decision.

## Precedence, conflict, and aggregation

A qualified authored/user assignment has precedence for downstream domain use under the approved principle. Automatic candidates remain retained provenance, including source references, geometry, evidence quality, and prior actions.

If authored/user input disagrees with automatic candidates, the disagreement remains visible as `conflict`. Under the recommended strict view, unresolved conflict yields downstream `not_available` until an explicit resolution event exists. Whether a qualified authored domain may be consumed while the conflict badge remains visible is unresolved and must be decided later.

At set scope, retained `candidate_count` includes historical records. `active_candidate_count` excludes replaced versions and may report rejected records separately. `singleton` is true only when one active version remains. `ambiguous` is true only when the owner-defined plausibility/interpretation rule says multiple current possibilities remain; this proposal does not choose thresholds. `unassigned` is true when no authored/user assignment relation exists.

At candidate scope, lifecycle state is derived from the latest valid ordered lifecycle event while all events remain queryable. Evidence states are independently retained. Replaced versions remain inspectable through version references and are excluded from the active version view.

A set-level view should expose evidence badges instead of forcing `partial`, `invalid`, `unsupported`, and `diagnostic_only` into one total order. A compact display label must not change downstream gates.

## Null and `not_available` propagation

`null` records the absence of a relation or selected ID. Explicit no-selection uses `selected_candidate_id=null` together with `selection_state=none` and `selection_relation_present=true`. An absent relation uses `selection_relation_present=false` and no relation object.

`not_available` is a derived downstream result. Missing qualified domain, unresolved conflict, invalid required geometry, unsupported required representation, or incomplete required evidence propagates to downstream `not_available`. A partial diagnostic result may retain successful members, but a full downstream result remains unavailable until required dependencies pass. Zero, empty geometry, a scene bounding box, or a diagnostic frame is not a substitute for a qualified result.

## Identity and provenance requirements

- `candidate_set_id` identifies one candidate-set lineage for a source/context snapshot.
- `candidate_id` identifies logical candidate lineage; `candidate_version_id` identifies an immutable geometry or edit version.
- `event_id` and `relation_id` are immutable and unique within the relevant record scope.
- Replacement records retain both prior and replacement version references.
- IFC GlobalId/STEP IDs and artifact paths remain source references, not lifecycle IDs.
- Records carry real/synthetic class, source artifact and IDs, units, coordinate frame, analysis plane, generator/adapter version, assumptions, uncertainty, and diagnostic restrictions.
- Lifecycle events carry actor, recorded time, event sequence, action type, reason code, stable targets, and a non-production flag.

## UI implications

- **Confirmation:** show all retained candidates, require an explicit target and actor/reason provenance, and give a singleton a confirmation-needed cue rather than a confirmed badge.
- **Rejection:** remove the candidate from the active selection view while retaining an evidence-history affordance, reason, and provenance.
- **Replacement:** create a new version, show prior versions in history, and make the replacement relation inspectable.
- **Manual boundary editing:** record before/after geometry references as an ordered new-version event.
- **Conflict:** show automatic and authored/user sides together, show the reason, disable silent promotion, and expose a resolution path only after owner rules exist.
- **Availability:** render `not_available` and partial evidence as distinct badges with dependency reasons; do not render an empty successful result.

## Real-IFC evidence context and synthetic controls

The real-IFC fixture is limited to the approved serialized context:

- eight retained automatic candidates;
- no authored domain;
- explicit no-selection (`selection_relation_present=true`, `selection_state=none`, `selected_candidate_id=null`);
- no production promotion;
- candidate records separated into `lifecycle_state=provisional` and `evidence_state=diagnostic_only`;
- derived display label `provisional_diagnostic_only` only.

The real case is not used as evidence for confirmation, rejection, replacement, manual editing, authored precedence, conflict resolution, or threshold choice. Those relationships appear in separately tagged `synthetic_control` fixtures. Synthetic controls must not be interpreted as real-IFC conclusions.

## Verification package and scope

`run_contract_design.py` deterministically writes the matrix, fixtures, truth table, provenance, and Mermaid diagram. `verify_contract_design.py` checks:

- JSON parsing and required top-level shape;
- separation of lifecycle and evidence fields;
- absence of an independent serialized `provisional_diagnostic_only` state;
- confirmation with evidence remaining `diagnostic_only`;
- rejection and replacement evidence/history retention;
- explicit no-selection versus absent relation;
- unresolved conflict, deferred resolution, and downstream `not_available`;
- required ordered event fields and monotonic `event_sequence`;
- real-IFC/synthetic separation;
- deterministic generator rerun;
- Mermaid labels, layer nodes, relation edges, line bounds, and readability markers;
- manifest byte counts;
- bounded whitespace;
- Git scope and absence of production-owned changes.

The manifest records byte counts only. No digest check is claimed. The verifier intentionally does not rerun the full IFC adapter or the full pytest suite.

## Remaining owner decisions and validation assumptions

1. Freeze or rename production concepts and serialization fields.
2. Decide whether a qualified authored domain may be consumed while an automatic disagreement remains visible as conflict.
3. Define conflict-resolution authority and the explicit override/resolution event.
4. Define active-count behavior when rejected and replaced histories coexist.
5. Define formal `AnalysisDomain` promotion policy.
6. Decide how `ambiguous` is derived from plausibility evidence without selecting thresholds in this package.
7. Separately decide free-space, connectivity, route, walkability, geometry backend, resolution, threshold, Bayesian/ML, selector, and public-API behavior.

These assumptions require later validation against owner decisions and future evidence. They are not production behavior.

## Method provenance

The package applied the repository skills `experimental-design`, `scientific-critical-thinking`, `scientific-visualization`, `verification-before-completion`, and `stop-that-shit`. `writing-plans` was read for task decomposition; no separate implementation plan was created because this is a bounded repair package rather than production implementation. The applied guidance informed separation of observed evidence from interpretation, bounded fixture design, diagram readability review, and evidence-before-completion verification. The procedural-skills reference named by the repository skill material is Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, arXiv:2609.00065, doi:10.48550/arXiv.2609.00065.

STOP FOR LIFECYCLE STATUS-CONTRACT REPAIR REVIEW
