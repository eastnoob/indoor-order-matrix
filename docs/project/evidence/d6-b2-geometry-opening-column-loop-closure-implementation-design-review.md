# D6 B2 Geometry, Opening, and Column Loop-Closure Implementation Design Review

- Review date: **2026-10-07**
- Evidence class: **bounded synthetic design evidence**
- Reviewed repair commit: **82d08fe**
- Independent evidence decision: **ACCEPT LIMITED DESIGN EVIDENCE**
- Real IFC: **not verified / not run for this review**
- Blender: **not run for this review**
- Production implementation: **not approved**
- Final recommendation: **READY FOR OWNER DESIGN APPROVAL**

## Review scope

This record converts the accepted B2 evidence into a bounded implementation design. It identifies existing production touch points, the proposed handoff order, fields that must remain separate, and refusal/provenance behavior.

It does not implement geometry, change features/, adapters/, NeutralSceneV2, public APIs, tests, dependencies, IFC files, Blender files, or production configuration. It does not choose a tolerance, selector, resolution, route width, free-space backend, space role, Bayesian/ML model, real-IFC policy, UI behavior, or merge policy.

The synthetic B2 evidence is used as a contract oracle only. It is not real IFC or Blender validation.

## Accepted evidence basis

The original nine B2 fixtures and the repair-v2 uncertainty fixtures establish these bounded invariants:

- Physical occupancy is retained for every represented wall and column.
- A column can be listed in candidate_segment_ids without receiving boundary support.
- conditional_support_in_this_fixture is the support result for the diagnostic fixture; it is not a production tolerance or public status.
- Exact endpoint contact and a nonzero fixture gap remain distinguishable in the current exact-endpoint diagnostic helper. The gap value is not a production tolerance.
- Conflicting column contact keeps both source observations and refuses conditional boundary support.
- A conflicting opening host/geometry record keeps all host and geometry provenance and refuses subtraction.
- Candidate polygon validity and source-component connectivity are independent observations.
- Domain promotion is refused when the required evidence is incomplete, conflicting, ambiguous, or unsupported.
- Downstream free-space and route claims remain unevaluated after refusal.
- The exact-endpoint helper is diagnostic evidence only; it does not resolve intersections, near-coincidence, physical contact, or production tolerance.

The repair-v2 manifest and independent review confirm deterministic reruns, preservation of the original nine fixtures, 11 total cases, and an exact seven-path repair scope in commit 82d08fe. The wording issue in the repair-v2 report (seven artifacts versus six non-self manifest entries) is documentation debt and does not change the design boundary.

## Proposed data flow

flowchart TD
    A[IFC / SVG / Blender source] --> B[Existing adapter]
    B --> C[Source facts and geometry references]
    C --> D[NeutralSceneV2]
    D --> E[Reference and context validation]
    E --> F[B2 boundary/opening diagnostic projection]
    F --> G{Promotion gate}
    G -->|qualified and authorized| H[AnalysisDomain handoff]
    G -->|missing, invalid, partial, conflict, unsupported, ambiguous| I[Refusal with provenance]
    H --> J[Downstream space field gate]
    I --> J
    J -->|later approved backend only| K[Free-space/topology consumer]
    J -->|current gate| L[not_available or not_evaluated diagnostic]
    D --> M[Read-only UI/Blender projection]
    F --> M
    I --> M

The adapter supplies source facts and references. It must not infer a room, silently close an opening, or write a derived boundary projection. The diagnostic projection consumes immutable Neutral Scene facts and emits an auditable candidate record. The promotion gate is the only boundary between a candidate and a formal AnalysisDomain. No automatic candidate selector is introduced.

## Production touch-point inventory

These are existing files and functions that a later implementation design may touch. This review does not modify them.

