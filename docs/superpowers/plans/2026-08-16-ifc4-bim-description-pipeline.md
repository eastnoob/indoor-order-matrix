# IFC4 BIM Description Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a BIM-native, source-independent description and inference pipeline that accepts IFC, explicitly selected Blender geometry, hybrid IFC/Blender geometry, and SVG, then produces auditable description records and a disposable three-dimensional Blender acceptance run without perceptual weights or a final score.

**Architecture:** Bonsai/Blender authors and previews; IFC remains the durable factual source; explicit Blender geometry is an opt-in geometry source; SVG is a planar adapter. All adapters terminate at a pure Neutral Scene v2 contract. Functional substitutes (`MassPatch`, `SurfacePatch`, `AffordanceZone`) and task views feed the existing region, path, trend, network, boundary, and column-grid analysis, while the exported description registry remains separate from any later fitted feature model.

**Tech Stack:** Python 3.12 via Pixi, existing geometry helpers, IfcOpenShell 0.8.5 when available, Blender 5.2 portable executable, pytest, nbformat/nbclient, JSON artifacts, and jj for history checkpoints.

---

## Operating Rules For Every Gate

Every gate below is a hard checkpoint. The worker must complete the steps in
order, run the listed focused tests, run the full accepted regression suite,
perform the gate-specific Grill Me review, repair findings in the same gate,
and only then create the listed jj checkpoint. A later gate may not repair an
earlier gate's contract silently.

```text
write failing test -> prove failure -> implement minimum slice -> focused test
-> artifact inspection -> full pytest -> Grill Me self-review -> repair
-> jj commit -> record change id and test evidence
```

For every new or modified project-owned function:

- add an English docstring;
- add English comments before important geometry, inference, graph, scoring,
  serialization, and adapter handoff operations;
- keep weights and final scores out of Neutral Scene and description records;
- preserve source ids, method names, tolerances, capabilities, and uncertainty.

The commands below run from `D:\PROJECTS\understandOtherPackage\order_analyzer`.
Use `pixi run`, never pip or a virtualenv. Use only
`D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` for Blender.

## Gate 0: Baseline And Acceptance Manifest

**Purpose:** Freeze a trustworthy starting point and define the stable ids and
assertions that the later Blender fixture must satisfy.

**Files:**
- Create: `test/bim/acceptance_manifest.py`
- Create: `test/bim/test_acceptance_manifest.py`
- Modify: `docs/indoor_layout_evaluation_matrix_task_status.md`

- [ ] **Step 1: Record the baseline.**

Run:

```powershell
pixi run pytest
jj status
jj log -r @ --no-graph
```

Expected: `295 passed`, a clean working copy except for the empty plan
working-copy commit, and the current parent is the amended design spec.

- [ ] **Step 2: Write the failing manifest test.**

The test must require stable ids for `room`, `floor`, `wall_north`,
`table_group_aligned`, `table_group_oblique`, `sofa`, `low_cabinet`,
`glass_partition`, `carpet`, `grid_main`, and two chair affordances. It must
also require output paths `test/output/blender_demo_description.json` and
`test/output/blender_demo_room_analysis_model.json`.

- [ ] **Step 3: Implement the manifest.**

Expose a plain dict and a validator. The validator must reject duplicate ids,
missing required output names, and an input mode outside `ifc`,
`blender_geometry`, `hybrid`, and `svg`.

- [ ] **Step 4: Verify and self-review.**

Run the focused manifest tests, then `pixi run pytest`. Grill Me questions:
does the manifest depend on viewport names, does it encode a weight, and can a
fixture be regenerated without manual edits? Repair any yes before continuing.

- [ ] **Step 5: Create the checkpoint.**

```powershell
jj commit -m "test: lock BIM acceptance manifest and baseline"
```

Checkpoint: `JJ-00-baseline`.

## Gate 1: Neutral Scene V2 Contract

**Purpose:** Create source-independent records and strict JSON round trips.

**Files:**
- Create: `features/scene_contract.py`
- Create: `test/test_scene_contract.py`
- Modify: `features/__init__.py`
- Modify: `docs/room_analysis_model_development_standard.md` only if the public
  contract needs a documented version addition

- [ ] **Step 1: Write failing record and round-trip tests.**

