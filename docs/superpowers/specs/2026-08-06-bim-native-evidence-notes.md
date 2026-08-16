# BIM Native Evidence Notes

Date: 2026-08-06

This note records the current shared direction for the indoor layout matrix work. It is not an implementation spec.

## Current Progress

We have converged on one important point:

- The user should draw or import real BIM objects and surfaces.
- The analyzer should derive boundary, region, path, and relation evidence from those objects.
- Boundary is not a manually authored object class in the first instance. It is an emergent analysis result.

## Current Design Commitments

### What the user provides

- walls, columns, furniture, cabinets, sofas, chairs
- carpet or floor covering
- floor elevation changes or platform edges
- glass, partitions, openings
- column grid axes and other authored structural references

These are factual BIM inputs.

### What the analyzer derives

- boundary evidence from height, continuity, permeability, and geometry
- surface cues from carpet, color fields, and continuous floor regions
- level-change boundaries from elevation differences
- furniture groups and activity regions
- gap paths between regions
- grid bays and grid relations
- subject-cue relations and matrix evidence rows

These are BIM-native analysis objects, not ad hoc JSON fields.

## Boundary Principle

Boundary should be treated as a role, not a hard object name.

A sofa back, cabinet edge, carpet edge, glass partition, or wall face can all emit boundary evidence if their geometry and attributes support it.

The analyzer should not ask, "Is this a boundary object?"
It should ask, "Does this object or surface emit boundary evidence here?"

## Column Grid Principle

Column grid is user-authored input, not automatically inferred by default.

The analyzer may derive grid bays, local influence, and region-grid relations from the authored axes, but it should not invent the grid as the primary workflow.

## What This Means For Software Structure

- VisualARQ or Rhino: modeling and authoring entry point
- IFC / IfcOpenShell / Bonsai: BIM exchange and inspection layer
- order_analyzer: evidence derivation and matrix evaluation layer

## IFC/Bonsai Mapping Resolution

The IFC object hierarchy, schema-version boundary, persistence policy, official
sources, and running-Blender round-trip evidence are resolved in:

`docs/superpowers/specs/2026-08-16-ifc-bonsai-object-mapping-research.md`

In summary, authored factual objects use native IFC classes; project facts use
minimal `OM_` property sets; `MassPatch`, `SurfacePatch`, inferred boundaries,
regions, paths, graphs, fields, and heatmaps remain analyzer-owned by default.
The current project targets IFC4 first and guards IFC4X3-only relationships.

## Next Step

Write the IFC4 adapter implementation spec from the verified mapping. Do not
begin by adding every possible analysis object to IFC.

## Technical Route Confirmed In Brainstorming

The recommended route is:

```text
source BIM objects
    -> geometric and semantic primitives
    -> boundary/surface/level feature candidates
    -> continuity and enclosure grouping
    -> derived BIM analysis objects
    -> subject-cue relations
    -> evaluation matrix
```

The user does not draw boundary objects. The analyzer derives them and keeps
the source object ids that explain each derived feature.

## Academic Definition Of Boundary

For this project, a boundary is not only a wall or a visible line.

An analysis boundary is a spatial interface that separates, groups, encloses,
or changes the relation between two sides of a scene. It may be produced by:

- a geometric discontinuity, such as height, depth, thickness, or elevation;
- a surface discontinuity, such as material, color, or texture change;
- a continuous contour or aligned set of object edges;
- a closed or partly closed region;
- a difference in visual or locomotive permeability;
- a directional or organizational transition in the surrounding layout.

The definition is deliberately relational. A sofa seat may not emit much
boundary evidence, while its back may emit a strong local interface. A carpet
may emit no physical barrier but still define a common region.

## Gestalt Principles As Engineering Evidence

Gestalt principles should be used as evidence generators, not as a final
perceptual score:

| Perceptual principle | Engineering use |
|---|---|
| Common region | Detect elements contained by the same carpet, surface patch, or closed contour. |
| Uniform connectedness | Detect homogeneous connected floor/material regions as one surface cue. |
| Good continuation | Merge compatible collinear or smoothly continuing edges into a boundary run. |
| Proximity | Support merging nearby compatible segments or repeated furniture edges. |
| Similarity / contrast | Detect surface boundaries from material, color, texture, height, or orientation changes. |
| Closure | Estimate whether segments form a complete or partial enclosure around a region. |
| Figure-ground / border ownership | Record which side is the enclosed or organized side when geometry and context support it. |
| Parallelism | Detect a coherent directional boundary or reference frame. |

The literature supports common region, uniform connectedness, closure,
continuity, similarity, parallelism, contour integration, and border ownership
as distinct organization processes. They should therefore remain separate
evidence fields rather than being collapsed into one boundary weight.

## What Counts As “Having A Boundary”

Version 1 should distinguish three concepts:

1. `boundary_candidate`
   - A coherent interface has been detected from geometry, surfaces, or
     relations.

2. `boundary_evidence`
   - The candidate has measurable channels such as height, thickness,
     continuity, closure, walk blocking, visual blocking, or surface
     grouping.

3. `boundary_influence`
   - A subject such as a furniture group or region has a measurable relation
     to the evidence: distance, coverage, containment, side relation, or frame
     agreement.

This avoids a hidden universal `boundary_strength`. The matrix should expose
the evidence vector and relation values; later perception experiments may
learn how to combine them.

## Academic Framework

The project uses a layered framework rather than one single theory:

### 1. Perceptual organization

Gestalt and contemporary vision science explain how local elements become
organized into contours, surfaces, figures, and common regions. This layer
motivates proximity, similarity/contrast, good continuation, closure, common
region, uniform connectedness, parallelism, and border ownership.

### 2. Environmental spatial cognition

Reference-frame research explains why a layout can be organized relative to
multiple local and global axes. A nearby boundary, corridor, furniture group,
or column grid may provide a frame without replacing the other frames.

### 3. Environmental affordance and permeability

Permeability research explains why a boundary has several independent effects:
visual permeability, locomotive permeability, height, gaps, and enclosure.
This layer prevents a transparent wall, low cabinet, carpet edge, and solid
wall from being collapsed into one binary boundary type.

### 4. Computational evidence model

The software does not claim that the feature vector is already a complete
human-perception model. It exposes measurable evidence and relations:

```text
scene geometry and semantics
    -> perceptual organization evidence
    -> reference-frame relations
    -> permeability / affordance channels
    -> subject-cue evidence table
    -> perception-calibrated model later
```

The final weights, nonlinearities, and task-specific interpretation must be
learned or validated through perception experiments. The current matrix is the
measurement layer, not the final psychological law.

### Working definition

Within this framework, an indoor layout boundary is:

> a spatial interface whose geometry, surface organization, permeability, or
> contextual grouping makes the relation between two sides measurably
> different.

This definition includes physical separators, surface/common-region edges,
level changes, continuous object contours, and emergent arrangements of
multiple objects. It does not require a dedicated authored boundary object.

## Research Basis

- Wagemans, Elder, Kubovy, Palmer, Peterson, Singh, and von der Heydt (2012),
  *A Century of Gestalt Psychology in Visual Perception: I. Perceptual
  Grouping and Figure-Ground Organization*, Psychological Bulletin, 138(6),
  1172-1217. DOI: 10.1037/a0029333; PMID: 22845751. This is the main review
  for perceptual grouping, contour integration, figure-ground organization,
  and border ownership.
  https://pubmed.ncbi.nlm.nih.gov/22845751/
- Palmer (1992), *Common Region: A New Principle of Perceptual Grouping*,
  Cognitive Psychology, 24(3), 436-447. DOI: 10.1016/0010-0285(92)90014-S;
  PMID: 1516361. This supports common-region and containment evidence.
  https://pubmed.ncbi.nlm.nih.gov/1516361/
