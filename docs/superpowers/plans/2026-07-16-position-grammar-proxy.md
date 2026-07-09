# Position Grammar Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the runtime group layer from `activity_group` to canonical `FurnitureGroup`, then add `PositionGrammarProxy` with `P_position_fit` and `P_position_confidence`.

**Architecture:** Keep one runtime group system only: `furniture_groups`. SVG/BIM legacy group fields are normalized at the loader/inference boundary. `PositionGrammarProxy` consumes canonical furniture groups plus furniture affordance extents and emits nested grammar evidence; matrix rows expose only two public position variables.

**Tech Stack:** Python stdlib, existing `Rect`, existing `scene_loader` / `scene_inference` / `scene_evaluator`, Pixi pytest, nbformat/nbclient for notebook verification, jj for change management.

---

## Change Strategy

The current working copy is already the jj change `feat: add explicit column-grid relation evidence` and contains many column-grid/spec/SVG edits. Do not implement this plan in that change.

Use a new jj change after the current change is checkpointed:

```powershell
jj status
pixi run pytest test/test_floorplan_scene_loader.py -q -k "column_grid or overlay_draws or dashed_axis"
jj new -m "feat: add position grammar proxy"
```

Do not create a git branch yet. A jj change is the right isolation unit here; create a branch only when publishing or opening a PR.

---

## File Structure

- Modify: `features/scene_loader.py`
  - Preserve explicit `data-furniture-group` / `data-furniture-group-id` on object records.
- Modify: `features/scene_inference.py`
  - Rename runtime `activity_groups` to canonical `furniture_groups`.
  - Preserve current group frame, member, extent, bbox, and internal-network behavior under the new contract.
- Create: `features/position_grammar.py`
  - Pure evidence builder for line/grid/pair/authored position grammar candidates.
- Modify: `features/scene_evaluator.py`
  - Consume `furniture_groups`.
  - Add `P_position_fit` and `P_position_confidence` rows.
  - Export position grammar evidence in adapter payload.
  - Draw slots and residuals in overlay.
- Modify: `test/test_floorplan_scene_loader.py`
  - Update old activity-group assertions to canonical furniture-group assertions.
  - Add focused proxy tests.
- Create: `test/position_grammar_proxy_demo.ipynb`
  - Visual verification over SVG proxy scenes and synthetic shifted/rotated cases.
- Update: `docs/superpowers/specs/2026-07-16-position-grammar-proxy-design.md`
  - Only if implementation discovers a naming mismatch that must be reflected.

---

### Task 1: Canonical FurnitureGroup Runtime Migration

**Files:**
- Modify: `features/scene_inference.py`
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write the failing canonical group test**

Add this test near the existing activity group tests in `test/test_floorplan_scene_loader.py`:

```python
def test_inference_exposes_canonical_furniture_groups_without_activity_groups():
    """Runtime inference should expose one canonical furniture-group system."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    evidence = infer_scene_evidence(scene)

    assert "furniture_groups" in evidence
    assert "activity_groups" not in evidence
    assert len(evidence["furniture_groups"]) >= 5
    group = {
        item["id"]: item
        for item in evidence["furniture_groups"]
    }["furniture_group_center_lounge"]
    assert group["metadata"]["level"] == "furniture_group"
    assert group["activity_region_id"] == "center_lounge"
    assert group["member_ids"]
    assert group["furniture_affordance_extent_ids"]
    assert "group-axis-angle" in group["metadata"]
```

- [ ] **Step 2: Run the failing test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_inference_exposes_canonical_furniture_groups_without_activity_groups -q
```

Expected: FAIL because `infer_scene_evidence()` still returns `activity_groups`.

- [ ] **Step 3: Rename the inference runtime collection**

In `features/scene_inference.py`, replace the top-level inference flow with:

```python
def infer_scene_evidence(scene: dict) -> dict:
    """Infer analysis evidence from a neutral scene, independent of SVG loading."""
    zones = affordance_zones(scene)
    extents = furniture_affordance_extents(scene)
    groups = furniture_groups(scene, extents)
    candidates = inferred_region_candidates(scene)
    regions = inferred_regions(scene, candidates)
    gap_paths = inferred_region_gap_paths(candidates)
    networks = spatial_networks(groups, gap_paths)
    boundaries = boundary_semantics(scene)
    return {
        "affordance_zones": zones,
        "furniture_affordance_extents": extents,
        "furniture_groups": groups,
        "inferred_region_candidates": candidates,
        "inferred_regions": regions,
        "inferred_region_gap_paths": gap_paths,
        "spatial_networks": networks,
        "boundary_semantics": boundaries,
        "inferred_region_gap_path_graph": build_inferred_region_gap_path_graph(
            candidates,
            gap_paths,
            scene=scene,
        ),
    }
