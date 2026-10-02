# D6 封闭房间 / AnalysisDomain 候选实验独立复核

- 复核日期：2026-10-02
- 复核模式：`$stop-that-shit review`；只读证据复核
- 复核范围：`outputs/design/space_field_domain_candidate_experiment/` 及用户指定的契约、证据、runner
- 总体结论：**ACCEPT LIMITED DIAGNOSTIC EVIDENCE**
- 终止标记：`STOP FOR ENCLOSED-ROOM DOMAIN CANDIDATE INDEPENDENT REVIEW`

本实验可以作为有界的设计诊断证据：9 个 case 均存在，候选优先级与状态传播可由 JSON 和 runner 对上，显式候选没有静默回退到 automatic candidate，单一大房间的 automatic candidate 保持未确认，墙体厚度和 source/candidate/free-space 分层被保留，真实 IFC 仍是 native inventory。没有发现足以否定这组有限诊断证据的一致性 blocker。

这不是 production boundary construction、free-space backend、网格/多边形、resolution、route width、threshold、Bayesian/ML、公共 API 或 implementation approval。下一阶段仍须经过 owner review；本复核不授权实现。

## Blockers

### 当前有限诊断证据

无 blocker。candidate payload、优先级、主要状态、候选几何引用、provenance 和已记录的语义复现结果相互支持。

### 下一阶段 gate

下一阶段不能自动开启。boundary construction、partial/ambiguous 聚合、用户确认后的 accepted 生命周期、跨楼层/孔洞规则和 free-space gate 仍需单独 owner review。这里是设计 gate，不是把本实验升级为 production 证据。

## Important findings

1. `interaction_states.svg` 的第二个面板标题是 `authored / explicit`，但面板使用的 fixture key 是 `automatic_closed_wall_shell`，图中主要画的是橙色 automatic candidate 和绿色 selected/hover 状态，没有蓝色 authored override。JSON 语义没有因此改变，但静态图的候选来源标签不够清楚，容易把 automatic candidate 读成 authored/explicit。作为交互契约证据继续使用前，应把标题改成 automatic shell，或在同一面板明确画出 authored/explicit override。

2. `single_large_room` 的 case-level `candidate_records` 保留了 automatic candidate 和 user-authored candidate 的完整记录，但 `selection` 只保留 `selected_candidate_id`、优先级顺序和抑制/确认摘要，并不独立携带两个候选的完整元数据。当前 bundle 通过 `candidate_records + selection` 可审计；若未来把 `selection` 单独消费，应明确它是 summary，或把候选引用/快照加入 selection 设计。

3. `negative_domain_missing_geometry` 和 `negative_opening_host_relation_broken` 保留了显式 intent 的 candidate id，同时分别给出 `domain_status=not_available` / `status_reason` 和 `evidence_status=missing|partial`。这符合“不静默回退”的实验结论，但必须继续解释为“保留用户/源 intent 与证据缺口”，不能把 `selected_candidate_id` 读成合格 domain。断 opening-host case 的 adapter payload 有 `host_refs=[]`，而 `uncertainty_codes` 为空；`partial` 是候选层对证据缺口的传播，不能冒充 adapter 已产生统一 uncertainty enum。

## 按 1–10 项逐条结论

### 1. 九个 case 覆盖

**通过。** `candidate_results.json` 的 `cases` 数为 9，case id 与要求一一对应：

| 要求 case | 实际 case id | 结论 |
|---|---|---|
| positive explicit `IfcSpace` | `positive_ifc4_explicit_ifcspace` | 存在；真实 fixture 观察到 `IfcSpace=1`，domain mesh `is_closed=false`，因此 candidate 为 `partial`，没有被写成合格闭合 domain |
| missing domain | `negative_missing_domain` | `analysis_domain=null`，选择为空，`not_available` |
| domain missing geometry | `negative_domain_missing_geometry` | domain record 保留；adapter uncertainty 为 `missing_geometry`，candidate `evidence_status=missing`、domain 结果 `not_available` |
| broken opening-host relation | `negative_opening_host_relation_broken` | opening geometry 保留，`host_refs=[]`，candidate 为 `partial` / evidence gap |
| automatic closed wall shell | `automatic_closed_wall_shell` | 单 connected closed shell，`computed` automatic candidate |
| single large room | `single_large_room` | automatic candidate 与 user-authored closed curve 同时保留 |
| multi-shell conflict | `multi_shell_conflict` | candidate `ambiguous`，selection 无合格 domain |
| open boundary | `open_boundary` | candidate `partial`，selection 无合格 domain |
| cross-floor candidate | `cross_floor` | candidate `invalid`，selection 无合格 domain |

