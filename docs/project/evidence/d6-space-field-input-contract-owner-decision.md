# D6 空间场 IFC -> Neutral Scene 输入契约 Owner 裁决

- 日期：2026-10-01
- 对象：`docs/project/space-field-ifc-neutral-scene-input-contract.md`
- 依据：`docs/project/evidence/d6-space-field-input-contract-independent-review.md` 及返修后的契约草案

## 裁决

**APPROVE LIMITED DESIGN GATE**：允许进入有界、只读的空间场输入设计实验。

这不是 production implementation approval，也不冻结公共 API、统一状态 enum、boundary scope、domain 自动推导、opening subtraction、free-space backend、采样分辨率、route width、空间角色或 Bayesian/ML 模型。

## 已接受的设计边界

- IFC 原生事实、当前 Neutral Scene 能力、future derived evidence 与 owner 假设分开记录。
- `domain_record_present`、`domain_geometry_refs_available`、`domain_geometry_valid` 分层；没有合格 domain 时自由空间、连通、路径和区域结果保持 `not_available`。诊断 view bounds 只能是 `diagnostic_only`。
- `SourceOpening` 当前可有空 `host_refs`；host ref 必需是未来资格规则，不写成当前 schema 约束。当前 adapter 只提取 opening/host/geometry provenance。
- `available`、`partial`、`missing`、`invalid`、`ambiguous`、`conflict`、`unsupported`、`not_available`、`diagnostic_only` 作为设计候选状态保留；正式 enum、优先级、聚合和序列化仍 deferred。
- boundary、opening、physical occupancy、walk blocking、visibility blocking 保持独立通道。
- 门默认关闭只作为 owner scenario assumption，不作为 IFC 观测，也不关闭所有 boundary opening。

## 下一阶段允许范围

实验 session 可以读取真实 IFC、现有 IFC4 fixture 和 Neutral Scene 代码，执行有限的只读输入盘点与可视化，至少覆盖：

- 合格/缺失 domain；
- opening-host 事实与断开关系；
- `partial`、`conflict` 或 `unsupported` 传播；
- source geometry、diagnostic bounds 和 provenance；
- 无 domain 时不生成自由空间或连通结果。

实验不得选择 production backend、resolution、threshold、route width、空间角色分类器或 Bayesian/ML 模型；不得修改 production code、adapter、正式测试、公共 API、依赖、源 IFC 或用户 Blender 文件。

**STOP FOR SPACE FIELD INPUT DESIGN EXPERIMENT**

## Repair v1 Controller Review: 2026-10-01

The `repair_v1` delivery is sufficient to send to independent review. It
resolved the original evidence mismatch by executing the fixture adapter cases
with recorded commands and exit codes, producing actual PNG renders with a
camera, and separating the live IFC native inventory from the unverified live
geometry adapter path.

Accepted for review:

- five fixture cases with adapter payloads and provenance;
- explicit-domain closed/manifold observation;
- missing domain geometry and disconnected opening-host relation evidence;
- concrete `unsupported_grid_axis_curve` uncertainty as the current API
  expression of unsupported input;
- source-fact-only live/fixture Blender previews;
- temporary reproduction, PNG/Blend readback, JSON and SHA-256 checks.

Still unresolved and therefore not accepted as production evidence:

- live IFC geometry extraction;
- free-space, connectivity, or opening subtraction;
- formal unified status enum;
- boundary scope, room inference, door-state behavior, backend, resolution,
  route width, space roles, Bayesian/ML, and public API.

Next action: send `repair_v1` to an independent reviewer for a bounded review.
If accepted, close the input-contract repair and start a separate design
experiment for enclosed-room/analysis-domain candidates, keeping wall
thickness as physical field geometry.

## Repair v1 Independent Review Decision: 2026-10-02

The independent review returned `ACCEPT LIMITED DIAGNOSTIC EVIDENCE`.

The input-contract repair is closed at the diagnostic boundary. The review's
two provenance qualifications remain recorded: case-level `exit_code` values
are runner fields rather than independent subprocess exit codes, and the
historical failed runner lacks a separate byte-level hash. Neither blocks the
bounded conclusion that the five fixture cases, source-fact previews,
provenance, manifest, and temporary reproduction are mutually consistent.

