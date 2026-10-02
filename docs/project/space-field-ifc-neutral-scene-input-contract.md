# D6 空间场：IFC → Neutral Scene 输入契约（设计草案）

- 日期：2026-10-01
- 状态：设计阶段；不批准生产实现
- 范围：IFC 只读事实进入 Neutral Scene，再由 inference 形成可计算自由空间的前置契约
- 终止标记：STOP FOR SPACE FIELD INPUT CONTRACT REVIEW

## 已实际阅读与技能记录

本节记录本次设计工作的实际读取与使用；它不把未执行的实验写成已执行结果。

已读：`AGENTS.md`、`docs/indoor_layout_evaluation_matrix_architecture_memory.md`、`docs/project/d6-space-field-closed-open-minimal-repair-handoff.md`、`docs/project/d6-space-field-geometry-ifc-design-handoff.md`、`docs/project/d6-multilayer-space-field-block-graph-design.md`、`docs/project/evidence/d6-space-field-closed-open-independent-review.md`、`docs/project/evidence/d6-space-field-input-contract-independent-review.md`、`docs/project/evidence/d6-space-field-input-contract-owner-decision.md`、`docs/project/evidence/d6-space-field-ifc-input-contract-experiment-repair-v1-independent-review.md`、`docs/project/evidence/d6-live-blender-input-inspection-2026-09-29.md`、`features/scene_contract.py`、`features/scene_loader.py`、`features/scene_inference.py`、`features/boundary_evidence.py`、`features/neutral_scene_views.py`、`adapters/ifc_bonsai.py`、`adapters/blender_geometry.py`、`adapters/blender_preview.py`、`test/fixtures/ifc4_description_fixture.py`、`scripts/design/space_field/run_ifc_input_contract_experiment.py`，以及 `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` 的既有只读盘点证据。

实际读取并用于本草案：

- `experimental-design`（`.agents/skills/experimental-design/SKILL.md`）：把 fixture、坐标/单位、适配器能力和失败状态作为设计因素；同一源文件的分辨率/原点变体是敏感性观测，不是独立样本。
- `scientific-critical-thinking`（`.agents/skills/scientific-critical-thinking/SKILL.md`）：分离观察事实、推导量、假设和未验证主张，并按证据强度设置停止条件。
- `speckit-assess-intake`、`speckit-assess-define`、`speckit-assess-research`、`speckit-assess-shape`、`speckit-assess-decide`（`.agents/skills/speckit-assess-*/SKILL.md`）：只借用 intake → 问题定义 → 证据/缺口 → 方案比较 → 需要澄清的门槛。仓库没有适合本任务的 `.specify/assessments/<slug>/`，没有创建 assess 工件，也没有声称完成 spec-kit 评估流程；这些步骤适用于评估一个想法，不适合替代本次输入契约设计审查。
- `verification-before-completion`（`C:/Users/tianf/.codex/plugins/cache/openai-curated-remote/superpowers/6.4.2/skills/verification-before-completion/SKILL.md`）：用于要求完成前重新读取文档、检查允许范围和运行 `git diff --check`；没有把文档存在误报成实验或测试通过。
- `stop-that-shit`（`C:/Users/tianf/.codex/plugins/cache/stop-that-shit/stop-that-shit/0.2.2/skills/stop-that-shit/SKILL.md`）：本任务采用其 review/只读边界；本次只改本设计文档。

## 现有代码如何使用这些事实

当前调用链不是生产空间场实现：`adapters.ifc_bonsai.load_ifc_neutral_scene(path, analysis_domain_source_id=...)` 打开原生 IFC，构造 `NeutralSceneV2`；`_native_analysis_domain` 只接受调用方明确选择的 IFC spatial element，未选择时返回 `None`，选择但无可提取网格时保留 domain 记录和 `missing_geometry` uncertainty。`_native_opening_records` 遍历 `IfcOpeningElement.VoidsElements`，把 opening、host 和 geometry refs 写入 `SourceOpening`；它不做 host subtraction，也不生成通行或视觉结论。

