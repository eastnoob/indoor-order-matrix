# B3 PRIMARY eye-plane discrete field

Date: 2026-10-08. Status: **owner accepted** the bounded design-only PRIMARY eye-plane conditional discrete field with localized unknown in final run `run_20261008T211817Z_095de3`; **B3 remains open**. The owner reviewed final source code, field counts/channel contract, component parity evidence and both final PNGs. This acceptance does not establish complete physical occupancy. The next route is primary-plane geometric versus sampled connectivity with unknown preserved, followed by a minimal field handoff decision; no further implementation is included in this package.

The query is fixed at world z=1.6 m: human-confirmed IFC storey #13 datum 0 m plus eye offset 1.6 m. Frozen actual Body geometry is already in world metres. Historical S3 remains 206.5209234821732 m² with two holes; its horizontal binding is retained, its current live binding is not rechecked and its vertical extent remains unknown. Slab support is excluded from occupancy.

## Runnable package and preserved evidence

- Runner: [`run_b3_eye_plane_field.py`](../../../scripts/design/space_field/run_b3_eye_plane_field.py); output-only renderer: [`render_b3_eye_plane_field.py`](../../../scripts/design/space_field/render_b3_eye_plane_field.py); focused tests: [`test_b3_eye_plane_field.py`](../../../test/test_b3_eye_plane_field.py).
- Final run: [`field_samples.json`](../../../outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/field_samples.json), [`source_sections.json`](../../../outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/source_sections.json), [`artifact_manifest.json`](../../../outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/artifact_manifest.json), [`execution.json`](../../../outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/execution.json).
- Images: [`primary_eye_plane.png`](../../../outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/primary_eye_plane.png), [`blender_primary_eye_plane.png`](../../../outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/blender_primary_eye_plane.png); disposable [`b3_primary_eye_disposable.blend`](../../../outputs/design/b3_eye_plane_field/run_20261008T211817Z_095de3/b3_primary_eye_disposable.blend).
- Frozen A capture: `outputs/design/b3_real_source_field/run_001`. All 366 immutable index entries are checked by the runner. Per-source mesh refs retain original capture-relative `meshes/<step>.json` paths and hashes.
- First eye-plane run `run_20261008T210753Z_b357e3` remains unchanged. Intermediate `run_20261008T211301Z_8138e9` retains the pre-correction whole-object parity failures and [`door_parity_probe_audit.json`](../../../outputs/design/b3_eye_plane_field/run_20261008T211301Z_8138e9/door_parity_probe_audit.json). No historical B attempt, including `attempt_004`, or accepted synthetic `run_002` was rewritten.

## Qualification and numerical bookkeeping

The path validates finite indexed triangles, metre/frame flags and index bounds. Finite referenced triangles wholly above/below the plane prove absence independently of mesh closure. Zero-area triangles remain explicitly invalid source geometry: no triangles are removed. The 15 degenerate CozyChair meshes are entirely below eye height (max z approximately 0.667–0.685 m), so they retain `source_geometry_status=invalid_degenerate_mesh` alongside `status=valid_empty_below_plane` and zero plane uncertainty support.

Crossing sources require capture closed/manifold flags, independent indexed watertight/consistent-winding checks (`trimesh 5.1.0`, `process=False`, `validate=False`), degree-2 section endpoints, no cuts/dangles/invalid rings, valid positive planar faces and unanimous per-shell parity. Source vertices within 1e-9 m of the plane retain boundary/coplanar ambiguity. The section uses one linear intersection per sorted **original vertex-index edge**, with endpoint merge tolerance **0 m**. It does not weld, snap, repair, close contours, replace mass with hull/bbox occupancy, or fall back to projection/band slicing. Installed trimesh slicing was examined earlier; its closed-path handling is not the final algorithm, and no rtree dependency was added.

Raw private-helper linework/polygonization is retained beside the indexed-edge result. Eight closed indexed sources previously had arithmetic gaps: #59, #25058, #29707, #34356, #39005, #142222, #142689, #143931. All crossing shared-edge multiplicities are two. For column #59, edge `(1053,1059)` on faces 1064/1065 produced y values `0.037412928707069824` and `0.03741292870706982`, a 6.938893903907228e-18 m discrepancy. Door #25058 edge `(2300,2320)` and walls #142222/#142689 reach 8.881784197001252e-16 m; #143931 reaches 2.7755575615628914e-17 m. Single original-edge computation eliminates these eight section gaps without changing source geometry. Door #6231 instead has crossing-edge multiplicities `{1:4, 2:46, 4:2}` and remains genuinely unsupported by the closed-solid prerequisite.

