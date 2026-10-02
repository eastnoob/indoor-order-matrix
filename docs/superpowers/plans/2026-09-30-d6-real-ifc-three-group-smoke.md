# D6 Real IFC Three-Group Smoke Check Execution Plan

> **For agentic workers:** use `superpowers:executing-plans` task-by-task. This is a design-validation probe, not a production implementation plan. No subagent or additional session dispatch is required. Execute only after the user dispatches this plan or its handoff prompt.

**Goal:** Verify three real authored furniture groups from IFC through source-linked geometry, the existing standalone descriptor, and visible Blender output.

**Architecture:** Read the factual IFC without mutation; reuse reviewed extraction/projection/preview helpers in a design-only sample harness. Feed a typed NeutralSceneV2 sample directly to `describe_group_relations`; keep source Body meshes, terminal Analysis geometry, descriptor output and display annotations separate. Do not run candidate recipes or automatic-space experiments.

**Tech Stack:** Existing Pixi environment, IfcOpenShell, Shapely, Python standard library; only `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` for Blender.

**Spec / decision sources:**
- `docs/project/evidence/d6-h2-contract-repair-controller-review.md`, current effective A APPROVE for `9a38ea89336c521ff6e076982e986ec27f4f9a53`.
- `docs/project/d6-overall-self-description-design-table.md`, foundational observations only; later user clarification requires automatic space, not user-authored corridors.
- `docs/superpowers/plans/2026-09-29-d6-contract-repair-ifc-shadow-validation.md`, section 8 narrowing the next real-model task to three groups.
- `docs/project/evidence/d6-live-blender-input-inspection-2026-09-29.md`, historical input inspection, not this task's execution evidence.

**Date:** 2026-09-30, project-local planning date.
**Current state:** Plan drafted; task not executed and dispatch not yet authorized. A is approved as a diagnostic baseline, not a production selector.

## 1. Scope and Provenance

User requirements: furniture groups are minimum nodes; other objects are context; show actual IFC/Blender results; design and implementation remain separate. Space must ultimately be automatically derived; this task does not remove or freeze that requirement.

Verified by reading current code:
- `adapters/ifc_bonsai.py::load_ifc_neutral_scene(source, *, ifc_module=None, analysis_domain_source_id=None)` has no selective-group argument. Its native path tessellates all IfcProduct records.
- `_native_group_records(source)` assigns the exact furniture-group role; it omits groups with no members, so inventory must record those separately.
- `_native_mesh_record(entity, source_id, units, ifc_module, representation=None)` requests world coordinates and records metre geometry with `transform_applied=True`.
- `_scene_from_records(units, source_objects, geometries, *, authored_groups=(), analysis_units=None, ...)` can assemble existing typed records without full-scene tessellation. It is private, not a selective public adapter API.
- `features/group_self_description.py::describe_group_relations(scene)` accepts NeutralSceneV2. Group aggregation and candidate views remain deferred; 3D/Z/barrier/space measurements are unavailable in this slice.
- `adapters/blender_preview.py::build_preview_manifest(scene, matrix)` and `write_preview_script(scene, matrix, target)` preserve referenced source meshes. Their legacy furniture-group overlay keys do not directly consume the new `group_geometry/group_frame/group_axis` records.

Interpretation: a selective design harness is the smallest useful input smoke check. It tests the sampled extraction/descriptor chain, not the unmodified public loader end to end, full-scene completeness, Bonsai UI integration, or inferred-group accuracy. No new academic evidence is required to check this transport chain.

## 2. Global Constraints

