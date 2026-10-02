# D6 空间场 IFC → Neutral Scene 输入契约独立复核

- 日期：2026-10-01
- 复核对象：`docs/project/space-field-ifc-neutral-scene-input-contract.md`
- 结论：**REVISE**
- 生产实现：不批准

## 总结

草案正确守住了主要边界：`analysis_domain=None` 不得被包围盒替代；门几何不等于 `IfcOpeningElement`/`IfcRelVoidsElement`；owner 的“门一般默认关闭”被标为分析假设；boundary、opening、physical occupancy、walk blocking、visibility blocking 被拆开；domain 来源、source/derived 几何和 deferred 项也基本分开。因此没有发现需要立即停止整个设计方向的事实性 blocker。

但仍需 **REVISE** 后再作为冻结契约：当前草案把“建议的状态词汇”写得像已存在的统一 Neutral Scene 状态契约，且没有明确 `partial`、`conflict`、`unsupported`、`diagnostic_only` 的传播规则；它还把某些通道写成输入/推导混合物，尤其是 opening 的接受条件和 physical occupancy 的排除集合，容易被误读为现有 adapter 已支持的正式字段。现有 `NeutralSceneV2` 实际只有 `analysis_domain`、`SourceOpening`、几何、provenance 和 `UncertaintyRecord`；并没有 boundary/opening-channel/occupancy/walk/visibility 的专用顶层记录或统一 status enum。

## Blockers

1. **状态契约未与现有代码对齐（需修正文档后再冻结）。** `features/scene_contract.py` 没有草案中完整的 `available/missing/invalid/ambiguous/not_available` 状态字段，也没有 `partial/conflict/unsupported/diagnostic_only` 的统一传播结构。现有代码使用 `UncertaintyRecord.code`、`is_closed/is_manifold`、channel 内的 `unknown/blocked/clear/transmitting/ambiguous` 等局部表达。草案必须明确哪些是设计目标状态、哪些是当前字段、哪些仍 deferred，且不得把建议字段写成已支持能力。
2. **free-space 流程第 3–5 步需要更严格的资格门槛。** 当前 neutral view 会在没有 domain 时仍使用所有源几何/axis 形成诊断 view bounds；这符合“view bounds 不是 domain”，但草案应明确这是仅 diagnostic 的输入盘点，不能产出 free-space、components、connectivity 或 path。当前 `features/neutral_scene_views.py` 的 `physical_occupancy` 与 channel blockers 是描述层投影，不是已经实现的 effective obstacle/free-space 算法。文档需把“设计契约”和“当前可执行消费者”分开。

## Important findings

- `AnalysisDomain` 本身只保存 `id/geometry_refs/source_id/selection_method/provenance/uncertainties`；它不携带显式 status、单位或 analysis plane。单位和 plane 在 `AnalysisContext`，因此草案应明确这是跨记录约束，而不是 domain 字段已具备这些信息。
- `_native_analysis_domain` 只接受显式 `analysis_domain_source_id`，且选择 `IfcSpatialElement`；指定但无网格时返回带 `missing_geometry` 的 domain，未指定时返回 `None`。草案对此描述基本正确。
- `_native_opening_records` 根据 `IfcOpeningElement.VoidsElements.RelatingBuildingElement` 生成 `SourceOpening`；它保留 opening geometry 缺失 uncertainty，但没有把 opening 自动扣除 host，也没有生成 walk/visual permeability。草案应在 opening 行和第 3 步显式写出“当前 adapter 只提取事实，不执行 subtraction”。
- `SourceOpening.host_refs` 可以为空（代码允许），所以“opening 来源 id 与 host refs 必须同时存在”是未来输入资格规则，不是当前 `SourceOpening` 构造器的硬约束。应标为 proposed validation/deferred，而不是现有事实。
- `neutral_scene_views._domain_points` 只以 `analysis_domain.geometry_refs` 找点；空 refs 会使 domain 不可用于 view frame。建议文档区分“domain record 存在”与“domain geometry usable”。
- 现有 `boundary_evidence` 的 walking channel 在没有 body profiles 时不会生成有效 walking observations；visual channel 还区分 geometry status 与 optical status。草案的通道独立性正确，但应保留现有 `unknown/clear/transmitting` 词汇映射或明确未来归一化尚未裁决。
- `physical_occupancy` 排除 domain support geometry，但当前 view 也会保留 source records、surface interfaces 和 legacy `physical_blockers`；草案应避免让读者以为只要 source role 是 wall/furniture 就已经进入统一 occupancy contract。
- `adapters/ifc_bonsai.py` 有 `unsupported_grid_axis_curve`、invalid placement、missing geometry、unusable authored affordance 等 uncertainty；草案只列几何状态，没有把 adapter unsupported/conflict diagnostics 接入传播规则。
- `verification-before-completion` 在本项目和已检查技能路径中未找到可读 `SKILL.md`，因此未运行也未声称使用。`scientific-critical-thinking`、`experimental-design`、`scientific-visualization` 和适用的 `speckit-assess` 文件在本环境也没有找到可读取路径；本复核没有声称使用它们。审查方法采用了同类原则，但不能把它写成技能执行证据。