## Connected-shell and five-door audit

Original indexed-edge face connectivity is retained, including original face indices, signed volumes, referenced z ranges and plane-shell pair intersections. Orientation is never flipped. Of the original 29 would-be qualified sources, 26 are single-shell objects; walls #142689/#142850/#143931 have 2/4/5 shells. Their 17 plane-shell pairs have intersection area zero and neither-direction containment false. All 37 signed volumes are positive. Representative compound-wall volumes are:

| Source | Original shell signed volumes (m³, rounded for display) | Crossing shells |
| --- | --- | ---: |
| #142689 | 7.29000026, 7.29000042 | 2 |
| #142850 | 5.94000374, 5.94000391, 2.92677841, 2.92677770 | 4 |
| #143931 | 2.92677452, 2.92677595, 2.92677667, 4.64813412, 5.94000020 | 5 |

Doors #20409, #25058, #29707, #34356 and #39005 each contain six positive-orientation closed shells: two cross z=1.6, four hardware shells lie below it. Each crossing pair has zero section-intersection area and no containment. For #20409, crossing-shell signed volumes are 0.03675001168224575 and 0.07019990501406419 m³. Across the final 34 qualified sources there are 67 shells, 47 crossing shells and 22 tested plane-shell pairs, with no detected nesting/positive-area overlap.

The door failure was **cross-shell ray-hit deduplication**, not proof of a defective source. At the unchanged disputed #20409 representative `(8.271090030670166, 8.671923747880925)`, the containing shell yields ray counts `[1,1,1]`; the other, exterior shell yields `[2,0,2]`. Whole-object deduplication merges near-coincident distances across shells to `[2,1,2]`, incorrectly producing mixed parity. #25058/#29707/#39005 have the same count pattern; #34356 has component counts `[1,1,1]` and `[0,2,0]`, formerly merged to `[1,2,1]`. The fixed path deduplicates only within each original shell, then combines parity **only for audited disjoint plane interiors**. Correct combined counts are `[3,1,3]` or `[1,3,1]`; every component vote is unanimous. Final source records retain both `whole_object_face_parity_probes` and the corrected `face_parity_probes.component_probes`.

Nested/overlapping compound interiors of either orientation remain `unresolved_compound_shell_interior` with source support unknown. Signed orientation alone cannot declare a cavity, physical union or XOR. Component vote disagreement also remains unknown. Regression evidence covers nested positive shells, overlapping positive shells, reversed inner shells and near-coincident cross-shell ray hits. These are plane-local safeguards, not 3D material or self-intersection certification.

## Actual field and remaining unknown

| Non-slab source plane status | Count |
| --- | ---: |
| Conditional qualified closed section | 34 |
| Valid empty below plane | 111 |
| Valid empty above plane | 195 |
| Unresolved open/nonmanifold | 13 |
| Total | 353 |

One slab and four semantic nonmass records are separately excluded. Forty-seven non-slab referenced z ranges straddle the plane; only 45 have crossing triangles. Qualified sources are 16 columns, 11 walls, five doors and two IfcFurnishingElements. Qualified raw union area is **22.392615629752758 m²**; S3-clipped area is **0.014987329164664116 m²**. This is a qualified subset, not total physical eye occupancy. Clipped unknown XY-hull support is **19.069186870135574 m²**, used only to localize missingness.

All qualified columns/walls clip to zero area: their mass lies outside S3 or in its boundary/hole context. Qualified clipped contributions are #3556226 (0.004263132136077599 m²), #3556367 (0.010724149344688797 m²) and door #29707 (4.7683897719252855e-08 m²). The tiny eye result is supported by actual below-eye furniture and the S3 boundary placement; it is not filled in for presentation. Its final area equals the historical eye-band approximation numerically; that agreement does not replace exact-height qualification.

