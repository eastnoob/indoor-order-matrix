# Indoor Layout Evaluation Matrix: Technical Spec And Operating Guide

## 1. Project Goal

Build a technical evaluation matrix for indoor layouts. The system starts from a 2D plan, extracts or accepts geometry and light semantic hints, computes quantitative layout descriptors, and produces an explainable metric table for design analysis, perception experiments, and later Rhino / Grasshopper / VisualARQ / BIM workflows.

This is not a paper-writing task. The useful output is an operational system:

1. represent furniture, groups, regions, paths, boundaries, column grids, and room envelopes;
2. compute order, alignment, connectivity, boundary, and spatial-force metrics;
3. visualize the result in notebooks;
4. record ambiguous cases instead of hiding them;
5. keep the same data model portable to Rhino / Grasshopper / BIM.

The current `order_analyzer` code already has useful pieces:

- `OrderAnalyzer` maps matrix cells into OCTA patterns.
- `FEATURE_TO_OCTA` currently exposes `shapes`, `custom_attr`, and `orientations`; OCTA itself also supports `boundingboxes`.
- `SceneModel`, `Rect`, `Polygon`, `Furniture`, `AffordanceBand`, `RoadBand`, `ClearanceBand`, and `EntryBand` already separate continuous geometry from sampled debug grids.
- `TableGrid`, `Road`, and `Entry` already show the correct API pattern: user intent first, internal geometry second, sampled grid only for explanation.

The next system should extend that pattern, not replace it.

## 2. Core Concepts

| Concept | What It Is | Input | Output | Computation | Uncertainty |
|---|---|---|---|---|---|
| `FurnitureObject` | One physical object: table, chair, sofa, cabinet, podium, plant, etc. | polygon/rect/circle, orientation, optional type | footprint, bbox, center, axis, affordance hints | geometry normalization; local frame from orientation or principal axis | object recognition may need manual picking or CAD/BIM metadata |
| `FurnitureGroup` | A repeated or functional cluster, e.g. table-chair group or sofa-table group | member objects, optional group id | group boundary, centroid, local axes, internal order | explicit group first; later soft clustering by distance/orientation/function | fully automatic grouping needs perception validation |
| `Region` | Area produced by furniture groups, boundary cues, or room subdivision | group boundaries, room boundary, soft boundary cues | polygon, local frame, region force field | convex hull / alpha shape / boundary-constrained polygon; local axes from PCA or boundary axes | region membership is fuzzy, not always binary |
| `Path` | Walkable negative space or explicit circulation object | room boundary minus blockers, entries, road intents | path polygon/network, widths, graph nodes | negative space, medial axis/Voronoi/skeleton, or explicit road bands | when a gap becomes a path is perceptual, not fixed |
| `Boundary` | General divider: wall, glass, cabinet, rug edge, material edge, color edge | curve/polygon, thickness, passability, visibility, cue type | boundary strength and graph constraints | convert each boundary into walk/see/grouping weights | transparent/visual/material boundaries need calibration |
| `RoomBoundary` | Outer envelope and openings | polygon/curves, doors/windows | bounded analysis domain | geometry containment, openings as entries | irregular/curved walls need polygon approximation first |
| `ColumnGrid` | Structural/reference grid, not sampled analysis grid | axes, columns, bays, optional levels | reference frame, bay cells, phase field | nearest-axis distance, bay coordinates, local grid vectors | irregular grids need local reference frames |
| `Order` | Regularity of comparable elements within a view | elements + feature projection + ideal/pattern | score and deviant map | OCTA where elements form a comparable matrix; local geometry metrics otherwise | full-room order is invalid if elements are not comparable |
| `Alignment` | Continuous agreement between directions, axes, centers, or phase fields | two force/frame descriptors | score in `[0,1]` plus vector evidence | angular similarity, distance-to-axis kernels, phase residuals | multi-axis objects can have multiple valid alignments |
| `SpatialForce / 势` | A weighted set of local dominant directions and attraction/constraint fields | objects, regions, paths, boundaries, column grid | vector/axis field, dominant directions | PCA, oriented bbox, boundary normals, path tangent fields, column grid fields | not a physical force; it is a descriptive field |
| `Connectivity` | How areas connect by walking or seeing | entries, path graph, boundaries, regions | reachability, shortest paths, detours, loops | graph metrics; visibility graph for seeing | graph construction depends on geometric precision |
| `Visibility` | Can see through/around space | boundary transparency, occluders, vantage points | visibility graph/isovist metrics | visibility graph or ray/isovist sampling | curved/transparent boundaries need approximation |
| `Walkability` | Can physically move through space | blockers, passability, entries | walk graph and width field | negative-space graph, navmesh/skeleton | human body width is a scale parameter |
| `Permeability` | Degree of crossing a boundary | boundary properties | pass/see weights | weighted graph edges | perception of partial permeability needs experiment |
| `Thickness` | Boundary or object physical thickness | width/offset/profile | solid zone, passability impact | buffer geometry | CAD layers may omit thickness |
| `Entrance` | Start/access opening | boundary edge, door/slot geometry | entry band/cells/nodes | current `EntryBand` pattern; later boundary opening object | interior openings need boundary association |
| `Local Coordinate Frame` | Coordinate system for one group/region/grid | axes or geometry | local x/y, origin, transform | principal axis, boundary edge, column-grid bay frame | multiple directions may be equally valid |
| `Global Coordinate Frame` | Drawing/model coordinates | CAD/Rhino/BIM units | scene coordinates | pass-through with unit metadata | imported drawings may have wrong scale |
| `Multi-scale Layout Structure` | Object -> group -> region -> room hierarchy | all objects and boundaries | nested graph | containment, grouping, adjacency | some memberships are soft or overlapping |

## 3. Data Structures

Use neutral Python dictionaries/dataclasses first. Rhino and BIM adapters can map their native objects into this model.

### 3.1 Furniture Object

```python
FurnitureObject = {
    "id": "table_01",
    "type": "table",                 # optional semantic label
    "geometry": Polygon | Rect,       # continuous footprint
    "bbox": Rect,
    "center": (x, y),
    "orientation": 0.0,
    "size": (w, h),
    "group_id": "north_table_group_01",
    "source": "manual|svg|rhino|bim",
    "metadata": {},
}
```

Required fields for first implementation: `id`, `geometry`, `center`, `orientation`, `size`. Type is useful but should not be required for geometry-only order views.

### 3.2 Furniture Group

```python
FurnitureGroup = {
    "id": "north_tables",
    "members": ["t1", "c1", "c2"],
    "geometry": Polygon,
    "local_frame": {"origin": (x, y), "x_axis": (dx, dy), "y_axis": (dx, dy)},
    "order_view": "octa_grid|geometry_group",
    "confidence": 1.0,
}
```