- Palmer and Rock (1994), *Rethinking Perceptual Organization: The Role of
  Uniform Connectedness*, Psychonomic Bulletin & Review, 1, 29-55. This
  supports treating homogeneous connected surfaces as primitive grouping
  units before later grouping relations.
  https://doi.org/10.3758/BF03200760
- Palmer and Brooks (2008), *Spatial Organization of Perceptual Groups:
  Elements of a Unified Theory of Perceptual Grouping*, in *Perceptual
  Organization in Vision*. This supports treating grouping as a contextual
  organization process rather than a list of isolated local rules.
- Palmer (2008), *The Origin of Figure-Ground Organization in Vision*,
  Journal of Vision, 8(16). This supports contextual edge grouping and
  border-ownership evidence for deciding which side of a contour is organized
  as figure or ground.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC2593880/
- Stamps (2005), *Visual Permeability, Locomotive Permeability, Safety, and
  Enclosure*, Environment and Behavior, 37(5), 587-619. DOI:
  10.1177/0013916505276741. This supports separate visual and movement
  permeability channels.
  https://doi.org/10.1177/0013916505276741
- Mou and McNamara (2002), *Intrinsic Frames of Reference in Spatial Memory*,
  Journal of Experimental Psychology: Learning, Memory, and Cognition, 28(1),
  162-170. DOI: 10.1037/0278-7393.28.1.162; PMID: 11827078. This supports
  object/layout-intrinsic reference frames.
  https://pubmed.ncbi.nlm.nih.gov/11827078/
- Meilinger, Riecke, and Bülthoff (2014), *Local and Global Reference Frames
  for Environmental Spaces*, Quarterly Journal of Experimental Psychology,
  67(3), 542-569. DOI: 10.1080/17470218.2013.821145; PMID: 23972144. This
  supports simultaneous local and global reference frames in environmental
  spaces.
  https://pubmed.ncbi.nlm.nih.gov/23972144/

## Research To Matrix Mapping

The first implementation-oriented feature groups should be:

- geometry: height profile, thickness, elevation delta, edge length;
- continuity: physical continuity, perceptual continuity, directional
  continuity, segment continuation, run length, smoothness, gap ratio,
  repetition count, and spacing regularity;
- grouping: common-region containment, surface continuity, surface contrast,
  ground color or material organization, edge clarity, and closure ratio;
- permeability: walk blocking and visual blocking;
- relation: distance, edge coverage, side relation, angle agreement;
- provenance: source object ids, derivation method, semantic confidence.

These are objective descriptors. They are not a final human-perception model.

## Uneven BIM Geometry And Computational Substitutes

Real BIM objects are uneven. A sofa has a low seat, high back, arms, cushions,
legs, and material changes. The analyzer should not use the whole object bbox
as the boundary source except as a last fallback.

The project should use two primary analysis substitutes:

1. `MassPatch`
   - Represents local physical mass, height, thickness, elevation, and
     permeability.
   - Covers wall faces, sofa backs, chair backs, cabinets, platforms, steps,
     columns, and other body-like or height-producing scene parts.

2. `SurfacePatch`
   - Represents local surface organization, color, material, texture, and
     common-region grouping.
   - Covers carpets, ground color fields, material changes, floor finishes,
     and other surface-like scene parts.

The intended route becomes:

```text
source BIM object
    -> MassPatch and/or SurfacePatch
    -> candidate interfaces
    -> derived BIM evidence objects
```

`MassPatch` should carry:

- footprint or face geometry;
- base elevation, top elevation, and height profile;
- thickness and vertical face evidence;
- walk blocking and visual blocking;
- local frame;
- source object ids.

`SurfacePatch` should carry:

- area geometry;
- material, color, texture, or finish identity;
- surface continuity and surface contrast;
- edge clarity and closure hints;
- local frame when the surface boundary has a clear direction;
- source object ids.

