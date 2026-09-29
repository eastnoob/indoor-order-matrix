# D6 Inferred-Group Candidate Field Design

- Date: 2026-09-29
- Status: design checkpoint; no production selector or public API
- Upstream contract: `docs/project/d6-overall-self-description-design-table.md`
- First-slice contract: `docs/project/d6-group-self-description-implementation-design-review.md`
- Evidence basis: D3-D5 evidence ledger, D6 Bayesian evidence synthesis, E8-E11 probes

## 1. Purpose and boundary

The next research object is the mechanism that describes which authored
furniture groups may be organized by the same spatial structure. It is not a
replacement for authored IFC membership. It is also not a claim about what a
person perceives.

The output of this checkpoint is a comparable design and a deterministic
computational experiment. It must not add a production candidate selector,
modify `NeutralSceneV2`, change adapters, change the public room model, or
introduce human labels. A candidate may be overlapping, weak, ambiguous, or
unassigned; the design must not force a unique partition.

## 2. Source separation

The following are separate layers:

| Layer | Meaning | Authority |
|---|---|---|
| authored group | Explicit `furniture_group` node and its member references | Source fact |
| context | Walls, openings, columns, counters, lamps, and other non-node geometry | Spatial reference only |
| analysis domain | Explicit region in which empty-space observations are defined | Source fact |
| relation evidence | Pairwise geometry, gap, contact, overlap, Z, barrier, and semantic observations | Derived evidence |
| space field | Empty-space connectivity, clearance, bottleneck, openness, occupancy, and role candidates | Derived evidence on the domain |
| candidate field | Competing, scale-declared combinations of authored groups | Experimental inference |

An authored group is never created from proximity, a name, a layer, an ordinary
group reference, or an inferred candidate. An empty region is a first-class
spatial observation and may receive several role candidates; it is not a
furniture group.

## 3. Interpretation of the design question

The primary interpretation is:

> An inferred group describes authored furniture groups that are jointly
> organized by a spatial structure, while preserving the possibility that the
> structure is weak, overlapping, multi-scale, or unresolved.

Pure geometric compactness is therefore evidence, not the definition. A wide
relative gap may support a separator or corridor field, but a fixed distance
cannot define a corridor across all scenes. Type labels can supply soft
compatibility or conflict evidence. Explicit mutual exclusion is a hard
candidate-level constraint. No single channel is allowed to silently dominate.

The candidate field is a computational description. A value such as
`co_membership_evidence` is not a probability and is not a human confidence
rating. A Bayesian posterior, if later implemented, must use a separate
distribution payload and model provenance.

## 4. Common evidence object

Every candidate mechanism consumes the same first-slice records:

```text
G_i  authored group geometry, frame/axis, member completeness, provenance
R_ij pair relation evidence and missingness
S(D) spatial field over the explicit AnalysisDomain
T_i semantic facts and source reliability
V     explicit mutual-exclusion constraints
```

`R_ij` remains a vector. Its fields include physical gap/contact/overlap,
normalized gap, Z/3D/barrier status, semantic support/conflict, and witnesses.
`S(D)` remains separate from the group graph and can describe empty regions even
when no candidate group is formed.

The candidate record proposed for experiments is:

```text
candidate_id
members
scale_descriptor
co_membership_evidence       # deterministic support, not probability
positive_support_vector
negative_evidence_vector
space_role_refs
mutual_exclusion_conflicts
missingness
status = overlapping | unassigned | weak | ambiguous | diagnostic_only
provenance
```

The exact aggregation of `R_ij` into candidate evidence is deliberately an
experiment factor. No `formal_membership_edge` is created by this design.

## 5. Candidate mechanisms to compare

### A. Multi-scale relation-field baseline (recommended first)

Build a group relation graph whose edges retain the complete evidence vector.
Declare scale from the scene's observed gap/clearance distribution and local
field persistence, rather than from a fixed distance. At each declared scale,
produce candidate views and retain the evidence that supports or separates each
candidate. Connected components are only a chaining diagnostic. Complete-link
and max-span are bounded-cohesion diagnostics; none is silently promoted to a
production rule.

