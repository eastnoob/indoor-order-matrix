# Constrained MassPatch Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate conservative, geometry-validated `MassPatch` substitutes from
one `MeshGeometry3D`, run the generator against the live Rhino MCP model, and
verify that simplification never loses meaningful occupancy, height, gap, or
occlusion evidence.

**Architecture:** Keep `MassPatch` as the existing source-independent output
record. Add one focused backend module that uses `trimesh` for mesh
inspection/components/OBB candidates and the existing project geometry views
for validation. The exact connected-component mesh is always the fallback;
Rhino integration only transports data and invokes the Pixi backend.

**Tech Stack:** Python 3.12, Pixi, NumPy, Shapely, trimesh, pytest, existing
Neutral Scene and Rhino MCP JSON extraction workflow.

**Spec:** `docs/superpowers/specs/2026-09-04-mass-patch-generation-design.md`

## Global Constraints

- Use the existing Pixi environment and update `pixi.toml`/`pixi.lock`, never pip or venv.
- Do not change the source Rhino model or existing `mass_patch_from_mesh()` behavior.
- Do not add furniture-kind templates, perceptual weights, or IFC persistence.
- Use exact geometry as the fallback whenever simplification is uncertain.
- Every new or modified project-owned function gets an English-first docstring.
- Important geometry and validation blocks get English-first intent comments.
- Use `jj` checkpoints and preserve unrelated dirty files.

---

### Task 1: Freeze the backend API and dependency

**Files:**
- Modify: `pixi.toml`
- Modify: `pixi.lock`
- Create: `test/test_mass_patch_generation.py`
- Create: `features/mass_patch_generation.py`

**Interfaces:**
- Produces `MassPatchGenerationConfig`, `MassPatchCandidateReport`,
  `MassPatchComponentReport`, `MassPatchGenerationResult`, and
  `generate_mass_patches`.
- Reuses `MeshGeometry3D` and `MassPatch` without changing either record.

- [ ] **Step 1: Add the `trimesh` dependency with Pixi**

Run:

```powershell
pixi add --pypi trimesh
```

Expected: `pixi.toml` and `pixi.lock` contain `trimesh`; no pip environment is
created.

- [ ] **Step 2: Write the failing API and validation tests**

Add tests that import the four new records and assert:

```python
def test_generator_returns_exact_baseline_for_a_valid_box():
    result = generate_mass_patches(_box_mesh())
    assert result.source_mesh_id == "box"
    assert len(result.patches) == 1
    assert result.component_reports[0].selected_candidate == "exact_component"


def test_generator_rejects_empty_mesh():
    with pytest.raises(ValueError, match="at least one triangle"):
        generate_mass_patches(_mesh_without_triangles())
```

- [ ] **Step 3: Run the focused tests and confirm the expected RED state**

Run:

```powershell
pixi run pytest test/test_mass_patch_generation.py -q
```

Expected: collection or import failure because the new API is not implemented;
fix test typos only if the failure is unrelated to the missing API.

- [ ] **Step 4: Add the smallest record shells and input validation**

Implement the configuration and result records with finite positive tolerance
validation, then implement `generate_mass_patches` as an exact-component
fallback that raises on empty or degenerate-only input.

- [ ] **Step 5: Re-run focused tests and check the GREEN state**

Run the same command. Expected: the API and exact-baseline tests pass.

- [ ] **Step 6: Run `grill-me` checkpoint 1**

Check that:

- no perceptual weight entered the config;
- the old transport function is unchanged;
- invalid input fails explicitly;
- the exact baseline is always available.

- [ ] **Step 7: Create a `jj` checkpoint**

Run:

```powershell
jj describe -m "feat: freeze MassPatch generation backend contract"
jj new -m "feat: generate conservative MassPatch candidates"
```

---

### Task 2: Build deterministic connected-component geometry

**Files:**
- Modify: `features/mass_patch_generation.py`
- Modify: `test/test_mass_patch_generation.py`

**Interfaces:**
- Internal conversion turns one `MeshGeometry3D` into ordered component
  `MeshGeometry3D` records.
- Component ids use `mass-patch:<source-id>:component:<index>`.

- [ ] **Step 1: Add failing component tests**

Add tests for:

```python
def test_disconnected_components_remain_independently_addressable():
    result = generate_mass_patches(_two_disconnected_boxes())
    assert len(result.patches) == 2
    assert [report.component_index for report in result.component_reports] == [0, 1]


def test_repeated_generation_is_deterministic():
    first = generate_mass_patches(_two_disconnected_boxes()).to_dict()
    second = generate_mass_patches(_two_disconnected_boxes()).to_dict()
    assert first == second
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```powershell
pixi run pytest test/test_mass_patch_generation.py::test_disconnected_components_remain_independently_addressable test/test_mass_patch_generation.py::test_repeated_generation_is_deterministic -q
```

- [ ] **Step 3: Implement component extraction**

Use `trimesh.Trimesh(..., process=False)` and its factual face-connectivity
split. Remap component vertices and triangles into deterministic local records.
Do not merge components based on names, object kind, groups, or distance.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run the two tests from Step 2, then:

```powershell
pixi run pytest test/test_mass_patch_generation.py -q
```

- [ ] **Step 5: Run `grill-me` checkpoint 2**

Check that a chair's seat, back, and legs cannot be merged merely because they
belong to one source object, and that component ordering does not depend on
hash iteration or object names.

- [ ] **Step 6: Create a `jj` checkpoint**

Run:

```powershell
jj describe -m "feat: split MassPatch input by factual connectivity"
jj new -m "feat: add validated oriented-box candidates"
```

---

### Task 3: Generate oriented-box candidates without changing source geometry

**Files:**
- Modify: `features/mass_patch_generation.py`
- Modify: `test/test_mass_patch_generation.py`

**Interfaces:**
- Internal `_oriented_box_candidate(component)` returns a candidate
  `MassPatch` or `None` for degenerate components.
- Candidate provenance identifies `oriented_bounding_box`.

- [ ] **Step 1: Add failing candidate tests**

Add tests that assert:

```python
def test_box_component_produces_a_smaller_oriented_box_candidate():
    result = generate_mass_patches(_box_mesh())
    report = result.component_reports[0]
    assert "oriented_bounding_box" in report.candidate_methods
    assert result.patches[0].provenance["source_component_index"] == 0


def test_source_mesh_is_not_mutated_by_candidate_generation():
    source = _box_mesh()
    before = source.to_dict()
    generate_mass_patches(source)
    assert source.to_dict() == before
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```powershell
pixi run pytest test/test_mass_patch_generation.py -q
```

- [ ] **Step 3: Implement OBB candidate construction**

Use `trimesh` only to calculate the oriented bounds. Convert the resulting
candidate vertices and faces back into the project-owned `MassPatch`. Preserve
the source units and provenance. Do not use a hard angle, furniture type, or
vertex-count threshold to accept the candidate.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run the full focused file. Expected: both exact and OBB candidates exist in
the component report, while the selected result remains exact until validation
is implemented.

- [ ] **Step 5: Run `grill-me` checkpoint 3**

Check that OBB is only a candidate, that no source vertices are overwritten,
and that no candidate is selected merely because it has fewer triangles.

- [ ] **Step 6: Create a `jj` checkpoint**

Run:

```powershell
jj describe -m "feat: construct oriented-box MassPatch candidates"
jj new -m "feat: validate MassPatch occupancy and height fidelity"
```

---

### Task 4: Validate candidates and select only safe simplifications

**Files:**
- Modify: `features/mass_patch_generation.py`
- Modify: `test/test_mass_patch_generation.py`

**Interfaces:**
- `validate_mass_patch_candidate(source, candidate, config)` returns
  `MassPatchCandidateReport`.
- `generate_mass_patches` selects the accepted candidate with the lowest
  geometry error, then the lowest triangle count.

- [ ] **Step 1: Add failing source-comparison tests**

Add deterministic fixtures and tests:

```python
def test_hollow_frame_rejects_a_filled_box():
    result = generate_mass_patches(_hollow_frame_mesh())
    report = result.component_reports[0]
    assert report.selected_candidate == "exact_component"
    assert report.rejections["oriented_bounding_box"] == "plan_overreach"


def test_chair_leg_gaps_are_not_filled():
    result = generate_mass_patches(_chair_mesh())
    assert result.component_reports[0].gap_preservation_error <= 0.02


def test_sloped_component_falls_back_when_height_error_is_too_large():
    result = generate_mass_patches(_sloped_component_mesh())
    assert result.component_reports[0].selected_candidate == "exact_component"
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```powershell
pixi run pytest test/test_mass_patch_generation.py -q
```

- [ ] **Step 3: Implement deterministic samples**

Build XY samples from the union of source/candidate bounds at the configured
`sample_spacing`, or at the larger of `4 * linear_tolerance` and one
thirty-second of the combined plan-bound span when it is omitted. Then append
all source and candidate plan vertices. Use `vertical_intervals_at` for
occupied height intervals and
`occlusion_intersections` for deterministic ray checks. Keep plan recall,
overreach, gap error, height endpoint error, and occlusion disagreement as
separate report fields.

- [ ] **Step 4: Implement candidate decision**

Reject a candidate if any configured hard tolerance fails. Treat exact
component geometry as the mandatory accepted baseline. Record all tolerances,
errors, and rejection reasons in provenance and reports.

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run:

```powershell
pixi run pytest test/test_mass_patch_generation.py -q
```

Expected: boxes may select OBB; hollow frames, sloped geometry, and gap-heavy
chairs select exact fallback.

- [ ] **Step 6: Run `grill-me` checkpoint 4**

Try to break the implementation with:

- a box that is rotated;
- a chair with disconnected legs;
- a hollow rectangular frame;
- a sloped seat or back;
- a component with very small but real gaps.

Confirm that geometry tolerances are not perceptual weights and that exact
fallback prevents false occupancy.

- [ ] **Step 7: Create a `jj` checkpoint**

Run:

```powershell
jj describe -m "feat: validate and select safe MassPatch simplifications"
jj new -m "test: verify MassPatch generation against live Rhino geometry"
```

---

### Task 5: Run the complete backend regression suite

**Files:**
- Modify: `test/test_mass_patch_generation.py` only if a test exposes a
  genuine contract defect.
- Modify: `features/mass_patch_generation.py` only for defects proven by tests.

- [ ] **Step 1: Audit comments and docstrings**

Check every new or modified function and every geometry/selection/serialization
block for English-first documentation and intent comments.

- [ ] **Step 2: Run focused and repository tests**

Run:

```powershell
pixi run pytest test/test_mass_patch_generation.py -q
pixi run pytest test/test_geometry_substitutes.py test/test_scene_contract.py test/test_neutral_scene_analysis_regression.py -q
pixi run pytest -q
```

- [ ] **Step 3: Run `grill-me` checkpoint 5**

Review the diff for accidental changes to inference, scoring, SVG parsing,
IFC persistence, or source geometry. Remove unrelated edits before continuing.

- [ ] **Step 4: Create a `jj` checkpoint**

Run:

```powershell
jj describe -m "test: pass MassPatch backend regression suite"
jj new -m "test: run MassPatch generation on live Rhino MCP"
```

---

### Task 6: Execute the live Rhino MCP acceptance run

**Files:**
- Create: `test/bim/run_live_mass_patch_generation.py`
- Create: `test/test_live_mass_patch_generation.py`
- Create: `test/output/mass_patch_generation_live.json`
- Create: `test/output/mass_patch_generation_live.executed.ipynb`
- Create: `test/output/mass_patch_generation_live.html`

**Interfaces:**
- The Rhino extraction remains read-only and produces the existing neutral
  mesh JSON shape.
- The backend runner consumes that JSON and emits generated patches plus
  `MassPatchGenerationResult` validation reports.

- [ ] **Step 1: Add a failing live-run contract test**

Test that the runner rejects a missing source file and writes a result with
`source_mesh_id`, `patches`, `component_reports`, and `source_mutation_check`.

- [ ] **Step 2: Run the contract test and confirm RED**

Run:

```powershell
pixi run pytest test/test_live_mass_patch_generation.py -q
```

- [ ] **Step 3: Implement the read-only runner**

Use the active Rhino MCP endpoint on port `10500` or the existing exported
neutral mesh artifact. Do not delete, rename, move, or edit Rhino objects.
Convert each selected logical source object to `MeshGeometry3D`, call
`generate_mass_patches`, and write only external JSON artifacts.

- [ ] **Step 4: Execute against the current Rhino MCP model**

Run the runner with the current MCP model and record:

- source object and triangle counts;
- generated patch counts;
- selected candidate per component;
- plan recall and overreach;
- height and occlusion errors;
- source mutation check.

- [ ] **Step 5: Execute the notebook**

Render source geometry and generated MassPatch geometry together. Keep labels
outside the main geometry where possible. Show a compact table for candidate,
selected method, triangle count, recall, overreach, height error, and gap error.

- [ ] **Step 6: Run `grill-me` checkpoint 6**

Inspect the live result for:

- false filled chair-leg gaps;
- missing seat/back height levels;
- unexpected world/local coordinate changes;
- mutation or replacement of Rhino source objects;
- reports that claim accuracy without measured evidence.

- [ ] **Step 7: Create the final `jj` checkpoint**

Run:

```powershell
jj describe -m "test: verify MassPatch generation on live Rhino MCP"
```

Do not package the backend yet. Packaging begins only after this end-to-end
result is reviewed and accepted.