| Existing path | Existing responsibility | B2 handoff constraint |
|---|---|---|
| features/scene_contract.py | Defines SourceObject, SourceOpening, AnalysisDomain, NeutralSceneV2, and UncertaintyRecord. | Reuse immutable records, geometry_refs, provenance, and uncertainties. Do not add a public status enum or overload SourceOpening with derived subtraction state without a later contract decision. |
| adapters/ifc_bonsai.py: _native_opening_records | Reads IFC4 IfcOpeningElement void relations and opening geometry references. | Preserve missing host/geometry facts and uncertainty records. A SourceOpening is source evidence; it is not proof that subtraction is qualified. |
| adapters/ifc_bonsai.py: _native_analysis_domain, _scene_from_native_ifc, load_ifc_neutral_scene | Builds explicit IFC source objects, meshes, openings, and an explicitly requested spatial domain. | Keep explicit-domain selection separate from inferred candidates. Missing explicit domain remains unavailable; do not substitute scene bounds or furniture bounds. |
| adapters/svg_scene.py: _source_openings, _analysis_domain, _validate_adapter_references | Reads authored SVG opening/domain roles and checks references. | Preserve empty/unresolved host and missing geometry evidence for diagnostics. Reference validation must not silently convert unresolved openings into valid boundaries. |
| adapters/blender_geometry.py: _validate_scene_references, load_blender_neutral_scene | Validates and combines Blender/IFC Neutral Scene records. | Keep Blender viewport facts as source/diagnostic input. Do not let viewport selection or display geometry promote a domain. |
| features/neutral_scene_views.py: analysis_scene_view | Projects Neutral Scene facts to the legacy consumer view, including boundaries and domain references. | Keep boundary evidence and formal domain references separate. Legacy view fields must not imply that a candidate was promoted. |
| features/group_self_description.py: _space_observations | Exposes current domain/channel observations while formal space measurements remain deferred. | Propagate domain availability/refusal and preserve free_space, connectivity, and bottleneck deferral. Do not compute topology in this B2 gate. |
| features/boundary_evidence.py | Existing source/geometry evidence helpers. | May be reused for factual geometry observations after a separate review; the current exact-endpoint helper is not automatically promoted as production policy. |
| features/analysis_substitute_discovery.py | Typed function-substitute resolution for other analysis consumers. | No role in deciding wall/column/opening boundary support; do not use furniture substitute bindings as domain evidence. |

## Source facts and semantic roles

| Fact | Required source representation | Allowed interpretation at this gate |
|---|---|---|
| Wall geometry | SourceObject identity, geometry_refs, source class/role, transform, provenance, uncertainties | Physical occupancy and candidate boundary evidence. Wall geometry does not by itself authorize domain promotion. |
| Column geometry | SourceObject identity, geometry_refs, source class/role, transform, provenance, uncertainties | Always physical occupancy. Conditional boundary-support evidence is separate and requires sufficiently evidenced contact and loop closure. A column is never converted into a virtual wall. |
| Boundary opening | SourceOpening.host_refs, geometry_refs, opening_kind, provenance, uncertainties | A source relation candidate. Subtraction is allowed only after qualification; an opening record alone is not a passage or walkability claim. |
| Door | Source object or opening relation plus provenance | Default-closed is a scenario assumption only. It must not be recorded as observed opening state, route access, or free-space truth. |
| Analysis domain | Explicit AnalysisDomain with qualified geometry references and selection provenance | A formal input only when explicitly authored/selected and validated. An inferred candidate remains diagnostic until an owner-approved promotion policy exists. |

## Column rules

The future diagnostic projection should carry two independent columns of information:

1. physical_occupancy: the column geometry/source record remains included regardless of boundary-support uncertainty.
2. boundary_support_evidence: candidate segment IDs, contact observations, resolution, and a conditional support result.

candidate_segment_ids means segments considered by this diagnostic candidate. It does not mean segments accepted as a domain boundary. In particular, B2-U01 may retain column-uncertain-face in candidate_segment_ids while conditional_support_in_this_fixture=false.

Conditional support may be true in a bounded diagnostic record only when contact is sufficiently evidenced and the relevant boundary loop is closed under the diagnostic observation. Exact endpoint equality is the current evidence helper, not a production tolerance. Near-contact, conflicting contact observations, or incomplete source components must withhold support and carry the reason/provenance.

The implementation design must never subtract or erase the column from occupancy merely because it contributes a candidate face.

## Opening qualification and propagation

Qualification is a gate over independent facts:

| Opening evidence | Diagnostic consequence | Subtraction |
|---|---|---|
| Host relation and usable geometry both present and consistent | Candidate may be recorded as reviewable | Still deferred until the owner approves the production opening policy |
| Missing host relation | not_available/missing diagnostic with source provenance | Refused |
| Missing geometry or malformed geometry | invalid or not_available, depending on the observed fact | Refused |
| Some references available but qualification incomplete | partial with retained source IDs | Refused |
| Host/geometry observations conflict | conflict with all variants retained | Refused |
| Representation unsupported | unsupported with representation provenance | Refused |
| Review-only evidence | diagnostic_only | Refused |

These labels are local diagnostic vocabulary. They must not become a unified public status enum in this gate. The existing SourceOpening record can carry source refs and UncertaintyRecords; a later derived projection may carry qualification/refusal reasons without mutating source facts.

A door shown as closed by scenario convention remains a closed-assumption fact. It is not a qualified boundary opening and does not authorize subtraction or route computation.

## Candidate polygon and source connectivity

The implementation design must preserve these as separate records:

candidate_polygon_validity:
  status: valid | invalid | not_available (local diagnostic values)
  area / geometry references when available
  reason
  provenance

source_components:
  source_segment_ids
  component_count
  connectivity status
  degree/topology evidence
  method and provenance

A valid candidate polygon can be produced from disconnected source components. A connected source loop can still yield an invalid polygon such as a self-intersecting bow-tie. Neither observation implies domain promotion.

candidate_segment_ids belongs to candidate provenance. source_components.source_segment_ids belongs to source topology. They may overlap, but they answer different questions and must not be merged into one Boolean.

## Domain-promotion gate

A future implementation may expose a single promotion decision, but its prerequisites must be explicit:

1. Analysis context is qualified: analysis plane, units, level/work plane, transforms, and relevant uncertainty are available.
2. Candidate polygon validity is acceptable for the later approved geometry policy.
3. Source component/connectivity evidence is independently recorded.
4. All boundary openings required by the candidate have qualified host and geometry evidence.
5. No unresolved contact/opening conflict affects the candidate boundary.
6. Candidate provenance identifies all source objects, segments, openings, and geometry records.
7. Candidate selection is authorized. Until the deferred selector policy is approved, multiple candidates remain retained and singular promotion remains refused/ambiguous.
8. The owner-approved promotion policy explicitly permits the candidate source kind.

If any prerequisite fails, preserve the candidate and emit a refusal record. Do not construct an AnalysisDomain from the candidate. Do not use scene bounds, furniture extents, a singleton candidate, replay order, lexical order, score, Bayesian posterior, or UI order as a hidden selector.

The existing explicit AnalysisDomain path remains valid for an authored domain with referenced geometry; this B2 design does not replace it with automatic inference.

## Downstream state boundary

The B2 design only defines upstream refusal propagation:

- no qualified explicit domain: preserve analysis_domain=None and report domain availability as not_available;
- candidate promotion refused because of conflict, incomplete evidence, or ambiguity: preserve the candidate and report domain_promotion=refused; downstream formal free-space/route claims remain not_evaluated;
- candidate geometry exists but no approved space backend is selected: keep free-space, connectivity, and bottleneck channels unavailable/deferred;
- unsupported or invalid source evidence: retain the reason and provenance; never coerce it to empty geometry.

not_available, not_evaluated, invalid, partial, conflict, unsupported, and diagnostic_only must remain distinguishable where the existing local projection supports them. Their final public contract is deferred.

## Minimal provenance shape

Until public serialization is approved, a derived B2 diagnostic record should keep a JSON-compatible, append-only shape:

{
  candidate_id: "diagnostic-candidate-id",
  source_segment_ids: ["wall-segment-a", "column-face-b"],
  physical_occupancy_refs: ["ifc-object:column-1"],
  boundary_support: {
    candidate_segment_ids: ["column-face-b"],
    conditional_support: false,
    contact_evidence: {
      resolution: "unresolved",
      source_ids: ["geometry-observation-A", "geometry-observation-B"]
    }
  },
  opening_evidence: [
    {
      opening_id: "ifc-opening:...",
      host_refs: ["ifc-object:wall-1"],
      geometry_refs: ["mesh:opening-1"],
      qualification_observation: "conflict",
      subtraction_performed: false
    }
  ],
  candidate_polygon_validity: {
    status: "valid",
    reason: "..."
  },
  source_components: {
    source_segment_ids: ["wall-segment-a"],
    component_count: 2,
    status: "partial",
    method: "diagnostic-only"
  },
  promotion: {
    status: "refused",
    reason: "unresolved_boundary_contact"
  },
  downstream: {
    free_space: "not_evaluated",
    route: "not_evaluated"
  },
  provenance: {
    evidence_class: "bounded_synthetic_design_evidence",
    source_ids: ["..."],
    geometry_refs: ["..."],
    method: "diagnostic_projection"
  }
}

This is a design shape, not a frozen public API or status enum. Source facts remain in NeutralSceneV2; derived diagnostic records must retain lineage and must not overwrite source records.

## Recommended call order

1. Adapter extracts source identities, transforms, geometry references, relation facts, and uncertainty records.
2. Existing reference validation rejects dangling references.
3. Neutral Scene context validation checks units, plane, level/work-plane scope, and source capabilities.
4. A bounded diagnostic projection gathers wall/column/opening facts and creates candidate evidence.
5. Candidate polygon validity and source-component connectivity are evaluated independently.
6. Opening qualification and contact uncertainty are propagated without subtraction or support promotion.
7. Promotion gate either retains a refused/ambiguous candidate or hands an explicitly authorized domain forward.
8. Downstream space consumers receive only a qualified domain; otherwise they receive an unavailable/unevaluated diagnostic projection.
9. UI/Blender reads the source and diagnostic projections; any later edit must append an authorized event and must not mutate a derived field silently.