- Do not modify `features/`, `adapters/`, `test/`, NeutralSceneV2, public APIs, dependencies, source IFC, or the currently open Blender/Bonsai model.
- Only exact `IfcGroup.ObjectType == "furniture_group"` qualifies. Ordinary groups, names, layers, proximity and legacy regions never create nodes. `OM.Role` is upstream provenance, not an alternate runtime eligibility rule.
- Members remain observations. Preserve direct authored membership, shared refs, duplicates and unresolved refs in the audit; do not invent nested membership or silently repair invalid declarations.
- Affordance is external input. Do not generate it from furniture type. Doors are not opening relations.
- No candidate recipes, selector, threshold tuning, Bayesian/ML, automatic domain/free-space/role computation, or full-scene tessellation. No fabricated capability values.
- An absent Analysis representation or failed Analysis extraction stays missing/invalid. Body may be displayed for audit, but cannot silently supply analytic geometry.
- Use Pixi; do not install dependencies or mix compiled Pixi modules into Blender Python. Exchange serialized files between runtimes.
- New functions have English-first docstrings; explain selection, representation, unit, projection and source/display transformations.
- Existing dirty/untracked work must remain intact. This plan supersedes only the initial broad B dispatch, not its future scope or historical records.

## 3. Files, Interfaces and Sampling

Read first: `AGENTS.md`, architecture memory, the current controller verdict, the old plan section 8, the inspection record, and the code/helpers named above.

Only these new tracked deliverables are authorized on execution:
- `scripts/design/group_level/run_ifc_three_group_smoke.py`: inventory, selective sample, numeric checks, JSON/provenance, self-check and verification.
- `scripts/design/group_level/render_ifc_three_group_smoke.py`: consume saved data, reuse source preview, add explicit output-only overlays, render and save a disposable blend.
- `docs/project/evidence/d6-ifc-three-group-smoke-report.md`: observations, exclusions, checks, images, limits and recommended next gate.
- `docs/project/evidence/d6-ifc-three-group-smoke-artifact-manifest.json`: source/input/script/output hashes, bytes, commands, software versions and scope.

Existing inputs are read-only. Large/local artifacts go to `outputs/design/ifc_three_group_smoke/`: `inventory.json`, `sample_scene.json`, `description.json`, `audit.json`, preview data/script, logs, `source_sample.png`, `analysis_sample.png`, and `three_group_smoke.blend`. Do not edit `.gitignore` just to hide them; explicit staging suffices. A manifest is provenance, not long-term binary backup.

