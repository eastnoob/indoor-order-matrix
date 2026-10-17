# Locked Input Seam Review

Date: 2026-10-10

## Scope

`specs/002-free-space-field-inspection/` currently contains only the generated
placeholder `spec.md`; there is no existing delegated report with another
meaning. This review is read-only and covers the locked B3 package and the
existing whole-height preview path. No Blender, IFC, live evaluator, or full
test run was used.

## Verdict

**The frozen source set is sufficient for an offline whole-height 2D
inspection, but `preview_input.json` alone is not yet a complete reusable
`FreeSpaceField` input.** The smallest seam should consume the frozen package
artifacts and normalize them once into explicit domain components plus
pre-resolved whole-height occupancy records. It must not reuse the historical
`z=1.6 m` samples as occupancy.

## Real Locked Entry

Use the successful frozen package:

```text
outputs/design/b3_shared_occupancy_enrollment/
  run_20261009T142454Z_0d7308/
```

The minimal existing producer is
`scripts/design/space_field/build_b3_whole_height_preview.py:build_input`.
Its locked inputs are:

- `field_samples.json`: exact domain geometry with two holes, frame/units,
  package algorithm and source references. Its `variants` and
  `primary_plane_world_z_m=1.6` are historical section metadata only.
- `source_sections.json`: source ids, global ids, classes, status, geometry
  references, and proxy rows with `represented_source_ids`.
- `selection_audit.json`: exact `selected_source_ids`, three
  `proxy_target_ids`, seven represented owners, five `unknown_source_ids`, and
  the exact `boundary_scoped_ids` entry `live-step-6231`.
- `transport_audit.json`: frozen source-object and proxy mesh records,
  capture/proxy counts, world-metre transform policy, and package provenance.
- `artifact_manifest.json` plus each referenced SHA-256: the integrity lock.

`build_input` verifies those hashes, loads original capture meshes and the
three proxy meshes, and calls
`plan_projection(..., height_band=None)` at
`build_b3_whole_height_preview.py:112-124`. That is the correct whole-height
route. It does not use the saved eye-plane occupied geometry as mass.

## What the Locked Data Proves

The frozen package contains the required source coverage:

- 361 source records in `source_sections.json`;
- 343 selected whole-height candidates;
- 95 `IfcFurniture` records, rendered as 58 chairs and 37 tables;
- 245 additional `physical_context` projections, so occupancy is not a
  furniture-only bucket;
- three accepted proxy geometries representing seven owners exactly once;
- five unresolved owners retained as unknown supports;
- one exact boundary member, `live-step-6231`, excluded upstream.

The existing generated `preview_input.json` records:

- schema `b3-whole-height-plan-preview/v1`;
- query `frame=world_xy`, `units=m`, `height_band=null`;
- domain geometry and two holes;
- all 343 selected projections, not only furniture;
- `represented_source_ids`, selected ids, unknown supports, and the excluded
  boundary-door reference;
- complete occupancy and clearance as `null`.

The preview renderer draws the union of all selected physical occupancy, while
also outlining furniture and proxies. It therefore does not silently present
only furniture. The rings/markers are display geometry; they are not a claim
that the marker spacing is the field lattice.

## Required Normalized Input

For Spec002, the reusable offline seam should read the package above and
construct one immutable input mapping with these explicit keys:

```text
frame: "world_xy"
units: "m"
origin_offset_m: [0.0, 0.0]          # explicit, even when zero
query_scope: "whole_height_plan"
domain: exact polygon components including holes
physical_occupancy: one record per selected geometry
unresolved_source_ids: exact five ids
boundary_scoped_ids: ["live-step-6231"]  # audit only; already excluded
package_fingerprints: manifest + consumed mesh refs
```

Each occupancy record needs the selected id, whole-height plan components,
`represented_source_ids`, original/accepted representation status, and
provenance/reference to the frozen capture or proxy binding. A proxy record
must remain one geometry with seven-owner coverage split across the three
proxy records; do not duplicate it per owner.

The existing package has all of these facts across the files above, but the
current `preview_input.json` does not copy two of them explicitly:

1. `origin_offset_m` is present in historical field variants as
   `origin_offset_m=[0,0]`, but not as a top-level whole-height preview input
   field. Do not infer it from array coordinates.
2. Per-proxy binding/object provenance (`proxy_obj_ref`, binding declaration
   hash, approximation limit) remains in `source_sections.json`, the
   binding reference, and package manifest rather than on each normalized
   preview projection.

