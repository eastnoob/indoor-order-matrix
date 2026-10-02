# D6 Space Field Geometry and IFC Input: Independent Review

Date: 2026-10-01  
Status: independent read-only review; no production approval.

## Review scope and skills

Reviewed AGENTS.md, architecture memory, the D6 handoff, design table, baseline/polygon/IFC JSON, source runner, manifest, and source IFC. Applied `experimental-design` (fixture is the experimental unit; no cell pseudoreplication), `scientific-critical-thinking` (separate oracle, sampling, implementation and scope claims), `scientific-visualization` (inspect raw SVG semantics and retain missing/unsupported states), and global `verification-before-completion` (fresh commands and observed exit status before claims). The project-local verification skill was absent; the global skill at `C:/Users/tianf/.codex/plugins/cache/openai-api-curated/superpowers/5fd93af4/skills/verification-before-completion/SKILL.md` was used.

## Blockers

1. **Narrow-opening fixture semantics are not the stated width experiment.** The executed inline polygon baseline constructs a connector whose X span is 2 units and whose Y span is 0.4, 0.8 or 1.5. It is a genuine width change, but all three exact areas and component counts are identical because each opening bridges the same blocked wall and all widths are positive. This is explainable geometry, not a blocker by itself. The design table did not state this topology construction explicitly, so the acceptance question “width changes topology” is under-specified. Add a fixture where a width crosses a declared geometric/topological condition, without turning it into a production threshold.
2. **The subcell independent check exposes an oracle inconsistency in prior wording.** Exact Shapely geometry for the source coordinates has free area 19.2 and **three** connected components: the 0.8-wide vertical gap is an open component, while left and right strips are separated by the two full-height obstacles. The prior report called this fixture “exact one-component.” That is false for the literal coordinates. The sampler's 2–3 components are therefore not sufficient evidence of a program defect until the fixture intent is repaired or the expected topology is corrected. This is the primary blocker for causal attribution.
3. **Polygon baseline is not an exact sampled-topology baseline.** It uses Shapely polygon boolean/contains operations to define source geometry, then applies center-point lattice sampling and four-neighbor connectivity. Its exact polygon area/topology is independent and useful; its sampled rows remain resolution/origin sensitive. It must not be described as an exact topology guarantee.

## Important findings

### Design-table coverage

| Item | Planned | Executed | Status |
|---|---|---|---|
| Rotated/oblique geometry | 15/30/45 degree comparison intended | 30 degree rotated obstacle only in polygon probe | partial |
| Hole-bearing domain | required | one rectangular hole domain, sampled with polygon baseline | executed, but sampled output exactly equals source area only because grid aligns with hole |
| Narrow openings | 0.4/0.8/1.5 | all three coordinates and widths present | executed; topology invariant is geometrically expected |
| Disconnected region | required | prior rectangle fixture and polygon hole/union checks | executed |
| Resolution | 1, 0.5, 0.25, 0.125 | baseline and polygon rows | executed |
| Origins | (0,0), (0.23,0.17) | baseline and polygon rows | executed |
| Runtime / memory | budget requested | elapsed seconds recorded by baseline; memory explicitly unavailable | partial; memory missing |
| Units / scaling | required | IFC unit inventory; synthetic fixtures unitless | partial |
| Visual inspection | required | SVG source inspected; PNG conversion attempted | partial; `cairosvg` unavailable, so raster image inspection unavailable |
| Reproducibility | required | fresh baseline run in independent output directory; JSON/hash checked | executed |

The fresh command `pixi run python scripts/design/space_field/run_space_field_probe.py --output-dir outputs/design/space_field_geometry_ifc_independent_repro` exited 0 and produced a new result hash. The command output directory was distinct from the delivered directory.

### Subcell geometry and connectivity

Independent rectangle arithmetic gives domain area 24, obstacle union area 4.8, free area 19.2, gap width 0.8, and gap area 3.2. Positive-area geometry has three components for the literal coordinates. The sampler uses four-neighbor cell connectivity; diagonal contact is not traversable. No point-contact or edge-contact bridge exists in this fixture's continuous free set. Therefore the old “exact one component” oracle/fixture note is the unresolved source of the apparent persistent topology disagreement. The correct next action is fixture/oracle repair and rerun, not resolution selection or production code repair.

### Polygon comparison

Shapely 2.1.2 was available. The polygon baseline correctly preserves rotated and hole-bearing source geometry for boolean area calculations, but sampled results still depend on lattice phase and resolution. It is an independent geometry baseline, not an exact raster topology oracle. No dependency was installed.

### IFC input inventory

Source: `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`  
SHA-256: `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`  
Schema: IFC4.  
Length unit: millimetre (`IfcSIUnit`, `METRE`, `MILLI`).  
Counts from direct read: `IfcSpace=0`, `IfcOpeningElement=0`, `IfcDoor=6`, `IfcSpatialZone=0`, `IfcGroup=37`, typed furniture groups (`ObjectType=furniture_group`)=37, representations on 354 entities.

Placement and representations exist in the source, but this inventory alone does not prove world-space geometry extraction. The adapter path is capable of tessellation and placement resolution; that must be reported separately from source capability. Explicit analysis domain is **absent in this sample**, not merely unselected: there are no `IfcSpace` entities. The prior inventory phrase “not_selected” is therefore ambiguous and should be replaced by “no explicit IfcSpace domain present; adapter selection cannot resolve one.” Scene bounds remain an invalid substitute. Doors are physical geometry; no opening relation was found. No affordance zones are present in this source. Furniture nodes remain restricted to typed groups; ordinary groups/names/context do not create them.

## Minor findings

- Baseline manifest records the runner and hashes, but the polygon manifest identifies only an inline probe and does not preserve its source script as a file; exact replay therefore depends on the review command text.
- The first fresh reproduction generated no PNG because `cairosvg` is unavailable. SVG source inspection succeeded; raster inspection is an environment limitation.
- Baseline memory measurement is explicitly unavailable, so resource-budget conclusions are incomplete.
- Synthetic fixture units and scaling provenance are not recorded as a formal unit field.

## Verdicts

- **Subcell cause analysis: REVISE.** The persistent disagreement cannot be attributed to a sampler defect because the literal fixture geometry contradicts its one-component oracle. Repair the fixture/oracle definition first, then rerun the bounded comparison.
- **Polygon comparison: ACCEPT LIMITED DESIGN EVIDENCE.** It demonstrates a usable polygon-capable independent baseline and exposes remaining sampling sensitivity, but does not approve a backend or topology guarantee.
- **IFC input inventory: ACCEPT LIMITED DESIGN EVIDENCE.** The source/hash/schema/unit/group/opening/domain facts are useful. It does not constitute real IFC space-field acceptance; explicit domain and affordance inputs are absent.

## Required minimum next step

Correct the subcell fixture note/oracle or alter the geometry so the intended one-component neck is physically present, then rerun the same bounded resolution/origin matrix with a saved source script for the polygon baseline. Keep production resolution, backend, space-role thresholds, selector, API, Bayesian and ML decisions deferred.

## Range and verification audit

Only this review report is authorized as a new repository artifact. Existing dirty/untracked files were preserved and not attributed to this review. No production files, IFC sources, dependencies, or Blender installations were modified or invoked. JSON parsing, fresh probe execution, source IFC hash, SVG inspection, and output-directory separation were checked. One attempted raster conversion failed because `cairosvg` is unavailable; this remains reported rather than hidden.

**STOP FOR SPACE FIELD GEOMETRY AND IFC INPUT INDEPENDENT REVIEW**
