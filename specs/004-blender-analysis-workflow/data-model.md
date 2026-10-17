# Data Model

**APPROVED / IMPLEMENTATION IN PROGRESS。** 用户于 2026-10-15 批准本计划。所有新格式仍在 `specs/004-blender-analysis-workflow` 中作为**提议合约**描述；尚无 Spec004 持久化实现验收证据。序列化严格 JSON，不含 arbitrary executable paths/callables。状态显示区分 runtime lifecycle 和 FieldStatus。

## 身份与请求关系

```text
Analysis workbench / shared capture + canonical identity
  ├── DomainRequest(B4 structural frame/cut, source token)
  │     └── B4Session(existing reducer + explicit confirmation)
  │            ├── DomainSessionResult(candidates + full service diagnostics)
  │            └── AnalysisDomain(actual geometry + verified member/support refs)
  └── AnalysisPlane(uuid, revision, frame) + confirmed AnalysisDomain
         └── AnalysisRequest(request_id, operation, query, grid, rules, domain)
                └── AnalysisRun(FieldSamples + snapshot + global support status)

DomainSessionResult / AnalysisRun -> immutable persisted documents
  -> manifest-derived metadata -> exact ResultRef open -> read-only snapshot/sample

AnalysisPlane / confirmed domain / request / result are separate identities.
```

改变 plane display name 不改变几何身份。plane frame 变化 revision；影响 B4 structural input 时要求按当前 reducer 规则重新确认。occupancy `origin.z` 改变 exact query semantics，但不单独撤销 XY boundary consent。source change 使相应 fingerprint/cache result stale；不能把旧 consent 静默带到新 identity。

## Records

