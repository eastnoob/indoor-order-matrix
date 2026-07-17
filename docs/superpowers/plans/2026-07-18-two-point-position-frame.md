# Two-Point Position Frame Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Prevent exactly-two furniture-group scopes from self-inferring a scoring frame by default, while keeping an explicit demo/debug opt-in.

**Architecture:** Keep the fix inside `features/position_grammar.py`, where all region-level position frame candidates are built. Thread one optional boolean from `evaluate_scene()` only so notebooks can opt into the old self-inferred behavior for comparison.

**Tech Stack:** Python, Pixi, pytest, existing notebook renderer.

---

### Task 1: Red Tests For Two-Point Self-Inferred Frames

**Files:**
- Modify: `test/test_floorplan_scene_loader.py`

- [x] **Step 1: Add synthetic regression tests**

Add these tests near the existing position grammar tests:

```python
def test_region_position_grammar_two_point_scope_does_not_self_infer_frame_by_default():
    """Two furniture groups should not use their own connecting line as frame."""
    from features.position_grammar import region_position_grammar_evidence

    groups = [
        {
            "id": "furniture_group_pair_a",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=0, cy=0, width=20, height=20),
            "member_ids": ["a"],
            "furniture_affordance_extent_ids": ["a"],
            "metadata": {},
        },
        {
            "id": "furniture_group_pair_b",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=100, cy=100, width=20, height=20),
            "member_ids": ["b"],
            "furniture_affordance_extent_ids": ["b"],
            "metadata": {},
        },
    ]

    item = region_position_grammar_evidence(groups)["items"][0]

    assert item["position-frame-basis"] == "global_position_fallback"
    assert item["position-frame-angle"] in {0.0, 90.0}
    assert item["position-residual-mean"] > 0
    assert item["position-fit"] < 1.0
```

```python
def test_region_position_grammar_two_point_scope_can_opt_into_self_inferred_frame():
    """The demo switch should expose the old two-point inferred frame behavior."""
    from features.position_grammar import region_position_grammar_evidence

    groups = [
        {
            "id": "furniture_group_pair_a",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=0, cy=0, width=20, height=20),
            "member_ids": ["a"],
            "furniture_affordance_extent_ids": ["a"],
            "metadata": {},
        },
        {
            "id": "furniture_group_pair_b",
            "activity_region_id": "room",
            "region": "room",
            "rect": Rect(cx=100, cy=100, width=20, height=20),
            "member_ids": ["b"],
            "furniture_affordance_extent_ids": ["b"],
            "metadata": {},
        },
    ]

    item = region_position_grammar_evidence(
        groups,
        allow_two_point_inferred_frame=True,
    )["items"][0]

    assert item["position-frame-basis"] == "position_pair_direction"
    assert item["position-frame-angle"] == 45.0
    assert item["position-fit"] == 1.0
```

- [x] **Step 2: Add SVG fixture regression**

Add this test after the position/no-rotation fixture tests:

```python
def test_position_no_rotation_center_lounge_no_false_two_point_residual():
    """Center lounge should not self-score zero residual from two group centers."""
    scene = load_structured_svg_scene(Path("test/SVG_potionNoRotation.svg"))

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}
    item = [
        evidence
        for evidence in rows["P_position_fit"]["region_position_grammar_evidence"]
        if evidence["subject_id"] == "position_scope_region_center_lounge"
    ][0]

    assert item["position-frame-basis"] != "position_pair_direction"
    assert item["position-residual-mean"] > 0
    assert item["position-fit"] < 1.0
```

- [x] **Step 3: Verify the tests fail for the expected reason**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "two_point_scope or no_false_two_point_residual"
```

Expected: the first test fails because the current default selects
`position_pair_direction`; the opt-in test fails because the keyword argument
does not exist yet.

### Task 2: Minimal Implementation

**Files:**
- Modify: `features/position_grammar.py`
- Modify: `features/scene_evaluator.py`

- [x] **Step 1: Add the public grammar option**

Change the grammar entrypoint to:

```python
def region_position_grammar_evidence(
    furniture_groups: list[dict],
    *,
    allow_two_point_inferred_frame: bool = False,
) -> dict:
    """Build public position grammar evidence for furniture groups in scopes."""