Cover `AnalysisContext`, `AnalysisDomain`, `SourceObject`, `MeshGeometry3D`,
`MaterialFact`, `SurfaceFact`, `AuthoredGroup`, `AuthoredGrid`,
`AuthoredGridAxis`, `AuthoredAffordanceZone`, `SourceOpening`, and
`UncertaintyRecord`. Assert that nested records serialize to JSON-compatible
lists, dicts, strings, numbers, booleans, and null only.

- [ ] **Step 2: Implement immutable-enough dataclass records and serializers.**

Use standard-library dataclasses and explicit `to_dict`/`from_dict` methods.
Validate contract version, normalized units, analysis plane basis, source ids,
and tolerance values at construction. Do not import SVG, Blender, Bonsai,
IfcOpenShell, or OCTA.

- [ ] **Step 3: Add capability and uncertainty behavior.**

Represent absent height, optical, domain, grid, or affordance evidence as an
explicit capability/unavailable record rather than `0.0` or a guessed bbox.

- [ ] **Step 4: Verify and self-review.**

Run:

```powershell
pixi run pytest test/test_scene_contract.py -q
pixi run pytest
```

Grill Me: can a raw `Rect`, mesh object, IFC entity, or Blender object leak
through serialization? Can a missing value be mistaken for zero? Repair in this
gate if yes.

- [ ] **Step 5: Create the checkpoint.**

```powershell
jj commit -m "feat: add Neutral Scene v2 contract and serializers"
```

Checkpoint: `JJ-01-contract`.

## Gate 2: SVG Adapter And Compatibility Boundary

**Purpose:** Route the existing SVG fixtures through the new contract without
letting SVG define regions, paths, boundaries, or matrix behavior.

**Files:**
- Create: `adapters/__init__.py`
- Create: `adapters/svg_scene.py`
- Create: `test/test_svg_scene_adapter.py`
- Modify: `features/scene_loader.py` only for a compatibility call-through
- Modify: `docs/indoor_layout_evaluation_matrix_architecture_memory.md` if a
  compatibility limitation needs recording

- [ ] **Step 1: Write failing adapter-contract tests.**

Load `test/SVG_baseline.svg`, `test/SVG_oblique.svg`, and
`test/SVG_chaoticsvg.svg`. Assert stable source ids, planar capability flags,
authored affordance preservation, authored column axes preservation, and no
fabricated height, optical, or affordance records.

- [ ] **Step 2: Implement the adapter.**

Translate current scene-loader records into Neutral Scene v2. Keep XML/data-
attribute parsing here. Preserve the old loader as a compatibility wrapper so
existing region/trend tests remain runnable during migration.

- [ ] **Step 3: Add cross-adapter shape checks.**

Assert that the adapter imports no Blender or IFC dependency and that a plain
dict fixture can reach the inference layer without an SVG parser.

- [ ] **Step 4: Verify, self-review, and repair.**

Run the focused adapter tests and `pixi run pytest`. Grill Me: did any region,
path, boundary, trend, or score get authored by the SVG adapter? If yes, move
that behavior into the inference layer before checkpointing.

- [ ] **Step 5: Create the checkpoint.**

```powershell
jj commit -m "feat: adapt SVG fixtures to Neutral Scene v2"
```

Checkpoint: `JJ-02-svg-adapter`.

## Gate 3: Functional Geometry Substitutes And Views

**Purpose:** Make three-dimensional geometry computable without source-specific
proxy classes or scalar object heights.

**Files:**
- Create: `features/geometry_substitutes.py`
- Create: `features/geometry_views.py`
- Create: `test/test_geometry_substitutes.py`
- Create: `test/test_geometry_views.py`

- [ ] **Step 1: Write failing synthetic-mesh tests.**

Use deterministic meshes for a constant-height box, sofa seat/back/arms,
bottom void, low cabinet, open mesh, and split-level platform. At named plan
points assert expected occupied vertical intervals and explicit uncertainty for
open/non-manifold input.

- [ ] **Step 2: Implement `MassPatch`, `SurfacePatch`, and `AffordanceZone`.**

Keep source geometry and provenance on the records. Allow multiple patches per
source object. Do not inspect IFC class names, SVG metadata, or furniture names.