| Record | 字段和不变量 |
|---|---|
| `PlaneRecord` | `plane_uuid: str` 唯一 UUID；`revision: int>=1`；`name: str` display-only；`origin_m: [x,y,z]` finite；`basis: [right,forward,normal]` right-handed orthonormal；`length_unit: "m"`；`support_binding: str|None`；可选 `camera_binding_ref` 仅作为已选平面的 display follower 绑定，不能改变 authoring plane 或计算几何。duplicate UUID 不能自动沿用旧 result，必须显式 duplicate-plane/reassign flow。 |
| `DomainRequestIdentity` | `request_id`；`plane_uuid` + `structural_frame_key`（XY basis/origin、固定 datum 0 m/cut 1.5 m、B4 parameters/constants version 和 structural fingerprint）；不直接绑定完整 occupancy plane revision。它不是 occupancy `AnalysisRequest`；runtime job/AnalysisRequest 仍绑定完整 plane revision。 |
| `CanonicalSourceIdentity` | canonical `source_object_id="ifc-object:{GlobalId}"`；`source_id=GlobalId`；verified `source_class`；current `project_global_id`、IFC source identity、STEP id、Blender object/data refs 存在 capture provenance。GlobalId/project 必须在当前 linked IFC 唯一。legacy map 记录 old id、STEP、GUID、project/source identity、mesh ref and geometry digest，全相符才接受；不做 string-prefix rewrite。 |
| `CanonicalCapture` | `capture_id`、`session_token`、scene/file identity、IFC identity/schema、units scale、frame/subframe；一份 full source inventory + evaluated geometry records + unresolved records；每源 actual transform/modifier/evaluated-frame/properties/material facts；structural subset 是同一 scene source ids/geometry refs 的派生只读视图。capture 全面性不足时 freshness unverified 或请求失败。 |
| `SupportBinding` | `source_object_id` 必须唯一对应当前 canonical IFC Slab/Floor-capable source，带 IFC project, class, geometry refs/digest, capture fingerprint 和显式确认记录。未绑定不创建排除；不提供 class-wide inference。只移除恰好确认 membership/domain source。 |
| `B4Session` | reducer `session_state`、monotonic `session_revision`、ordered action/status/reason events；`current_binding` 包 `source_revision`（stable structural-source-facts digest）、`frame_id`（canonical structural frame key）、B4 request + candidate identity + conflict acknowledgement；两者不包含完整 occupancy plane revision/exact-Z/name/camera/volatile capture token。`invalidated` sticky 直到新鲜显式 user confirmation。new canonical mapping 不迁移确认。 |
| `AnalysisDomain` | 使用现有 record；exact polygon/mesh `geometry_refs`、holes、provenance、boundary member canonical IDs；inferred outline 默认 `source_id=None`；`domain_geometries` handoff 中 record 的 actual authored `MeshGeometry3D` 或 `_qualified` 实物。 |
| `AnalysisRequest` | 使用 `features.analysis_requests.AnalysisRequest`；request UUID、plane/domain identity、`GeometryQuery` whole-height 或 exact XY、`GridSampling(origin,spacing=.25,n_rows,n_cols)`、现有 rules/tolerances/backend. Exact `world_z_m=plane.origin_m[2]` 在 request freeze 时确定且不可由显示 lift 改变。 |
| `SourceAudit` | source object id、role/class、geometry refs/digest、capture completeness、mass/representation status、proxy exact-once selected/represented IDs、boundary/support decisions、uncertainty reason、materials/transforms/modifiers facts used by query。全对象一次记录；无几何必须留 unknown fact。 |
| `CellResult` | `row,column` 唯一 lattice index；`value: bool|None`；`status: FieldStatus` 六态；`explanation/ref`；`source_ids/ref`；`support_delta`；`provenance_delta`；完整 FieldSample reconstruction 需保留 query/revision/tolerance/plane/domain/frame/height-band/demand/version/audit/support/explanation/status/value 的每个字段。未知值不推断 empty。 |
| `RunSnapshot` | run UUID；完整 shared frozen query/snapshot provenance；plane/domain identities/revisions；domain request identity；semantic key、structural/full source fingerprints、registry/helper/algorithm/schema/backend versions；grid layout；global `support_status`、explanation；cell records；created timestamp。display color/lift/name 不进入 semantic key。 |
| `OverlayRecord` | tagged native mesh handle/id；vertices/faces；face attribute `cell_index`（face fragment 指向共享 CellResult）；row/column 可复用 face attrs或 shared lookup；presentation palette/lift 单独记录。每 face 属某 cell fragment，mesh 不定义 occupancy。world pose 来自 RunSnapshot frozen frame；禁止 live parent transform。 |
| `RuntimeJob` | process-global slot：`job_id`、lifecycle enum、scene-session token、plane UUID/revision、domain confirmation binding、request semantic key、source/config fingerprints、progress counters/stage/elapsed、process handle、cancel flag、temporary result path、error。Blender runtime only, never persisted/resumed. |
| `Freshness` | `current | stale | unverified | historical`；外部于 FieldStatus。只在所有 tokens 与 capture comparison 验证相同时 current。load/reopen 默认 historical/unverified；任一不可观测变化不猜测 current。 |
| `PersistedDocument` | top-level `kind: domain_session | free_space_run`、`result_id`、`schema_version`、`algorithm_version`、snapshot identity、authoritative payload、digest；free-space payload 使用 shared `tables`/cells；domain payload 保留既有 service facts。JSON embedded in fake-user Text；manifest 仅引用 document/ref，不复制权威结果。Additional sidecar final artifact optional. malformed/future-schema/digest mismatch rejected, with prior embedded bytes/mesh retained. |

## Localized unknown support semantics

`GeoJSON` is a strict data-only `Mapping[str, object]`: a finite world-XY/metre geometry with `type` equal to `Polygon`, `MultiPolygon`, `LineString`, `MultiLineString`, `Point`, `MultiPoint` or an explicit empty `GeometryCollection`. Polygon rings are closed with valid shell/hole topology; no Feature wrapper, CRS conversion, implicit buffer or NaN/Infinity is accepted. Geometry decoding and topology validation occur in Pixi, never by importing Shapely into the addon.