`fixture_manifest.json` 也把正向 IFC fixture、三个 negative variant 和五个 synthetic variant 分列记录。

### 2. 优先级只作为设计实验结果

**通过，有一项 schema 说明。** `priority_order` 与 runner 的 rank 均为：

`user-authored > explicit IFC > automatic candidate > diagnostic-only > not_available`

实验没有修改 production selector 或公共 API。具体行为符合要求：

- 显式用户输入优先；
- 显式 IFC 优先于 automatic candidate；
- automatic candidate 只有 `status=computed` 才能被选为默认候选；
- automatic candidate 的 `user_confirmed=false`、`accepted=false`，并在 selection 中标出 `user_confirmation_required=true`；
- 显式 candidate 即使 `partial` 或 `not_available` 仍保留，不静默回退到 automatic candidate；
- 没有合格 domain 时，selection 的 `domain_status` 为 `not_available`，或 `selected_candidate_id=null`。

`not_available` 在当前 bundle 主要是终止状态，而不是另一个可接受 candidate 的 `priority` 值；这与 diagnostic-only view bound 的分层相容，但后续 schema 应继续明确该区别。完整候选元数据在 `candidate_records` 中，`selection` 是摘要。

### 3. 单一大房间结论

**通过。** `single_large_room` 形成 `candidate:auto:single_large_room`，状态为 `computed`，但 `user_confirmed=false`、`accepted=false`，没有被称为真实房间。`automatic_closed_wall_shell` 的 selection 明确标记 `selected_candidate_is_default_only=true` 和 `user_confirmation_required=true`；单一大房间因已有 user-authored closed curve，自动候选被保留并被显式输入压过。runner 的 endpoint identity 是 probe-only，provenance 明确没有 production tolerance；没有固定绝对距离、墙厚、面积或心理阈值。

### 4. 显式 domain 覆盖 automatic candidate

**通过，带 selection summary 说明。** `single_large_room.candidate_records` 同时保留：

- `candidate:auto:single_large_room`：`source_kind=automatic_candidate`、`priority=automatic candidate`、`accepted=false`、`user_confirmed=false`；
- `candidate:user:closed-curve`：`source_kind=user_authored`、`priority=user-authored`、`accepted=true`、`user_confirmed=true`。

selection 选择 user-authored，并有 `automatic_candidate_suppressed_by_explicit_intent=true`。候选记录保留 `candidate_id`、source kind、priority、accepted、user_confirmed、provenance、geometry refs 和 source refs；但 selection 对象本身是摘要，不是两个候选的完整快照。

### 5. 墙体和 domain 的几何分层

**通过，candidate geometry 的独立命名仍需保持清楚。** `source_geometry.json` 每个 case 分列：

- `scope_enclosure_geometry`；
- `wall_occupancy_geometry` / `physical_wall_field`；
- `opening_host_evidence`；
- `derived_free_space_candidate`，固定为 `status=not_available`。

synthetic wall field 保留 `thickness`（0.18 或 0.20）和 level；没有把墙体简化成 interior-only room。candidate geometry 目前由 `candidate_records.geometry_refs` 与 provenance 表达，而不是另建一个名为 `candidate_geometry` 的顶层对象；这在当前 bundle 可追溯，但后续设计应避免消费者把 scope/source geometry 误当 candidate geometry。没有声称已计算 free-space、connectivity、path、walkability 或 visibility。

### 6. 状态与 `evidence_status`

**通过。** 状态和证据状态分别保留：

