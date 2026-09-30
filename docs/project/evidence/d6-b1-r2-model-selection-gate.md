# D6 B1-R2 Bayesian model selection and implementation-design gate

**Date:** 2026-09-30  
**Status:** STOP FOR B1 DESIGN REVIEW  
**Scope:** design arbitration and synthetic evidence only. No production code, public API, adapter, NeutralSceneV2, or formal tests changed.

## Decision

The conditional membership estimand is approved for diagnostic use only:

`P(Z[g,k] = 1 | E, K, M)` where `g` is an authored group, `k` is a member of an externally frozen candidate universe, `E` is observed evidence, `K` is provenance/validity state, and `M` is the declared dependence policy.

The candidate universe remains an external frozen input. Bayesian output may describe membership support, uncertainty, and evidence state for each `(g,k)` pair; it does not create, rank, select, merge, or rewrite candidate scopes.

## Route A: diagnostic-only Bayesian

Route A is approved as an interpretable smoke diagnostic. The current binary-channel posterior is conditional on fixed synthetic likelihood values and therefore has a narrow meaning: it is a diagnostic posterior under declared assumptions. It is not an empirically calibrated probability, a production confidence score, or a selector signal.

The first diagnostic posterior may admit computed geometry, trend/frame, Z/clearance, and contact/overlap evidence. A partial record contributes only its named observed component. Missing, invalid, not_available, and conflict statuses propagate in the trace and contribute no likelihood unless a later policy explicitly defines a validated uncertainty model. Normalized gap is scale/audit evidence in Route A. Wall/opening barrier is deferred until source availability, orientation, and barrier semantics are validated. Empty-space evidence remains a separate space-role output and never changes furniture membership.

Route A must return posterior, prior, dependence label, status trace, source provenance, and an uncertainty/state explanation. It must not return a selector decision.

## Route B: richer Bayesian design

Route B is required before any implementation design can be approved, but no richer hierarchical model is fitted in B1-R2. The design must specify a continuous normalized-gap likelihood, trend/frame direction likelihood, availability-gated Z/clearance and wall/opening barrier channels, and shared-node/shared-source dependence. Candidate overlap, singleton, unassigned, and ambiguous states remain explicit outputs of the frozen candidate universe.

Route B must model source/group dependence rather than treat repeated scope projections, members, or pair observations as iid samples. CAR or generic spatial covariance remains `not_identifiable` for this design line: the current five-node synthetic graph has no replicated graph realizations sufficient to identify a covariance structure. It is permanently deferred unless a separately approved replicated spatial design is added.

## Same-input comparison

R1 frozen Bayesian outputs and the relative-gap, local-persistence, and space-profile diagnostics are compared on the exact same observation manifest. Deterministic strength/support remains a rule output and is not a probability. Space-profile membership truth comparison is prohibited because it is independent space-role evidence. No threshold, winner, prior, dependence setting, or selector is chosen from the synthetic scores.

## Truth isolation and acceptance boundary

Truth is serialized separately from observations and is joined only after frozen inference. The whole fixture is the split unit: 32 development fixtures and 16 holdout fixtures. Brier values and recipe summaries are synthetic computational gates only. They must not be interpreted as real-layout accuracy, psychological perceptual validity, or production readiness.

Posterior predictive checks are **not run**. The R1 prototype has no jointly fitted generative posterior; calibration plots cannot substitute for PPC.

## Implementation-design gate

Entry requires a frozen candidate universe and output-state contract, source/provenance identity rules, calibrated continuous and directional likelihoods, a predeclared shared-source dependence sensitivity grid, whole-fixture holdout calibration, joint-model PPCs, and an uncertainty/state contract that does not select candidates.

Exit is required for any truth leakage, split overlap, unresolved conflict/missingness policy, treatment of non-identifiable dependence as fitted, calibration presented as PPC, or introduction of thresholds, winners, selectors, or psychological-validity claims.

The machine-readable gate, evidence matrix, same-input comparison, SVG, manifest, and verification are under `docs/project/evidence/d6-b1-r2-artifacts/`.
