# VisualARQ Source Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only VisualARQ/Rhino source adapter that preserves authored IFC evidence and emits a neutral payload for downstream mapping and export.

**Architecture:** A provider-neutral Python normalizer accepts serialized Rhino/VisualARQ records and returns a versioned JSON-compatible payload. A small semantic registry validates authored IFC entity labels without assigning missing labels. The skill document describes the independent phase and handoff; existing mapping and IFC export remain separate.

**Tech Stack:** Python 3.12, standard library only for the adapter, pytest, JSON fixtures, Rhino MCP capture as an optional live acceptance check.

**Spec:** `docs/superpowers/specs/2026-09-16-visualarq-source-adapter-design.md`

## Global Constraints

- Use Pixi; do not use pip or venv.
- Do not modify the Rhino document; port `15002` is read-only for live acceptance.
- Every new or modified function has an English-first docstring.
- Core extraction, normalization, semantic mapping, provenance, and handoff logic has English-first comments.
- The adapter must not export IFC, generate MassPatch, infer regions, or import Bonsai.
- Preserve raw authored values and report unknown or malformed evidence instead of guessing.

---

### Task 1: Define the neutral source adapter contract

**Files:**
- Create: `adapters/rhino_visualarq_source.py`
- Test: `test/test_rhino_visualarq_source.py`

**Interfaces:**
- Consumes: an iterable of mapping-like provider records and optional source metadata.
- Produces: `normalize_visualarq_source(records, source_metadata=None) -> dict[str, object]`.
- Produces per object: stable `id`, preserved names and properties, geometry summary, relationships, source semantics, analysis participation, and provenance.

- [ ] **Step 1: Write failing tests for the public contract**

```python
def test_normalize_preserves_identity_geometry_and_provenance():
    report = normalize_visualarq_source([{
        "id": "chair-1", "name": "Chair", "layer": "Furniture",
        "object_type": "Mesh", "vertices": [[0, 0, 0]], "faces": [],
        "user_text": {"IfcEntity": "IfcFurnishingElement"},
    }], {"source_name": "room.3dm"})
    item = report["objects"][0]
    assert report["schema_version"] == "visualarq-source-1"
    assert item["id"] == "chair-1"
    assert item["source_name"] == "Chair"
    assert item["source_semantics"]["ifc_entity"] == "IfcFurnishingElement"
    assert item["provenance"]["raw_id"] == "chair-1"

def test_missing_ifc_label_is_unknown_and_not_guessed():
    report = normalize_visualarq_source([{"id": "x", "object_type": "Mesh"}])
    item = report["objects"][0]
    assert item["source_semantics"]["ifc_entity"] == "unknown"
    assert item["analysis_participation"] == "unknown"
    assert report["review_records"]

def test_malformed_top_level_input_fails_clearly():
    with pytest.raises(ValueError, match="records"):
        normalize_visualarq_source({"id": "not-an-iterable-record-list"})
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pixi run pytest test/test_rhino_visualarq_source.py -q`

Expected: FAIL because the adapter module and public function do not exist.

- [ ] **Step 3: Implement the minimal normalizer**

Implement these focused helpers with type annotations and docstrings:

```python
def normalize_visualarq_source(
    records: Iterable[Mapping[str, object]],
    source_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]: ...

def _normalize_object(
    record: Mapping[str, object], index: int, provider_name: str
) -> tuple[dict[str, object], list[dict[str, object]]]: ...

def _normalize_geometry(record: Mapping[str, object]) -> dict[str, object]: ...

def _normalize_relationships(record: Mapping[str, object]) -> dict[str, object]: ...
```

