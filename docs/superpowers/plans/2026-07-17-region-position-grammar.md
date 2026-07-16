# Region Position Grammar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the public position-order metric so `P_position_fit` scores furniture-group positions inside an analysis scope, not affordance extents inside a furniture group.

**Architecture:** Add a region-level position grammar builder that consumes existing neutral `furniture_groups` and emits scope-level evidence. Keep the old extent-level grammar as `group_assembly_grammar` debug evidence. Wire public matrix rows and the default focused overlay only to `region_position_grammar`.

**Tech Stack:** Python stdlib, existing `Rect`, existing `scene_loader` / `scene_inference` / `scene_evaluator`, Pixi pytest, nbformat/nbclient, Playwright screenshot CLI, jj.

---

## File Structure

- Modify: `features/position_grammar.py`
  - Add region-level scope construction and scoring.
  - Rename old public entry into debug assembly evidence.
  - Keep shared local-frame helpers in this file.
- Modify: `features/scene_evaluator.py`
  - Call both region-level and debug assembly grammar builders.
  - Make `P_position_fit` and `P_position_confidence` use region-level evidence only.
  - Make `scene_position_grammar_overlay_svg()` draw furniture-group slots/residuals only.
- Modify: `test/test_floorplan_scene_loader.py`
  - Add boundary tests proving the public metric is group-level.
  - Add `SVG_potionNoRotation.svg` coverage.
- Modify: `test/position_grammar_proxy_demo.ipynb`
  - Add `SVG_potionNoRotation.svg`.
  - Show region-level position evidence only.
- Generate: `test/output/position_grammar_proxy_demo.executed.ipynb`
- Generate: `test/output/position_grammar_proxy_demo.visual.html`
- Generate: `test/output/position_grammar_proxy_demo.visual.png`

---

### Task 1: Public Position Boundary Tests

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add imports if missing**

Ensure the file already imports `Path`, `Rect`, `load_structured_svg_scene`, and
`evaluate_scene`. If not, add only the missing import.

- [ ] **Step 2: Add a synthetic region-level slot-count test**

Add this test near the existing position grammar tests:

```python
def test_region_position_grammar_scores_furniture_groups_not_extents():
    """Public position evidence should assign one slot per furniture group."""
    from features.position_grammar import region_position_grammar_evidence

    groups = [
        {
            "id": "furniture_group_a",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=0, cy=0, width=20, height=20),
            "member_ids": ["a_table", "a_chair"],
            "furniture_affordance_extent_ids": ["a_table_extent", "a_chair_extent"],
            "metadata": {"group-axis-angle": "0", "group-axis-basis": "test"},
        },
        {
            "id": "furniture_group_b",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=100, cy=0, width=20, height=20),
            "member_ids": ["b_table", "b_chair"],
            "furniture_affordance_extent_ids": ["b_table_extent", "b_chair_extent"],
            "metadata": {"group-axis-angle": "0", "group-axis-basis": "test"},
        },
        {
            "id": "furniture_group_c",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=200, cy=0, width=20, height=20),
            "member_ids": ["c_table", "c_chair"],
            "furniture_affordance_extent_ids": ["c_table_extent", "c_chair_extent"],
            "metadata": {"group-axis-angle": "0", "group-axis-basis": "test"},
        },
    ]

    evidence = region_position_grammar_evidence(groups)
    item = evidence["items"][0]

    assert item["subject_kind"] == "room_scope"
    assert item["position-member-count"] == 3
    assert item["position-slot-count"] == 3
    assert item["assignments"] == [
        "furniture_group_a",
        "furniture_group_b",
        "furniture_group_c",
    ]
    assert all("extent" not in assignment for assignment in item["assignments"])
```