These are small input-normalization omissions, not missing source evidence.
The adapter should copy them into the locked mapping; it should not invent
new resolver or qualification logic.

## Traps the Offline Example Must Avoid

- **Section confusion:** `field_samples.json`, `source_sections.json.status`,
  and `run_b3_shared_occupancy_enrollment.py:QUERY` describe historical
  `world_xy` at `z=1.6 m`. They are identity/qualification evidence only for
  the whole-height rebuild. The whole-height consumer must use
  `plan_projection(..., height_band=None)` and label the query with
  `height_band=null`.
- **Domain fallback:** use `field_samples.json.domain_geometry` and preserve
  its two holes. Never use the preview bounds or source-file extent as the
  domain.
- **Role filtering:** use `selection_audit.selected_source_ids` and the
  resolved physical records. Do not rebuild occupancy from `IfcFurniture`,
  `objects`, or the furniture union.
- **Boundary inference:** consume `boundary_scoped_ids` as upstream exact
  membership. Do not reclassify doors by class, name, proximity, or geometry.
- **Unknown handling:** the five `unknown_source_ids` remain unknown support,
  never occupied mass and never established free space. The existing preview's
  convex-hull supports are diagnostic uncertainty geometry only.
- **Proxy semantics:** accepted proxies remain conditional/audited
  representations; their seven owner ids are coverage provenance, not seven
  geometries.
- **Frame/offset:** all domain, meshes, projections, and lattice coordinates
  must share `world_xy` metres and the same explicit offset. The current
  frozen run uses zero offset, but zero must be recorded rather than assumed.

## Can This Offline Example Be Done?

**Yes, with the normalized seam above.** The locked package has enough real
data to reconstruct the explicit domain, whole-height resolved occupancy,
furniture plus non-furniture mass, exact proxy ownership, unknown support,
boundary exclusion, and frame/unit provenance without opening Blender.

**Not from `preview_input.json` alone without a small normalization step.**
That file is a display manifest: it has union geometries and projection rows,
but it omits a top-level offset and direct per-proxy binding provenance. The
minimal reusable implementation should read the authenticated package files,
copy those fields into the FreeSpaceField input, and then render/serialize
only the field samples and audit metadata.

No production code, tests, Spec002 `spec.md`, or Git state was changed.

Not checked: live IFC/Blender execution, new Spec002 implementation, and
full-suite performance. 

## Design Supplement: Reusing the Frozen Enrollment Seam

`frozen_inputs()` is reusable for the whole-height path as an integrity
boundary. It verifies the binding declaration, package fingerprints, source
inventory, capture manifest, scope binding, proxy metadata, and exact
`boundary_scoped_ids`; those facts can be carried forward without rebuilding
the historical `z=1.6 m` section.

`transport_scene()` is not reusable unchanged. It calls `exact_plane_section`
for each proxy, creates an analysis plane fixed at `world_xy_z_1_6`, and
constructs `AnalysisDomain(geometry_refs=(), ...)`. That leaves
`analysis_scene_view` without explicit domain geometry for a whole-height
`FreeSpaceField` request. The smallest compliant route is a sibling or
runner-local whole-height transport that reuses the existing
`SourceObject`/mesh construction and shared occupancy bindings, omits section
records, explicitly carries the domain components, frame, units, and offset,
then calls the existing `analysis_scene_view(neutral)` path. Substitution and
role resolution must remain in the existing shared resolver; do not add a
direct-preview resolver.

There is one data-handoff blocker: the five
`selection_audit.unknown_source_ids` are not guaranteed to stay unknown through
the current transport. Their historical `frozen_section_status` is stored as a
fact, but `resolve_source_representation()` qualifies whole-height originals
from geometry refs and does not treat that fact alone as uncertainty. The
whole-height input must therefore preserve those exact five IDs through the
main-chain uncertainty/qualification semantics (or an upstream handoff that
the resolver explicitly recognizes). Convex-hull supports remain diagnostic
only and must never become occupancy or free-space geometry.

Boundary membership must continue to come exactly from
`boundary_scoped_ids`; no class/name inference is permitted. This supplement
does not change production code, tests, specs, or Git state.

## Qualified NeutralSceneV2 Handoff Assessment

