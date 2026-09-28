# D6 Task 3d：家具组层面的场景自描述设计

> 2026-09-28 E8b/E10b 收口更新：当前裁决见 [总控证据收口](d6-group-level-design-decision.md)。本轮证据审查收口，整体设计仍为 REVISE；E10b 仅验已声明 SVG facts，contact/overlap 退回修订，完整双 adapter parity 与 inferred-group selector 未冻结。下文保留历史裁决，不据此自动进入实现。

- **状态：** design-only；A–G 裁决见第 13 节，设计比较仍待完成。STOP FOR DESIGN REVIEW。
- **当前裁决优先级：** 第 13 节依据用户本轮授权作出设计裁决；第 1–12 节保留为历史讨论，不再把已裁决事项重复列作 owner 待决。批准设计政策不等于批准算法实现或声称实验通过。
- **后续澄清：** 见 [独立设计审查交接](d6-inferred-group-design-review-handoff.md)。用户已明确 IFC 家具组候选入口、家具组之间的几何推断、外部 affordance 和 SVG 仅作 2D oracle；这些澄清优先于本文旧表述。算法和待决政策仍未批准。
- **日期：** 2026-09-28
- **范围：** canonical plan geometry → authored furniture group → representative geometry → group trend → neighboring-group relations
- **实现边界：** 本任务只修订设计、probe 证据和迁移裁决；不修改 `features/`、adapter、正式测试、IFC 或 SVG 生产路径。
- **probe 输入：** `scripts/design/group_level/fixtures.json`
- **probe：** `scripts/design/group_level/run_group_level_probe.py`
- **probe 结果：** `docs/project/evidence/d6-group-level-design-probe.json`

本设计描述可计算的场景证据。它不声称人的秩序感、可用性、审美判断或真实场景准确率。

## 1. 产品边界和当前实现事实

首个产品单位是明确 authored 的家具组。`IfcGroup` 或等价 adapter relation 是事实输入；inferred group 使用独立 record，不能覆盖 authored membership。一个 object 可属于多个 authored groups；每个 group 独立计算并保留重复 membership provenance。

当前审计事实：

- `features/scene_inference.py` 的 group frame 从最终 plan geometry 计算 member frame consensus，并保留 deterministic strength、member support 和 coherence metadata。
- `features/column_grid.py::_frame_from_angles()` 使用四倍角、结果归一到 `[0°, 90°)`，所以 0° 与 90° 等价。
- design probe 的 `_member_consensus()` 使用 doubled-angle `2θ`、结果为 modulo-π 无向轴，所以 0° 与 180° 等价，90° 与 0° 不等价。
- probe 当前保留 additive multi-part support、面积加权 center、总 covariance、excluded reasons；不计算 polygon union 或 overlap area。
- `inter-region gap-path graph` 的节点是 activity-region candidates，不是 furniture groups；它包含自由空间、占用率、路径宽度和连通性语义。

### 本次修订审计

| 原设计内容 | 当前实现事实 | 修订后的设计 | 仍需 owner 决定 |
|---|---|---|---|
| trend 只写成一个 `member_frame_consensus` | production-compatible column-grid frame 使用四倍角；probe 使用 doubled-angle | 明确拆成 `group_frame` 与 `group_axis` 两个 estimand，禁止互称 | 首个 Bayesian trend 选 frame 还是 axis |
| representative 只写 additive support、center、covariance | probe 输出总 covariance，未拆 within/between；无 overlap area/union status | 冻结字段、公式、invalid/missing 状态和 union 边界 | overlap area 的多重重叠算法、union 进入哪个阶段 |
| strength、support、coherence、uncertainty 语义相近 | 当前值是确定性几何派生量，无 posterior | 分离四类字段；deterministic strength 永不解释为概率 | 后续 uncertainty 模型及校准方法 |
| neighbor 只给 normalized boundary-gap | gap-path graph 已在 region/path 层存在 | 增加 group-neighbor 与 inter-region graph 边界表，二者并存 | 是否把 group edge 纳入联合模型 |
| 迁移表只列宽泛组件 | 当前实现能力分散在 inference、column-grid、position grammar 和两个 adapter | 按 `migrate / wrap / rewrite / discard / reference_only` 逐项裁决 | 每项进入哪个后续 checkpoint |

## 2. Group unit 和 representative geometry

### 2.1 Authored group record

每个 group record 至少包含 `group_id`、`member_object_ids`、`membership_provenance`、`membership_kind` 和 `analysis_frame`。输入顺序、object id lexical order、adapter traversal order 都没有空间语义。缺失 authored relation 不得隐式把 object 变成 singleton group；上层必须显式选择 inferred candidate 或返回 `not_evaluated`。

### 2.2 冻结字段和语义

对每个 usable member `i`，令 `A_i` 为几何面积，`c_i` 为 member centroid，`C_i^within` 为 member 内部、以 `c_i` 为中心的面积加权 covariance；令 `A = Σ_i A_i`，`c = Σ_i A_i c_i / A`。

