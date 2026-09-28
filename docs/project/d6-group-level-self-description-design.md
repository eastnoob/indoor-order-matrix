# D6 Task 3d：家具组层面的场景自描述设计

- **状态：** design-only，等待 owner review
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

**STOP FOR DESIGN REVIEW**