`UnknownSupportEvidence` (owned by `adapters/blender_analysis_session.py`) has `source_object_id`, `selected_owner_ids`, `query_key`, `geometry_digest`, `helper_algorithm_version`, `coverage_complete: bool`, `state: valid_nonempty | validated_empty | missing_or_malformed`, `geometry: GeoJSON | None`, and `reason`. `validated_empty` requires successful trusted helper identity/query/complete-coverage proof; `{}`, `None` and an unverified empty geometry are never that proof. Only accepted evidence is handed to the optional field mapping; failed-target, missing/malformed or incomplete/ambiguous multi-owner evidence keeps each unresolved owner global unknown. A complete multi-owner support is usable only after exact selected-owner coverage validates as a whole; the generic multi-owner case cannot be guessed local.

## Concrete adapter records and ownership

These minimum fields define every new type crossing the task seams. They are adapter-local records, not a new core class hierarchy. Existing `AnalysisPlane`, `NeutralSceneV2`, `MeshGeometry3D`, `AnalysisRun` and `FieldSample` refer to the Spec003 checkpoint contracts and must be verified by T0 before implementation.

| Type | Owning module | Minimum fields |
|---|---|---|
| `CaptureJob` | `adapters/blender_analysis_capture.py` | `capture_id`, `session_token`, `inventory`, `next_index`, accumulated `sources`, `geometries`, `unresolved`, `started_monotonic`, `cancelled`, `errors`, `callback_seconds`, `max_object_seconds`; Blender runtime handles stay in memory only. |
| `CaptureProgress` | same capture module | `capture_id`, `stage`, `processed`, `total`, `elapsed_seconds`, `callback_seconds`, `max_object_seconds`, `errors`, `complete`, `cancelled`. |
| `CanonicalCaptureInput` | same capture module | Wire form of `CanonicalCapture`: `capture_id`, `session_token`, `ifc_identity`, `project_global_id`, `schema`, `units_scale`, `frame`, full `source_inventory`, `geometry_records`, `unresolved_records`, `capture_complete`, `observation_token`; stable digest inputs are separated from volatile provenance. |
| `LegacySourceBinding` | `adapters/bonsai_live.py` | `legacy_object_id`, `legacy_step_id`, `global_id`, `project_global_id`, `ifc_identity`, `canonical_object_id`, `geometry_refs`, `geometry_digest`, `scope`, `covered_owner_ids`, `required`; all must agree with current capture before enrollment. |
| `SupportBinding` | `adapters/bonsai_live.py` | `source_object_id`, `project_global_id`, `source_class`, `geometry_refs`, `geometry_digest`, `capture_fingerprint`, `confirmation_id`; unique current canonical source validation is mandatory. |
| `BonsaiLiveScene` | `adapters/bonsai_live.py` | `scene`, `structural_scene`, `structural_context`, `identity_map`, `domain_support_audit`, `structural_fingerprint`, `full_fingerprint`, `capture_fingerprint`, `diagnostics`. |
| `StructuralContext` | `adapters/bonsai_live.py` | `plane_uuid`, `xy_origin_m`, `xy_basis`, `datum_z_m=0`, `cut_z_m=1.5`, `b4_parameters`, `constants_version`, `structural_frame_key`; this context actually drives B4 geometry, not only a token. |
| `DomainSessionResult` | `adapters/blender_analysis_session.py` | `domain_request_identity`, `session_state`, `session_revision`, `events`, `candidates`, `selected_candidate_id`, `confirmation_binding`, `analysis_domain`, exact `domain_geometries`, `scope_polygon`, `status`；保留/引用既有权威 service payload 的 `provenance`, `attempt`, `current`, `handoff_executed`, `downstream`, `apertures`（含 significant residuals）, `source_count`, `geometry_count`, `source_identity`, `scenario`, `tolerance_mm2` 和 candidate `id/version/area/holes/label_xy/reason`，以及 ignored tiny residual/stale/error/conflict diagnostics；不从显示 mesh 重新推导。 |
| `ValidatedAnalysisResult` | `adapters/blender_analysis_session.py` | immutable validated `document`, `schema_version`, `algorithm_version`, `digest`, `job_id`, `plane_uuid`, `plane_revision`, `semantic_key`, `snapshot`, `lattice`, `cells`, precomputed `display_fragments`, `source_audit`; no bpy/process objects. Addon consumes its wire record without importing this heavy module. |
| `ResultRef` | session adapter 的 lightweight read portion | frozen `kind`, `result_id`, `digest`；kind 区分 domain/free-space，digest 绑定不可变精确内容；无可变 latest 指针。 |
| `ResultMetadata` | same read portion | `ref`；`schema_version/algorithm_version/backend_versions`；`project_source_identity`；structural/full fingerprints（按 kind 适用）；`domain_identity`；`plane_uuid/revision/frame_key`；`request_identity`；free-space `operation/query_key/semantic_key`；domain 为 structural request/frame 而无 occupancy query；持久事实不包含可自证 current 的 flag。 |
| `ResultReadContext` | same read portion | expected identity/version fields 对应 metadata；expected-domain 默认 None 仅用于未确认域的精确诊断读取；`require_confirmed_domain: bool=False`；`require_current: bool`；显式 `allow_historical: bool`；可选经过既有 freshness 比较验证的 current source/request/domain/plane observation。confirmed/current-domain 消费必须要求非 None domain/confirmation；require_current 缺少匹配核验证据即拒绝；本 record 不执行 capture。 |
| `ReadOnlyResultSnapshot` | session adapter | validated immutable `ref`, `metadata`, authoritative `payload`, contextual `freshness`；domain payload 是 DomainSessionResult snapshot，free-space 是既有 compact AnalysisRun payload；冻结嵌套记录/防御复制，consumer 修改不能回写内存文档/embedded bytes。纯读取不启动 job、不更新 consent/current、不读取 mesh。 |