| 字段 | 语义和首阶段规则 |
|---|---|
| `support_area` | 几何面积。首阶段使用 additive support `Σ_i A_i`；重叠不会被静默扣除。它不是 member 数、directional support 或置信度。 |
| `center` | 面积加权 group center `Σ_i A_i c_i / support_area`。 |
| `within_member_covariance` | `Σ_i (A_i/A) C_i^within`；描述家具自身形状分布。 |
| `between_member_covariance` | `Σ_i (A_i/A)(c_i-c)(c_i-c)^T`；描述 member center 的组内排布。 |
| `covariance` | `within_member_covariance + between_member_covariance`；总 covariance 仍可作为兼容派生字段，但不能隐藏两个分量。 |
| `overlap_area` | usable member 几何交叠面积的独立观测字段。若尚未运行拓扑计算，值为 `null` 且 `overlap_area_status=not_computed`；不能用 `0` 代表未知。多重 pair overlap 是否去重由 owner 决定。 |
| `union_area_status` | 首阶段为 `deferred`，因为 polygon union 的拓扑、孔洞、self-intersection 和多重重叠语义尚未冻结。 |
| `excluded_member_reasons` | 每个未纳入派生计算的 member id 到明确 reason 的映射，如 `missing_geometry`、`invalid_geometry`、`degenerate_geometry`、`non_finite`；不能把 invalid 改写成 missing。 |
| `geometry_completeness` | `complete`、`partial`、`not_applicable` 或 `not_computable`。它描述 member geometry 输入完整度，不是 posterior uncertainty。 |

首阶段代表是 multi-part additive support；polygon union 暂缓。`overlap_area` 不改变 additive `support_area`。当 `normalized_boundary_gap` 使用 `sqrt(support_area_i + support_area_j)` 归一化时，overlap 只作为 relation observation 和 provenance 保留，不从 denominator 中扣除；若未来改用 union denominator，必须成为新 estimand 并重新比较。

### 2.3 状态规则

| member 状态 | group geometry status | trend status | 规则 |
|---|---|---|---|
| 全部 usable | `computed` | `complete` 或 `undefined` | `undefined` 只表示没有可解释方向，不表示 geometry missing。 |
| 至少一个 usable，其他 `not_available` | `computed` | `partial` | 缺失 member 写入 `excluded_member_reasons`，不补零。 |
| 任一 member `invalid`，即使另一个 valid | `invalid` | `not_computable` | valid support 可保留为诊断，但 group result 不得伪装成 computed；invalid 不得静默排除或改成 missing。 |
| 全部缺失 | `not_available` | `not_applicable` | 不返回伪造 center、area 或 angle。 |
| membership 非 authored relation | `not_evaluated` | `not_applicable` | 不把 inferred membership 当 authored fact。 |

## 3. Trend estimands：`group_frame` 与 `group_axis`

二者都可由 member terminal geometry 计算，但不是同一个 estimand：

| estimand | 数学语义 | 0°/90° | 适用范围 |
|---|---|---|---|
| `group_frame` | 两轴正交 frame；用 `4θ` 共识并归一到 modulo-90° | 等价 | 兼容当前 `column_grid._frame_from_angles()` 和既有正交 frame 语义 |
| `group_axis` | 单一无向主轴；用 `2θ` 共识并归一到 modulo-180° | 不等价 | 描述 horizontal 与 vertical 是不同方向的 group 主轴 |

四倍角把 `θ`、`θ+90°` 映射到相同向量；doubled-angle 把 `θ`、`θ+180°` 映射到相同向量，却把 `θ+90°` 映射到相反向量。因此 probe 的 doubled-angle 结果不能直接宣称复现当前 column-grid frame。

推荐：`group_frame` 作为兼容当前 trend 的 deterministic baseline；`group_axis` 若保留，作为独立描述量，单独输出 angle/status/strength/coherence。不得把二者当成同一个 trend，也不得在字段名中用 `axis` 掩盖 frame 语义。Bayesian 模型必须在模型名称、结果 schema 和比较指标中明确估计 `group_axis` 或 `group_frame`。

首阶段 deterministic member evidence：member weight 可用 `area × anisotropy`，其中 `anisotropy=(λ_primary-λ_secondary)/(λ_primary+λ_secondary)`。方向不明确的 square/circle member 不贡献 directional support。最终 extent 必须在最终 frame/axis angle 下重算。

## 4. Evidence 字段：严格分层

| 字段 | 严格语义 | 当前/首阶段状态 |
|---|---|---|
| `support_area` | 几何面积，单位为 analysis unit² | deterministic geometry |
| `directional_member_support` | 有方向 member 数量，或经声明的 reliability weight 总和 | count/weight；不是面积 |
| `coherence` | directional member 对同一 frame/axis 的一致性，例如 resultant length `[0,1]` | deterministic concentration |
| `strength` | 由声明 estimator 从 geometry、support 和 coherence 生成的确定性证据强度 | evidence-only；不是 probability |
| `uncertainty` | 未来模型的区间、credible interval、posterior 或 geometry uncertainty record | 当前 absent/unknown，不得填零 |

