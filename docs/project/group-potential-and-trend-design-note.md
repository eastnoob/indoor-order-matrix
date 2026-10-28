# Furniture-Group Potential and Trend Design Note

Date: 2026-10-28

Compact decision index: [`group-evidence-design-index.md`](group-evidence-design-index.md).

## User-confirmed direction

- Finish the furniture-group potential evidence before implementing the arrangement-pattern package, because the latter needs direction from potential rather than an absolute horizontal/vertical axis.
- Keep individual-furniture analysis and furniture-group analysis as separate layers. Current work is at the furniture-group level and concerns the PCA axis of the group as a whole; individual-furniture axes/frames are outside this work.
- The axis-only potential uses `overall_group_axis` only. `layout_axis` remains a separate group-level layout descriptor and is not an input to the current potential.
- The current working rule keeps clarity in two parallel roles: it supports/limits group-to-group axis relation evidence, and it weights each axis contribution when forming a higher-level resultant. These roles remain separately recorded and are not collapsed into one hidden value.
- A low but computed clarity keeps its angle as weak directional evidence. An undefined/degenerate axis has no comparable angle: do not invent one or replace it with zero; preserve its status and report its effect on aggregate coverage.
- A potential belongs to a furniture group as a feature. Similarity between group potentials is evidence; it does not itself declare the groups identical or create a hard boundary.
- A higher-level group's potential is the channel-wise average of its constituent furniture-group potentials. Keep channel dispersion so heterogeneity remains visible as trend/coherence evidence.
- For a higher-level resultant, keep direction coherence and resultant strength as separate outputs. A set of similarly oriented but weakly clear axes may have high directional coherence while retaining low resultant strength; this is not a contradiction.
- Keep potential and potential strength separate. In the current plan, potential is the group-level axis/orientation feature only. Keep frame as a later dedicated evidence package, and keep form and scale as a separate geometry-feature package.
- Do not replace direction with world-XY or analysis-plane U/V.

## Current implementation facts

`features/group_self_description.py` currently exposes two active group-level trend descriptors through `features/group_trend_alignment_field.py`:

- `overall_group_axis`: major eigenvector (one undirected axis, modulo 180 degrees) of the group's area-weighted total-geometry covariance.
- `layout_axis`: major eigenvector (one undirected axis, modulo 180 degrees) of the between-member centroid covariance.

`overall_group_axis` is the PCA major axis of the furniture group as a whole. `layout_axis` is a separate group-level descriptor derived from the distribution of member centers; it is not an individual-furniture axis and is excluded from the current potential. The two are not the major and minor axes from one PCA, and neither currently exposes its covariance's secondary eigenvector. Individual-furniture axes/frames are a separate analysis layer and are not part of this work. The global operator does not use pairwise relations as extra votes. A separate read-only diagnostic calculates the approved inter-group axis relation channels from retained IFC artifacts. Its local `strength` fields describe direction clarity, not the strength of a group-organization potential.

## Earlier design and current axis-only refinement

