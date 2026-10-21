# Group Attribution Field Slice

- Date: 2026-10-26
- Status: design-only diagnostic; no production scoring rule selected
- Fixture: `scripts/design/group_level/group_attribution_field_slice_fixture.json`

## Result

All four diagnostic checks passed. With the eligible scope fixed at `G1`, `G2`, and `G3`, the two overlapping proposals `K1={G1,G2}` and `K2={G2,G3}` produced all six candidate-by-group field cells. Shared group `G2` retains separate candidate-local readouts (`0.56` in K1 and `0.67` in K2); values are not normalized across candidates.

| Candidate | Group | In proposal extent | Field status/readout | Note |
|---|---|---:|---|---|
| K1 | G1 | yes | computed / 0.82 | — |
| K1 | G2 | yes | computed / 0.56 | Also has its own K2 cell |
| K1 | G3 | no | computed / 0.31 | Retained; marked boundary tension |
| K2 | G1 | no | unknown / no scalar | Reason retained |
| K2 | G2 | yes | computed / 0.67 | Also has its own K1 cell |
| K2 | G3 | yes | conditional / no scalar | Reason and source retained |

`GX` is explicitly out of scope and has no field cell. Unknown and conditional cells remain categorical with reasons; neither is converted to zero. K2 has 1 of 3 eligible groups with a computed readout, so its displayed computed-readout coverage is `1/3`.

The supplied weak-bridge vector `[0.5125, 0.5125, 0.5125, 0.5125, 0.15]` yields mean `0.44`, median `0.5125`, and weakest-member value `0.15`. Masking one core readout leaves the observed values unchanged, lowers coverage from `5/5` to `4/5`, and produces observed-value mean `0.421875`; missing data are not zero-filled.

The replayable result is [`group-attribution-field-slice.json`](group-attribution-field-slice.json). The runner asserts the field domain, candidate-local overlap, extent-external cell, categorical status, and profile arithmetic.

## What this supports and leaves open

This supports the **representation boundary**: organization candidates remain overlapping views over a field, and proposal extent does not erase in-scope evidence. It does not select an evidence-to-readout mapping, candidate recipe, profile operator, or real-world strength scale. Proposal-evidence leakage, input qualification/identity disagreement, driver/modifier effects, exclusion endpoint edge cases, and incomplete-search propagation remain open diagnostics. Real-scene review and search-cost comparison remain later gates.
