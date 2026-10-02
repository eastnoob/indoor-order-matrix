# D6 IFC furniture-group zone candidates

**Status:** `STOP FOR OWNER VISUAL REVIEW`  
**Current Blender source observed:** yes; Bonsai IFC path matches the source IFC below. The open scene was not modified or saved.  
**IFC:** `live-rhino-10500-furniture-groups.ifc` · IFC4 · Level 1 · mm (render labels use metres)  
**Source SHA-256:** `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`

The figures compare an unsplit 37-group baseline with exploratory 2-, 3-, and 4-set candidates. Only exact authored `ObjectType == "furniture_group"` groups are analysis nodes; members are not split. The cut sequence removes the largest positive area-normalized XY boundary-gap edges from one diagnostic MST. It is not an accepted algorithm or region count.

All figures use a shared source-geometry extent as a `diagnostic_only` view frame because this IFC has no IfcSpace or owner-accepted AnalysisDomain. Colored convex hulls are display envelopes; they can overlap and are not occupied area or a closed partition. Walls preserve source solid plan projection and thickness. Other displayed objects, including doors, are context only; door geometry is not opening-relation or open/closed evidence. Obstacle crossing, free space, connectivity, routes, walkability, visibility, activities, and production roles are not inferred.

See [`docs/project/evidence/d6-space-field-zone-visual-experiment.md`](../../../../../docs/project/evidence/d6-space-field-zone-visual-experiment.md) for detailed input coverage, limitations, and owner questions. Use `artifact_manifest.json` for file hashes and command results.