`features.neutral_scene_views.analysis_scene_view` 将已有 mesh 投影到 `AnalysisContext.analysis_plane`，并分别返回 `physical_occupancy`、`walk_blockers`、`visibility_blockers`、`entries` 与 channel evidence。没有可用 domain 时，它仍可用源几何计算诊断 view bounds，但 `_analysis_view.domain_available` 为 false、`view_bounds_basis` 标为 `scene_geometry_fallback_not_analysis_domain`；这条路径不能产生自由空间、组件、连通性或路径。`features.scene_inference.boundary_semantics` 消费这些 neutral/interface facts，当前输出是描述性通道记录，不是统一状态 enum。

因此，本契约的“输入事实”可用于现有只读 view/evidence 消费；“effective blocker → free geometry → topology”是 future derived evidence，不能被现有 adapter 输出或诊断包围盒冒充。

## 当前代码能力 / 提议中的契约 / 尚未决定

| 层次 | 当前代码能力 | 提议中的契约 | 尚未决定 |
|---|---|---|---|
| Neutral Scene 记录 | `NeutralSceneV2` 提供 `AnalysisContext`、可空 `analysis_domain`、source objects、meshes、`SourceOpening`、materials/surfaces、provenance 与 `UncertaintyRecord`。 | 以这些记录承载 IFC 事实，并通过跨记录校验表达 domain、单位、plane 和几何资格。 | 是否新增统一 boundary、opening-channel、occupancy、walk、visibility records。 |
| 状态 | 现有代码使用局部状态（例如 `missing_geometry` uncertainty、`is_closed`/`is_manifold`、channel 内 `unknown`/`blocked`/`clear`/`transmitting`/`ambiguous`）。 | 设计候选状态见下文；任何归一化只作为 future evidence contract。 | 全局 enum、优先级、聚合和序列化字段。 |
| 推导 | 当前 view/inference 可做 plan projection、描述性 channel evidence 和诊断 view bounds。 | future derived evidence 才能构造 effective blockers、free geometry 与 connectivity。 | backend、resolution、route width 和正式 topology schema。 |

草案中的状态和通道名是设计候选，不是现有统一 Neutral Scene API。

## 当前代码和真实样本能提供的事实

| 类别 | 当前可确认内容 | 证据 | 结论边界 |
|---|---|---|---|
| IFC 原生事实 | IFC4 schema、项目长度单位、GlobalId/STEP 身份、空间容器/层级、产品类别、placement、Body/Analysis representation（若存在）、IfcRelVoidsElement 的 opening-host 关系、IfcGroup/Grid/材料/表面/显式 affordance 关系 | `adapters/ifc_bonsai.py` 的原生遍历；`test/fixtures/ifc4_description_fixture.py` 明确建有 IfcSpace、wall、IfcOpeningElement、IfcRelVoidsElement | 原生事实不等于可计算的域、通行或可见性结论 |
| 已输出到 Neutral Scene | `AnalysisContext`（单位、世界坐标、analysis plane、tolerances、capabilities）、`SourceObject`、`MeshGeometry3D`、`SourceOpening(host_refs, geometry_refs, opening_kind)`、materials、surfaces、groups/grids/affordances、uncertainties；`analysis_domain` 可为空 | `features/scene_contract.py`、`adapters/ifc_bonsai.py` | 目前 opening 是来源事实；不自动变成 boundary opening 或 permeability |
| 真实 live IFC 观察 | IFC4；单位 MILLI METRE；37 个 furniture_group、95 个 IfcFurniture；11 IfcWall；6 IfcDoor；0 IfcOpeningElement、0 IfcRelVoidsElement、0 IfcRelFillsElement、0 IfcSpace；成员同时声明 Analysis/Body 表示 | `docs/project/evidence/d6-live-blender-input-inspection-2026-09-29.md`，读取自实际 Bonsai `IfcStore.file` | 这是该样本的盘点，不是所有 IFC 的排除证明；门几何不是 opening 关系 |
| 可推导量 | 3D 网格到明确 analysis plane 的 plan projection、物理 occupancy 候选、按高度带的 walk/visibility blocker 观测 | `features/neutral_scene_views.py`、`features/boundary_evidence.py` | opening subtraction、free-space geometry、连通分量、路径/区域候选是未来推导，不是当前 adapter 输出 |
| 缺失量 | live IFC 没有合格 explicit domain；没有 opening relations；没有验证 door state；没有 walk profile/visual bands；未证明所有 mesh 可提取、闭合或适合平面布尔；没有 production route width/resolution/role classifier | live inspection、adapter uncertainty paths、architecture memory | 缺失传播为 `not_available`/`unknown`，不能用 0、空图或场景 bbox 代替 |
| 设计假设 | “门一般默认关闭”只作为 owner-directed analysis assumption；closed/open contrast 是合成几何实验；boundary 范围尚未冻结 | handoff 与 independent review | 不得据此关闭所有 boundary opening，也不得声称从 IFC 观察到门状态 |