- [ ] **Step 3: Implement deterministic task views.**

Implement `plan_projection`, `vertical_intervals_at`, `vertical_profile`,
`surface_elevation_at`, `occlusion_intersections`, and `clearance_geometry`.
Use a spatial index for repeated mesh queries; use bbox only as a diagnostic or
explicit fallback with uncertainty.

- [ ] **Step 4: Verify and self-review.**

Run focused geometry tests and the full suite. Grill Me: does the sofa back
change only a global height, or does it change local intervals? Does a missing
solid become false certainty? Repair before checkpoint.

- [ ] **Step 5: Create the checkpoint.**

```powershell
jj commit -m "feat: add functional geometry substitutes and task views"
```

Checkpoint: `JJ-03-geometry-views`.

## Gate 4: Surfaces, Elevation, And Boundary Evidence

**Purpose:** Derive boundaries from geometry and surface relations while keeping
physical, walking, visual, and Gestalt channels separate.

**Files:**
- Create: `features/boundary_evidence.py`
- Create: `test/test_boundary_evidence.py`
- Modify: `features/scene_inference.py`
- Modify: `features/scene_evaluator.py`
- Modify: `features/room_analysis_model.py`

- [ ] **Step 1: Write failing channel tests.**

Cover a carpet/color surface with no mass, a wall, a low cabinet, a glass-like
partition with optical facts, a walkable gap, and a split-level edge. Assert
that each result exposes physical continuity, walking permeability, visual
permeability, and Gestalt continuity independently.

- [ ] **Step 2: Implement candidate generation and subject relations.**

Generate candidate interfaces from mass contours, occupied-height changes,
openings, elevation changes, surface edges, and continuation. Expose distance,
side, frame agreement, coverage, containment, openings, and channel
observations. Range limits produce `not_evaluated`, never zero.

- [ ] **Step 3: Keep description weight-free.**

Reject or isolate legacy aggregate boundary weights behind an explicit
compatibility flag. Do not emit `boundary_strength`, `walk_block`, `see_block`,
or `grouping_strength` as authored/final values.

- [ ] **Step 4: Verify and self-review.**

Run focused tests and `pixi run pytest`. Grill Me: can a carpet become a wall
because its color contrast is high? Can a low cabinet be treated as fully
opaque without geometry/material evidence? Repair in this gate.

- [ ] **Step 5: Create the checkpoint.**

```powershell
jj commit -m "feat: add weight-free multi-channel boundary evidence"
```

Checkpoint: `JJ-04-boundary-evidence`.

## Gate 5: IFC4/Bonsai Adapter

**Purpose:** Read IFC4 facts through IfcOpenShell and map them to Neutral Scene
without computing analysis in Blender.

**Files:**
- Create: `adapters/ifc_bonsai.py`
- Create: `test/test_ifc_bonsai_adapter.py`
- Create: `test/fixtures/ifc4_description_fixture.py`
- Modify: `pyproject.toml` or `pixi.toml` only if the locked environment lacks
  an already available IFC dependency

- [x] **Step 1: Write failing in-memory IFC4 fixture tests.**

Build furniture, groups, walls, slab, openings, covering, surface feature,
affordance zone, and grid axes in memory. Serialize/reopen and assert stable
source ids and mappings. Add missing geometry, missing grid, missing domain,
and IFC4 versus IFC4X3 schema-guard cases.

- [x] **Step 2: Implement read-only extraction.**

Resolve units and placements once, extract tessellated transport meshes with
settings provenance, map native IFC relationships, and emit structured
uncertainties. Never infer a column grid, affordance, region, path, boundary,
trend, order, or score here.

- [x] **Step 3: Add no-mutation tests.**

Hash source entity ids and serialized source facts before and after adapter use.
Assert that the hashes are unchanged.

- [x] **Step 4: Verify and self-review.**

Run focused IFC tests and `pixi run pytest`. Grill Me: does an IFC class decide
boundary meaning, or merely select factual extraction? Does IFC4 code touch an
IFC4X3-only relationship without a capability check? Repair before checkpoint.

- [x] **Step 5: Create the checkpoint.**

```powershell
jj commit -m "feat: add read-only IFC4 Bonsai adapter"
```