This option is the recommended first computational baseline because it is
auditable, deterministic, compatible with missingness, and able to express
overlap and ambiguity without pretending that one score is truth. It still
requires experiments to decide how scale persistence and candidate competition
should be summarized.

### B. Hierarchical Bayesian latent candidate field

Treat candidate membership or group edges as latent quantities conditioned on
`G`, `R`, `S(D)`, semantic evidence, missingness, and reliability. A possible
future estimand is:

```text
P(candidate membership | group relations, space roles,
  semantic evidence, mutual-exclusion constraints,
  missingness, reliability)
```

This option can express multi-level dependence, posterior multimodality, and
uncertainty. It requires a declared generative model, prior, likelihood,
spatial dependence structure, identifiability checks, posterior predictive
checks, and synthetic calibration. Existing evidence supports this as a
methodological candidate, not as a validated furniture model. It is not the
first production implementation.

### C. Unsupervised ML/community candidate view

Use geometry, relation, space-field, and semantic features to generate a
learned embedding or community structure. HDBSCAN, spectral methods, or other
clustering methods are possible diagnostics, but no specific library or
algorithm is selected here.

This option may discover patterns that a hand-specified rule misses, but it
needs a validation target, is sensitive to representation and hyperparameters,
and can silently force clusters. It is therefore a comparison baseline only;
it cannot define the production contract without an independent synthetic
evaluation and an explainable evidence projection.

## 6. Recommended design position

Use A as the first candidate-field experiment, preserve B as the uncertainty
extension, and use C only as an exploratory comparison when the installed
environment already supports it. The experiment compares mechanisms; it does
not declare A, B, or C correct merely because it produces a partition.

The first candidate-field result should be a set of named views at declared
relative scales. Each view retains candidate membership support vectors,
separator/connector role references, conflict provenance, missingness, and
whether the result is overlapping, weak, ambiguous, or unassigned. It should
not output a single `group_id` assignment for every authored node.

## 7. Empty-space field policy

The spatial field is defined only on an explicit `AnalysisDomain`. It may expose
the following role candidates without forcing one primary role:

- `corridor_candidate`
- `activity_space_candidate`
- `separator_space`
- `connector_space`

The role evidence uses free-space distance/clearance, connectivity, bottleneck
profiles, boundary openness, occupancy, barriers, and context alignment when
those channels are available. A role candidate can separate two furniture
groups, connect them, or remain unresolved. A group edge never becomes a route
path automatically, and a gap-path edge never rewrites authored membership.

If the domain or a required channel is missing, the result carries
`not_available` or `partial` with a reason. It is never replaced by zero,
clearance, or a fixed corridor width.

## 8. Interaction rules

The experiment must preserve these rules:

1. Ordinary type/name disagreement is soft negative evidence.
2. Explicit `factual_properties["mutual_exclusion"]` is a hard candidate-level
   veto with provenance.
3. Geometry, space, semantic, and context evidence remain separately visible.
4. Missing and invalid evidence are categorical states, not numeric penalties.
5. A shared authored member is a diagnostic dependency; it does not create an
   inferred edge.
6. Trend, frame, coherence, and deterministic strength do not decide first
   membership unless a later experiment explicitly changes this gate.
7. Candidate support is not probability. Bayesian posterior fields, if added,
   remain model-specific and separate.

## 9. Design experiment

The experimental unit is a complete synthetic layout fixture. Members and pairs
inside a fixture are not independent replicates. Every fixture has an external
computational truth file that is not read by the candidate mechanism.

### Fixture families

