# D6 B1-R1 design repair record

**Date:** 2026-09-30. **Scope:** repair synthetic experiment evidence only. **Review state:** STOP FOR B1 DESIGN REVIEW.

## Repair objective and estimand

R1 retains the conditional membership estimand Z[g,k]: whether authored group node g is included in frozen candidate scope k, conditional on the predeclared candidate universe and provenance. Candidate scopes may overlap. Singleton, unassigned, and ambiguous states remain representable; authored furniture membership is not rewritten. Generated truth is synthetic computational truth only.

The inference function signature is infer(observation_fixture, prior_name, dependence). It cannot receive truth or split labels. The experiment serializes observations and truth separately, writes all posterior output to inference-frozen.json, reads that file back, and only then passes frozen predictions to scoring code that joins truth. Split/family metadata is a third file. The split unit is the complete fixture: 32 development and 16 holdout fixture IDs are disjoint.

## Scene observations, candidates, and provenance

Each authored group has exactly one scene-level immutable record containing geometry summary, trend/frame, Z/clearance, channel status, and source provenance. Candidate scopes store references and SHA-256 signatures to those records; they do not copy or regenerate them. Each canonical unordered member-pair relation is stored exactly once at fixture level, with sorted group IDs, canonical pair key, source references, normalized gap and contact-support observations. Candidate scopes reference shared pair IDs through candidate_specific_evidence; this identifies the candidate-specific projection of shared observations without duplicating pair rows. Members, candidate scopes, pair relations, and repeated scope references are nested observations, never independent replicate counts.

The synthetic fixture schema includes six families: geometry-driven merge, shared spatial structure, overlapping candidates, singleton/unassigned, ambiguous alternatives, and status perturbation. The experiment data carry group geometry, trend/frame, Z/clearance, normalized boundary gap, contact support, relation provenance, and a separate empty-space role profile. The space profile is independent, has no membership likelihood link, and is never compared with furniture truth.

## Status generation and propagation

The status schedule is a deterministic cycle over fixture, record, and channel indices. It is established independently of truth labels and observed signal values. Every status is asserted in both generated input and posterior status traces.

| Status | Synthetic payload | Inference behavior |
|---|---|---|
| computed | Finite/binary value and source references | Use declared likelihood |
| missing | Reason and source references; no value | Preserve status, no likelihood |
| invalid | Reason, source references, malformed-payload marker; no numeric value | Preserve invalid, no likelihood |
| partial | Only one named observed component plus missing-component list | Use that observed component; output remains partial |
| not_available | Reason and source references; no value | Preserve unavailable, no likelihood |
| conflict | Both source alternatives and values, no selected primary value | Preserve both alternatives; no likelihood contribution |

This status mechanism is not a fitted missingness model. MNAR mechanisms cannot be distinguished from latent membership without designed replication, observed availability predictors, or external calibration. R1 does not claim to identify them.

## Prior and dependence sensitivity

The fixed Bernoulli membership prior scenarios are declared before scoring:

| Scenario | p | Expected size of a five-group candidate scope |
|---|---:|---:|
| Sparse | 0.20 | 1.00 |
| Central | 0.40 | 2.00 |
| Diffuse | 0.70 | 3.50 |

These are sensitivity points, not an estimated or selected prior. Development truth is used only for the prevalence-only scoring baseline. All three priors are reported on the same frozen holdout predictions.

Two likelihood aggregation contrasts are reported: independent sums channel/pair log likelihood ratios; shared_node_source_discount averages contributions within shared scene and pair-source blocks. This is a deliberate sensitivity contrast, not an estimated random effect or covariance parameter. A CAR/spatial covariance contrast is not_identifiable: five-node fixtures and no repeated realizations of a common spatial graph do not identify the spatial covariance structure. All uncertainty intervals and scores resample/aggregate whole fixtures.

## Same-input deterministic recipe comparison

R1 implements the existing H2 semantics on the exact same frozen observation records and candidate scopes:

- relative_gap_rank: finite computed normalized gaps; inclusive-linear quantiles 0.25, 0.50, 0.75; select gap <= quantile.
- local_persistence_window: endpoint neighbor rank ordered by gap then neighbor ID; windows 1, 2, 3 and persistence 1 or 2 across the declared windows, matching H2 behavior.
- space_profile_rank: finite computed independent space-role profiles; inclusive-linear quantiles 0.50 and 0.75; select profiles at or above the quantile.

Outputs are diagnostic relation selections with per-fixture selected-pair counts, input status counts, and overlap counts. For the gap and persistence recipes, pair F1 is computed within fixture against synthetic pair truth, then averaged at fixture level. For space-profile, membership-truth comparison is prohibited; only role-record availability and selected-role-pair counts are reported. No output chooses a posterior, recipe, threshold, scale, candidate selector, or production rule. Deterministic support remains distinct from posterior probability.

## Calibration, acceptance boundary, and limitations

Prior/dependence scores use per-fixture Brier values and a 1,000-resample fixture-cluster percentile interval. Calibration bins first summarize memberships within each fixture, then weight contributing fixtures equally. Labels show fixture counts; nested member counts are retained only as descriptive audit values. The SVG includes all six prior/dependence configurations and its caption states synthetic computational truth and the fixture unit.

Posterior predictive checks are explicitly not_run: this prototype has no jointly fitted generative posterior model, and a calibration plot is not a PPC. Numerical comparisons are synthetic computational gates only; they do not establish real-layout accuracy, psychological validity, or production readiness. Holdout has 16 fixtures and only 2–3 per family, so family differences are exploratory and low precision. No holdout-driven tuning or winner selection is authorized.

## Reproduction

pixi run python scripts/design/group_level/d6_b1_experiment.py

Generated inputs, truth, split, frozen predictions, same-input recipe outputs, calibration rows/SVG, report, and hashes are under docs/project/evidence/d6-b1-r1-artifacts/. The artifact manifest includes the amended script and both R1 records.
