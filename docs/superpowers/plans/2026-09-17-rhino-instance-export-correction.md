# Rhino Instance Export Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export the live Rhino/VisualARQ scene as correctly placed IFC products, preserving furniture semantics and attaching authored analysis substitutes to the same IFC product.

**Architecture:** A read-only Rhino MCP capture emits one top-level occurrence plus leaf geometry and transform evidence. A pure-Python normalization layer composes every nested transform, classifies display versus analysis branches, verifies world bounds, and applies explicit semantic mappings before the existing IFC writer serializes one product with two representations.

**Tech Stack:** Python 3.12 via Pixi, RhinoCommon through Rhino MCP, IfcOpenShell IFC4, pytest, JSON.

**Spec:** `docs/superpowers/specs/2026-09-17-rhino-instance-export-correction-design.md`

## Global Constraints

- Rhino capture is read-only and uses `http://localhost:15002/`.
- One top-level Rhino object is one product unless explicit product-boundary evidence says otherwise.
- World transforms are applied exactly once; mirrored transforms reverse face winding.
- Semantic classes require authored, provider, or explicit project-mapping evidence.
- `GEOMETRY`, `GEOMATRY`, and `BODYPROXY` are representation roles, not product boundaries.
- Every new or modified function has an English-first docstring; important transform, geometry, semantic, and adapter steps have English-first comments.
- Use Pixi; do not use pip or venv.
- Export, validation, and Bonsai import remain independent.

---

### Task 1: Transform-Aware Occurrence Normalizer

**Files:**
- Create: `adapters/rhino_instance_capture.py`
- Create: `test/test_rhino_instance_capture.py`

**Interfaces:**
- Consumes: `normalize_rhino_occurrences(raw_payload: dict, config: dict) -> dict`
- Produces: normalized `objects`, `substitutes`, transform/bounds reports, semantic evidence counts.

- [ ] **Step 1: Write failing tests for nested transforms and product boundaries**

  Test translation plus rotation, non-uniform scale, nested matrices, one top-level block producing one product, and source identity retention.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pixi run pytest test/test_rhino_instance_capture.py -q`

  Expected: collection/import failure because `adapters.rhino_instance_capture` does not exist.

- [ ] **Step 3: Implement matrix composition and world geometry merging**

  Implement homogeneous point transforms, face-index offsets, world bounds, tolerance-based Rhino bounds comparison, and explicit cycle/failure review records. Matrix chains are ordered outermost to innermost and documented in the source schema.

- [ ] **Step 4: Add mirrored-winding and role-classification tests**

  Add tests proving a negative linear determinant reverses polygon winding and that properties, exact layer aliases, then suffix aliases classify `display`, `analysis`, and `unclassified` branches in that order.

- [ ] **Step 5: Implement branch classification and configured semantic mapping**

  Resolve authored IFC entity first, provider mapping second, project family rules third, and fallback proxy last. Emit display geometry in `objects`; emit analysis geometry in explicit substitute records linked by source id.

- [ ] **Step 6: Run tests and verify GREEN**

  Run: `pixi run pytest test/test_rhino_instance_capture.py -q`

- [ ] **Step 7: Commit the independently tested normalizer**

  Commit: `feat: normalize nested Rhino occurrences`

### Task 2: Read-Only Rhino MCP Capture

**Files:**
- Create: `skills/visualarq-source-adapter/scripts/capture_rhino_instances.py`
- Create: `test/test_rhino_instance_capture_cli.py`
- Modify: `skills/visualarq-source-adapter/SKILL.md`

**Interfaces:**
- Consumes: MCP endpoint, output path, mapping JSON, Rhino document through injected `__rhino_doc__`.
- Produces: raw occurrence graph and normalized source/substitute JSON without changing Rhino.

- [ ] **Step 1: Write failing CLI contract tests**

  Test JSON-RPC request formation, extraction of top-level object identity, recursive definition paths, transform-chain serialization, source world bounds, user strings, and a clear failure on malformed MCP output.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pixi run pytest test/test_rhino_instance_capture_cli.py -q`

- [ ] **Step 3: Implement the read-only capture script**

  Traverse top-level document objects without exploding blocks. For instance references, recursively enumerate definition members and preserve every occurrence transform in an outer-to-inner chain. Tessellate Mesh, Brep, and Extrusion leaves, but do not transform them inside Rhino or mutate/save the document.

- [ ] **Step 4: Document the capture contract and safety boundary**

  Add the exact invocation, mapping configuration, representation aliases, review gates, and explicit statement that capture does not export IFC or import Bonsai.

- [ ] **Step 5: Run tests and verify GREEN**

  Run: `pixi run pytest test/test_rhino_instance_capture_cli.py skills/visualarq-source-adapter/tests -q`

