# Region Frame Extent Consistency Design

## Problem

The inferred region trend overlay can show an overlong vertical axis when the final
two-axis frame angle is normalized after PCA. For example, `SVG_chaoticsvg.svg`
`north_tables` can carry a near-horizontal PCA extent into a near-vertical
normalized angle.

## Scope

- Keep the current angle and strength algorithms unchanged.
- Recompute `axis-primary-extent` and `axis-secondary-extent` after the final
  region frame angle is selected.
- Preserve existing region geometry, path inference, and notebook drawing rules.

## Acceptance

- A regression test proves final metadata extents match projection ranges at the
  final `axis-angle`.
- Existing tests continue to pass.
- The inference demo notebook is re-executed so visual review uses fresh output.
