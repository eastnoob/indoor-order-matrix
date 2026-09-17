# Full Rhino IFC Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export all usable Rhino/VisualARQ source geometry to IFC with authored IFC classes preserved and untyped objects represented as `IfcBuildingElementProxy`.

**Architecture:** Keep source capture, semantic normalization, IFC serialization, validation, and import independent. Extend the existing Rhino exporter with a product-class registry and proxy fallback; add a read-only Rhino mesh capture path for live models.

**Tech Stack:** Python 3.12, Pixi, IfcOpenShell, pytest, RhinoCommon through MCP `15002`.

**Spec:** `docs/superpowers/specs/2026-09-16-full-rhino-ifc-export-design.md`

## Global Constraints

- Use Pixi, not pip or venv.
- Rhino MCP `15002` is read-only during capture; do not delete, modify, export, or save the Rhino document.
- Every new or modified function has an English-first docstring.
- Important geometry conversion, semantic selection, IFC serialization, and adapter handoff blocks have English-first comments.
- No missing semantic label may be guessed from name, layer, or geometry.
- Untyped objects default to `IfcBuildingElementProxy` and `analysis_participation=unknown`.

---

### Task 1: Add red tests for typed classes and proxy fallback

**Files:**
- Modify: `test/test_rhino_source_ifc_type_families.py`
- Create: `test/test_rhino_source_ifc_full_export.py`

- [ ] **Step 1: Write failing tests**

Add source records containing one `IfcWall`, one `IfcFurnishingElement`, one unsupported label, and one untyped object. Assert the written IFC contains one occurrence per record, typed entities retain their classes, unknown/unsupported records become `IfcBuildingElementProxy`, and the export report includes entity counts and review counts.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `pixi run pytest test/test_rhino_source_ifc_full_export.py -q`

Expected: FAIL because the exporter currently creates every object as `IfcFurniture`.

- [ ] **Step 3: Commit the failing tests**

```powershell
git add test/test_rhino_source_ifc_full_export.py test/test_rhino_source_ifc_type_families.py
git commit -m "test: define full Rhino IFC export contract"
```

### Task 2: Implement product class selection and proxy fallback

**Files:**
- Modify: `test/bim/export_rhino_source_ifc.py`
- Modify: `test/test_rhino_source_ifc_full_export.py`

- [ ] **Step 1: Add the registry and selector**

Implement:

```python
SUPPORTED_PRODUCT_CLASSES: frozenset[str]

def _select_ifc_product_class(record: dict[str, Any]) -> tuple[str, str]:
    """Return the authored product class or the untyped proxy fallback."""
```

Use `source_semantics.ifc_entity` first, then legacy `ifc_entity`; accept only product classes in the registry. Return `(class_name, status)` where status is `authored`, `untyped`, or `review`.

- [ ] **Step 2: Replace hard-coded `IfcFurniture` creation**

Create the selected IFC class for each source record. Create `IfcFurnitureType` and type relations only for furniture/furnishing records where the existing type-family evidence is present. Keep all other products as occurrences without fake furniture types.

- [ ] **Step 3: Attach common source properties**

Add `OM_Source` properties for source id, layer, geometry kind, authored label, semantic status, analysis participation, source path, and provider. Keep the existing layout properties for backward compatibility.

- [ ] **Step 4: Add report distributions**

Return `entity_counts`, `untyped_count`, `review_count`, and `geometry_skipped_count` in the export report while retaining existing report keys.

- [ ] **Step 5: Run focused tests**

Run: `pixi run pytest test/test_rhino_source_ifc_full_export.py test/test_rhino_source_ifc_type_families.py -q`

Expected: PASS.

- [ ] **Step 6: Commit exporter behavior**

```powershell
git add test/bim/export_rhino_source_ifc.py test/test_rhino_source_ifc_full_export.py test/test_rhino_source_ifc_type_families.py
git commit -m "feat: export untyped Rhino objects as IFC proxies"
```

### Task 3: Update skills and workflow routing

**Files:**
- Modify: `skills/ifc-export/SKILL.md`
- Modify: `skills/ifc-bim-conversion-workflow/SKILL.md`
- Modify: `skills/visualarq-source-adapter/SKILL.md`
- Create: `test/test_full_ifc_export_skill_contract.py`

- [ ] **Step 1: Write failing skill contract tests**

Require the docs to state full export is the default, authored labels are preserved, unlabeled objects become `IfcBuildingElementProxy`, and untyped objects default to `analysis_participation=unknown`.

- [ ] **Step 2: Update the skill contracts**

Document the default command and explicit opt-out policy. Clarify that full export does not mean semantic guessing, and that validation/import remain separate.

- [ ] **Step 3: Run contract tests**

Run: `pixi run pytest test/test_full_ifc_export_skill_contract.py skills/visualarq-source-adapter/tests skills/ifc-bim-conversion-workflow/tests -q`

Expected: PASS.

- [ ] **Step 4: Commit skill updates**

```powershell
git add skills test/test_full_ifc_export_skill_contract.py
git commit -m "docs: define full IFC export workflow"
```

### Task 4: Reuse the existing live Rhino geometry capture

**Files:**
- Existing capture output: `outputs/full-rhino-ifc-2026-09-16/live-rhino-15002-export-source.json`
- Existing source adapter: `adapters/rhino_visualarq_source.py`
- Modify: `skills/visualarq-source-adapter/SKILL.md`

The read-only Rhino/VisualARQ capture chain already exists and produced the
source payload through MCP port `15002`. This change does not add a duplicate
capture script or mutate the Rhino document; it verifies that the existing
payload flows through the full exporter.

### Task 5: Run live export, inspection, and validation

**Files:**
- Generated: `outputs/full-rhino-ifc-2026-09-16/`

- [ ] **Step 1: Read MCP `15002` and capture source geometry**

Use read-only Rhino Python through `armadillo` / port `15002`. Preserve the source document, object ids, labels, layers, and geometry. Do not mutate or save Rhino.

- [ ] **Step 2: Normalize and export**

Run the source adapter, logical mapping where evidence is sufficient, and the exporter with default full-export mode. Use `IfcBuildingElementProxy` for untyped records.

- [ ] **Step 3: Inspect and validate independently**

Run `inspect_ifc.py` and `validate_ifc.py --express-rules`. Record whether validation is `passed`, `failed`, or `not_available`.

- [ ] **Step 4: Grill Me self-check**

Confirm every exported product has one source id, typed labels were not collapsed, untyped products are proxies, no object was silently duplicated, and Rhino was not modified.

- [ ] **Step 5: Run final tests and review**

```powershell
pixi run pytest test/test_rhino_source_ifc_full_export.py test/test_full_ifc_export_skill_contract.py skills/visualarq-source-adapter/tests skills/ifc-bim-conversion-workflow/tests -q
git diff --check
```
