# FreeSpaceField Preflight Review

Date: 2026-10-10

## What this review covers

This is a read-only preflight of the design in
`docs/project/free-space-field-instance-design.md` against the current
`analysis_scene_view` handoff, `geometry_views.py`, `field_core.py`, and the
existing occupancy tests. The review began before the red test draft landed;
the current snapshot includes `test/test_free_space_field.py`, while the
production implementation remains the owner-controlled follow-up.

The design keeps the correct boundary: exact-cell physical occupancy only,
no evaluator call, no resolver copy, no B3 read, and no clearance,
walkability, connectivity, or decay semantics.

## Must Fix

### 1. Freeze the input handoff; the current record shape is not enough

**Evidence:** `docs/project/free-space-field-instance-design.md:48-56` says
the field consumes `physical_occupancy` records with plan components,
represented ids, provenance, and unresolved owners. The actual handoff is
assembled in `features/neutral_scene_views.py:188-190,215-253`,
`_resolved_physical_occupancy` at `1291-1374`.

**Problem:** The selected records carry `geometry_components`,
`represented_source_ids`, `representation_status`, and
`representation_provenance`, while unresolved owners are returned separately
as `_analysis_view["physical_occupancy_unresolved_source_ids"]`. There is no
single immutable input object saying which query/operation produced the
components, whether the geometry is whole-height or section-qualified, or
whether an empty result is a qualified empty observation. A field that accepts
the raw dicts will have to guess across two containers and can accidentally
turn an absent record into empty.

**Minimum fix (owner decision):** Do not add a new upstream qualification
system or public `Frozen*` class. Require an explicit, small constructor
mapping/argument set containing:

- `domain` geometry and domain identity;
- `analysis_plane` and view transform/origin offset;
- `query_scope` (`whole_height` or explicit section);
- selected plan components, represented owner ids, and per-record
  representation status/provenance;
- unresolved owner ids and their reasons;
- a source/revision/schema fingerprint;
- `unresolved_source_ids`, passed explicitly and never defaulted to an empty
  collection.

Preserve the real selected-record values (`representation_status` is normally
`"original"` or `"accepted"`) and their existing provenance. Do not make
`FreeSpaceField` rediscover values from `_neutral_scene` or call
`resolve_source_representation`. The field consumes the existing handoff once,
without a second resolver.

**Reproducible case:** In
`test/test_physical_occupancy_resolution.py:72-77`, an invalid proxy coverage
leaves owner `A` in `_analysis_view["physical_occupancy_unresolved_source_ids"]`
while the returned `physical_occupancy` list contains only `B`. A constructor
that sees only the list returns a false empty for cells formerly covered by
`A`.

### 2. Specify domain clipping, holes, and the half-cell rule

**Evidence:** `docs/project/free-space-field-instance-design.md:41-47,81-110`
only says “cell lies outside the explicit domain” and “positive intersection”
with occupancy. `features/geometry_views.py:80-94,526-573` preserves
disconnected components and holes, while
`features/neutral_scene_views.py:719-730` derives only domain points and
`684-707` shifts component coordinates.

**Problem:** `analysis_scene_view` does not hand the field a canonical domain
polygon; it exposes domain availability and source records, while geometry
components can contain holes. For a cell that straddles a boundary or lies
entirely inside a hole, “outside” is undefined. If the implementation uses
the domain bounding box, a half-cell at the edge can be reported as
established empty outside the selected domain. If it uses `contains(cell
centroid)`, a valid partial cell can be discarded. If it uses “any positive
overlap,” the meaning of a boundary cell is different again.

**Minimum fix:** Carry the exact domain components, including holes, in the
field input and define one rule: a cell is in-domain when its footprint has
positive-area intersection with the selected domain; a cell with no positive
intersection is `outside`. Preserve the domain intersection area in support.
Use the same positive-area tolerance for domain and occupancy tests, and state
whether boundary-touch-only contact is ignored. Do not infer domain from
`_analysis_view["size"]` or `view_bounds_basis`; the latter explicitly records
`scene_geometry_fallback_not_analysis_domain` at
`features/neutral_scene_views.py:254-257`.

**Reproducible case:** Use an explicit rectangular domain with a hole and a
`0.5 m` lattice whose edge cell overlaps the domain by a sliver. The result
must be deterministic for the sliver, hole, and boundary-touch cases.

### 3. Preserve the shared analysis-plane transform

**Evidence:** `features/neutral_scene_views.py:239-242` records
`analysis_plane` and `origin_offset`; `684-707` shifts every component;
`710-716` projects into the plane. `features/geometry_views.py:97-124`
projects MassPatch geometry before component serialization.

