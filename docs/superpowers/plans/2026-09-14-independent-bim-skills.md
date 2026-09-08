# Independent BIM Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose independent discovery, generation, export, validation, import,
and verification skill boundaries while preserving the existing coordinator.

**Architecture:** Keep the current `ifc-bim-conversion-workflow` as an
optional router. Add the smallest independent skill for discovering existing
analysis substitutes, keep MassPatch generation as a separate producer, and
make IFC export consume an optional discovery report rather than generating
proxies. Existing logical-object mapping and validation/import scripts remain
usable.

**Tech Stack:** Markdown skill contracts, Python 3.12, Pixi, pytest, IFC4,
IfcOpenShell, jj.

**Spec:** `docs/superpowers/specs/2026-09-14-independent-bim-skills-design.md`

## Global Constraints

- Missing MassPatch means `not_found`; export must not silently generate one.
- Discovery, generation, export, validation, import, and verification are independently runnable.
- The coordinator must not duplicate domain calculations.
- Source models remain read-only during discovery, generation, inspection, and validation.
- Import is the only mutating phase and requires an explicit user choice.
- Existing logical furniture mapping remains the prerequisite for export when mapping is needed.
- Every modified project-owned function has an English-first docstring.
- Important discovery, proxy binding, IFC serialization, routing, and import-gate logic has concise English-first intent comments.
- Use Pixi and jj; do not add dependencies.

---

### Task 1: Add the independent substitute-discovery skill contract

**Files:**
- Create: `skills/analysis-substitute-discovery/SKILL.md`
- Create: `skills/analysis-substitute-discovery/references/substitute-contract.md`
- Create: `skills/analysis-substitute-discovery/tests/test_skill_contract.py`

**Interfaces:**
- Consumes: a source model or normalized object records containing candidate
  substitute objects and source identities.
- Produces: `SubstituteDiscoveryReport` with `substitutes`,
  `source_bindings`, `missing_sources`, `ambiguous_candidates`, `confidence`,
  and `provenance`.

- [x] **Step 1: Write failing contract tests**

```python
def test_discovery_skill_declares_read_only_missing_and_no_generation_rules():
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "already-authored",
        "does not create",
        "not_found",
        "read-only",
        "source_global_id",
        "masspatch",
    ):
        assert phrase in text
```

- [x] **Step 2: Run the focused test and confirm it fails**

Run:

```powershell
pixi run pytest skills/analysis-substitute-discovery/tests/test_skill_contract.py -q
```

Expected: FAIL because the new skill directory and contract do not exist.

- [x] **Step 3: Write the minimal skill contract**

Document only discovery responsibilities, candidate location rules, binding
fields, missing/ambiguous statuses, and the explicit prohibition on generation.
Keep layer, collection, object-property, and IFC proxy lookup as evidence
channels rather than hard-coding one application.

- [x] **Step 4: Add focused reference and contract tests**

Test that the reference defines `substitute_kind`, `analysis_role`,
`visibility_policy`, `source_global_id`, provenance, confidence, and that the
skill does not claim to export or import IFC.

- [x] **Step 5: Run the focused tests**

Run:

```powershell
pixi run pytest skills/analysis-substitute-discovery/tests/test_skill_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Checkpoint with jj**

```powershell
jj status
jj describe -m "docs: define independent substitute discovery skill"
```

Do not include unrelated working-copy changes in a separate cleanup.

### Task 2: Make the existing MassPatch producer independently discoverable

**Files:**
- Create: `skills/masspatch-generation/SKILL.md`
- Create: `skills/masspatch-generation/references/masspatch-generation-contract.md`
- Create: `skills/masspatch-generation/tests/test_skill_contract.py`
- Modify: `features/mass_patch_generation.py` only if the public contract is missing

**Interfaces:**
- Consumes: `MeshGeometry3D` and optional
  `MassPatchGenerationConfig`.
- Produces: `MassPatchGenerationResult` or its JSON-safe serialization.

- [x] **Step 1: Inspect the existing public generator**

Confirm the callable and result serialization in
`features/mass_patch_generation.py`; do not create a second generator.

- [x] **Step 2: Write failing skill-contract tests**

Require the skill to say that generation is explicit, source-read-only,
backend-neutral, and does not export IFC or discover user-authored proxies.

- [x] **Step 3: Write the skill contract**

Reference the existing backend and its tests. State that generated output is
an upstream artifact that consumers may choose to use, not an automatic
fallback hidden inside IFC export.

- [x] **Step 4: Run focused tests and the existing MassPatch suite**

```powershell
pixi run pytest skills/masspatch-generation/tests -q
pixi run pytest test/test_mass_patch_generation.py test/test_mass_patch_cuboid_cover.py test/test_open_mass_patch_generation.py -q
```

Expected: PASS without changing generator behavior.

- [ ] **Step 5: Checkpoint with jj**

```powershell
jj describe -m "docs: expose independent MassPatch generation skill"
```

### Task 3: Extract a reusable discovery report helper without generation

**Files:**
- Create: `features/analysis_substitute_discovery.py`
- Create: `test/test_analysis_substitute_discovery.py`
- Modify: `features/scene_contract.py` only if an existing neutral record type
  is required by the helper

**Interfaces:**

```python
def discover_analysis_substitutes(
    source_records: Sequence[Mapping[str, object]],
) -> SubstituteDiscoveryReport:
    ...