Checkpoint: `JJ-05-ifc-adapter`.

Gate 5 verification record (2026-08-17): strict RED/GREEN cycles repaired
optical IFC value typing, unit dimensionality, type-level `OM_Surface`
inheritance, invalid occurrence overrides, source provenance, explicit
affordance purpose/source ids, and semantic reference auditing when geometry
or purpose is unavailable. Three independent read-only reviews ended with no
Critical or Important findings. Final focused cross-adapter result was
`225 passed`; final full result was `568 passed in 879.64s` under Pixi Python
3.12.13. Compileall, project-owned function docstring audit, JSON/no-mutation
checks, and `git diff --check` also passed.

## Gate 6: Explicit Blender Geometry And Hybrid Modes

**Purpose:** Permit analysis of a normal Blender model without making Blender a
second implicit BIM authority.

**Files:**
- Create: `adapters/blender_geometry.py`
- Create: `test/test_blender_geometry_adapter.py`
- Modify: `features/scene_contract.py`

- [x] **Step 1: Write failing mode-isolation tests.**

Create a Blender-side fixture with selected meshes, unselected distractor
meshes, explicit role/group mappings, an explicit domain, and an explicitly
linked helper. Assert that `ifc` ignores distractors, `blender_geometry`
includes only selected meshes, and `hybrid` includes only explicit links.

- [x] **Step 2: Implement mode validation and extraction.**

Record mode, selected source ids, helper links, absent IFC identity, and
capabilities in provenance. Preserve explicit role, surface, grid, group, and
affordance mappings; do not infer them from object or collection names.

- [x] **Step 3: Verify and self-review.**

Run focused tests and the full suite. Grill Me: can simply opening a Blender
file change an IFC analysis result? Can an unselected mesh enter because it is
visible? Can a mesh with no role silently become furniture? Repair before
checkpoint.

- [x] **Step 4: Create the checkpoint.**

```powershell
jj commit -m "feat: support explicit Blender geometry and hybrid input modes"
```

Checkpoint: `JJ-06-blender-input-modes`.

Gate 6 verification record (2026-08-17): the adapter accepts only explicit
evaluated Blender mesh snapshots. `ifc` mode short-circuits before reading
Blender input; `blender_geometry` uses selected ids only; `hybrid` uses only
explicit helper-to-IFC links. Names, visibility, collections, bboxes, and IFC
classes do not provide semantics. Missing geometry, unknown selections/roles/
links, duplicate record ids, and dangling cross-record references are explicit
errors or uncertainties rather than silent omissions. Three independent
read-only reviews ended with no Critical or Important findings. Final focused
cross-adapter result was `240 passed`; final full result was
`583 passed in 811.86s` under Pixi Python 3.12.13. Compileall, project-owned
function docstring audit, JSON/no-mutation checks, and `git diff --check` also
passed.

## Gate 7: Migrate Existing Analysis Consumers

**Purpose:** Make the existing region, path, network, trend, local-reference,
and column-grid logic consume neutral facts and derived views rather than raw
SVG fields, world bboxes, or authored weights.

**Files:**
- Modify: `features/scene_inference.py`
- Modify: `features/scene_evaluator.py`
- Modify: `features/column_grid.py`
- Modify: `features/room_analysis_model.py`
- Modify: `features/local_reference.py`
- Create: `test/test_neutral_scene_analysis_regression.py`

- [x] **Step 1: Write adapter-independent regression tests.**

Feed a plain Python Neutral Scene fixture with rectangular geometry and no SVG
parser. Assert furniture affordance extents, group extents, activity regions,
remaining free-space paths, shared-scope network records, two-axis trend and
strength, and local/global grid relations.

- [x] **Step 2: Replace raw-source access at one consumer at a time.**

Use explicit view protocols and preserve legacy planar output through a labeled
compatibility adapter. Region trend remains furniture-group frame consensus;
shape PCA and polygon geometry describe shape rather than overriding trend.

- [x] **Step 3: Add cross-adapter equivalence tests.**

Equivalent planar SVG and IFC fixtures must produce equivalent derived plan
evidence within recorded tolerances. Planar SVG must report height-aware
metrics unavailable rather than inventing them.

- [x] **Step 4: Verify and self-review.**