Remaining unresolved sources are door #6231; windows #43654/#49645/#55636/#61627/#67618; bar-counter/shelves #1992252; and CET objects #2032485/#2053009/#2082638/#3236022/#3237875/#3269286. Closed section loops do not promote an open 3D mesh (#1992252 and the two CET_yellow sources). CET_dark_green #2053009/#3237875 have 220 crossing triangles each with incomplete linework.

Of the historical ten in-scope unsupported eye-band candidates, six have actual plane crossings: #6231/#1992252/#2053009/#2082638/#3236022/#3237875. CET_dull_yellow #2032485/#3269286 globally straddle 1.6 (z range 0.5389143824577332–1.7290375232696533 m) but have zero crossing triangles; their open-solid interpretation remains unknown. CET_yellow #3362781/#3439270 end at z=1.5735121965408325 m and prove plane-empty despite intersecting the comparison band. Full source-linked status, linework, geometry and quality refs are in `source_sections.json`.

## Discrete evidence and channels

| Spacing (m) | XY origin shift (m) | All points | Domain points | Occupied | Empty under qualification | Unknown | Outside |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 | (0,0) | 960 | 815 | 0 | 744 | 71 | 145 |
| 0.5 | (0.125,0.125) | 960 | 817 | 0 | 745 | 72 | 143 |
| 0.25 | (0,0) | 3888 | 3323 | 0 | 3015 | 308 | 565 |
| 0.25 | (0.0625,0.0625) | 3840 | 3276 | 0 | 2978 | 298 | 564 |

All lattices miss the tiny positive subset. The complete 9,648 indexed point records retain XY/z, domain mask, qualified-subset mask, unresolved source ids, source-support and section-boundary ambiguity masks, status and true/false/null occupancy. Positive established interior survives overlapping missingness; false is allowed only inside S3 with no unresolved support or section-boundary ambiguity. Null is unknown or separately masked outside. `known_free_under_qualification` is conditional, never complete physical free space. Domain-boundary distance includes both holes; raw-qualified-subset distance includes outside-domain mass and has an incomplete target. Complete physical clearance stays null. No qualified groups means Gaussian remains unavailable.

## Execution, inspection and handoff

`pixi run pytest test/test_b3_eye_plane_field.py -q`: **exit 0, 10 passed in 0.59 s**. The first touching-box version of the new fixture was correctly rejected by the existing section degree rule; the final fixture uses two separate boxes with a 1e-10 m gap, reproducing hit deduplication without changing section topology. `pixi run python scripts/design/space_field/run_b3_eye_plane_field.py`: **host exit 0; approved portable Blender 5.2.0 LTS exit 0**. The Blender executable is exclusively `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`.

Both final PNGs were actually viewed by the agent and subsequently reviewed by the owner. The primary plot has readable title/metre axes, equal aspect, two S3 holes, orange unknown support, tiny magenta occupied evidence and teal conditional-empty samples. Gray Body vertex audits are not occupancy. The Blender render shows actual frozen furniture/structure, separate teal S3/hole outlines, orange unknown outlines and tiny magenta boundary features; labels are readable and unclipped. Raised overlays are display only; query z stays 1.6. The independent scene contains 354 meshes, 1,802,274 vertices and 3,543,857 triangles. The `.blend` was saved; it was not interactively reopened. Owner acceptance is limited to the conditional design field described above.

The final bounded check covers strict JSON, sample/lattice/null semantics, geometry/source refs, declared artifact hashes, immutable A entries, prior manifest evidence, function docstrings and scoped whitespace/Git observations. There was no separate global baseline before this package; pre-existing unrelated changes remain, including `features/` edits and `scripts/design/live_domain/`. Scope preservation is based on declared immutable refs and this package's named edits, not a clean-working-tree claim.

Owner handoff: the conditional closed-solid/compound-shell qualification, localized unknown support and incomplete distance meanings are accepted for this bounded design field. Proceed next to primary-plane geometric versus sampled connectivity while preserving unknown, then decide the minimal field handoff. No production API, resolution, body/route/sightline model, IFC/source repair, dependency change, commit or B3 closure is included. Full-suite testing, live binding requalification, 3D self-intersection certification and interactive `.blend` reopening were skipped. Unknown sources and point-sampling misses remain material limits.

**STOP FOR OWNER REVIEW**