Groups can be manual first. Later automatic grouping should output confidence instead of a hard yes/no.

### 3.3 Region

```python
Region = {
    "id": "north_work_region",
    "boundary": Polygon,
    "members": ["north_tables"],
    "local_frame": {...},
    "boundary_sources": ["room_wall", "path_gap", "rug_edge"],
    "membership": {"north_tables": 1.0, "podium": 0.2},
}
```

Region membership should be allowed to be fuzzy. This handles cases where a path visually separates two zones but boundary cues visually bind them.

### 3.4 Boundary

Boundary is central and should be explicit.

```python
Boundary = {
    "id": "glass_wall_01",
    "geometry": Curve | Polygon,
    "kind": "wall|glass|cabinet|rug|material|color|visual|furniture",
    "thickness": 0.0,
    "walk_block": 1.0,        # 0 passable, 1 fully blocks walking
    "see_block": 0.0,         # 0 transparent, 1 opaque
    "grouping_strength": 0.8, # how strongly it creates region identity
    "continuity": 1.0,
    "openings": [
        {"id": "door_01", "geometry": Rect, "width": 900, "edge_param": 0.45}
    ],
    "source": "wall|furniture|surface_cue|manual|bim",
}
```

Boundary examples:

- rug edge: `thickness=0`, `walk_block=0`, `see_block=0`, high `grouping_strength`;
- low cabinet: positive thickness, `walk_block` high, `see_block` medium/low;
- glass wall: small thickness, `walk_block` high, `see_block` low, high continuity;
- wall: positive thickness, high walk and see block.

### 3.5 Path / Circulation

```python
PathNetwork = {
    "id": "main_negative_space",
    "mode": "walk|visibility",
    "geometry": [Polygon],
    "nodes": [{"id": "entry_main", "point": (x, y), "kind": "entry"}],
    "edges": [{"a": "entry_main", "b": "north_region", "weight": 0.74}],
    "width_field": "optional sampled/continuous descriptor",
}
```

Path should not be just sampled cells. Continuous negative space is the source; graph/sampling is an explanation or computation layer.

### 3.6 Column Grid

```python
ColumnGrid = {
    "id": "grid_A",
    "axes": [
        {"id": "x1", "geometry": LineString, "direction": (1, 0), "weight": 1.0},
        {"id": "y1", "geometry": LineString, "direction": (0, 1), "weight": 1.0},
    ],
    "columns": [{"id": "col_01", "point": (x, y), "size": (w, h)}],
    "bays": [{"id": "bay_01", "polygon": Polygon}],
    "local_frames": [],
}
```

Column grid is a reference field. It is not the OCTA grid and not the sampled grid.

### 3.7 Metric Matrix

```python
MetricMatrix = {
    "layout_id": "fixture_01",
    "unit": "mm|model_unit",
    "views": {
        "north_tables_order": {...},
        "sofa_region_geometry": {...},
        "circulation_connectivity": {...},
        "boundary_permeability": {...},
        "column_alignment": {...},
    },
    "uncertainties": [...],
}
```

Each metric should include `score`, `raw_values`, `evidence_geometry`, `method`, and `confidence`.

## 4. Layer Relationship Model

Use this hierarchy:

```text
RoomBoundary
  -> Boundary system
  -> FurnitureObject
      -> FurnitureGroup
          -> Region
              -> Region-internal path
  -> Inter-region path / negative space
  -> ColumnGrid reference field
  -> Global multi-scale spatial force
```

Relation types:

- Geometry: overlap, distance, containment, intersection, orientation, boundary touch.
- Topology: adjacency, reachability, graph connectivity, openings.
- Semantics: optional labels such as table, sofa, podium, rug.
- Perception: grouping strength, visual continuity, boundary cue strength.
- Function: affordance, walkability, visibility, access.

Design rule:

> Do not compute all metrics on one grid. Build multiple views, each with a valid comparison domain.

The north repeated table area in the fixture is valid for an OCTA-like view. The sofa areas are not the same kind of pattern and should be evaluated with group geometry and region-force descriptors.

## 5. Evaluation Matrix

Keep the matrix compact. First version:

| Family | Metric | Source | Output | Notes |
|---|---|---|---|---|
| A. Internal order | OCTA feature order | comparable objects in a local view | `[0,1]`, deviants | use for repeated arrays: north tables |
| A. Internal order | local position regularity | object centers in local frame | continuous score | spacing CV / phase residual, no hard threshold |
| A. Internal order | orientation consistency | object orientations | `[0,1]` | circular resultant length already exists in analyzer |
| A. Internal order | size / bbox consistency | object bbox classes or values | `[0,1]` | expose OCTA `boundingboxes` later |
| B. Region alignment | region force alignment | region axes / PCA / boundary axes | `[0,1]` | compare axis sets, not single global angle |
| B. Region alignment | centroid/edge phase | region frame relation | residual score | normalized by local scale |
| C. Column alignment | object/grid phase | objects vs nearest grid axis/bay | `[0,1]` | distance kernel, bay-relative not absolute |
| C. Column alignment | region/grid direction | region axes vs grid axes | `[0,1]` | supports non-orthogonal axes |
| D. Whole-space force | dominant direction agreement | groups, paths, boundaries, grid | vector summary | multi-scale weighted axes |
| D. Whole-space force | boundary axis concentration | boundary axes + length/thickness + walk/see/grouping weights | `[0,1]` | compare authored boundary-force variants without claiming calibrated perception |
| E. Connectivity | entry-to-region reachability | entries + path graph | weighted graph score | walk and visibility separated |
| E. Connectivity | detour / directness | path shortest path vs straight distance | continuous ratio | no pass/fail |
| E. Connectivity | loop/dead-end structure | graph topology | counts and normalized ratios | useful for circulation |
| F. Boundary | walk block strength | boundary properties | continuous weight | walls/cabinets/glass/rugs differ |
| F. Boundary | visibility block strength | boundary transparency | continuous weight | separate from walking |
| F. Boundary | grouping cue strength | material/color/rug/wall cues | continuous weight | perception-sensitive |

### A. Region Internal Order

Workflow:

1. Select a valid `OrderView`, e.g. north tables.
2. Create local coordinate frame from region boundary, column grid, or object distribution.
3. Project objects into local frame.
4. If objects form a rectangular/repeated comparable set, use OCTA:
   - `shapes` for object categories;
   - `orientations` for direction;
   - `classlabels` / `custom_attr` for grouping labels;
   - future: `boundingboxes` for size consistency.
