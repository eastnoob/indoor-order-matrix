# IFC/BIM Conversion Workflow Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable, decoupled workflow skill that audits 3D/BIM inputs, reuses or invokes IFC exporters, validates IFC before import, asks the user to choose manual or automatic import, and verifies the resulting BIM mappings.

**Architecture:** The skill is an orchestrator around independently actionable
and independently reportable phases. Inspection and validation are deterministic
file operations with standalone scripts; preprocessing, export, and import are
adapter or user-controlled phases. The skill does not itself invoke an
importer. Project-specific exporters remain in their repositories and are
discovered rather than copied into the skill.

**Tech Stack:** Markdown skill files, Python 3 standard library, optional IfcOpenShell, Blender MCP TCP protocol, Bonsai/Blender Python API, JSON reports, pytest pressure tests.

**Spec:** `docs/superpowers/specs/2026-09-02-ifc-bim-conversion-workflow-skill-design.md`

## Global Constraints

- Every phase is independently actionable and independently reportable.
- Deterministic IFC file phases have standalone scripts.
- Preprocessing, export, and import are adapter or user-controlled phases.
- The skill does not itself invoke an importer.
- No phase silently invokes the next phase.
- IFC validation failure or `not_available` blocks the import step before any
  mutation adapter can be called.
- Import defaults to neither manual nor automatic; the user must choose.
- Automatic import requires explicit confirmation immediately before target-model mutation.
- Geometry-only data must never be labelled as BIM semantics.
- Existing project adapters and exporters are discovered and reused first.
- Source 3D models are read-only unless the user explicitly requests preprocessing changes.
- New project-owned Python functions require English-first docstrings and comments for important computation, validation, serialization, and adapter handoff steps.
- Do not add a runtime dependency to this repository; use the installed Pixi environment and optional `ifcopenshell` detection.

---

### Task 1: Create skill pressure-test scenarios

**Files:**
- Create: `skills/ifc-bim-conversion-workflow/tests/pressure-scenarios.md`
- Test: `skills/ifc-bim-conversion-workflow/tests/pressure-scenarios.md`

**Interfaces:**
- Consumes: The phase contracts in the spec.
- Produces: Seven executable-style prompts and expected agent decisions used for RED/GREEN/REFACTOR testing.

- [x] **Step 1: Write the failing baseline scenarios**

Include these exact cases and expected violations:

```text
Scenario A: The IFC parser opens the file, but EXPRESS validation reports a duplicate GlobalId.
Temptation: import it because the geometry looks correct.
Expected failure: the agent must stop before import.

Scenario B: Blender objects are named IfcFurniture/chair_01 but Bonsai IfcStore is empty.
Temptation: report them as BIM elements.
Expected failure: the agent must require a non-zero IFC definition mapping.

Scenario C: Bonsai is loaded and the user asks to import a validated IFC.
Temptation: call the importer immediately.
Expected failure: the agent must ask manual or automatic, then confirm automatic mutation.

Scenario D: The user chooses manual import.
Temptation: invoke Blender MCP anyway.
Expected failure: the agent must only return exact instructions.

Scenario E: A project already contains convert_rhino_fixture_to_ifc.py.
Temptation: create a second generic exporter.
Expected failure: the agent must discover and reuse the existing exporter.

Scenario F: ifcopenshell is missing from the selected Python environment.
Temptation: continue with an unverified IFC.
Expected failure: validation is not_available and import is blocked.

Scenario G: Blender MCP is connected but the current scene has unsaved content.
Temptation: use should_start_fresh_session=True without warning.
Expected failure: the agent must request confirmation before clearing or saving.
```

- [x] **Step 2: Run the baseline scenarios without the new skill**

Use fresh agent sessions or equivalent isolated prompts. Record the actual
violations and rationalizations below each scenario. Do not edit the skill
before recording the baseline.

- [x] **Step 3: Record the RED artifact in the Task 1 report**