```

Rename `activity_groups()` to `furniture_groups()` and change the emitted record shape:

```python
def furniture_groups(scene: dict, extents: list[dict] | None = None) -> list[dict]:
    """Build canonical furniture groups from authored semantic keys and extents."""
    extents = extents if extents is not None else furniture_affordance_extents(scene)
    objects_by_id = {obj["id"]: obj for obj in scene.get("objects", [])}
    extents_by_region: dict[str, list[dict]] = {}
    for extent in extents:
        region = _analysis_region_key(extent)
        if not region:
            continue
        extents_by_region.setdefault(region, []).append(extent)
    groups = []
    for region, region_extents in sorted(extents_by_region.items()):
        sorted_extents = sorted(region_extents, key=lambda item: item["id"])
        group_rect = _bounds(sorted_extents)
        members = [
            objects_by_id[extent["object_id"]]
            for extent in sorted_extents
            if extent["object_id"] in objects_by_id
        ]
        frame = _activity_group_frame(members, sorted_extents)
        groups.append(
            {
                "id": f"furniture_group_{region}",
                "activity_region_id": region,
                "region": region,
                "member_ids": sorted(extent["object_id"] for extent in sorted_extents),
                "furniture_affordance_extent_ids": [
                    extent["id"] for extent in sorted_extents
                ],
                "rect": group_rect,
                "bbox": _rect_bbox(group_rect),
                "overlap_evidence": _extent_overlap_evidence(sorted_extents),
                "metadata": {
                    "level": "furniture_group",
                    "source": "semantic_region_grouped_furniture_affordance_extents",
                    "geometry_basis": "union_envelope_of_member_furniture_affordance_extents",
                    **_group_frame_metadata(frame),
                },
            }
        )
    return groups
```

Rename helper `_activity_group_internal_edges()` to `_furniture_group_internal_edges()` and update `spatial_networks()`:

```python
def spatial_networks(furniture_groups: list[dict], gap_paths: list[dict]) -> list[dict]:
    """Build shared-schema spatial networks for internal and inter-region scopes."""
    networks = [
        {
            "id": f"spatial_network_region_internal_{group['activity_region_id']}",
            "scope": "region_internal",
            "nodes": [
                {
                    "id": extent_id,
                    "kind": "furniture_affordance_extent",
                }
                for extent_id in group["furniture_affordance_extent_ids"]
            ],
            "edges": _furniture_group_internal_edges(group),
            "components": [[extent_id] for extent_id in group["furniture_affordance_extent_ids"]],
            "metadata": {
                "method": "furniture_group_member_extent_network_skeleton",
                "furniture_group_id": group["id"],
            },
        }
        for group in furniture_groups
    ]
    region_node_ids = sorted(
        {
            region_id
            for path in gap_paths
            for region_id in (path["region_a"], path["region_b"])
        }
    )
    # Continue with the existing inter-region gap-path adjacency construction,
    # using `networks.append(...)` to add the inter-region network after the
    # canonical furniture-group internal networks above.
```

- [ ] **Step 4: Update evaluator runtime consumers**

In `features/scene_evaluator.py`, replace local variables and returned keys:

```python
furniture_groups = inference["furniture_groups"]
```

Replace returned matrix key:

```python
"furniture_groups": furniture_groups,
```

Replace `_adapter_payload(...)` argument name from `activity_groups` to `furniture_groups`.

Rename `_activity_group_evidence()` to `_furniture_group_evidence()`:

```python
def _furniture_group_evidence(group: dict) -> dict:
    """Return adapter-safe furniture group evidence without Rect objects."""
    return {
        "id": group["id"],
        "activity_region_id": group["activity_region_id"],
        "region": group["region"],
        "member_ids": list(group["member_ids"]),
        "furniture_affordance_extent_ids": list(group["furniture_affordance_extent_ids"]),
        "bbox": _rect_bbox(group["rect"]),
        "overlap_evidence": list(group["overlap_evidence"]),
        "metadata": dict(group["metadata"]),
    }
```

In adapter payload evidence geometry, replace:

```python
"activity_groups": {
    "count": len(activity_groups),
    "items": [
        _activity_group_evidence(group)
        for group in activity_groups
    ],
},
```

with:

```python
"furniture_groups": {
    "count": len(furniture_groups),
    "items": [
        _furniture_group_evidence(group)
        for group in furniture_groups
    ],
},
```

- [ ] **Step 5: Update tests that assert old names**

Replace old assertions in `test/test_floorplan_scene_loader.py`:

```python
evidence["activity_groups"]
matrix["activity_groups"]
matrix["adapter_payload"]["evidence_geometry"]["activity_groups"]
"activity_group_"
"activity_group"
"activity_group_frame_mean"
```

with canonical equivalents:

```python
evidence["furniture_groups"]
matrix["furniture_groups"]
matrix["adapter_payload"]["evidence_geometry"]["furniture_groups"]
"furniture_group_"
"furniture_group"
"furniture_group_frame_mean"
```

For existing region metadata assertions, update `axis-basis` expected values from:

```python
"activity_group_frame_mean"
```

to:

```python
"furniture_group_frame_mean"
```

Update `_attach_region_axis_metadata()` metadata string accordingly:

```python
"axis-basis": "furniture_group_frame_mean",
```

- [ ] **Step 6: Run focused migration tests**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "furniture_group or activity_group or spatial_network"
```

