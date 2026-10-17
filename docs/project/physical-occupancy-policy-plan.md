# Physical occupancy policy: source accounting and height queries

Date: 2026-10-09.
Status: **SCOPED TWO-DIMENSIONAL IMPLEMENTATION COMPLETE / VERIFIED; B3 SHARED ENROLLMENT IMPLEMENTED / VERIFICATION IN PROGRESS**. Arbitrary plane/band semantics, live adapter promotion, complete occupancy, and complete clearance remain **OPEN**.

**Current architecture pointer:** See [`../software-architecture.md`](../software-architecture.md) for the repository-wide operation/consumer/representation boundary. This document records the verified scoped implementation and its remaining limits.

概览：实体占据由源对象的几何事实决定，与家具、组、趋势、朝向和服务范围资格分开。
代理几何只在明确绑定、用途获准且几何合格时替代原始源；缺失或失败不能变成“空”。
高度查询必须注明基准面和范围；悬空物体在相交高度仍然是实体。

## Scope and decision

The scoped two-dimensional implementation and the B3 shared enrollment package are implemented. Owner verification is still in progress; this is not an OWNER ACCEPTED claim. The changes preserve the current scene, public model shape, accepted historical packages, and legacy dict behavior.
The accepted occupancy-only handoff at outputs/design/b3_occupancy_only_handoff/run_20261009T091601Z_242b33 remains untouched.
Its three proxy groups and seven represented sources are a regression fixture, not a general source-count rule.
The implementation resolves source eligibility and exactly-once occupancy representation through existing scene facts. The B3 route adds the explicit world-XY `z=1.6 m` section query over the same physical representative. It does not add a rule language, a new solid engine, a top-level Neutral Scene schema, or a new furniture definition.

## Verified implementation scope

- `features/analysis_substitute_discovery.py:resolve_source_representation` reads operation descriptors and resolves original, approved substitute, or unresolved input.
- `features/neutral_scene_views.py:_resolved_physical_occupancy` builds the physical inventory, selects `MassPatch` geometry with qualified `Analysis` or `GeneratedProxy` provenance, enforces exact many-to-one coverage, and retains unresolved source ids. `GeneratedProxy` is not a geometry kind.
- `features/scene_evaluator.py:_physical_occupancy_blockers` and `_negative_space_descriptor` consume resolved physical occupancy; `free_space` delegates to the physical-occupancy operation and propagates unknown status rather than treating unresolved sources as known free.
- The default live geometry query remains whole-height planar projection. The isolated B3 package adds only explicit world-XY `z=1.6 m` section qualification; arbitrary height bands and tilted planes remain outside this checkpoint.
- The B3 shared route additionally qualifies explicit world-XY `z=1.6 m` sections through `features/section_views.py`; it does not add tilted planes, general height bands, or live evaluator integration.
- Current implementation report: **60 focused tests passed**; the final aggregate count is pending owner closeout. Full repository tests and live IFC/Blender checks were not run.

## B3 shared enrollment implementation evidence

Package: `outputs/design/b3_shared_occupancy_enrollment/run_20261009T141817Z_8e23c2/`.

- `execution.json`: `exit_0`.
- `comparison_audit.json`: all **9,648** samples match field-by-field; `frozen_original_rows_identical = true`; all four area deltas are `0.0`; conditional free area is `190.1616840398615 m²`.
- Inventory: 358 raw source rows, 354 capture Body meshes, 3 proxy meshes, 343 selected records including the 3 proxies, 5 unknown sources, 6 scoped sources (`4` semantic nonmass, `1` support slab, `1` boundary), and 7 proxy-represented owners.
- Historical diagnostics remain: 13 raw open/non-manifold cases and 15 below-plane degeneracy cases. Complete occupancy and complete clearance remain null/open.
- The unchanged A loader reads all four variants. Failed run `run_20261009T141637Z_243803` remains historical mappingproxy-serialization evidence; the later package is the successful implementation run.

## Verified current behavior and gaps

