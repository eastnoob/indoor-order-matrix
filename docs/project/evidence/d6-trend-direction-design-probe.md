# D6 furniture-group trend direction design-only comparison

- Status: **design probe complete; STOP FOR TREND ESTIMAND REVIEW**
- Schema: `d6-trend-direction-design-probe/v1`
- Runner: [`run_trend_direction_probe.py`](../../scripts/design/group_level/run_trend_direction_probe.py)
- Fixture: [`trend_direction_fixtures.json`](../../scripts/design/group_level/trend_direction_fixtures.json)
- Truth: [`trend_direction_truth.json`](../../scripts/design/group_level/trend_direction_truth.json)
- Results: `outputs/design/trend_direction_probe/trend_direction_results.json`
- Full exact-group inventory: `outputs/design/trend_direction_probe/trend_direction_inventory.json`
- Artifact manifest: [`d6-trend-direction-artifact-manifest.json`](d6-trend-direction-artifact-manifest.json)
- Renderer: [`render_trend_direction_probe.py`](../../scripts/design/group_level/render_trend_direction_probe.py)

This is a design-only comparison. It does not freeze a trend estimand, rename a production field, replace a production function, or select a winner.

## Inputs and scope

The probe read `AGENTS.md`, the architecture memory, the D6 group self-description records, the programming prompt, and the existing real-IFC smoke report (`docs/project/evidence/d6-ifc-three-group-smoke-report.md`), inventory, description, and manifest. It inspected the current implementations of `_furniture_group_frame`, `_pca_frame_stats`, `_member_frame_consensus`, `_directions`, and `_representative`.

The real source is `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`. The probe inventories all 37 `IfcGroup` records, keeps only exact `ObjectType == "furniture_group"`, and scans groups in stable source-id order until three complete Analysis-footprint groups are found. This is a different policy from the existing smoke artifact's first-three selection.

Selected complete groups:

| Group | Members | Status |
|---|---:|---|
| `ifc-group:0WEjP61oTMbOLVcpUvUD7i` | 2 | computed |
| `ifc-group:1MjgmtdBrGMeDxpe0HfC5h` | 3 | computed |
| `ifc-group:1NlcVLoeXPOeA7YFm0NjMG` | 3 | computed |

The first 12 geometry-probed groups were skipped because one or more Analysis polygons were classified `unsupported_holes`. Their exact member reasons are preserved in the machine-readable result. The metadata inventory covered all 37 groups; 22 later groups were not tessellated after the three-group stopping condition was met. No group was repaired, filled, treated as missing, or replaced with a nicer sample.

The source SHA-256 before and after the probe was `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`.

## Four separately named estimands

### A. `member_orientation_consensus`

**Estimand.** Consensus of each valid member footprint's own principal orientation. For member `i`, the polygon covariance gives

`theta_i = 1/2 atan2(2 Cxy, Cxx - Cyy)`.

The current slice uses `anisotropy_i = sqrt((Cxx-Cyy)^2 + 4 Cxy^2) / trace(C_i)` and `w_i = area_i * anisotropy_i`. It reports the independent four-angle frame `R4 = sum(w_i exp(4 j theta_i)) / sum(w_i)` and two-angle axis `R2 = sum(w_i exp(2 j theta_i)) / sum(w_i)`. `group_frame` is modulo 90 degrees; `group_axis` is modulo 180 degrees. `coherence` is resultant concentration/strength, never a probability.

**Input and center.** Valid member polygon covariance; the frame has no group center dependency.

**Strengths.** Answers “which way do the furniture bodies themselves face?” and is insensitive to member placement when member shapes are unchanged.

**Failure examples.** A square/circle has near-zero anisotropy and an uninformative angle. Holes and invalid members propagate invalid group status. A partial group can expose a usable-subset diagnostic only; it is excluded from winner comparison.

### B. `legacy_projected_point_cloud_pca`

**Estimand.** The old `_furniture_group_frame` PCA input semantics: one unweighted point cloud made from all `extents` rectangle points plus all member `_record_points`. The probe records point counts, whether affordance extents were present, and member footprint counts. The historical cloud therefore gives every recorded vertex one point weight; boundary tessellation can change its influence.

**Center and formula.** Arithmetic mean of the assembled points, then `_pca_frame_stats` and the major eigenvector angle modulo 180 degrees.

**Production timing.** `_furniture_group_frame` always computes this PCA statistics record. When member frame weight is positive, the old function emits `member_frame_consensus` as its actual angle/strength and keeps this PCA as `geometry_angle`/clarity diagnostic. When member frame weight is zero, the PCA angle becomes the fallback output with basis `affordance_group_pca_frame`. It is therefore not the same output as A when member direction support exists.