The proposed runner-local handoff is compatible with the existing shared view
and is the minimum viable way to preserve frozen qualification without editing
`features/`. For each exact `selection_audit.unknown_source_ids` member,
construct a `SourceObject` with `geometry_refs=()` and an
`UncertaintyRecord(code="missing_geometry", ...)`. `SourceObject.__post_init__` accepts this
explicit missing-geometry form, and the existing
`resolve_source_representation()` then reaches `_geometry_rejection()` and
returns `reason="missing_geometry"` for the whole-height original fallback.
`_resolved_physical_occupancy()` consequently emits `status="unknown"` and
includes the owner in `physical_occupancy_unresolved_source_ids`. Retain the
authenticated captured mesh refs/arrays only under `factual_properties` or
`provenance` as audit-only data; do not place those refs in
`SourceObject.geometry_refs`. Also ensure no accepted physical-occupancy
binding can promote one of these five IDs through a proxy path.

The handoff should use these existing symbols/fields:

- `NeutralSceneV2.context.analysis_plane` with `AnalysisPlane` named for
  `world_xy` whole-height projection, plus `context.analysis_length_unit="m"`.
- `MeshGeometry3D` for authenticated body/proxy meshes that are eligible for
  occupancy, and `SourceObject.geometry_refs` only for those eligible mesh
  ids.
- `SourceObject.uncertainties` with source-bound `UncertaintyRecord` entries
  for the five unknown owners; audit-only capture refs belong in
  `factual_properties`/`provenance`.
- `AnalysisDomain.geometry_refs` containing the exact projected domain mesh
  component ids, with `AnalysisDomain.provenance["boundary_member_source_ids"]`
  carrying the exact upstream boundary membership.
- `AnalysisDomain.source_id` set to the unique matching `SourceObject.source_id`
  when domain-support exclusion is intended.

`analysis_scene_view()` derives `domain_points` only from
`scene.analysis_domain.geometry_refs`, then computes its own zero-based
`_analysis_view["origin_offset"]` via `_view_frame()`. A runner must therefore
pass that returned offset to `FreeSpaceField(origin_offset=...)`; a nominal
zero offset in the frozen package is a recorded input fact, not a control that
overrides this view translation. Exact support-slab scoping is representable
only when the slab/domain source has both a matching `source_id` and mesh
geometry: `_domain_shell_identity()` can then mark that source
`selected_analysis_domain_support`. Domain mesh refs alone still establish
the polygon, but do not identify a source object to exclude.

## Static Review Refinement: Inherited Guarantees

The proxy cardinality/owner condition is **not an independent defect in this
runner**. The consumed binding declaration is hash-pinned by
`B3.frozen_inputs()`/`verified_ref()`, and that helper checks target identity,
target/group agreement, and duplicate-free represented-source coverage before
this function receives `bindings`. The shared
`resolve_source_representation()` / `_exact_coverage()` path then rechecks
declared coverage during occupancy resolution. I found no concrete input that
passes those existing authenticated checks while duplicating or dropping a
proxy owner; the runner’s three-target/seven-owner facts are inherited from
that locked package rather than independently re-derived. No cardinality
blocker should be recorded here.

The semantic/support role rewrite is likewise not a qualification or geometry
bug in the current path. Lines 148-174 preserve the original status and
capture references, while `source_role="analysis_domain"` removes those
records from `_is_original_physical_source()` occupancy inventory. Thus the
current counts, occupancy status, and selected geometry remain unchanged; the
loss is limited to explicit downstream provenance distinguishing semantic
nonmass from support-slab scope. If that audit distinction is required, the
minimal follow-up is to copy the authenticated ID sets into domain or scene
provenance. It is a targeted audit-record improvement, not a blocker for this
transport.

## Artifact Half Acceptance Review

Reviewed prototype
`outputs/design/free_space_field_inspection/run_20261010T134650Z_8f438d`
without reading the older 1 GB prototype or rerunning projection. The current
inspection manifest is 21,740,805 bytes, the HTML is 13,063,614 bytes, and
`execution.json` reports `exit_0` with manifest SHA-256
`719a9377c47189304e3e5447c7f0a6a27852a948b1e222e8561e4ab6197bd8e5`.
This prototype is **not accepted** because `source_layer` has 347 records, all
with `representation_status="original"`; it has no accepted proxy records and
no unknown-source records. The owner-binding correction already identified by
the implementer is therefore a required prerequisite, not repeated here as a
new finding.

### Verified in the prototype

- The field has 3,969 cells (`81 x 49`), and the embedded HTML payload
  round-trips to the same 3,969 cells and 347 source records.
- The domain is one component with two holes. The source and field panels use
  the same `bounds` and `point()` scale in the runner; the HTML contains source
  paths and cell rectangles in the corresponding 20/520 panel offsets.
