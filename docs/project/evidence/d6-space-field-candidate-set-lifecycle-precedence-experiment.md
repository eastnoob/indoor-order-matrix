# D6 candidate-set lifecycle and authored-domain precedence design experiment

- Date: 2026-10-04
- Status: bounded design-only experiment complete; owner review required
- Scope: candidate-set lifecycle relationships and authored-domain precedence
- Production behavior: not implemented
- Stop marker: `STOP FOR CANDIDATE-SET LIFECYCLE AND PRECEDENCE DESIGN REVIEW`

## Purpose and boundary

This experiment compares candidate-set lifecycle and precedence representations
without selecting a production winner, promoting an `AnalysisDomain`, changing a
public API, or implementing a selector. The real-IFC case reuses the retained
serialized evidence from the approved eight-candidate comparison. User actions,
authored-domain precedence, rejection, replacement, conflict, and evidence-status
propagation are separate synthetic controls. The controls are never merged into
the real-IFC conclusion.

The experiment keeps the following evidence fields together for every record:

- candidate-set ID and stable candidate ID;
- source IDs and source roles;
- support references separated from occupancy-context references;
- candidate geometry, source-union component count, and candidate component count;
- explicit selection state and user-action provenance;
- prior candidate/version references;
- analysis plane and units;
- uncertainty/reason codes;
- record class (`real_ifc`, `synthetic_control`, or `owner_scenario`).

It does not compute free-space, connectivity, routes, walkability, space roles,
Bayesian or ML inference, production thresholds, or a production resolution.

## Blockers

- The source IFC still has no qualified authored `AnalysisDomain`. The real case
  therefore remains `not_available` for formal domain promotion and keeps all
  eight automatic candidates unassigned.
- Formal lifecycle/status aggregation remains undecided. The proposed concepts
  are comparison vocabulary only; no production enum or selector was frozen.
- Authored-domain precedence is not observable in the real IFC because no
  qualified authored domain exists there. Its behavior is represented only by a
  separate synthetic control.
- The source file has no verified opening/void/fill evidence for treating doors
  as openings. Door semantics remain outside this experiment.

## Important findings

### Real-IFC evidence

The real-IFC case retains all eight approved candidate IDs in one candidate set:
three wall-only candidates, three wall-plus-column candidates, and two
column-assisted candidates. The candidate-set record preserves explicit
`selection = none`; no candidate becomes a room, a formal domain, or a winner.
The candidate records retain the existing diagnostic world-XY plane, metre units,
source roles, geometry, support references, occupancy context, and component
counts. All columns remain physical occupancy even when a candidate records exact
boundary support.

The lifecycle comparison represents the same real case twice: once with the
observed automatic diagnostic state and once with a proposed `ambiguous`
candidate-set description. The second view does not alter the evidence or select
one candidate; it makes the distinction between “several plausible candidates”
and “a candidate was selected” explicit.

### Candidate-set state versus per-candidate state

The comparison keeps cardinality and assignment at the set level while keeping
confirmation, rejection, replacement, validity, and source uncertainty at the
candidate level. A singleton candidate remains provisional until an explicit
owner action is recorded. A set can remain ambiguous while individual candidates
carry different evidence states. This separation is useful, but the exact
serialization and aggregation rules remain an owner decision.

### Authored-domain precedence

The synthetic authored-precedence control contains two automatic provisional
candidates and one explicit authored domain. The authored domain is shown as the
precedence-bearing record while both automatic candidates remain retained
provenance. A separate conflict control keeps automatic and authored records
without silently resolving the disagreement. This adequately represents the
approved design principle without pretending that a production selector exists.

### Rejection and replacement

The rejection control records an explicit user action against a stable candidate
ID and preserves its geometry, source references, and reason codes. The replacement
control keeps version 1 as `replaced`, records version 2 as the explicit
replacement, and carries `prior_candidate_version_refs` from version 2 back to
version 1. Prior evidence is therefore auditable rather than deleted or silently
rewritten.

### Evidence-status propagation

Separate synthetic records cover `not_available`, `partial`, `invalid`,
`unsupported`, `conflict`, and `diagnostic_only`. Missing qualified domain is
represented as `not_available`; incomplete source evidence remains `partial`;
invalid geometry remains invalid; unsupported representations retain their reason
codes; conflict preserves both sides; and display/source facts remain
`diagnostic_only`. None of these records is promoted to a production result.

### Source topology versus candidate topology

The real records retain both `source_union_component_count` and
`candidate_component_count`. The synthetic topology control repeats this
distinction with a multi-component source union and a single candidate polygon.
The experiment does not merge disconnected source components and does not treat
candidate polygon validity as proof that the source topology is unambiguous.

## Minor findings and limitations