The earlier notes establish that a furniture-group potential is a structured feature, that similarity is separate relation evidence, and that a higher-level group can have a per-channel average with dispersion retained. They also keep strength, coherence, support, and uncertainty separate from the potential itself. See [`grouping-goal-alignment.md`](grouping-goal-alignment.md#用户澄清家具组势特征与上层组势2026-10-26) and [`d6-group-level-self-description-design.md`](d6-group-level-self-description-design.md#4-evidence-字段严格分层). The reviewed definition of `overall_group_axis` supplies the present group-level axis and its deterministic PCA clarity: see [`d6-trend-estimand-owner-review.md`](evidence/d6-trend-estimand-owner-review.md#c-is-the-overall-group-geometric-trend) and [`d6-trend-implementation-design-review.md`](evidence/d6-trend-implementation-design-review.md#24-c-a-and-d-formulas).

For the current narrowed axis-only scope, the user confirms these layers:

1. **Per-group axis clarity:** `overall_group_axis.strength` is the PCA anisotropy `(lambda_primary - lambda_secondary) / (lambda_primary + lambda_secondary)`. It describes how clearly that group's whole geometry expresses one axis. It is deterministic evidence, not a probability and not the potential itself.
2. **Between-group axis relation:** compare two groups' undirected `overall_group_axis` directions through their angular difference. This is a separate similarity relation; it does not by itself create membership or a hard group boundary.
3. **Clarity compatibility:** compare the groups' own axis clarity as another relation observation. The user explicitly adds that equal directions do not imply strong combined evidence when one or both axes are unclear; low clarity can weaken the directional relation or higher-level resultant.
4. **Higher-level resultant:** the reviewed axis-only aggregate baseline uses the clarity-weighted doubled-angle resultant described below. The resultant direction, coherence, and support remain separate from each member group's own axis clarity. Pairwise axis-similarity and clarity-compatibility now have a diagnostic-only IFC implementation; they are not extra votes in the global resultant, and no cross-scene or real-world calibration is claimed.

The prior design distinguishes `strength`, `coherence`, and `support`; the current user refinement also treats clarity as something that can affect relation strength. Keep the layers visible: group axis clarity belongs to the individual group observation; direction similarity and clarity compatibility belong to the relation observation; higher-level resultant strength/coherence belongs to the aggregate observation.

## Evidence-package composition principle

An evidence package may contain several internal observations and rules while exposing one coherent evidence layer to its consumer. For the axis-only package, the internal record should retain at least:

- each group's raw axis angle and PCA clarity;
- the angle relation between groups;
- the clarity compatibility between groups;
- any later approved combined relation reading, with its rule, status, and source references.

The confirmed relation layer keeps its component readings separate and emits no combined scalar. Any later combination must be additive and transparent; it must not replace the source readings or become a hard grouping answer or probability.

## Group-to-group relation layer — user-confirmed design (2026-10-29)

This layer belongs to the axis-only potential package; it is not a required
section of every evidence package. Its target is a relation between two
furniture groups, and its purpose is to make the existing group-axis evidence
inspectable locally. A pair is only a relation address: do not interpret the
complete relation matrix as pairing groups, selecting neighbors, creating
groups, or defining membership.

For the complete supplied authored-group scope, emit one record for every
unordered pair. With the currently retained 37 group observations this means
666 relation records. Do not add thresholds, edge selection, ranking, candidate
generation, or winner selection. Preserve each endpoint's source axis,
clarity, status, and lineage. Evaluate relation channels independently so an
unavailable direction does not erase clarity observations that remain
available.

The confirmed channel set is:

1. `axis_angle_gap`: the minimum undirected angle difference `δ` in `[0°, 90°]`.
   It is available only when both endpoint axes are valid.
2. `direction_similarity`: `cos²(δ)`, in `[0, 1]`. It reads parallel axes
   (including the 0°/180° equivalence) as fully aligned and perpendicular axes
   as non-aligned. It is an axis-compatibility reading, not a probability or
   calibrated force.
3. `clarity_similarity`: `1 - |c_a - c_b|`, in `[0, 1]`. It answers whether
   the two source axes have similar clarity; by itself it does not say that
   either axis is clear. The endpoint clarity values remain available through
   the unchanged source envelopes.
4. `clarity_support`: `min(c_a, c_b)`, in `[0, 1]`. This is the conservative
   common support: the less clear endpoint limits how much clarity supports
   the relation. It complements clarity similarity rather than duplicating
   it.

`clarity_similarity` and `clarity_support` are two readings derived from the
same endpoint clarity values, not independent source observations. Preserve
the endpoint values and their source references so consumers can inspect what
each derived reading means.

Keep these readings separate. Do not emit a formal `combined_relation =
direction_similarity × clarity_support` in this design revision: the product
adds no new observation, embeds a further rule, and could be counted again
alongside the existing global clarity-weighted resultant. A later diagnostic
may examine such a derived value only if it remains explicitly labeled and
additive beside every component; it must not be treated as an independent
source of evidence or fed back into the global resultant.

The pairwise layer and the existing global resultant answer different
questions while reusing the same source axes. Pairwise readings show where
local directional relations occur; global direction/coherence/resultant
summarize all supplied axes. They are not independent evidence sources and
must not be added together as separate votes. Leave the global operator
unchanged.

Statuses are channel-specific. If either axis is undefined, degenerate, or
invalid, retain its status and mark only the angle/similarity channels
unavailable as appropriate; never invent an angle or substitute zero. If an
endpoint clarity is independently valid, clarity similarity/support may
still be computed. Keep coverage and source references for all input pairs,
including pairs with unavailable channels.

For the real-IFC diagnostic visualization, retain neutral group coloring on the
shared analysis-plane base map and provide complete symmetric matrices for
direction similarity and clarity support (with values available on inspection;
self-comparison diagonal cells are not applicable).
Selecting a matrix cell may highlight its two source groups on the plane; do
not draw thresholded relation edges or encode group membership. This is a
diagnostic visualization contract. The current retained IFC run contains the
relation matrices and neutral plane view; it does not provide interactive
matrix-to-plane selection.

User-confirmed first readings: `cos²(δ)` for direction similarity and
`min(c_a, c_b)` for conservative common clarity support, alongside endpoint
clarity and all component channels. These are explicit package readings, not
uniquely dictated physical truths or external calibration. The design and
active additive package integration are complete; the retained diagnostic
remains a separate read-only visualization/replay artifact.

## Owner's working design proposal

1. Build a channel-preserving axis/orientation potential record for each authored furniture group. Use group-level inputs only; existing axis descriptors may be recorded as source observations, but do not silently treat them as a complete frame or geometry description.
2. Compare axis potentials across the complete supplied scope using the confirmed relation layer above. Keep the complete matrix as relational evidence, not a pair-based candidate selector or membership decision.
3. For any higher-level group supplied by a future organization view, compute the axis potential mean and retain axis dispersion. This operation consumes a supplied set; it does not infer membership or select a winner.
4. Keep pairwise channels separate from the global resultant; do not produce a combined pair score, probability, threshold, or winner in this draft. Any later external calibration or use of the relation matrix in another rule requires separate review.

## Sequence

1. Use the whole-group PCA axis `overall_group_axis` as the axis-only potential, reusing its existing clarity/strength observation. Keep the group-level `layout_axis` outside this potential.
2. Review and, after user approval, implement the full-scope group-to-group relation channels in the design draft above; the pair records do not pair or group furniture groups.
3. Keep the frozen axis-only resultant operator as the global aggregate baseline, retaining coherence and support separately. Do not add pairwise channels into this resultant.
4. Apply the shared minimum package standard to the next potential output: declare source channels, deterministic targets, query/scope/plane, dependency fingerprints, output function/version, normalization, freshness and IFC manifest. Reuse the existing envelope/output/status contracts; do not add a second kernel or registry.
5. Review the owner-recommended source-axis field design: continuous `S(g,alpha)=c_g cos²(theta_g−alpha)`, with every usable actual whole-group axis supplying a reference column and all qualified groups retained as rows. Keep complete evidence; this support projection is not general M or a discovered organization cluster. The new recipe awaits user review and implementation.
6. Keep the furniture-group Frame package, Form+Scale package and whole-space arrangement-pattern package deferred until the `g→k` axis support layer passes review and specified-IFC validation. Do not derive them from individual-furniture frames or substitute absolute world/plane axes.

## Confirmed aggregate-output boundary

The user confirms that the higher-level axis aggregate must expose at least two independent observations:

- `direction_coherence`: how consistently the valid group axes point in the same undirected direction;
- `resultant_strength`: how much clarity-weighted directional evidence is present.

These outputs must not be collapsed into one score. Undefined/degenerate axes remain outside the directional resultant and are reported through coverage/status diagnostics. The current operator and normalization are the accepted implementation baseline; they are not a scientific calibration claim. The pairwise relation layer is a separate sublayer of the axis-only package, not an input to or extra vote in this global aggregate.

## Evidence-package output governance

The user confirmed the working direction that each evidence package may own its
output function. That function may derive package-level evidence from several
internal channels, but it must keep every original channel, state, source, and
provenance record intact. Derived outputs are additive and identify the input
channels they use; they do not replace the package's raw observations.

The shared field core now provides the internal `EvidencePackageOutput`
contract for retaining source envelopes beside package-derived channels. Each
output can describe its meaning, units, normalization method, optional range
and endpoints, and an optional shared `scale_id`. Normalization by itself does
not establish cross-package comparability: a shared scale requires an
explicitly reviewed semantic meaning. Outputs without such a scale remain
separate evidence. Cross-package fusion and its formula are not implemented.

The axis-only package now uses the reviewed operator
`R = sum(c_i * (cos(2 theta_i), sin(2 theta_i)))`, where `theta_i` is the
`overall_group_axis.angle` and `c_i` is its PCA clarity/strength in [0, 1].
The canonical additive outputs are `aggregate_direction`,
`direction_coherence = |R| / sum(c_i)` when at least two positive-clarity axes
contribute, `resultant_strength = |R| / N_valid`, `coverage`, and excluded-axis
diagnostics. Zero clarity is retained as valid data but has no direction
support; positive directional cancellation is `ambiguous`. Undefined,
degenerate, invalid, and non-finite axes do not contribute to `R`. The complete
scene result is diagnostic-only for all currently supplied authored groups and
does not infer membership or a higher-level group. The verified pinned-IFC
replay artifact supplies the source envelopes and same analysis-plane geometry;
no synthetic scene is used.

The axis-only potential aggregate and full-scope pair-relation package are implemented as described above. The source-axis `g→k` support views below and the arrangement runner are not implemented; the arrangement draft's absolute-axis proposal was withdrawn after user correction.

## No-fixed-region field protocol (2026-10-30)

The owner-reviewed source-axis draft supersedes the earlier external-only proposal prerequisite; user review is pending. For continuous `S(g,alpha)=c_g cos²(theta_g−alpha)` modulo 180°, every usable actual `overall_group_axis` supplies a reference view k. All qualified scope groups remain rows; all usable references remain columns, including exactly parallel aliases. No fixed region/K, radius, threshold, approximate merging or winner is introduced. These are usable overlapping axis-support views, not discovered true organization clusters; axis evidence cannot distinguish spatially separated parallel sets. The reference-conditioned projection preserves complete structured E, pair channels, states and provenance, and is not the final general M.

The fixed producer reads existing source envelopes; `EvidencePackage.evaluate(source_envelopes)` stays unchanged, with no proposal envelope framework or external/derived modes implemented first. Logical identity binds scene namespace, immutable anchor group ID, query/plane identity and recipe; canonical content fingerprints include scope/query/plane/source axes/envelopes and versions, not timestamps/revisions. Edit/undo can reuse original content. Each cell references both actual source axes through current lineage. Extent is absent/unspecified; no inside/outside or candidate-strength profile is invented. Anchor clarity remains separate; clarity means geometric anisotropy, not calibrated angular uncertainty.

Self support is computable and flagged, excluded from a non-self known-value mean with expected `N_scope−1`; unknown is not zero, computed zero support still counts toward coverage, singleton mean is unavailable and coverage inapplicable. Source-axis references need no LOO re-estimation; future derived-reference recipes require their own review. Separately, read-only `Q_k=ΣS(g,k)exp(i2theta_g)` describes the full soft view including self, using support once without multiplying clarity again. Report direction/coherence, sum of support, coverage, positive count, self weight/fraction and anchor_only; do not call anchor-only consensus, update the reference, or treat this as support validation. Zero support and cancellation keep explicit statuses. Unlike the existing global helper, this proposed descriptive operator permits a singleton resultant with coherence 1 when correctly flagged.

The scalar `Σc cos²` has only a constant and first doubled-angle harmonic, so crossing directions can flatten that scalar; preserve the full response matrix and do not claim mode discovery. This does not assert Q has the same moment restriction. Planned replay reuses the pinned IFC's retained 37 usable axes/geometry: 1,369 cells, 37 self and 1,332 non-self is a source-inventory expectation, not completed validation. No synthetic scene or new extraction. Full identity, formulas, evidence and the uncompleted review/implementation gates: [`identity/generation protocol`](../superpowers/specs/2026-10-30-group-axis-potential-field-identity-and-generation-protocol.md).