5. If not OCTA-compatible, compute geometry order:
   - orientation consistency;
   - spacing regularity;
   - symmetry around local axis/center;
   - enclosure/around-center score for sofa groups.

Important: a slanted region is not judged against global X/Y. Its local frame comes from its own boundary, dominant furniture axis, or column grid.

### B. Region-To-Region Alignment

Each region produces a force descriptor:

```python
RegionForce = {
    "axes": [(angle, weight), ...],
    "centroid": (x, y),
    "extent": (major, minor),
    "boundary_axes": [...],
}
```

Alignment is the weighted similarity of axis sets and position phase:

- axis similarity: `abs(cos(theta_diff))` or multi-axis max/weighted match;
- phase similarity: normalized distance between projected centroids/edges;
- scale normalization: use region extent or column bay size, not fixed meters.

No hard "angle < X" rule. Output a continuous score and raw angle residuals.

### C. Region / Column Grid Alignment

Column grid is a reference field:

- regular grid: axes and bays are explicit;
- non-orthogonal grid: local grid directions come from nearest axes;
- incomplete grid: use nearest available axes with confidence;
- irregular grid: use local frame interpolation from nearby axes/columns.

Metrics:

- object-to-axis phase: how close object centers/edges are to axis/bay centers;
- region-to-bay fit: overlap between region polygon and bay polygons;
- direction alignment: region axes vs local grid axes;
- force agreement: weighted comparison between region force and grid force.

### D. Whole-Space Force

Whole-space force should not be a single angle unless the layout has one dominant direction.

Compute:

1. group-level axes;
2. region-level axes;
3. path tangent axes;
4. boundary axes;
5. column grid axes;
6. weighted aggregate histogram over directions.

Output:

- global dominant axes;
- local force map by region;
- agreement scores: furniture vs path, furniture vs boundary, furniture vs column grid.

### E. Path Connectivity

Two path systems should be separated:

- walkability graph: blocked by walls/furniture/high `walk_block`;
- visibility graph: blocked by opaque/partially opaque boundaries using `see_block`.

Candidate methods:

- negative-space polygon: room boundary minus furniture/blocking boundaries;
- medial axis / Voronoi / skeleton: derive path centerlines;
- visibility graph / isovist: visual connectivity;
- graph metrics: reachability, shortest paths, detour, loops, dead ends.

Do not start with full computational geometry complexity. First notebook can use manually drawn path polygons and graph edges. Later replace manual path with automatic negative-space extraction.

### F. Boundary Metrics

Boundary affects:

- region belonging: grouping cue;
- walking: passability;
- seeing: visibility;
- alignment: boundary tangent/normal as local force;
- connectivity: openings become graph edges.

Boundary score fields:

```python
BoundaryMetrics = {
    "continuity": 0.0..1.0,
    "walk_block": 0.0..1.0,
    "see_block": 0.0..1.0,
    "grouping_strength": 0.0..1.0,
    "opening_ratio": opening_length / boundary_length,
    "force_axis": angle/axis set,
}
```

## 6. Avoiding Hard Thresholds

Use continuous metrics first. Only classify later for display if necessary.

Strategies:

1. Normalize by current layout scale:
   - distance / median object size;
   - distance / local bay size;
   - width / local furniture module.
2. Use kernels instead of thresholds:
   - alignment: `abs(cos(angle_diff))`;
   - distance affinity: `exp(-(d / local_scale)^2)`;
   - phase residual: `1 / (1 + residual_cv)`.
3. Use soft grouping:
   - group membership as probability/weight;
   - boundary grouping strength as weight.
4. Use multi-scale analysis:
   - object scale;
   - furniture group scale;
   - region scale;
   - room scale.
5. Output raw values with confidence:
   - do not force "good/bad" where perception is unknown.

Parameters that cannot be eliminated:

| Issue | Why It Cannot Fully Disappear | Preferred Handling |
|---|---|---|
| human body clearance | real body size and code standards matter | store as profile; use continuous width ratio |
| when a gap becomes a path | perceptual and functional | output path-likeness score; validate by experiment |
| boundary cue strength for rug/color | perceptual | expose continuous cue weight; calibrate by experiment |
| transparent boundary visibility | material and lighting dependent | use `see_block` weight; BIM/material metadata if available |
| automatic group recognition | ambiguous in mixed scenes | manual first; soft clustering later |

## 7. Resolution And Units

Do not use one universal resolution.

### Units

Use real model units whenever available:

- 2D notebook: arbitrary units, but declare scale, e.g. `1000 SVG units = room width`.
- Rhino: model units from document.
- BIM/VisualARQ: BIM object units.
- Pixel image: pixels are only tracing input, not final unit.

### Resolution Layers

| Layer | Resolution | Purpose |
|---|---|---|
| continuous geometry | exact or polygon approximation | source of truth for objects, boundaries, paths |
| OCTA matrix | semantic/order view resolution | compare repeated elements |
| column grid | bay/axis resolution | reference frame |
| sampled debug grid | adjustable | visualization, approximate reachability, heatmap |
| graph network | nodes/edges | connectivity metrics |

Existing work already learned this lesson: sampled grid should explain geometry, not define geometry. Keep that rule.

### Relationship Description

Object relations should be described in continuous geometry and graph terms:

- distance between footprints;
- center/edge alignment;
- overlap;
- containment;
- nearest boundary/axis;
- graph reachability;
- visibility edge;
- membership weight.

Grid matrices are projections for specific questions, not the universal representation.

## 8. Implementation Flow

The target workflow is automatic evaluation from a structured 2D plan, not a manually typed object table. The first reliable input format is structured SVG because it is simple, inspectable, and maps cleanly to Rhino / BIM adapters later.

1. Input a 2D layout.
2. Parse or import neutral geometry:
   - structured SVG with `id`, `class`, and `data-*` attributes is the first automated path;
   - Rhino / VisualARQ adapters should produce the same neutral records later;
   - manual object declaration is only a fallback/debug path, not the completion target.
3. Build a continuous `Scene`:
   - room boundary;
   - furniture objects;
   - furniture groups;
   - boundary objects;
   - openings / entries;
   - optional column grid.
4. Build object groups:
   - read explicit group ids when present;
   - infer soft groups from distance, orientation, boundary cues, and repeated structure when group ids are absent.
5. Build regions:
   - read explicit region polygons when present;
   - infer candidate regions from group hulls, boundaries, path-likeness gaps, and room envelope.
6. Build path / negative-space network:
   - continuous negative space is room boundary minus positive blockers;
   - entries / openings determine which negative-space components become candidate circulation;
   - graph and sampled views are explanations, not the geometric source of truth.