## Minor findings

- “首选 factual 来源”可保留，但应改成“候选优先级仍待 owner 裁决”，避免把 IfcSpace 解释成唯一首选。
- `opening_relation=missing`、`door_state=unknown`、`blocked/permeable` 等示例最好标为 proposed vocabulary；当前代码不存在同名统一字段。
- probe 计划已经覆盖正向 fixture、live inventory、负 fixture、opening-host、无 domain、manifest 和停止条件；可增加 `conflict` 与 `unsupported` 的专门 fixture，但这属于增强项，不是当前 blocker。
- 文档保留了 owner 原话，也清楚区分了事实、解释和假设；建议在“Owner 原话与解释”标题下再加一行“下列解释不是 IFC 观测”。

## 按 1–14 项逐条结论

1. **基本通过，需补状态边界。** 五类内容分表清楚；但 adapter uncertainty 与设计状态没有完全接上。
2. **通过。** `NeutralSceneV2.analysis_domain` 可为 `None`；架构记忆要求缺失 domain 时负空间/拓扑保持 unavailable。需补充“diagnostic view bounds 仍可存在，但不是 domain”。
3. **通过但需澄清。** IfcSpace、显式 domain、OM proxy/spatial zone、多空间 union、未来推导和 bbox 已分开；每行也有前提/provenance/失败/验证。需把 host/geometry validation 的“未来规则”标出。
4. **通过。** 明确禁止 bbox 作为 AnalysisDomain。
5. **通过。** 明确门几何不能替代 opening relation；live IFC 的 6 Door/0 Opening 事实表达正确。
6. **设计上通过，代码对齐需修订。** 五个通道已独立叙述；但当前 Neutral Scene 没有对应专用 records/status，不能把草案词汇写成已实现 API。
7. **通过。** “门一般默认关闭”被标为 owner analysis assumption，不是 IFC 状态；没有封闭所有 boundary opening。
8. **通过。** boundary scope、自动 domain、opening policy、阈值、backend、role/model/API 均 deferred。可再标记 `selection_method=derived_*` 只是候选命名，不是已冻结枚举。
9. **基本通过。** context 已有单位、world coordinate metadata、analysis plane、tolerances；对象/mesh/opening 有 refs/provenance/source identity。需说明 domain/status/plane 是跨记录校验，而不是每个 domain/opening record 自带。
10. **不充分，需修订。** missing/invalid/ambiguous/not_available 已提及，但 partial、conflict、unsupported、diagnostic_only 没有传播表；代码已有对应 uncertainty/rejection 语义，不能遗漏。
11. **基本通过，需拆开当前实现与目标设计。** source geometry、effective blockers、opening subtraction、channel blockers、free geometry、connectivity 的概念顺序正确；但当前代码只提供 projection/evidence，不提供完整 free-space backend。应写明第 3–5 步是 future derived evidence。
12. **通过，允许小修。** positive fixture、live inventory、missing/invalid、opening-host、domain 缺失、Blender/IFC 可视化、manifest/provenance、停止条件均在计划中；增加 conflict/unsupported fixture 有助于状态审计。
13. **通过。** 没有冻结 backend、resolution、route width、role classifier、Bayesian/ML 或 public API。
14. **通过。** 原话完整保留；当前事实、解释、假设和 deferred 项基本可辨识。建议再明确 owner 原话不是 IFC 证据。

## 必须修改的章节和字段

1. 在“输入与状态契约”后增加一张状态传播表，至少覆盖：
   - `available`：几何和关系可用且通过当前资格检查；
   - `partial`：部分成员/通道可用，只能进入 diagnostic/partial evidence；
   - `missing`：预期输入不存在；
   - `invalid`：输入存在但不合法，不能改写成 missing；
   - `ambiguous`：多个候选或冲突未裁决；
   - `conflict`：来源/属性/关系互相矛盾；
   - `unsupported`：adapter/backend 不支持该 IFC 表达；
   - `not_available`：前置条件不足或明确没有资格结果；
   - `diagnostic_only`：可显示/审计但不得进入正式 derived evidence。