`strength=0.8` 不能解释成“方向正确概率 80%”。`coherence` 高也不代表几何输入正确；`directional_member_support` 高也不代表 member 独立。member missingness、invalidity、dependence 和 geometry uncertainty 必须在 provenance/status 中保留。

## 5. Neighbor relation 与 graph 边界

`normalized_boundary_gap` 的 relation 只由 group representative/member geometry 计算：`gap` 和 `overlap` 是 geometry observations；`edge` 是几何关系，不是 authored membership。首阶段仍用 synthetic `τ=0.33` 做候选比较，不能当 human threshold。

| graph | 节点 | 描述 | 不替代 |
|---|---|---|---|
| `normalized_boundary_gap` | furniture groups | group 几何邻近、member boundary gap、overlap、normalized gap 和 pair provenance | 不描述自由空间路径或 activity-region 连通性 |
| `inter-region gap-path graph` | activity-region candidates | 自由空间、占用率、路径宽度、入口连通性和 disconnected components | 不定义 group membership，也不替代 group-neighbor edge |

二者并存。一个 group edge 不能自动变成 route path；一个 gap-path edge 不能反写 authored group。internal overlap network 仍属于 group 内部 relation evidence，须与 inter-region graph 分开。

## 6. Bayesian estimand boundary

本任务不实现 Bayesian。候选必须先声明自己估计的量：

```text
P(group_axis | member geometry, missingness, reliability)
```

或兼容 frame 的模型：

```text
P(group_frame | member geometry, missingness, reliability)
```

neighbor 模型必须明确为：

```text
P(group_edge | group geometry, gap, overlap, uncertainty)
```

这里 `gap`、`overlap` 是由 geometry 计算的观测；`group_edge` 是几何关系，不是 authored membership；posterior 不是人的感知概率。missingness、geometry uncertainty、member dependence 不能省略，也不能用默认独立 member 假设隐藏。

若模型估计 latent partition、continuous field 或 authored membership posterior，结果必须使用独立 record。只有在声明相同 estimand、联合 likelihood、prior、missingness model、uncertainty model 和可识别性后，才可讨论 fusion。当前不选择 prior、likelihood、concentration 或 calibration 数据。

## 7. Probe 与 production 的硬边界

probe 只能用于：

- 候选比较和 synthetic computational truth；
- 数值 oracle、退化/缩放/旋转/缺失/tessellation 检查；
- 可视化诊断和 provenance 检查。

probe 不得被解释为 production API、默认心理阈值、Bayesian prior、真实场景准确率或人类感知效度证据。probe 不导入 IFC、SVG、legacy evaluator 或 production trend code；通过 probe 不等于通过 IFC/SVG parity acceptance gate。

## 8. 后续设计 fixtures

以下 fixtures 必须在实现设计前加入 probe 计划；当前结果文件只记录已运行 cases，未运行项标为 `planned`：

- `0°`、`90°`、`180°`、`270°`，分别检查 frame equivalence 和 axis equivalence；
- 同一 geometry 的 axis/frame 差异；
- 一个 valid、一个 missing、一个 invalid member，检查 `computed/partial` 与 `invalid/not_computable`；
- overlapping members，记录 `overlap_area` status；
- additive area 与 union area 对照；
- unequal-size groups 的 normalized gap；
- 多重 authored membership，不合并重复 group evidence；
- disconnected neighbor components；
- IFC/SVG 等价 canonical facts，作为 parity acceptance fixture。

## 9. 迁移与停止门

逐项迁移裁决见 `docs/project/d6-migration-ledger.md`。其中 IFC/SVG parity 是实现阶段验收门：同一 canonical facts 必须产生相同 geometry、status、trend estimand、gap/overlap observations 和 provenance。现有 production regression 只能作为 reference evidence，不能替代该门。

当前停止条件：owner 未决定首个 Bayesian trend estimand、overlap/union area 语义、invalid-member group policy 的下游消费方式和 parity fixture 前，不进入 Task 3c、implementation design、descriptor API 或生产算法实现。

## 10. Grill-me reverse review

| 质询 | 当前答案 |
|---|---|
| 0° 与 90° 是否被错误地当成同一量？ | 只有 `group_frame` 等价；`group_axis` 不等价；二者分开命名和比较。 |
| invalid member 是否被静默当 missing？ | 不会；group status 为 `invalid`，reason 保留。 |
| overlap 是否偷偷改变 normalized gap denominator？ | 不会；首阶段 additive support denominator 不扣 overlap；union 改变需新门。 |
| strength 是否代表正确概率？ | 不代表；它是 deterministic evidence scalar。 |
| edge 是否代表 authored membership？ | 不代表；edge 只描述 geometry relation。 |
| kNN 是否强行连接 disconnected components？ | 会，所以只作 diagnostic，不作 neighbor baseline。 |
| probe 是否证明人类感知效度？ | 不证明；只证明 synthetic computational checks。 |

## 11. Owner decisions

请 owner 明确：

