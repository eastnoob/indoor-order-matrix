# FreeSpaceField precision repair evidence

Date: 2026-10-10. Historical worker report: implementation and focused
regressions passed; owner acceptance was pending when this report was written.
Current owner disposition is recorded in the final review and implementation
evidence: the isolated US4 slice is accepted with no blocker in scope.

## Scope and ownership

Only these paths were written by this precision worker:

- `features/free_space_field.py`
- `test/test_free_space_field.py`
- This evidence file.

The prior implementation writer stopped code/test edits before this handoff.
No upstream resolver, evaluator, Field core, B3 loader, fixture JSON, dependency,
export, or runtime adapter was changed. No staging, commit, reset, or push was performed.
The shared checkout contains unrelated existing dirty work, preserved throughout.
Call-site search found the new focused tests as the only concrete-field callers.

## Repair decisions

- Domain and occupancy both use strict positive intersection area. Linear query
  tolerance is recorded but never compared against area. Holes, line/point contact,
  clipped-out mass, and a `1e-10` area sliver have explicit tests.
- Field metadata assignments retain the base `Field` protections. After construction
  all assignments/deletions are refused. Geometry caches and unknown inventories are
  tuples; nested consumed input and sample metadata are frozen copies.
- Selected record IDs and represented owner IDs must be nonempty strings. Repeated
  selected IDs, duplicate owners in one record, and owner overlaps between records
  invalidate the handoff. IDs are not silently converted to strings.
- Every sample retains input query context, actual query, frame, origin offset,
  boolean/geometry/area units, algorithm/schema revisions, and selected-record audit
  inventory. Each selected record keeps its own provenance without flattening or
  merging conflicting source dictionaries. Occupied samples identify intersecting
  selected records; empty samples retain the evaluated owner inventory. Known
  positive occupancy preserves unresolved IDs in provenance.
- Normal supported samples, empty cells, and outside-domain cells retain exact target,
  cell bounds, lattice, and domain intersection area. Empty remains a physical
  occupancy statement, not a walkability, clearance, or connectivity certificate.
- Constructor context must be whole-height with matching domain/frame and no section,
  height band, or demand. A normal `FieldQuery` is required. Malformed requests are
  `invalid`; well-formed unsupported sections, height bands, and demands are
  `not_available`, before missing-channel handling. Non-FieldQuery input raises an
  explicit TypeError. Optional plane refusal recognizes axis/value or origin/normal;
  height bands use a numeric two-element range and demands a nonempty mapping.
- Missing/None/empty selected geometry keeps its owners unknown; malformed geometry
  is invalid. An accepted substitute makes all computed booleans conditional;
  original geometry can establish values. Known positive mass wins over unlocalized
  unknown mass, while a potentially empty cell remains unknown.
- Real `analysis_scene_view` records include compatibility `Rect` objects, so freezing
  the entire mapping was a real integration bug. The field now freezes only consumed
  geometry, identity, selected-representation provenance/diagnostics, geometry refs,
  adapter refs, and source identity. Upstream absent representation provenance (`None`)
  normalizes to an empty audit mapping. No generic serializer was added.

## Actual scene integration

The old dictionary passthrough test was replaced with four actual `NeutralSceneV2`
fixtures sent through `analysis_scene_view`; tests never invoke `evaluate_scene`:

1. Furniture, plant, and counter mass all count while the plant/counter remain outside
   the furniture object bucket. All geometry is translated to a nonzero world origin.
2. Two originals use one accepted source-bound substitute exactly once, preserving
   selected target `T`, owners `A/B`, and the binding provenance.
3. An exact boundary-member door is excluded as closed domain support; another interior
   door with the same role remains physical occupancy.
4. A missing original source reaches unknown support while known other mass survives.

The explicit domain is projected only from `analysis_domain.geometry_refs` using
existing `mass_patch_from_mesh` / `plan_projection` helpers, then shifted by the view's
provided offset. Actual view convention is **projected coordinate + origin_offset**:
a world translation `(20, -30)` produces an offset `(-20, 30)`. The field applies no
second translation; both occupancy and explicit domain arrive in the same view frame.

## Commands and results

Red phase, before production repair:

```powershell
$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_field.py -q --tb=short
```

Result: **27 failed, 22 passed**. Initial actual-scene fixture extraction attempted a
floor record in a bucket that excludes domain support. After changing the test to
project the explicit domain refs, the same 27/22 split included four actual `Rect`
freezing failures. This corrected fixture run used `--tb=line`.

After primary repair: **48 passed, 1 failed**; remaining failure was the fixture's
incorrect offset-sign assertion. The test was corrected against `_view_frame` /
`_shift_point` source, after which **49 passed**.

After final focused edge checks (lattice finite bounds, domain identity/topology,
row/column ordering, mixed accepted/original limitation, existing manifest handoff):

```powershell
$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_field.py -q --tb=short
```

Result: **62 passed in 0.23s**, exit 0.

Final combined regression command:

```powershell
$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_field.py test/test_field_core.py test/test_space_field_adapter.py test/test_space_field_visualization.py test/test_discrete_space_field.py test/test_field_fixture_replay.py -q
```

Result: **136 passed in 5.16s**, exit 0 (62 new concrete-field checks plus original 74).
Timing is pytest wall-clock evidence for small fixtures, not a production benchmark.

### Owner follow-up: malformed occupancy container

Owner identified one additional input boundary: `tuple(physical_occupancy or ())`
treated falsey malformed containers as known empty. This was reproduced before
repair with `{}`, `""`, `b""`, and `0` (4 failed, 1 passed, 62 deselected):

```powershell
$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_field.py -q -k 'occupancy_container or generic_record_iterables' --tb=short
```

The constructor now explicitly rejects mappings/strings/bytes as the record
container and raises a named TypeError for noniterable input. `None` alone means
an absent channel; valid empty sequences and generic record iterables still work.
No other validation was expanded in this follow-up.

```powershell
$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_field.py -q
```

Latest focused result: **67 passed in 0.19s**, exit 0.

```powershell
$env:PYTHONPATH='.'; pixi run pytest test/test_free_space_field.py test/test_field_core.py test/test_space_field_adapter.py test/test_space_field_visualization.py test/test_discrete_space_field.py test/test_field_fixture_replay.py -q
```

Latest combined result: **141 passed in 5.53s**, exit 0 (67 concrete-field checks
plus original 74). Code/test writes stopped after this repair.

## Remaining scope

No live IFC/Blender execution, full repository suite, large-scene performance
benchmark, or rendered visualization was run. No evaluator/room-model promotion,
section computation, clearance, connectivity, Bayesian calibration, or decay was
added. B3 remains open. The constitution remains unratified; this work does not claim
its approval. Documentation synchronization and final acceptance belong to the owner.