| Current seam | Verified behavior | Gap to close |
| --- | --- | --- |
| [Neutral projection](../../features/neutral_scene_views.py), `_resolved_physical_occupancy` | Complete source inventory is resolved before planar records are exposed; selected-domain support and boundary members are scoped out. | Exact height qualification and generic B3 enrollment remain open. |
| [Record construction](../../features/neutral_scene_views.py), _source_record lines 1061–1125 | A source record requires projected points. | Missing or failed geometry disappears from this compatibility view; this path alone cannot certify a complete physical inventory or known free area. |
| [Occupancy selection](../../features/neutral_scene_views.py), `_resolved_physical_occupancy` | Purpose-bound resolution and represented-source accounting decide original/substitute/unknown status; furniture eligibility remains separate. | Height-band qualification is not part of this two-dimensional checkpoint. |
| [Blocker merge](../../features/scene_evaluator.py), `_physical_occupancy_blockers` | Free-space blockers consume the resolved physical occupancy selection and represented ids. | Complete clearance and exact height-channel semantics remain open. |
| [Free-space calculation](../../features/scene_evaluator.py), `_negative_space_descriptor` | The explicit domain is required; blocker geometry is unioned for area and topology. Unresolved inventory makes free area unavailable while retaining known occupied area. | A resolved provided inventory does not prove the input contains every real-world source. |
| [Geometry projection](../../features/neutral_scene_views.py), _projection_components lines 681–695 | Calls plan_projection without a height band, hence projects the whole mesh into plan. | This is neither exact eye-plane occupancy nor body-height walking occupancy. |
| [Height-aware geometry](../../features/geometry_views.py), plan_projection lines 97–176, and [channel evidence](../../features/neutral_scene_views.py), _neutral_channel_evidence lines 296–350 | Optional positive-overlap height bands and explicit walking/visual queries exist. | Those channel observations are not the current physical_occupancy representation or an exact-plane qualification. |
| [Typed resolution](../../features/analysis_substitute_discovery.py), `resolve_source_representation` | Operation descriptors resolve source-owned bindings, target role/representation, geometry refs, ambiguity, rejection, and exact coverage. Trend compatibility remains available through `resolve_function_substitute`. | The resolver currently qualifies whole-height planar occupancy, not exact height sections. |
| [Direct group inputs](../../features/group_self_description.py), `_neutral_inputs`, `_group_geometry`, `_member_geometry` | Reads raw authored membership while explicitly excluded/unknown furniture contributes no group or trend geometry. | Standalone mesh-only geometry functions have no source participation context. |
| [Registry](../../scripts/design/group_level/trend_substitute_registry.json) and [contract loader](../../features/substitute_contract.py) | Operation descriptors now include physical occupancy/free-space delegation while preserving trend compatibility. | Generic B3 enrollment is not implied by registry support. |
| [IFC adapter](../../adapters/ifc_bonsai.py), lines 1471–1509 | The actual furniture owner retains Body; a separate analysis_substitute target uses Analysis and a trend binding on the owner. | Do not relabel all geometry as Analysis or infer occupancy authority from the helper role. |
| [B3 section runner](../../scripts/design/space_field/run_b3_eye_plane_field.py), section_source and sample_variant | Exact world z=1.6 m sections yield qualified occupied, conditional empty, or unknown with local support and boundary ambiguity. | This bounded design method has not become a generic scene occupancy service. |
| [B3 occupancy handoff](../../scripts/design/space_field/run_b3_occupancy_only_handoff.py), occupancy_only_field | Requires three qualified positive proxy sections, seven distinct represented originals, exact scope, and no double count. | It is fixed to accepted packages and groups; its source IDs and counts must not become generic branching logic. |
| [A loader](../../features/discrete_space_field.py), load_discrete_space_field lines 217–248 | Validates and returns selected serialized field dictionaries. | It neither discovers live sources nor computes a substitute or a free-space field. |

The [architecture memory](../indoor_layout_evaluation_matrix_architecture_memory.md) already states that physical volume is independent of furniture eligibility and that selected-domain boundary membership is an exact scope fact.
The [non-furniture regression](../../test/test_neutral_scene_analysis_regression.py) at line 819 shows a counter reducing free area while excluded from furniture analysis.
The view's `physical_planar_occupancy` flag now requires no unresolved source in the scoped provided inventory. It is not a real-world inventory completeness certificate.

## Policy invariants