1. 首个 trend 是否冻结为 `group_frame`，以及 `group_axis` 是否作为独立描述量保留；
2. `overlap_area` 是否先只作 pairwise diagnostic，何时定义 union area；
3. invalid-member group 的下游是否允许消费 valid diagnostic support；
4. Bayesian 首个模型估计 `P(group_axis | …)` 还是 `P(group_frame | …)`；
5. IFC/SVG parity fixtures、tolerances 和 acceptance owner；
6. 后续 fixtures 是否纳入 probe schema v2。

**STOP FOR DESIGN REVIEW（原设计版本）**

## 12. 独立设计审核与修订（2026-09-28）

本节是一次独立的反向审核记录。它不把本文件前文的“推荐”“首阶段”或
probe 的 selected 字段升级为 owner 已批准的规格，也不授权 Task 3c、implementation
design、descriptor API 或生产算法实现。

### 12.1 当前实现事实

- `adapters/ifc_bonsai.py::_native_group_records()` 会读取所有 `IfcGroup`，只有
  `ObjectType == "furniture_group"` 才写入 `group_role="furniture_group"`；普通组仍被
  保留为 `ifc_group` provenance。
- `features/neutral_scene_views.py::_group_membership()` 仍有旧兼容行为：当普通组的
  全部成员恰好是家具时也会接受它，而且 `setdefault` 只保留每个对象的首个组。这与
  “只有明确 furniture_group、保留多重 membership”的边界冲突。
- `features/scene_inference.py::furniture_groups()` 按 semantic key 或旧 region/group
  fallback 建组；当前没有“家具组节点之间的独立 pairwise relation graph → inferred
  group candidate”步骤。`spatial_networks()` 的 `inter_region` 图节点是
  `activity_region_candidate`，不是家具组。
- 当前 `furniture_groups()` 把 physical footprint 与本组 member 的 affordance extent
  合成一个 union envelope；它不是本次 inferred-group 的物理支撑代表，也没有外部
  affordance 与 physical support 的独立 relation channel。
- `scene_inference._member_frame_consensus()` 和 `column_grid._frame_from_angles()`
  都使用 `4θ`，把 0° 与 90° 视为同一正交 frame；设计 probe 的
  `_member_consensus()` 使用 `2θ`，得到的是 modulo-180° 的单一无向 axis。二者不能
  互称同一个 trend。
- probe 目前只运行 additive support、总 covariance、doubled-angle consensus、
  kNN/raw gap/normalized gap 和少量 missing/tessellation cases；planned 的 invalid、
  overlap/union、multi-membership、3D/阻隔和 IFC/SVG parity 尚未运行。

### 12.2 原设计、实现事实、修订设计、owner 问题

| 原设计内容 | 当前实现事实 | 修订后的设计 | 仍需 owner 决定 |
|---|---|---|---|
| `IfcGroup` 或等价 relation 可作为首个 group 单位 | IFC adapter 标记了 `furniture_group`，但 neutral view 仍接受“全家具的普通组” | IFC 候选节点严格限定为 `ObjectType=furniture_group`；普通 `IfcGroup` 只保留 provenance；缺少 authored relation 不生成 singleton 家具节点 | SVG/其他来源如何在 canonical facts 中声明同一事实，以及谁负责映射验收 |
| 现有 semantic group 可代表 inferred group | 当前按 key/fallback 建组，尚无家具组之间的推断 | 先固定 authored furniture-group nodes，再计算 pairwise relation graph；inferred group 使用独立 candidate record，不改写 authored membership | 新 candidate 与旧 activity-group/activity-region 的命名和下游连接 |
| 一个对象属于一个 group | `setdefault` 丢掉重复 membership | canonical input 保留全部 authored memberships；共享 member 只作为 provenance 和依赖标记，不重复计数 | 共享 member 的几何 relation 是否可进入 membership 决策，还是仅诊断 |
| group extent 可用单一 affordance union envelope | 当前 physical 与外部/旧 affordance extent 在 group rect 中混合 | `physical_support`、`external_affordance`、各自的 2D/3D relation evidence 分列；无外部 affordance 时为 unavailable，不由 furniture kind 生成 | affordance 是否允许进入 inferred membership、标签/purpose、绑定方式和高度适用范围 |
| 一条 normalized-gap edge 可直接形成 group | probe 只比较 edge 候选；生产没有该步骤 | 必须先生成带 provenance/status 的 pairwise relation graph，再比较 connected-components 与 complete-link/max-intragroup-gap candidate；graph edge 不等于 authored membership | 首个 candidate 生成器、阈值/尺度函数和是否允许多尺度结果 |
| connected-components 是默认 inferred group | A-B、B-C 近但 A-C 远时会链式合并 | connected-components 只作为 chaining baseline/diagnostic；complete-link 或最大组内距离约束作为独立候选；不在本节冻结最终算法 | 目标是几何聚集还是功能/活动组合，以及如何选择/比较候选 |
| inferred group 是 hard partition | 当前没有 partition contract | candidate schema 必须允许 hard partition、overlapping candidate、未分组节点和 ambiguous candidate；候选含成员、边证据、算法、参数和 status | 首个生产输出是否只能 hard partition，还是保留重叠/歧义候选 |
| missing member 可排除后继续计算 | probe 只覆盖一个 missing member，未覆盖混合 invalid | missing/not_available：代表可为 `computed/partial`，relation 标记 partial；invalid：group 为 `invalid/not_computable`，valid support 只保留 diagnostic，不进入 computed 下游；invalid 不改写成 missing | partial node 能否进入 inferred candidate 图；invalid diagnostic 谁可以消费 |
| overlap 是 denominator 的隐含修正 | probe 未算 overlap area/union | 首阶段 additive `support_area`；`overlap_area` 是独立 pairwise observation；polygon union 延后；overlap 不从 additive denominator 静默扣除；任何 union denominator 都是新 estimand | pairwise overlap 是否去重、多重重叠语义和 union 进入哪个阶段 |
| trend/coherence 可帮助挑 group member | 当前 trend 可从 member geometry 计算，但无 inferred membership | 首轮 membership 禁用 `group_frame`、`group_axis`、trend、coherence 和 strength，避免循环证据；它们只在 candidate 形成后描述 candidate | 是否另开独立实验比较方向参与 membership，以及独立评价量是什么 |
| 2D neighbour 与 path graph 可互换 | `inter_region` graph 已使用自由空间/路径语义 | `normalized_boundary_gap` 节点是 furniture groups；`inter-region gap-path graph` 节点是 activity-region candidates；二者同时存在，不能互相替代或反写 authored membership | 是否把 group edge 纳入任何联合模型 |
| SVG/IFC 可以宣称全量 parity | 现有测试是 planar canonical evidence；SVG capability 明确没有 height/volume query | IFC 是主验收，含 2D、3D、混合指标；SVG 只验声明的等价 2D canonical facts；3D/Z/clearance/阻隔混合指标只能由 IFC fixture 验收 | fixture 维护人、analysis plane、单位归一化和每类事实 tolerance |
| probe 的 selected baseline 是设计结论 | `group-level-design-probe/v1` 生成 `selected_*_baseline`，但只代表当前 probe 候选 | v1 结果保留为候选比较和数值 oracle；v2 才覆盖本审查新增退化/3D/parity cases，仍不是 production API、prior、心理阈值或真实准确率 | 是否创建 schema v2、纳入哪些 planned cases、谁批准其 oracle |

