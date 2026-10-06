# D6 AnalysisDomain/UI handoff bounded design

- Date: 2026-10-06
- Status: bounded design evidence only; implementation and owner approval deferred
- Scope: candidate-to-UI handoff contract, lifecycle/event semantics, visual states, and downstream refusal gates
- Stop marker: **STOP FOR ANALYSISDOMAIN UI HANDOFF DESIGN REVIEW**

## Boundary and evidence posture

This record defines a reviewable design contract for handing AnalysisDomain
candidates to a UI. It is not a production API, selector, adapter, geometry
backend, threshold, or implementation plan. The probe uses fixed synthetic
fixtures and standard-library JSON/SVG generation. No production adapter,
NeutralSceneV2, IFC geometry extraction, Blender, route algorithm, Bayesian/ML
model, or formal test suite was run.

The real IFC boundary remains `not_verified`: a future read-only preview may
carry source identity, input mapping, and provenance only. Native inventory or
diagnostic bounds must not be promoted to a qualified domain, free-space,
connectivity, membership, route, or walkability result.

The bounded design follows the read `experimental-design`,
`scientific-critical-thinking`, `scientific-visualization`,
`superpowers:writing-plans`, and `superpowers:verification-before-completion`
skills. The fixture is a fixed repeated-measures comparison: each case has
declared inputs, deterministic event order, explicit truth, and no random
winner. Critical-thinking rules separate observed fixture facts, derived
state, and unsupported production claims. The SVG uses redundant labels and
color/outline cues; it is a static contract figure, not a UI implementation.

## Design judgments

1. A single connected closed shell may emit one automatic singleton candidate.
   It is retained as `provisional` and `unassigned` by default. `singleton`
   describes collection cardinality only; it does not mean selected.
2. Multiple closed shells remain `ambiguous`; the handoff carries every
   candidate and does not elect a winner. `unassigned` preserves candidates.
3. A qualified authored/user domain has precedence for domain use. Automatic
   candidates remain retained provenance and comparison evidence.
4. Confirmation, rejection, assignment, replacement, and hand-drawn closed
   boundaries are explicit events. Every event carries a stable ID, actor,
   timestamp/order key, reason, and provenance. Duplicate semantic events may
   be retained idempotently; incompatible same-key events remain a conflict.
5. Replacement keeps old and new versions plus a lineage relation. The new
   version starts provisional/unconfirmed and does not inherit confirmation.
   Both sides of an unresolved conflict retain provenance; promotion is
   blocked until the relation is resolved by a later explicit design decision.
6. Hover/highlight changes display focus only. It never changes lifecycle,
   assignment, confirmation, selection, or downstream status. Only a
   qualified candidate with explicit confirmation or assignment can render as
   an active green domain. Automatic singleton, ambiguous, and unassigned
   candidates use neutral/amber styling. Conflicts are explicit and disable
   promotion. Rejected/replaced history remains inspectable.
7. Evidence state is separate from lifecycle action. The fixture distinguishes
   `missing`, `partial`, `invalid`, `unsupported`, `not_available`, and
   `diagnostic_only` from `provisional`, `confirmed`, `rejected`, and
   `replaced` lifecycle values. An evidence state cannot masquerade as a
   lifecycle action.
8. Without one qualified active domain, or with invalid geometry or unresolved
   conflict, `free_space`, `connectivity`, `membership`, and `route` are
   `not_available`. Diagnostic bounds only provide a display frame.
9. Walls may provide enclosure/boundary evidence and physical occupancy.
   Columns always provide physical occupancy; they provide boundary-support
   evidence only with an explicit contact relation. Arrangement alone cannot
   create a virtual wall. Openings/doors/windows record source facts only and
   do not infer open/closed/permeable state. Authored furniture-analysis nodes
   retain membership; a candidate cannot rewrite them. Context records do not
   silently become domains.

## Candidate, lifecycle, and event matrix

| Concern | Handoff rule | Probe evidence |
|---|---|---|
| Automatic singleton | Retain one automatic candidate as provisional/unassigned; no selected ID | `automatic_singleton_provisional` |
| Multiple shells | Retain all candidates as ambiguous/unassigned; selected ID is null | `multi_closed_shell_ambiguous` |
| Authored precedence | Explicit authored candidate becomes active when qualified and assigned/confirmed; automatic candidate remains provenance | `authored_user_precedence`, `hand_drawn_closed_boundary` |
| Explicit confirmation | Sets confirmation/acceptance and records actor/time/reason/provenance | `event:confirm:*` |
| Explicit assignment | Sets assignment without silently deleting other candidates | `event:assign:*` |
| Rejection | Sets rejected lifecycle and keeps the candidate in history | `rejected_candidate` |
| Replacement | Old version becomes replaced history; new version has lineage and fresh provisional state | `replacement_lineage` |
| Same-key conflict | Retain all incompatible events and provenance; no lexical/event-ID winner; block promotion | `unresolved_conflict_blocks_promotion` |
| Authored/automatic conflict | Retain both candidate records and conflict provenance; block promotion while unresolved | `authored_auto_conflict` |
| Hand-drawn boundary | Explicit user-authored geometry is a lifecycle event, not an inferred winner | `hand_drawn_closed_boundary` |
| Hover | Focus outline/label only; before/after lifecycle and downstream projections are equal | `hover_only_highlight` |