- `computed`：automatic closed wall shell、single large room 的合格拓扑候选；
- `partial`：explicit IfcSpace 的未闭合网格、broken opening-host，以及 open boundary candidate；
- `missing`：domain missing geometry 的 `field_geometry_status/evidence_status` 与 adapter 的 `missing_geometry` uncertainty；
- `ambiguous`：multi-shell candidate，selection 不静默选择；
- `invalid`：cross-floor candidate，保留跨 level 原因；
- `not_available`：missing domain、missing geometry 的 domain 结果，以及没有合格 candidate 的 selection；
- `diagnostic_only`：无合格 domain 的诊断 candidate/source kind/priority 和 fallback-like evidence。

`status`、`domain_geometry_status`、`field_geometry_status`、`evidence_status`、`uncertainty_status` 没有被压成一个布尔值。开放边界的 candidate 本身是 `partial`，但 selection 为 `not_available`，因此没有产生合格 domain；这一区分是正确的。

### 7. UI 交互契约

**有限通过。** SVG 是静态交互状态图，不是真实 UI。图例包含：橙色 automatic candidate、蓝色 authored candidate、绿色 hover/selected、深灰 physical wall field、红色 opening evidence；文本包含 candidate not accepted、accept/reject、edit/redraw、split/merge、user-confirmed/accepted 语义。实验记录也明确说没有实现真实 hover。

重要限制是第二面板标题 `authored / explicit` 与其中实际使用的 automatic shell 不一致，见 Important finding 1。除该来源标签问题外，没有把 SVG 声称成已实现 hover，也没有显示伪造 free-space、route 或 walkability 结果。

### 8. 真实 IFC 边界

**通过。** `live_ifc_inventory` 标记 `native_inventory_only=true`、`geometry_adapter=not_verified`，并只记录 IFC4 和原生计数：`IfcSpace=0`、`IfcOpeningElement=0`、`IfcRelVoidsElement=0`、`IfcRelFillsElement=0`、`IfcDoor=6`、`IfcWall=11`。没有把真实 IFC 盘点升级成 automatic room inference；没有把门几何解释成 opening relation；`closed_by_assumption` 只出现在 synthetic closure scenario，不是 IFC 事实。

### 9. 复现与 provenance

**通过，哈希独立重算有边界。** `verification_report.json` 的结果是 `verified_semantic_reproduction_with_known_ifc_timestamp_difference`，并记录：

- `case_payload_equal=true`；
- `priority_equal=true`；
- `constraints_equal=true`；
- `fixture_manifest_equal=true`；
- JSON、source geometry、provenance、SVG 的 primary/reproduction `byte_equal=true`；
- disposable IFC 唯一已知差异是 IfcOpenShell `FILE_NAME` 自动时间戳。

我另外完成了有界 JSON/文件大小比较：primary 与 `tmp_reproduction_20261002` 的 candidate/manifest/source geometry/provenance/SVG 文件大小相等，candidate payload、priority 和 constraints 深度序列化相等；SVG XML 解析通过。`artifact_manifest.json` 的条目均存在且记录的 bytes 与当前文件一致，manifest 中没有 `tmp_reproduction_20261002` 路径。

不要把该结果写成“所有文件字节完全一致”：IFC fixture 明确是已知时间戳差异。当前 review guard 拒绝了本轮独立 SHA-256 重算命令，因此本复核对哈希一致性的判断依赖已存在的 `verification_report.json` 和 manifest 中的记录；这列入未验证项，不改变已记录的语义复现结论。

### 10. 范围

**通过。** 针对 `features/`、`adapters/`、`test/`、`analyzer.py`、`__init__.py`、`pixi.toml`、`pixi.lock`、真实源 IFC 和本复核目标文件的定向 `git status --short` 没有当前状态变化。输出目录中的临时复现位于允许的实验输出根目录内，但没有进入最终 `artifact_manifest.json`。实验记录的 scope audit 也保持 production features、adapters、formal tests、public API、dependencies、source IFC 和 user Blender 均未修改。

## 直接回答

