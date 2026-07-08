# Furniture Group Region Inference Design

## Goal

Infer activity regions from authored furniture groups instead of requiring authored region markers.

## Design

SVG and BIM adapters provide neutral object records: furniture instances, authored group ids, affordance metadata, boundaries, columns, entries, and optional settings. They do not provide the evaluation matrix and should not be required to provide final activity regions.

The inference layer treats a furniture group as the smallest semantic unit. Each group first becomes furniture affordance extents, then one activity group. Activity regions are inferred from these activity groups using their affordance geometry plus grouping boundary cues. Inter-region paths continue to be the existing gap-band network between inferred region candidates.

For this change, authored region ids remain supported, but group ids are allowed to drive region inference when region is empty, `global`, or `room`. Close/overlapping group merge is deferred unless a boundary cue explicitly links groups, because the current fixtures already encode useful furniture-group ids and the shortest reliable step is to stop treating `region` as mandatory.

## Tests

The three `test/SVG_*.svg` fixtures must load without manual region/path records and still produce activity groups, inferred region candidates, gap paths, and overlayable trend geometry.
