# Position Overlay Basemap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the focused position-order notebook readable by drawing the original furniture basemap under group-level position evidence.

**Architecture:** Keep `P_position_fit` computed from `ActivityRegion / RoomScope -> FurnitureGroup positions`. Add only display-context SVG elements to `scene_position_grammar_overlay_svg`, and correct fixture roles so group internals are inspectable without changing the public score layer.

**Tech Stack:** Python, pytest, structured SVG fixtures, notebook execution through existing project scripts.

---

## Grill-Me Self-Check

- If the focused overlay draws only green group boxes and yellow residuals, can the user understand which furniture made the group? No. Add a faint object basemap.
- If yellow slots appear per chair/table, does that violate the matrix proxy design? Yes. Keep yellow slots/residuals at furniture-group level only.
- If SVG chair circles load as tables, can later assembly/debug evidence be trusted? No. Add explicit `data-role` and stable ids to every north table chair.
- If the basemap changes `P_position_fit`, did display leak into scoring? Yes. The basemap must be generated only inside the focused overlay renderer.

## Tasks

- [ ] Add red tests in `test/test_floorplan_scene_loader.py`:
  - north table groups contain exactly one table and four chairs;
  - focused overlay contains `data-layer="position-basemap-object"`;
  - focused overlay still omits `furniture_affordance_extent_`.
- [ ] Update the four SVG fixtures so every `north_table_group_r*_c*` has one table role and four chair roles with stable ids.
- [ ] Add a minimal `_position_basemap_object_svg(obj)` helper in `features/scene_evaluator.py`, then render scene objects before group proxies.
- [ ] Run the new tests first to observe failure, then after implementation run:
  - `pixi run pytest test/test_floorplan_scene_loader.py -q -k "furniture_group or position_grammar or potionNoRotation or position_no_rotation"`
  - `pixi run pytest test/test_order_analyzer_mvp.py -q`
- [ ] Regenerate `test/output/position_grammar_proxy_demo.executed.ipynb`, `.visual.html`, and `.visual.png`.
- [ ] Inspect the visual output: faint objects below, green group proxies above, yellow group slots/residuals only.