Run focused migration tests and `pixi run pytest`. Grill Me: can the evaluator
run on a dict with no SVG? Did compatibility fields accidentally become source
truth? Did any weight enter the description registry? Repair before checkpoint.

- [ ] **Step 5: Create the checkpoint.**

```powershell
jj commit -m "refactor: consume neutral scene views in layout analysis"
```

Checkpoint: `JJ-07-analysis-migration`.

Verification evidence before checkpoint creation:

- adapter-independent Neutral regression: `32 passed`;
- Gate 7 focused migration set: `122 passed in 4.50s`;
- SVG adapter: `64 passed`; IFC adapter: `62 passed`;
- negative-space, line-of-sight, and sampled-channel subset: `35 passed`;
- full suite after the Cartesian cell-adjacency optimization:
  `620 passed in 298.00s` (`0:04:57`);
- `compileall` and `git diff --check` passed (line-ending warnings only);
- independent spec review approved; quality review's unavailable-topology
  propagation finding was repaired, regression-tested, and approved on
  re-review.

## Gate 8: Programmatic Three-Dimensional Acceptance Scene

**Purpose:** Build the user-approved simple three-dimensional version of the
existing SVG organization and prove that the full pipeline has a realistic
height-aware input.

**Files:**
- Create: `test/blender/__init__.py`
- Create: `test/blender/generate_bim_acceptance_scene.py`
- Create: `test/blender/run_bim_acceptance.py`
- Create: `test/test_bim_acceptance_scene.py`
- Create: `test/output/blender_demo_description.json`
- Create: `test/output/blender_demo_room_analysis_model.json`

- [ ] **Step 1: Write failing acceptance assertions.**

Require the manifest ids and the assertions from the spec: local sofa height
interval differences, carpet without mass, distinct cabinet/partition walking
and visual evidence, explicit affordances, three furniture ordering cases,
internal/inter-region graphs, grid relations, provenance, uncertainty, and
weight-free JSON outputs.

- [ ] **Step 2: Generate the scene deterministically.**

Create room/floor/walls; simple tables, chairs, sofa seat/back/arms, cabinet,
carpet, transparent partition, explicit chair affordance volumes, and authored
grid axes. Place aligned, oblique, and mixed groups using stable transforms.
Write a temporary `.blend` or IFC fixture only as a generated artifact.

- [ ] **Step 3: Run both supported paths where applicable.**

Analyze the generated IFC through `ifc_bonsai`; analyze explicitly selected
Blender geometry through `blender_geometry`; compare shared description records
where both paths describe the same facts. Save the two required JSON outputs.

- [ ] **Step 4: Verify and self-review.**

Run the acceptance test and `pixi run pytest`. Re-run generation and compare
JSON after removing only explicitly timestamped provenance. Grill Me: can the
fixture pass with a one-height bbox, invented affordances, or a surface treated
as mass? It must fail those regressions.

- [ ] **Step 5: Create the checkpoint.**

```powershell
jj commit -m "test: add generated three-dimensional BIM acceptance scene"
```

Checkpoint: `JJ-08-acceptance-scene`.

## Gate 9: Blender Preview And Notebook Inspection

**Purpose:** Make the results inspectable without making visualization the
authority.

**Files:**
- Create: `adapters/blender_preview.py`
- Create: `test/test_blender_preview.py`
- Create: `test/bim_description_demo.ipynb`
- Create: `test/output/bim_description_demo.executed.ipynb`
- Create: `test/output/bim_description_demo.visual.png`
- Create: `test/output/bim_description_demo.visual.html`

- [ ] **Step 1: Write failing preview tests.**

Assert that regeneration creates only `OM_AnalysisPreview`, keeps source IFC
entity digest stable, and emits source geometry, inferred regions, two trend
axes, authored grid axes, paths, and compact boundary-channel summaries.

- [ ] **Step 2: Implement output-only preview.**

Use result ids and source GlobalIds, never IFC classes for derived records. Draw
the original geometry and overlays together. Keep legends compact and keep
tables outside the main geometry view where possible.

- [ ] **Step 3: Execute the notebook.**

Run:

