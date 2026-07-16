# Matrix Notebook Explainers Spec

Create two executed notebooks that explain the current implemented matrix without redesigning it.

## Scope

- `axis_orientation_metrics_explained.ipynb` explains the region / axis / orientation / consistency family.
- `position_order_metrics_explained.ipynb` explains the object-position / spatial-order family.
- Both notebooks use the existing SVG fixtures and `evaluate_scene()` output.
- Notebook helper code is presentation-only; it must not change matrix logic.

## Content

- Each notebook starts with short Markdown in English, with occasional Chinese labels where helpful.
- Each notebook includes a clean model visualization and a metric table.
- The axis notebook focuses on regions, furniture groups, region axes, trend axes, boundary/column relations.
- The position notebook focuses on furniture-group local frames, slots, residual vectors, fit, confidence, and grammar evidence.

## Non-goals

- No new metric rows.
- No new inference rules.
- No BIM adapter changes.
