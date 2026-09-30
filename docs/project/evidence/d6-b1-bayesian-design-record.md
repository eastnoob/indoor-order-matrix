# D6 B1 — inferred-group candidate-field Bayesian design

**Status:** design and synthetic computational experiment only; submitted for owner review on 2026-09-30. No production implementation, selector, automatic-space behavior, or perception-validity claim is authorized by this record.

## Question and estimand

Let `G` be the authored furniture-group nodes in a scene and let `K` be a frozen, predeclared diagnostic candidate scope set with source/provenance. The primary target is

`Z[g,k] = 1` iff authored node `g` belongs to diagnostic candidate scope `k`, conditional on the frozen candidate universe and its provenance.

The target is the membership posterior `P(Z[g,k]=1 | E, K, M)`, where `E` is the admissible evidence and `M` is a declared model. Candidate-universe generation uncertainty is outside this conditional estimand and must be reported separately in any later work. Candidate scopes may overlap; a partition is not assumed. Singleton, unassigned, and ambiguous memberships remain representable. Authored memberships are facts and are not rewritten by these candidate posteriors. An explicit authored mutual-exclusion declaration may constrain a candidate only when its source and provenance are retained.

Computational truth in the synthetic experiment is a generator-defined membership label, not an expert label, human judgment, or psychological ground truth.

## Quantities that must not be conflated

| Quantity | Meaning | Interpretation boundary |
|---|---|---|
| Deterministic strength | A fixed recipe's support summary, e.g. mean of available channel indicators or an existing recipe output | Not a probability; no calibration claim follows from its numeric range |
| Bayesian strength / posterior | `P(Z=1 | declared prior, likelihood, dependence, evidence)` | Model-conditional probability for this estimand only |
| Posterior uncertainty | Distribution/credible interval, entropy, and calibration diagnostics for `Z` | Not another strength score; depends on data, model, and prior |

The prototype's deterministic strength is a simple parallel evidence index, not a reproduction or endorsement of a D1 recipe. Existing D1 deterministic recipes remain parallel comparators; no winner or selector is chosen.

## Evidence contract

Evidence is channelized and provenance-bearing. It does not create formal furniture membership.

| Channel | Proposed likelihood role | Required fields / separation |
|---|---|---|
| Normalized boundary gap | Continuous geometry likelihood; use within-scene normalized/rank-based transforms and sensitivity checks | Scale definition, support, source geometries, status; no absolute-distance cutoff |
| Contact / overlap | Separate binary/continuous observations: 2D contact, 2D overlap, and 3D overlap | Never collapse dimensions; retain geometric source and tolerance provenance |
| Member-pair provenance | Dependency and reliability grouping, not a positive membership label by itself | Pair IDs, relation source, derivation chain, duplicate/canonical key, and shared source IDs |
| Group geometry | Candidate extent/shape and member-geometry summaries | Geometry validity, coordinate frame, source IDs; avoid duplicating evidence already encoded by pair gaps |
| Trend / frame | Directional/axis evidence with uncertainty and support count | World-space final geometry frame; direction and concentration stay distinct; no trend when unavailable |
| Z / clearance | Height-aware compatibility/clearance evidence, separately measured | Z interval, vertical datum, support geometry, analysis domain and status |
| Wall / opening barrier | Channel-specific barrier observations and permeability | Wall/opening source IDs and walk/visual semantics remain distinct; explicit hard constraints only if authored |
| Missingness / reliability | Observation process model and source reliability | Explicit status, reason, reliability provenance, and shared-source grouping; missingness is not zero |
| Empty-space evidence | Separate `space-role` posterior/report, if a valid explicit analysis domain and space evidence exist | No direct likelihood edge into furniture membership in B1; `not_available` when domain is absent |

Do not infer affordance from furniture kind. Do not substitute scene bounds for `AnalysisDomain`. Current clearance, barrier, and space evidence may remain `not_available` or deferred.

## Prior, likelihood, and spatial dependence proposal

### Prior