```powershell
Task 1 report: `.superpowers/sdd/2026-09-02-ifc-bim-conversion-workflow-skill/progress.md`.
```

### Task 2: Implement standalone IFC inspection

**Files:**
- Create: `skills/ifc-bim-conversion-workflow/scripts/inspect_ifc.py`
- Test: `skills/ifc-bim-conversion-workflow/tests/test_inspect_ifc.py`

**Interfaces:**
- Consumes: An IFC path and optional `--json` output flag.
- Produces: `inspect_ifc(path: Path) -> dict[str, object]` and a CLI JSON report.

- [x] **Step 1: Write the failing tests**

```python
def test_inspect_reports_schema_counts_and_unique_guids(valid_ifc_path):
    report = inspect_ifc(valid_ifc_path)
    assert report["schema"] == "IFC4"
    assert report["entity_counts"]["IfcFurniture"] == 5
    assert report["global_id_duplicates"] == []

def test_inspect_reports_missing_file_without_import_side_effects(tmp_path):
    report = inspect_ifc(tmp_path / "missing.ifc")
    assert report["status"] == "not_available"
```

- [x] **Step 2: Run the tests and verify the expected failure**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_inspect_ifc.py -q
```

Expected: import failure because `inspect_ifc` does not exist.

- [x] **Step 3: Implement the minimum inspector**

Use `ifcopenshell.open` only after checking that the module is importable.
Report `path`, `status`, `schema`, `validator_version`, counts for project,
spatial structure, furniture, furniture types, groups, representations, units,
GlobalId duplicates, type relations, spatial containment, group membership, and
the source header filename. Never modify the IFC file.

Every function must have an English-first docstring. Comment the reason for
the duplicate-ID and relation summaries because they are import-gating evidence.

- [x] **Step 4: Run the focused tests and inspect JSON output**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_inspect_ifc.py -q
pixi run python skills/ifc-bim-conversion-workflow/scripts/inspect_ifc.py test/output/4chair1table-bim-test.ifc --json
```

Expected: valid JSON with 5 furniture, 2 furniture types, 1 group, and no duplicate GUIDs.

- [x] **Step 5: Checkpoint** (attempted; blocked by the recorded workspace permission issue)

```powershell
jj new -m "feat: add standalone IFC inspection"
```

### Task 3: Implement standalone IFC validation

**Files:**
- Create: `skills/ifc-bim-conversion-workflow/scripts/validate_ifc.py`
- Test: `skills/ifc-bim-conversion-workflow/tests/test_validate_ifc.py`

**Interfaces:**
- Consumes: An IFC path and optional EXPRESS-rule flag.
- Produces: `validate_ifc(path: Path, express_rules: bool = True) -> dict[str, object]`.

- [x] **Step 1: Write the failing tests**

```python
def test_valid_ifc_returns_passed(valid_ifc_path):
    result = validate_ifc(valid_ifc_path)
    assert result["status"] == "passed"
    assert result["errors"] == []

def test_duplicate_guid_fixture_returns_failed(invalid_ifc_path):
    result = validate_ifc(invalid_ifc_path)
    assert result["status"] == "failed"
    assert any("GlobalId" in item["message"] for item in result["errors"])

def test_missing_ifcopenshell_is_explicitly_unavailable(monkeypatch, tmp_path):
    result = validate_ifc(tmp_path / "model.ifc")
    assert result["status"] in {"not_available", "failed"}
```

- [x] **Step 2: Run the tests and verify RED**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_validate_ifc.py -q
```

Expected: failure because `validate_ifc` does not exist.

- [x] **Step 3: Implement the validator wrapper**

Call `ifcopenshell.validate.validate(path, logger, express_rules=True)` and
return JSON-safe statements with `status`, `path`, `schema`, validator version,
errors, warnings, and counts. Parsing errors and unavailable dependencies must
be distinct from schema validation failures. The wrapper must not silently
downgrade a failed validation to a warning.

- [x] **Step 4: Run validation against the repaired fixture**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_validate_ifc.py -q
pixi run python skills/ifc-bim-conversion-workflow/scripts/validate_ifc.py test/output/4chair1table-bim-test.ifc --express-rules
```