- [ ] **Step 6: Commit the capture boundary**

  Commit: `feat: capture Rhino instance transforms`

### Task 3: Same-Product IFC Representations and Reporting

**Files:**
- Modify: `test/bim/export_rhino_source_ifc.py`
- Modify: `test/test_rhino_source_ifc_full_export.py`
- Create: `test/test_rhino_instance_ifc_export.py`
- Modify: `skills/ifc-export/SKILL.md`

**Interfaces:**
- Consumes: normalized source JSON plus substitute JSON from Tasks 1-2.
- Produces: one IFC product per source occurrence with visible Body and analysis-only Analysis representation.

- [ ] **Step 1: Write failing IFC tests**

  Assert that two furniture occurrences remain two `IfcFurniture` products at distinct placements, each BODYPROXY becomes an Analysis representation on its owning product, and no extra `IfcBuildingElementProxy` is created for representation mode.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `pixi run pytest test/test_rhino_instance_ifc_export.py -q`

- [ ] **Step 3: Correct representation serialization and acceptance reporting**

  Preserve world-to-local conversion exactly once, attach analysis meshes in the product local frame, keep visibility policy as factual metadata, and report `furniture_family_count`, exported occurrence count, display/analysis counts, transform mismatch count, and semantic evidence distribution.

- [ ] **Step 4: Add failure-gate tests**

  Assert that expected furniture downgraded to proxy, bounds mismatches, missing source bindings, or invalid geometry fail the acceptance result instead of producing a misleading passed report.

- [ ] **Step 5: Run focused and regression tests**

  Run: `pixi run pytest test/test_rhino_instance_ifc_export.py test/test_rhino_source_ifc_full_export.py test/test_rhino_source_ifc_type_families.py -q`

- [ ] **Step 6: Commit the IFC correction**

  Commit: `fix: preserve Rhino products in IFC export`

### Task 4: Live Rhino Acceptance and Independent IFC Validation

**Files:**
- Create: `outputs/rhino-instance-export-fix-2026-09-17/project-mapping.json`
- Create: generated raw/normalized/substitute/report/IFC artifacts under `outputs/rhino-instance-export-fix-2026-09-17/`
- Modify: `docs/superpowers/specs/2026-09-17-rhino-instance-export-correction-design.md` only if live evidence exposes a missing contract.

**Interfaces:**
- Consumes: live Rhino MCP model on port `15002`.
- Produces: validated IFC4 file and machine-readable acceptance evidence for Bonsai review.

- [ ] **Step 1: Capture the current live model without mutation**

  Record document object count and modified state before and after capture. Use explicit rules `CHAIR_* -> IfcFurniture` and `TABLE_* -> IfcFurniture`, provider rules for authored VisualARQ families, and the configured geometry/proxy aliases.

- [ ] **Step 2: Run the live geometry and semantic gate**

  Require all 56 chair and 37 table occurrences to map to furniture, every occurrence to have a distinct authored placement where Rhino does, zero furniture bounds mismatches, and BODYPROXY branches to bind to their owning occurrence.

- [ ] **Step 3: Export the corrected IFC**

  Run the IFC writer in `representation` mode and save the JSON export report beside the IFC.

- [ ] **Step 4: Inspect and validate independently**

  Run:

  `pixi run python skills/ifc-bim-conversion-workflow/scripts/inspect_ifc.py <ifc> --json`

  `pixi run python skills/ifc-bim-conversion-workflow/scripts/validate_ifc.py <ifc> --express-rules`

  Require no duplicate GlobalIds and no validator errors.

- [ ] **Step 5: Run the complete focused suite and static checks**

  Run all source-adapter, full-export, type-family, instance-capture, workflow-skill, and new acceptance tests; then run `python -m compileall`, `git diff --check`, and inspect the final diff.

- [ ] **Step 6: Prepare Bonsai visual handoff**

  Provide the absolute validated IFC path plus expected furniture counts and positions. Import remains a separate user-controlled action; do not overwrite the user's current Blender scene.

- [ ] **Step 7: Commit verified code and documentation only**

  Commit: `test: verify live Rhino IFC export`

## Self-Review

- Spec coverage: product boundaries, nested transforms, mirroring, representation roles, semantic evidence, failure handling, reporting, live counts, IFC validation, and Bonsai handoff each map to a task.
- Placeholder scan: no deferred implementation or unspecified error handling remains.
- Type consistency: Tasks 1-2 produce `objects` plus `substitutes`; Task 3 consumes exactly those records; Task 4 invokes the same public interfaces.
- Grill Me result: the plan tests the real failure at the source-capture boundary and avoids model-name hardcoding by making current naming rules explicit project configuration.