Expected: PASS after all old runtime assertions are migrated.

---

### Task 2: SVG Loader Furniture Group Alias

**Files:**
- Modify: `features/scene_loader.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write the failing loader test**

Add:

```python
def test_svg_loader_preserves_explicit_furniture_group_id(tmp_path):
    """SVG proxy group labels should normalize into furniture_group metadata."""
    svg = tmp_path / "furniture_group.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect id="table" data-role="table" data-region="dining" data-furniture-group="dining_set_1" x="10" y="10" width="20" height="10" />
  <rect id="chair" data-role="chair" data-region="dining" data-furniture-group="dining_set_1" x="10" y="30" width="20" height="10" />
</svg>""",
        encoding="utf-8",
    )

    scene = load_structured_svg_scene(svg)

    assert {obj["metadata"]["furniture-group"] for obj in scene["objects"]} == {
        "dining_set_1"
    }
    assert {obj["furniture_group"] for obj in scene["objects"]} == {"dining_set_1"}
```

- [ ] **Step 2: Run the failing loader test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_svg_loader_preserves_explicit_furniture_group_id -q
```

Expected: FAIL because object records do not yet expose `furniture_group`.

- [ ] **Step 3: Implement neutral furniture group field**

In `features/scene_loader.py`, inside `_shape_record()`, after `metadata` is built, add:

```python
    furniture_group = (
        meta.get("data-furniture-group")
        or meta.get("data-furniture-group-id")
        or metadata.get("furniture-group")
        or metadata.get("furniture-group-id")
        or group
    )
    if "furniture-group" not in metadata:
        metadata["furniture-group"] = furniture_group
```

Then add this field to the returned record:

```python
        "furniture_group": furniture_group,
```

- [ ] **Step 4: Route furniture extents through the canonical group key**

In `features/scene_inference.py`, update `_furniture_affordance_extent_record()` to include:

```python
        "furniture_group": record.get("furniture_group") or _analysis_region_key(record),
```

Add helper:

```python
def _furniture_group_key(record: dict) -> str:
    """Return the authored furniture-group key used for canonical grouping."""
    metadata = record.get("metadata", {})
    neutral = {"", "global", "room", "misc", "room_misc", None}
    key = record.get("furniture_group") or metadata.get("furniture-group")
    if key not in neutral:
        return str(key)
    return _analysis_region_key(record)
```

Use `_furniture_group_key(extent)` in `furniture_groups()` instead of `_analysis_region_key(extent)` when grouping extents.

- [ ] **Step 5: Run loader and group tests**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_svg_loader_preserves_explicit_furniture_group_id test/test_floorplan_scene_loader.py::test_inference_exposes_canonical_furniture_groups_without_activity_groups -q
```

Expected: PASS.

---

### Task 3: Position Grammar Evidence Module

**Files:**
- Create: `features/position_grammar.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write line-fit failing test**

Add:

```python
def test_position_grammar_line_fit_drops_for_shifted_member():
    """Line grammar should penalize a shifted member while keeping one public fit."""
    from features.position_grammar import position_grammar_evidence

    group = {
        "id": "furniture_group_row",
        "activity_region_id": "row",
        "rect": Rect(cx=100, cy=50, width=200, height=40),
        "furniture_affordance_extent_ids": ["a", "b", "c"],
        "metadata": {
            "group-axis-angle": "0",
            "group-axis-strength": "1.0",
            "group-axis-basis": "test",
        },
    }
    regular = [
        {"id": "a", "rect": Rect(cx=0, cy=50, width=20, height=20)},
        {"id": "b", "rect": Rect(cx=100, cy=50, width=20, height=20)},
        {"id": "c", "rect": Rect(cx=200, cy=50, width=20, height=20)},
    ]
    shifted = [
        {"id": "a", "rect": Rect(cx=0, cy=50, width=20, height=20)},
        {"id": "b", "rect": Rect(cx=100, cy=75, width=20, height=20)},
        {"id": "c", "rect": Rect(cx=200, cy=50, width=20, height=20)},
    ]

    regular_fit = position_grammar_evidence([group], regular)["items"][0]
    shifted_fit = position_grammar_evidence([group], shifted)["items"][0]

    assert regular_fit["position-grammar-type"] == "line"
    assert regular_fit["position-fit"] > shifted_fit["position-fit"]
    assert shifted_fit["position-residual-mean"] > 0
```

- [ ] **Step 2: Run the failing line-fit test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_grammar_line_fit_drops_for_shifted_member -q
```

Expected: FAIL because `features.position_grammar` does not exist.

- [ ] **Step 3: Create minimal module with line/grid candidates**

Create `features/position_grammar.py`:

```python
from __future__ import annotations

from math import cos, hypot, radians, sin
from statistics import mean, pstdev


def position_grammar_evidence(
    furniture_groups: list[dict],
    extents: list[dict],
) -> dict:
    """Build internal position grammar evidence for canonical furniture groups."""
    extents_by_id = {extent["id"]: extent for extent in extents}
    items = []
    for group in furniture_groups:
        members = [
            extents_by_id[extent_id]
            for extent_id in group.get("furniture_affordance_extent_ids", [])
            if extent_id in extents_by_id
        ]
        evidence = _group_position_evidence(group, members)
        if evidence is not None:
            items.append(evidence)
    return {
        "method": "local_frame_position_grammar_proxy",
        "items": items,
    }


def _group_position_evidence(group: dict, members: list[dict]) -> dict | None:
    """Return the simplest available position grammar evidence for one group."""
    if len(members) < 2:
        return None
    frame = _group_frame(group)
    if frame is None:
        return None
    coords = [
        {
            "id": member["id"],
            "x": member["rect"].cx,
            "y": member["rect"].cy,
            "u": u,
            "v": v,
            "scale": max(member["rect"].width, member["rect"].height, 1e-9),
        }
        for member in members
        for u, v in [_project(member["rect"].cx, member["rect"].cy, group["rect"].cx, group["rect"].cy, frame["angle"])]
    ]
    line = _line_candidate(group, coords, frame)
    grid = _grid_candidate(group, coords, frame)
    candidates = [item for item in [line, grid] if item is not None]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (-item["position-fit"], item["complexity"]))[0]


def _group_frame(group: dict) -> dict | None:
    """Read the local frame from canonical group metadata."""
    raw = group.get("metadata", {}).get("group-axis-angle")
    if raw is None:
        return None
    try:
        return {
            "angle": float(raw) % 180.0,
            "basis": group.get("metadata", {}).get("group-axis-basis", "group-axis"),
        }
    except ValueError:
        return None


def _project(x: float, y: float, cx: float, cy: float, angle: float) -> tuple[float, float]:
    """Project scene coordinates into a local u/v frame."""
    theta = radians(angle)
    ux, uy = cos(theta), sin(theta)
    vx, vy = -uy, ux
    dx, dy = x - cx, y - cy
    return dx * ux + dy * uy, dx * vx + dy * vy


def _unproject(u: float, v: float, cx: float, cy: float, angle: float) -> tuple[float, float]:
    """Map local u/v coordinates back to scene coordinates."""
    theta = radians(angle)
    ux, uy = cos(theta), sin(theta)
    vx, vy = -uy, ux
    return cx + u * ux + v * vx, cy + u * uy + v * vy


def _line_candidate(group: dict, coords: list[dict], frame: dict) -> dict:
    """Score one-axis spacing plus cross-axis residual."""
    ordered = sorted(coords, key=lambda item: item["u"])
    gaps = [b["u"] - a["u"] for a, b in zip(ordered, ordered[1:])]
    gap_scale = _stable_scale(gaps, coords, group)
    v_center = mean(item["v"] for item in coords)
    residuals = [
        _residual_record(
            item,
            item["u"],
            v_center,
            group,
            frame,
            gap_scale,
        )
        for item in coords
    ]
    gap_score = _cv_score(gaps)
    residual_fit = _fit(mean(item["normalized"] for item in residuals))
    fit = min(gap_score, residual_fit)
    return _evidence(group, frame, "line", fit, residuals, len(coords), len(coords), complexity=1)


def _grid_candidate(group: dict, coords: list[dict], frame: dict) -> dict | None:
    """Score a local u/v row-column slot explanation."""
    if len(coords) < 4:
        return None
    columns = _cluster_axis([item["u"] for item in coords])
    rows = _cluster_axis([item["v"] for item in coords])
    if len(columns) < 2 or len(rows) < 2:
        return None
    scale = _stable_scale(
        [b - a for a, b in zip(sorted(columns), sorted(columns)[1:])]
        + [b - a for a, b in zip(sorted(rows), sorted(rows)[1:])],
        coords,
        group,
    )
    residuals = []
    for item in coords:
        u_slot = min(columns, key=lambda value: abs(item["u"] - value))
        v_slot = min(rows, key=lambda value: abs(item["v"] - value))
        residuals.append(
            _residual_record(
                item,
                u_slot,
                v_slot,
                group,
                frame,
                scale,
            )
        )
    return _evidence(
        group,
        frame,
        "grid",
        _fit(mean(item["normalized"] for item in residuals)),
        residuals,
        len(coords),
        len(columns) * len(rows),
        complexity=3,
    )


def _cluster_axis(values: list[float]) -> list[float]:
    """Split sorted coordinates into simple clusters using the largest gaps."""
    ordered = sorted(values)
    if len(ordered) < 2:
        return ordered
    gaps = [b - a for a, b in zip(ordered, ordered[1:])]
    positive = [gap for gap in gaps if gap > 1e-9]
    if not positive:
        return [mean(ordered)]
    threshold = mean(positive) * 0.5
    clusters = [[ordered[0]]]
    for value, gap in zip(ordered[1:], gaps):
        if gap > threshold:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return [mean(cluster) for cluster in clusters]


def _residual_record(
    item: dict,
    slot_u: float,
    slot_v: float,
    group: dict,
    frame: dict,
    scale: float,
) -> dict:
    """Return member-to-slot residual evidence in local and scene coordinates."""
    slot_x, slot_y = _unproject(
        slot_u,
        slot_v,
        group["rect"].cx,
        group["rect"].cy,
        frame["angle"],
    )
    distance = hypot(item["u"] - slot_u, item["v"] - slot_v)
    return {
        "id": item["id"],
        "x": round(item["x"], 4),
        "y": round(item["y"], 4),
        "slot_x": round(slot_x, 4),
        "slot_y": round(slot_y, 4),
        "du": round(item["u"] - slot_u, 4),
        "dv": round(item["v"] - slot_v, 4),
        "distance": round(distance, 4),
        "normalized": round(distance / scale, 4),
    }


def _stable_scale(gaps: list[float], coords: list[dict], group: dict) -> float:
    """Choose a local positive scale for normalized residuals."""
    positive = [abs(gap) for gap in gaps if abs(gap) > 1e-9]
    if positive:
        return max(mean(positive), 1e-9)
    member_scale = mean(item["scale"] for item in coords)
    return max(member_scale, group["rect"].width, group["rect"].height, 1e-9)


def _cv_score(values: list[float]) -> float:
    """Return inverse coefficient-of-variation regularity."""
    if len(values) < 2:
        return 1.0
    avg = mean(values)
    if abs(avg) < 1e-9:
        return 0.0
    return 1.0 / (1.0 + pstdev(values) / abs(avg))


def _fit(mean_residual: float) -> float:
    """Map normalized residual to a bounded fit score."""
    return 1.0 / (1.0 + max(0.0, mean_residual))


def _confidence(grammar: str, member_count: int, slot_count: int, fit: float) -> float:
    """Return reliability evidence for the selected grammar."""
    count_score = min(1.0, member_count / (4.0 if grammar == "grid" else 3.0))
    slot_score = 1.0 / (1.0 + abs(slot_count - member_count) / max(member_count, 1))
    return round(min(1.0, fit * 0.5 + count_score * 0.3 + slot_score * 0.2), 4)


def _evidence(
    group: dict,
    frame: dict,
    grammar: str,
    fit: float,
    residuals: list[dict],
    member_count: int,
    slot_count: int,
    *,
    complexity: int,
) -> dict:
    """Create one adapter-safe grammar evidence record."""
    mean_residual = mean(item["normalized"] for item in residuals)
    return {
        "id": f"position_grammar_{group['id']}",
        "subject_id": group["id"],
        "subject_kind": "furniture_group",
        "position-frame-angle": round(frame["angle"], 4),
        "position-frame-basis": frame["basis"],
        "position-grammar-type": grammar,
        "position-fit": round(fit, 4),
        "position-confidence": _confidence(grammar, member_count, slot_count, fit),
        "position-residual-mean": round(mean_residual, 4),
        "position-residual-max": round(max(item["normalized"] for item in residuals), 4),
        "position-member-count": member_count,
        "position-slot-count": slot_count,
        "position-system-id": f"{group['id']}__{grammar}",
        "slots": [],
        "assignments": [item["id"] for item in residuals],
        "residuals": residuals,
        "complexity": complexity,
    }
```

- [ ] **Step 4: Run line-fit test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_grammar_line_fit_drops_for_shifted_member -q
```

Expected: PASS.

- [ ] **Step 5: Add rotated local-frame grid test**

Add:

```python
def test_position_grammar_grid_uses_local_frame_not_global_xy():
    """Rotated grids should fit in local u/v coordinates."""
    from features.position_grammar import position_grammar_evidence

    group = {
        "id": "furniture_group_rotated_grid",
        "activity_region_id": "rotated_grid",
        "rect": Rect(cx=100, cy=100, width=160, height=160),
        "furniture_affordance_extent_ids": ["a", "b", "c", "d"],
        "metadata": {
            "group-axis-angle": "45",
            "group-axis-strength": "1.0",
            "group-axis-basis": "test",
        },
    }
    extents = [
        {"id": "a", "rect": Rect(cx=100, cy=57.57, width=12, height=12)},
        {"id": "b", "rect": Rect(cx=142.43, cy=100, width=12, height=12)},
        {"id": "c", "rect": Rect(cx=57.57, cy=100, width=12, height=12)},
        {"id": "d", "rect": Rect(cx=100, cy=142.43, width=12, height=12)},
    ]

    item = position_grammar_evidence([group], extents)["items"][0]

    assert item["position-grammar-type"] == "grid"
    assert item["position-fit"] > 0.95
    assert item["position-frame-angle"] == 45.0
```

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_grammar_grid_uses_local_frame_not_global_xy -q
```

Expected: PASS.

---

### Task 4: Complete Authored And Pair Grammars

**Files:**
- Modify: `features/position_grammar.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Add failing authored grammar test**

Add:

```python
def test_position_grammar_uses_authored_slots_when_available():
    """Authored slots should win over inferred grammar when complete."""
    from features.position_grammar import position_grammar_evidence

    group = {
        "id": "furniture_group_authored",
        "activity_region_id": "authored",
        "rect": Rect(cx=50, cy=50, width=100, height=100),
        "furniture_affordance_extent_ids": ["a", "b"],
        "metadata": {
            "group-axis-angle": "0",
            "group-axis-basis": "test",
            "position-slots": "a:0,0;b:50,0",
        },
    }
    extents = [
        {"id": "a", "rect": Rect(cx=50, cy=50, width=10, height=10)},
        {"id": "b", "rect": Rect(cx=100, cy=50, width=10, height=10)},
    ]

    item = position_grammar_evidence([group], extents)["items"][0]

    assert item["position-grammar-type"] == "authored"
    assert item["position-fit"] == 1.0
    assert item["position-confidence"] > 0.9
```

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_grammar_uses_authored_slots_when_available -q
```

Expected: FAIL before authored grammar exists.

- [ ] **Step 2: Add failing pair grammar test**

Add:

```python
def test_position_grammar_pair_scores_matched_offsets():
    """Pair grammar should explain two symmetric members around the local center."""
    from features.position_grammar import position_grammar_evidence

    group = {
        "id": "furniture_group_pair",
        "activity_region_id": "pair",
        "rect": Rect(cx=100, cy=100, width=120, height=60),
        "furniture_affordance_extent_ids": ["left", "right"],
        "metadata": {
            "group-axis-angle": "0",
            "group-axis-basis": "test",
        },
    }
    extents = [
        {"id": "left", "rect": Rect(cx=70, cy=100, width=20, height=20)},
        {"id": "right", "rect": Rect(cx=130, cy=100, width=20, height=20)},
    ]

    item = position_grammar_evidence([group], extents)["items"][0]

    assert item["position-grammar-type"] == "pair"
    assert item["position-fit"] > 0.95
```

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_grammar_pair_scores_matched_offsets -q
```

Expected: FAIL before pair grammar exists.

- [ ] **Step 3: Add authored candidate**

In `features/position_grammar.py`, add this candidate before line/grid selection:

```python
def _authored_candidate(group: dict, coords: list[dict], frame: dict) -> dict | None:
    """Score authored local slots when complete member-slot metadata exists."""
    raw = group.get("metadata", {}).get("position-slots")
    if not raw:
        return None
    slots = {}
    for chunk in raw.split(";"):
        if not chunk.strip() or ":" not in chunk:
            return None
        member_id, pair = chunk.split(":", 1)
        values = pair.split(",")
        if len(values) != 2:
            return None
        try:
            slots[member_id.strip()] = (float(values[0]), float(values[1]))
        except ValueError:
            return None
    if {item["id"] for item in coords} - set(slots):
        return None
    scale = _stable_scale([], coords, group)
    residuals = [
        _residual_record(
            item,
            slots[item["id"]][0],
            slots[item["id"]][1],
            group,
            frame,
            scale,
        )
        for item in coords
    ]
    return _evidence(
        group,
        frame,
        "authored",
        _fit(mean(item["normalized"] for item in residuals)),
        residuals,
        len(coords),
        len(slots),
        complexity=0,
    )
```

In `_group_position_evidence()`, include it before inferred candidates:

```python
    authored = _authored_candidate(group, coords, frame)
    if authored is not None:
        return authored
    pair = _pair_candidate(group, coords, frame)
    if len(coords) == 2 and pair is not None:
        return pair
    line = _line_candidate(group, coords, frame)
    grid = _grid_candidate(group, coords, frame)
    candidates = [item for item in [line, pair, grid] if item is not None]
```

- [ ] **Step 4: Add pair candidate**

Add:

```python
def _pair_candidate(group: dict, coords: list[dict], frame: dict) -> dict | None:
    """Score two-member matched offsets around the local origin."""
    if len(coords) != 2:
        return None
    first, second = coords
    slot_a = (-abs(first["u"]), mean([first["v"], second["v"]]))
    slot_b = (abs(first["u"]), mean([first["v"], second["v"]]))
    if abs(second["u"]) < abs(first["u"]):
        slot_a, slot_b = slot_b, slot_a
    scale = _stable_scale([abs(first["u"] - second["u"])], coords, group)
    residuals = [
        _residual_record(first, slot_a[0], slot_a[1], group, frame, scale),
        _residual_record(second, slot_b[0], slot_b[1], group, frame, scale),
    ]
    return _evidence(
        group,
        frame,
        "pair",
        _fit(mean(item["normalized"] for item in residuals)),
        residuals,
        len(coords),
        2,
        complexity=2,
    )
```

- [ ] **Step 5: Run authored and pair tests**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_position_grammar_uses_authored_slots_when_available test/test_floorplan_scene_loader.py::test_position_grammar_pair_scores_matched_offsets -q
```

Expected: PASS.

---

### Task 5: Matrix Rows And Adapter Payload

**Files:**
- Modify: `features/scene_evaluator.py`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing evaluator row test**

Add:

```python
def test_evaluator_emits_position_grammar_rows():
    """Matrix should expose only fit and confidence as public position variables."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))

    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}

    assert rows["P_position_fit"]["view_id"] == "internal_order"
    assert rows["P_position_fit"]["status"] == "computed"
    assert rows["P_position_confidence"]["view_id"] == "internal_order"
    assert rows["P_position_confidence"]["status"] == "computed"
    assert "position_grammar_evidence" in rows["P_position_fit"]
    assert "line_fit" not in rows
    assert "grid_fit" not in rows
    assert "pair_fit" not in rows