- Cell records retain query frame, whole-height query kind, algorithm/schema
  versions, support, explanation, and a shared provenance reference.
- The payload documents `False` as empty physical occupancy rather than
  walkability/clearance. In this prototype, however, no cell has a boolean
  `False` value; only `established=True`, `unknown=None`, and `outside=None`
  occur.

### Independent acceptance gaps

1. **Input-hash ledger is incomplete in the manifest.** Per-mesh capture
   hashes are embedded under shared provenance, but the top-level payload has
   no exact consumed `artifact_manifest`/binding/capture/scope/proxy input
   hash ledger. `execution.json` hashes only the generated manifest. This
   leaves SC-005 unable to prove the complete frozen-input set from the
   inspection artifact alone. Minimal fix: add a deterministic
   `input_hashes` object containing the consumed artifact-manifest entries and
   the binding, capture, scope, proxy metadata, and domain/selection refs.

2. **SC-002 and provenance recovery are not focused-tested.**
   `test/test_free_space_field_inspection.py` currently contains only the
   two-hole mesh test and the five-ID constant test. It does not compare
   serialized cells with `FreeSpaceField.evaluate`, recover a cell through
   `shared_provenance`, verify embedded HTML payload equality, or check source
   and field alignment. Minimal fix: add focused tests for those exact
   invariants after the owner-binding fix; do not rerun the expensive real
   projection for each test.

3. **Six-state coverage is not evidenced by this artifact.** The manifest
   samples contain only `established`, `unknown`, and `outside`; there are no
   `conditional`, `invalid`, or `not_available` samples and no explicit
   “unavailable in this run” report. The legend text is not sufficient evidence
   for SC-004. Minimal fix: record per-status availability in the manifest
   (or include representative cells where the current field can produce them)
   and retain distinct visual-state mapping.

The final artifact remains pending owner-binding correction, then the three
independent checks above plus focused tests and architecture/checklist
truthfulness review. No runner, test, docs, or Git files were changed in this
review.

### Architecture and Checklist Truthfulness

The architecture documents still label the Spec002 inspection layer
`PLANNED`, while the runner and focused-test files now exist. That wording is
truthful only if the feature remains explicitly in verification/incomplete
status; it must not be presented as an accepted implemented layer yet. The
living checklist likewise leaves input hashes, non-furniture occupancy,
boundary acceptance, SC-002, and frozen-hash verification unchecked, which
matches the current prototype and the gaps above. The `[X]` six-state visual
mapping item is a code-level mapping claim, not evidence that all six states
occur in this run. After final artifact acceptance, update architecture and
checklist status together; until then, retain the pending wording.

## Prototype Consolidation: `run_20261010T140338Z_935ec9`

The newer prototype is also **not accepted**. Its manifest is 20,523,860
bytes, its HTML is 12,369,483 bytes, and `execution.json` reports `exit_0`
with manifest SHA-256
`e03ae783e24e811024bf8e11b86da97ba0670a518d23a1201d69da22dd425b9b`.
It contains 3,969 cells with statuses `539 outside`, `2,141 unknown`, and
`1,289 established`, plus 340 `source_layer` records, all
`representation_status="original"`. There are no accepted proxy records.

The 340 count is diagnostic of a specific transport loss, not a harmless
count variation: the locked selection needs 340 retained originals plus three
accepted proxy records, while the seven proxy owners are absent. The field is
therefore missing the proxy occupancy that should replace those seven owners.
The five hardcoded `UNKNOWN_IDS` still appear in the cell provenance, but they
cannot account for the seven omitted proxy owners. Final acceptance remains
blocked until the owner binding fields are complete and the three proxy
records appear with their seven-owner coverage.

### Additional Output-Layer Gap

Even after the owner binding correction, the current `source_layer`
serialization (runner lines 379-386) selects only:
`id`, `represented_source_ids`, `representation_status`,
`geometry_components`, `representation_provenance`,
`representation_diagnostics`, and `_neutral_source_id`. It omits
`source_role`, `source_class`, furniture participation, and source-bound
uncertainty diagnostics. Consequently the artifact cannot independently
verify the requested source-class/role/furniture split, nor explain unknown
owners beyond the top-level five-ID list. Minimal fix: include those fields
from the normalized scene/source records (and preserve the five
`UncertaintyRecord` details) in the source layer or a linked audit table.