## Next Gate: Enclosed-Room / Analysis-Domain Candidate Experiment

Start a new design experiment, with a new session and a separate independent
review, to compare three scope candidates:

1. explicit room geometry such as a selected `IfcSpace`;
2. an authored closed curve or analysis proxy;
3. a derived closed wall shell with wall thickness retained as physical field
   geometry.

The experiment must compare candidate geometry, closure, source references,
wall inclusion, and domain/field separation. It must not choose a production
boundary construction, infer a door state from geometry, select a grid or
polygon backend, or implement free-space/path/space-role production logic.

**STOP FOR ENCLOSED-ROOM DOMAIN CANDIDATE DESIGN**

## Enclosed-Room Candidate Independent Review Decision: 2026-10-02

The independent review returned **`ACCEPT LIMITED DIAGNOSTIC EVIDENCE`**.

The experiment is accepted for its bounded conclusions:

- a single large room can produce an automatic provisional candidate;
- explicit user-authored or explicit IFC intent has higher priority and can
  suppress the automatic default while preserving it as provenance;
- automatic candidates remain unconfirmed until user acceptance;
- wall thickness remains in physical field geometry while scope/enclosure and
  future free-space geometry stay separate;
- multi-shell, open-boundary, cross-floor, missing-geometry and broken
  opening-host cases retain distinct diagnostic states;
- the live IFC remains native inventory only, with geometry extraction
  `not_verified`.

The following are recorded as non-blocking corrections before downstream
consumption:

1. Rename or redraw the static interaction panel whose title says
   `authored / explicit` while displaying the automatic shell case.
2. Keep `selection` documented as a summary; any future consumer that reads it
   independently must carry candidate references or snapshots rather than
   treating `selected_candidate_id` as a complete candidate record.

These corrections do not require rerunning the nine-case experiment. They are
documentation/interaction-contract maintenance and must not be used to imply
that a production selector or UI exists.

## Next Gate

Proceed to a separate boundary-construction design experiment. Compare inner
wall face, outer wall face, wall centerline, and user-authored closed curve as
scope constructions while preserving wall thickness as physical field
geometry. This experiment must decide how scope geometry is represented and
audited; it must not implement free-space, route, walkability, visibility,
space-role, Bayesian/ML, or production UI behavior.

**STOP FOR BOUNDARY CONSTRUCTION DESIGN REVIEW**

## Owner Direction: Enclosed Room Candidate and Wall Inclusion

The owner accepts a Revit-like concept as a design candidate: a geometrically
enclosed shell can provide a room/domain candidate, with doors and windows
treated as closed in the default enclosure scenario. This is a derivation
scenario, not an assertion that the IFC records a verified door state.

The candidate must preserve wall geometry as part of the spatial field. It
must not copy an interior-only room boundary that silently removes wall
thickness. The design therefore keeps two linked facts:

- **Scope/enclosure geometry:** the closed shell that defines where this room
  candidate is considered;
- **Physical field geometry:** the wall and other source solids retained as
  occupancy/boundary evidence, so derived free space is computed inside the
  scope while the wall remains represented and auditable.

An explicit authored domain or manually supplied closed curve remains a higher
priority scope source than an inferred enclosed-room candidate. A derived room
candidate must carry its closure scenario, wall/opening source references,
analysis plane, units, and geometry status. Boundary semantics must state
whether the boundary is an outer wall face, inner face, centerline, or another
explicit construction; this choice is deferred for experiment rather than
silently inherited from Revit defaults.

Room enclosure is a scope/topology hypothesis. It does not by itself decide
walking permeability, visual permeability, route width, or space role. Later
channel-specific opening evidence may refine those outputs.

Next bounded experiment: compare an authored closed curve, an explicit room
geometry source, and a derived closed wall shell with wall thickness retained;
render source shell, wall occupancy, assumed closed openings, and derived free
space separately. Do not implement production room inference or freeze the
boundary construction in this experiment.
