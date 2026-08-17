# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Environment

This project uses **Pixi** (conda-based) for environment management, not pip/venv.

### Blender

When this project needs to invoke Blender, use only the portable installation in `D:\Blender\BlenderPortableLTS5.2`. Do not discover, launch, or configure any other Blender installation. The executable is `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe`.

```bash
# Install Pixi if not already installed, then:
pixi install       # Set up environment from pixi.lock
pixi shell         # Activate the environment
```

The locked environment currently resolves to **Python 3.12.13** under the
`>=3.12,<3.13` constraint in [pixi.toml](pixi.toml).

OCTA toolbox dependencies not listed in pixi.toml but imported in source: `svgwrite`, `svg.path`, `svgpathtools`, `svgutils`, `jsonpickle`, `html2image`, `svglib`, `reportlab`, `colour`, `IPython`, `pandas`, `PIL`, `matplotlib`.

## Tests

```bash
pixi run pytest OCTA_toolbox-master/tests/
pixi run pytest OCTA_toolbox-master/tests/test_pattern.py  # single file
```

## Code Comments

All new or modified project-owned code must use English-first comments at two levels:

- Every function should have a docstring.
- Important computation steps should have comments explaining why the step exists, especially inference, scoring, geometry conversion, graph construction, and adapter handoff logic.

Do not add noisy comments that merely restate obvious assignments. Vendored OCTA toolbox code is exempt unless it is edited.
Short Chinese annotations are allowed when they improve communication, but they supplement rather than replace the English documentation.

## Project Memory

For layout-matrix work, read `docs/indoor_layout_evaluation_matrix_architecture_memory.md` first.
Read `docs/room_analysis_model_development_standard.md` when adding model layers or metrics.
Read `docs/room_analysis_model_interface.md` only when changing the exported `room_analysis_model` shape.
Use `docs/indoor_layout_evaluation_matrix_task_status.md` only as a history ledger; do not load it by default for ordinary feature work.

## Architecture

This project is a **thin wrapper** (`analyzer.py`) around the embedded OCTA toolbox (`OCTA_toolbox-master/`), which is included as source rather than a package dependency.

### `OrderAnalyzer` flow

```
OrderAnalyzer(actual, ideal)
  └── _build_grid()         → octa.Grid (Stimulus subclass)
  └── _apply_matrix()       → maps shape aliases → OCTA shape classes, sets labels
  └── _prepare()            → sets ideal GridPattern, marks deviants
  └── calculate_order()     → stimulus.Render() → CalculatePatternDeviants() → [0.0, 1.0]
  └── report()              → wraps calculate_order() with summary dict
```

Input is a 2D list of `{"shape": ..., "attr": ...}` dicts. Shape aliases: `"rect"`/`"square"` → `Rectangle`, `"circle"`/`"round"` → `Ellipse`.

### OCTA toolbox key classes

- **`Stimulus`** ([OCTA_toolbox-master/octa/Stimulus.py](OCTA_toolbox-master/octa/Stimulus.py)) — 3000+ line base class; owns the element list, SVG/PNG rendering, and all measurement hooks. This is the core engine.
- **`Grid`** — `Stimulus` subclass that builds a rectangular grid from n_rows/n_cols/spacing.
- **`GridPattern`** — Repeats shape/label patterns across grid elements (`RepeatAcrossElements`, `RepeatAcrossRows`, `RepeatAcrossColumns`).
- **Shapes** — `Rectangle`, `Ellipse`, `Triangle`, `Polygon`, `Text`, `Image`, etc., live in [OCTA_toolbox-master/octa/shapes/](OCTA_toolbox-master/octa/shapes/).
- **Measurements** — Order and complexity metrics in [OCTA_toolbox-master/octa/measurements/](OCTA_toolbox-master/octa/measurements/).

### Module layout

```
order_analyzer/
  analyzer.py              ← public API (OrderAnalyzer class)
  __init__.py
  OCTA_toolbox-master/
    octa/
      Stimulus.py          ← core engine (~3000 lines)
      Positions.py
      patterns/
      shapes/
      measurements/
    tests/
```

OCTA is licensed GNU LGPL 3.0. Original authors: Van Geert, Bossens, and Wagemans (2021).