### 12.3 修订后的 inferred-group 形成契约（建议，不冻结）

1. **节点过滤。** 输入节点是有效的 authored furniture-group records：IFC 中必须有
   `IfcGroup.ObjectType=furniture_group`，且保留 group id、member ids、来源和全部
   membership provenance。单个家具不能因 proximity、名称、图层、普通 group、旧
   region 或缺失 group relation 自动成为节点。节点的 authored validity 与其 geometry
   status 分开记录。
2. **代表与通道。** 每个节点分别保留 physical plan/3D support、外部传入的
   affordance geometry、level/Z-band 和 geometry completeness。physical support 与
   affordance support 不相加，不以家具类型补造 affordance；每个通道都可为
   `computed`、`partial`、`not_available` 或 `invalid`。
3. **先 pairwise，后 candidate。** 对所有可评估的家具组对生成关系记录；至少保留
   `raw_boundary_gap`、`normalized_boundary_gap`、contact/overlap、member-pair
   provenance、尺寸/center 摘要、3D clearance/overlap、Z-band/level compatibility
   和 wall/opening barrier observation。不能用一个布尔 edge 隐藏 channel 缺失或
   invalid。2D 投影近邻、3D 关系和阻隔关系分别命名；不同楼层的同 XY 投影不能仅
   因 2D gap 变成 computed membership edge。
4. **候选生成。** relation graph 是共同输入；connected-components 只回答
   “chaining baseline 会怎样”，complete-link/max-intragroup-gap 只作为可比较候选。
   结果应是独立的 inferred candidate records（成员 authored group ids、支持边、
   排除边、算法、参数、status），而不是覆盖 authored groups 的新事实。
5. **歧义与共享成员。** 在 owner 决定前，contract 必须能表达 overlapping
   candidates、未分组节点和 ambiguous candidates。共享 authored member 的 pair relation
   必须标记 `shared_member_dependency`；同一 shared member 的零 gap/overlap 不应被
   当作两个独立 group 的充分 membership 证据，是否排除该证据留给 owner。
6. **状态传播。** 全部 member usable 才是 `computed/complete`；usable 加 missing 是
   `computed/partial`，缺失原因进入 `excluded_member_reasons`；任一 invalid 使 group
   representative `invalid/not_computable`，但可保留 valid diagnostic support；全缺失
   是 `not_available/not_applicable`。任何 invalid 都不能静默改成 missing 或数值零。
7. **membership 与 trend 解耦。** candidate 形成不读取 `group_frame`、`group_axis`、
   trend、coherence 或 deterministic strength。若将来允许方向参与，必须另建 estimand、
   independent comparison 和敏感性分析，不能使用“先按方向分组、再用方向证明分组”的
   循环流程。

### 12.4 Representative geometry 与 trend 语义

- 首阶段物理 representative 使用 additive `support_area = Σ A_i` 和面积加权
  `center = Σ A_i c_i / Σ A_i`。同时输出 `within_member_covariance`、
  `between_member_covariance` 和它们的和 `covariance`，不能只输出总 covariance。