**Problem:** The design says the field receives a “plan frame” but does not
say whether cell origins are in world coordinates or shifted analysis-view
coordinates. Passing world-space cells to shifted `physical_occupancy`
components yields systematic misses; applying the offset twice yields the
opposite error. This is especially easy to miss because exact-cell tests with
an origin at `(0, 0)` pass.

**Minimum fix:** Make the field's lattice and domain use the same canonical
coordinate frame as the supplied components, and put `origin_offset`,
plane id, and units in immutable provenance. Reject a query with a different
frame/plane instead of silently transforming it. A future explicit transform
operator can be separate; it is not needed for this slice.

**Reproducible case:** Translate the same scene so the view offset is non-zero,
then query the same logical cell in world coordinates and view coordinates.
Only the correctly declared frame may evaluate; the mismatch must be a
status-bearing result, not a shifted guess.

### 4. Do not let unresolved evidence erase known occupied cells

**Evidence:** The design's evaluation order at
`docs/project/free-space-field-instance-design.md:88-94` says positive
intersection returns `True`, then an unresolved source that can affect the
cell returns `unknown`. Existing behavior requires known positive occupancy to
survive overlapping uncertainty:
`test/test_b3_eye_plane_connectivity.py:58-67`.

**Problem:** A blanket “unresolved overlap => unknown” rule would regress the
existing invariant. For a cell covered by a known occupied component and also
covered by an unresolved source, occupancy is already decided as `True`; the
unresolved source matters only to the empty claim and must remain in
provenance/diagnostics.

**Minimum fix:** Use this decision rule:

- any qualified known positive overlap -> `value=True`, with the query's
  strongest valid status, and retain unresolved ids in support;
- no known positive overlap plus an unresolved source that could cover the
  cell -> `value=None`, `unknown`;
- no positive overlap and no affecting unresolved source -> qualified empty.

Add one focused test copied from the existing positive-interior-overrides-
unknown case.

### 5. Define whole-height empty qualification; do not equate “no components” with empty

**Evidence:** `features/geometry_views.py:125-176` returns empty components for
several height-band outcomes and records uncertainty. The section tests make a
legal empty explicit through `valid_empty_below_plane` at
`test/test_physical_occupancy_section.py:65-78`. The design claims a fully
qualified whole-height empty at
`docs/project/free-space-field-instance-design.md:103-110`, but the current
handoff has no explicit whole-height qualification field.

**Problem:** A selected record with `geometry_components == ()` can mean a
legal empty section, missing projection, invalid geometry, or a whole-height
record that was never qualified. The field cannot infer which meaning from
geometry alone. Returning `established, False` for all empty component lists
would certify unknown or invalid mass as free.

**Minimum fix (owner decision):** This slice accepts only resolved
whole-height plan inputs. An `original` record with valid non-empty
components may support an established occupied value. An `accepted`
substitute is conservatively `conditional` for the whole field, with a plain
explanation that the result is based on accepted substitute occupancy
geometry; do not infer conditionality from the `GeneratedProxy` string.
An explicit empty collection is established empty only when the input is
fully known and `unresolved_source_ids` is empty. A selected record with no
components is never a legal empty: missing/empty required geometry adds its
owner to unknown, while malformed coordinates/topology are invalid.

**Reproducible case:** Reuse
`test/test_physical_occupancy_section.py:65-78` and a missing/open proxy case
from `81-104`; both have no ordinary occupied plan component but must produce
different statuses.

### 6. Keep GeneratedProxy conditionality explicit and provenance-only

**Evidence:** The architecture says `GeneratedProxy` is a representation
provenance identifier, not a geometry kind. The design repeats that at
`docs/project/free-space-field-instance-design.md:58-72`, while the current
handoff stores `representation_status` and
`representation_provenance` at
`features/neutral_scene_views.py:1349-1357`.

**Problem:** A field must not infer `conditional` merely because the source
class or representation string is `GeneratedProxy`; conversely, it must not
promote a proxy to `established` without the upstream qualification scope.
The current design does not name the exact flag or provenance key that carries
that qualification.

**Minimum fix (owner decision):** Keep `representation_status` as the
resolver's existing `"original"`/`"accepted"` value and retain its
provenance. Map `"accepted"` to conservative `conditional` in this slice;
map a valid original record according to the known whole-height evidence.
`GeneratedProxy` remains provenance only. It is not a status discriminator.

**Reproducible case:** A valid generated proxy can be accepted for whole-height
physical occupancy, while an exact `world_xy` section proxy is only conditional
(`test/test_physical_occupancy_section.py:50-62`). The same representation
identifier must not decide both statuses.

### 7. Boundary doors are excluded only by upstream exact membership

**Evidence:** The design says boundary doors are closed support at
`docs/project/free-space-field-instance-design.md:74-77`. The real exclusion
path is exact declared membership in
`features/neutral_scene_views.py:733-777`, with selected ids passed into
`_resolved_physical_occupancy` at `180-190`.