## 统一 workbench 与只读消费边界

B4 Domain section 使用现有 operation 语义和 service/reducer，独立生成 DomainSessionResult；free-space 使用既有 AnalysisRequest 的 `operation="free_space"` / `physical_occupancy` 和 Field 合约。架构中的 Operation 是既有 string/descriptor vocabulary，不是假设已有 Operation class。substitute registry 只选表示，不变成 operation/job/result dispatcher。新操作未来增量接入同一 UI/service，共享 capture/identity/domain/result access；本轮没有真实下游分析 consumer。

Result catalogue 是已有 embedded manifest/documents 的只读轻量投影；live 内存文档与从 Text 恢复的文档均输入同一 list/open 入口。list 只暴露 metadata；open 必须用完整 ResultRef 精确匹配且校验 digest/支持的版本及 expected identities，missing、duplicate/conflicting ambiguity、kind/domain/plane/revision/mode/query/source mismatch 一律拒绝。没有自动选择 latest、按时间回退、跨域拼接或 mesh/color 推断真值。domain 的候选/诊断 snapshot 不因未确认而不可读；其可读不授予 AnalysisDomain consent。

未确认/拒绝且无合法 active domain 的 DomainSessionResult 明确 `analysis_domain=None`、`confirmation_binding=None`，对应 ResultMetadata.domain_identity=None；candidate/request identities 保留。exact diagnostic open 允许 context expected-domain=None 且 require_confirmed_domain=False；需要 confirmed-domain/current-domain 的消费者必须置该要求并拒绝 None。候选身份不能替代有效 AnalysisDomain；有旧 active domain 时如实保留 reducer 的 current/attempt 差异，不因新 attempt 失败擅自清空或更新 consent。

historical read 必须显式允许；重开无 sidecar 的 payload 可只读恢复但 freshness 为 historical/unverified。要求 current 必须有新鲜核验证据；freshness 与每个样本 FieldStatus 独立。free-space `physical_occupancy_bool` True=occupied，False 在 established/conditional 才表示本 query 的 known-empty；unknown/outside/invalid/not_available 仍为 None。conditional 限制、完整 query/support/source_ids/provenance/explanation 保持，任何 current 标记均不证明 complete occupancy、clearance 或 routing。

## Stable digests, B4 context and request-scoped support