Mesh, voxel, or raster/grid substitutes should not be the normal abstraction.
They are only accelerators for extracting `MassPatch` or `SurfacePatch` from
complex curved or uneven geometry. They must keep links back to the source BIM
object ids and the derived OM evidence object ids.

This keeps the substitute layer small:

```text
BIM object
    -> MassPatch      physical / height / permeability evidence
    -> SurfacePatch   color / material / common-region evidence
```

## Spatial Evidence And Viewpoint Evidence

Most matrix evidence should be spatially intrinsic:

- MassPatch geometry and height profile;
- SurfacePatch color, material, and containment;
- boundary candidate geometry derived from MassPatch or SurfacePatch changes;
- continuity, closure, and common-region grouping;
- walk blocking and visual blocking;
- region/path/grid relations.

These do not depend on where one user stands.

Some evidence is viewpoint-dependent and should be a separate optional layer:

- visibility from a sampled viewpoint;
- occlusion;
- sightline openness;
- apparent continuity from one view;
- user-route-specific perception.

The default model should compute intrinsic spatial evidence first. Viewpoint or
agent-based evidence can be added later as a small optional substitute:

3. `ViewSample`
   - Represents one camera, user location, or route sample.
   - Does not create the boundary itself.
   - Filters or reweights already-derived evidence by visibility, occlusion,
     and viewing direction.

```text
viewpoint / path sample
    -> visible evidence subset
    -> view-specific subject-cue relations
```

This keeps the matrix useful for global layout comparison while still allowing
future heatmaps from user locations, paths, or camera views.

Current decision: do not make `ViewSample` part of the core model yet. The
core boundary and order evidence should be spatially intrinsic. Add
viewpoint-based evidence only when the task explicitly asks for camera,
route, or user-position analysis.

## BIM Facts, Measured Properties, And Analysis Variables

The BIM route should keep three layers separate:

```text
BIM / IFC facts
    -> measured geometry and material properties
    -> analysis variables
```

### BIM / IFC facts

The source BIM model provides factual records:

- object ids and stable references;
- object types and relationships;
- geometry;
- material assignments;
- surface styles;
- property sets;
- authored column grid axes and other intentional references.

These records do not directly mean that an object is a strong or weak
boundary. They are inputs.

### Measured geometry and material properties

The analyzer should measure or read:

- height, base elevation, top elevation, and height profile;
- thickness and edge or face geometry;
- elevation difference between adjacent surfaces;
- material, color, texture, and finish identity;
- transparency or surface rendering values when available;
- surface continuity and surface contrast.

`height` and `thickness` are geometric properties, not semantic labels. They
should preferably be measured from geometry rather than copied from manually
typed fields.

### Analysis variables

Only after the measurement layer should the analyzer derive:

- `MassPatch`;
- `SurfacePatch`;
- boundary evidence;
- surface cue evidence;
- level-change evidence;
- walk graph evidence;
- visual graph evidence;
- region, path, and reference-frame relations.

Rules must not hard-code material names:

```text
do not: material == "glass" -> see_block = 0
do: geometry + material + transparency + height -> visual permeability evidence
```

Likewise, walls, low cabinets, sofas, carpets, and glass partitions should be
distinguished by their measured attributes and relations, not by a final
category weight.

## Space Syntax Compatibility Rule

Space syntax algorithms may be reused only after the BIM facts have been
converted into analysis variables.

The traditional single obstacle model should be split into:

- `walk_graph`: uses physical passability, geometry blocking, openings,
  elevation changes, and walk cost.
- `visual_graph`: uses height profile, sightline obstruction, transparency,
  and visual permeability.
- `surface_grouping`: uses `SurfacePatch` containment, color, material,
  common-region grouping, and edge clarity.

This keeps space syntax as graph evidence, not as the semantic definition of
boundaries.