**Problem:** If `FreeSpaceField` rechecks source class, name, role, opening
type, or geometry overlap, it can exclude an interior door or retain a
boundary member whose exact identity was unresolved. That violates the
architecture rule that only upstream `boundary_member_source_ids` establish
membership.

**Minimum fix:** The field should receive only the already-excluded boundary
owner ids and their diagnostic provenance, or consume records where boundary
support has already been removed. It must not inspect `_neutral_scene`, source
classes, names, or openings to decide exclusion. Add a test with an interior
door and a boundary door having the same class/name.

### 8. Query mismatch and unsupported planes need distinct status behavior

**Evidence:** `FieldQuery` currently carries free-form `frame`, `plane`, and
`height_band` in `features/field_core.py:50-75`, while the design defers tilted
planes/general height bands at `docs/project/free-space-field-instance-design.md:146-156`.
Existing exact-section validation rejects missing, non-finite, tilted, or
non-metre queries at `test/test_physical_occupancy_section.py:156-160`.

**Problem:** The six-state table only says malformed query is `invalid` and
missing domain is `not_available`. It does not define a valid query for the
wrong frame/plane, or a valid but unsupported plane. Without this distinction,
implementations may report `outside`, `not_available`, or silently reuse
whole-height geometry.

**Minimum fix (owner decision):** Freeze these rules:

- malformed target/query (wrong shape, non-finite values) -> `invalid`;
- absent domain/channel -> `not_available`;
- valid query whose frame/plane/height scope differs from the field's declared
  whole-height support -> `invalid` for fixed domain/frame mismatch, and
  `not_available` for a well-formed section, height-band, or tilted-plane
  request that this slice does not support; never evaluate with fallback;
- valid supported query with no domain intersection -> `outside`.

The concrete field should use one documented choice for “unsupported but well-
formed”; the simplest is `not_available` with an explanation.

## Should Fix

### 9. Make the handoff and sample provenance deterministic and immutable

`FieldSample` freezes its own payload and requires algorithm/schema versions at
`features/field_core.py:90-123`, which is good. The FreeSpaceField design
should additionally require domain id, plane id, origin offset, lattice
descriptor, source/representation ids, tolerance, and occupancy query scope in
the sample support/provenance. Otherwise two cells from differently shifted
views can compare equal after canonicalization.

The existing source records are ordinary dictionaries
(`features/neutral_scene_views.py:1349-1357`), so the field constructor must
deep-freeze a copied boundary, not retain live dict references.

### 10. Preserve exact-once semantics without rebuilding resolution

The resolver already performs exact-once owner accounting and fixed-point
uncertainty propagation at `features/neutral_scene_views.py:1358-1374`.
`test/test_physical_occupancy_resolution.py:80-82` verifies a many-to-one proxy
is counted once. The field should consume the selected target once and use
`represented_source_ids` only for audit/support; it must not union one geometry
per represented owner or re-run coverage logic.

A minimal test should assert that one proxy covering `A,B` produces one occupied
cell/support record, not two.

### 11. Keep invalid geometry distinct from absent geometry

`component_shape` skips invalid/empty polygons at
`features/geometry_views.py:80-94`, while adapter uncertainty records preserve
why geometry was missing or malformed. The field input must carry the upstream
reason, because an empty component list alone is ambiguous. Map malformed
handoff geometry to `invalid` and absent required occupancy evidence to
`not_available`/`unknown` according to the upstream record, never to empty.

## Can Be Deferred

- Spatial indexing or a faster batch path; `Field.evaluate_many` already has an
  ordered default in `features/field_core.py:160-165`.
- Arbitrary tilted planes, general height bands, clearance, route width,
  connectivity, and evaluator promotion; the design correctly leaves these
  out.
- A public serialized handoff schema. A private immutable constructor record is
  enough for this checkpoint, provided its fields are explicit and tested.
- Rich provenance class hierarchies. The existing frozen JSON-safe provenance
  in `field_core.py` is sufficient if the missing field-specific keys above are
  required.

## Minimum API Shape

Keep the existing generic `Field[Target, Value]` contract. Add only the
concrete constructor seam needed by this instance:

```text
FreeSpaceField(
    *,
    domain: FrozenDomainGeometry | None,
    lattice: FrozenLattice,
    occupancy: tuple[FrozenOccupancyRecord, ...],
    unresolved_source_ids: tuple[str, ...],
    query_scope: QueryScope,
    frame: str,
    plane: str,
    provenance: FrozenMapping,
)
```

`FrozenOccupancyRecord` needs exact plan components (including holes),
represented owner ids, an upstream qualification status/reason, and immutable
representation provenance. It must not contain a `NeutralScene`, resolver, or
evaluator reference.

The constructor may reject malformed records. Ordinary query/evidence failures
must return `FieldSample` statuses through `evaluate`; they must not be hidden
by exceptions or converted to `False`.

