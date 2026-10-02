# D6 trend implementation design review

Status: **APPROVE IMPLEMENTATION DESIGN; PRODUCTION IMPLEMENTATION DEFERRED**

This document turns the approved owner decision into an implementable design.
It does not modify production code, adapters, NeutralSceneV2, public APIs,
tests, source IFC, or Blender files.

## 1. What the current code already provides

- `features/group_self_description.py` already computes additive member area,
  area-weighted center, within-member covariance, between-member covariance,
  total covariance, and the A-style four-angle/two-angle member consensus.
- `features/scene_inference.py::_furniture_group_frame` is a legacy comparator.
  It builds a vertex point cloud, computes a PCA diagnostic, and may emit
  `member_frame_consensus` as its final historical result.
- `adapters/ifc_bonsai.py` extracts both Body and Analysis representations and
  currently replaces the original furniture object's geometry references with
  Analysis references while also serializing an `analysis_substitute` source
  object.
- `features/analysis_substitute_discovery.py` can discover explicit substitute
  records, but it is not yet the authoritative consumer-side resolver.
- `NeutralSceneV2.SourceObject` already has open JSON `factual_properties` and
  `provenance` mappings, so a first implementation can carry typed bindings
  without changing the dataclass shape.

## 2. Frozen implementation decisions

### 2.1 Typed function-specific substitute binding

The normalized source-object contract will carry a list under
`factual_properties["OM_FunctionSubstitutes"]`:

```json
[
  {
    "substitute_id": "ifc-object:<source-global-id>:analysis",
    "consumer": "trend",
    "substitute_kind": "MassPatch",
    "analysis_role": "analysis_geometry_substitute",
    "representation_identifier": "Analysis",
    "provenance": {
      "source_global_id": "<source-global-id>",
      "extraction_method": "ifcopenshell_analysis_representation",
      "world_transform_applied": true,
      "visibility_policy": "analysis_only"
    }
  }
]
```

The record is a binding, not geometry. `substitute_id` must resolve to a
separate `SourceObject` in the scene. The target source object must have
`source_role="analysis_substitute"`, a matching `geometry_refs` entry, and the
same typed provenance. A source object may have several bindings for different
consumers.

The trend resolver accepts a binding only when the shared registry matches all
of the following:

- `consumer == "trend"`;
- `substitute_kind == "MassPatch"`;
- `analysis_role == "analysis_geometry_substitute"`;
- `representation_identifier == "Analysis"`;
- `substitute_id` is unique and resolves to geometry;
- source IFC and world-transform provenance are present or explicitly
  unavailable.

Names, layers, `source_role` alone, display labels, and Body records never
authorize trend geometry. Body geometry may remain available for audit and
other consumers, but the trend resolver cannot fall back to it.

### 2.2 Shared registry placement

The design-only registry in
`scripts/design/group_level/trend_substitute_registry.json` becomes the source
for the implementation contract. Its semantic keys and display metadata stay
separate. The production implementation should reuse the existing
`analysis_substitute_discovery.py` module by adding the typed resolver there,
rather than creating a second discovery system.

The resolver returns an auditable mapping with `accepted`, `rejected`,
`not_available`, or `ambiguous` status. It never silently selects the first
candidate.

### 2.3 Descriptor names and schema boundary

The current production keys `group_frame` and `group_axis` already describe A
member-orientation consensus. They must not be silently repurposed to mean C.
The implementation evidence namespace will add:

```text
trend_descriptors:
  overall_group_axis   # C: total area covariance, modulo 180 degrees
  member_frame         # A: four-angle consensus, modulo 90 degrees
  member_axis          # A: two-angle consensus, modulo 180 degrees
  layout_axis          # D: between-centroid covariance, modulo 180 degrees
  legacy_diagnostic    # B/legacy, never a formal trend
```

Existing `group_frame` and `group_axis` fields remain compatibility aliases for
the current A semantics until a separate deprecation decision. No consumer may
infer C from the old field names.

### 2.4 C, A, and D formulas

For a complete valid group, reuse the existing representative moments:

- `C = within_member_covariance + between_member_covariance`;
- C direction is the major eigenvector of `C`, modulo 180 degrees;
- D direction is the major eigenvector of `between_member_covariance`, modulo
  180 degrees;
- C and D deterministic strength are
  `(lambda_primary - lambda_secondary) / (lambda_primary + lambda_secondary)`;
- A keeps the existing area-times-member-anisotropy weighting, with 4θ frame
  and 2θ axis resultants.

Strength/coherence are deterministic geometric evidence. They are never
probabilities or posterior uncertainty.

If the trace is below the declared geometry degeneracy tolerance, angle is
`null` and direction status is `undefined`. A partial, invalid, or unavailable
group cannot expose a complete formal trend. Any usable-subset numeric result
is nested under diagnostic evidence and is not consumed as the group descriptor.

### 2.5 Geometry and source status

Reuse the existing status distinctions:

- `computed`: all required proxy members are valid;
- `partial`: some optional/declared members are unavailable; formal descriptor
  fields remain unavailable unless the contract explicitly marks the result as
  diagnostic;
- `invalid`: a required member is malformed or has unsupported holes;
- `not_available`: no usable typed Analysis geometry;
- `not_evaluated`: no eligible authored furniture group.

Invalid is never rewritten as missing, and no numeric zero is fabricated.
Additive area, center, and covariance remain the representative facts. Polygon
union and overlap aggregation stay outside this implementation slice.

## 3. Proposed implementation units

### Unit A: typed substitute resolver

Extend `features/analysis_substitute_discovery.py` with a resolver that accepts
`NeutralSceneV2`, a source-object id, a consumer key, and the registry. It must
return the resolved Analysis `SourceObject` plus provenance or an explicit
failure status. Add tests for accepted Analysis, Body spoofing, wrong role,
missing geometry, duplicate ids, and ambiguous multiple trend bindings.

### Unit B: trend descriptor calculation

Keep geometry moment calculation in `features/group_self_description.py` and
add a small covariance-axis helper. It consumes only resolved trend substitutes
and writes `trend_descriptors`. It must not call the legacy point-cloud PCA to
produce C. The legacy function remains a comparator and compatibility path.

### Unit C: IFC binding integration

Update the IFC adapter in a later implementation checkpoint to serialize the
typed binding from the Analysis representation to the owning furniture source
object and to preserve the separate Analysis source object. The adapter must
keep raw IFC property names in provenance while exposing normalized consumer,
kind, role, and representation fields.

### Unit D: SVG 2D parity

The SVG adapter may provide the normalized trend binding and 2D geometry facts.
It cannot claim Z, 3D clearance, or opening/barrier capabilities. SVG parity
compares eligibility, area, center, covariance, angles, and status only.

### Unit E: Blender output

The preview renderer reads `trend_descriptors`, registry display metadata, and
provenance. It renders Analysis footprints and separate vectors for C, A, D,
and legacy diagnostics. It does not recompute geometry, change status, or
choose a winner.

## 4. Test and review contract

Before production integration, the implementation design must specify tests for:

1. exact `furniture_group` eligibility and context exclusion;
2. typed Analysis resolution and Body rejection;
3. C covariance-axis formula, center anchoring, translation/rotation behavior,
   isotropic undefined state, and tessellation invariance;
4. A frame/axis harmonic separation and D placement-only behavior;
5. invalid/missing/partial/not-available propagation;
6. legacy parity showing final legacy output is separate from B diagnostic;
7. IFC Analysis binding and source/body provenance;
8. SVG 2D parity and unavailable 3D channels;
9. Blender output-only rendering and registry display labels;
10. full existing regression suite with no public `room_analysis_model` change.

## 5. Explicit non-goals

This design does not implement inferred-group candidate selection, automatic
space roles, inter-region gap-path synthesis, Bayesian inference, ML,
psychological calibration, IFC write-back, or a production selector.

## Review result

The design is internally consistent with the owner estimand decision and the
existing Neutral Scene contract. It is ready for an implementation plan and a
separate implementation approval gate. Production code must remain unchanged
until that plan is reviewed.

**STOP FOR IMPLEMENTATION DESIGN REVIEW**

