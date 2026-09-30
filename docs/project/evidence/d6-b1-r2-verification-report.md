# D6 B1-R2 verification report

**Date:** 2026-09-30  
**Status:** verified; design-only gate

Command:

`pixi run python scripts/design/group_level/d6_b1_r2_gate.py`

The run consumed the R1 observation, truth, split, frozen inference, deterministic comparison, and verification artifacts without modifying them. Assertions verified 48 complete fixtures, 32 development fixtures, 16 disjoint whole-fixture holdout fixtures, frozen inference truth isolation, shared group observation signatures across scopes, non-duplicated candidate-specific pair references, and the exact R1 observation hash binding.

The same-input comparison contains 1,584 deterministic recipe views and all six R1 Bayesian prior/dependence configurations. It records no winner or threshold. `space_profile_rank` remains prohibited from furniture membership truth comparison. Status counts cover computed, missing, invalid, partial, not_available, and conflict evidence; no status is silently imputed.

The SVG route matrix parses as XML. Posterior predictive checks are `not_run` because no joint generative model was fitted; the calibration artifact is not presented as a PPC.

All quantitative values remain synthetic computational evidence. They do not establish real-layout accuracy, psychological validity, or production readiness. No production selector or implementation code was entered.

**STOP FOR B1 DESIGN REVIEW**
