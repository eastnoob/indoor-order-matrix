# D6 总体自描述设计表

- 日期：2026-09-29
- 状态：设计稿；未批准 production API、候选合成算法或 Bayesian 实现
- 目的：定义家具组与空间场的机器可计算描述，使后续实验可以比较 inferred-group 合成机制
- 非目标：心理感知效度、人工 order label、真实场景准确率、由家具类型自动生成 affordance
- 设计来源：项目架构记忆、D6 group-level 设计记录、E8/E9/E10b 证据、group-inference grill notes

## 1. 总体结构

```text
输入事实
  ├─ eligible authored furniture groups
  ├─ group member geometry and authored semantic fields
  ├─ context geometry and source provenance
  ├─ explicit AnalysisDomain / openings / boundaries / affordances
  └─ analysis frame, units, tolerances
        ↓
F0 基础观测
  ├─ group geometry descriptors
  ├─ group-pair physical relations
  ├─ domain-relative spatial field
  └─ authored semantic evidence
        ↓
交互与竞争证据
  ├─ positive support
  ├─ negative evidence
  ├─ candidate competition
  ├─ explicit mutual-exclusion veto
  └─ missingness / invalidity / uncertainty
        ↓
场景自描述输出
  ├─ relation records
  ├─ spatial-role field
  ├─ local-neighborhood view
  └─ named inferred-group candidates
```

空间场和组关系场保持分离。空间场定义在 `AnalysisDomain` 上；组关系场定义在 eligible authored furniture-group graph 上。空区可以有自己的 `space_role` 候选，但不是家具组成员。

首阶段是无循环基线：基础空间观测不读取 inferred groups；inferred-group 候选可以读取基础空间场和组关系证据，但不回写 occupancy、domain 或 blocker 事实。联合或迭代 Bayesian 模型只能在单独设计后加入。

## 2. 输入与资格表

| 输入 | 进入方式 | 首阶段用途 | 禁止的偷换 | 状态 |
|---|---|---|---|---|
| authored furniture group | IFC 严格 `ObjectType="furniture_group"` 或等价显式 adapter relation | 最小家具分析节点 | 名称、图层、普通 `IfcGroup`、邻近关系不能创造节点 | 已确定 |
| group member geometry | world-space canonical analysis proxy（IFC `Analysis` 或外部传入 proxy）；3D 信息按指标保留 | 面积、中心、协方差、frame、pair relation | `Body`/本体几何永远不进入 trend；不使用历史 placement/local axis 伪造 trend | 已确定 |
| group semantic fields | 作者提供的类型、名称、用途、角色、兼容/互斥声明及 provenance | 软正/负证据或显式硬互斥 | 不等同心理主观性；不自动生成 affordance | 已确定方向 |
| context geometry | 未被标记为 furniture group 的 IFC/SVG/Neutral source object | alignment、边界、阻隔、自由空间、局部参照 | 不成为家具节点；不进入类型同类证据 | 已确定方向 |
| AnalysisDomain | 显式域几何和 provenance | 负空间、拓扑、空区角色场 | scene bounds 不能替代 domain | 已确定 |
| authored affordance | 外部传入的显式 geometry/purpose | 任务特定空间投影 | 不从家具类型自动生成 | 已确定 |
| openings / boundaries / levels | IFC/SVG/Neutral facts | barrier、Z compatibility、path/topology | 门几何不自动宣称 IFC opening relation | 已确定 |

### 2.1 资格与完整性

资格和完整性是两道不同的门：

- **资格**决定对象是否能成为 authored furniture-group node。
- **完整性**决定某个分析 profile 是否允许正式计算。UI checklist 检查 profile 所需字段；它不生成标签、不补全缺失字段。
- 没有资格的对象只作为 context。
- 已有资格但缺字段的节点，在诊断中保留 `not_available` / `partial` provenance；若 profile 把该字段列为必需，则不得静默进入正式结果。

## 3. 观测设计表

