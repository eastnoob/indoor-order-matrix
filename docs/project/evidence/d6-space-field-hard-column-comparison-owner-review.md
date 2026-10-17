# D6 hard partition A/B/C column comparison · owner review

Review gate: **STOP FOR COLUMN-AWARE HARD PARTITION REVIEW**<br>
Frame: **provisional diagnostic frame** · **not owner-confirmed**

Please review the A/B/C PNGs in `outputs/design/space_field_soft_field_experiment/repair_v1_hard_column_comparison/`:

- `furniture_only_1_regions.png` through `furniture_only_4_regions.png` — furniture-only hard partition;
- `wall_aware_1_regions.png` through `wall_aware_4_regions.png` — wall-aware diagnostic;
- `wall_plus_column_1_regions.png` through `wall_plus_column_4_regions.png` — wall-plus-column diagnostic;
- `cut_edge_before_after.png` — all existing cuts overlaid with A/B/C colors.

The PNGs were regenerated after restoring display-only convex-hull envelopes from the same furniture-group footprints. This restores the closed candidate outlines and translucent region fills visible in the earlier hard-candidate views; it does not introduce a production selector or change the JSON partition result. The previous cut-only PNGs and disposable blend remain in `pre_envelope_render_20261003/` for comparison.

The physical columns and walls are visible in all scenes, while the hard cut recipe remains the furniture relation recipe. The visual legend distinguishes `physical column geometry`, `boundary evidence`, `internal obstacle evidence`, `virtual separation not selected`, and `not owner-confirmed`.

The real IFC comparison finds no new or disappearing hard candidate, no membership change, and no cut-edge sorting change. Wall and column source profiles are attached to every existing cut. None of the cut segments has an exact wall or column intersection; the nearest physical sources are retained as relative evidence only. The empty-space diagnostic changes because physical occupancy changes, but its component count is not treated as furniture region count.

The owner decision still needed is whether to define a future boundary/obstacle-aware selector. Until that decision, the furniture relation graph and boundary/obstacle evidence graph should remain separate, and all B/C partition effects remain `deferred` / `not_computable`.