This review does not add a new cardinality gate: the binding declaration and
shared resolver already own coverage validation. The current blockers are the
observed missing proxy handoff in this artifact and the output-schema loss of
role/furniture/unknown evidence. No projection, renderer rerun, code, tests,
or Git state was changed.

## Pending Final-Artifact Review: `run_20261010T141847Z_c347ce`

The owner-provided final-correction path is not present in the workspace yet;
there is no directory or `execution.json` for
`run_20261010T141847Z_c347ce`. No acceptance claim is possible until that
artifact arrives.

Static review of the current runner shows the owner handoff has materially
improved: `_whole_height_scene()` now constructs typed
`OM_FunctionSubstitutes` bindings with `analysis_role`,
`representation_identifier`, and binding provenance, while `build_inspection()`
checks that the accepted proxy ids and represented owner coverage match the
authenticated bindings. The focused test also resolves all seven owners
through the shared resolver. These checks are evidence for the intended
343-record path, not evidence for the missing final artifact.

Remaining substantive checks for the final artifact:

- `test_domain_mesh_preserves_two_holes()` only asserts that one hole-center
  vertex is absent. It does not project the mesh and assert that a point or
  cell inside each hole is outside the projected domain while a nearby shell
  point is covered. A small synthetic projection/coverage assertion is still
  required.
- The runner’s payload still has no explicit top-level consumed-input hash
  ledger (`artifact_manifest`, binding, capture, scope, proxy metadata, and
  selection/domain refs). Per-mesh provenance hashes alone do not satisfy the
  whole-input audit requirement.
- `source_layer` still serializes only occupancy view records; it omits
  `source_role`, `source_class`, furniture participation, and source-bound
  uncertainty details. The final artifact must either include these fields or
  provide a linked audit table covering 95 `IfcFurniture`, physical-context
  sources, three proxies, and five unknown owners.
- `0.25 m` is recorded as `resolution_m`, but the payload/HTML limits do not
  explicitly label it demonstration-only. Add that wording before acceptance.
- The color map and legend name all six statuses, but availability is not
  recorded in the manifest. The final artifact must show which of
  `conditional`, `unknown`, `outside`, `invalid`, and `not_available` are
  present or explicitly unavailable; legend text alone is insufficient.
- SC-002 still needs an actual exact-recovery check: each serialized cell must
  reconstruct the pre-deduplicated `build_field_layer_manifest` record, and
  the embedded HTML JSON must byte-for-byte equal the final manifest payload
  after the intentional HTML-only wrapper is removed. Final `sizes` must match
  the written JSON/HTML bytes, not only pre-write estimates.

Architecture/checklist status should remain implemented-under-review, not
accepted, until these checks are evidenced by the final output. B3 remains
OPEN. No code, tests, runner execution, or Git state was changed in this
review.

## Intermediate Eligibility: `run_20261010T141847Z_c347ce`

The artifact is now present and provides useful intermediate evidence, but it
is not final acceptance evidence. The current bytes on disk are:

- `inspection_manifest.json`: 19,868,951 bytes
- `inspection.html`: 12,469,121 bytes
- `execution.json`: `exit_0`
- observed manifest SHA-256:
  `9e9edf52e28636b5237d1692fc77cebd31590dd50c4265e358766738173e14c7`

These differ from the handoff values (`78bc6f...`, 20,634,939 manifest bytes,
and the recorded 19,868,878 bytes), so the output must be treated as a
different or still-changing artifact until its final manifest is regenerated
and its execution hash is reconciled.

### Verified eligibility facts

- `source_layer` contains 343 records: 340 `original` records and three
  `accepted` proxy records.
- Proxy coverage is exact: `proxy:counter_1992252` represents one owner and
  `proxy:assembly_A` / `proxy:assembly_B` represent three each, for seven
  distinct owners exactly once.
- The field has 3,969 cells. Status counts are `1,544 conditional`,
  `1,886 unknown`, and `539 outside`; the accepted proxies produce the
  conditional status rather than being silently treated as original geometry.
- The five locked unknown IDs appear in the audit and in the global field
  provenance. Unknown cells explain
  `unresolved support prevents a known-empty result`; conditional cells explain
  accepted substitute geometry without claiming an exact envelope.
- The domain remains one component with two holes, and the whole-height query
  metadata is `frame=world_xy`, `height_band=null`, `resolution_m=0.25`.

### Remaining final-output blockers

1. The top-level manifest still has no consumed-input hash ledger. Its
   `audit` contains source counts and unknown/boundary ids, but not exact
   artifact-manifest, binding, capture, scope, proxy-metadata, and
   selection/domain fingerprints.