The effective active-domain gate is:

```
active = qualified(evidence_state=available, geometry_state=valid)
         AND explicit confirmation OR explicit assignment
         AND lifecycle not rejected/replaced
         AND no unresolved conflict
```

If more than one active candidate remains at the same effective source
priority, the result is ambiguous and selected ID remains null. The probe does
not use a random, lexical, geometric, or event-time winner.

## Evidence-state and downstream matrix

| Evidence state | UI treatment | Domain promotion | Domain-dependent outputs |
|---|---|---|---|
| `available` + explicit action | active green when the gate passes | permitted by this design gate | `available` |
| `available` + automatic/unassigned | neutral/amber provisional | refused | `not_available` |
| `ambiguous` | amber, all candidates retained | refused | `not_available` |
| `missing` / `partial` | warning label and provenance | refused | `not_available` |
| `invalid` / `unsupported` | warning/error label and provenance | refused | `not_available` |
| `diagnostic_only` | grey diagnostic frame | refused | `not_available` |
| unresolved `conflict` | conflict texture/label; promotion disabled | refused | `not_available` |

`not_available` is a downstream refusal state, not a substitute candidate.
`diagnostic_only` bounds do not establish an AnalysisDomain.

## Scope and role separation

The role fixture records these invariants independently of domain lifecycle:

- wall: boundary/enclosure evidence and physical occupancy;
- column: physical occupancy always, boundary evidence false without a contact relation;
- opening host: source identity and host relation, permeability `not_inferred`;
- authored furniture-analysis node: physical occupancy with membership immutable by domain inference;
- context: display/source context only, domain upgrade false.

## Fixture/truth/probe package

The package is under `scripts/design/analysis_domain_ui/`:

- `fixtures.json` — fixed synthetic cases and event provenance;
- `truth.json` — expected selection, lifecycle-derived visual labels, refusal
  status, lineage, conflict, hover, and role assertions;
- `run_probe.py` — deterministic event replay and SVG renderer;
- `verify_probe.py` — strict JSON/XML checks, truth comparison, two-run byte
  comparison, and scoped Git audit;
- `artifacts/run_001/` — primary result, SVG, verification report, scope audit,
  and artifact manifest;
- `artifacts/run_002/` — independent deterministic reproduction used for byte
  comparison.

The figure is generated from `result.json`, so its candidate labels, active
green state, conflict state, replacement history, hover-only outline, and grey
`not_available` downstream controls are the same values checked by `truth.json`.

## Verification commands and scope

The bounded commands are:

```text
pixi run python -B -m py_compile scripts/design/analysis_domain_ui/run_probe.py scripts/design/analysis_domain_ui/verify_probe.py
pixi run python -B scripts/design/analysis_domain_ui/run_probe.py --fixtures scripts/design/analysis_domain_ui/fixtures.json --output scripts/design/analysis_domain_ui/artifacts/run_001
pixi run python -B scripts/design/analysis_domain_ui/run_probe.py --fixtures scripts/design/analysis_domain_ui/fixtures.json --output scripts/design/analysis_domain_ui/artifacts/run_002
pixi run python -B scripts/design/analysis_domain_ui/verify_probe.py --primary scripts/design/analysis_domain_ui/artifacts/run_001 --reproduction scripts/design/analysis_domain_ui/artifacts/run_002 --baseline-status C:/Users/tianf/AppData/Local/Temp/d6_ui_baseline_git.json --report scripts/design/analysis_domain_ui/artifacts/run_001/verification_report.json --scope-audit scripts/design/analysis_domain_ui/artifacts/run_001/scope_audit.json --manifest scripts/design/analysis_domain_ui/artifacts/run_001/artifact_manifest.json
```

The baseline was captured at the required starting point: HEAD
`0ebe158931b7a2255f606925099d9b29b5abd22f`, branch
`codex/d6-analysis-domain-layout-handoff`, and 44 pre-existing untracked
paths. No existing untracked path is an output target. The experiment does not
run `git clean`, `git add .`, reset, rebase, batch move/delete, full pytest,
full IFC geometry adapter, Blender, production selector, or production space
algorithm.

## Unresolved items and stop conditions

Owner review is still required for the production serialization shape,
selector policy, confirmation/undo semantics, conflict resolution workflow,
multi-floor and opening rules, boundary construction, geometry tolerances,
free-space backend, connectivity/path definitions, and real IFC adapter
handoff. These are intentionally not chosen by this package.

The work stops here. It does not approve implementation or convert the design
evidence into a production API.

STOP FOR ANALYSISDOMAIN UI HANDOFF DESIGN REVIEW