| Family | Controlled contrast | Required observation |
|---|---|---|
| gap-jump | locally regular spacing, then a relative spacing jump, then regular spacing | separator/corridor evidence and multi-scale persistence |
| minority-mixed | minority types either join a surrounding field or form a local pocket | soft semantic evidence versus local geometric/space support |
| geometry-conflict | same type with different size, shape, or direction | interaction rather than type-only grouping |
| space-conflict | similar groups separated by a domain gap, wall, or opening | empty-space role and barrier evidence |
| bridge-chain | A-B and B-C support while A-C is weak | chaining diagnostic, overlapping candidates, ambiguity |
| overlapping-candidates | two plausible spatial organizations share a node | overlapping candidate representation |
| missing-invalid | missing domain, missing geometry, invalid geometry, partial members | status propagation and no zero filling |
| context-perturbation | add or remove wall, column, counter, or lamp context | context changes evidence without changing node eligibility |
| invariance | translation, rotation with frame, unit scale, ID/traversal reorder | canonical result invariance |

### Mechanisms and outputs

The probe compares:

- D0: evidence-only relation/local-neighborhood view;
- D1: multi-scale relation-field candidate views using relative distribution
  descriptors and persistence;
- B1: a declared latent-membership model contract or, if the installed
  runtime permits, a small synthetic posterior prototype;
- M1: an installed-runtime ML/community diagnostic, with no new dependency.

If B1 or M1 cannot run without installing a dependency or inventing a model
prior, the probe records that limitation rather than substituting a fake result.

### Decision observations

The probe reports:

- invariance and deterministic reproducibility;
- preservation of overlapping, weak, ambiguous, and unassigned states;
- whether a single channel can override an explicit veto;
- whether empty-space roles remain separate from group membership;
- sensitivity to relative scale and scene composition;
- status and missingness propagation;
- explanation completeness and provenance;
- for Bayesian candidates only: identifiability, posterior predictive behavior,
  multimodality, and synthetic calibration;
- computational cost and dependency burden.

No human visual judgment, human label, or psychological dependent variable is
required for this experiment. Blender or SVG rendering is optional diagnostic
evidence only; it cannot approve a candidate selector.

## 10. Freeze gates before implementation

The candidate selector must remain in design until these decisions are recorded:

1. the exact candidate estimand and whether it is edge-level, membership-level,
   or spatial-role-level;
2. the relative-scale descriptor and persistence rule;
3. the representation of empty-space roles and domain/channel missingness;
4. the permitted candidate statuses and whether singleton/unassigned views are
   retained;
5. the aggregation rule from pair evidence to candidate evidence;
6. the interaction of soft semantics and hard mutual exclusion;
7. the deterministic/Bayesian/ML output schema boundary;
8. the synthetic holdout and acceptance criteria.

After these gates, a separate implementation plan may define a production
candidate selector. Until then, the only approved implementation target is the
design probe and its evidence records.

## 11. Evidence and limits

The existing Bayesian synthesis supports the methodological possibility of
latent grouping and spatial hierarchical models, synthetic calibration, and
posterior predictive checks. It does not establish a validated furniture
grouping model or psychological validity. Existing E8-E11 probes support the
need for auditable pair evidence, missingness, ambiguity, context separation,
and IFC/SVG capability boundaries. They do not select a candidate algorithm.

The design therefore treats deterministic, Bayesian, and ML mechanisms as
competing computational descriptions. A posterior is conditional uncertainty
under a declared model, not a probability that people will perceive a group.

## 12. Skills used for this design

- `superpowers:brainstorming`: classified this as architectural work and kept
  design approval separate from implementation authorization.
- `speckit-assess-*`: reused the existing project assessment and decision rather
  than creating a duplicate project-level assessment.
- `experimental-design`: set the computational fixture unit, controlled factors,
  invariants, holdout boundary, and anti-pseudoreplication rule.
- `scientific-critical-thinking`: separated verified repository facts, design
  interpretations, external method evidence, and unsupported claims.
- `grill-me`: checked for fixed thresholds, hidden human labels, circular
  validation, and confusion between field, group, and probability.

**STOP FOR DESIGN REVIEW**