1. A source with supported physical mass participates in physical occupancy irrespective of furniture, group, trend, orientation, or affordance eligibility.
2. Excluding furniture analysis cannot opt its actual mass out of occupancy; a counter, plant, shelf, partition, or suspended object is handled by geometry evidence.
3. Conceptual paths, regions, entries, openings, surfaces, grid axes, and analysis-domain records are not mass merely because they carry drawing geometry.
4. A physical-source decision must use explicit scene facts and geometry; source class, name, STEP number, and object order are never a substitute selection algorithm.
5. Exact selected analysis-domain support and uniquely resolved boundary members are scoped out of interior mass and interior uncertainty, while raw sources and channel evidence remain.
6. A door or window class does not imply global boundary membership; only a selected scope's exact member identity establishes that exclusion.
7. Raw source objects, meshes, typed bindings, uncertainties, and provenance remain available even when an occupancy query uses a substitute.
8. Occupancy, walk blocking, and visual blocking are separate judgments. Optical transparency needs optical evidence; it cannot be inferred from occupancy.
9. No failed section, absent mesh, unqualified helper, or unlocalized uncertainty can become known free by default.

## Minimal representation contract

Reuse [SourceObject](../../features/scene_contract.py) and its factual_properties, geometry_refs, provenance, and uncertainties.
Reuse existing mesh records and [MassPatch transport](../../features/geometry_substitutes.py); no copied occupancy-specific mesh object is needed.
Reuse OM_FunctionSubstitutes as the source-owned typed link, with resolve_function_substitute's exact target, geometry, representation, and rejection checks.
The implemented consumer identifier is **physical_occupancy**, with `free_space` delegating to it through the operation descriptors. The existing trend contract remains separate and is not treated as occupancy authority.
The target's representation identifier must match its actual provenance; the current IFC Body owner and Analysis target stay distinct.
Accepted B3 OBJ proxy geometry needs its own truthful provenance when bound; merely calling it Analysis would not prove IFC Analysis lineage.
MassPatch is a transport/geometry kind, not proof that a substitute is physical or approved for this consumer.

The following input fields fit existing SourceObject facts; `OM_PhysicalOccupancy` coverage and `GeneratedProxy` provenance are accepted only when present and qualified by the current resolver.
The example has two originals, source:a and source:b, represented by one target, proxy:g1.

| Record and field | Implemented value or rule |
| --- | --- |
| source:a factual_properties.OM_FunctionSubstitutes entry | {"source_object_id":"source:a","substitute_id":"proxy:g1","consumer":"physical_occupancy","substitute_kind":"MassPatch","analysis_role":"physical_occupancy_substitute","representation_identifier":"GeneratedProxy","provenance":{"method":"explicit_owner_binding","representation_identifier":"GeneratedProxy"}} |
| source:b factual_properties.OM_FunctionSubstitutes entry | {"source_object_id":"source:b","substitute_id":"proxy:g1","consumer":"physical_occupancy","substitute_kind":"MassPatch","analysis_role":"physical_occupancy_substitute","representation_identifier":"GeneratedProxy","provenance":{"method":"explicit_owner_binding","representation_identifier":"GeneratedProxy"}} |
| Binding representation_identifier | Match the target's real provenance: Analysis only for an actual Analysis target; proposed GeneratedProxy for a B3-generated OBJ target if its occupancy contract accepts that representation. Never rewrite Body provenance to pass matching. |
| Target SourceObject | Keep source_role analysis_substitute, its actual geometry_refs, world transform, units, and provenance.representation_identifier. The target is not another physical inventory source. |
| Target factual_properties.OM_PhysicalOccupancy.represented_source_ids | Exactly [source:a, source:b]. Both originals must own compatible occupancy bindings to proxy:g1; the resolver compares the complete bound-source set with this declaration and rejects missing, extra, duplicate, or overlapping assignments. |
| Original factual_properties.furniture_analysis_participation | Values included, excluded, unknown; absent preserves current role-based compatibility. Explicit excluded vetoes furniture, direct authored-group/trend, group-frame, and affordance analysis contributions while leaving physical occupancy intact. Included permits existing eligibility checks; it does not manufacture a furniture role. Unknown asserts no positive eligibility without further evidence. The standalone mesh-only frame API has no source eligibility context. |