7. Build metric views:
   - OCTA order views for repeated comparable sets;
   - geometry group views for sofas/non-grid areas;
   - boundary view;
   - column alignment view;
   - connectivity view.
8. Compute metrics.
9. Output:
   - `MetricMatrix` table;
   - raw evidence values;
   - SVG/notebook overlays;
   - uncertainty log.
10. Run a short grill-me style pass:
    - Which metric relies on semantics?
    - Which metric relies on a threshold?
    - Which result changes under scale/resolution?
    - Which result needs perception validation?
11. Run the notebook and tests. If they fail or the evidence graphic contradicts the metric table, update the spec or implementation and rerun. Completion requires a passing loop, not a one-shot draft.

## 9. Notebook / IPYNB Test Plan

Use the existing fixture:

- `test/floorplan_order_fixture.svg`

Implemented first executable fixture notebook:

- `test/floorplan_order_matrix_demo.ipynb`

Detailed notebook acceptance criteria are tracked separately in:

- `docs/indoor_layout_evaluation_matrix_notebook_test_plan.md`

Notebook cells:

```python
# 1. Load or display the SVG fixture.
from IPython.display import SVG, display
display(SVG(filename="test/floorplan_order_fixture.svg"))

# 2. Parse neutral 2D objects from structured SVG attributes.
scene = load_structured_svg_scene("test/floorplan_order_fixture.svg")

# 3. Define metric views.
views = [
    OrderView(id="north_tables_order", mode="octa_grid", members=north_tables),
    MetricView(id="west_lounge_geometry", mode="group_geometry", members=west_lounge),
    MetricView(id="center_lounge_geometry", mode="group_geometry", members=center_lounge),
    MetricView(id="circulation", mode="path_graph", members=[]),
]

# 4. Compute and display the metric matrix.
matrix = evaluate_layout(scene, views)
display(matrix.to_dataframe())

# 5. Visualize evidence layers.
display(scene_overlay_svg(scene, matrix))
```

First notebook target:

- display fixture;
- parse structured SVG into a `Scene`;
- compute a small metric table by straightforward functions;
- show overlays for regions, local axes, path, and metric evidence;
- list uncertainty items.

Current notebook evidence:

- `test/floorplan_order_matrix_demo.ipynb` executes with `nbformat` / `nbclient`.
- It displays the fixture SVG.
- It calls the structured SVG loader and no longer manually declares the main fixture object table.
- It outputs prototype metric rows for order, lounge/armchair geometry, region alignment, column alignment status, whole-space force, path connectivity, boundary metrics, and uncertainties.
- It renders an evidence overlay SVG.
- It outputs an uncertainty table.

Do not implement automatic PNG/image recognition before structured SVG works. The first completion target is automatic evaluation from structured SVG, not arbitrary computer vision.

Test cases to include:

1. current fixture: mixed repeated tables + lounges + boundary + doors;
2. slanted boundary case: region local frame differs from global frame;
3. irregular room case: non-rectangular boundary;
4. missing/partial column grid case;
5. rug boundary case: grouping without walk blockage;
6. glass wall case: visual pass, walk blocked.

## 10. Rhino / Grasshopper / BIM Migration

### Rhino

Map neutral geometry to Rhino:

- `Polygon` -> closed `Curve` / `PolylineCurve` / `Brep`;
- `Rect` -> rectangle curve or planar Brep;
- `Boundary` -> curve with user attributes;
- `ColumnGrid` -> line curves + point/column geometry;
- `PathNetwork` -> curves + graph table.

Use RhinoCommon geometry operations for intersection, containment, offsets, and area. Keep metric code independent from Rhino types by converting at the boundary.

### Grasshopper

Use DataTrees:

```text
{layout;objects}       FurnitureObject records
{layout;groups}        group membership
{layout;regions}       region polygons
{layout;boundaries}    boundary records
{layout;paths}         graph edges / curves
{layout;metrics}       metric matrix rows
```

Grasshopper components should be thin adapters:

1. collect geometry;
2. assign or read attributes;
3. call evaluator;
4. display overlays and tables.

### VisualARQ / BIM

Possible mappings:

- wall -> `Boundary(kind="wall", walk_block=1, see_block=1)`;
- glass wall/window -> boundary with lower `see_block`;
- door -> boundary opening / `Entry`;
- space/room -> `RoomBoundary` or `Region`;
- column -> `ColumnGrid.columns`;
- furniture block/family -> `FurnitureObject`.

Manual / automatic split:

| Item | First Version | Later |
|---|---|---|
| room boundary | manual or BIM room | automatic from walls/spaces |
| furniture | manual pick / block metadata | object recognition |
| groups | manual ids | soft clustering |
| boundaries | manual/BIM types | material-driven boundary weights |
| openings | manual/BIM doors | automatic topology |
| column grid | manual axes | infer from columns |
| paths | manual sketch | negative-space skeleton/navmesh |

## 11. Uncertainty Register

| Uncertainty | Why It Is Uncertain | Affects | Handling |
|---|---|---|---|
| how far apart means "not one region" | depends on function, scale, and perception | region grouping/path split | output continuous separation score; perception experiment later |
| how wide a path must be to split regions | human/body/code/perception | path and region metrics | width ratio and path-likeness; no hard class first |
| rug/color/material boundary strength | perceptual grouping | boundary/grouping | literature + experiment |
| transparent boundary visibility | material/light/viewpoint | visibility graph | `see_block` weight, BIM material if available |
| irregular region principal direction | may have multiple axes | alignment/order | axis set, not single angle |
| irregular column grid force | no global x/y | column alignment | local grid frame interpolation |
| whether order and alignment double count | metrics can correlate | metric matrix | output families separately; later correlation/PCA in perception study |
| full automatic furniture grouping | scene dependent | groups/regions | manual first, confidence-based auto later |
| positive/negative space road definition | leftover space is not always road | connectivity | path-likeness score + entry connectivity |

## 12. Current Fixture Interpretation

The current test fixture is:

- north: repeated table-chair groups, valid for OCTA-style order;
- north wall: small table;
- west lower: two sofas + one coffee table;
- center lower: two sofa groups;
- east lower: armchairs + coffee table;
- east middle: podium/work table;
- boundaries: room shell, partial internal wall, door openings;
- circulation: soft negative-space layer for later path testing.

This fixture is good because it contains both easy order and hard order:

- easy: north table array;
- hard: sofa clusters, mixed sizes, boundary/path relations.

## 13. Next Implementation Plan

Minimal next batch:

1. Keep `test/floorplan_order_matrix_demo.ipynb` as the visual test carrier.
2. Add structured metadata to `test/floorplan_order_fixture.svg`.
3. Add a minimal `load_structured_svg_scene()` helper that derives the fixture object table from SVG metadata.
4. Add a tiny local metric table, no broad framework:
   - `north_tables_order`: OCTA-compatible projection;
   - `west_lounge_geometry`: sofa/table group geometry;
   - `center_lounge_geometry`: two sofa groups;
   - `east_armchair_geometry`: armchair/table grouping;
   - `boundary_summary`;
   - `path_placeholder`.
5. Visualize:
   - object ids;
   - group boundaries;
   - local axes;
   - metric evidence.
5. Record uncertainty rows directly in notebook.

Implementation should reuse existing `Rect`, `Polygon`, `SceneModel` patterns where possible. Avoid adding a large new evaluator framework until one notebook proves the metric rows are useful.

## References Used For Technical Positioning

- OCTA is suitable for feature-based order/complexity over comparable visual elements, not as a whole-building semantic evaluator. See the OCTA project page and manual:
  - https://elinevg.github.io/OCTA/
  - https://elinevg.github.io/OCTA_manual/
  - https://link.springer.com/article/10.3758/s13428-022-01900-w
- Space syntax / visibility graph / isovist methods are relevant for visibility and connectivity, not furniture order itself. See:
  - https://spacegroupucl.github.io/depthmapX/
  - https://www.spacesyntax.online/software-and-manuals/depthmap/building-spatial-model/
- RhinoCommon / Grasshopper migration should happen through neutral geometry records, not by coupling the evaluator directly to Rhino or BIM objects. See:
  - https://developer.rhino3d.com/api/rhinocommon/rhino.geometry
  - https://developer.rhino3d.com/api/grasshopper/html/M_Grasshopper_DataTree_1_Add_1.htm

## 14. Method Selection Matrix

This section is the technical filter. The system should not import every theory into the first implementation.

| Method / Theory | Use In This Project | Do Not Use For | Reason |
|---|---|---|---|
| OCTA feature order | repeated, comparable element sets: north tables, chair arrays, modular furniture | whole-room semantic scoring | OCTA counts feature-pattern deviants; it needs comparable elements and a projection |
| Local geometric order | sofa clusters, armchairs, non-grid groups | replacing OCTA where a clean repeated matrix exists | simple geometry covers non-OCTA clusters without fake semantics |
| PCA / oriented bbox | local frame for groups/regions, dominant axis extraction | treating multi-axis regions as one-axis objects | cheap and robust first pass; output confidence when axes are ambiguous |
| Column-grid phase field | furniture/region relation to structural grid | sampled grid scoring | column grid is a reference frame, not analysis cells |
| Negative-space geometry | candidate walkable area and path-likeness | final human route prediction | leftover space is only a candidate path; entries and width field matter |
| Medial axis / Voronoi / skeleton | later path centerline extraction | first notebook | useful but implementation-heavy; manual path polygon is enough for fixture v1 |
| Visibility graph / isovist | visibility and visual connectivity | furniture group order | good for seeing, not for layout regularity |
| Space syntax graph metrics | region/path integration, depth, choice | object-level furniture scoring | helpful at path/room scale after path graph exists |
| Shape grammar / layout grammar | future generative design constraints | first evaluation matrix | too heavy before metrics are validated |
| Perceptual grouping / Gestalt | boundary cue strength, grouping ambiguity | hard deterministic grouping | useful as a conceptual basis; requires calibration |

Immediate adoption:

- OCTA for valid order views.
- Continuous geometry for objects, groups, regions, boundaries.
- Weighted graph for walk/visibility connectivity.
- Column grid as a reference field.

Deferred:

- automatic image recognition;
- full skeletonization;
- exact polygon boolean for arbitrary curved CAD;
- perception-calibrated boundary weights.

## 15. Metric Cards With Computation Details

Each metric should be implemented as a small card:

```python
MetricCard = {
    "id": "...",
    "family": "order|alignment|connectivity|boundary|force",
    "input": "...",
    "output": {"score": 0.0, "raw": {}, "evidence": []},
    "normalization": "...",
    "uncertainty": "...",
}
```

### 15.1 OCTA Order View

Use when objects can be projected into a matrix or list with comparable features.

Input:

- objects;
- view-local row/column index;
- ideal/pattern feature values;
- feature list: `shape`, `orientation`, `classlabel`, later `boundingbox`.

Score:

```text
score = 1 - deviants / n
```

where `deviants` comes from OCTA `CalculatePatternDeviants` or a local equivalent when a feature is not exposed by the wrapper.

Evidence:

- deviant cells;
- feature deviants per dimension;
- view-local matrix.

Failure mode:

- invalid if the objects do not form a comparable set. Example: do not compare north tables, sofas, podium, and armchairs in one OCTA view.

### 15.2 Position Phase Regularity

Use when objects are repeated but not necessarily in a strict matrix.

Input:

- object centers in local frame;
- reference axes from region, group, or column grid.

Computation:

```text
sort projected coordinates along axis
gaps = adjacent differences
cv = std(gaps) / mean(gaps)
score = 1 / (1 + cv)
```

This avoids a hard spacing threshold. Perfect equal spacing gives score near `1`; irregular spacing decreases continuously.

### 15.3 Orientation Consistency

Input:

- object orientations.

Computation:

```text
score = length(mean(unit vectors of doubled angles if 180-degree symmetry applies))
```

Use doubled angles for furniture where 0 and 180 degrees should be equivalent; use normal angles when facing direction matters.

Uncertainty:

- chairs and podiums may have directed orientation; tables/sofas may be axis-symmetric.

### 15.4 Group Compactness

Input:

- member footprints;
- group boundary.

Computation:

```text
compactness = occupied_area / group_boundary_area
```

Normalize by comparing the current group to its own local scale. Do not say compactness is "good" by itself; store it as a descriptor.

### 15.5 Sofa / Seating Enclosure

Use for sofa and armchair groups where order is "around a conversational center", not grid repetition.

Input:

- seat centers;
- seat orientations if known;
- coffee table center or inferred group center.

Computation:

```text
center = coffee_table.center if present else centroid(seat centers)
radial_vectors = normalize(center - seat.center)
facing_score = mean(max(0, cos(angle(seat.forward, radial_vector))))
angular_balance = 1 / (1 + circular_gap_cv(angles around center))
distance_balance = 1 / (1 + cv(distances_to_center))
enclosure_score = mean(facing_score, angular_balance, distance_balance)
```

If orientations are unknown, omit `facing_score` and renormalize.

### 15.6 Region Force Alignment

Input:

- region force descriptor A;
- region force descriptor B.

Force descriptor:

```python
{"axes": [{"angle": deg, "weight": w}], "centroid": (x, y), "scale": s}
```

Axis matching:

```text
axis_score = weighted_mean(max(abs(cos(angle_i - angle_j))) for each axis_i)
```

Position phase:

```text
phase_score = 1 / (1 + normalized_centroid_or_edge_residual)
```

Final:

```text
alignment = weighted_mean(axis_score, phase_score)
```

No binary aligned/not-aligned judgment.

### 15.7 Column Grid Alignment

Input:

- object/region geometry;
- column grid axes/bays.

Scores:

```text
axis_distance_score = exp(-(distance_to_nearest_axis / local_bay_size)^2)
bay_center_score = exp(-(distance_to_bay_center / local_bay_size)^2)
direction_score = max(abs(cos(region_axis - grid_axis)))
```

Output each component separately before aggregating. This prevents hiding whether the object is direction-aligned but offset.

### 15.8 Path-Likeness / Region Split

This addresses the "XXX width gap" problem without a hard threshold.

Input:

- gap polygon between groups/regions;
- entries;
- negative-space graph;
- local human/furniture scale profile.

Compute descriptors:

```text
width_ratio = gap_min_width / local_scale
continuity = path_length_through_gap / direct_distance
entry_connection = graph_weight(entry, gap)
boundary_reinforcement = boundary_cue_strength_along_gap
path_likeness = weighted_mean(width_ratio_kernel, continuity_score, entry_connection)
```

Then use path-likeness as a continuous value:

- high path-likeness separates regions more strongly;
- low path-likeness behaves like internal spacing;
- boundary grouping can counteract path-likeness.

Region split tendency:

```text
split_tendency = path_likeness * (1 - grouping_strength_across_gap)
```

This is the correct form for "path separates, but boundary can pull things back together."

### 15.9 Boundary Strength

Boundary is multi-channel:

```text
boundary_strength = weighted_mean(
    walk_block,
    see_block,
    grouping_strength,
    continuity,
    material_or_color_cue
)
```

Do not collapse boundary into "wall/not wall". Keep channels separate and aggregate only for a named question:

- region grouping: prioritize grouping strength and continuity;
- walkability: prioritize walk block and openings;
- visibility: prioritize see block and transparency.

### 15.10 Connectivity

Use graph scores.

Nodes:

- entries;
- region centroids;
- group centroids;
- path junctions;
- openings.

Edges:

- walk edges weighted by passability and width;
- visibility edges weighted by transparency and occlusion.

Metrics:

```text
reachability(region) = max_path_capacity(entry -> region)
detour(region_a, region_b) = shortest_path_length / euclidean_distance
dead_end_ratio = dead_end_nodes / total_nodes
loop_ratio = independent_cycles / total_edges
```

Keep walk and visibility graphs separate. Glass wall: low walk connectivity, high visibility connectivity.

## 16. Positive / Negative Space Protocol

The user's "剩余的部分是道路吗" issue should be handled as follows:

```text
positive space = furniture footprints + blocking boundaries + fixed obstacles
negative space = room boundary - positive space
candidate path = negative space connected to entries and having sufficient continuous width as a continuous descriptor
```

Important:

- negative space is not automatically road;
- road/path is a role assigned by connectivity, width field, and relation to entries/regions;
- leftover dead corners remain negative space but can have low path-likeness.

First implementation:

1. manually draw or declare `path_placeholder` polygon for the fixture;
2. compute path descriptors against entries and regions;
3. later replace with automatic negative-space extraction.

## 17. Region Construction Protocol

Region construction must be layered because region is partly geometric and partly perceptual.

Inputs:

- furniture group hulls;
- room boundary;
- boundary cues;
- path-likeness gaps;
- optional manual region polygons.

First version:

```text
region = manual polygon + member ids + boundary_sources
```

Second version:

```text
candidate regions = soft clusters of furniture groups
membership_weight = function(distance, orientation similarity, boundary cues, path split tendency)
```

Membership:

```text
same_region_affinity =
    distance_affinity
    * orientation_affinity
    * semantic_affinity_optional
    * boundary_grouping_across_gap
    * (1 - split_tendency)
```

No hard "distance < X means group" rule.

## 18. Fixture Object Table For Structured SVG

The current SVG fixture should expose enough `id`, `class`, and `data-*` metadata for the loader to derive this object table automatically. The table below is the expected parsed result and a human audit target, not the primary input method.

| ID Pattern | Type | Region | Geometry Source |
|---|---|---|---|
| `north_table_r{1..2}_c{1..3}` | table | north_tables | SVG `<rect class="table">` groups |
| `north_chair_*` | chair | north_tables | SVG `<circle class="chair">` groups |
| `north_small_table` | table | north_wall | SVG `g#north_small_table` |
| `west_sofa_1`, `west_sofa_2` | sofa | west_lounge | SVG `g#west_lounge` |
| `west_coffee_table` | table | west_lounge | SVG `g#west_lounge` |
| `center_sofa_group_1_*` | sofa/table | center_lounge | SVG `g#center_lounge` upper pair |
| `center_sofa_group_2_*` | sofa/table | center_lounge | SVG `g#center_lounge` lower pair |
| `east_armchair_left/right` | armchair | east_armchairs | SVG `g#east_armchairs` |
| `east_coffee_table` | table | east_armchairs | SVG `circle.table` |
| `east_work_table` | podium/work table | east_work | SVG `g#east_work` |
| `room_boundary` | boundary | room | outer SVG path |
| `internal_partition` | boundary | room | thin wall |
| `bottom_entry`, `right_entry` | entrance | room | door arcs |

Manual object declaration is allowed only as a debug fallback. The main notebook must use the structured SVG loader once the automatic path is implemented.

## 19. Validation And Experiment Route

This project has two validation levels.

### Technical Validation

Use notebooks and tests:

- parsed objects match visible fixture;
- metric matrix rows are reproducible;
- OCTA view is only used for comparable sets;
- changing sampled/debug resolution does not change continuous descriptors;
- Rhino/BIM adapters can produce the neutral data model.

### Perception Validation

Use later experiments:

- whether path-likeness correlates with perceived region separation;
- whether boundary grouping strength matches human grouping judgments;
- whether sofa enclosure metrics match perceived order;
- whether column-grid alignment scores correlate with perceived order/coherence;
- whether order and alignment should be combined or kept separate.

Issues needing literature search before experiment:

- space syntax / VGA for visual connectivity descriptors;
- environmental psychology / territorial cues for rug/material boundaries;
- perceptual grouping for region membership;
- furniture layout grammar only after metric descriptors stabilize.

## 20. Concrete Next Work Items

Do these in order:

1. Make `test/floorplan_order_fixture.svg` machine-readable with stable metadata.
2. Implement `load_structured_svg_scene()`.
3. Implement `evaluate_scene(scene)` for the current fixture metric rows.
4. Convert `test/floorplan_order_matrix_demo.ipynb` to call the automatic loader and evaluator.
5. Add tests that fail if the notebook returns to a manually typed fixture object list.
6. Expose OCTA `boundingboxes` as a wrapper feature only after the north-table fixture needs size-order scoring.
7. Add Rhino/GH/BIM adapter stubs only after the neutral `Scene` generated from SVG is stable.

## 21. Reverse Analysis And Forward Design Protocol

The same metric matrix should support both directions, but not with equal maturity.

### 21.1 Reverse Analysis

Input:

- existing plan geometry;
- optional object labels and group ids;
- optional boundary/entry/column-grid metadata.

Pipeline:

```text
layout geometry
  -> neutral objects / boundaries / entries / column grid
  -> groups and regions
  -> metric views
  -> metric matrix + evidence overlays + uncertainty log
```

Best-supported metrics:

- order of repeated objects;
- group compactness/enclosure;
- boundary pass/see/grouping descriptors;
- region-column alignment;
- path/connectivity descriptors.

Reverse analysis is the first product because it can be validated on real layouts and perception experiments.

### 21.2 Forward Design

Input:

- target metric ranges;
- room boundary;
- required object inventory;
- optional column grid and boundary constraints.

Pipeline:

```text
target metric matrix
  -> generate candidate groups / regions
  -> place objects under constraints
  -> evaluate same metric matrix
  -> optimize / compare alternatives
```

Metrics suitable for generation:

- spacing regularity;
- orientation consistency;
- column-grid phase;
- entry-to-region reachability;
- boundary passability constraints.

Metrics less suitable for direct generation now:

- perception-calibrated region belonging;
- rug/material boundary strength;
- social meaning of lounge arrangement;
- semantic podium/frontness unless user supplies program intent.

Design rule:

> Forward design uses the same evaluators as reverse analysis, but generation should only target metrics whose meaning is technically stable.

## 22. Whole-Space Force Aggregation Recipe

Whole-space force is a multi-scale descriptor, not one final vector.

### 22.1 Build Component Forces

For each layer:

```text
furniture group force = group local axes weighted by group area/member count
region force = region axes weighted by region area
path force = path tangent axes weighted by path length/connectivity
boundary force = boundary tangent axes weighted by continuity/grouping strength
column force = grid axes weighted by bay/axis confidence
```

### 22.2 Aggregate Into Direction Histogram

Use an angle histogram over `[0, 180)` for axis-symmetric forces.

```text
for each force axis:
    add weight to nearest/smoothed angle bin
normalize histogram by total weight
```

Output:

- dominant direction list;
- entropy / concentration of directions;
- pairwise agreement:
  - furniture vs column;
  - furniture vs boundary;
  - path vs column;
  - region vs boundary.

Do not hide local conflict behind one global score. A room can have a strong north-table field and a different lounge field.

## 23. Adapter Payload Examples

### 23.1 Rhino Adapter Payload

```python
rhino_payload = {
    "unit": "millimeter",
    "objects": [
        {"id": guid, "geometry_type": "ClosedCurve", "target": "FurnitureObject"},
    ],
    "boundaries": [
        {"id": guid, "geometry_type": "Curve", "target": "Boundary"},
    ],
    "columns": [
        {"id": guid, "geometry_type": "Brep|Point", "target": "ColumnGrid.columns"},
    ],
}
```

Adapter responsibility:

1. read Rhino object geometry and attributes;
2. convert to neutral `Rect` / `Polygon` / curve representation;
3. attach source ids for round-trip debugging;
4. never put RhinoCommon objects inside metric functions.

### 23.2 Grasshopper DataTree Payload

```text
{0;objects;i}      object records
{0;groups;i}       group records
{0;regions;i}      region polygons
{0;boundaries;i}   boundary records
{0;entries;i}      entry records
{0;column_grid;i}  axes / bays / columns
{0;metrics;i}      metric result rows
```

Each item should be JSON-like data plus geometry references. Grasshopper components should be wrappers around the same neutral evaluator.

### 23.3 VisualARQ / BIM Payload

```python
bim_mapping = {
    "Wall": "Boundary(kind='wall', walk_block=1, see_block=1)",
    "CurtainWall|Window": "Boundary(kind='glass', walk_block=1, see_block=low)",
    "Door": "Entry or Boundary.openings[]",
    "Space|Room": "RoomBoundary or Region",
    "Column": "ColumnGrid.columns[]",
    "Furniture": "FurnitureObject",
}
```

Manual fields likely still needed:

- boundary grouping strength for rugs/material/color zones;
- furniture group ids when BIM families do not encode usage;
- region membership when spaces are open-plan and not modeled as rooms.

## 24. Uncertainty Decision Table

| Uncertainty | Current Output | Literature Search | Perception Experiment | User Parameter |
|---|---|---|---|---|
| gap becomes path | `path_likeness` continuous score | space syntax, path width studies | yes, perceived separation | optional scale profile |
| furniture clusters become one region | soft membership / affinity | Gestalt grouping, environmental psychology | yes | optional manual group id |
| rug/material boundary strength | boundary grouping strength | territorial cue / surface cue literature | yes | yes |
| transparent boundary | separate `walk_block` and `see_block` | visibility/isovist literature | maybe | material metadata |
| irregular region main direction | axis set with confidence | computational geometry / shape descriptors | no first pass | no |
| irregular column grid force | local grid frame interpolation | architectural grid / CAD references | no first pass | manual axes |
| order vs alignment overlap | keep metric families separate | statistics after dataset | yes, correlation with perception | no |
| social meaning of podium/front | output geometry descriptors only unless program intent supplied | design cognition / classroom layout | likely | semantic program input |

Rule:

> If an uncertainty is perceptual, do not convert it into a hard rule. Output a continuous descriptor and record the uncertainty route.

## 25. Final Deliverables Checklist

The completed system must deliver an automated technical evaluation workflow, not only a written design. Current documents and the fixture notebook are supporting material.

Completion requires:

1. a structured 2D plan fixture: `test/floorplan_order_fixture.svg`;
2. an automatic SVG-to-scene loader that reads object, group, region, boundary, opening, and column-grid metadata from SVG attributes;
3. a neutral `Scene` model independent from SVG, Rhino, or BIM APIs;
4. an `evaluate_scene(scene)` pipeline that produces a compact metric matrix;
5. OCTA-backed order views only for comparable repeated sets, such as the north table array;
6. non-OCTA geometry / topology metrics for sofa groups, armchairs, podium/work table, boundaries, and circulation;
7. evidence overlays showing parsed objects, inferred groups/regions, local frames, path/negative-space descriptors, and metric evidence;
8. an executable notebook that calls the automatic loader and evaluator instead of manually constructing the object table;
9. tests that fail if the notebook falls back to manual object declaration for the main fixture;
10. a Rhino / Grasshopper / VisualARQ migration section that maps native objects into the same neutral `Scene`;
11. a prompt coverage audit that marks implementation status honestly as `implemented`, `documented only`, or `deferred`.