Copy raw properties under `source_properties`; derive only stable structural fields. Use a review record for missing ids, unavailable geometry, and malformed per-object values. A malformed top-level records argument raises `ValueError`.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `pixi run pytest test/test_rhino_visualarq_source.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the adapter contract**

```powershell
git add adapters/rhino_visualarq_source.py test/test_rhino_visualarq_source.py
git commit -m "feat: add neutral VisualARQ source adapter"
```

### Task 2: Add authored IFC semantic evidence handling

**Files:**
- Modify: `adapters/rhino_visualarq_source.py`
- Modify: `test/test_rhino_visualarq_source.py`

**Interfaces:**
- Consumes: normalized provider records from Task 1.
- Produces: `source_semantics.ifc_entity`, `ifc_entity_source`, `confidence`, and review records.

- [ ] **Step 1: Write failing tests for semantic precedence and safety**

```python
def test_om_ifc_entity_is_used_when_plain_ifc_entity_is_absent():
    report = normalize_visualarq_source([{
        "id": "wall-1", "user_text": {"OM.IfcEntity": "IfcWall"}
    }])
    semantics = report["objects"][0]["source_semantics"]
    assert semantics == {
        "ifc_entity": "IfcWall",
        "ifc_entity_source": "OM.IfcEntity",
        "confidence": "authored",
    }

def test_invalid_or_unsupported_label_becomes_unknown_with_review():
    report = normalize_visualarq_source([{
        "id": "x", "user_text": {"IfcEntity": "ChairMaybe"}
    }])
    assert report["objects"][0]["source_semantics"]["ifc_entity"] == "unknown"
    assert report["review_records"][0]["reason"] == "unsupported_ifc_entity"

def test_required_building_and_grid_labels_are_preserved_as_distinct_classes():
    labels = ["IfcWall", "IfcDoor", "IfcWindow", "IfcColumn", "IfcBeam", "IfcSlab", "IfcGrid"]
    report = normalize_visualarq_source([
        {"id": label, "user_text": {"IfcEntity": label}} for label in labels
    ])
    assert [item["source_semantics"]["ifc_entity"] for item in report["objects"]] == labels
```

- [ ] **Step 2: Run tests to verify the semantic tests fail**

Run: `pixi run pytest test/test_rhino_visualarq_source.py -q`

Expected: FAIL until the registry and precedence logic are implemented.

- [ ] **Step 3: Implement a narrow semantic registry**

Add a module-level immutable allowlist for the required IFC entity names. Read `IfcEntity` first, then `OM.IfcEntity`; record which source supplied the value. Accept only exact `Ifc...` names in the registry. Preserve the raw candidate in `source_properties` and add one review record for conflicting values instead of silently choosing between them.

The registry must include `IfcFurniture`, `IfcFurnishingElement`, `IfcEquipmentElement`, `IfcElectricalElement`, `IfcWall`, `IfcDoor`, `IfcWindow`, `IfcColumn`, `IfcBeam`, `IfcSlab`, `IfcRoof`, `IfcStair`, `IfcRailing`, `IfcOpeningElement`, `IfcGrid`, `IfcGridAxis`, and `IfcBuildingElementProxy`.

- [ ] **Step 4: Run tests and verify they pass**

Run: `pixi run pytest test/test_rhino_visualarq_source.py -q`

Expected: PASS.

- [ ] **Step 5: Commit semantic handling**

```powershell
git add adapters/rhino_visualarq_source.py test/test_rhino_visualarq_source.py
git commit -m "feat: preserve authored IFC semantics from VisualARQ"
```

### Task 3: Preserve blocks, instances, guides, and analysis participation

**Files:**
- Modify: `adapters/rhino_visualarq_source.py`
- Modify: `test/test_rhino_visualarq_source.py`

**Interfaces:**
- Consumes: provider relationship fields and optional guide records.
- Produces: `relationships`, `analysis_participation`, and top-level `visualarq_guides` without product merging.

- [ ] **Step 1: Write failing tests for relationship preservation**

```python
def test_nested_instance_path_is_preserved_without_merging():
    report = normalize_visualarq_source([
        {"id": "chair-a", "instance_definition": "Chair",
         "instance_path": ["Room", "Furniture", "Chair"],
         "analysis_participation": "include"},
        {"id": "chair-b", "instance_definition": "Chair",
         "instance_path": ["Room", "Furniture", "Chair"]},
    ])
    assert len(report["objects"]) == 2
    assert report["objects"][0]["relationships"]["instance_path"] == [
        "Room", "Furniture", "Chair"
    ]
    assert report["objects"][0]["analysis_participation"] == "include"