## Minimum Tests

Add focused tests for:

1. domain with a hole, disconnected components, boundary-touch, and a
   half-cell/sliver rule;
2. non-zero `analysis_scene_view` origin offset and frame mismatch;
3. known occupied plus overlapping unresolved evidence;
4. missing, invalid, legal-empty, and whole-height-qualified-empty records;
5. generated proxy whole-height versus section conditional scope;
6. exact declared boundary membership versus same-class interior door;
7. invalid query, unsupported plane, absent domain, and outside target;
8. many-to-one represented owners counted once and provenance retained;
9. scalar/batch equivalence and deep-frozen sample provenance.

## Verdict

**Preflight blocked until findings 1-8 are resolved in the concrete API and
focused tests.** The design boundary is sound and can stay small; the main
risk is not architecture drift but losing upstream qualification and
coordinate/domain semantics while converting the existing rich handoff into
exact cell samples.

## Red-test Draft Check

The new `test/test_free_space_field.py` confirms several useful minimum
behaviors: explicit domain holes, invalid versus unavailable construction,
known-positive-over-unknown handling, ordered batches, and missing/invalid
geometry. Two details must be corrected before using it to freeze the API.

### A. Whole-height input must not become a section result

`test_section_query_is_conditional_and_query_context_must_match` currently
constructs a field from ordinary whole-height `physical_occupancy` records and
then queries it with `plane={"axis": "z", "value": 1.6}`, expecting
`CONDITIONAL`. That is unsafe. The field has only plan components from the
whole-height handoff; it has no exact section geometry or section qualification
record. Returning `False, conditional` would claim that the cell is empty at
`z=1.6` by reusing whole-height evidence.

Change the test to require `NOT_AVAILABLE` with an “unsupported section
query” explanation. Do not add a section-qualified fixture in this slice:
section geometry handoff is deferred. The representation identifier alone
must not create conditionality.

### B. Red-test records are close, but not the full real-view contract

The helper record fields
`geometry_components`, `represented_source_ids`, `representation_status`, and
`representation_provenance` do correspond to selected records produced by
`features/neutral_scene_views.py:1349-1357`. However, real
`analysis_scene_view` places unresolved owners in
`_analysis_view["physical_occupancy_unresolved_source_ids"]`
(`features/neutral_scene_views.py:247-253`), not inside each occupancy record.
The draft's `unresolved_source_ids` constructor argument correctly models that
separate channel.

The implementation must not assume the draft's `"established"` value is what
the resolver emits: selected records carry the resolver status (normally
`"accepted"` or `"original"`), while inventory entries use
`"substitute"`/`"original"` and unresolved owners are separate. Preserve the
resolver value and map it once at the field boundary: accepted substitutes
make field results conservative `conditional`; valid originals may support
`established`. Also preserve `represented_source_ids` as audit support only
and never duplicate geometry per owner. A many-to-one proxy must remain one
selected record, as verified by
`test/test_physical_occupancy_resolution.py:80-82`.

### C. Validate polygons before `component_shape`

The helper in `features/geometry_views.py:80-94` silently skips invalid or
empty polygons. The field constructor must validate every supplied component
before calling it; otherwise one malformed component can disappear and make a
cell look free. Malformed coordinates/topology are `INVALID`, not empty.

## Owner-Frozen Minimum Boundary

The implementation is limited to the following decisions:

1. Constructor input explicitly contains exact domain components, pre-resolved
   occupancy records, explicit `unresolved_source_ids`, fixed query context,
   shifted view frame, and `origin_offset`/provenance. No `SourceObject`
   rescanning and no resolver copy.
2. Only resolved whole-height plan inputs are supported. Section,
   height-band, and tilted-plane requests return `NOT_AVAILABLE`; malformed
   input is `INVALID`; fixed domain/frame mismatch is `INVALID`.
3. Valid original non-empty components may yield established occupied values.
   Accepted substitutes are conservative `CONDITIONAL` for the field, with
   an explicit limitation explanation. Fully known original/explicit-empty
   inputs with no unresolved owners may yield established empty values.
4. Missing/empty selected geometry adds an unknown owner; malformed geometry
   is invalid. Known positive occupancy wins over unrelated unknown evidence,
   while unknown ids remain in support.
5. Domain clipping preserves holes and disconnected components. Boundary
   exclusion is consumed from upstream exact membership only. One selected
   geometry is counted once; represented owners remain audit coverage.
6. Changes are limited to the new field/tests and explicitly authorized
   documents.

No production code, architecture files, or Git index were changed by this
review. The report and the pre-existing red-test draft are the only review
artifacts considered here.

Not checked: the future `FreeSpaceField` implementation does not exist yet,
so runtime behavior and performance were not measured. Constitution remains
pending and no compliance claim is made.