2. `source_layer` still exposes only occupancy-view fields. It has no
   `source_role`, `source_class`, furniture participation, or per-owner
   uncertainty diagnostics, so the requested 95-`IfcFurniture` and
   physical-context audit cannot be independently recovered from the artifact.
3. The recorded `sizes` are not the bytes currently written: the manifest
   records `json_bytes=19,868,937` and `html_bytes=12,469,107`, while the
   files are 14 bytes larger each. This must be fixed before relying on the
   byte-count contract.
4. The embedded HTML payload currently round-trips to the same 343 records and
   3,969 cells, but exact SC-002 recovery and final HTML/manifest byte
   reconciliation still need an explicit focused test. The existing
   two-hole test remains vertex-only and does not prove projected hole
   coverage.

This is a core-selection eligibility result, not final acceptance. No
projection, tests, runner, docs, or Git state were changed.

## Revised-Path Static Check

`outputs/design/free_space_field_inspection/run_20261010T141847Z_c347ce_revised`
does not contain a new projection output. Its `inspection_manifest.json` and
`inspection.html` are byte-identical in size/timestamp to the previously
reviewed `c347ce` files, `execution.json` still points at the original
directory, and the added `acceptance.json` merely restates 343/3/7 counts,
five unknown ids, the existing manifest hash, and a six-item legend. It is
therefore intermediate metadata, not a new accepted artifact lineage.

The current acceptance metadata is useful evidence for the core selection:
343 source records, three proxy ids, seven unique proxy owners, five unknown
ids, embedded payload present, and recorded file sizes. It does not supply
consumed-input hashes, source role/class/furniture diagnostics, projected-hole
coverage, or cell recovery evidence.

### Concrete recovery question

`build_field_layer_manifest()` is the semantic baseline: its original record
has `support.target` and full `provenance`, but no top-level `target` or
`provenance_ref`. The runner adds top-level `target` for SVG indexing and
`provenance_ref` for deduplication. Therefore `recover_cell()` removing those
two output-only fields is not, by itself, an SC-002 failure. The required
comparison is against the original
`FreeSpaceField.evaluate() -> build_field_layer_manifest()` record, including
support/query/source/value/status and the full provenance.

The real unresolved question is recursive provenance recovery:
`recover_cell()` replaces the cell's selected-record payload with the shared
table, but no focused test proves that nested selected-record structures,
support, and every provenance key are exactly preserved relative to the
canonical pre-dedup record. The final implementation must establish that
comparison explicitly; do not expand scope merely to retain output-only
`target` or `provenance_ref`.

### Frozen visual/geometry requirements still unproven

- The SVG path builder emits an exterior and hole rings with
  `fill-rule="evenodd"`, but the only focused hole test checks absence of one
  vertex. It does not project a synthetic mesh and assert coverage inside each
  hole versus adjacent shell coverage.
- The six status names in `acceptance.json`/legend are not six-state
  availability evidence. The manifest must report which statuses are present
  or explicitly unavailable; legend membership alone is insufficient.
- The revised path still has no top-level consumed-input hash ledger and no
  source-layer role/class/furniture/unknown diagnostic fields.

Accordingly this path remains intermediate eligibility evidence only. Browser
automation is not required by the spec assumptions, and B3 remains OPEN. No
projection, tests, runner, docs, or Git state was changed.

## Current Runner Static Review: Reuse Path

The runner is still under repair and this is not final acceptance. Two
substantive issues remain in the new `--reuse-projection` path.

1. **Effective offset is applied twice.** In
   `build_inspection(projected_handoff=...)` (around lines 402-426), the
   handoff domain is reconstructed from `handoff["domain"]["components"]`.
   Those components are already the translated/effective domain written by a
   prior build. The common path then calls
   `translate(facts["domain_polygon"], xoff=offset[0], yoff=offset[1])`
   again (around line 446). Reuse therefore shifts the domain a second time,
   while the source projection geometry remains in the handoff frame. This
   can make lattice bounds and domain/source alignment wrong even if the
   handoff itself is valid. Minimal repair: reuse the handoff domain in its
   already-effective frame, or carry an explicitly unshifted source-origin
   domain and translate exactly once; assert the frame/offset provenance.