Authored furniture-group membership remains a raw fact even when an excluded member contributes no higher-level analysis.
Existing analysis_participation and OM_Layout.AnalysisParticipation facts remain raw legacy input; only a named adapter or record contract with explicit semantics may map one to the proposed furniture field.
Do not silently reinterpret these older facts for every consumer.

Consumer participation is a query decision derived from existing role, binding, geometry, and scope facts.
Avoid four mandatory booleans for mass, walking, visual, and furniture on every source.
An optional future query-scoped descriptive fact may report floor contact or height relation, but it must not redefine global physical existence.
An explicit approved occupancy binding can represent one or several originals; every represented original owns a binding and appears in the target's exact represented_source_ids declaration.
One target may cover several sources only when those two sides agree completely and its coverage does not overlap any other accepted target.
A helper without such binding is a retained analysis source, not a new physical product in the interior inventory.

## Resolution and accounting

Process a complete source inventory before building planar compatibility records.
Do not infer the inventory from _source_record output, since it drops sources without projected points.
Retain source IDs, mesh refs, units, transforms, role facts, uncertainty, selected-domain identity, and binding provenance.

1. Resolve the analysis domain and exact selected-boundary membership using the existing identity resolver over raw source identities. Unmatched, duplicated and ambiguous tokens exclude nothing. Projected channel records may independently report an unprojected member; this does not erase exact raw membership for occupancy scope.
2. Classify explicit conceptual nonmass separately from potentially physical sources. Exclude selected-domain support/members only for the selected interior scope.
3. For each remaining physical candidate, resolve a required occupancy binding if present. Require a unique target, approved physical-purpose contract, truthful representation, exact coverage, valid geometry refs, units, and frame.
4. If a required binding is valid and its query geometry qualifies, use that target for its represented source IDs once. Do not add the original's mass or original uncertainty for that same query.
5. If there is no binding, use the original only when its geometry qualifies for the requested query.
6. If an explicit required binding is broken, stale, ambiguous, or unqualified, retain unknown for its represented source. Never silently fall back to original geometry.
7. Any future fallback from a failed required binding needs independent explicit qualification and a named policy; it is outside the first stage.
8. Apply the chosen geometry at the requested plane or band, union valid occupied geometry, and subtract only from the selected analysis domain.
9. Carry unresolved support into free-space area, components, and connectivity; release complete-free or complete-clearance claims only after coverage is established.

Let I be the set of physical candidate source IDs after semantic exclusions and selected-domain scope.
The result partitions I into O (original geometry selected), S (represented by approved substitute), and U (unresolved): **I = O disjoint-union S disjoint-union U**.
Each ID occurs exactly once in that partition; each accepted substitute target has one unambiguous coverage set; distinct target coverage sets do not overlap.
The geometry union contains selected originals and each distinct accepted target once; it never counts the target helper as an additional inventory source.
ID deduplication in _physical_occupancy_blockers is insufficient because original and target IDs differ.
Resolve representation before the objects plus physical_occupancy merge, or make that consumer consume the one resolved occupancy selection.
Do not leave replaced furniture originals in objects as physical blockers.

| Case | First-stage outcome |
| --- | --- |
| No occupancy binding, qualified original | Original contributes once. |
| No binding, missing or unqualified original | Unknown; support localized only if qualified evidence allows it. |
| Trend-only binding or orphan analysis helper | Trend remains independent; helper contributes no occupancy mass. |
| Accepted occupancy binding and qualified target | Target contributes once for exactly its represented IDs; original facts remain raw. |
| Explicit required binding missing, stale, conflicted, or failed | Represented source remains unknown; no implicit original fallback. |
| Two accepted targets claim one source, or ambiguous target ID | Reject/conflict; affected coverage is unresolved, never silently doubled. |
| Selected-domain member with exact identity | Excluded from this interior occupancy and uncertainty scope; retained as raw evidence. |
| Mixed boundary and interior members inside one proxy | Split into separately qualified per-scope interior geometry or remain unresolved; do not discard the entire group's interior mass. |

No bbox, vertex hull, convex hull, class-derived prism, floor-to-ceiling fill, or name-based replacement is generated by this policy.
The accepted three B3 convex meshes are explicit approved approximations for their frozen scope, with their approximation limit retained.

