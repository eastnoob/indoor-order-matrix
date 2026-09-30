# D6 B1-R1 execution verification

**Date:** 2026-09-30. **Run status:** verified by a clean replay.

This report accompanies the B1-R1 repair. The execution command is:

pixi run python scripts/design/group_level/d6_b1_experiment.py

The script checks whole-fixture split separation, shared group observation signatures, canonical shared pair relations, all six status input/output transitions, truth-free inference, and finite posterior values. A clean replay produced 48 fixtures (32 development, 16 holdout), six prior/dependence sensitivity configurations, 1,584 deterministic recipe views, and 11 hashed artifacts. It writes separate observations, truth, and split manifests; frozen inference output; same-input deterministic recipe results; fixture-cluster scoring; calibration SVG; and a SHA-256 artifact manifest.

Verification commands:

- pixi run python scripts/design/group_level/d6_b1_experiment.py — exit 0.
- Manifest SHA-256 recomputation — 11/11 valid.
- XML parse of calibration.svg — valid.
- Report inspection — CAR not_identifiable; posterior predictive checks not_run; space-profile truth comparison prohibited.
- git diff --check — pass after staging the exact R1 paths.

Posterior predictive checks remain not_run because no jointly fitted generative model exists. All scores are synthetic computational diagnostics only.

**STOP FOR B1 DESIGN REVIEW**
