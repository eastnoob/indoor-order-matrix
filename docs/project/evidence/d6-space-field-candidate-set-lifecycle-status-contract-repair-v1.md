# D6 Candidate-Set Lifecycle Status-Contract Repair v1 Evidence Record

- Date: 2026-10-05
- Branch: `codex/d6-pairwise-channel-run2-repair-v2`
- Scope: design-only lifecycle status-contract repair
- Output package: `outputs/design/live_ifc_candidate_set_lifecycle_status_contract/repair_v1/`

## Repair result

The original package conflated `provisional_diagnostic_only` as both lifecycle and evidence state. Repair v1 separates the proposal into:

- candidate-set facts: `unassigned`, `ambiguous`, `singleton`, and explicit selection relation state;
- candidate-level lifecycle state: `provisional`, `user_confirmed`, `rejected`, `replaced`;
- candidate/set evidence state: `diagnostic_only`, `partial`, `invalid`, `unsupported`;
- lifecycle relations/events: `confirm`, `reject`, `replace`, `assign_authored_domain`, `record_conflict`, and `manual_boundary_edit`;
- downstream availability: derived `available`, `partial`, or `not_available` result;
- derived display label: `provisional_diagnostic_only`, computed only from provisional lifecycle plus diagnostic-only evidence.

Confirmation can therefore produce `user_confirmed` while evidence remains `diagnostic_only`. Rejection retains evidence. Replacement creates a new version and retains prior-version references. Conflict retains automatic and authored/user records, remains unresolved, and blocks silent downstream availability under the recommended strict interpretation.

## Evidence boundary

The real-IFC context is reused from the existing serialized case: eight retained automatic candidates, no authored domain, explicit no-selection, and no production promotion. Synthetic controls cover confirmation, rejection, replacement, authored precedence, conflict, evidence limitations, missing-domain propagation, and selection-relation distinction. Synthetic controls are explicitly tagged and are not real-IFC conclusions.

## Verification scope

The repair runner and verifier perform bounded deterministic checks for JSON shape, separated layers, transition invariants, event ordering, null and `not_available` propagation, real/synthetic separation, Mermaid readability, manifest byte counts, bounded whitespace, and Git scope. The verifier does not rerun the full IFC adapter or the full pytest suite. The manifest records byte counts only; no digest check is claimed.

## Branch and staging note

No new branch was created. The existing branch contains pre-existing D6 untracked evidence. The repair package is under ignored `outputs/design`; this record is the named auditable evidence path. Stage this file explicitly when the owner wants the repair record tracked; do not use `git add .`. A later implementation-design branch should be created only after this checkpoint and a separate owner approval.

## Scope result

No production code, adapter, NeutralSceneV2, public API, test, dependency, source IFC, or user Blender file was modified. No candidate was promoted to `AnalysisDomain`, no selector was implemented, and no thresholds, backends, route widths, Bayesian/ML model, or production status enum were chosen.

STOP FOR LIFECYCLE STATUS-CONTRACT REPAIR REVIEW