## Geometry and height semantics

Keep three query types distinct:

- **Whole-height plan projection:** the current plan_projection call without height_band projects all valid mesh surfaces into plan. It is a useful footprint view, not a guarantee that a body or eye at a particular height collides.
- **Exact plane section:** use a stated analysis plane and qualified section evidence. B3's accepted method is fixed at world z=1.6 m; valid geometry entirely above or below is empty only at that plane.
- **Body-height-band projection:** use an explicit band/profile and positive overlap, drawing on plan_projection's band clipping and existing walking profile machinery. It must retain the band and qualification status in its output.

Use [AnalysisPlane and AnalysisContext](../../features/scene_contract.py), geometry_tolerance, walking_body_profiles, and visual_height_bands already in the scene.
Reuse [geometry_views](../../features/geometry_views.py), existing boundary evidence, and accepted B3 section qualification where their guarantees fit.
Do not build a second general solid model or pretend a face projection has B3's watertight/parity guarantees.
All heights are in metres relative to an explicit datum and oriented analysis-plane basis; record the transform and source units.
Height minimum and maximum are broad-phase bounds, not proof of material throughout that interval or of floor contact.
Floor contact needs sufficiently qualified geometry and a stated support/datum convention; an inconclusive mesh or absent floor fact yields unknown contact, not false.
No floor-contact gate applies to physical mass: a hanging object still occupies a query that intersects its actual geometry.
An exact plane or body band wholly inside an actual under-table void may qualify as empty there; a whole-height plan projection legitimately includes the tabletop shadow.
A body band that overlaps the tabletop is blocked normally, and an expressly accepted conservative substitute such as the bounded B3 hull may intentionally fill a void.
Proven above/below-plane absence is separate from conceptual exclusion, domain-boundary exclusion, and unresolved geometry.

These are **proposed derived audit/query outputs**, calculated from source geometry and a stated query rather than manually authored truth or a rule language:

| Derived feature | Meaning and limit |
| --- | --- |
| source_object_id, selected_geometry_id, representation_identifier | Preserve the represented source, actual selected mesh/target, and truthful representation provenance for each query result. |
| bottom_m, top_m | Referenced mesh bounds in metres relative to the explicit datum and oriented basis; useful for broad-phase rejection, never evidence that the whole interval is solid. |
| physical_geometry_status | Qualified original, qualified approved substitute, missing, invalid, or unresolved with the source-specific reason and qualification method. |
| query_intersection | True, false, or unknown for the stated exact plane or body band; false requires qualified absence, and whole-height projection remains a separately labeled footprint view. |
| floor_contact | True, false, or unknown under a later explicit floor/support convention and tolerance; absent or suspect floor facts cannot produce false. |

The owner has not set the proposed XX threshold. Do not invent its numeric value or borrow B3 eye z=1.6 m as a walking default.
If a later floor or height selector is requested, expose it as a query-scoped/descriptive parameter with a stated datum.
Filtered free space must be labeled for that query; it cannot be advertised as full walkable area or complete 3D free volume.

## Failure and unknown propagation

The complete source inventory includes sources without mesh, even if _source_record cannot project them.
A missing source with no qualified spatial support yields unlocalized unknown across the selected domain for free-space certification.
A qualified conservative support may localize unknown; a hull used only as uncertainty support is never promoted into occupied geometry.
At a sample or area intersection, qualified occupied evidence wins even if another source is unresolved there.
In the absence of occupied evidence, unresolved support or section-boundary ambiguity stays unknown, not free.
Only a qualified source's proved absence at the queried plane or band can contribute empty evidence.
Known empty is always conditional on the selected scope and coverage; it does not assert global physical clearance.
Missing or suspect floor geometry leaves floor-contact status unknown without erasing a physical obstacle at an intersecting height.
The accepted [B3 sampler](../../scripts/design/space_field/run_b3_eye_plane_field.py), sample_variant lines 247–267, is the reference for positive-over-unknown precedence and tri-state labeling.
Its section_source lines 145–244 keeps invalid/degenerate, contact, open/nonmanifold, compound-shell, and parity failures separate from qualified empty.