```

- [ ] **Step 2: Run failing evaluator row test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_evaluator_emits_position_grammar_rows -q
```

Expected: FAIL because rows are not emitted.

- [ ] **Step 3: Wire position evidence into evaluator**

In `features/scene_evaluator.py`, import:

```python
from .position_grammar import position_grammar_evidence
```

After `furniture_groups` and `furniture_affordance_extents` are read:

```python
position_grammar = position_grammar_evidence(
    furniture_groups,
    furniture_affordance_extents,
)
```

Append rows after `_furniture_affordance_extent_row(...)`:

```python
rows.extend(_position_grammar_rows(position_grammar))
```

Add helper:

```python
def _position_grammar_rows(position_grammar: dict) -> list[dict]:
    """Expose compact public position-order variables from grammar evidence."""
    items = position_grammar.get("items", [])
    if not items:
        return [
            _not_available(
                "internal_order",
                "P_position_fit",
                "needs canonical furniture groups with measurable local position evidence",
            ),
            _not_available(
                "internal_order",
                "P_position_confidence",
                "needs canonical furniture groups with measurable local position evidence",
            ),
        ]
    return [
        {
            "view_id": "internal_order",
            "metric": "P_position_fit",
            "score": round(mean(item["position-fit"] for item in items), 4),
            "status": "computed",
            "method": "position_grammar_proxy_selected_fit_mean",
            "evidence": [item["id"] for item in items],
            "position_grammar_evidence": items,
            "uncertainty": "position grammar is internal evidence only; final perceptual weight is deferred to experiments",
        },
        {
            "view_id": "internal_order",
            "metric": "P_position_confidence",
            "score": round(mean(item["position-confidence"] for item in items), 4),
            "status": "computed",
            "method": "position_grammar_proxy_confidence_mean",
            "evidence": [item["id"] for item in items],
            "position_grammar_evidence": items,
            "uncertainty": "confidence describes evidence reliability, not design quality",
        },
    ]
```