Use a weakly informative, candidate-size-aware exchangeable prior as the baseline. One reviewable option is a beta-binomial scope-size prior: `p[k] ~ Beta(a,b)` with `a,b` selected so prior expected occupancy is stated before outcomes; conditional on `p[k]`, `Z[g,k] ~ Bernoulli(p[k])`. Candidate scopes use hierarchical `p[k]` centered on a scene-level occupancy prior, with regularizing hyperpriors and explicit prior sensitivity (at least sparse, central, and diffuse scenarios). This yields exchangeability without making larger candidate sets intrinsically more probable by an accidental combinatorial prior. Report prior expected size, prior probability by size, and sensitivity. Hard authored mutual exclusion is a scoped constraint with provenance; semantic disagreement is soft evidence.

### Likelihood

Use channel-specific likelihoods conditional on `Z`, with robustness to contamination/outliers and reliability informed by provenance. Continuous normalized gaps and geometry summaries can use robust Student-t or contaminated-normal families; contact/overlap/barrier observations can use Bernoulli/logistic families; trend/frame can use axial/circular likelihoods; clearance uses an appropriate continuous or interval-censored family. Do not multiply correlated encodings of the same geometry as if they were independent. Group observations by shared source/provenance and either use a joint channel model, a latent source effect, or a predeclared reduced sufficient summary. Model observation availability explicitly when missingness may depend on source or state; otherwise carry a status and marginalize only under a declared missing-at-random assumption. Reliability uncertainty should be estimated or sensitivity-tested, not silently fixed from deterministic strength.

### Spatial and provenance dependence

Memberships share authored nodes across scopes; pair relations share endpoints; multiple measures can reuse the same geometry; repeated frames share a scene/source. Model these dependencies with node and source random effects plus a fixture/scene effect. For spatially adjacent memberships, consider a proper CAR/latent Gaussian effect only after the graph, neighborhood definition, scaling, and identifiability constraints are specified. Compare against a simpler shared-random-effect model and report dependence sensitivity. Never count membership rows, candidate rows, member pairs, or frames as independent experimental replicates. The independent replication unit for the synthetic experiment is the whole generated fixture.

## Status propagation

| Input status | Likelihood action | Posterior/report action |
|---|---|---|
| `computed` / valid | Use only with declared measurement model and provenance | Record channel contribution and validity |
| `missing` | No numeric imputation; model availability only if its mechanism is specified | Preserve missing status/reason; posterior may be prior-dominated and must say so |
| `invalid` | Exclude from numeric likelihood; do not relabel as missing | Preserve invalid reason and source; invalidate dependent derived summaries |
| `partial` | Use only the observed components in a declared partial-data likelihood | Propagate partial support; do not promote to computed |
| `not_available` | No likelihood contribution | Preserve unavailable; dependent space/topology remains unavailable if domain/evidence absent |
| `conflict` | Do not choose one source silently; model alternatives only if conflict mechanism is explicit | Preserve all source records and conflict; widen/branch uncertainty or withhold derived conclusion |

Optional unavailable channels do not erase computed evidence from other channels. A required input absence blocks only the affected estimand/diagnostic. Status aggregation must not turn unknown into zero or clear. Empty-space role status is independent of furniture membership status.

## Explanatory views retained

1. **Geometry-driven merge:** posterior support can arise from geometry evidence, with sensitivity to geometry provenance and duplicated encodings exposed.
2. **Shared spatial structure:** candidate support can reflect modeled node/source/spatial effects; show which dependencies create it and check graph-definition sensitivity.
3. **Overlapping candidate:** a node can have high inclusion probability in multiple scopes; display the joint ambiguity rather than normalize candidates into a partition.
4. **Singleton / unassigned / ambiguous:** preserve singleton scope, no eligible multi-member candidate, or multiple plausible scopes as distinct states. A thresholded display is only a view and cannot select production membership.
5. **Empty-space role:** if available, report a separate space-role posterior with its own estimand and validation; it cannot directly rewrite furniture membership.

## Identifiability and failure modes