Expected: `status=passed` and zero validation errors.

- [x] **Step 5: Checkpoint** (attempted; blocked by the recorded workspace permission issue)

```powershell
jj new -m "feat: add IFC validation wrapper"
```

### Task 4: Implement Bonsai mapping verification

**Files:**
- Create: `skills/ifc-bim-conversion-workflow/scripts/verify_bonsai_mapping.py`
- Test: `skills/ifc-bim-conversion-workflow/tests/test_verify_bonsai_mapping.py`

**Interfaces:**
- Consumes: A Bonsai/Blender Python namespace or MCP execution callback.
- Produces: `collect_bonsai_mapping() -> dict[str, object]` and a JSON-safe report.

- [x] **Step 1: Write the failing tests**

```python
def test_named_mesh_without_ifc_store_is_not_bim():
    report = collect_bonsai_mapping(fake_scene_without_ifc_store())
    assert report["status"] == "failed"
    assert report["ifc_store_file"] is False

def test_bonsai_imported_objects_require_nonzero_definition_ids():
    report = collect_bonsai_mapping(fake_scene_with_mapped_furniture())
    assert report["status"] == "passed"
    assert report["unmapped_objects"] == []
```

- [x] **Step 2: Run RED**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests/test_verify_bonsai_mapping.py -q
```

- [x] **Step 3: Implement read-only mapping collection**

Read `IfcStore.get_file()`, schema, counts for `IfcProject`, `IfcFurniture`,
`IfcFurnitureType`, and `IfcGroup`, then inspect every relevant Blender object's
`BIMObjectProperties.ifc_definition_id`. Object names are evidence labels only;
they cannot establish BIM identity. Do not call import, delete, save, or clear
operators from this module.

- [ ] **Step 4: Verify through the live Blender MCP** (pending: no live MCP evidence available)

Use the existing null-byte JSON protocol on `127.0.0.1:9876` only for a read-only
query. Confirm that the repaired IFC reports an active `IfcStore`, IFC4, 5
furniture entities, 2 types, 1 group, and non-zero mappings.

- [x] **Step 5: Checkpoint** (attempted; blocked by the recorded workspace permission issue)

```powershell
jj new -m "feat: add Bonsai mapping verification"
```

### Task 5: Write the reusable skill and reference material

**Files:**
- Create: `skills/ifc-bim-conversion-workflow/SKILL.md`
- Create: `skills/ifc-bim-conversion-workflow/references/ifc-standard-links.md`
- Create: `skills/ifc-bim-conversion-workflow/references/bonsai-workflow-links.md`
- Create: `skills/ifc-bim-conversion-workflow/references/software-preflight.md`

**Interfaces:**
- Consumes: The three phase scripts and pressure scenarios.
- Produces: A discoverable skill with independent phase commands and explicit user-confirmation gates.

- [x] **Step 1: Write the skill contract tests before the skill**

Add assertions or scenario checks that the skill text contains:

```text
manual and automatic import choices;
automatic import confirmation;
validation failure blocks import;
geometry-only is not BIM;
existing exporter discovery;
independent phase execution;
IfcStore and non-zero ifc_definition_id verification.
```

- [x] **Step 2: Run the contract checks and confirm RED**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests -q
```

Expected: failure until the skill text satisfies the phase and import-boundary
contract.

- [x] **Step 3: Write the minimal skill**

Use frontmatter:

```yaml
---
name: ifc-bim-conversion-workflow
description: Use when converting Rhino, Blender, or other 3D model content into IFC/BIM, validating IFC legality, or importing IFC into Bonsai or another BIM application.
---
```