## Implementation seams and blast radius

| Place | Smallest intended work when implementation is authorized |
| --- | --- |
| [substitute_contract.py](../../features/substitute_contract.py) and [trend registry](../../scripts/design/group_level/trend_substitute_registry.json) | Add a dedicated physical_occupancy consumer contract while preserving trend and exact representation checks. Registry location/name may be revised only if needed for truthful shared ownership. |
| [analysis_substitute_discovery.py](../../features/analysis_substitute_discovery.py) | Reuse typed resolution and rejection reasons; extend only for exact many-to-one coverage/accounting needed by occupancy. Preserve trend caller behavior. |
| [neutral_scene_views.py](../../features/neutral_scene_views.py) | Build inventory before planar record dropping; resolve selected-domain identity and representation once; keep raw channel evidence; project only selected occupancy geometry for the query. |
| [scene_evaluator.py](../../features/scene_evaluator.py) | Make negative-space blockers consume resolved occupancy rather than reintroducing replaced objects; propagate unknown/completeness into free area and dependent topology. Preserve legacy dict behavior. |
| [scene_inference.py](../../features/scene_inference.py), [group_self_description.py](../../features/group_self_description.py), and [furniture_frame.py](../../features/furniture_frame.py) | Audit direct source/group/frame consumers as well as objects-bucket callers. Preserve authored memberships as facts while consistently gating excluded members' analysis contributions; occupancy remains independent. |
| [geometry_views.py](../../features/geometry_views.py), boundary evidence, [scene_contract.py](../../features/scene_contract.py) | Reuse explicit plane/band, tolerance, and query context; change validation only if an actually required factual field cannot be expressed with current records. |
| [B3 section writer](../../scripts/design/space_field/run_b3_eye_plane_field.py), [comparison](../../scripts/design/space_field/run_b3_proxy_eye_plane_comparison.py), [handoff](../../scripts/design/space_field/run_b3_occupancy_only_handoff.py), [loader](../../features/discrete_space_field.py), and [connectivity](../../scripts/design/space_field/run_b3_eye_plane_connectivity.py) | Compare new generic policy against frozen accepted evidence; migrate bindings as data with exact source coverage, without changing accepted packages or teaching general code three group IDs. Loader remains a serialized consumer. |
| [IFC adapter](../../adapters/ifc_bonsai.py) and other adapters | Touch only if they fail to preserve required factual source, geometry, units, frame, or typed binding evidence. Do not add an adapter-specific occupancy rule. |
| [room_analysis_model.py](../../features/room_analysis_model.py), exports, fixtures, and config | Preserve current public model shape and direct imports initially. Scope any required new availability field or export change separately and document its caller impact before implementation. |

The shared selection must precede every negative-space, route-topology, and free-area consumer that uses physical blockers.
The selected-domain identity resolver and channel blocker machinery remain independent of substitute purpose.
Existing availability fields now propagate unresolved occupancy through the affected free-space rows, graph and adapter handoff. The public top-level room-model shape is unchanged; independent walking/visibility channel judgments remain separate.
No existing adapter, public export, or schema expansion is assumed without a failing fact-preservation or output-contract case.

## Staged minimal implementation

Stages 1 and 2 are implemented and focused-tested. Stage 3 has whole-height projection and dependent unknown propagation implemented; exact plane/body-band queries remain open. Stage 4 remains open. The original sequence below is retained as the roadmap, not a claim that all stages are complete.

1. Add the consumer-specific binding and inventory/coverage resolver in the shared Neutral Scene path. Keep raw sources and diagnostic statuses. Accept valid original geometry before considering substitute only when no required occupancy binding exists.
2. Feed one resolved occupancy selection into planar physical_occupancy and negative-space blockers. Remove the objects-merge reintroduction of represented originals, while preserving legacy dict and furniture consumers.
3. Add explicit full-height, exact-plane, or body-band query geometry and propagate unresolved coverage to free area/components/connectivity. Keep B3's 1.6 m contract as its own query.
4. Represent the accepted B3 three-target/seven-source mapping as exact input bindings; compare frozen area/count evidence for equivalent semantics and label any new semantics as a new result. Preserve all accepted files.

