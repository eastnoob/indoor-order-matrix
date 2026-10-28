# Source-axis `g→k` field replay v1

Status: implemented and replay-validated on 2026-10-31 from retained IFC-derived envelopes; owner/user review of the current reference-support result is complete. This record does not approve later field-family merging, reality calibration or cross-package use.

## Source and replay

The read-only replay reused the retained trend package at `outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/`. The pinned IFC is `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`, 408,618,044 bytes, SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`. No IFC geometry extraction was rerun. The inherited analysis plane is `ifc-world-plan`.

Replay command:

```powershell
$env:PYTHONPATH='.'
pixi run python -m scripts.design.group_level.run_group_axis_potential_ifc_replay --output-root outputs/design/group_axis_potential_ifc_replay
```

Final retained output: `outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z/`.

## Results

- 37 source envelopes, 37 usable `overall_group_axis` anchors, and 37 qualified scope groups produced 1,369 cells: 37 self and 1,332 non-self.
- All 1,369 cells are computed on this source. Each support is `group_clarity × cos²(undirected_delta)`; anchor clarity is separately retained.
- 37 non-self profiles each report expected/valid count 36. 37 read-only soft directions each include the self contribution and preserve direction, coherence, support, coverage, positive count, and self weight/fraction.
- All 37 original source envelopes and their source channels remain serialized. All 666 pair addresses retain the four independent relation channels; no combined relation score or extra global-resultant vote is emitted.
- Each of the 37 `field_views/field_NNN.svg` views contains all 37 groups, support opacity, anchor marking, source fingerprint, plane, and cell status counts. All 37 SVG files parsed as XML.
- `field_matrix.json`, `field_profiles.json`, `field_directions.json`, both visualization manifests, `package_contract.json`, `package_status.json`, and `report.json` are present. Freshness is `fresh`, with `recompute_required=false` and no reasons.

## Verification and limits

On 2026-10-31, after viewing the complete matrix and representative IFC plans,
the user replied “不错，我理解了”; the owner accepted the current overlapping
reference-conditioned support views. See the [visual review record](group-axis-source-axis-visual-preview-v1.md).
This closes checklist .11a/.12.6 within the displayed result's scope, without
claiming browser interaction acceptance or real-world grouping calibration.
Next is hierarchy/merge spec .14, followed by implementation plan .15; neither
is implemented or approved by this result review.

`PYTHONPATH=. pixi run pytest test/test_group_axis_potential_field.py test/test_evidence_package_output.py -q` passed (26 tests). `pixi run python -m compileall -q features scripts/design/group_level test/test_group_axis_potential_field.py` passed.

Structural tests cover the non-empty/no-usable-anchor diagnostic, singleton profile semantics, stable output identity for restored content, and complete source lineage. Pure mathematical checks cover zero total support and doubled-angle cancellation. The pinned IFC itself has 37 computed axes and does not cover invalid/undefined target axes, zero clarity, field-level zero support, or cancellation. Those states are not represented as IFC observations. Empty input remains rejected by the existing `EvidencePackage.evaluate` non-empty contract.