def test_guides_are_separate_from_objects():
    report = normalize_visualarq_source([], {
        "visualarq_guides": [{"id": "axis-a", "name": "A"}]
    })
    assert report["objects"] == []
    assert report["visualarq_guides"] == [{"id": "axis-a", "name": "A"}]

def test_decorative_object_can_be_explicitly_excluded_but_is_not_deleted():
    report = normalize_visualarq_source([{
        "id": "plant", "name": "Plant", "analysis_participation": "exclude"
    }])
    assert len(report["objects"]) == 1
    assert report["objects"][0]["analysis_participation"] == "exclude"
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `pixi run pytest test/test_rhino_visualarq_source.py -q`

Expected: FAIL until relationship and guide preservation is implemented.

- [ ] **Step 3: Implement relationship and participation normalization**

Copy list-valued ids defensively, preserve block-definition and instance paths, and normalize only `include`, `exclude`, and `unknown`. Preserve explicit guide payloads as a separate top-level list. Do not flatten nested groups or collapse repeated instances.

- [ ] **Step 4: Run tests and verify they pass**

Run: `pixi run pytest test/test_rhino_visualarq_source.py -q`

Expected: PASS.

- [ ] **Step 5: Commit relationship handling**

```powershell
git add adapters/rhino_visualarq_source.py test/test_rhino_visualarq_source.py
git commit -m "feat: preserve VisualARQ relationships and guides"
```

### Task 4: Add the reusable skill documentation and correct workflow routing

**Files:**
- Create: `skills/visualarq-source-adapter/SKILL.md`
- Create: `skills/visualarq-source-adapter/tests/test_skill_contract.py`
- Modify: `skills/ifc-bim-conversion-workflow/SKILL.md`
- Modify: `skills/ifc-export/SKILL.md`

**Interfaces:**
- Consumes: the adapter module contract and the existing mapping/export skill names.
- Produces: a discoverable independent skill with exact phase boundaries and valid routing references.

- [ ] **Step 1: Write failing skill-contract tests**

```python
def test_skill_has_triggering_frontmatter_and_phase_boundaries():
    text = Path("skills/visualarq-source-adapter/SKILL.md").read_text()
    assert "name: visualarq-source-adapter" in text
    assert "Use when" in text.splitlines()[2]
    assert "read-only" in text
    assert "does not export IFC" in text
    assert "does not import Bonsai" in text

def test_workflow_does_not_route_to_missing_skill_directories():
    text = Path("skills/ifc-bim-conversion-workflow/SKILL.md").read_text()
    assert "visualarq-source-adapter" in text
    assert "ifc-validation" not in text or "not installed" in text
```

- [ ] **Step 2: Run the contract tests and verify they fail**

Run: `pixi run pytest skills/visualarq-source-adapter/tests/test_skill_contract.py -q`

Expected: FAIL because the skill directory does not exist.

- [ ] **Step 3: Write the concise skill and update routing**

The skill must document when to use the adapter, the provider-neutral input, the output contract, the authored-label safety rules, the read-only guarantee, live MCP `15002` usage, and handoff to `bim-logical-object-mapping`. Replace unavailable routing names with concrete repository scripts or explicitly mark external capabilities as unavailable; do not leave broken skill names that appear callable.

- [ ] **Step 4: Run contract tests and existing skill tests**

Run: `pixi run pytest skills/visualarq-source-adapter/tests skills/ifc-bim-conversion-workflow/tests -q`

Expected: PASS.

- [ ] **Step 5: Commit documentation and routing**

```powershell
git add skills/visualarq-source-adapter skills/ifc-bim-conversion-workflow/SKILL.md skills/ifc-export/SKILL.md
git commit -m "docs: add VisualARQ source adapter skill"
```

### Task 5: Add fixture and live MCP acceptance checks