- [ ] **Step 3: Verify the new test fails**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_region_position_grammar_scores_furniture_groups_not_extents -q
```

Expected: FAIL with `ImportError` or missing `region_position_grammar_evidence`.

- [ ] **Step 4: Add a matrix evidence boundary test**

Add:

```python
def test_evaluator_position_rows_use_region_position_evidence():
    """Public P_position rows should expose region-level group assignments."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}
    evidence = rows["P_position_fit"]["region_position_grammar_evidence"]

    assert evidence
    assert "position_grammar_evidence" not in rows["P_position_fit"]
    assert all(item["subject_kind"] in {"activity_region", "room_scope"} for item in evidence)
    assert all(
        assignment.startswith("furniture_group_")
        for item in evidence
        for assignment in item["assignments"]
    )
```

- [ ] **Step 5: Verify the matrix evidence test fails**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_evaluator_position_rows_use_region_position_evidence -q
```

Expected: FAIL because the current row still exposes extent-level `position_grammar_evidence`.

---

### Task 2: Region-Level Grammar API

**Files:**
- Modify: `features/position_grammar.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Rename the current public function to debug assembly evidence**

In `features/position_grammar.py`, rename:

```python
def position_grammar_evidence(
    furniture_groups: list[dict],
    extents: list[dict],
) -> dict:
    """Build internal position grammar evidence for canonical furniture groups."""
```

to:

```python
def group_assembly_grammar_evidence(
    furniture_groups: list[dict],
    extents: list[dict],
) -> dict:
    """Build debug position evidence for extents inside each furniture group."""
```

Keep the function body, but return:

```python
return {
    "method": "local_frame_group_assembly_grammar_debug",
    "items": items,
}
```

Then add a temporary compatibility wrapper:

```python
def position_grammar_evidence(
    furniture_groups: list[dict],
    extents: list[dict],
) -> dict:
    """Return legacy debug assembly evidence for older callers."""
    return group_assembly_grammar_evidence(furniture_groups, extents)
```

- [ ] **Step 2: Add the region-level public function**

Add above the old `_group_position_evidence()` helper:

```python
def region_position_grammar_evidence(furniture_groups: list[dict]) -> dict:
    """Build public position grammar evidence for furniture groups in scopes."""
    scopes = _position_scopes(furniture_groups)
    items = []
    for scope in scopes:
        evidence = _scope_position_evidence(scope)
        if evidence is not None:
            items.append(evidence)
    return {
        "method": "region_level_furniture_group_position_grammar",
        "scopes": scopes,
        "items": items,
    }
```

- [ ] **Step 3: Add scope construction**

Add:

```python
def _position_scopes(furniture_groups: list[dict]) -> list[dict]:
    """Create analysis scopes that contain two or more furniture groups."""
    groups = [
        group
        for group in furniture_groups
        if _is_position_group(group)
    ]
    by_region: dict[str, list[dict]] = {}
    for group in groups:
        region = group.get("activity_region_id") or group.get("region") or "room"
        by_region.setdefault(str(region), []).append(group)
    region_scopes = [
        _scope_record(f"position_scope_region_{region}", "activity_region", members)
        for region, members in sorted(by_region.items())
        if len(members) >= 2
    ]
    if region_scopes:
        return region_scopes
    if len(groups) >= 2:
        return [_scope_record("position_scope_room", "room_scope", groups)]
    return []
```

Add:

```python
def _is_position_group(group: dict) -> bool:
    """Return whether a group should participate in public position scoring."""
    region = str(group.get("activity_region_id") or group.get("region") or "")
    metadata = group.get("metadata", {})
    if region.lower() == "global":
        return False
    if metadata.get("analysis-position") == "false":
        return False
    return True
```

Add:

```python
def _scope_record(scope_id: str, kind: str, groups: list[dict]) -> dict:
    """Return one position scope with a shared local frame."""
    rect = _bounds(groups)
    frame = _scope_frame(groups, rect)
    return {
        "id": scope_id,
        "kind": kind,
        "member_group_ids": [group["id"] for group in sorted(groups, key=lambda item: item["id"])],
        "groups": sorted(groups, key=lambda item: item["id"]),
        "rect": rect,
        "position-frame-angle": round(frame["angle"], 4),
        "position-frame-basis": frame["basis"],
    }
```

- [ ] **Step 4: Add scope frame and bounds helpers**

Update the import line at the top of `features/position_grammar.py` from:

```python
from math import cos, hypot, radians, sin
```

to:

```python
from math import atan2, cos, degrees, hypot, radians, sin
```

Add:

```python
def _bounds(records: list[dict]):
    """Return the axis-aligned union rect for records with Rect geometry."""
    left = min(record["rect"].left for record in records)
    right = max(record["rect"].right for record in records)
    top = min(record["rect"].top for record in records)
    bottom = max(record["rect"].bottom for record in records)
    rect_type = type(records[0]["rect"])
    return rect_type(
        cx=(left + right) / 2,
        cy=(top + bottom) / 2,
        width=right - left,
        height=bottom - top,
    )
```

Add:

```python
def _scope_frame(groups: list[dict], rect) -> dict:
    """Choose a local frame for group-position scoring without scoring rotation."""
    angles = []
    for group in groups:
        raw = group.get("metadata", {}).get("group-axis-angle")
        if raw is None:
            continue
        try:
            angles.append(float(raw) % 180.0)
        except (TypeError, ValueError):
            continue
    if angles:
        x = mean(cos(radians(angle * 2.0)) for angle in angles)
        y = mean(sin(radians(angle * 2.0)) for angle in angles)
        angle = (0.5 * degrees(atan2(y, x))) % 180.0
        return {"angle": angle, "basis": "furniture_group_frame_consensus"}
    return {
        "angle": 0.0 if rect.width >= rect.height else 90.0,
        "basis": "scope_bbox_axis_weak",
    }
```

- [ ] **Step 5: Add scope-position evidence**

Add:

```python
def _scope_position_evidence(scope: dict) -> dict | None:
    """Return selected grammar evidence for furniture groups inside one scope."""
    groups = scope["groups"]
    if len(groups) < 2:
        return None
    frame = {
        "angle": scope["position-frame-angle"],
        "basis": scope["position-frame-basis"],
    }
    coords = [
        {
            "id": group["id"],
            "x": group["rect"].cx,
            "y": group["rect"].cy,
            "u": u,
            "v": v,
            "scale": max(group["rect"].width, group["rect"].height, 1e-9),
        }
        for group in groups
        for u, v in [
            _project(
                group["rect"].cx,
                group["rect"].cy,
                scope["rect"].cx,
                scope["rect"].cy,
                frame["angle"],
            )
        ]
    ]
    candidates = [
        item
        for item in (
            _line_candidate(scope, coords, frame),
            _pair_candidate(scope, coords, frame),
            _grid_candidate(scope, coords, frame),
        )
        if item is not None
    ]
    if not candidates:
        return None
    selected = sorted(candidates, key=lambda item: (-item["position-fit"], item["complexity"]))[0]
    selected["subject_kind"] = scope["kind"]
    selected["subject_id"] = scope["id"]
    selected["position-system-id"] = f"{scope['id']}__{selected['position-grammar-type']}"
    selected["scope-member-group-ids"] = list(scope["member_group_ids"])
    return selected
```

The existing candidate helpers already accept a dict with `id` and `rect`, so
the scope dict can reuse them.

- [ ] **Step 6: Run boundary test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_region_position_grammar_scores_furniture_groups_not_extents -q
```

Expected: PASS.

---

### Task 3: Wire Public Matrix Rows To Region Evidence

**Files:**
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Update imports**

Replace:

```python
from .position_grammar import position_grammar_evidence
```

with:

```python
from .position_grammar import group_assembly_grammar_evidence
from .position_grammar import region_position_grammar_evidence
```

- [ ] **Step 2: Build both evidence sets in `evaluate_scene()`**

Replace:

```python
position_grammar = position_grammar_evidence(
    furniture_groups,
    furniture_affordance_extents,
)
```

with:

```python
region_position_grammar = region_position_grammar_evidence(furniture_groups)
group_assembly_grammar = group_assembly_grammar_evidence(
    furniture_groups,
    furniture_affordance_extents,
)
```

- [ ] **Step 3: Append public rows from region evidence**

Replace:

```python
rows.extend(_position_grammar_rows(position_grammar))
```

with:

```python
rows.extend(_position_grammar_rows(region_position_grammar))
```

- [ ] **Step 4: Return both evidence sets**

In the returned matrix dict, add:

```python
"region_position_grammar": region_position_grammar,
"group_assembly_grammar": group_assembly_grammar,
```

Do not return a top-level `"position_grammar"` key for the new public path.

- [ ] **Step 5: Change `_position_grammar_rows()` evidence key**

In `_position_grammar_rows()`, replace both occurrences of:

```python
"position_grammar_evidence": items,
```

with:

```python
"region_position_grammar_evidence": items,
```

Change the not-available text to:

```python
"needs at least two canonical furniture groups in a position scope"
```

Change row methods:

```python
"method": "region_position_grammar_selected_fit_mean",
```

and:

```python
"method": "region_position_grammar_confidence_mean",
```

- [ ] **Step 6: Update `_position_grammar_items()`**

Replace:

```python
return list(row.get("position_grammar_evidence", []))
```

with:

```python
return list(row.get("region_position_grammar_evidence", []))
```

- [ ] **Step 7: Update adapter payload evidence geometry**

Find the evidence geometry builder near the adapter payload. Add:

```python
"region_position_grammar": region_position_grammar,
"group_assembly_grammar": group_assembly_grammar,
```

and remove any `"position_grammar"` payload key if present.

- [ ] **Step 8: Run matrix evidence boundary test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_evaluator_position_rows_use_region_position_evidence -q
```

Expected: PASS.

---

### Task 4: Default Overlay Uses FurnitureGroup Slots

**Files:**
- Modify: `features/scene_evaluator.py`
- Modify: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add focused overlay boundary test**

Add:

```python
def test_position_grammar_overlay_draws_group_slots_not_extent_slots():
    """Focused position overlay should show furniture-group assignments only."""
    from features.scene_evaluator import scene_position_grammar_overlay_svg

    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)

    svg = scene_position_grammar_overlay_svg(scene, matrix)

    assert 'data-layer="position-grammar-slot"' in svg
    assert 'data-member="furniture_group_center_lounge"' in svg
    assert "furniture_affordance_extent_" not in svg
```

- [ ] **Step 2: Verify overlay test fails**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_grammar_overlay_draws_group_slots_not_extent_slots -q
```

Expected: FAIL because the current overlay still draws extent ids.

- [ ] **Step 3: Add group proxy outline helper**

In `features/scene_evaluator.py`, add:

```python
def _position_grammar_group_svg(group: dict) -> str:
    """Draw one furniture-group proxy outline for focused position evidence."""
    rect = group["rect"]
    return (
        f'<rect data-layer="position-grammar-group" '
        f'data-group="{escape(group["id"])}" '
        f'x="{rect.left:.1f}" y="{rect.top:.1f}" '
        f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
        f'fill="none" stroke="#059669" stroke-width="2.0" '
        f'stroke-dasharray="2 4" opacity="0.72">'
        f'<title>{escape(group["id"])}</title></rect>'
    )
```

- [ ] **Step 4: Replace focused overlay extent loop**

In `scene_position_grammar_overlay_svg()`, replace:

```python
objects_by_id = {obj["id"]: obj for obj in scene.get("objects", [])}
for extent in matrix.get("furniture_affordance_extents", []):
    obj = objects_by_id.get(extent["object_id"])
    layers.append(
        _position_grammar_extent_svg(extent, obj)
    )
```

with:

```python
for group in matrix.get("furniture_groups", []):
    layers.append(_position_grammar_group_svg(group))
```

Leave `_position_grammar_extent_svg()` in place only if other tests still use it.

- [ ] **Step 5: Run focused overlay tests**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_grammar_overlay_draws_group_slots_not_extent_slots test/test_floorplan_scene_loader.py::test_position_grammar_overlay_hides_unrelated_metric_layers -q
```

Expected: PASS.

---

### Task 5: PotionNoRotation Fixture Coverage

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add fixture matrix test**

Add:

```python
def test_position_no_rotation_fixture_scores_position_without_rotation_signal():
    """Position fixture should produce group-level position evidence with zero object rotations."""
    scene = load_structured_svg_scene(Path("test/SVG_potionNoRotation.svg"))

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}
    evidence = rows["P_position_fit"]["region_position_grammar_evidence"]

    assert rows["P_position_fit"]["status"] == "computed"
    assert evidence
    assert all(item["position-member-count"] >= 2 for item in evidence)
    assert all(
        assignment.startswith("furniture_group_")
        for item in evidence
        for assignment in item["assignments"]
    )
```

- [ ] **Step 2: Run fixture test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_no_rotation_fixture_scores_position_without_rotation_signal -q
```

Expected: PASS after Tasks 2-3.

---

### Task 6: Notebook And Visual Verification

**Files:**
- Modify: `test/position_grammar_proxy_demo.ipynb`
- Generate: `test/output/position_grammar_proxy_demo.executed.ipynb`
- Generate: `test/output/position_grammar_proxy_demo.visual.html`
- Generate: `test/output/position_grammar_proxy_demo.visual.png`

- [ ] **Step 1: Update notebook fixture list**

In `test/position_grammar_proxy_demo.ipynb`, ensure the displayed fixtures are:

```python
[
    Path("test/SVG_baseline.svg"),
    Path("test/SVG_oblique.svg"),
    Path("test/SVG_chaoticsvg.svg"),
    Path("test/SVG_potionNoRotation.svg"),
]
```

- [ ] **Step 2: Update notebook row access**

Change notebook text output to read:

```python
evidence = rows["P_position_fit"].get("region_position_grammar_evidence", [])
print(
    path.name,
    "groups=", len(matrix.get("furniture_groups", [])),
    "position_items=", len(evidence),
    "fit=", rows["P_position_fit"]["score"],
    "confidence=", rows["P_position_confidence"]["score"],
)
for item in evidence:
    print(
        " ",
        item["subject_id"],
        item["subject_kind"],
        item["position-grammar-type"],
        "members=", item["position-member-count"],
        "slots=", item["position-slot-count"],
        "residual_mean=", item["position-residual-mean"],
    )
display(SVG(data=scene_position_grammar_overlay_svg(scene, matrix)))
```

- [ ] **Step 3: Execute notebook**

Run:

```powershell
@'
import nbformat
from nbclient import NotebookClient
from pathlib import Path
source = Path("test/position_grammar_proxy_demo.ipynb")
out = Path("test/output/position_grammar_proxy_demo.executed.ipynb")
nb = nbformat.read(source, as_version=4)
NotebookClient(nb, timeout=300, kernel_name="python3").execute()
out.parent.mkdir(parents=True, exist_ok=True)
nbformat.write(nb, out)
print(out)
'@ | pixi run python -
```

Expected: writes `test/output/position_grammar_proxy_demo.executed.ipynb`.

- [ ] **Step 4: Export simple HTML**

Run:

```powershell
@'
from html import escape
from pathlib import Path
import nbformat

source = Path("test/output/position_grammar_proxy_demo.executed.ipynb")
target = Path("test/output/position_grammar_proxy_demo.visual.html")
nb = nbformat.read(source, as_version=4)
parts = [
    '<!doctype html><meta charset="utf-8">',
    '<style>body{font-family:Arial,sans-serif;margin:24px;background:#fff;color:#111} pre{white-space:pre-wrap} svg{display:block;margin:16px 0 40px;border:1px solid #ddd;max-width:100%;height:auto}</style>',
    '<h1>Region position grammar demo</h1>',
]
for cell in nb.cells:
    if cell.cell_type != "code":
        continue
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream":
            parts.append(f'<pre>{escape(output.get("text", ""))}</pre>')
        data = output.get("data", {})
        svg = data.get("image/svg+xml")
        if isinstance(svg, list):
            svg = "".join(svg)
        if svg:
            parts.append(svg)
target.write_text("\n".join(parts), encoding="utf-8")
print(target)
'@ | pixi run python -
```

Expected: writes `test/output/position_grammar_proxy_demo.visual.html`.

- [ ] **Step 5: Screenshot visual HTML**

Run:

```powershell
npx --yes playwright screenshot --full-page "file:///D:/PROJECTS/understandOtherPackage/order_analyzer/test/output/position_grammar_proxy_demo.visual.html" "test/output/position_grammar_proxy_demo.visual.png"
```

Expected: writes `test/output/position_grammar_proxy_demo.visual.png`.

---

### Task 7: Focused Verification

**Files:**
- All modified files

- [ ] **Step 1: Run position grammar tests**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "position_grammar or potionNoRotation or position_no_rotation"
```

Expected: PASS.

- [ ] **Step 2: Run MVP tests**

Run:

```powershell
pixi run pytest test/test_order_analyzer_mvp.py -q
```

Expected: PASS.

- [ ] **Step 3: Inspect visual screenshot**

Open:

```powershell
Start-Process "D:\PROJECTS\understandOtherPackage\order_analyzer\test\output\position_grammar_proxy_demo.visual.html"
```

Expected:

- yellow points correspond to furniture groups;
- no `furniture_affordance_extent_` ids appear in the default focused overlay;
- `SVG_potionNoRotation.svg` appears as the fourth visual case.

- [ ] **Step 4: Check jj status**

Run:

```powershell
jj status
```

Expected: current change contains the region-position grammar implementation, tests, notebook outputs, and spec/plan docs.