**Strengths and failure examples.** It exposes the shape of the projected point cloud and can diagnose affordance envelope orientation. It is sensitive to point density, point selection, and affordance/member mixing; it is not an area estimator. Real probe groups had no external affordance extents, so their B cloud contains only Analysis member footprint vertices.

### C. `area_weighted_total_covariance_pca`

**Estimand.** Principal direction of the area distribution of the whole group. The center is the area-weighted group center `sum(A_i c_i) / sum(A_i)`. The covariance is explicitly `total = within + between`, where within is area-weighted member shape covariance and between is area-weighted centroid placement covariance. Its axis is modulo 180 degrees and its `strength` is eigenvalue anisotropy, not probability.

**Strengths.** Tessellation-invariant for the same polygonal region and captures both body shape and placement spread. It can be dominated by a long row of centers even when member bodies face another way.

**Failure examples.** An invalid/holes member makes the complete group result invalid in this probe. Near-isotropic total covariance has weak/undefined direction.

### D. `between_member_centroid_pca`

**Estimand.** Principal direction of member centers alone. It uses the same area-weighted group center and weights `A_i / total_support_area`, but removes all within-member shape covariance. The axis is modulo 180 degrees and its `strength` is eigenvalue anisotropy, not probability.

**Strengths.** Directly answers “which way are the member placements arranged?” and separates layout direction from body orientation.

**Failure examples.** One member or coincident centers have zero between covariance. Equal or symmetric center placement can be isotropic even when bodies are directional. Invalid/partial status follows the same input state policy.

## Deterministic fixture observations

| Case | A member orientation | B legacy cloud | C total area covariance | D centroid placement | Observation |
|---|---:|---:|---:|---:|---|
| aligned members, vertical centers | 0° frame | 90° | 90° | 90° | body orientation and spatial layout are orthogonal |
| aligned members, horizontal centers | 0° | 0° | 0° | 0° | all quantities agree when layout follows body axis |
| mixed 0°/90° members, horizontal centers | 0° frame; 2θ axis coherence near zero | 0° | 0° | 0° | frame and axis must stay separately named |
| near-isotropic squares | raw angle retained with near-isotropic diagnostic | 0° | 0° | 0° | angle is not informative when member anisotropy is near zero |
| area/shape disparity | 0° | 90° with low clarity | 0° | 90° | area weighting and within-member covariance change the result |
| sparse/dense tessellation | 0° | point count 52 | 0° | 0° | A/C/D are region based; B is vertex-count sensitive |
| affordance extent mixed into legacy cloud | 0° | 33.6° with low clarity | 0° | 0° | B reports the mixed input semantics explicitly |
| holes / invalid | no complete result | no complete result | no complete result | no complete result | only usable-subset partial diagnostic is retained |
| missing / partial | no complete result | no complete result | no complete result | no complete result | missing is not silently converted to valid geometry |

## Real IFC observations

The three complete groups expose clear disagreements between member orientation and placement/shape in the serialized result. For the first selected group, A is about 89.99° modulo the current frame representation, while C and D are about 0° and B is about 3.44°. The other two groups have A frame about 39.15° and A axis about 129.15°, while C/D are about 128.10°/128.10° and B is about 128.55° or 127.66°. These are parallel descriptions, not a winner decision.

The existing smoke sample's first three source-id groups were not reused because they were partial/invalid under the explicit holes policy. Their `unsupported_holes` reasons remain visible in this probe's skipped list.

## Rendering and verification

Blender was run with the required portable executable in background/factory-startup mode. It consumed `trend_direction_results.json`; the renderer does not recompute metrics. The two images show member footprints, area-weighted group center, A in green, C in orange, D in purple, and B in cyan. Invalid/partial panels are marked and do not show a complete trend result.

- Synthetic image: `outputs/design/trend_direction_probe/synthetic_trend_direction.png`
- IFC image: `outputs/design/trend_direction_probe/ifc_trend_direction.png`
- Blend: `outputs/design/trend_direction_probe/trend_direction_probe.blend`

The runner assertions passed, saved JSON/schema/source/image verification passed, PNG dimensions were checked, and both images were visually inspected. `git diff --check` and explicit Git scope audit were run before handoff. The complete command/output record and hashes are in the artifact manifest.

## Decision boundary

This experiment keeps A, B, C, and D as distinct descriptions. It does not select a winner, call coherence or strength a probability, change formal trend names, edit `features/`, `adapters/`, tests, NeutralSceneV2, public APIs, dependencies, source IFC, or the user's open Blender/Bonsai model.

**STOP FOR TREND ESTIMAND REVIEW**