## Analysis domain 来源比较

| 候选来源 | 已核实事实 / 前提 | 证据与 provenance | 风险 | 失败状态与验证方法 | 待裁决 |
|---|---|---|---|---|---|
| 显式 IFC spatial element（如 IfcSpace） | adapter 只接受调用方提供的 spatial source id；fixture 有 `IfcSpace`，live 样本没有 | `_native_analysis_domain`；`selection_method=explicit_ifc_source_id`、source id、schema、geometry refs | 把 IfcSpace 当唯一来源；可提取网格不等于有效 domain | 未指定：`analysis_domain=None`；无网格：domain + `missing_geometry`；非法 id：输入错误。核对 class/GlobalId、网格、平面、拓扑、单位 | 候选之一；优先级待裁决 |
| 显式 Neutral Scene domain geometry | `AnalysisDomain` 可保存 geometry refs/source id/provenance，但单位与 plane 在 context | `scene_contract.AnalysisDomain`、adapter/version、refs | refs 存在但几何不可解析或 context 不一致 | refs 缺失/不一致：`not_available` + uncertainty；独立核对闭合性、坐标系、投影和范围 | 可用，保持可审计 |
| Authored IFC/OM analysis proxy 或 spatial zone | fixture 有 `IfcSpatialZone` affordance，语义 marker 不自动等于 domain | OM marker/property set、source id、authoring method | 普通 mesh/name 被误判为 domain；语义无边界 | marker 冲突、无几何、仅语义：`conflict`/`not_available`；核对 property provenance 和 geometry refs | 未来比较；不得静默升级 |
| 多个显式空间/区域 union | 需要明确集合、同 level/plane、union 规则和重叠解释 | selected ids、union rule、overlap diagnostics | 重叠或跨坐标系会制造双计数/错误外壳 | 空集合或未解释重叠：`not_available`；独立 union、面积、组件和边界审查 | 设计候选 |
| 将来自动推导（封闭墙/楼板/边界壳） | live 样本有墙/门身份，但 closure、标高、opening 语义和几何质量未被本任务验证 | `selection_method=derived_*`（候选命名）、算法版本、输入 refs、plane、tolerances | 把墙壳、门假设或 bbox 偷换成 domain；多壳/漏缝拓扑 | 不闭合、歧义、多壳、缺 opening/标高：`not_available` 或 `ambiguous`；source-vs-derived 图、扰动/敏感性、独立布尔复核 | 仅研究候选，不选后端/阈值 |
| 场景包围盒 / 文件范围 | 当前 view 为无 domain 场景提供 fallback bounds | 只能证明 transport extent；不是空间事实 | 会把任意模型范围伪装成 AnalysisDomain，制造假 free-space | 只允许 `diagnostic_only` view frame；明确拒绝进入 domain | 禁止作为 AnalysisDomain |

规则：区分三层资格：`domain_record_present`（是否有 `AnalysisDomain` 记录）、`domain_geometry_refs_available`（其 refs 是否解析到几何）、`domain_geometry_valid`（几何是否通过适用有效性检查）。只有三者满足，domain 才可支持正式 derived evidence。没有合格 domain 时，`analysis_domain=None` 或 domain 不可用；负空间、自由空间、拓扑图及其下游路径状态为 `not_available`。view-frame bounds 可以从场景几何生成用于诊断显示，但其状态必须是 `diagnostic_only`，不能创建 domain 或自由空间。样本没有 IfcSpace 只表示该来源缺失，不排除 authored zone、proxy、多个显式区域或未来推导来源。