**Files:**
- Create: `test/fixtures/visualarq_source_fixture.json`
- Create: `test/test_rhino_visualarq_source_acceptance.py`
- Modify: `docs/ifc_bim_conversion_workflow_usage.md`

**Interfaces:**
- Consumes: a captured MCP object listing or fixture with VisualARQ-like fields.
- Produces: a neutral JSON acceptance report without changing Rhino or writing IFC.

- [ ] **Step 1: Write failing acceptance checks**

```python
def test_fixture_contains_mixed_visualarq_semantics():
    payload = json.loads(FIXTURE.read_text())
    report = normalize_visualarq_source(payload["objects"], payload)
    labels = {item["source_semantics"]["ifc_entity"] for item in report["objects"]}
    assert {"IfcWall", "IfcFurnishingElement", "unknown"} <= labels

def test_acceptance_is_read_only_and_does_not_export():
    payload = json.loads(FIXTURE.read_text())
    report = normalize_visualarq_source(payload["objects"], payload)
    assert report["exported_ifc"] is False
    assert report["imported_bonsai"] is False
```

- [ ] **Step 2: Run acceptance tests and verify the fixture/test contract fails**

Run: `pixi run pytest test/test_rhino_visualarq_source_acceptance.py -q`

Expected: FAIL until the fixture and explicit phase flags are present.

- [ ] **Step 3: Add a small representative fixture and acceptance report**

Include one furniture object, one wall, one decorative furnishing object, one unlabeled mesh, and one guide record. The fixture is not a snapshot of a single project; it is a stable contract fixture. Add usage documentation showing how a live `15002` read-only capture is fed into the adapter and how the resulting JSON is handed to the next independent phase.

- [ ] **Step 4: Run the complete focused suite**

Run:

```powershell
pixi run pytest test/test_rhino_visualarq_source.py test/test_rhino_visualarq_source_acceptance.py skills/visualarq-source-adapter/tests skills/bim-logical-object-mapping/tests skills/ifc-bim-conversion-workflow/tests -q
```

Expected: PASS.

- [ ] **Step 5: Commit fixture and acceptance documentation**

```powershell
git add test/fixtures/visualarq_source_fixture.json test/test_rhino_visualarq_source_acceptance.py docs/ifc_bim_conversion_workflow_usage.md
git commit -m "test: verify VisualARQ source adapter acceptance contract"
```

### Task 6: Run live MCP verification and final review

**Files:**
- No source changes expected.
- Optional generated artifact: `outputs/visualarq-source-adapter-<date>/source-report.json`

- [ ] **Step 1: Read the Rhino MCP on port 15002**

Use only the documented read-only object listing/query operation. Capture object ids, geometry types, IFC label properties, block/instance evidence, and guide records into a temporary JSON input. Do not call mutation, export, delete, or save operations.

- [ ] **Step 2: Run the adapter against the capture**

Run the adapter through a small Python command or test harness and write a distinct output directory. Confirm counts by geometry type, authored IFC label, unknown labels, review records, and analysis participation.

- [ ] **Step 3: Grill Me self-check**

Verify:

- no object disappeared because it lacked an IFC label;
- no unlabeled object was guessed into a furniture or building class;
- decorative objects were preserved;
- repeated instances were not merged;
- guides were not emitted as furniture;
- no Rhino document mutation occurred;
- no IFC or Bonsai phase was invoked.

- [ ] **Step 4: Run repository verification**

Run:

```powershell
git diff --check
pixi run pytest test/test_rhino_visualarq_source.py test/test_rhino_visualarq_source_acceptance.py skills/visualarq-source-adapter/tests skills/bim-logical-object-mapping/tests skills/ifc-bim-conversion-workflow/tests -q
git status --short
```

Expected: all focused tests pass, diff check is clean, and only intentional files/artifacts are present.

- [ ] **Step 5: Request code review before integration**

Use `superpowers:requesting-code-review` for a review of the adapter boundary, safety against semantic guessing, and compatibility with existing mapping/export contracts. Do not merge or push from this plan without a separate integration decision.
