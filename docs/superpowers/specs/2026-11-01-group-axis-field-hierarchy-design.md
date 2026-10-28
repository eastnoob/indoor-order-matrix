# Group axis-field hierarchy：圆周方向族设计

日期：2026-11-01。状态：**owner-reviewed frozen design；.14 complete；实现未开始。**

本稿冻结 .14 首版行为；.15 implementation plan 已存在，索引、架构说明和主 checklist 已同步。实现、测试、指定 IFC replay 与新 artifacts 尚未开始。沿用[分组目标](../../project/grouping-goal-alignment.md)、[证据包最小规范](2026-10-30-evidence-package-minimal-standard.md)和[源轴身份协议](2026-10-30-group-axis-potential-field-identity-and-generation-protocol.md)。当前边界见[架构记忆](../../indoor_layout_evaluation_matrix_architecture_memory.md#group-field-hierarchy-decision-2026-10-31)与[实际架构](../../software-architecture.md#group-field-hierarchy--frozen-design-implementation-pending)。

## 1. 首版职责与对旧草案的收缩

在 `group-axis-potential` 包内追加自动、多尺度、可重叠的方向组织视图 `FieldFamily`。输入仍为实际家具组整体 PCA `overall_group_axis`；每个可用源轴生成的原始叶场、完整 scope 行、原始/组对渠道和状态均保留。家族不产生硬成员、空间边界、winner 或最终归属 `M`。

[2026-10-31 决策笔记](../../project/group-field-merge-decision-note.md)曾提出 complete-link、多条件关系门、formal/nonformal 晋升和近似 profile 压缩，均未冻结。本稿以一个确定的 circular angular-arc recipe 替代这些选择：

- 只枚举一个连贯方向带内的连续方向类，尺度 `beta∈[0°,90°)`；不强制全 scope 根节点。
- 方向与支持 profile 来自同一轴证据，仅作并列描述，不当独立票；coverage 不成为删场门。
- 所有生成族都是声明尺度下的 soft axis organizations；取消“正式场晋升”、最少三组资格和近似压缩。
- 小叶场与小家族始终可查；residual、effective support 和 scale persistence 供解释，不决定存亡。

`90°` 是本 recipe 的明确建模上限：只描述单一方向带，舍去正交混合与更粗方向组织；它未经现实校准，不是建筑学阈值。允许多个 maximal tops，也可能只有叶/alias 视图而没有多方向家族。距离条件、其他通道或未来联合结果仍可在同一 potential 包中追加，所需计算由该包拥有，不要求另一个 evidence package 启用；本稿不定义其公式。

## 2. 输入、叶场和精确方向类

冻结 `G=scope`：同一 scene、query、analysis plane 下全部合格 AuthoredGroup，按稳定 group identity 排序。继续使用现有可用轴判定：原渠道 computed、有限有效角度、有限 `c_g∈[0,1]`；undefined/degenerate/invalid 等保留原始原因，不造参考轴。`layout_axis` 和 suppressed member 渠道仅保留来源审计。

```text
theta_g = float(source_angle) modulo 180°, with -0 normalized to +0
delta(g,k) = min(|theta_g-theta_k|, 180°-|theta_g-theta_k|)
S(g,k) = c_g*cos²(delta(g,k))
K = every usable actual source-axis anchor; every g∈G remains a row
```

`S` 的计算与值保持现状；anchor clarity 不再乘一次，正交浮点尾数不人为截零。布尔值、非有限值、非法 clarity 不参与轴枚举。不同 scene/query/plane 或重复 group identity 在包边界拒绝，不做 first-wins。

**精确方向类** `C_i` 只由规范化 `theta` 的精确数值相等构成；不 round、不用 epsilon、不按 profile 接近合并。每类保留排序后的全部 anchor group IDs、原始 leaf field IDs、源角度与来源引用。类中每个叶场仍独立存在。`direction_alias` 只表示同向参考的支持函数冗余：叶场的 self flags、non-self 域、anchor metadata、lineage 不相同，不能互换整个记录。首版没有 `compressed` 状态。

将 n 个不同方向类按 `(theta, sorted anchor IDs)` 排序。先按上述约定得到 `[0°,180°)` 的 canonical source binary64 角度（若浮点 modulo 恰返回 180，则规范为 0），再以标准库 `Fraction.from_float(theta)` 将这个既有 binary64 值视为**精确 dyadic 值**。类相等、拓扑排序、unwrap 的 ±180、span、事件比较/相等和 lifespan/persistence 均在这些精确有理数上计算；不能先以 binary64 加 180 再转换，否则可能把两个不同角度舍入成同一 unwrapped 值。无 rounding、epsilon 或新依赖。相等事件同时处理，禁止顺序贪心。

精确运算仅用于本 recipe 的方向拓扑和尺度事件。原 S/J、profile、residual 与 resultant 保持现有浮点计算；方向描述的抵消仍采用现有 `1e-12` coherence 容差，此容差不影响 alias、birth、death 或 family identity。不引入通用精度框架。

## 3. 全尺度圆周枚举与停止

在无向圆周 `[0°,180°)` 上，取 `a_i=Fraction.from_float(theta_i)`，以精确整数 180 延展 `a_(i+n)=a_i+180°`（负下标同理），枚举每个起点 i 和长度 `1..n` 的连续类窗口 `W=[i..j]`。以下 0、90、180 均为精确整数常量，族 `F(W)` 包含这些类的**全部原始叶场**。

```text
birth(W) = a_j-a_i
if W contains all n classes:
    death(W) = 90°
else:
    left_extension_span  = a_j-a_(i-1)
    right_extension_span = a_(j+1)-a_i
    death(W) = min(left_extension_span, right_extension_span, 90°)
retain W iff birth(W) < death(W)
active(F,beta) iff birth(F) <= beta < death(F), 0° <= beta < 90°
scale_persistence(F) = (death(F)-birth(F))/90°
```

环绕窗口按上述 unwrapped 角度计算，不能把跨 0° 的相邻轴拉成远端。每个族按 anchor-group 集合去重；如同一集合有多个窗口表示，取 birth 最小、再按 unwrapped 起始规范角度、再按 anchor IDs 的顺序选定唯一表示。全类窗口仅在其实际 span `<90°` 时保留；n=1 时唯一类为 `[0°,90°)`。n=0 时不枚举，输出引用实际轴来源的 scope-level not_available 诊断；empty scope 仍由 caller 在 evaluate 之前处理。

输出所有非空 lifespan 及排序后的全部事件值，不挑一个默认“最佳尺度”。在任一 beta，active 集合就是该尺度下不可再向左右加入相邻类的方向窗口；同尺度可重叠，所有历史叶/族记录仍保留。birth 包含、death 排除，tie 事件先作为一个整体更新后再读 active 集合。`beta=90°` 不在定义域。

机器可读事件记录固定使用约分后的整数对 `[numerator,denominator]`（denominator>0，0 为 `[0,1]`），保存 `theta_exact`、`birth_exact`、`death_exact`、`scale_persistence_exact` 及事件列表；前三区间量单位为 degrees，persistence 为 unitless。可另附 display floats，但排序、去重、内容指纹和 active 区间判定使用精确值，不从 display float 恢复事件。事件选择使用原 rational pair；任意 binary64 beta 查询先以 `Fraction.from_float(beta)` 转换，再在 `[0,90)` 内比较。fraction 的整数对必须按原整数精度读写，不能经 JSON consumer 的浮点解析静默舍入。

最多检查 `n(n−1)+1` 个不同非空连续类集合（n≥1；全类集合只算一次），不枚举一般子集或 maximal cliques，无随机种子、固定 K、搜索截断或隐蔽规模门。所有有限窗口枚举完即停止，不另设支持阈值。枚举候选数为 O(n²)，完整 family×group 支持输出在组数与轴数同阶时可达 O(n³)；本次首次验收只针对真实 37 组基线，不承诺千组规模，不静默截断输出。

## 4. 包含关系是输出 DAG

每个 retained 族连接到由它增加紧邻左类或右类而成、span `<90°` 的直接超集；相同边去重，按 `(child family_id,parent family_id)` 排序。精确 dyadic 方向类的相邻 gap 严格为正，因此每个这类 one-neighbor 超集均有 birth<death，必定存在于 retained 结果中。它们是集合包含的 immediate parents；多父节点、重叠节点与多个无父 tops 均合法。族的 leaf IDs 完整列出，因此无需沿 DAG 累加才能还原其组成。

单方向类节点引用单个原叶或全部精确 direction aliases；原叶到该类的引用是 alias/包含记录，不是“新增独立证据”。DAG 仅为**结果包含关系**，不引入执行器、scheduler、registry、服务或包间依赖框架。不生成虚拟全域根，也不把 parent 的合成朝向当作新 k。

## 5. 家族支持、缺失和统计域

对所有 `g∈G`，父/家族支持直接从原始叶场计算一次：

```text
J_F(g) = max_{k∈leaves(F)} S(g,k)
```

这是“对该族中至少一个实际参考方向的轴支持”，非负、`[0,1]`、越大越支持；不是概率、物理力或真实 cluster membership。不得 sum children、sum aliases、重复乘 clarity、重新定 anchor 或把覆盖不足的均值当完整支持。族方向类/anchor 集合不是家具组的硬成员名单；所有 scope 行继续显示。

每个 family cell 保留构成它的原始 cell IDs、值/状态/原因与源渠道引用。设 `V` 为已知原叶支持，缺失项仅作 `[0,1]` 的**可能值边界**：

```text
lower = max(V) if V nonempty else 0
upper = max(lower, 1 if any leaf cell unknown else lower)
value = max(V) only when every required leaf cell is known; otherwise null
known_max = max(V) if V nonempty else null
```

`lower=0` 是未知的下界，不是把未知观察填成零。全已知为 computed；有已知与未知为 partial；全未知为 not_available，并保存具体 source/raw/cell 状态和原因。即使上下界巧合相等也不掩盖未知来源。原始 invalid、outside、ambiguous 等事实继续原样留在 source 与 cell audit；结构性非法输入直接拒绝。输出只用现有 `FieldResultStatus` 七状态，不能新增 raw `conditional/unknown/incomplete` 枚举。

每个族保留两套明确域：`full_scope=G`；`non_anchor=G\A_F`，其中 `A_F` 是族的全部 anchor group IDs。non-anchor profile 的 expected 为 `|G|−|A_F|`，排除全部 anchors，不能沿用单叶 `N−1`。每域报告完整行向量、known/expected row 数与 coverage、known/expected leaf-cell 数与 coverage、原始状态计数、已知值均值及均值上下界。有效 0 计入 coverage；空域的均值/coverage 不可用，不能显示 1。

对每个域的 computed family rows，令 `w_g=J_F(g)`，描述统计固定为：

```text
support_mass = sum(w_g)
n_eff = sum(w_g)^2 / sum(w_g^2)  if sum(w_g^2)>0 else null
```

同时显示统计使用的 row IDs、known/expected coverage 与 missing counts；partial 时标为已知部分读数，不代表全域 n_eff。全零时 mass=0、n_eff 不可用且说明 no_positive_support；没有已知行时二者不可用。均值边界按全部 expected 行的 lower/upper 求和再除 expected；mass 边界同理。n_eff 是权重分散度，不是独立样本数、核心成员数或资格门；共享家具来源依赖仍保留，不能当作独立组投票。不采用 `support>0` cardinality 或 min3 eligibility。

缺失源轴不制造方向类；报告 admitted/excluded anchors、scope-axis coverage 及逐组原因。枚举只能声明 `complete_over_available_axes=true`，存在排除轴时同时标记 scope evidence partial，不能声称已穷尽未知方向组织。

## 6. 描述性关系、residual 与方向

叶场对保留实际 angle gap 和 `cos²(delta)`。profile 关系固定在 `D=G\{anchor(k),anchor(l)}` 上比较，排除两边 self；共同已知行 `D_known` 上报告 `profile_l1_mean=mean(|S(g,k)−S(g,l)|)`、`profile_similarity=1−profile_l1_mean`、逐行差、known/expected coverage。无共同已知行为 not_available，部分覆盖为 partial。它们仅解释方向支持的相似性，不作为独立验证、另一个支持票或家族生成门。

对每条 child F → immediate parent P，令 `C=leaves(P)\leaves(F)`，直接计算 `J_C=max_{k∈C}S(g,k)`，使用 `D=G\A_P`：

```text
residual_F_given_P(g) = max(0, J_F(g)-J_C(g))
```

标量 residual 只在两侧均 computed 的共同已知行给出，并保留全 D 的行/状态、共同覆盖、已知 residual mass/mean 与不可比较原因。未知行可报告保守边界 `[max(0,L_F−U_C), max(0,U_F−L_C)]`，不能填零；空 D/无共同已知行为 not_available。这里比较 F 与 **P\F**；`J_F−J_P` 因 max 包含关系退化，禁止使用。多父分别报告，不选最有利 parent；无 parent 时 `parent_ids=[]`、residual not_available/no_parent，不能称 residual 为零。方向 aliases 所产生的零 residual 不删叶、不晋升父。

`scale_persistence` 只描述这个方向窗口作为尺度极大窗口存在的长度比例；不是时间稳定性、扰动鲁棒性、正确概率或物理强度。singleton 与 two-anchor family 保留 `singleton_anchor` / `two_anchor` 提示；n_eff 不替代这些来源基数，三者都不决定是否保留。

显示族的实际 member axes；另以完整 G 的 computed J 行只读描述：

```text
Q_F = sum_g J_F(g)*exp(i*2*theta_g)
direction = arg(Q_F)/2 modulo 180°
coherence = |Q_F|/support_mass
```

支持只用一次。报告 coverage、anchor contribution mass/fraction、anchors included。零质量时方向/一致性 not_available；抵消时方向 null/ambiguous、一致性保留；正贡献仅来自族 anchors 时标 `anchor_only`（仅一组时亦标 singleton）。缺失覆盖与方向状态分开保存。Q_F 不改变原轴、S、J、家族或原全场 resultant helper 的语义。

## 7. 现有封装的具体接线

复用 [`features/group_axis_potential_field.py`](../../../features/group_axis_potential_field.py) 的实际轴判定、source-axis 计算及 [`features/field_core.py`](../../../features/field_core.py) 的 `EvidencePackage` / `EvidenceOutputChannel`。内部普通函数可以复用同一批轴输入和原叶输出；现有 factory 拟增声明参数 `build_group_axis_potential_package(*, scene_namespace=None)`。无参数调用继续原 axis-only 行为；传入非空稳定 namespace 时，以不可变闭包固定这个 recipe/target 参数，在一次 evaluate 内追加 hierarchy 输出；空字符串拒绝。扩展模式使用新的 output function/schema 版本，保留全部既有纯轴值与叶身份；不新建必须启用的 hierarchy evidence package。

`EvidencePackage.evaluate(source_envelopes)` 签名不变。其输入只能为 `FieldResultEnvelope`；现有 `EvidencePackageOutput` 不是任意嵌套输入。`derived_from` 必须引用本次 source envelopes 中实际存在的渠道，不能把内存中的 child output 伪装成合法 `EvidenceChannelReference`。因此 hierarchy 渠道直接引用实际 row/anchor `overall_group_axis`，并在 provenance 追加 `leaf_output_refs`、`child_family_refs`、公式和版本；这是可审计结果关系，不绕过 shared-core 校验。

派生渠道的最小声明如下；均使用现有 `EvidenceOutputChannel`，无新结果基础类型：

| target / channel | 观察内容与量尺 |
| --- | --- |
| direction-class / `axis_direction_aliases` | theta、全部 anchor/leaf IDs、仅 direction alias 的声明；degrees_mod_180 与身份记录 |
| family / `axis_family_definition` | scope、classes、anchor/leaf IDs、exact birth/death、半开区间、exact scale persistence、generation coverage；按 §3 rational pairs 保存 degrees/ratio，可附 display floats |
| family-cell `(family_id,group_id)` / `axis_family_support` | J、known_max、上下界、完整原 cell refs/status；unitless `[0,1]` support |
| family / `axis_family_profile` | full/non-anchor 域、向量、mass、n_eff、均值边界与覆盖；各项明确 count/unitless，不作为总强度 |
| leaf-pair / `axis_field_relation` | direction/profile 差异及共同 coverage；描述性量尺 |
| child-parent / `axis_family_residual` | set difference、完整 residual 行/界、coverage、parent/child refs；unitless residual support |
| family / `axis_family_direction` | Q、direction、coherence、anchor-only/zero/cancellation/coverage；只读描述 |
| scope / `axis_family_scope_diagnostics` | 全部行、admitted/excluded anchors、无族/无轴原因、recipe 完整性 |

每个输出保留 source IDs、原 envelope identity、plane、schema、source algorithm versions、output_function_id/version；非 computed 必须有 explanation。任何可选 channel 缺失不删除完整 source envelopes、原叶/pair 输出或其状态。

## 8. 身份、缓存与 edit/undo/recompute seam

```text
family_id = hash(scene_namespace, semantic_query, recipe_id,
                 sorted immutable anchor_group_ids)
semantic_query = domain_id, frame, full plane, height_band, demand, tolerance,
                 declared semantic query/protocol version
recipe_id = source-axis-circular-arc-lt90-v1
```

family logical identity 不含当前角度、birth/death、运行时间、非语义 revision、child output IDs 或原 leaf IDs；叶 ID 可能含版本化 query 指纹，仅作为原样来源引用保存。相同 anchor 集合在方向变化后若仍合法，逻辑身份相同，内容指纹必须改变；若不再生成则从 current target set 消失，旧结果仅供审计。新增/删除成员或 scene/semantic query/recipe 改变产生相应新身份。

scene namespace 与可变 source-content fingerprint 分开，不能以 IFC 文件内容 hash 或每次编辑生成的 ID 代替。**当前 retained envelopes 没有稳定 scene namespace；实际 `source_manifest.project_global_id`（manifest 顶层）为 `2uGd6yom9GZe5$z7LfbGW0`。** replay caller 在核验 manifest/源指纹后，显式向上述 factory 传入 `scene_namespace="ifc-project:"+project_global_id`，作为声明的 recipe 参数；不能假定 sidecar 自动进入 evaluate。namespace、hierarchy recipe/version 必须同时进入输出 provenance 和 package contract 的 recipe dependency fingerprint，不能只藏在闭包或 target ID 中。原始 envelopes、cache identities、legacy leaf IDs 均不重封装或改写。hierarchy 请求缺失/冲突 namespace 时拒绝伪造身份，不能悄用 path、世界坐标或全局变量。此 factory seam 尚未实现。

family semantic content 身份包含规范化 scope/semantic query/plane、namespace、实际原始角度与 clarity/状态/完整 sources、recipe、算法/schema/output function 版本、numerical policy、targets/channels。timestamp 与纯递增 UI/capture counters 不作为语义内容；真实 query/protocol、算法或 source 版本必须保留。实际 package cache/output_identity 仍含原始 envelope references 及现有 dependency identities，遵守 shared core；family content key 不能直接替换它或保证跨不同 source/result identities 的复用。

已核实的兼容行为：当前 `_field_id` 使用 `cache_identity.query_fingerprint` 且未显式加入 scene namespace；`build_field_result_cache_identity` 的 query payload **包含 revision**。保留源当前 revision 是固定的语义 query/protocol tag `group-trend-alignment-v1`，不是观察到的编辑计数器，必须保留在语义依赖中；这不证明已有 undo 故障。UI adapter 应把非语义编辑/capture counters 与该 tag 分开。旧叶 IDs 保持原样，新 family 身份显式记录 semantic query signature；metadata-only revision 行为是 .15 的兼容性检查与已知边界，不成为广泛 core cache 重写任务。

复用 whole-package freshness：scene/model/source/plane/query/recipe/channels 和 algorithm/schema 变化均按真实依赖失效；输出 `recompute_required`、`reasons[{code,dependency,cached,current}]`、`affected_targets`。recompute 后重建当前 target set，移除的目标也须进入受影响报告。UI 只读这些字段并区分旧结果；不在 freshness 查询时自动重算。edit 改内容，undo 恢复相同内容且恢复当前支持的 dependency identities 时允许缓存复用；若 raw source/result revision identities 不同，不能仅凭 family content 相同声称自动复用。验收必须独立构建 current contract 与 saved contract 比较，不能以 runner 的 cached=current 写时 `fresh` 收据证明 undo 或浏览器操作通过。缓存存储与 live UI 仍不在本稿实现范围。

## 9. 指定 IFC 与验收边界

只复用保留的真实数据：`outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z/` 的 envelopes、完整原输出、matrix、description、source_reuse/source_manifest 与同平面几何，来源 trend run 为 `outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/`。指定 IFC 为 `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`，SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`。既有报告记录 37 组、1,369 computed cells、4,112 原派生输出；95 成员是来源几何规模，不改变分析行单位。[原回放证据](../../project/evidence/group-axis-source-axis-field-v1.md)与[用户图面审阅](../../project/evidence/group-axis-source-axis-visual-preview-v1.md)不等于新 hierarchy 验收。

实施后的 replay 须保留原 IFC 指纹，并另记录所读 retained 文件/规范输入的内容指纹、原/适配 envelope identity、schema/function/recipe 版本、query/plane/scope、scene namespace 的来源。不能改写旧 run 或仅核验 IFC hash 而忽略 retained 输入变化；不重提 IFC、不创建模拟家具/关系/数值布局 fixture。

验收数据为真实 retained 输入及其真实子集/排序重放；数学边界用公式级 algebraic assertions，不能伪装成观察到的新布局。必要断言包括：规范角度等价与精确 dyadic unwrap，尤其 binary64 加 180 会舍入合并但精确值仍不同的情况；原叶和 source 状态完全保留；精确 aliases 不丢来源；枚举覆盖、rational pairs 无损往返与半开事件/tie；DAG 严格包含/无环；J 的 max 一次性、alias 幂等与 parent 单调性；residual 对 P\F；固定 non-anchor 分母；上下界与 unknown 不补零；质量/n_eff 的公式；顺序确定性与独立 contract 的 edit/undo 内容比较。topology/event 断言按精确值相等，数值容差仅验证原支持/描述的浮点代数，不改变生成谓词。

所有未出现在实际 retained 数据的 singleton、two-group、missing/invalid、zero-clarity、cancellation、精确事件 tie、跨平面等情形，按真实覆盖清单如实标记 uncovered；纯代数断言只证明公式性质。禁止用修改真实数值或造家具的方式补称 IFC 覆盖。

实施计划将给出精确命令；拟议输出入口延续旧决策笔记的 `scripts/design/group_level/run_group_field_hierarchy_ifc.py`（当前不存在），仅接 retained run 和 output root。其验收应有 Pixi focused tests 与 retained replay；本稿不创建脚本或执行这些未来命令。

图面交付覆盖 **每个原叶与每个生成族**：完整 group×leaf/family 数值矩阵、可索引的同 IFC/同 analysis-plane plan views、尺度事件/包含关系表、可读 manifest 与 contract/status。复用一份 retained geometry dataset 和被选中的 family 向量即可；每个视图可按 manifest 索引展开，不要求为每族复制几何或另建 UI 框架。manifest 将每个 leaf/family/cell、birth/death、状态、来源指纹映射到实际可读的图层/索引视图；无族也保留原叶和 scope 诊断。平面展示连续支持/unknown 样式、实际 axes、覆盖和 residual 来源，不画硬场边界、阈值成员圈或 winner 分区。全部声明的 SVG/XML 和 JSON 结构可解析、所有索引视图可访问，owner 查看总览及代表小族/重叠族/顶部族后才裁定现实解释性；不能仅交截图或采样矩阵。

## 10. Owner 审阅项与停止点

owner 已选择这个明确收缩：方向带上限 `<90°`、完整连续窗口枚举、保留所有叶与小族、max 支持、互补 residual、仅 scale persistence、取消 formal 晋升/近似压缩。focused review corrections（manifest 顶层 project ID 与精确 dyadic topology/event 约定）已写入本稿，仍待 targeted reviewer 确认；不提前改变 .14/.15 或草案最终状态。算法本身没有留给实现者选择的关系门或核心规模参数。

实施接线限定为：①现有 factory 的显式 namespace 参数、已核验 manifest caller、recipe dependency 与扩展函数版本；②核查语义 query tag 与非语义编辑计数的分离，以及当前 dependency identities 下的 cache/edit-undo 行为。不存在已批准的 raw-envelope 重封装或通用 cache 重写。既有架构/2026-10-31 说明仍是历史设计基线；本稿接受后应同步为新的圆周 recipe，不能把两套规则同时宣称现行实现。

本稿已由 owner 接受并冻结为 .14 设计；.15 implementation plan 现已单独记录在 [`2026-11-01-group-axis-field-hierarchy-implementation.md`](../plans/2026-11-01-group-axis-field-hierarchy-implementation.md)，但实现、测试、IFC replay 与 artifacts 尚未开始。不要把本冻结设计或计划自检写成实现证据；不改代码/测试/脚本、不新跑 IFC、不创建输出 artifacts、不做 commit/push/merge/jj snapshot。