## 输入与状态契约

所有记录必须带稳定身份、来源身份、几何 refs、provenance 和 uncertainty；单位、world coordinate system、analysis plane、geometry/topology tolerance 位于 `AnalysisContext`，是跨记录校验条件，不是每个 domain/opening/channel record 都自带的字段。以下是设计候选状态，不是已冻结 API：

| 状态 | 当前代码可对照的表达 | 设计传播规则 |
|---|---|---|
| `available` | 记录存在，geometry refs/关系通过当前资格检查 | 可进入相应 future derived evidence；不能单凭状态跳过 domain/plane 校验。 |
| `partial` | 部分 source objects、mesh 或 channel query 有结果 | 保留成功与缺失成员；只能产生 partial/diagnostic evidence，完整自由空间/拓扑保持不可用。 |
| `missing` | `analysis_domain=None`、空 host relation、缺 profile，或 `UncertaintyRecord` 指向缺失输入 | 传播为依赖通道的 unavailable/unknown；不得改写为 `invalid` 或 `available`。 |
| `invalid` | 非有限/不合法几何、关系或数值；代码通常以校验异常或 uncertainty 表达 | 停止该记录进入正式 derived evidence；保留原始 identity 与诊断。 |
| `ambiguous` | 多个 domain/host/几何解释未裁决；当前没有统一字段 | 保留候选、provenance 和比较结果；下游不得静默选择。 |
| `conflict` | 来源、属性或关系互相矛盾；当前需用 uncertainty/diagnostic record 表达 | 不合并为一个事实；依赖该冲突的 derived evidence 为 `not_available` 或 `diagnostic_only`。 |
| `unsupported` | 例如 adapter 的 `unsupported_grid_axis_curve` uncertainty | 保留 source identity、failure details 和可显示事实；不伪造支持结果。 |
| `not_available` | 下游当前没有合格 domain/输入；不是现有统一 enum | 自由空间、components、connectivity、paths 和依赖其的 regions 均保持 `not_available`。 |
| `diagnostic_only` | `neutral_scene_views` 的 fallback view bounds、source inventory 或局部 channel evidence | 可显示和审计；不得进入正式自由空间、连通或路径结果。 |

这些状态的全局 enum、聚合优先级和序列化形状尚未决定。

| 通道 | 输入事实 | 几何/单位 | 语义与状态 |
|---|---|---|---|
| boundary | 明确 host/界面几何；可来自 wall/partition/域边界或 authored boundary hint；必须记录 scope | 3D source mesh + analysis-plane projection；长度/面积用 `analysis_length_unit` | 物理连续性证据，不等于 domain perimeter；`boundary_scope` 必填或 deferred |
| opening | IFC `IfcOpeningElement` + `IfcRelVoidsElement` host relation，或明确 authored opening geometry；来源 id 与 host refs 的关系资格需单独检查。当前 adapter 可以构造空 `host_refs` 的 `SourceOpening`；host ref 必需若被采用，是未来资格规则，不是当前 schema 约束 | opening geometry 在同一 world/analysis plane；保留 3D height | 是“几何/关系存在”的事实；当前 adapter 只提取 opening/host/geometry provenance，不执行 opening subtraction，也不推导通行或可见性。门几何、`IfcRelFillsElement` 或 owner assumption 分开记录 |
| physical occupancy | 设计目标是非 domain support geometry 的事实质量体；当前 view 以明确 geometry 为依据，并排除选中的 domain support refs，同时保留 source records 和 legacy boundary fields | 3D mesh 投影；不以 source role 单独决定是否有质量 | 物理占据通道；更细的 path/region/entry/opening 排除集合属于 future consumer 规则，不能说成当前统一 occupancy API |
| walk blocking | occupancy/boundary/opening 在 walking body height band 上的观察或推导；需要 walking profile、height band、tolerance | 2D projection tied to explicit plane + z interval；单位同 context | channel-local vocabulary：`blocked`、`clear`、`unknown`、`not_available`；没有 profile 或几何不可用时不升级为可通行；不是现有全局 enum |
| visibility blocking | 由几何、材料光学事实、visual height band 或射线/遮挡分析产生 | 平面/高度带明确；材料 transmittance 只作为 factual input，不是通行结论 | channel-local vocabulary：`blocked`、`clear`、`transmitting`、`unknown`、`not_available`；不能从 walk 状态复制；不是现有全局 enum |

