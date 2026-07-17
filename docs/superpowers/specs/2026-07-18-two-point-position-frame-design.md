# Two-Point Position Frame Design

## Goal

Fix the degenerate case where a position scope with exactly two furniture
groups proves its own order by deriving a scoring frame from the same two
centers. Two points may still be evaluated, but they must not self-infer the
frame that gives them a perfect score by construction.

This spec narrows the existing position grammar design. It does not introduce a
second public position system.

## Problem

The current region-level position grammar tests frame candidates such as
`position_pair_direction` and center PCA. With exactly two group centers, both
sources collapse to the line through those two centers. A `line` or `pair`
candidate then scores the same two points against that self-derived line, so
the residual is always zero.

That means a two-group scope can report:

```text
position-frame-basis = position_pair_direction
position-fit = 1.0
position-residual-mean = 0.0
```

even when the two groups are visibly shifted relative to the expected layout.

## Design Rule

Two-point scopes need an external reference before they can claim strong
position order.

For `len(coords) == 2`:

- use shared authored `position-frame-angle` when every group in the scope
  provides the same value;
- use authored slots when complete slot metadata is available;
- otherwise use only weak non-self-derived fallback frames, currently global
  `0` and `90`;
- do not use `position_pair_direction` as a default scoring frame;
- do not use two-point PCA as a default scoring frame.

For `len(coords) >= 3`, keep the current position-only frame search:

- authored position frame;
- pairwise center directions;
- center PCA;
- global `0/90` fallback.

The reason is simple: three or more points have redundancy. A candidate line,
grid, or cluster can be contradicted by the extra points. Two points cannot
contradict their own connecting line.

## Public Switch

Add a narrow debug/demo option:

```python
allow_two_point_inferred_frame=False
```

Default `False` is the production behavior. When `True`, two-point scopes may
include `position_pair_direction` and two-point PCA candidates so the notebook
can show the old self-inferred behavior for visual comparison.

The option should be threaded only through the existing position grammar path,
for example:

```python
region_position_grammar_evidence(
    furniture_groups,
    allow_two_point_inferred_frame=False,
)
```

and, if needed by the demo:

```python
evaluate_scene(
    scene,
    position_grammar_enabled=True,
    allow_two_point_inferred_frame=True,
)
```

No caller should need to set the option for normal matrix evaluation.

## Evidence Semantics

When `allow_two_point_inferred_frame=False` and no authored frame or authored
slots exist:

- the two groups are still evaluated;
- selected evidence should expose real residuals against weak fallback frames;
- confidence should stay limited by the weak frame basis;
- the score must not become `1.0` only because the frame was generated from the
  same two centers.

This does not mean two points are automatically bad. It means two points alone
are insufficient to prove strong position order.

## Code Scope

Keep the implementation minimal:

- modify `features/position_grammar.py`;
- add targeted tests in `test/test_floorplan_scene_loader.py`;
- update the position grammar notebook/demo only to pass
  `allow_two_point_inferred_frame=True` for the requested comparison view.

Do not change:

- furniture-group inference;
- region inference;
- trend scoring;
- rotation scoring;
- column-grid relation scoring;
- BIM/SVG loading semantics.

## Acceptance

- A synthetic two-group diagonal scope without authored frame does not select
  `position_pair_direction` or two-point PCA by default.
- The same synthetic scope can select self-inferred frame candidates when
  `allow_two_point_inferred_frame=True`.
- A two-group scope with shared authored `position-frame-angle` still uses
  `authored_position_frame`.
- A three-group line or grid can still use inferred position frames.
- `SVG_potionNoRotation.svg` center-lounge evidence no longer reports a false
  zero residual by default.
- The notebook/demo can render an explicit opt-in comparison with
  `allow_two_point_inferred_frame=True`.

## Grill-Me Self-Check

- Does this disable two-group evaluation? No. It disables only two-point
  self-inferred scoring frames by default.
- Does this reintroduce rotation, trend, or column-grid alignment into
  `P_position_fit`? No. The fallback frames are still position-only.
- Does this add another public scoring system? No. It adds one debug option to
  the same grammar path.
- Can a two-point pair still score high? Yes, when it fits authored slots,
  authored frame, or a weak fallback frame without self-proof.
- Is the fix at the shared root? Yes. The frame candidate helper is the common
  source used by region-level position evidence.
