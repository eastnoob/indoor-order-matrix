# D6 pairwise channel run_002 independent review

Review mode: read-only independent review.  No run_002 artifact, run_001 artifact,
input contract, production code, adapter, test, API, source IFC, or user Blender
file was modified.  The only project file added by this review is this document.

Branch reviewed: `codex/d6-pairwise-channel-run2-design`  
Review date: 2026-10-03  
Review scope: `outputs/design/space_field_pairwise_channel_experiment/run_002`

## Blockers

None for the bounded design-evidence decision.  The evidence is sufficient for a
limited design experiment and for another design-only round.  It is not sufficient
to authorize implementation design or any production selector/API.

## Important findings

1. Candidate preservation works at the data level.  `candidate_evidence.json`
   contains all 12 fixture records; the qualified fixtures retain one candidate
   each except `multiple_candidate_channels`, which retains `candidate:01` and
   `candidate:02`.  Each serialized candidate has `candidate_id`, `source_ids`,
   `source_refs`, `floor_eligibility`, `domain_relation`, `geometry`,
   `geometry_valid`, `validity`, and `provenance`.  `candidate_count` matches the
   serialized list.  The missing-domain fixture correctly has zero candidates and
   `not_available`.

2. Multiple-candidate behavior is correct.  The set status is `ambiguous`, both
   candidates are retained, `selection.selected_candidate_id` is `null`,
   `selection.selector` is `none`, and no candidate has `accepted = true`.
   The free-space profile remains `ambiguous`, while connectivity remains
   `computed_same_component` with `candidate_selection_independent = true`.

3. Connectivity is computed independently from candidate selection.  The runner
   uses `qualified domain minus unioned physical occupancy` before it computes
   components.  The disconnected fixture remains `computed_disconnected` with
   two components.  The multiple-candidate fixture does not become ambiguous
   connectivity.  Column/furniture overlap is unioned once (`0.24 m2` overlap
   removed in the overlap fixture), wall/column contact is also unioned once, and
   the open column row remains a single connected component rather than becoming
   a virtual wall.

4. Status propagation is correct at the estimand layer.  Missing AnalysisDomain
   produces `not_available`; missing and invalid in-scope column geometry produce
   `partial`; the source-level reasons are preserved as `missing_geometry` and
   `invalid_geometry`; the other-floor source is recorded as
   `known_other_floor_exclusion` and does not force `partial`; and
   `computed_disconnected` is preserved.  The scene frame is explicitly marked
   as fixture-only and is not used as `AnalysisDomain`.

5. The three estimands are separated and labeled.  JSON and visual guardrails
   distinguish pairwise boundary gap, free-space profile, connectivity,
   synthetic candidate generation, and real IFC availability.  The real IFC
   audit records `adapter_rerun = false`, `pairwise_free_space_profile =
   not_available`, and `pairwise_connectivity_evidence = not_available`.
   Synthetic fixture results are not presented as real IFC partition/channel
   conclusions.  Route width, walkability, Bayesian/ML, fixed thresholds,
   production backend, and production selector remain unselected.

6. The implementation contract has a layer mismatch that must be repaired before
   implementation design.  `schema.json` lists `selection` in the per-candidate
   `candidate_contract`, but the artifact stores `selection` on `candidate_set`;
   `validate.py` also omits `selection` from its per-candidate required fields.
   The set-level location is the coherent current behavior, but the schema and
   validator must agree before a consumer is designed.

7. Candidate provenance is complete enough to audit the fixture but is not yet
   cleanly separated by role.  Normal candidate generation passes all obstacle
   records into `source_refs`; `_candidate_record` then reports all obstacle
   references under `relation.physical_occupancy_sources`, including the excluded
   Level 2 column and the missing/invalid columns.  Occupancy computation itself
   correctly excludes those records, but the candidate relation can be read as if
   those sources supported the candidate.  A future design should separate
   `support_basis_source_ids` from `occupancy_context_source_ids` and preserve
   exclusion state on the latter.

8. The status reason is machine-readable at source eligibility but flattened at
   the profile/connectivity layer.  The missing/invalid fixture emits the string
   `invalid_geometry; missing_geometry`.  This is adequate for the diagnostic,
   but a downstream contract should expose a reason-code list or structured
   per-source reasons instead of requiring string parsing.

9. The Blender PNG is readable as a disposable render and contains the required
   warnings, but the top warning text overlaps the central panel title area and
   the candidate labels are crowded.  The SVG render is clear, uncropped, and
   explicitly labels `synthetic fixture diagnostic`, `not real IFC
   partition/channel inference`, `not route width`, and `not walkability`.
   Improve PNG layout before using the visual as review-facing evidence.  This is
   a presentation issue, not a semantic pass/fail issue.

## Minor findings