五个通道必须有独立 record/status/provenance。禁止一个 `open`/`closed` 布尔值同时代表 boundary existence、opening relation、physical occupancy、walk blocking 和 visibility blocking。当前 `SourceOpening.host_refs` 可以为空；“host refs 必须存在”是未来 opening acceptance rule，不是现有 schema 约束。缺少 opening relation 时，设计状态可记为 `missing`；缺少 door state 时，设计状态可记为 `unknown` 或 owner assumption 单独标记；不要把二者互相填充。

## Owner 原话与解释

下列解释是设计解释和 owner-directed assumption，不是 IFC 观测。

> “门这个东西意义不大其实，一般而言，我们默认其关闭，后面对于boundary的开口，那才是真正的开与闭，所以从元的角度，你当前做的是有意义，只是要注意未来的使用场景”

> “门一般默认关闭”是分析假设，不是从 IFC 核实的门状态。它可以作为一个带 owner provenance 的 scenario input，影响门相关的分析分支；不能因此封掉所有 boundary 开口。`IfcOpeningElement` 与 host relation 仍按 IFC 事实单独提取。boundary 的确切范围（domain perimeter、internal divider 或其他 derived boundary）必须通过候选方案比较后裁决。

## 从输入到可计算自由空间

1. 校验单位、世界坐标、analysis plane 和几何 refs；无合格 domain 立即输出 `not_available`。
2. 在 plane 上投影 domain support、physical occupancy、boundary/opening 候选，保留 source ids 与 projection diagnostics。
3. **未来 derived evidence：** 按届时裁决的规则构造 effective blockers；当前 occupancy/channel projection 不等于已实现的 blocker 合成。物理占据、boundary continuity、opening subtraction、walk/visibility observations 必须分开。
4. **未来 derived evidence：** 对有效障碍做几何差集得到 free-space candidate；当前代码没有冻结或承诺 free-space backend、网格/多边形实现、面积/组件生产结果。
5. **未来 derived evidence：** 仅在 domain record、geometry refs、geometry validity 和所需 channel evidence 满足时建立连通/路径/region evidence；否则下游保持 `not_available` 或 `diagnostic_only`。

这里不预选后端、网格分辨率、走廊宽度阈值、空间角色分类器或 Bayesian/ML 模型。closed/open fixture 只证明 synthetic source geometry 的有限差异：closed area 20/components 2，open area 21/components 1；不证明生产采样、路由可用性或门状态。

## 最小真实 IFC 只读 probe 与可视化方案（不执行）

### Fixtures, assertions, visualization, and provenance

