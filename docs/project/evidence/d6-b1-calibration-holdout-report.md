# D6 B1 synthetic calibration and holdout report

**Run date:** 2026-09-30. **Decision status:** execution evidence for design review only.

## Result

Command: `pixi run python scripts/design/group_level/d6_b1_experiment.py` (exit 0). Seed `61030` generated 48 whole fixtures; development used 32 and holdout used 16. Holdout family counts were geometry merge 2, shared spatial structure 2, overlapping candidate 3, singleton/unassigned 3, ambiguous alternatives 3, and status perturbation 3. Each fixture contains three predeclared candidate scopes and five authored group nodes; these nested rows are not independent samples.

Mean per-fixture holdout Brier score was **0.0910** for the simplified Bayesian diagnostic, versus **0.2194** for the development-prevalence-only baseline (33.125% prevalence). The predeclared computational gate of at least 10% lower Brier than baseline was met in this generator. Each of the six small family strata also had a lower mean fixture Brier than that same baseline; family counts are only 2–3 and do not establish generalization. A mean deterministic-index accuracy of **0.8625** is reported as a descriptive comparison only; its index is the mean of available binary evidence families and is not a D1 recipe reproduction or a probability.

The calibration SVG and bin table show nested-membership aggregates against generator truth. Bin counts were 145, 0, 14, 32, and 49. The empty 0.2–0.4 bin is retained as empty. Calibration is visibly evaluated at the membership display level, but uncertainty intervals and fixture-cluster bootstrap intervals were not implemented. It is therefore not a precision estimate and no statistical claim is made from the row counts.

## Scope and limitations

The runnable prototype has a fixed Bernoulli membership prior (`p=0.4`), a simple channel likelihood, and a per-membership marginal mixture over two declared reliability states. It is not the proposed beta-binomial/hierarchical prior, does not jointly fit shared-node/source or spatial CAR effects, and does not use continuous gap, contact, trend, Z/clearance, or barrier values in the posterior calculation. Those requested evidence types are preserved in the synthetic observed fixture records as design inputs, but this prototype uses three grouped binary evidence-family observations. Status categories are preserved, with non-computed values omitted from this simplified likelihood. The truth is written separately and is read only in the scoring function.

Posterior predictive checks are **not run** because the prototype does not fit a joint generative model. Existing D1 deterministic recipes were reviewed as parallel diagnostics in the design record, but a same-input execution comparison was **not run**; the reported deterministic index is explicitly a minimal proxy. Accordingly the metrics show reproducibility and a narrow synthetic calculation, not approval of the proposed Bayesian model, a production candidate selector, or psychological/perceptual validity.

## Artifacts

See `docs/project/evidence/d6-b1-artifacts/artifact-manifest.json` for byte sizes and SHA-256 hashes. It lists the fixture manifest, separate truth manifest, holdout report and scores, calibration SVG, and experiment script. The report preserves fixture-level metrics, per-family summaries, fixed seed, split, calibration bins, and the truth-isolation flag.

## Review questions remaining

1. Approve or revise the primary conditional membership estimand and candidate-universe boundary.
2. Decide whether the beta-binomial occupancy prior and proposed provenance/source effects are the right next model specification.
3. Require an owner-reviewed missingness mechanism and conflict policy before fitting a richer likelihood.
4. Review dependence sensitivity, posterior predictive checks, and same-input D1 recipe comparisons before any implementation checkpoint.
5. Confirm that fixture-level acceptance gates are suitable for later synthetic development; this small run must not be treated as a confirmatory holdout.

**STOP FOR B1 DESIGN REVIEW**