```

Pass the flag into `_scope_position_evidence(scope, allow_two_point_inferred_frame)`.

- [x] **Step 2: Thread the flag through scope scoring**

Change:

```python
def _scope_position_evidence(scope: dict) -> dict | None:
```

to:

```python
def _scope_position_evidence(
    scope: dict,
    allow_two_point_inferred_frame: bool,
) -> dict | None:
    """Return selected grammar evidence for furniture groups inside one scope."""
```

Call:

```python
_frame_candidates(
    scope,
    base_coords,
    allow_two_point_inferred_frame=allow_two_point_inferred_frame,
)
```

- [x] **Step 3: Guard self-derived frame candidates**

Change `_frame_candidates()` to accept the flag:

```python
def _frame_candidates(
    scope: dict,
    coords: list[dict],
    *,
    allow_two_point_inferred_frame: bool = False,
) -> list[dict]:
    """Return position-only frame candidates for one scope."""
```

Only add pairwise directions and PCA when either there are at least three
points or the flag is enabled:

```python
self_inferred_allowed = len(coords) >= 3 or allow_two_point_inferred_frame
if self_inferred_allowed:
    for first, second in combinations(coords, 2):
        dx = second["x"] - first["x"]
        dy = second["y"] - first["y"]
        if hypot(dx, dy) > 1e-9:
            candidates.append((degrees(atan2(dy, dx)), "position_pair_direction"))
    pca = _pca_position_angle(coords)
    if pca is not None:
        candidates.append((pca, "position_pca_frame"))
```

Keep authored frames before this block and global `0/90` after it.

- [x] **Step 4: Add evaluator demo option**

Change:

```python
def evaluate_scene(scene: dict, *, position_grammar_enabled: bool = True) -> dict:
```

to:

```python
def evaluate_scene(
    scene: dict,
    *,
    position_grammar_enabled: bool = True,
    allow_two_point_inferred_frame: bool = False,
) -> dict:
    """Evaluate a parsed layout scene into stable, notebook-friendly rows."""
```

Call:

```python
region_position_grammar_evidence(
    furniture_groups,
    allow_two_point_inferred_frame=allow_two_point_inferred_frame,
)
```

only when `position_grammar_enabled` is true. The disabled branch stays
unchanged.

- [x] **Step 5: Verify focused tests pass**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "two_point_scope or no_false_two_point_residual"
```

Expected: all selected tests pass.

### Task 3: Demo Opt-In And Regression Verification

**Files:**
- Modify: `test/position_grammar_proxy_demo.ipynb`

- [x] **Step 1: Set the notebook demo opt-in**

In the cell that builds `matrix`, call:

```python
matrix = evaluate_scene(
    scene,
    allow_two_point_inferred_frame=True,
)
```

This keeps normal matrix evaluation strict while letting the visual demo show
the old two-point inferred-frame behavior on request.

- [x] **Step 2: Run the focused position grammar suite**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "position_grammar or potionNoRotation or position_no_rotation"
```

Expected: selected tests pass.

- [x] **Step 3: Run the MVP suite**

Run:

```powershell
pixi run pytest test/test_order_analyzer_mvp.py -q
```

Expected: selected tests pass.

- [x] **Step 4: Regenerate the position grammar visual demo**

Run the existing notebook execution command used in this repo for
`test/position_grammar_proxy_demo.ipynb`, producing
`test/output/position_grammar_proxy_demo.executed.ipynb` and
`test/output/position_grammar_proxy_demo.visual.png`.

Expected: command exits 0 and the visual PNG exists.