| fixture | 只读动作与断言 | 可视化 | provenance / stop condition |
|---|---|---|---|
| `live-rhino-10500-furniture-groups.ifc` | 读取 schema、units、counts、GlobalId/STEP identity；记录 0 `IfcSpace`、0 opening/void/fills、6 doors、11 walls、95 furniture；不调用 live mesh extraction | 输入盘点、source identities、`NOT AVAILABLE — NO QUALIFIED ANALYSIS DOMAIN`；不画 free-space | IFC path/hash、read method、timestamp、adapter version；若 schema/units/counts 无法核实则停止 |
| `ifc4_description_fixture.py` 正向 fixture | 生成 IFC4 fixture；无 domain 时 `analysis_domain=None`；显式 room id 才能成为 domain；核对 `IfcOpeningElement` + `IfcRelVoidsElement` host/geometry refs；单位与 plane 明确 | 源 product/mesh、room support、wall、opening 和 host relation 分层显示；标注 source facts only | fixture writer、stable ids、adapter call args；若 relation/geometry 只能靠命名或硬编码则停止 |
| 缺 domain / 缺 geometry / 断 opening relation | 只读 adapter payload；保留 `missing_geometry`、空 host refs 与 uncertainty；domain record 与 usable geometry 分开断言 | 输入盘点和 uncertainty；不显示 derived free-space | case id、source refs、uncertainty details；任一缺失被填成 0/empty graph 或 host 被猜测则停止 |
| `partial` / `conflict` / `unsupported` 状态 fixture | 观察现有 uncertainty/diagnostic 表达，验证候选传播表；不声称已有统一 enum | 以状态标签和来源身份显示；不进入正式场 | failure details、status vocabulary version；无法保留冲突双方或 unsupported 原因则停止 |
| closed/open synthetic fixture | 只复核既有 source oracle：closed 20/2、open 21/1；不把它当 IFC 门状态或通行实验 | 并排 domain/effective barrier/opening/source result；采样若显示必须与 source 分列 | synthetic units、fixture ids、算法/tolerance；若图或数值把门状态升级为事实则停止 |

未来若 domain 合格，右侧才可显示 derived free-space candidate；无合格 domain 时右侧固定显示 `NOT AVAILABLE — NO QUALIFIED ANALYSIS DOMAIN`，并只显示输入盘点。所有图层带 `source_id`、`geometry_ref`、`analysis_plane`、单位、算法版本、tolerance、status。Blender 预览只消费序列化 manifest，不定义 inference；只能使用规定的 portable Blender，运行失败必须记录为验证限制。本计划不执行。

### 停止条件

- schema/单位/坐标无法核实；
- domain 候选几何缺失、非有限、非共面或拓扑歧义；
- opening 无 host relation 或几何交集无法判定；
- 关键 source/derived 数值只能靠 bbox、命名或硬编码；
- 任何 probe 试图把门状态、采样连通性或视觉材料值升级为未验证语义。

本实验计划不执行；它只定义将来的有界验证。

## 字段裁决：可暂定 vs 必须 deferred

**可暂定**：Neutral Scene v2 已有的 units、analysis plane 结构、source/object/geometry/opening identity、provenance/uncertainty 结构、`analysis_domain=None` 的 unavailable 表达、source 与 derived 结果分列、walk/visibility 分通道。

**必须 deferred**：boundary 的确切范围；domain 自动推导算法；opening 接受规则及几何容差；door-state scenario 默认的字段形状；walking body profile 数值；visibility height bands 与光学解释；free-space backend、网格分辨率、走廊宽度阈值；空间角色分类器；Bayesian/ML 模型；任何公共 API 变更。

## 独立复核清单

- [ ] 只引用实际读取的文件和技能；实际使用的 `verification-before-completion` 有路径和验证动作记录。
- [ ] IFC 原生、adapter 输出、推导量、缺失量、设计假设分列。
- [ ] 门几何未被解释为 opening relation；无 IfcSpace 未被解释为排除其他 domain 来源。
- [ ] 场景 bbox 未被当作 AnalysisDomain；无合格 domain 保持 `not_available`。
- [ ] boundary、opening、physical occupancy、walk blocking、visibility blocking 各有独立事实/状态/provenance。
- [ ] owner 原话完整保留；“门一般默认关闭”标为假设，未封掉所有 boundary opening。
- [ ] 单位、analysis plane、几何表示、来源身份、有效性和缺失传播明确。
- [ ] closed/open fixture 仅作为有限几何证据，不扩展为生产阈值或路由结论。
- [ ] probe 计划包含 positive/negative fixtures、partial/conflict/unsupported 状态观察、断言、可视化、manifest、provenance、停止条件，且本轮未执行。
- [ ] 未修改 features、adapters、正式测试、公共 API、依赖、源 IFC 或用户 Blender 文件。

STOP FOR SPACE FIELD INPUT CONTRACT REVIEW