The canonical structural digest uses sorted stable project/source identities, structural source geometry digests, relevant transforms/factual properties, structural XY context and algorithm/config versions. The full digest additionally covers physical occupancy sources/query-relevant facts from the same full capture. Both exclude timestamp, capture/job/session UUID, runtime pointers, selection/visibility/dirty state, camera/display state, IFC transaction counter and file mtime. Capture-volatile observations remain separate freshness audit tokens; structural digest also excludes occupancy-only furniture/proxy changes. Unchanged recapture must reproduce the same stable digests.

B4 receives the actual `structural_scene` and `StructuralContext` at datum 0 m/cut 1.5 m with the selected XY basis. Occupancy receives the full scene and full frozen plane revision/Z. Merely changing `structural_frame_key` while passing the occupancy plane to B4 is invalid. Start verifies that the full capture observation token is current; if stale or unverifiable, it recaptures the full scene once and derives both structural/full views and digests from that capture before validating domain consent.

After `SupportBinding` uniquely resolves, map its `source_object_id` to that canonical source's `source_id` (GlobalId) only in the request-scoped child domain passed to `_scope_exclusions`. Preserve inferred B4 `source_id=None` in shared scene/session facts; unbound or rejected binding excludes no slab. Exact confirmed boundary members alone participate in closed-scenario exclusions.

`CameraBinding` is display-only follower metadata: no camera transform, clipping or display offset enters authoring geometry, semantic keys, structural/full digests or occupancy. Reopen sets historical/unverified; Start must freshly verify IFC/project identity, GUID mapping, source fingerprints and support/domain bindings before a new run. Save Copy failure retains live Text/overlay/result and cleans only addon-owned partial files; only successful save records an artifact.

提议的 additive input：`unresolved_supports: Mapping[str, GeoJSON | None] | None = None` (field mapping coordinates are query-plane local; raw helper GeoJSON is world XY). Absent (`None`) keeps legacy `unresolved_source_ids` global semantics. For a source with a validated non-empty support geometry, an eligible cell becomes unknown iff exact geometric intersection is non-empty; line/point touch counts as uncertainty. An empty support is safe only when a trusted helper proves selected identity, query, and complete coverage and emits a qualified empty fact; an untrusted empty object remains unresolved. A known occupied positive wins over unknown support. Domain clipping occurs before evaluation; support fully outside domain affects no cell. Missing/malformed geometry, invalid transform, failed required proxy, incomplete or ambiguous multi-owner coverage, or unsupported query keeps that source global unknown. Run-level `support_status` remains independent of every cell status.

Existing exact cell occupancy semantics remain authoritative: positive area occupancy is occupied; mere boundary line/point mass contact does not fill a cell. The more conservative touch rule applies to uncertainty support only. No tolerance buffering is introduced. Algorithm version advances because the semantic key/result interpretation changes.

Coordinate seam: trusted helper `UnknownSupportEvidence.geometry` retains raw world-XY metres. Before `FreeSpaceField`, `features.analysis_requests` applies exactly once the same affine frame transform captured by `_components(geometry, request.plane.origin[:2])` for occupied geometry into query-plane local coordinates. Reuse the coordinate mathematics, not a polygon-only extractor: preserve polygon/multipolygon rings, line/multiline coordinates, point/multipoint coordinates, and qualified empty geometry so touch evidence is not dropped. Domain/grid/cells use that same local frame. Preserve raw geometry, units, frame and applied-transform audit. Qualified-empty remains empty after transform. Never intersect raw world XY with local cells or apply the origin twice; unsupported basis is conservatively rejected. T2 tests use plane origin (100,200), a nonzero grid origin, and translated line/point touch supports to expose misplaced unknown/outside supports. No core import of adapter records is introduced; the core consumes existing plain geometry mapping/evidence primitives.

## Transitions

```text
plane created -> ready
ready -> B4 capturing -> candidates previewed -> selected -> user confirms -> domain active
domain active + request -> capturing -> running -> complete
capturing/running -> cancelling -> interrupted
capturing/running -> failed | interrupted
complete -> stale (source/request/plane/config observed changed)
saved complete -> historical on load; validated user refresh -> current new run
```

Never transition `selected` to `confirmed` automatically. A running result cannot become current after ABA edits, undo, file switch, duplicate UUID, process/job/session mismatch, or an unverified source condition.
