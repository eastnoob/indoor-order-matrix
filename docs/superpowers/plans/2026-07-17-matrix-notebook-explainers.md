# Matrix Notebook Explainers Implementation Plan

> **For agentic workers:** Use the current session directly; this is a documentation/notebook task with no core logic change.

**Goal:** Produce two clear executed notebooks that explain the existing evaluation matrix families.

**Architecture:** Reuse `load_structured_svg_scene()`, `evaluate_scene()`, and existing evidence rows. Notebook-local SVG helpers draw only the relevant model layer.

**Tech Stack:** Python, nbformat, nbclient, IPython SVG display, pandas.

---

### Task 1: Axis / Orientation Notebook

**Files:**
- Create: `test/axis_orientation_metrics_explained.ipynb`

- [ ] Add Markdown explaining the region-axis model.
- [ ] Add notebook-local SVG helper for regions, furniture groups, axes, and column axes.
- [ ] Add metric explanation and actual row summary tables.
- [ ] Execute notebook and verify outputs render.

### Task 2: Position / Order Notebook

**Files:**
- Create: `test/position_order_metrics_explained.ipynb`

- [ ] Add Markdown explaining local position grammar.
- [ ] Reuse `scene_position_grammar_overlay_svg()` for slots/residuals.
- [ ] Add metric explanation and per-group evidence tables.
- [ ] Execute notebook and verify outputs render.

### Task 3: Verification

- [ ] Run notebook execution for both files.
- [ ] Run a small pytest subset that covers metric rows and focused overlay.