Include in returned matrix:

```python
"position_grammar": position_grammar,
```

Include in adapter payload evidence geometry:

```python
"position_grammar": position_grammar,
```

- [ ] **Step 4: Run evaluator row test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_evaluator_emits_position_grammar_rows -q
```

Expected: PASS.

---

### Task 6: Overlay And Notebook Verification

**Files:**
- Modify: `features/scene_evaluator.py`
- Create: `test/position_grammar_proxy_demo.ipynb`
- Test: `test/test_floorplan_scene_loader.py`

- [ ] **Step 1: Write failing overlay test**

Add:

```python
def test_overlay_draws_position_grammar_residuals():
    """Overlay should expose selected position grammar residual vectors."""
    scene = load_structured_svg_scene(Path("test/SVG_baseline.svg"))
    matrix = evaluate_scene(scene)

    svg = scene_metric_overlay_svg(scene, matrix)

    assert 'data-layer="position-grammar-residual"' in svg
    assert 'data-layer="position-grammar-slot"' in svg
```

- [ ] **Step 2: Run failing overlay test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_overlay_draws_position_grammar_residuals -q
```

Expected: FAIL because overlay layers do not exist.

- [ ] **Step 3: Add minimal overlay layers**

In `scene_metric_overlay_svg()`, after existing region trend/column layers are built, collect:

```python
    for item in matrix.get("position_grammar", {}).get("items", []):
        for residual in item.get("residuals", []):
            group = next(
                (
                    group
                    for group in matrix.get("furniture_groups", [])
                    if group["id"] == item["subject_id"]
                ),
                None,
            )
            if group is None:
                continue
            extent = next(
                (
                    extent
                    for extent in matrix.get("furniture_affordance_extents", [])
                    if extent["id"] == residual["id"]
                ),
                None,
            )
            if extent is None:
                continue
            region_layers.append(
                f'<circle data-layer="position-grammar-slot" '
                f'data-system="{escape(item["position-system-id"])}" '
                f'data-member="{escape(residual["id"])}" '
                f'cx="{residual["slot_x"]:.1f}" cy="{residual["slot_y"]:.1f}" r="4" '
                f'fill="#f59e0b" opacity="0.75">'
                f'<title>{escape(item["position-grammar-type"])} '
                f'{residual["normalized"]:.4f}</title></circle>'
            )
            if residual["distance"] > 0:
                region_layers.append(
                    f'<line data-layer="position-grammar-residual" '
                    f'data-system="{escape(item["position-system-id"])}" '
                    f'data-member="{escape(residual["id"])}" '
                    f'x1="{residual["x"]:.1f}" y1="{residual["y"]:.1f}" '
                    f'x2="{residual["slot_x"]:.1f}" y2="{residual["slot_y"]:.1f}" '
                    f'stroke="#f59e0b" stroke-width="2" opacity="0.7" />'
                )
```