- `overlap_area` 是独立 observation；未运行拓扑时必须是 `null` 加
  `overlap_area_status=not_computed`，不能用零代替未知。`union_area_status` 首阶段为
  `deferred`；self-intersection、孔洞、多重 overlap 的去重规则不能静默猜测。
- `excluded_member_reasons` 按 member id 保存 `missing_geometry`、`invalid_geometry`、
  `degenerate_geometry`、`non_finite` 等原因。`geometry_completeness` 表示输入完整度，
  不是 posterior uncertainty。
- `group_frame` 是正交两轴 frame，使用 `R_4 = mean(exp(i·4θ_j))`，结果 modulo
  90°；因此 0°、90°、180°、270° 对 frame 等价。当前
  `column_grid._frame_from_angles()` 正是对归一后的角度取 `cos(4θ)`/`sin(4θ)`，而
  当前 `scene_inference._member_frame_consensus()` 也采用同一 4θ 语义。
- `group_axis` 是单一无向主轴，使用 `R_2 = mean(exp(i·2θ_j))`，结果 modulo
  180°；因此 0° 与 180° 等价，但 0° 与 90° 不等价。probe 的 doubled-angle
  `member_consensus` 只能作为 axis candidate，不能声称复现 column-grid frame。
- `directional_member_support` 是方向成员数或明确声明的 reliability weight；
  `coherence` 是方向集中度；`strength` 是确定性几何证据标量；`uncertainty` 是
  区间、geometry uncertainty 或 posterior。`strength=0.8` 永远不是“方向正确概率
  80%”。首个 Bayesian 模型仍有两个未选 estimand：
  `P(group_frame | member geometry, missingness, reliability)` 或
  `P(group_axis | member geometry, missingness, reliability)`。

### 12.5 反例和失败模式

- **Chaining：** A-B、B-C 过近而 A-C 很远；connected-components 会把三者合并，
  complete-link 会保留跨度约束。两者都不能在没有目标定义时被称为正确。
- **尺寸偏差：** 大 group 让 `sqrt(A_i+A_j)` 分母变大，可能把不相邻 pair 变成边；
  必须同时记录 raw gap、分母定义和 unequal-size fixture，不能把 synthetic `τ=0.33`
  当心理阈值。
- **投影假近邻：** 同 XY、不同 level/Z-band 或上下叠置；没有 3D compatibility 时
  relation 应为 unavailable/ambiguous，而不是 2D computed membership。
- **阻隔：** 墙或闭合开口夹在近邻之间；barrier observation 可限制 candidate，但不能
  被 inter-region path graph 或墙名替代。
- **外部 affordance 误导：** affordance-only overlap 与 physical contact/overlap
  不是同一证据；缺失 affordance 不能回退到家具类型自动生成的区域。
- **状态污染：** 一个 valid、一个 missing 应是 partial；一个 valid、一个 invalid
  应是 invalid/not_computable。把 invalid 排除后继续输出 computed 会掩盖数据错误。
- **共享 member：** A、B 都 authored 包含 X；X-X 的零 gap 不代表 A/B 独立相邻，需
  provenance 和依赖标记。
- **趋势循环：** 先用 frame/coherence 组成员，再用同一 frame 证明 group trend，
  会把定义重复计算成证据。
- **孤立与歧义：** 没有任何可靠 pair edge 的 authored group 必须允许未分组；有多个
  同分候选时必须返回 ambiguous，而不是按输入顺序、id 或 kNN tie 静默裁决。

### 12.6 仍需 owner 决定的问题

1. inferred group 的目标是几何聚集、功能/活动组合，还是两个独立 estimand。
2. pairwise relation 的必需 channel、3D clearance 定义、Z-band/level 兼容规则及墙/开口
   barrier 规则。
3. normalized gap 的 denominator（group additive、member-pair、union 或其他）与
   阈值/多尺度策略。
4. connected-components、complete-link/max-span 或其他 candidate generator 的首选及
   hard partition、overlap、未分组、ambiguous 的输出政策。
5. shared authored member 的 relation 是否可用于 membership，还是只作诊断。
6. partial/missing node 是否能进入正式 candidate 图；invalid diagnostic support 的
   消费者和权限。
7. physical support 与外部 affordance 是否都参与 membership，以及 affordance 标签、
   绑定和高度适用范围。
8. overlap_area 的 pairwise 多重去重语义、union 的拓扑范围和启用阶段。
9. 首个 trend 是否冻结为 `group_frame`；`group_axis` 是否作为独立描述量保留；Bayesian
   首模估计 frame 还是 axis。
10. IFC fixture、等价 SVG 2D fixture、analysis plane、单位归一化、canonical facts、
    tolerance 和 acceptance owner。建议 fixture 由 IFC/adapter 维护者提供，审查者只验
    canonical comparison；这只是责任分工建议，不是 owner 决定。
11. probe schema v2 是否纳入 0/90/180/270、axis/frame 差异、valid/missing/invalid、
    overlap/union、unequal-size、multi-membership、disconnected components、
    chaining、墙体阻隔、不同楼层、上下叠置、trend/membership independence 和
    IFC/SVG equivalent canonical facts。