2. **Reuse trusts stale output data instead of revalidating the current frozen
   ledger.** The reuse branch copies `source_layer`,
   `input_hashes["entries"]`, `origin_offset_m`, and boundary ids from the old
   `inspection_manifest.json`, while `B3.frozen_inputs()` is called only for
   partial facts. It does not compare the handoff ledger with a freshly
   reconstructed `_input_hash_ledger()`, verify the source handoff's successful
   execution/manifest lineage, or require the handoff boundary membership to
   equal the current frozen `boundary`. The fallback
   `facts["selection"].get("boundary_scoped_ids", ... default [])` can silently
   turn a missing boundary field into an empty boundary. Minimal repair: accept
   only a validated successful source handoff whose complete selected audit,
   domain, boundary, and input ledger exactly match current frozen facts; fail
   closed on missing/mismatched boundary rather than defaulting to `[]`.

The focused tests currently cover typed owner resolution and saved count/byte
metadata, but do not exercise either reuse invariant or the required projected
hole coverage. All new runner functions inspected have English docstrings.
No projection, tests, Blender, runner, architecture, or Git state was changed.

## Intermediate Artifact Review: `run_20261010T152122Z_3379c1`

This artifact is still intermediate and is not final acceptance evidence.
Observed execution is `mode="reuse_projection"`, `exit_0`, with disk sizes
`inspection_manifest.json=20,063,836` and `inspection.html=12,621,529`; the
recorded `sizes` match those disk bytes. The embedded JSON payload has the same
343 source records and 3,969 cells as the manifest, and the core field/domain
payloads compare equal.

### Confirmed repairs and eligibility evidence

- The reuse branch now keeps the already-effective handoff domain instead of
  translating it a second time. The current artifact reports one domain
  component with two holes and the same effective `origin_offset_m` used by
  the lattice.
- Source selection is correct: 343 records comprise 340 originals plus three
  accepted proxies. Proxy owner coverage is 1 + 3 + 3, seven distinct owners
  exactly once.
- Display categories are present and count 95 `furniture`, 245
  `physical_context`, and three `accepted_proxy` records. Source records now
  expose `source_role`, `source_class`, geometry/source refs, and proxy
  provenance. The field statuses are 1,544 `conditional`, 1,886 `unknown`,
  and 539 `outside`; conditional cells carry `value=True`, while unknown and
  outside carry `value=None`.
- SVG generation uses the same bounds/scale function for both panels, emits
  domain holes with `fill-rule="evenodd"`, creates 3,969 clickable cell
  rectangles, and embeds a JSON payload equal to the disk manifest. The
  writer-focused test covers this byte/payload loop.

### Remaining concrete blockers

1. **Reuse input ledger is incomplete.** The artifact’s
   `input_hashes.entries` contains only 10 entries: six package artifacts,
   binding declaration, capture manifest, structural capture, and scope. It
   contains zero `captured_mesh` entries and zero `proxy_object` entries,
   despite the contract requiring all 354 meshes and three proxy objects.
   This occurs because the reuse branch copies
   `handoff["input_hashes"]["entries"]` instead of comparing/replacing it with
   a freshly reconstructed `_input_hash_ledger()`. The successful
   `source_handoff_sha256` lineage does not repair the missing per-mesh/object
   fingerprints.

2. **Global unknown diagnostics are dropped in reuse mode.** The artifact’s
   `uncertainty_sources` is empty. In `build_inspection(projected_handoff=...)`,
   `source_facts` is deliberately `{}` and the uncertainty list iterates over
   no scene sources, so the five global unknown owners appear only as
   `audit.unknown_source_ids` and field provenance, not as source-bound
   `UncertaintyRecord` diagnostics. The final output must preserve those five
   diagnostics while retaining their global unknown semantics.

The earlier reuse boundary/unknown identity checks are now present and the
double-offset issue is resolved. Focused tests still do not prove actual
projected-hole coverage, nor do they assert the 354+3 ledger and non-empty
reuse unknown diagnostics. B3 remains OPEN; no runner, tests, architecture,
or Git state was changed in this review.

## Closing Gap Review: `run_20261010T153011Z_ef95cf`

The latest artifact supplies the requested intermediate evidence:

- 368 ledger entries: 354 `captured_mesh`, 3 `proxy_object`, 6 package
  artifacts, binding/capture/structural/scope/proxy-metadata entries.
- Five `uncertainty_sources`, exactly matching the five locked unknown ids,
  each with `missing_geometry` and capture hash provenance.
- Distinct `source_origin_offset_m=[0,0]` and effective
  `origin_offset_m=[-5.150000095367432,-0.30000001192092896]`.