- [ ] **Step 4: Run overlay test**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py::test_overlay_draws_position_grammar_residuals -q
```

Expected: PASS.

- [ ] **Step 5: Create notebook**

Create `test/position_grammar_proxy_demo.ipynb` with cells:

```python
from pathlib import Path
from IPython.display import SVG, display

from features.scene_loader import load_structured_svg_scene
from features.scene_evaluator import evaluate_scene, scene_metric_overlay_svg

fixtures = [
    Path("test/SVG_baseline.svg"),
    Path("test/SVG_oblique.svg"),
    Path("test/SVG_chaoticsvg.svg"),
]

for path in fixtures:
    scene = load_structured_svg_scene(path)
    matrix = evaluate_scene(scene)
    rows = {row["metric"]: row for row in matrix["rows"]}
    print(
        path.name,
        "groups=", len(matrix.get("furniture_groups", [])),
        "fit=", rows["P_position_fit"]["score"],
        "confidence=", rows["P_position_confidence"]["score"],
    )
    display(SVG(data=scene_metric_overlay_svg(scene, matrix)))
```

- [ ] **Step 6: Execute notebook and screenshot**

Run:

```powershell
@'
import nbformat
from nbclient import NotebookClient
from pathlib import Path
source = Path("test/position_grammar_proxy_demo.ipynb")
out = Path("test/output/position_grammar_proxy_demo.executed.ipynb")
nb = nbformat.read(source, as_version=4)
NotebookClient(nb, timeout=120, kernel_name="python3").execute()
out.parent.mkdir(parents=True, exist_ok=True)
nbformat.write(nb, out)
print(out)
'@ | pixi run python -
```

Expected: writes `test/output/position_grammar_proxy_demo.executed.ipynb`.

Render HTML:

```powershell
@'
import html
from pathlib import Path
import nbformat