Source IFC: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`.

Selection policy, fixed before tessellation:
1. Inventory every IfcGroup and direct relationship/member identity, with exact role eligibility and representation metadata. Do not tessellate to rank the sample.
2. Select the first three nonempty exact-role groups sorted by stable source identity (`GlobalId`, else the existing STEP source-id fallback). Record selection policy and IDs in `inventory.json` before processing geometry.
3. Keep every declared member of the selected groups; extract a shared source mesh once without altering membership. Do not replace failed sample groups with nicer examples. Fewer than three eligible nonempty groups is a reported scope limitation.
4. No context tessellation in this first probe. Record context inventory and omitted counts, including walls/doors. The figures are a three-group sample, not the full room; no room/occupancy/barrier inference follows from this omission.

Planned commands below are NEW design-script interfaces, not claims that these scripts already exist:

```powershell
pixi run python scripts/design/group_level/run_ifc_three_group_smoke.py self-check
pixi run python scripts/design/group_level/run_ifc_three_group_smoke.py inventory --ifc outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/ifc_three_group_smoke
pixi run python scripts/design/group_level/run_ifc_three_group_smoke.py probe --ifc outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/ifc_three_group_smoke
& 'D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe' --background --factory-startup --python scripts/design/group_level/render_ifc_three_group_smoke.py -- --input-dir outputs/design/ifc_three_group_smoke --output-dir outputs/design/ifc_three_group_smoke
pixi run python scripts/design/group_level/run_ifc_three_group_smoke.py verify --ifc outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/ifc_three_group_smoke
```

`inventory` freezes selection; `probe` refuses stale source hashes or changed selection instead of quietly rewriting it. `self-check` is small and IFC-free. `verify` validates saved artifacts without rerunning extraction. Unexpected numerical/source/hash mismatch returns nonzero; unsupported real data yields explicit limitation records, never fabricated success.

## 4. Task 1: Freeze Sample and Verify Input Transport

**Files:** runner, inventory/sample/audit artifacts; report updated incrementally.
**Consumes:** source IFC, reviewed extraction helpers and typed record constructors.
**Produces:** source-linked sample_scene.json, Body audit geometry, extraction status, transform audit; no new production interface.

- [ ] Record HEAD/status, relevant code hashes, source IFC SHA-256/bytes, available memory and installed Pixi dependency versions. Confirm the designated Blender executable exists without launching the live model.
- [ ] Implement an IFC-free self-check for exact-role exclusion, shared identity, unresolved refs and the coordinate guard. Run negative cases so applying placement or mm-to-m conversion twice is detected, then retain a passing check.
- [ ] Run inventory; recheck schema, units, groups/members and opening/void/fill/domain metadata. Historical 37 groups/95 furniture counts are comparisons, not hardcoded acceptance constants. Do not infer domain availability solely from IfcSpace count.
- [ ] Reuse private adapter helpers for the selected products only. Assemble SourceObject/MeshGeometry3D/AuthoredGroup records and a NeutralSceneV2 sample via existing constructors/helpers. Never monkeypatch the backend, save a trimmed IFC, or invoke the full loader while claiming selective extraction.
- [ ] Preserve the adapter's source-ID convention, factual type/property/level fields and uncertainty records. Computational member `geometry_refs` point only to the selected terminal Analysis mesh. Keep Body meshes in a separate audit view; do not create duplicate furniture nodes. Explicitly guard an absent representation before calling `_native_mesh_record`: passing `None` selects its default tessellation path, not an absent Analysis representation.
- [ ] Mark the sample context/provenance as `design-selective-smoke/v1` (preserve original helper/adapter version separately). Record omitted context and selected membership scope. This is not full native-adapter acceptance.
- [ ] Extract terminal Analysis explicitly for computation and Body separately for source inspection. Save representation STEP ids, geometry ids, original units, SI conversion, vertex/face counts, placement provenance, coordinate space and transform-applied state. Retain failures and unsupported geometry.
- [ ] For at least one declared member per selected group, independently compare local Analysis geometry transformed once to world space with world-coordinate extraction. Verify the installed IfcOpenShell local-shape/placement API before using it; record the actual settings and method. Compare geometric support/bounds, not assumed vertex index equality. A second call through the identical helper is repeatability, not independent transform validation.
- [ ] If local extraction cannot be obtained, record which placement/unit check is unverified; keep source visuals but do not approve the transport chain. Never invent raw IFC coordinates or silently accept identity-placement uncertainty.

Numerical comparison settings for this sample (not grouping thresholds): coordinates/gap `atol=1e-6 m`, `rtol=1e-9`; area `atol=1e-8 m^2`, `rtol=1e-8`; covariance `atol=1e-8 m^2`, `rtol=1e-8`; angles `atol=1e-6 degrees` modulo 90/180 as appropriate. Record actual residuals and native tessellation settings. A failed comparison is investigated, not fixed by silently increasing tolerance; justified revised settings require a separate documented sensitivity run.

## 5. Task 2: Check Existing Descriptor on the Sample

**Files:** runner, sample_scene/description/audit JSON; report.
**Consumes:** unchanged typed sample with actual Analysis meshes.
**Produces:** direct `describe_group_relations(sample_scene)` output and separate checks, not synthetic fixture reconstructions.

- [ ] Feed NeutralSceneV2 directly; no legacy dict or synthetic `_scene` reconstruction. Set analysis units explicitly to metres and use world XY plane, origin zero, identity basis for this audit. Do not infer a domain from bounds or sample hull.
- [ ] Keep mesh coordinates already in SI world space; world_transform is provenance when transform_applied is true. A display-only offset must be recorded and must not alter descriptor values.
- [ ] Verify eligibility and every member/source/geometry reference against frozen inventory. Preserve excluded-member reasons, holes, multipart, shared dependencies and invalid placements. Do not use geometry repairs to pass the check.
- [ ] Independently check member polygon area/centroid using installed Shapely on the same saved projected components; keep invalid/holes exclusions. Verify additive support, area-weighted group center and within + between = total covariance. These checks assess calculation consistency, not real grouping truth.
- [ ] Compare repeat-run numeric output and semantic sets on the same saved sample; report tolerance-based reproducibility separately from binary render hashes. Do not rerun the large extraction just to repeat descriptor calculation.
- [ ] Check exact current fields: `candidate_view_status == "deferred"`, `candidate_views is None`, relation aggregation deferred, group-level gap/contact/overlap null, formal_membership_edge null. Do not substitute the design probe's false value for the descriptor's null.

Minimum runnable contract checks belong in the runner, against actual output (the surrounding function needs its English docstring):

```python
result = describe_group_relations(sample_scene)
assert result["candidate_view_status"] == "deferred"
assert result["candidate_views"] is None
expected_ids = {group.id for group in sample_scene.authored_groups
                if group.group_role == "furniture_group"}