The Bayesian model cannot recover information absent from its evidence or design. Membership and prevalence are not empirically identifiable from one unlabeled scene without external truth/constraints. The candidate universe itself is not identified by a conditional membership model. Collinear gap/contact/overlap/extent channels cannot identify separate effects. A source reliability effect is confounded with channel sensitivity absent replicated sources or calibration labels. CAR strength is not identifiable from a tiny or disconnected graph, or when it aliases a fixture random effect. Trend is not informative without directional support; Z/clearance and barriers cannot be inferred when no valid 3D/domain support exists. Missing-not-at-random mechanisms cannot be distinguished from latent membership without design information. Exact channel confounding, conflict, or no repeated fixture replication requires sensitivity bounds or an explicit `not_identifiable` result, not a confident posterior. Posterior concentration under an untestable prior is not evidence of identification.

## Calibration and posterior predictive checks

Calibration is evaluated only against known synthetic computational truth and at whole-fixture holdout. Predeclare Brier score, log score, reliability bins, and interval/coverage checks if posterior intervals are implemented. Report fixture-level summaries and cluster bootstrap intervals or fixture-level permutation; member rows are nested and only descriptive bin constituents. Priors and model parameters must be learned on development fixtures only. Holdout truth is opened only by scoring code after inference output is frozen. Posterior predictive checks compare generated/replayed distributions for gap/contact patterns, candidate sizes, overlap counts, status frequencies, trend support, and barrier/clearance patterns, stratified by fixture family and reliability. A calibration plot must show bin counts and computational truth semantics. Poor calibration triggers model revision, not post hoc threshold tuning.

### Synthetic split and preregistered acceptance gates

The runnable prototype uses seed `61030`, 48 complete synthetic fixtures: first 32 development, final 16 whole-fixture holdout. The truth manifest is generated separately from observations and is scoring-only. The manifest records hashes. Fixture families cover geometry-driven merge, shared spatial structure, overlapping candidates, singleton/unassigned, ambiguous alternatives, and status perturbations. This first prototype is a small smoke experiment, not powered evidence. The final holdout is not to be repeatedly tuned against; any model change requires a new seed/family holdout.

Before using a richer model for a design decision, require all of the following: deterministic byte-identical rerun for fixed seed; truth isolation; no leakage of fixture IDs across split; status preservation and invariance (unknown does not become numeric zero); overlapping candidates preserved; authored memberships unchanged; no empty-space-to-membership path; posterior probabilities finite and within `[0,1]`; calibration and scoring at fixture level; posterior predictive checks include all declared families/statuses; and sensitivity results show prior/dependence effects. As a development gate, require mean holdout fixture Brier score at least 10% below the predeclared prevalence-only baseline and no fixture family with worse mean score than that baseline. These are computational gates only and may be revised by owner before confirmatory use. No absolute distance threshold is used.

## Deterministic comparison

Run existing D1 diagnostic recipes and the Bayesian diagnostic on identical synthetic fixture seeds and frozen scopes. The named parallel recipes are `relative_gap_rank`, `local_persistence_window`, and `space_profile_rank`, paired with `selected_relation_connected`, `all_internal_pairs`, `complete_link_diagnostic`, `max_span`, and `min_gap` as applicable. Present paired, per-fixture scores and status/overlap behavior; summarize across fixtures, never across pair rows as if independent. Record recipe definitions/version, input hashes, and unavailable-channel handling. No recipe, posterior cutoff, threshold, scale, or selector is selected in B1. Deterministic strength remains a descriptive support index; compare its ranking/scoring behavior without calling it probability. The current run did not execute these D1 recipes on the generated B1 observations.

## Prototype scope and limitations

`scripts/design/group_level/d6_b1_experiment.py` supplies a dependency-free generative smoke experiment, separate truth file, holdout scoring, calibration SVG, and SHA-256 artifact manifest. Its posterior calculation is intentionally a simplified binary-channel prototype; it does **not** fit the proposed beta-binomial prior, full joint shared random effects, CAR, continuous likelihoods, posterior intervals, or a full deterministic D1 recipe registry. Therefore its metrics are an execution/reproducibility demonstration, not acceptance of the richer Bayesian design or evidence of furniture-group validity. Those model components and formal posterior predictive checks remain review questions.

## References

Skills materially used: experimental-design, scientific-critical-thinking, scientific-visualization, and verification-before-completion.

Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065 (accessed 2026-09-30; current version). https://doi.org/10.48550/arXiv.2609.00065