### 12.7 接受、需要修订、暂缓

- **接受：** 严格的 IFC `furniture_group` 入口；普通 group 只作 provenance；家具组间
  inferred 层级；外部 affordance 输入边界；IFC 主验收与 SVG 2D oracle 边界；
  `normalized_boundary_gap` 与 `inter-region gap-path graph` 的 scope 分离；
  `group_frame`/`group_axis` 分离；support/coherence/strength/uncertainty 分层；
  deterministic strength 不解释为概率；probe 不证明心理效度。
- **需要修订：** 当前 generic-group fallback 和单 membership view；pairwise relation
  graph 与 candidate record；physical/affordance 分通道；within/between covariance、
  overlap/union/status 字段；invalid/missing 传播；3D/Z/barrier observations；
  IFC/SVG fixture 与 tolerance contract；probe schema v2 计划。
- **暂缓：** inferred candidate 的最终算法、阈值、hard/overlap partition policy、
  shared-member 证据政策、union 语义、Bayesian frame/axis 选择，以及任何 production
  implementation。未解决项不能从本次 probe 的 `selected_*_baseline` 字段静默冻结。

### 12.8 验证结果

- JSON 解析：`pixi run python -c ...` 成功解析
  `scripts/design/group_level/fixtures.json` 和
  `docs/project/evidence/d6-group-level-design-probe.json`，输出 `JSON_OK 2`。
  JSON 只验证语法，不证明设计正确。
- 设计 probe 数值断言：运行
  `pixi run python scripts/design/group_level/run_group_level_probe.py --output d6-group-level-probe-check.json`
  通过；随后比较临时结果与现有 evidence 的 `schema` 和 `results`，输出
  `PROBE_OK group-level-design-probe/v1 7 3`。v1 没有覆盖本节新增的 v2 planned cases。
- `git diff --check`：通过，输出 `DIFF_CHECK_OK`。
- 修改范围审计：`git diff --name-only` 只有
  `docs/project/d6-group-level-self-description-design.md`，输出
  `SCOPE_AUDIT_OK`；没有触及 `features/`、`adapters/`、正式测试、依赖或
  production API。临时 probe 输出已删除。

**STOP FOR DESIGN REVIEW**

## 13. A–G owner design ruling (2026-09-28)

本节是本轮 owner 裁决。它只批准设计边界和比较计划，不批准 Task 3c、implementation design、descriptor API 或生产代码。

### A. Inferred group formation

| 项目 | 裁决 | 设计规则 |
|---|---|---|
| authored nodes → pairwise graph | **批准** | 先固定有效 authored `furniture_group` nodes，再生成家具组之间 relation records；relation 不覆盖 authored membership。 |
| relation channels | **批准** | 至少记录 raw/normalized boundary gap、contact/overlap、member-pair provenance、center/size、3D clearance/overlap、Z-band/level compatibility、wall/opening barrier。每个 channel 独立有 value、status、reason；不得压成一个无来源 boolean。 |
| connected components | **批准为 baseline** | 只作为 chaining 对照，不作为默认正确答案。 |
| complete-link / max intragroup gap | **批准比较** | 与 chaining 在桥接链、长排、不等尺寸和多尺度 fixture 上比较；首个算法未冻结。 |
| candidate output | **批准表达能力** | schema 必须允许 hard partition、overlapping candidates、未分组节点和 ambiguous candidates；最终生产输出政策暂缓。 |
| shared authored member | **仅诊断** | shared-member pair 保留 zero-gap/overlap 和 `shared_member_dependency` provenance；不能单独作为 membership 证据。 |
| partial/missing/invalid | **分级处理** | partial/missing 节点可进入 relation graph，但 relation 只能是 `partial`/`not_available`，不能支持正式 membership edge；invalid 节点只保留 diagnostic relation，不进入正式 candidate generation。 |
| trend/frame/coherence/strength | **批准禁止首轮使用** | 首轮 membership 不读取 trend、frame、coherence 或 strength，避免循环证据。 |

正式 candidate generation 的最低输入是：两个节点均有有效 physical support、同一 analysis frame、可用 level/Z compatibility，以及未被 barrier channel 判为阻断。缺失 channel 返回显式状态，不变成通过。

### B. Representative geometry

以下全部**批准为首阶段设计语义**：

- `support_area = Σ A_i`，使用 additive support；overlap 不静默扣除。
- 输出 `center`、`within_member_covariance`、`between_member_covariance`、`covariance`、`overlap_area`、`union_area_status`、`excluded_member_reasons` 和 `geometry_completeness`。
- polygon union **暂缓**；其拓扑、孔洞、self-intersection 和多重 overlap 去重另开设计门。
- normalized-gap denominator 首阶段使用 additive support；overlap 只作 observation/provenance。
- valid + missing 为 `computed/partial`，但不得作为完整 membership evidence。
- valid + invalid 为 `invalid/not_computable`；valid support 只作 diagnostic；invalid 不得改写为 missing。
- physical support 与外部传入 affordance 永远分列。affordance 缺失为 unavailable，不得按家具类型生成。