assert {row["target_id"] for row in result["group_geometry"]} == expected_ids
for relation in result["group_relations"]:
    assert relation["aggregation_status"] == "deferred"
    for key in ("raw_boundary_gap", "normalized_boundary_gap", "contact",
                "overlap", "overlap_area", "formal_membership_edge"):
        assert relation[key] is None
assert result["space_observations"]["domain_status"] == "not_available"
```
- [ ] Preserve all member-pair gap/contact/overlap records and source witnesses. Compare usable raw gap/area observations independently; normalization is dimensionless. Do not turn the minimum witness into a formal group relation.
- [ ] Preserve current unavailable 3D/Z/barrier/space capability states. Actual 3D source meshes are not proof that the planar descriptor computed these channels. Unsupported sample geometry is reported, not a reason to change production code here.

If no selected group has usable Analysis support, stop numerical description approval, still produce an honest source/failure visualization if Body is usable, and return the failed inputs for review. Partial sample success must name its exact coverage.

## 6. Task 3: Visible Blender Evidence and Handoff

**Files:** renderer, generated preview/artifacts, report, manifest.
**Consumes:** saved Body/Analysis/source-map/description JSON only; Blender never redefines numerical evidence.
**Produces:** two inspected PNGs, disposable blend, render/source-map audit and review handoff.

- [ ] Reuse existing preview source-mesh generation where applicable. Keep a separate Body preview record/view; do not overwrite Analysis refs in the computational scene. Do not force new frame fields into old trend/region keys with invented strengths or rectangles.
- [ ] Add only output-only tagged overlays from actual saved projected components, valid centers and reported group_frame/group_axis. Undefined or invalid directions must not be drawn as confident arrows. Coherence is not probability; glyph lengths are display lengths, not inferred extents or confidence.
- [ ] When an existing direction record has a numeric angle but zero/negligible resultant, retain the original value/status in JSON and show the coherence beside it; suppress a decisive direction glyph with an explicit display-only numerical-degeneracy annotation. Do not silently change descriptor status or impose a semantic grouping threshold.
- [ ] Render `source_sample.png` (Body source sample with three group/member identity labels) and `analysis_sample.png` (terminal Analysis geometry/footprints, centers, separate 4theta frame and 2theta axis, compact actual-status legend). Use the same spatial orientation and consistent metre scale; no full-room caption or inferred-group shading.
- [ ] If showing gap endpoints, compute/display nearest boundary points only as a separately identified display diagnostic; current descriptor witness stores member/source refs, not endpoint coordinates. Never draw center-to-center lines labeled boundary gap.
- [ ] Use a separate factory-startup/background process. Save `three_group_smoke.blend`; do not attach to, modify or save the user's current Blender scene. Give editable collections for source/Analysis/overlays and source IDs on generated objects.
- [ ] Audit loaded object/mesh/reference counts and vertex/face payload correspondence; record any missing source mesh. Check PNG dimensions, nonuniform pixels, camera framing and label clipping, then actually inspect both PNGs. Exit 0 alone is not visual verification.
- [ ] Write report separating user requirements, verified facts, observations, interpretations and unverified questions. Provide an output capability checklist rather than implementing the final UI checklist. State exactly what this sample does and does not validate.
- [ ] Write manifest with IFC before/after hash, all consumed script/helper hashes, selected IDs, data files, PNG/blend bytes/hashes, versions, commands/exit codes, tolerances, omitted scope and local-only retention. Source SHA must match. Keep JSON strict (`allow_nan=False`) and missing values categorical/null.
- [ ] Run `self-check`, saved-artifact `verify`, focused regression tests and diff/scope checks. Do not regenerate or modify H2 evidence. Record actual results rather than copying old 52-pass counts.

```powershell
pixi run pytest test/test_group_self_description.py test/test_canonical_layout_contract.py test/test_canonical_layout_geometry.py -q
git diff --check
git diff --cached --check
git diff --cached --name-only
```

- [ ] Stage only the four authorized new deliverable paths; inspect staged scope and commit with `design: validate three real IFC furniture groups`. Never blanket-stage existing untracked work. No push. Return commit/HEAD, uncommitted files, commands/results and absolute artifact paths; embed both images for the user.

**Final stop:** `STOP FOR THREE-GROUP IFC INPUT REVIEW`.
The executor proposes APPROVE / REVISE / DEFER of sampled input readiness; the controller reviews. No automatic continuation into full B, automatic space, production integration, selector design or code.

## 7. Resource and Replanning Rule

Run inventory once and tessellate only selected members, reusing shared meshes. Reading the whole IFC is distinct from tessellating all products. Log parse and per-member timings/memory; flush progress between members. If any stage has 15 minutes with no progress, memory exhaustion, missing runtime/API, or needs a forbidden edit, preserve logs and stop with the smallest actionable blocker. One retry is allowed only for a diagnosed transient failure, not repeated full extraction.

No time promise based on synthetic scores. Expected work is one finite execution chat, followed by controller review. Real limits may justify a smaller failed-input handoff; they do not justify replacing the sample or adding dependencies.

After review, choose the next gate from actual findings: adapter contract repair if transport fails; broader real-source coverage if it passes; then a separately designed automatic-domain/free-space comparison. Final space-role and inferred-membership/Bayesian/ML design remains scheduled work, not a claim already implemented by this smoke check.

## 8. Skill Use and Planning Self-Check

Actually read and applied during planning:
- `superpowers:brainstorming`: classify as a finite feasibility/transport probe, not a new subsystem; preserve dispatch approval before execution.
- `superpowers:writing-plans`: explicit files, inputs/outputs, task-local checks, handoff and one final review gate. No production code or extra scaffold generated during planning.
- `scientific-visualization` plus its integrity reference: source/transformation/display separation, orthogonal views, missing-direction display, source IDs and actual image inspection.
- `uncertainty-and-units`: explicit source/SI/world/plane unit chain and squared units; no metrology uncertainty fabricated and no new unit libraries installed.
- `superpowers:verification-before-completion`: verify document scope and references before reporting plan completion; execution success remains unclaimed.

Inspected, not formally executed: `speckit-assess-decide` and existing `.specify/assessments/bim-furniture-layout/decision.md`. The 2026-09-27 go allowed clean-room specification, not this task's execution or production delivery. No overwrite/new assessment is needed for this local validation plan; formal Spec Kit gate is reconsidered when choosing the next model/production scope.

- [x] A approval and its commit are preserved; historical REVISE is not reopened.
- [x] Sample extraction is not mislabeled as public adapter acceptance.
- [x] Analysis/Body, units/placement, context omission and null/deferred fields have explicit checks.
- [x] Real source meshes and inspected Blender output are deliverables, not optional future work.
- [x] Automatic space remains a future design objective, not fabricated input or current output.
- [x] Minimal files, explicit Git scope and one final stop; existing work is not edited.
- [x] Missing Analysis cannot accidentally invoke default tessellation; native source identity and uncertainties remain traceable.
- [ ] User dispatch of the smoke-check task.
- [ ] Execution and independent source/image review.