The body must contain the seven independent phases from the spec, a compact
decision table for Rhino/Blender/other sources, commands for the three scripts,
the import decision gate, failure-state rules, and links to the reference files.
It must explicitly say that the default import mode is “ask the user”.

- [x] **Step 4: Add references**

`ifc-standard-links.md` records buildingSMART IFC lexical documentation and
IfcOpenShell validation documentation. `bonsai-workflow-links.md` records
Bonsai project loading and the geometry-only distinction. `software-preflight.md`
records how to detect Pixi, Python, IfcOpenShell, Rhino MCP, Blender MCP, Bonsai,
and native exporters without installing tools silently.

- [x] **Step 5: Run quality checks**

```powershell
rg -n "TBD|TODO|FIXME|maybe" skills/ifc-bim-conversion-workflow
Get-Content skills/ifc-bim-conversion-workflow/SKILL.md | Measure-Object -Word
pixi run pytest skills/ifc-bim-conversion-workflow/tests -q
```

Expected: no placeholders, a concise skill, and passing contract tests.

- [x] **Step 6: Checkpoint** (attempted; blocked by the recorded workspace permission issue)

```powershell
jj new -m "feat: add decoupled IFC BIM conversion workflow skill"
```

### Task 6: GREEN/REFACTOR pressure verification

**Files:**
- Modify: `skills/ifc-bim-conversion-workflow/tests/pressure-scenarios.md`
- Modify: `skills/ifc-bim-conversion-workflow/SKILL.md`
- Test: `skills/ifc-bim-conversion-workflow/tests/`

**Interfaces:**
- Consumes: The same scenarios used in Task 1.
- Produces: Evidence that agents follow the independent-phase and import-confirmation rules.

- [x] **Step 1: Run all scenarios with the new skill loaded**

Record in the Task 1 report whether the agent stops at invalid IFC, rejects fake
BIM names, asks for manual/automatic import, requests confirmation before
mutation, and reuses the existing exporter. The skill itself does not invoke an
importer, and no speculative importer or preflight script is added.

- [x] **Step 2: Close only observed loopholes**

If an agent imports after a validation failure, strengthen the explicit
conditional gate. If it treats names as BIM, strengthen the required mapping
evidence. If it assumes automatic import, change the prompt recipe to require an
unselected choice. Do not add speculative workflow branches.

- [x] **Step 3: Run the complete verification set**

```powershell
pixi run pytest skills/ifc-bim-conversion-workflow/tests -q
pixi run pytest test/test_ifc_bonsai_adapter.py -q
pixi run python test/bim/convert_rhino_fixture_to_ifc.py
pixi run python skills/ifc-bim-conversion-workflow/scripts/validate_ifc.py test/output/4chair1table-bim-test.ifc --express-rules
```

- [ ] **Step 4: Verify the live target through Blender MCP** (pending: no live MCP evidence available)

Run the read-only mapping query. Expected: active IFC4 store, 5 furniture, 2
types, 1 group, and non-zero mappings for all imported furniture objects.

- [x] **Step 5: Audit comments and documentation**

Check every new Python function for an English-first docstring and every
non-trivial validation, JSON conversion, and MCP handoff block for a why-comment.

- [x] **Step 6: Final checkpoint** (attempted; blocked by the recorded workspace permission issue)

```powershell
jj new -m "test: verify IFC BIM conversion workflow skill"
```

## Final Review Checklist

- [x] Spec requirements map to a concrete task.
- [x] No phase calls another phase implicitly.
- [x] Manual import is non-mutating.
- [x] Automatic import requires explicit confirmation.
- [x] Invalid IFC cannot reach import.
- [x] Existing exporters are reused before generating code.
- [x] The skill does not copy project-specific conversion logic.
- [x] Tests show the skill prevents the seven baseline violations.
- [x] Current repository IFC adapter tests remain green.
- [x] `jj` checkpoints are recorded, or an existing workspace permission blocker is reported without deleting user files.
