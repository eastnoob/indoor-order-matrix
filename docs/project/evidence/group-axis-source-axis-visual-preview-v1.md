# Source-axis support visualization preview v1

Completed 2026-10-31 as an output-only presentation of the pinned IFC replay.
Final artifact directory:
`outputs/design/group_axis_potential_visual_preview/run_20261031T174219Z/`.
Open `index.html`; the four SVGs and four PNGs can also be viewed independently.

## Owner recommendation and comparison

Use the complete matrix heatmap together with a linked representative-field
plan. A selected group's cross-field bars make overlapping support explicit.

| Expression | Benefit | Limitation |
| --- | --- | --- |
| One field plan, fixed legend and numerical table | Identifies the reference anchor, actual locations and each group's support | Does not by itself explain simultaneous support across fields |
| Complete group-by-anchor numerical heatmap | Shows all 1,369 readings and overlapping support in each row | Spatial locations require the plan |
| Three same-plane reference views | Makes directional differences spatially comparable | Display sampling cannot stand in for the complete 37-field matrix |

The HTML links all three expressions. G/F display codes map to original IFC
group/field IDs in `manifest.json`. Clicking a matrix cell chooses a view and
an inspected row, without choosing a winner or changing evidence. The anchor
uses an outline and symbol; its fill retains the same 0–1 support palette.
The HTML uses Chinese system-font text. Static SVG/PNG explanations use clear
English and an ASCII asterisk to avoid missing Chinese/star glyphs in raster
exports. Every numerical value remains available at original precision in the
embedded cell JSON and original retained files.

## Actual data and representative selection

Only `outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z/`
was consumed. `field_matrix.json`, `field_profiles.json`,
`field_directions.json`, `description.json` and `source_manifest.json` are
addressed and hashed in the manifest. The pinned IFC fingerprint is
`1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`;
the inherited plane is `ifc-world-plan`, world XY, metres. This runner reuses
the retained identity and polygons; it does not rehash/reextract the live IFC.

The 37 groups, 37 profiles, 37 direction records and all 1,369 support cells
retain their exact source values. The neutral plan uses actual retained
member polygons with an aspect-preserving projection, not simulated furniture
or an invented room outline. Color is only a display of existing
`axis_field_support`, never new evidence or a new strength channel. The fixed
range is 0–1 even though the maximum actual support is about 0.708719.

Three display references are existing anchors at the minimum and maximum
source-axis angles, plus the existing reference maximally separated from
those two in undirected angular distance. This produces contrasting existing
directions without creating references, clusters, or a claim about field count:

| Display | Field | Anchor group | Actual reference angle |
| --- | --- | --- | --- |
| Minimum angle | F06 | `ifc-group:0WEjP61oTMbOLVcpUvUD7i` | 0.0021346969915428983° |
| Direction contrast | F02 | `ifc-group:02Kyw_DsPG5BC3j07wct$4` | 90.0021337134291° |
| Maximum angle | F26 | `ifc-group:2YUldlHfjSawY3CBPVi5_Q` | 128.25931569125186° |

The full immutable field IDs and sampling reasons are in the manifest.
Non-self means exclude the anchor (36/36 coverage here); the separately
labelled soft direction includes the anchor (37/37). The reference angle is
not replaced by the soft summary. One row can support many fields; no row
normalization, threshold, membership, hard group, winner, FieldFamily or merge
is introduced.

## Independent review and owner integration

Independent reviewer `/root/visual_review` inspected the real source and
rendered PNGs. It verified exact equality of 1,369 cells, 37 profiles and 37
directions, the full group scope, self markers and source hashes. It endorsed
matrix + linked plan + same-row cross-field bars. Its actionable findings were:

- Keep a fixed 0–1 palette rather than scaling to the observed maximum.
- Keep support fill separate from anchor marking, and distinguish the
  non-self profile from the self-inclusive soft summary.
- Replace the initial minimum/median/maximum angle sample (0/128/128 degrees)
  with existing references near 0/90/128 degrees for meaningful contrast.
- Use readable static export text; the final remaining unsupported star glyph
  was replaced with ASCII `*`, including the legend.

These changes are integrated. The reviewer confirmed that English static text
and the revised 0/90/128 spatial comparison were readable before the final
ASCII-symbol-only repair. The final symbol repair and labels were checked
directly; no new design/review cycle was started.

## Validation and changes

Commands and observed results:

```powershell
$env:PYTHONPATH='.'
pixi run pytest test/test_group_axis_potential_preview.py -q
# 1 passed in 4.23s (final state)
pixi run python -m scripts.design.group_level.render_group_axis_potential_preview
# status pass; final directory above
pixi run python -m compileall -q scripts/design/group_level/render_group_axis_potential_preview.py test/test_group_axis_potential_preview.py
# passed
```

The embedded HTML script was extracted and passed to `node --check -`:
exit 0. All four SVGs parsed as XML; final static text was checked for English
labels and absence of the unsupported star/CJK glyphs. The focused test checks
all original cells/profiles/directions exactly, source polygon count, 37×37
scope, self count, manifest hashes, four raster artifacts, 0/90/128 display
sampling, and distinct NA/known-zero formatting. All five input byte sequences
remain unchanged. An initial test invocation without `PYTHONPATH=.` failed
collection (`scripts.design` unavailable); the project-standard invocation
above passed. Earlier previews are retained as historical outputs.

Changed files: the new standalone renderer, its focused test, this evidence
report, and a local renderer entry appended to `docs/software-architecture.md`.
Artifacts include HTML, complete matrix SVG/PNG, three representative SVG/PNG,
README and source/artifact manifest. No production feature or old replay file
was modified; no checkpoint, push or merge was performed.

## Limits and stopping condition

Browser interaction was not executed: the connected browser URL admission
blocked the local preview, and no bypass was attempted. JS syntax, exact data
preservation and static visible outputs are verified; this is not a claim of
end-to-end browser interaction acceptance. The retained IFC contains only
computed axes; missing/zero/cancellation cases were not fabricated as real
observations. No full production test suite or live IFC extraction was run.

Stop here: the complete requested real-data preview, traceable manifest,
comparison/recommendation, independent review integration and necessary
static/data checks exist. Later hierarchy/merge or live UI acceptance is
outside this visualization task.
