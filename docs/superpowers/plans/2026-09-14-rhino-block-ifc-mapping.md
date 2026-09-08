# Incremental Rhino Block IFC Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing BIM skills so nested Rhino Blocks become one logical IFC product with explicit display, analysis, and manual-review evidence.

**Architecture:** Add one small Rhino-block adapter that flattens nested Block instances into the existing `bim-logical-object-mapping` input contract. Preserve the existing normalizer as the authority for logical products, type families, and occurrences; attach representation records and review gates around its output. Do not change MassPatch generation or IFC geometry algorithms.

**Tech Stack:** Python 3.12, stdlib JSON/dataclasses only, pytest, Pixi, jj.

**Spec:** `docs/superpowers/specs/2026-09-14-incremental-rhino-block-ifc-mapping-design.md`

## Global Constraints

- Automation proposes evidence; supervisor judgment resolves ambiguous product and representation roles.
- A root Block is one complete logical product only when explicit or coherent evidence supports completeness.
- Block names are labels/evidence, not authoritative IFC semantics.
- `OM_*` is the project namespace; never create `Pset_OM_*`.
- `MassPatch` remains an analysis substitute, not a second furniture occurrence.
- Every new or modified project-owned function gets an English-first docstring and comments for important inference/conversion steps.
- Existing unrelated working-copy changes must remain untouched.

---

### Task 1: Add the failing nested-Block adapter tests

**Files:**
- Create: `test/test_rhino_block_mapping.py`

**Interfaces:**
- The tests define the required public function:
  `normalize_rhino_blocks(payload: Mapping[str, Any]) -> dict[str, Any]`.

- [x] **Step 1: Write the failing tests**

```python
def test_example_chair_is_one_product_with_two_representations():
    report = normalize_rhino_blocks(EXAMPLE_CHAIR)
    assert report["status"] == "passed"
    assert len(report["logical_objects"]) == 1
    assert report["logical_objects"][0]["id"] == "chair_001"
    assert {item["representation_role"] for item in report["representations"]} == {
        "display_geometry", "analysis_substitute"
    }
    assert report["representations"][1]["substitute_kind"] == "MassPatch"


def test_repeated_roots_share_type_but_keep_occurrences():
    report = normalize_rhino_blocks({"instances": [EXAMPLE_CHAIR_INSTANCE_1,
                                                       EXAMPLE_CHAIR_INSTANCE_2]})
    assert len(report["type_families"]) == 1
    assert len(report["occurrences"]) == 2


def test_unlabelled_child_requires_supervisor_review():
    report = normalize_rhino_blocks(AMBIGUOUS_CHILD)
    assert report["status"] == "blocked"
    assert report["manual_review"][0]["reason"] == "unresolved_representation_role"
```

- [x] **Step 2: Run the focused tests and verify the expected missing-function failure**

Run: `pixi run pytest test/test_rhino_block_mapping.py -q`

Expected: FAIL because `features.rhino_block_mapping.normalize_rhino_blocks` does not exist.

---

### Task 2: Implement the minimal Rhino nested-Block adapter

**Files:**
- Create: `features/rhino_block_mapping.py`
- Modify: `features/__init__.py` only if the project already exports feature helpers there

**Interfaces:**
- `normalize_rhino_blocks(payload: Mapping[str, Any]) -> dict[str, Any]`
- `_flatten_block(instance, path) -> tuple[list[component], list[representation], list[review]]`

- [x] **Step 1: Add the adapter data rules**

The adapter reads `instances` or `objects`, recognizes `user_text`/`attributes`, and uses these keys when present:

```text
OM.Role
OM.TypeKey
OM.InstanceId
OM.RepresentationRole
OM.SubstituteKind
OM.VisibilityPolicy
OM.SourceInstanceId
```

- [x] **Step 2: Flatten only for the existing normalizer**

Convert each confirmed logical root into the existing `groups` + `components` payload and call `normalize_source()`. Do not reimplement type-family or occurrence matching.