- **自动候选是否可作为单一大房间的默认候选：** 可以，限于 provisional/default candidate；必须保持 `user_confirmed=false`、`accepted=false`，不能称为真实房间或已确认 AnalysisDomain。
- **用户显式输入是否正确覆盖自动候选：** 是。`candidate:user:closed-curve` 覆盖 `candidate:auto:single_large_room`，自动候选仍保留为 provenance/可审查记录。
- **墙体厚度是否被保留：** 是。synthetic physical wall field 保留 thickness；scope enclosure 与 physical wall field 分列。
- **UI 是否只停留在交互契约与静态可视化：** 是。没有真实 hover/selection UI 实现声明；SVG 只表达状态契约。
- **是否允许进入下一阶段 boundary construction / free-space design：** 不自动允许。当前证据可以关闭本次有限诊断实验的 review，但下一阶段必须先完成 owner review，并处理上述来源标签、selection summary 解释和后续 boundary/free-space gate；本文件不批准 implementation。

## 未验证项

- live IFC geometry adapter、mesh 闭合性、manifold 性、平面适配和几何质量；
- production boundary construction、opening subtraction、free-space backend、网格/多边形、resolution、route width、threshold；
- connectivity、path、walkability、visibility、space-role 和 Bayesian/ML；
- door state；`closed_by_assumption` 仍是 scenario assumption；
- 真实 UI hover、accept/reject、edit/redraw、split/merge 行为；
- selection 作为独立消费接口时的完整候选携带方式；
- 本轮独立 SHA-256 重算，因 review guard 返回 `HASH_NOT_AUTHORIZED`；已有 verification report 的哈希记录仍保留；
- synthetic endpoint identity 是否适用于任何 production 几何容差；provenance 已明确不适用。

## 实际读取文件、命令和技能

### 实际读取文件

- `AGENTS.md`
- `docs/project/space-field-ifc-neutral-scene-input-contract.md`
- `docs/project/evidence/d6-space-field-input-contract-owner-decision.md`
- `docs/project/evidence/d6-space-field-ifc-input-contract-experiment-repair-v1-independent-review.md`
- `docs/project/evidence/d6-space-field-enclosed-room-domain-candidate-experiment.md`
- `docs/project/evidence/d6-space-field-enclosed-room-domain-candidate-comparison.md`
- `docs/project/evidence/d6-space-field-enclosed-room-domain-candidate-verification.md`
- `scripts/design/space_field/run_enclosed_room_domain_candidate_experiment.py`
- `outputs/design/space_field_domain_candidate_experiment/candidate_results.json`
- `outputs/design/space_field_domain_candidate_experiment/fixture_manifest.json`
- `outputs/design/space_field_domain_candidate_experiment/source_geometry.json`
- `outputs/design/space_field_domain_candidate_experiment/provenance.json`
- `outputs/design/space_field_domain_candidate_experiment/interaction_states.svg`
- `outputs/design/space_field_domain_candidate_experiment/verification_report.json`
- `outputs/design/space_field_domain_candidate_experiment/artifact_manifest.json`
- `outputs/design/space_field_domain_candidate_experiment/tmp_reproduction_20261002/` 下用于语义/文件大小比较的同名 JSON/SVG artifacts

### 实际执行的有界命令

- `Get-Content -Raw`：读取 AGENTS、契约、证据、runner、JSON 和 SVG；
- `rg -n -i`：定位 case、状态、优先级、candidate、provenance、free-space、UI、IFC 和范围声明；
- PowerShell `ConvertFrom-Json`：统计 9 个 case，读取每个 candidate/selection/status 字段，比较 primary 与 temporary reproduction 的 candidate payload、priority 和 constraints；
- PowerShell `[xml](Get-Content -Raw ...)`：解析 `interaction_states.svg`；
- PowerShell `Get-Item`：核对 artifact manifest 中记录的 bytes；
- `Get-ChildItem`：确认 temporary reproduction 的目录位置和最终 manifest 未引用临时目录；
- 定向 `git status --short`：核对 production/features/adapters/tests/API/dependencies/source IFC 和目标文档的范围状态。

没有运行完整 pytest、完整 live IFC geometry extraction、Blender、production backend 或 runner 以外的写入操作；本复核只读取既有实验产物。实际使用的技能只有 `stop-that-shit` review：`C:\Users\tianf\.codex\plugins\cache\stop-that-shit\stop-that-shit\0.2.2\skills\stop-that-shit\SKILL.md`。

STOP FOR ENCLOSED-ROOM DOMAIN CANDIDATE INDEPENDENT REVIEW