- The real case is based on existing serialized IFC-derived evidence; this run
  does not reopen the 408 MB IFC or claim a live adapter result.
- The diagnostic world-XY plane and metre serialization are evidence context,
  not a frozen production coordinate contract.
- Synthetic geometries demonstrate record relationships only. They are not
  geometry-quality evidence for the real IFC.
- The PNG is corroborated by Blender object/text readback; the SVG is the
  machine-readable geometry and label inspection surface. The disposable scene
  makes no live Blender/MCP correspondence claim.

## Observed evidence versus proposed lifecycle semantics

| Area | Observed evidence | Proposed relationship, still deferred |
|---|---|---|
| Automatic real-IFC candidates | Eight retained candidates, all `provisional_diagnostic_only`, explicit no-selection | A candidate set with several plausible candidates may be described as `ambiguous` without ranking |
| Candidate cardinality | The real set has eight records; a synthetic control has one record | `singleton` is a cardinality fact and does not imply confirmation |
| Assignment | Real IFC has no authored domain and no user action | `unassigned` describes the set while retaining every candidate |
| User confirmation | Only synthetic control action, tied to a stable ID | `user_confirmed` is explicit provenance, never geometry inference |
| Rejection | Only synthetic control action | `rejected` is candidate-level and retains prior evidence |
| Replacement | Synthetic v1/v2 control with a prior-version reference | `replaced` is a lifecycle relation, not deletion |
| Missing/invalid/unsupported/partial | Synthetic diagnostic records preserve identity and reasons | These concepts propagate evidence limitations; they do not become a winner |
| Authored precedence | Not observable in the real IFC | Qualified authored/explicit domain can take precedence while automatic candidates remain provenance |
| Conflict | Synthetic automatic-versus-authored disagreement | `conflict` remains unresolved until an owner rule exists |
| Diagnostic-only evidence | Real source inventory and synthetic diagnostic controls | `diagnostic_only` remains display/audit evidence and cannot promote a domain |

The table is a design comparison, not a frozen enum specification. The
`status_relationship_proposal.json` artifact records the open owner decisions
about names, overlap, precedence, and serialization.

## Real IFC versus synthetic control separation

`real_ifc_case.json` contains only the eight retained real-IFC records and the
source inventory context. `synthetic_control_cases.json` contains the action and
precedence controls with `record_class = synthetic_control`. The lifecycle and
precedence comparison files identify their scenario class explicitly and state
that synthetic controls cannot be used as real-IFC conclusions. The Blender
scene and SVG repeat the distinction in their labels:

- `REAL IFC CANDIDATE EVIDENCE`
- `SYNTHETIC CONTROL SCENARIO`
- `REAL IFC CONCLUSIONS EXCLUDE SYNTHETIC CONTROLS`

## Verification

The bounded verifier reports `status = pass` in
`outputs/design/live_ifc_candidate_set_lifecycle_experiment/verification_report.json`.
It performed the required checks:

- parsed every JSON artifact, including the final manifest and verification
  report;
- recomputed manifest byte counts and SHA-256 values;
- ran a deterministic JSON repeat in a temporary directory; all six core JSON
  digests matched;
- parsed the SVG, found 35 geometry paths, and found every required legend label;
- inspected the rendered PNG as 2200 × 1400 RGBA content with non-empty pixels;
- read back the disposable `.blend` with the approved portable Blender and
  verified 8 real candidate IDs, the semantic labels, and the scene flags;
- verified real-IFC and synthetic-control tags remain separate;
- verified the rejection/replacement provenance references;
- confirmed no production-scope file changed and the pre-existing dirty/untracked
  paths were preserved;
- did not run the full test suite or the full live IFC adapter.

The visual artifacts are disposable and were produced with only
`D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe`; no user Blender
file was opened or saved.

The experiment workflow applied the repository's bounded experimental-design,
scientific-critical-thinking, scientific-visualization, verification-before-
completion, and Stop That Shit guidance. The procedural-skills reference used
in the report is: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M.
(2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research
Agents*. arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065.

## Gate decision

Authored-domain precedence is adequately represented as a design principle:
the control shows explicit authored precedence and retains automatic candidates
as provenance, while the real IFC correctly reports that precedence is not
observable because no authored domain exists. Rejection and replacement preserve
prior geometry and provenance. The formal status/lifecycle contract remains
correctly deferred, including conflict handling, candidate-set versus
per-candidate serialization, cross-level precedence, and replacement semantics.

A later implementation-design gate is justified only after owner review of this
comparison and an explicit decision on those open relationships. This experiment
does not authorize production implementation, a selector, formal domain
promotion, free-space, connectivity, route, walkability, or a finalized status
enum.

STOP FOR CANDIDATE-SET LIFECYCLE AND PRECEDENCE DESIGN REVIEW