### C. Trend estimands

两个量同时保留，名称不可互换：

- `group_frame`：`4θ`、modulo 90°、0°/90° 等价；
- `group_axis`：`2θ`、modulo 180°、0°/90° 不等价。

裁决：

1. deterministic baseline 首先采用 **`group_frame`**，原因是它与当前 column-grid 和 region-frame 语义兼容。
2. `group_axis` 保留为独立候选描述量，不进入首个 production slice，也不作为 `group_frame` 的别名。
3. Bayesian 首模采用 **`P(group_frame | member geometry, missingness, reliability)`**，以便与 deterministic baseline 比较同一 estimand。`P(group_axis | …)` 保留为后续独立模型，不与 frame posterior 融合。

### D. Evidence semantics

以下定义**批准**：

- `support_area`：几何面积；
- `directional_member_support`：方向成员数量或声明的 reliability weight；
- `coherence`：方向一致性；
- `strength`：确定性几何证据强度；
- `uncertainty`：区间、geometry uncertainty 或 posterior。

`strength` 永远不是方向正确概率。`coherence` 也不等于输入正确率；member dependence、missingness 和 geometry uncertainty 必须单独保留。

### E. Graph boundary

以下**批准并存**：

- `normalized_boundary_gap`：furniture-group nodes；描述 geometric proximity、boundary gap、contact/overlap；
- `inter-region gap-path graph`：activity-region-candidate nodes；描述 free space、occupancy、path width 和 connectivity。

group edge 不自动成为 route path；gap-path edge 不反写 authored membership；两者不互相替代。`region_internal` overlap network 另保留为 group 内部 relation evidence。

### F. IFC/SVG acceptance contract

| 项目 | 裁决 |
|---|---|
| IFC fixture owner | IFC/Bonsai adapter workstream 负责生成和维护；project owner 负责最终 acceptance。 |
| SVG fixture owner | SVG/canonical adapter workstream 负责等价 2D fixture；project owner 负责最终 acceptance。 |
| analysis plane | canonical `AnalysisFrame` 的 explicit plane；首个平面验收为 XY。不得按世界轴或 SVG viewBox 猜测。 |
| units | IFC authored unit 和 SVG declared source unit 均转换到 canonical analysis unit；验收默认使用 metres，并保留 source unit/provenance。SVG 不得从 viewBox 猜单位。 |
| geometry/length/gap/clearance tolerance | 继承同一 `AnalysisFrame.geometry_tolerance`；首个 probe default 为 `1e-9 m`，不得由 adapter 各自改写。 |
| area/overlap tolerance | 由同一 topology tolerance 推导并写入 fixture；首个 probe default 为 `1e-9 m²`，不足时必须显式提高并记录理由。 |
| angle tolerance | `1e-6 rad`（约 `5.73e-5°`）；比较前统一 modulo 90° 或 180°，取决于 estimand。 |
| status | status/reason 是 exact categorical comparison，不使用数值容差。 |
| minimum 2D canonical comparison | frame id/origin/basis/unit、mapped object/group membership、plan geometry area/centroid、representative status、selected trend estimand/status/angle/strength/coherence、pair gap/contact/overlap/status 和 provenance method。 |
| 3D/Z/clearance/barrier/mixed metrics | **仅 IFC 验收**。SVG 只验证声明等价的 2D canonical facts，不声称 3D parity。 |

fixture mapping 必须提供 source-independent correspondence；不能按 XML/STEP traversal 或 lexical id 排序制造对应关系。

### G. Probe schema v2

**批准纳入设计 probe schema v2 计划**，但 v2 仍是 design-only evidence，不是 production API、默认心理阈值、Bayesian prior 或准确率证明。v2 planned cases：

- 0°、90°、180°、270°；
- axis/frame 差异；
- valid + missing + invalid；
- overlapping members；
- additive area / union area 对照；
- unequal-size normalized gap；
- multiple authored membership；
- disconnected components；
- chaining 与 complete-link/max-span 对照；
- wall/opening barrier；
- different levels；
- stacked geometry；
- trend/membership independence；
- IFC/SVG equivalent canonical 2D facts。

v2 每个 case 必须记录生成参数、analysis frame、unit、tolerance、expected computational property、status 和 limitation。未运行 case 标记 `planned`，不能写入 `selected baseline`。

### 13.1 Remaining design gates

本轮已裁决首个 deterministic trend、Bayesian 首模 estimand、candidate graph channel、状态传播和 probe v2 范围。仍未批准：

1. chaining 与 complete-link 的最终 candidate selector；
2. hard partition、overlap、unassigned、ambiguous 的 production 输出政策；
3. normalized-gap denominator 的多尺度敏感性策略；
4. shared-member evidence 是否在任何后续模型中可作非充分支持；
5. overlap 多重去重与 union topology；
6. IFC/SVG fixture 的具体文件、最终 tolerance acceptance 和人员签名。

这些问题解决前，保持 **STOP FOR DESIGN REVIEW**，不进入 Task 3c、implementation design、descriptor API 或生产代码。