2. 在 `SourceOpening` 说明处区分：当前 adapter 输出允许空 `host_refs`；“host refs 必须存在”是 proposed acceptance rule，不是现有 schema 事实。
3. 在 domain 表和 free-space 五步中增加 `domain_record_present` 与 `domain_geometry_usable` 的区别，并说明 view-frame bbox 只能是 `diagnostic_only`。
4. 将 opening subtraction 明确标为 future derived operation；当前 adapter 只输出 opening/host/geometry provenance。
5. 将 `blocked/permeable/clear/transmitting/unknown` 标记为 channel-local vocabulary 或 proposed normalization，避免误读成现有统一 enum。
6. 在技能章节改写为本次复核实际情况：指定技能路径未发现，因此未运行、未声称使用；不能沿用起草文档“已实际使用”的表述作为本复核证据。

## 可以暂时接受的字段

- `NeutralSceneV2.analysis_domain: AnalysisDomain | None` 的缺失表达。
- `AnalysisContext` 中 source/analysis units、world coordinate metadata、analysis plane、geometry/topology tolerances、capability flags。
- `SourceObject`、`MeshGeometry3D`、`SourceOpening` 的 stable ids、geometry refs、source refs、provenance、uncertainty 结构。
- source geometry 与 derived geometry 分列。
- boundary/opening/physical occupancy/walk/visibility 的概念分离。
- owner assumption 与 IFC observed fact 分离。
- 场景 bbox 仅作 diagnostic view bounds。

## 尚不能冻结的字段

- boundary scope 与 boundary record 的正式 schema。
- opening acceptance/host validation 和 opening-to-blocker subtraction 规则。
- `available/partial/...` 的正式 enum、聚合优先级和缺失传播表（需先补设计）。
- door-state scenario 字段及默认关闭策略的正式表示。
- walk body profiles、visual height bands、route width、sampling/resolution。
- free-space polygon/grid backend、连通性和路径 evidence schema。
- corridor/activity role、Bayesian/ML model、public API。

## 是否允许进入下一阶段设计实验

**允许进入有界设计实验，但不允许进入 production implementation。** 实验必须继续保持只读、source-vs-derived 分离、无合格 domain 时 `not_available`、不把 door geometry 当 opening relation，并新增至少一个 conflict/unsupported 或 partial 传播观测。实验结果不得反过来冻结尚未裁决的 backend、resolution、threshold 或公共 API。

## 实际读取的文件、技能和命令

实际读取：

- `AGENTS.md`
- `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- `docs/project/space-field-ifc-neutral-scene-input-contract.md`
- `docs/project/d6-space-field-closed-open-minimal-repair-handoff.md`
- `docs/project/evidence/d6-space-field-closed-open-independent-review.md`
- `docs/project/evidence/d6-live-blender-input-inspection-2026-09-29.md`
- `features/scene_contract.py`
- `features/scene_loader.py`
- `features/scene_inference.py`
- `features/boundary_evidence.py`
- `features/neutral_scene_views.py`
- `adapters/ifc_bonsai.py`
- `adapters/blender_geometry.py`
- `adapters/blender_preview.py`
- `test/fixtures/ifc4_description_fixture.py`

实际使用的命令包括：

- `Get-Content -Raw <path>`：读取指定文档和代码；
- `rg --files ...`：查找技能与相关文件；
- `rg -n <pattern> ...`：核对类、函数、状态和 IFC relation；
- PowerShell 字符串切片：读取 `AnalysisDomain`、`SourceObject`、`MeshGeometry3D`、`SourceOpening`、`NeutralSceneV2` 与 domain/channel 消费逻辑；
- `Test-Path`：确认复核对象和输入文件存在。

技能情况：本复核实际搜索了项目、全局和插件路径，但没有找到可读取的 `scientific-critical-thinking`、`experimental-design`、`scientific-visualization`、`speckit-assess-*` 或 `verification-before-completion` `SKILL.md`，因此没有声称运行这些技能。复核结论来自实际代码/文档读取和上述命令。

## 未执行的实验与证据限制

未执行完整 IFC probe、Blender probe、源 IFC 重导出、几何布尔、采样敏感性实验、可视化渲染、完整 pytest 或 production backend 对照。live IFC 数量只来自既有 2026-09-29 inspection 记录；本复核没有重新打开用户 Blender 或修改模型。故本 review 只判断契约文字与现有代码/记录的一致性，不证明真实 IFC 几何可提取、不证明 opening subtraction、自由空间连通性或通行能力。

STOP FOR SPACE FIELD INPUT CONTRACT INDEPENDENT REVIEW