```

The report must be JSON-safe and preserve source IDs, candidate IDs,
`MassPatch` kind, analysis role, visibility policy, provenance, confidence,
missing sources, and ambiguous candidates.

- [x] **Step 1: Write failing tests**

Cover:

```python
def test_discovery_returns_existing_masspatch_without_generation():
    report = discover_analysis_substitutes(
        [
            {"id": "chair-1", "role": "furniture"},
            {
                "id": "patch-1",
                "role": "analysis_substitute",
                "substitute_kind": "MassPatch",
                "source_global_id": "chair-1",
            },
        ]
    )
    assert report["status"] == "passed"
    assert report["substitutes"][0]["substitute_id"] == "patch-1"


def test_discovery_reports_missing_source_without_generating():
    report = discover_analysis_substitutes(
        [{"id": "chair-1", "role": "furniture"}]
    )
    assert report["status"] == "not_found"
    assert report["missing_sources"] == ["chair-1"]
```

- [x] **Step 2: Run tests and confirm the helper is absent**

```powershell
pixi run pytest test/test_analysis_substitute_discovery.py -q
```

Expected: FAIL with an import or symbol error.

- [x] **Step 3: Implement the smallest read-only discovery helper**

Accept explicit source bindings first, then recognized role/property evidence.
Never call `generate_mass_patches`. Reject duplicate or contradictory bindings
as `ambiguous`, preserving all candidate IDs.

- [x] **Step 4: Run focused tests**

```powershell
pixi run pytest test/test_analysis_substitute_discovery.py -q
```

Expected: PASS.

- [ ] **Step 5: Checkpoint with jj**

```powershell
jj describe -m "feat: add read-only analysis substitute discovery"
```

### Task 4: Add optional MassPatch consumption to the IFC exporter

**Files:**
- Modify: `test/bim/export_rhino_source_ifc.py`
- Create: `test/test_ifc_masspatch_export.py`

**Interfaces:**

```python
def write_ifc(
    source_path: Path,
    target_path: Path,
    *,
    substitute_path: Path | None = None,
) -> dict[str, object]:
    ...
```

The existing two-argument call remains valid. When `substitute_path` is absent,
the exporter writes source products only. When present, it consumes already
serialized MassPatch records and writes separate optional
`IfcBuildingElementProxy` objects with `OM_AnalysisProxy` properties.

- [x] **Step 1: Write failing exporter tests**

Assert source-only export has zero proxy objects, supplied substitutes produce
one proxy per valid binding, source GlobalIds are preserved, and proxy
properties include `OM_SourceGlobalId`, `OM_ProxyKind`, `OM_AnalysisRole`,
`OM_Authoritative`, and `OM_VisibilityPolicy`.

- [x] **Step 2: Run focused tests and confirm the optional interface is absent**

```powershell
pixi run pytest test/test_ifc_masspatch_export.py -q
```

Expected: FAIL because `write_ifc` has no substitute input and no proxy
serialization.

- [x] **Step 3: Implement optional proxy serialization**

Reuse existing IFC root, context, mesh, property, unit, and stable-GUID
helpers. Keep each proxy as a separate `IfcBuildingElementProxy`; do not use
`IfcRelAggregates` or `IfcRelNests` to represent a physical furniture part.
Use an `IfcGroup` for proxy organization and metadata for source binding.

- [x] **Step 4: Validate both branches**

```powershell
pixi run pytest test/test_ifc_masspatch_export.py test/test_ifc_bonsai_adapter.py -q
```

Expected: PASS for source-only and source-plus-proxy exports.

- [ ] **Step 5: Checkpoint with jj**

```powershell
jj describe -m "feat: export optional MassPatch IFC proxies"
```

### Task 5: Extend IFC inspection and neutral loading for proxy facts

**Files:**
- Modify: `skills/ifc-bim-conversion-workflow/scripts/inspect_ifc.py`
- Modify: `adapters/ifc_bonsai.py`
- Modify: `test/fixtures/ifc4_description_fixture.py`
- Modify: `test/test_ifc_bonsai_adapter.py`
- Modify: `skills/ifc-bim-conversion-workflow/tests/test_inspect_ifc.py`

**Interfaces:**

```python
def inspect_ifc(path: Path) -> dict[str, object]:
    # adds analysis_proxy records/counts without changing existing keys