The current fixture notebook now uses the automatic loader/evaluator path and is useful evidence for the metric direction, but it is not sufficient for final completion because many geometry, graph, visibility, and Rhino/BIM adapters remain prototype-level or deferred.

## 26. Master Execution Spec To Reach Full Completion

This section is the controlling spec for the remaining work. It supersedes earlier wording that treated a notebook-only prototype as complete.

### 26.1 Scope Boundary

The final system evaluates structured layout geometry. It does not need to solve arbitrary raster image recognition. The expected input sources are:

1. structured SVG for notebook testing;
2. Rhino / Grasshopper geometry records later;
3. VisualARQ / BIM object records later.

The evaluator must not depend on a single sampled grid. Continuous geometry is the source of truth. OCTA matrices, column grids, and sampled debug grids are separate projections for specific questions.

### 26.2 Required Architecture

Use the smallest set of modules that gives a real automated workflow:

```text
structured SVG
  -> Scene loader
  -> neutral Scene
  -> metric view builders
  -> evaluate_scene(scene)
  -> MetricMatrix rows
  -> notebook evidence overlays
```

Minimum public functions:

```python
scene = load_structured_svg_scene("test/floorplan_order_fixture.svg")
matrix = evaluate_scene(scene)
svg = scene_metric_overlay_svg(scene, matrix)
```

Manual constructors may remain for debugging, but the main fixture notebook must use the automatic loader.

### 26.3 Execution Process And Required Skills

Use the Superpowers workflow to prevent another premature completion claim:

1. Use `superpowers:writing-plans` to create short per-phase implementation plans.
2. Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to execute each phase.
3. Use `superpowers:verification-before-completion` before claiming any phase or the whole goal complete.
4. Use `grill-me` as a compact adversarial checklist, not as an open-ended discussion loop.
5. Use `academic-paper` only as a structure and argument-completeness review lens. Do not convert this deliverable into an academic paper.
6. Use `paperjury` only as an adversarial technical review lens for brittle metrics, unsupported assumptions, and weak validation.

Execution rule:

```text
plan phase -> write tests/checks -> implement minimum slice -> run tests/notebook
  -> if failing, revise implementation or spec -> rerun
  -> only then mark phase complete
```

Re-run brainstorming only when the design direction changes, for example switching from structured SVG to Rhino-first input or adding arbitrary image recognition. Do not restart full brainstorming for ordinary implementation failures.

### 26.4 Implementation Phases

Phase A: correct documentation state.

- Mark the current state as a prototype, not complete.
- Keep the existing fixture notebook, but label it as automatic prototype evidence.
- Keep the audit clear that automatic SVG-to-matrix is implemented for the current structured fixture, while robust CAD/BIM geometry remains open.

Phase B: make the SVG fixture machine-readable.

- Add stable `id`, `class`, and `data-*` attributes to the fixture SVG.
- Required metadata:
  - object role: `table`, `chair`, `sofa`, `armchair`, `coffee_table`, `podium`, `boundary`, `opening`, `column_axis`, `region`;
  - group id;
  - region id;
  - optional local order view id;
  - optional pass/see/grouping weights for boundaries.

Phase C: implement the loader.

- Parse only the SVG shapes used by the fixture first: `rect`, `circle`, `ellipse`, `polygon`, `path` when simple enough, and `g` metadata inheritance.
- Convert them to the existing lightweight continuous geometry records where possible.
- Preserve source ids for overlays and debugging.
- Skip unsupported SVG elements with an uncertainty row, not a crash, unless they are required for the fixture.

Phase D: implement the first automatic metric pipeline.

- `north_tables_order`: build an OCTA-compatible local matrix from parsed table/chair groups.
- `west_lounge_geometry`, `center_lounge_geometry`, `east_armchair_geometry`: compute group geometry descriptors, not OCTA.
- `boundary_connectivity`: compute walk/see/grouping descriptors from boundary and opening metadata.
- `column_alignment`: compute only if column axes exist; otherwise emit `not_available` with reason.
- `uncertainties`: output unresolved semantic or perceptual assumptions.

Phase E: convert the notebook.

- The notebook must call `load_structured_svg_scene()` and `evaluate_scene()`.
- It must display the original fixture, parsed scene overlay, metric matrix, and evidence overlay.
- It must not manually type the main object table.

Phase F: self-cycle review and repair.

- Run notebook execution and pytest.
- Run a grill-me style checklist:
  - Does any metric pretend semantics that are not present?
  - Is OCTA used outside a comparable view?
  - Does a sampled grid affect a continuous metric?
  - Does a threshold hide an uncertainty that should be reported?
- Run an academic-paper style structure check only for argument completeness: terms, assumptions, evidence chain, and references.
- Run a paperjury style adversarial check: find metrics that are brittle, overfitted, untestable, or not portable to Rhino/BIM.
- If any check fails, edit the spec or implementation and rerun. Do not mark complete until the loop passes.

### 26.5 Acceptance Tests

Minimum automated checks:

1. `load_structured_svg_scene("test/floorplan_order_fixture.svg")` returns non-empty objects, groups, boundaries, entries, and regions.
2. The north table view is automatically derived from SVG metadata and returns an OCTA-backed score.
3. Sofa and armchair regions return geometry-backed metric rows and are not evaluated by OCTA.
4. `evaluate_scene(scene)` returns a matrix with stable row ids:
   - `north_tables_order`;
   - `west_lounge_geometry`;
   - `center_lounge_geometry`;
   - `east_armchair_geometry`;
   - `boundary_connectivity`;
   - `uncertainties`.
5. Notebook source contains `load_structured_svg_scene` and does not manually define the full fixture object list.
6. Notebook executes with `nbformat` / `nbclient` and saves outputs.
7. Overlay SVG contains source object ids, group ids, region ids, and metric evidence ids.
8. Prompt coverage audit has no row marked `documented only` for the automated SVG-to-matrix path.

### 26.6 Non-Goals Until The Above Passes

- Arbitrary PNG/raster object recognition.
- Full CAD path boolean for every SVG path command.
- Full shape grammar or generative layout.
- Rhino / VisualARQ plugin UI.
- Perception-calibrated final weights.

These are valid later work, but adding them before structured SVG automation would expand scope without proving the core evaluator.