nb = nbformat.read("test/output/position_grammar_proxy_demo.executed.ipynb", as_version=4)
parts = [
    '<!doctype html><meta charset="utf-8"><title>Position Grammar Proxy Demo</title>',
    '<style>body{font-family:Arial,sans-serif;margin:24px;background:#f8fafc;color:#0f172a} .cell{margin:0 0 28px} pre{white-space:pre-wrap;background:#e2e8f0;padding:10px;border-radius:6px} svg{max-width:100%;height:auto;background:white;border:1px solid #cbd5e1;margin-top:8px}</style>',
]
for cell in nb.cells:
    if cell.cell_type == "markdown":
        title = cell.source.splitlines()[0].lstrip("# ") if cell.source else "Markdown"
        parts.append(f'<section class="cell"><h2>{html.escape(title)}</h2></section>')
        continue
    outputs = cell.get("outputs", [])
    if not outputs:
        continue
    parts.append('<section class="cell">')
    for output in outputs:
        if output.output_type == "stream":
            parts.append(f"<pre>{html.escape(output.text)}</pre>")
        data = output.get("data", {})
        if "image/svg+xml" in data:
            svg = data["image/svg+xml"]
            parts.append(svg if isinstance(svg, str) else "".join(svg))
        elif "text/plain" in data:
            text = data["text/plain"]
            parts.append(f'<pre>{html.escape(text if isinstance(text, str) else "".join(text))}</pre>')
    parts.append("</section>")

out = Path("test/output/position_grammar_proxy_demo.visual.html")
out.write_text("\\n".join(parts), encoding="utf-8")
print(out)
'@ | pixi run python -
```

Expected: writes `test/output/position_grammar_proxy_demo.visual.html`.

Capture screenshot:

```powershell
npx playwright screenshot --full-page "file:///D:/PROJECTS/understandOtherPackage/order_analyzer/test/output/position_grammar_proxy_demo.visual.html" test/output/position_grammar_proxy_demo.visual.png
```

Expected: writes `test/output/position_grammar_proxy_demo.visual.png`.

---

### Task 7: Full Focused Verification

**Files:**
- All modified files

- [ ] **Step 1: Scan for forbidden runtime double-system naming**

Run:

```powershell
rg -n 'activity_groups|activity_group_' features test -g '*.py'
```

Expected: no runtime references. If `activity_group` remains only in historical docs, leave docs alone. In code/tests, replace remaining references with `furniture_groups` / `furniture_group_`.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
pixi run pytest test/test_floorplan_scene_loader.py -q -k "furniture_group or position_grammar or spatial_network or column_grid"
```

Expected: PASS.

- [ ] **Step 3: Run existing MVP analyzer tests**

Run:

```powershell
pixi run pytest test/test_order_analyzer_mvp.py -q
```

Expected: PASS. This guards the old `positions` feature from being accidentally changed.

- [ ] **Step 4: Final jj status**

Run:

```powershell
jj status
jj describe -m "feat: add position grammar proxy"
```

Expected: one jj change containing only the FurnitureGroup migration, PositionGrammarProxy, tests, notebook, and related docs.