```

The neutral IFC adapter exposes discovered proxies as analysis substitutes,
without treating them as furniture products or requiring their display
visibility.

- [x] **Step 1: Add failing fixture assertions**

Create one valid `IfcBuildingElementProxy` with `OM_AnalysisProxy` and assert
inspection reports its proxy kind and source binding; assert neutral loading
keeps it out of the furniture product role and exposes its proxy geometry.

- [x] **Step 2: Run focused tests and confirm they fail**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_inspect_ifc.py test/test_ifc_bonsai_adapter.py -q
```

- [x] **Step 3: Implement read-only proxy extraction**

Read only the custom property set values and proxy geometry. Preserve explicit
uncertainty when the source binding or geometry is missing. Do not infer a
proxy merely from an object name.

- [x] **Step 4: Run the focused suite**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_inspect_ifc.py test/test_ifc_bonsai_adapter.py -q
```

Expected: PASS.

- [ ] **Step 5: Checkpoint with jj**

```powershell
jj describe -m "feat: inspect and load IFC analysis proxies"
```

### Task 6: Update the coordinator as a router, not a mandatory pipeline

**Files:**
- Modify: `skills/ifc-bim-conversion-workflow/SKILL.md`
- Modify: `docs/ifc_bim_conversion_workflow_usage.md`
- Modify: `skills/ifc-bim-conversion-workflow/tests/test_skill_contract.py`

**Interfaces:**
- Consumes: independent reports from mapping, discovery, generation, export,
  validation, import, and verification.
- Produces: routing guidance and phase statuses; no duplicate geometry or IFC
  calculations.

- [x] **Step 1: Add failing contract assertions**

Require explicit references to `analysis-substitute-discovery` and
`masspatch-generation`, and require wording that generation is optional,
discovery does not generate, and source-only export is valid.

- [x] **Step 2: Update coordinator documentation**

Add a capability-selection table:

```text
Need existing substitute? -> discovery
Need new substitute?      -> generation
Need IFC file?             -> export
Need legality check?       -> validation
Need Bonsai scene change?  -> import
Need post-import proof?    -> verification
```

Keep all phases independently runnable and preserve the existing import gate.

- [x] **Step 3: Run skill contract tests**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_skill_contract.py -q
```

Expected: PASS.

- [ ] **Step 4: Checkpoint with jj**

```powershell
jj describe -m "docs: route BIM workflow through independent skills"
```

### Task 7: End-to-end regression and acceptance evidence

**Files:**
- Modify only if a preceding test exposes a real contract defect.
- Create: `test/bim/acceptance_manifest.py` entry only if required for the
  existing acceptance harness.

**Interfaces:**
- Consumes: current Rhino source JSON and current manual MassPatch JSON under
  `outputs/`.
- Produces: source-only IFC, source-plus-MassPatch IFC, inspection report,
  validation report, and a compact binding summary.

 - [x] **Step 1: Run all focused suites**

```powershell
pixi run pytest skills/analysis-substitute-discovery/tests skills/masspatch-generation/tests -q
pixi run pytest test/test_analysis_substitute_discovery.py test/test_ifc_masspatch_export.py -q
pixi run pytest test/test_ifc_bonsai_adapter.py skills/ifc-bim-conversion-workflow/tests -q
```

Evidence: `119 passed, 13 skipped`.

 - [x] **Step 2: Run project compilation**

```powershell
pixi run python -m compileall -q features adapters test skills
```

Evidence: completed with exit code 0.

 - [x] **Step 3: Run full pytest**

```powershell
pixi run pytest -q
```

Evidence: `732 passed, 13 skipped in 385.50s`.

 - [x] **Step 4: Run the live-source read-only acceptance**

Use the existing Rhino extraction artifacts and current manual MassPatch
records. Do not mutate Rhino or Blender. Produce a distinct output directory
under `outputs/` and record source mutation status, proxy count, bindings,
inspection status, and validation status.

Evidence: source-only acceptance was run against
`test/output/live_rhino_ifc_source.json` and written to
`outputs/independent-bim-skills-2026-09-14/`. The generated IFC is IFC4,
inspection passed with no duplicate GlobalIds, and IfcOpenShell EXPRESS
validation passed with zero errors and zero warnings. The available
`current-chair-mass-patches-new.json` belongs to a different source identity,
so no proxy binding was fabricated; proxy export remains covered by the
dedicated tests.

 - [x] **Step 5: Perform final jj status review**

```powershell
jj status
jj diff --stat
```

Confirmed. The worktree contains pre-existing large generated artifacts that
JJ refuses to snapshot at its 1 MiB limit; they were not used as evidence for
the current source binding and were not force-added.

## Plan Self-Review

- Spec coverage: independent skill boundaries are covered by Tasks 1, 2, and 6.
- Discovery without generation is covered by Tasks 1 and 3.
- Optional IFC proxy consumption is covered by Task 4.
- IFC inspection and neutral loading are covered by Task 5.
- Import remains separate because no task adds an automatic importer.
- No perceptual weights or scoring logic are introduced.
- All tasks have concrete files, interfaces, tests, and runnable commands.
- No `TBD`, `TODO`, or vague implementation placeholders remain.