| 通道 | 首阶段观测 | 相对/连续原则 | 允许影响 | 不允许推出 |
|---|---|---|---|---|
| group geometry | `support_area`、center、within/between covariance、总 covariance、shape/extent、member frame | 使用同场景相对差异和多尺度变化；不写死距离阈值 | 几何相似或差异、代表 geometry | 功能相同、心理分组、membership 真值 |
| pair physical relation | raw/normalized boundary gap、contact、positive-area overlap、3D clearance/overlap、Z compatibility、member witness | 归一化规则、analysis plane、unit、tolerance 必须随记录保存 | pair support/separation | route path、authored membership |
| space field | free-space distance/clearance、connectivity、bottleneck profile、boundary openness、occupancy、barrier、local alignment | 定义在显式 `AnalysisDomain`；以场和剖面描述，避免单一 width cutoff | 空区角色、组间分隔/连接证据 | 家具类型、组内成员关系 |
| semantic evidence | type/name/purpose/role compatibility、source reliability、explicit mutual exclusion | 语义标签为交互证据；缺失不自动等同同类 | 软正/负支持；硬互斥 veto | 心理主观性、自动 affordance |
| contextual support | local neighbor support、同类/异类局部支持、cross-scale persistence、candidate separation | “没有气”只作为待实验的局部支持描述，不是计数阈值 | 少数混入 vs 独立成势的竞争 | 预先规定的最小成员数 |

任何通道都不能单独决定 inferred group。首阶段保留通道向量、来源、缺失、冲突和交互诊断，不先压成未经验证的固定权重。

## 4. 空间场与空区角色

空间场描述 `AnalysisDomain` 内的空区和其局部关系。空区不是“没有数据”，而是可被描述的场对象。首阶段可同时保留多个角色候选：

- `corridor_candidate`
- `activity_space_candidate`
- `separator_space`
- `connector_space`

`primary_role` 暂不冻结。角色应由自由空间、连通、瓶颈、开放度、占用和阻隔等证据形成；家具类型和方向只能作为与空间场连接的附加证据，不能取代场本身。空间角色记录必须保留分析域、采样/投影方法、缺失状态和 provenance。

context 对象不需要新增 blocker/occupancy 标签。指标根据其已有几何、位置、高度和来源信息判断参照作用；斜墙可以提供局部 alignment，墙体可产生分隔证据，悬空对象是否影响 clearance 由所分析的高度范围决定。具体判断待实验，不把所有对象投影一律视为地面障碍。

## 5. 证据交互与硬约束

首阶段每个 candidate 或 pair 至少保留：

- positive support vector；
- negative evidence vector；
- channel provenance/reliability；
- missingness and invalidity；
- conflict reasons；
- competing candidate references；
- optional deterministic strength（不是概率）。

普通类型/名称差异是软负证据。几何差异、空间分隔、缺乏局部支持等可以共同造成更强的竞争负证据。候选不必被强制压成唯一 partition，可以返回 overlapping、unassigned、weak 或 ambiguous。

作者明确声明的 mutual exclusion 是硬约束，作用到 candidate level：互斥的 A/B 不能出现在同一 inferred-group candidate，即使它们分别与共同邻居 C 有正向关系。该约束的 provenance 必须可追溯；普通标签差异不能自动升级为硬互斥。

`strength` 是确定性证据强度，`coherence` 是方向集中度，`support_area` 是几何面积，`uncertainty` 才表示区间、geometry uncertainty 或 posterior。它们不得互相改名。

## 6. Inferred-group 输出视图

### 6.1 Relation layer（必须保留）

节点是 eligible authored furniture groups。每个 pair record 保存 geometry、space、semantic 三类证据及 status/provenance。它是可审计事实层，不声称 pair 就是同组。

### 6.2 Local-neighborhood view（首个 canonical 候选）

回答“每个家具组与哪些其他家具组存在何种关系”。它保留局部邻域、连续 gap、contact/overlap、空间分隔、标签冲突和缺失状态，不生成唯一 partition，也不把最近邻自动当作同组。

### 6.3 Candidate view（待实验冻结）

回答“在声明的尺度与 cohesion 规则下，哪些 authored groups 可组成候选”。候选必须带：

- member group ids；
- scale/objective/provenance；
- support and negative evidence vectors；
- mutual-exclusion conflicts；
- overlapping/unassigned/ambiguous status；
- absorbed/weak candidate 解释（命名仍待实验）。

connected-components 仅作 chaining diagnostic；complete-link/max-span 作为 bounded-cohesion 对照；不得让任一方法静默覆盖其他方法。

## 7. Deterministic 与 Bayesian 边界

首阶段 deterministic 先输出证据和命名视图，不实现 Bayesian。后续 Bayesian 只能在 estimand 明确后加入，例如：

```text
P(group_edge | group geometry, space-field evidence,
  semantic evidence, gap, overlap, missingness, reliability)

P(candidate membership | group relations, space roles,
  semantic evidence, mutual-exclusion constraints)
```

