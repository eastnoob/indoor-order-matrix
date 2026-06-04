# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Environment

This project uses **Pixi** (conda-based) for environment management, not pip/venv.

```bash
# Install Pixi if not already installed, then:
pixi install       # Set up environment from pixi.lock
pixi shell         # Activate the environment
```

The locked Python version is **3.14.4** (see [pixi.toml](pixi.toml)).

OCTA toolbox dependencies not listed in pixi.toml but imported in source: `svgwrite`, `svg.path`, `svgpathtools`, `svgutils`, `jsonpickle`, `html2image`, `svglib`, `reportlab`, `colour`, `IPython`, `pandas`, `PIL`, `matplotlib`.

## Tests

```bash
pixi run pytest OCTA_toolbox-master/tests/
pixi run pytest OCTA_toolbox-master/tests/test_pattern.py  # single file
```

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