- Reuse lineage records the source-handoff path and SHA; the written JSON and
  HTML sizes match the recorded `20,219,660` and `12,727,971` bytes.
- The artifact's audit reports 95 furniture, 245 physical-context, and three
  accepted proxies. The architecture documents both describe the inspection
  layer as implemented while retaining B3 OPEN.

### Remaining concrete gaps

1. **Captured-mesh ledger paths are not self-resolving.** All 354 mesh entries
   use paths such as `meshes/59.json`, while package/proxy entries use
   repository-relative paths. The manifest does not carry the capture-root
   prefix or a base URI for those relative paths. A consumer of the artifact
   alone cannot resolve and re-hash the captured meshes without knowing the
   private `B3.CAPTURE` root. Minimal fix: serialize repository-relative paths
   (or an explicit `base_path`/root identifier) while preserving the
   authenticated bytes and SHA-256 values.

2. **Focused tests do not target the current final path or changed reuse
   path.** `test_revised_artifact_has_exact_proxy_and_byte_evidence()` reads
   `run_20261010T141847Z_c347ce_revised`, and
   `test_input_ledger_and_source_audit_are_complete()` reads
   `run_20261010T141847Z_c347ce_replay2`; neither reads
   `run_20261010T153011Z_ef95cf` or invokes `--reuse-projection`. The ledger
   assertion remains `len(entries) >= 10`, so it would pass without 354 mesh
   entries. This is a changed-path regression gap, not a core Field issue.

3. **Checklist/document status is not fully synchronized.** Both architecture
   documents now say the Spec002 layer is implemented and explicitly keep B3
   open, which matches the current slice. The living checklist still leaves
   per-proxy provenance, non-furniture occupancy, boundary acceptance,
   demonstration labeling, SC-002 comparison, and frozen-hash verification
   unchecked while marking replay evidence complete. Before final acceptance,
   either close those items with this artifact/test evidence or state why each
   remains intentionally open; do not claim the checklist is fully green.

No projection, pytest, Blender, runner, architecture, or Git mutation was
performed in this review. The artifact remains intermediate pending these
targeted output/test/document reconciliations.

## Final Static Reuse-Path Check

The current repair correctly calls `_whole_height_scene()` before consuming a
handoff, enriches reused source records from the authenticated scene, and
keeps the effective domain offset separate from `source_origin_offset_m`.
Those changes address the earlier double-offset and missing-source-facts
issues.

Two reuse-path gaps remain:

1. **Cached query/domain contract is not fail-closed.** The reuse branch checks
   source identities, boundary ids, and unknown ids, but it does not explicitly
   reject a handoff whose top-level `schema`, `frame`, `units`,
   `query_scope`, `resolution_m`, `domain.frame`, or domain components are
   missing or inconsistent. It also reconstructs only the first domain
   component. The Spec002 refusal contract requires stale/inconsistent domain
   and non-whole-height inputs to refuse output. Minimal repair: validate the
   exact `free-space-field-inspection/v1`, `world_xy`, `m`, `whole_height_plan`,
   `0.25`, effective offset, and complete domain components before reuse; compare
   the handoff ledger with `authenticated_facts["input_hashes"]` rather than
   merely copying the handoff entries.

2. **Old acceptance metadata is copied into the new result.** `_reuse_projection()`
   reads `source/acceptance.json` and inserts it verbatim into the new payload.
   That file can contain prior run counts/status claims, so a reuse output can
   appear to carry acceptance for the current rendering even though those
   values were not recomputed in this invocation. Minimal repair: do not copy
   the old acceptance file, or regenerate a fresh acceptance record solely from
   the newly built payload, fresh lineage hash, and current disk byte counts.

The focused synthetic tests cover reuse determinism and writer round-trip, but
do not currently exercise these invalid-cache refusal cases or stale
`acceptance.json` isolation. This remains a static review finding; no
projection, pytest, Blender, runner, architecture, or Git state was changed.

## Review Disposition Before Next Artifact

The worker’s proposed repair addresses both findings in principle: reuse will
use the existing 368-entry `ef95cf` ledger as the geometry baseline, normalize
legacy `meshes/*` references against the authenticated capture root before
comparing the complete fresh ledger, and validate source-origin/effective
offsets, domain holes, schema, frame, units, and whole-height query against
fresh facts. Removing the old `acceptance.json` copy also prevents prior-run
claims from being presented as current acceptance.

No new artifact or test result was reviewed in this turn, so these remain
pending implementation evidence rather than accepted fixes. B3 remains OPEN.