它们描述场景自描述模型的不确定性，不是人的感知概率。不能把确定性 `strength` 直接当 posterior，也不能把未经人类因变量校准的结果称为可信度。

## 8. 必须完成的设计实验

实验单位是完整布局 fixture；同一 fixture 的多个家具或 pair 是重复观测，不是独立样本。每次只改变预先声明的因素，并检查不变量。

| 实验族 | 改变因素 | 需要观察的输出 | 失败解释 |
|---|---|---|---|
| minority-mixed | 少数标签是否连续、几何/空间是否同质 | 软负证据、局部支持、竞争结果 | 标签单独决定分组 |
| independent-minority | 少数标签形成连续势或被空区分隔 | 独立 candidate 支持、多尺度持续性 | 成员数量阈值主导 |
| geometry-conflict | 标签相同但尺度/形状/方向差异扩大 | 正负几何证据和候选竞争 | 类型标签单独合并 |
| space-conflict | 几何相似但自由空间、瓶颈或墙体关系改变 | separator/connector 角色及 group relation | 纯几何聚类忽略空间 |
| semantic-conflict | 普通标签差异 vs explicit mutual exclusion | 软负证据 vs candidate veto | 普通差异误升级硬约束 |
| context-perturbation | 加入/移除斜墙、柜台、灯具等 context | 只改变允许的空间/参照证据 | context 偷变成家具节点 |
| bridge/multiscale | chain、near/far、不同声明尺度 | local view、CC diagnostic、cohesion candidates | 强行唯一 partition |
| missing-invalid | semantic/geometry/domain 缺失或非法 | status 和可计算性传播 | invalid 被改写为 missing |

实验先输出证据，不预设哪种算法“正确”。只有某个机制显示稳定、可解释、对 ID/变换/输入来源不敏感，才可进入 implementation design 比较。

## 9. 冻结与实现门槛

进入 implementation design 前必须完成：

1. relation layer 字段、status、contact/overlap/near、单位和 tolerance；
2. local-neighborhood 作为首个 canonical descriptor 的确认；
3. space-field 角色字段和 domain-missing 传播规则；
4. candidate view 的尺度/objective provenance；
5. candidate competition 的最小可解释输出，不要求先选唯一分数；
6. candidate-level mutual exclusion 的冲突语义；
7. IFC primary / SVG declared-2D parity 的 canonical facts；
8. deterministic 与 Bayesian 的独立 schema 边界。

实现顺序仍为：

```text
relation observations
  → spatial-field observations
  → local-neighborhood descriptor
  → candidate experiment/diagnostic output
  → approved candidate synthesis
  → optional Bayesian uncertainty layer
```

在第 1–3 项没有审查通过前，不实现候选 selector；在第 5–7 项没有审查通过前，不把 probe 字段升级为 production API。

## 10. Skill-assisted design record

- `grill-me`：把“标签、空间、几何谁优先”拆成逐项裁决；结果是普通标签软负、强几何/空间反向竞争、明确互斥为 candidate-level hard constraint。
- `experimental-design`：将剩余问题组织为多因素 fixture 比较；固定布局为实验单位，避免把 member/pair 当独立样本，并预先写明不变量和失败解释。
- `scientific-brainstorming`：保留 geometry-only、space-field、candidate-view 和 joint/probabilistic 方案，区分 idea、assumption、prediction、decision，不用共识票数伪造证据。
- `scientific-critical-thinking`：分离已核实实现事实、设计解释、可计算证据和心理效度；检查混淆、循环推断和过度外推。
- `superpowers:writing-plans`：将后续实现门槛拆为可检查的设计顺序；当前仍未生成 production implementation plan，因为 selector 尚未冻结。
- `superpowers:verification-before-completion`：本设计文档提交前执行 diff 检查、链接/路径审计和 git diff 范围审计。

## 11. E11 交互 probe 更新

E11 记录见 [d6-self-description-competition-experiment-record.md](d6-self-description-competition-experiment-record.md)，证据见 [d6-self-description-competition-probe.json](evidence/d6-self-description-competition-probe.json)。8/8 个预设不变量通过：普通标签差异保持软负证据，几何差异和 closed barrier 分通道，明确 mutual exclusion 作为 candidate-level veto，context 不改变家具节点资格，missing/invalid 状态不互相改写。

E11 支持冻结 interaction contract 的表达方式，但没有冻结 support 权重、尺度、候选 selector、唯一 partition 或 Bayesian prior。下一阶段应进入 implementation-design review 草案，而不是直接实现 selector。

**STOP FOR DESIGN REVIEW**
