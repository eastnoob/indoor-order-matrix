# Authored Rhino Furniture-Group Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serialize only explicitly tagged Rhino furniture-group Blocks as native IFC grouping relations.

**Architecture:** The source capture resolves effective User Text from Definition then Instance, expands only marked group containers, and supplies `furniture_groups` alongside normal product records. The IFC exporter creates `IfcGroup`/`IfcRelAssignsToGroup` only for those records and removes provenance-only source-model groups.

**Tech Stack:** Rhino MCP Python, Python 3.12, IfcOpenShell IFC4, pytest, Pixi.

**Spec:** `docs/superpowers/specs/2026-09-23-authored-rhino-furniture-group-export-design.md`

## Global Constraints

- Only effective `OM.Role=furniture_group` activates the feature.
- Definition User Text is inherited and instance User Text overrides it.
- No inference from names, layers, proximity, ordinary Rhino groups, or geometry.
- Preserve all existing unmarked Block, furniture type, and Body/Analysis behavior.
- Add English-first docstrings and intent comments to changed project code.

---

### Task 1: Add Explicit Group Serialization

**Files:**
- Modify: `test/bim/export_rhino_source_ifc.py`
- Modify: `test/test_rhino_source_ifc_full_export.py`

**Interfaces:**
- Consumes: `furniture_groups: list[dict[str, object]]` with `id` and `member_ids`.
- Produces: `IfcGroup(ObjectType="furniture_group")` plus `IfcRelAssignsToGroup`.

- [x] Write failing tests for a tagged group, repeated groups, empty/malformed memberships, and no synthetic source-model group.
- [x] Run `pixi run pytest test/test_rhino_source_ifc_full_export.py -k furniture_group -v` and confirm failure.
- [x] Implement strict member resolution against already-created furniture entities; report omitted membership and group counts.
- [x] Delete the source-model group accumulator/serialization loop without changing source provenance properties.
- [x] Run `pixi run pytest test/test_rhino_source_ifc_full_export.py -v`.

### Task 2: Capture Definition-Inherited Tagged Containers

**Files:**
- Modify: `test/bim/capture_rhino_mcp_source.py`
- Modify: `test/test_rhino_source_ifc_full_export.py`

**Interfaces:**
- Consumes: a root `InstanceReferenceGeometry` and effective Definition/Instance User Text.
- Produces: furniture object records and `furniture_groups` records.

- [x] Write metadata-level tests for deterministic furniture definition recognition and exact group-marker isolation; the live tagged Rhino run verifies nested member occurrence ids and non-furniture exclusion.
- [x] Implement effective User Text, tagged-root detection, direct child-instance transform composition, and deterministic member ids.
- [x] Ensure a tagged root has no flattened product record and all untagged roots retain current capture behavior.
- [x] Run focused capture/export tests with Pixi and live read-only untagged-capture regression.

### Task 3: Recover Group Role And Document Workflow

**Files:**
- Modify: `adapters/ifc_bonsai.py`
- Modify: `skills/visualarq-source-adapter/SKILL.md`
- Modify: `skills/ifc-export/SKILL.md`
- Modify: `skills/ifc-bim-conversion-workflow/SKILL.md`
- Modify: `test/test_full_ifc_export_skill_contract.py`

**Interfaces:**
- Consumes: `IfcGroup.ObjectType`.
- Produces: `AuthoredGroup.group_role` and documented authoring constraints.

- [x] Write failing adapter/skill contract tests.
- [x] Preserve `furniture_group` when `ObjectType` matches; retain `ifc_group` for all other IFC groups.
- [x] Document Definition default, Instance override, explicit-only behavior, and no effect on ordinary Blocks.
- [x] Run focused adapter, exporter, and skill tests.

### Task 4: Verify And Record Boundary

**Files:**
- Modify: `docs/indoor_layout_evaluation_matrix_architecture_memory.md`

- [x] Add the factual authored-group versus inferred activity-group boundary.
- [x] Run:

```powershell
pixi run pytest test/test_rhino_source_ifc_full_export.py test/test_full_ifc_export_skill_contract.py test/test_ifc_furniture_preflight.py test/test_furniture_frame.py -q
pixi run python -m compileall -q test/bim/capture_rhino_mcp_source.py test/bim/export_rhino_source_ifc.py adapters/ifc_bonsai.py
git diff --check
```

- [x] Tag the three confirmed outer Block Definitions, run live capture from the current Rhino MCP slot, and verify `37` explicit groups with `95` furniture members; write, inspect, and EXPRESS-validate the resulting IFC.
- [ ] Commit only the coherent implementation files; leave existing unrelated worktree changes untouched.