- The JSON artifacts parse successfully, but `schema.json` is a declarative
  contract rather than a standard JSON Schema document; the reported schema pass
  comes from bespoke assertions in `validate.py`, not a JSON-Schema validator.
- `real_ifc_audit.json` correctly limits the available real-IFC result to
  existing geometric gap evidence, but reviewers must read its semantic limit
  because the field name still contains `pairwise_boundary_gap`.
- The stored artifact manifest is self-excluded by design.  All listed file byte
  counts and SHA-256 values match on independent recomputation.
- `source_refs` preserve identifiers, kind, and level, but they do not carry a
  source-geometry hash or an external geometry reference.  Reconstructing the
  fixture source geometry therefore still depends on the saved runner/fixture
  definitions.

## Validation evidence

- All 14 JSON files in run_002 parsed successfully.
- Independent deterministic rerun of `run_experiment.py` into a system temporary
  directory produced identical SHA-256 values for all 13 core JSON/Markdown/SVG
  artifacts compared with run_002.
- Independent manifest verification found no byte-count or SHA-256 mismatch.
- `blend_readback.json` reports `status = pass`, 45 objects, and all required
  semantic labels.  The PNG was opened and inspected directly.  The SVG was
  rendered from the saved file and inspected directly; no clipping was observed.
- The source IFC hash matches the recorded provenance and real-IFC audit hash:
  `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`.
- A focused `git diff --check` for the run_002 path returned no diagnostics.
  Focused tracked-path status checks returned no modifications under run_001,
  `features`, `adapters`, `test`, or the source-IFC path.

## Verdict and stage decision

**Decision for run_002: `ACCEPT LIMITED`.**

The bundle supports the stated limited design claim: candidate support geometry
and domain-bounded connectivity remain separately auditable across qualified,
ambiguous, missing-domain, floor-excluded, missing/invalid-geometry, and
disconnected synthetic fixtures.

**Next-stage design experiment: allowed.**  Continue with synthetic, design-only
experiments that preserve the same separation and explicit real-IFC boundary.

**Implementation design: not allowed yet.**  First reconcile the candidate schema
and validator, separate support provenance from occupancy context, normalize
reason propagation, and repair the disposable PNG layout.  This review does not
approve a production selector, fixed threshold, route width, walkability metric,
Bayesian/ML model, or production API.

## Unverified items and Git-scope limitation

The output tree and source IFC are ignored by `.git/info/exclude`, so Git cannot
prove historical byte-for-byte non-modification of ignored run_001/run_002 files
or the ignored source IFC.  The current focused status checks are clean, the
recorded source hash is internally consistent, and the existing scope artifacts
report no modification.  A repository-level historical proof would require a
tracked baseline or an external immutable manifest.

The repository-wide `git diff --check` command also encountered pre-existing
permission errors under `.tmp-test-preview-final2`.  The target-path
`git diff --check` completed cleanly; the global command result is therefore
reported as an environment limitation rather than as a run_002 failure.

## Actual checks and Git range

Commands used, in read-only or temporary-output mode:

```powershell
Get-Content -Raw AGENTS.md
Get-Content -Raw docs/indoor_layout_evaluation_matrix_architecture_memory.md
Get-ChildItem outputs/design/space_field_pairwise_channel_experiment/run_002
git status --short --branch
git diff --no-ext-diff --check -- outputs/design/space_field_pairwise_channel_experiment/run_002
git diff --no-ext-diff --name-status -- outputs/design/space_field_pairwise_channel_experiment/run_002
git status --short --untracked-files=no -- outputs/design/space_field_pairwise_channel_experiment/run_001
git status --short --untracked-files=no -- features
git status --short --untracked-files=no -- adapters
git status --short --untracked-files=no -- test
git status --short --untracked-files=no -- outputs/full-rhino-ifc-2026-09-23
Get-FileHash -Algorithm SHA256 outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc
pixi run python -c "...parse all run_002 JSON..."
pixi run python -c "...rerun run_experiment.py in a system temp directory and compare SHA-256..."
pixi run python -c "...recompute artifact_manifest byte counts and SHA-256 values..."
pixi run python -c "...render the saved SVG to a temporary PNG for visual inspection..."
```

Git scope inspected:

- Allowed experimental root: `outputs/design/space_field_pairwise_channel_experiment/run_002/`
- Forbidden roots checked: `outputs/design/space_field_pairwise_channel_experiment/run_001`,
  `features`, `adapters`, `test`, and `outputs/full-rhino-ifc-2026-09-23`
- No `git add .` was used.
- The only new project file from this review is
  `docs/project/evidence/d6-pairwise-channel-run002-independent-review.md`.

STOP FOR PAIRWISE CHANNEL RUN_002 INDEPENDENT REVIEW
