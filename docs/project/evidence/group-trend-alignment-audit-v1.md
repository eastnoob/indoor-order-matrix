# Group trend alignment audit v1

## Purpose and boundary

This audit checks what the repository already computes for furniture-group
trend/alignment before defining the second evidence package. It does not add a
trend channel to the geometry relation package, choose a trend estimand, or
produce a current-IFC trend result.

## Existing implementation

`features/group_self_description.py` already computes group-level
`trend_descriptors` when typed `Analysis` substitute geometry is accepted for
the trend consumer. The current descriptors remain separate:

| Descriptor | Existing basis | Meaning |
| --- | --- | --- |
| `overall_group_axis` | `area_weighted_total_covariance_pca` | Axis of total area distribution, modulo 180 degrees |
| `member_frame` | `member_orientation_consensus` | Four-angle member frame, modulo 90 degrees |
| `member_axis` | `member_orientation_consensus` | Two-angle member axis, modulo 180 degrees |
| `layout_axis` | `between_member_centroid_pca` | Axis of member-centroid placement |

The same result retains descriptor status, angle, deterministic geometric
strength/coherence, center where applicable, accepted member bindings and
diagnostic evidence for excluded members. Missing, invalid and partial typed
Analysis geometry stay visible as status; Body geometry is not mixed into the
typed trend path.

`features/furniture_frame.py` provides a separate per-furniture frame helper
with primary/secondary angles, orientation strength, extents and eigenvalues.
`features/scene_inference.py` has an older compatibility path that emits
`group-axis-angle` and related metadata, and a region-level frame mean. These
are not the current group evidence package contract.

## Current package boundary

`features/group_geometry_relation_field.py` wraps only
`description["group_relations"]`. Its Envelope channels are boundary gap,
contact and positive-area overlap. It does not serialize
`group_geometry[*]["trend_descriptors"]`; therefore trend/alignment is not in
the current **Geometry Relation Evidence Package v1**.

## Evidence and limits

Historical trend reports and renders exist, but their recorded IFC fingerprint
is the older
`018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`.
The current pinned IFC for this project is
`1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`.
Those historical outputs cannot be reused as current evidence. The current
source manifest qualifies 37 groups and 95 Body members, but does not yet
record a fresh current-IFC typed Analysis trend audit.

The focused trend regression command was run during this audit:

```powershell
pixi run pytest test/test_trend_core_checkpoint_1a.py -q
```

The test initially exposed one stale monkeypatch target. The test now patches
the current `neutral_scene_views.plan_projection` seam, and the rerun is
**13 passed**. No production trend calculation was changed.

A current-IFC sample replay was then run through the existing design probe's
real-IFC path (without executing its synthetic cases): three complete groups
were selected, all had accepted typed Analysis bindings, and all four existing
estimands were `computed`. The replay source is the current pinned file:

```text
bytes: 408618044
sha256: 1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077
schema: IFC4
unit: mm
selected groups: 3
```

This is a sample audit only. The reused design probe stops after three complete
groups; it is not a 37-group current-IFC package run and it does not emit a
second field Envelope.

## Candidate second-package contract (pending review)

The existing output suggests a group-targeted package rather than another
group-pair package. A possible Envelope target is one `furniture_group` under
the same `FieldQuery`, with parallel channels for `overall_group_axis`,
`member_frame`, `member_axis` and `layout_axis`. The package would preserve
member bindings, source references, descriptor status, diagnostic evidence and
the four estimands separately. This is a proposal for the next discussion,
not an approved combination rule or strength formula.

Before implementation, a full current-IFC trend package run still needs its
own source manifest, complete-group coverage and plane-local visualization.
No trend result has yet been added to the geometry relation Envelope.