Use shared code first; B3 STEP and proxy IDs remain input provenance, not special cases in generic algorithms.
The general policy has no exact-three proxy limit. The frozen seven-source handoff remains a targeted regression.
No live promotion, full-suite rerun, IFC/Blender rerun, graph-wide rewrite, or B3 closure is part of this planning action.

## Verification coverage and later acceptance targets

The current focused tests cover the shared planar chain. Height/under-clearance cases and equivalence of generic B3 enrollment below remain later acceptance targets; the accepted frozen B3 evidence is unchanged.

| Test family | Required assertion |
| --- | --- |
| Role and identity permutations | Arbitrary class/name/STEP/ID/order changes with the same geometry and bindings produce the same physical result after ID remapping. |
| Independent participation | Ordinary furniture, furniture explicitly excluded from all higher analyses while still typed furniture and explicitly named in an authored group, counter/plant/shelf mass, and conceptual nonmass yield independent occupancy and furniture/group/trend/frame outputs. The existing counter-only regression does not cover the excluded typed-furniture case. |
| Helper purpose | Trend-only target and orphan analysis_substitute remain out of occupancy; an approved physical-purpose target enters only for its bound coverage. |
| Representation exactly once | Original plus target with distinct IDs, the objects merge, one-to-many conflicting targets, and many-to-one exact coverage cannot double count or silently drop a represented source. |
| Binding and geometry failures | Missing/invalid/stale/ambiguous binding, missing mesh, bad frame or units, failed section, and duplicate target IDs remain diagnostic unknown where required. |
| Height | Analytic low, suspended, and tall meshes queried below, inside, and above their actual occupied heights distinguish qualified absence from unknown; eye and body queries remain separate. |
| Shape and approximation | At an exact plane or body band wholly inside the table void, qualified geometry can establish under-clearance; a band intersecting the tabletop blocks. Whole-height projection may include the tabletop shadow. Only an explicitly accepted convex proxy may fill extra gaps, with its approximation label. |
| Domain scope | Exact boundary member inclusion/exclusion, ambiguous tokens, a door outside selected membership, and a proxy mixing boundary/interior members preserve interior contributions or stay unresolved. |
| Downstream status | Unknown blocks certified free area/components/connectivity; established occupied survives overlapping unknown; complete clearance stays unavailable without coverage. |
| Compatibility | On the same furniture eligibility facts, occupancy-only representation changes leave trend, furniture/group/orientation/affordance outputs unchanged. Explicit furniture exclusion intentionally changes those higher-level contributions. Legacy dict scenes, direct field loader, and accepted B3 handoff remain valid; no generic three-proxy assumption. |

Use small analytic scenes with known polygon/section areas so area and topology assertions have independent expected values.
Keep the accepted B3 package as a frozen comparison for equivalence cases; compare source count, coverage, qualified area, unknown area, and selected lattice statuses.
If a new query or policy changes semantics, publish a separately labeled result and explain the difference instead of rewriting accepted evidence.
Focused tests should run only with the corresponding implementation; this document creation does not run them.

## Acceptance and held decisions

Acceptance requires the inventory partition **I = O disjoint-union S disjoint-union U**, explicit excluded conceptual/boundary sets, and per-source provenance for every term.
Each represented original must map to exactly one selected geometry or one unresolved reason; each substitute target must have unique exact coverage and count once in the geometry union.
Analytic scenes must match known occupied and conditional-free areas at stated heights, including low, suspended, under-table, and mixed-boundary cases.
Free area, components, and connectivity must refuse completeness when unknown support intersects them or cannot be localized.
On the same furniture eligibility facts, furniture and trend results must remain invariant under occupancy-only representation changes; adding explicit furniture exclusion intentionally changes higher-level contributions.
Legacy dict behavior and A-loader consumption must remain stable.
The B3 frozen count/area comparison must match when semantics are equivalent, while any intentional change is separately labeled and leaves the accepted run intact.
Passing these criteria would support a scoped policy implementation, not automatically prove complete building inventory, exact original material, full 3D clearance, or B3 closure.

Held for a later query design: the owner-defined XX threshold and the exact floor-contact/support convention.
Neither held value blocks the generic source-accounting and substitute-purpose stage.