## Legacy compatibility and error boundaries

- Preserve analysis_scene_view() and legacy mappings as compatibility projections. Additive diagnostic fields must not make legacy boundaries appear authoritative.
- Preserve NeutralSceneV2 immutability and current from_dict validation.
- Reuse existing SourceOpening references and UncertaintyRecords. Do not silently discard empty host references or missing geometry.
- Keep the current typed trend-substitute path unrelated to B2 boundary support.
- Raise or return a typed refusal at adapter/reference boundaries for dangling IDs, duplicate IDs, invalid geometry references, and unresolved required context. Do not silently repair by inventing geometry.
- Keep local diagnostic labels local until a separate public status-contract review.
- Observability must include candidate ID, source IDs, geometry refs, opening relation IDs, uncertainty codes, promotion reason, and downstream refusal reason.

## Focused validation plan

These are proposed focused checks for a later implementation branch; they were not run in this design review.

- Reuse the existing B2 repair-v2 runner and fixtures as contract oracles.
- Add focused adapter-to-projection checks only after owner approval:
  - interior column remains occupancy;
  - exact contact can be recorded as conditional support only under explicit diagnostic evidence;
  - near contact and conflicting contact withhold support;
  - valid opening host/geometry is reviewable but not silently subtracted;
  - missing, invalid, partial, conflict, unsupported, and diagnostic-only opening evidence preserve provenance;
  - valid polygon/disconnected source and invalid polygon/connected source remain separate;
  - ambiguous or refused candidates never create a singular AnalysisDomain;
  - explicit authored domain continues to round-trip through NeutralSceneV2.
- Suggested bounded commands:
  - pixi run python outputs/design/d6_b2_geometry_opening_column_loop_closure/repair_v2/run_uncertainty_probe.py --output-dir <fresh-temp-dir>
  - pixi run python scripts/design/space_field/run_d6_b2_geometry_opening_column_loop_closure.py --output-dir <fresh-temp-dir>
  - targeted pytest files only after production implementation is authorized.
- Do not run full pytest, real IFC geometry, Blender, or unrelated history as part of this design gate.

## Explicit deferred decisions

The following remain DEFER and are outside this review:

- production geometry tolerance and near-contact policy;
- automatic candidate selector, precedence, score, Bayesian posterior, or ML model;
- public status enum and public serialization format;
- formal conflict/undo/replacement authority;
- multi-floor, units, transforms, and work-plane policy beyond prerequisite validation;
- free-space/topology backend, grid resolution, origin, clearance, bottleneck, route width, and walkability;
- space-role semantics and singleton acceptance;
- real IFC integration policy and UI authority/behavior;
- production API, production tests, and merge.

B5 remains narrow: only the separation of candidate polygon validity and source-component status is approved for representation in bounded designs.

## Unresolved risks and owner decisions required

1. Owner must approve the exact production touch-point sequence before code changes.
2. Owner must decide whether derived diagnostic records remain sidecar evidence or receive a public Neutral Scene field.
3. Owner must separately decide the promotion policy and multiple-candidate authority.
4. Owner must decide production tolerance and intersection/near-contact behavior.
5. Owner must decide whether opening qualification is source-adapter responsibility or a downstream domain gate.
6. Owner must approve any public status vocabulary and serialization.
7. Owner must authorize a production implementation branch only after this design review and its independent review pass.

## Review commands and exit codes

Commands executed in this review:

- Get-Content -Raw AGENTS.md — exit 0
- Read B2 repair, repair-v2, independent review, fixtures, results, provenance, and manifest — exit 0
- git show --stat --oneline 9b50bb1 — exit 0
- git show --stat --oneline f7f71a3 — exit 0
- git show 9b50bb1:docs/project/evidence/d6-contract-closure-owner-decision.md — exit 0
- rg production touch-point and call-graph scans — exit 0
- git status --short --branch — exit 0

No production code, API, test, dependency, IFC, Blender, or configuration was modified. No full pytest, real IFC geometry run, Blender run, commit, or merge was performed by this review.

## Git scope

Current HEAD is codex/d6-analysis-domain-layout-handoff at the time of review. The worktree contains pre-existing untracked evidence and log files from other D6 sessions. This review adds only:
docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-review.md

The B2 repair-v2 commit itself was verified by the independent review as an exact seven-path scope. This design review has no production diff.

STOP FOR D6 B2 IMPLEMENTATION DESIGN REVIEW