```powershell
pixi run python -c "import nbformat; from nbclient import NotebookClient; p='test/bim_description_demo.ipynb'; o='test/output/bim_description_demo.executed.ipynb'; n=nbformat.read(p, as_version=4); NotebookClient(n, timeout=300, kernel_name='python3').execute(); nbformat.write(n, o)"
```

Export the visual HTML/PNG using the repository's existing notebook flow.

- [ ] **Step 4: Perform portable-Blender visual verification.**

Run the generated acceptance scene with
`D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe`, inspect plan and
3D views, and confirm that source geometry, regions, both trend axes, grid,
paths, and selected boundary channels are all visible and not replaced.

- [ ] **Step 5: Verify and self-review.**

Run focused preview tests, execute the notebook again, and run `pixi run
pytest`. Grill Me: can a misleading overlay hide missing JSON evidence? The
answer must be no; the notebook must read and display the serialized records.

- [ ] **Step 6: Create the checkpoint.**

```powershell
jj commit -m "feat: add Blender preview and BIM description notebook"
```

Checkpoint: `JJ-09-preview-and-notebook`.

## Gate 10: Final Cross-Adapter Verification And Handoff

**Purpose:** Prove the complete delivery and document residual limitations.

**Files:**
- Modify: `docs/superpowers/specs/2026-08-16-ifc4-bim-description-pipeline-design.md`
- Modify: `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- Modify: `docs/indoor_layout_evaluation_matrix_task_status.md`
- Create: `test/output/bim_acceptance_verification.json`

- [ ] **Step 1: Run all required verification.**

```powershell
pixi run pytest
pixi run python -m json.tool test/output/blender_demo_description.json
pixi run python -m json.tool test/output/blender_demo_room_analysis_model.json
jj status
```

Run the portable Blender no-mutation check and notebook execution again. Record
the exact test count, artifact paths, source digest result, and unavailable
evidence in `bim_acceptance_verification.json`.

- [ ] **Step 2: Perform the final spec-to-plan audit.**

For every success criterion, point to a test, artifact, or preview assertion.
Search the implementation and outputs for forbidden authored aggregate weights,
raw geometry leakage, whole-scene bbox fallback, and unlinked Blender object
inclusion. Fix any finding in the responsible gate, re-run that gate, then
return here.

- [ ] **Step 3: Update documentation.**

Record the completed checkpoints, supported modes, exact generated artifacts,
known IFC4 limitations, planar SVG unavailable metrics, and the fact that
perception fitting/weights remain a later phase.

- [ ] **Step 4: Create the final checkpoint.**

```powershell
jj commit -m "test: verify complete BIM description pipeline"
```

Checkpoint: `JJ-10-final-verification`.

## Plan Self-Review

### Spec coverage

- Neutral Scene v2 and serialization: Gate 1.
- SVG/IFC separation: Gates 2 and 5.
- Explicit Blender and hybrid modes: Gate 6.
- Mass, surface, affordance substitutes and local height: Gate 3.
- Four boundary channels and elevation: Gate 4.
- Region, path, network, trend, and grid migration: Gate 7.
- Generated three-dimensional acceptance model and required JSON: Gate 8.
- Blender visualization and notebook inspection: Gate 9.
- Cross-adapter, no-mutation, and final evidence: Gate 10.
- Reversible jj history at every major stage: every gate checkpoint.

### Placeholder scan

No `TBD`, `TODO`, unnamed helper, or “handle later” step is used. Every code
change names its file, test, command, expected verification, and checkpoint.

### Type and name consistency

- Input modes are exactly `ifc`, `blender_geometry`, `hybrid`, and `svg`.
- Long-lived substitutes are exactly `MassPatch`, `SurfacePatch`, and
  `AffordanceZone`.
- Required artifacts are exactly
  `blender_demo_description.json` and
  `blender_demo_room_analysis_model.json`.
- Preview collection is exactly `OM_AnalysisPreview`.
- Network scopes remain `region_internal` and `inter_region` under one graph
  schema.

### Grill Me conclusion

The plan is safe to execute because it does not require repairing the user's
current Blender toy scene, does not make viewport visibility a source fact,
does not invent affordances or grids, does not collapse boundary evidence into
a weight, and cannot advance past a failing gate without a jj checkpoint. The
first implementation target is the contract and acceptance manifest, not a
large Blender integration jump.