- [x] **Step 3: Preserve representation evidence**

Return `representations` with root ID, nested Block path, role, substitute kind, visibility policy, source instance ID, and confidence. Keep display and analysis representations attached to the same logical root.

- [x] **Step 4: Add the manual-review gate**

Return `manual_review` records for incomplete roots, conflicting role declarations, multiple plausible roots, or unbound substitutes. Set report status to `blocked` whenever a review record blocks safe export.

- [x] **Step 5: Run the focused tests**

Run: `pixi run pytest test/test_rhino_block_mapping.py -q`

Expected: PASS.

---

### Task 3: Extend skill contracts without duplicating algorithms

**Files:**
- Modify: `skills/bim-logical-object-mapping/SKILL.md`
- Modify: `skills/analysis-substitute-discovery/SKILL.md`
- Modify: `skills/ifc-bim-conversion-workflow/SKILL.md`
- Modify: `skills/ifc-bim-conversion-workflow/tests/test_skill_contract.py`

- [x] **Step 1: Document the Rhino nested-Block input contract**

Require root product, role-bearing representation children, recursive traversal, stable block path, and explicit `OM_*` attributes.

- [x] **Step 2: Document the human/automation split**

Automation may collect and propose. Manual or supervisor confirmation is required for ambiguous roots, missing roles, conflicting names/properties, and unbound MassPatch records.

- [x] **Step 3: Document IFC handoff**

One root becomes one `IfcFurniture` occurrence; repeated compatible roots may share `IfcFurnitureType`; MassPatch is not a second furniture occurrence; custom factual fields use `OM_*` property sets.

- [x] **Step 4: Add contract assertions**

Assert that the skills mention nested Block paths, `OM.Role`, `OM.RepresentationRole`, `manual_review`, supervisor confirmation, and MassPatch not being a furniture occurrence.

- [x] **Step 5: Run contract tests**

Run: `pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_skill_contract.py -q`

Expected: PASS.

---

### Task 4: Verify the existing IFC exporter consumes the normalized boundary

**Files:**
- Modify: `test/test_ifc_masspatch_export.py` only if a focused regression is missing
- Inspect only: `test/bim/export_rhino_source_ifc.py`, `adapters/ifc_bonsai.py`

- [x] **Step 1: Add one regression for one logical furniture occurrence**

Use the normalized `exampleChair` report and assert that exported furniture occurrence count is one while representation evidence retains both display and MassPatch roles.

- [x] **Step 2: Run the regression**

Run: `pixi run pytest test/test_ifc_masspatch_export.py -q`

Expected: PASS without changing the MassPatch generator.

---

### Task 5: Full verification and audit

**Files:**
- No new production files.

- [x] **Step 1: Run focused tests**

Run: `pixi run pytest test/test_rhino_block_mapping.py test/test_analysis_substitute_discovery.py skills/ifc-bim-conversion-workflow/tests/test_skill_contract.py -q`

- [x] **Step 2: Run the related IFC/MassPatch tests**

Run: `pixi run pytest test/test_ifc_masspatch_export.py test/test_mass_patch_generation.py test/test_mass_patch_cuboid_cover.py -q`

- [x] **Step 3: Audit comments and scope**

Check every modified project-owned function for an English-first docstring and every non-obvious flattening, role-resolution, and exporter-handoff block for a why-comment.

- [x] **Step 4: Run the existing skill tests and record any unrelated failures**

Run: `pixi run pytest skills -q`

- [x] **Step 5: Use jj to inspect the final diff**

Run: `jj diff --stat` and `jj diff -- docs/superpowers/specs/2026-09-14-incremental-rhino-block-ifc-mapping-design.md features/rhino_block_mapping.py skills/bim-logical-object-mapping/SKILL.md skills/analysis-substitute-discovery/SKILL.md skills/ifc-bim-conversion-workflow/SKILL.md`

Do not describe or commit unrelated existing working-copy changes.
