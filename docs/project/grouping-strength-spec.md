# 家具分组归属证据场与非概率强度 Spec

- 日期：2026-10-26
- 状态：独立审阅通过并按意见收窄；作为实现计划基线；不构成生产实现批准
- 用户已确认：以下五条输入规则作为设计基线
- 证据：[协议执行结果](evidence/grouping-strength-design-protocol-results.md)、[场切片](evidence/group-attribution-field-slice.md)、[执行协议](grouping-strength-design-experiment-protocol.md)

## 1. 目标

本设计描述家具组之间模糊、可重叠的组织关系。系统保留一个由证据构成的归属场，不为每组强制给出二值“属于/不属于”答案，不把多个候选压成唯一获胜分组，也不把场读数解释为概率。

核心结果是分证据家族、保留状态和来源的场 `E(g,k,s)`：在冻结作用域和尺度/查询 `s` 下，记录 AuthoredGroup `g` 对候选组织视图 `k` 的支持、反对、冲突、未知及其依据。若将来某类证据到标量的映射有可辩护依据，可另派生非概率读数 `M_k(g,s)`；没有依据时只输出场记录，不合成分数。

AuthoredGroup 是有来源的输入事实，不是现实分组真值。候选是可能组织方式的提议视图；其边界不构成成员真值。多个候选可以重叠、嵌套、并存或未覆盖整个作用域。

## 2. 范围与输入资格

本设计的最小单元是来源可追的显式家具 AuthoredGroup。只有明确的 `furniture_group` 标记或 adapter 明确声明等价的来源标记才使其合格，不能仅根据组内对象都是家具来推断资格。

经用户确认的输入基线如下：

1. 显式空组保留在输入审计中并标为 `empty_group`，但不成为候选节点，也不进入归属场。
2. 组内重复引用保留原始引用与重复诊断；身份和证据计算只计一次。
3. 失效成员引用保留来源记录。受影响证据标为 `invalid`、`partial` 或 `not_available` 并说明原因；不得静默丢弃或改写为负证据。
4. 同一物理对象可以属于多个合格 AuthoredGroup。每个组保留其成员身份；同一物理观察通过来源依赖去重，不因多个组引用而重复投票。
5. 未归入合格 AuthoredGroup 的家具保留为未分配/未知输入事实，不被自动补进某个候选。

现有 `AuthoredGroup`、canonical contract、`analysis_scene_view`、`group_self_description` 和 legacy dictionary 路径仍存在资格或身份语义差异。新归属场必须直接从 `NeutralSceneV2` 的 authored-group 来源事实建立共享 inventory；不得从 `analysis_scene_view` 的单值 `furniture_group` 反推成员关系，否则共享成员会再次被压成首个归属。`analysis_scene_view` 的 `group`、`region` 和 `furniture_group` 继续作为旧推理/评价路径的兼容投影，本 spec 不把它们当作归属场，也不在本切片迁移其消费者。canonical contract 继续严格拒绝重复或失效引用；若要为此类原始事实保留审计记录，必须在 canonical validation 前记录来源事实或连同拒绝结果保留，不能从已拒绝的 canonical scene 反推。legacy dictionary 只能表达对象上的显式 marker，不能补造空组、dangling 引用或共享成员事实；对它只保留可表示信息及兼容行为。实现计划必须覆盖这些边界，并保留最小反例作为验收依据。

## 3. 候选提议与归属场

候选提议记录 `P=(recipe, scope, proposal_extent, closure_status, proposal_evidence)`。`proposal_extent` 只表示指定 recipe 在其证据和作用域下提出的范围；不能作为归属值，也不能填充真实成员标签。recipe、尺度、驱动证据和搜索闭包都必须可追溯。

对每个已提出候选和尺度/查询，归属场的定义域覆盖冻结作用域内的全部合格 AuthoredGroup，包括 proposal extent 之外的组。范围外但在作用域内的证据作为边界张力保留；作用域外实体不创建零值 field cell，而以带来源和原因的 scope 外记录呈现。

每个 field cell 至少保留候选、AuthoredGroup、尺度/查询、逐家族证据记录、极性或解释、状态及原因、source refs、来源依赖，以及候选发现是否暴露于该证据。一次物理观察即使被不同算子引用，也仍是一个有依赖关系的来源，不自动成为多条独立证据。

候选之间不得要求归属读数之和为 1。场不执行互斥分区，不挑选 winner；若存在明确互斥，也只约束同一候选中的联合参与，不删除端点自身证据或影响其他候选。

## 4. 状态与互斥

证据状态至少区分 `computed`、`unknown`、`conditional`、`partial`、`invalid`、`not_available`、`conflict` 和 `not_evaluated`。无数值的 field cell 必须保留状态、原因和来源边界；缺失、无效、冲突或条件性不能转成数值零、支持或反对。

搜索完整度与证据状态分开记录。受限或预算耗尽的搜索标为 `incomplete`，不得宣称候选在 recipe 下已闭包或结果穷尽；这不应抹掉已计算的 field evidence。

只有来源可追、两个端点均唯一解析且处于冻结有效作用域内的明确互斥声明，才可以否决两端共同进入同一候选。端点 dangling、ambiguous 或 out-of-scope 时，声明保留为未决诊断，不作硬 veto。互斥不将任何端点的归属读数归零。

## 5. 非概率读数与组 profile

`M_k(g,s)` 是可选的证据派生读数，不是概率。只有当证据到读数的映射、适用证据家族、缺失处理、依赖处理和解释均有依据并经审阅时，才允许产出该标量。当前不指定数值权重、跨家族融合方法、阈值或强度校准方式。

候选 profile 汇总 proposal extent 内成员读数的分布，同时报告成员数、有效读数数、证据家族 expected/observed coverage、状态计数与缺失原因。extent 外但仍在作用域内的场单元继续保留并可单列观察，不计作候选内成员真值。

均值、中位数和最弱成员值只是比较用的 profile 视图，不是选定的生产聚合器。缺失值不得以零填补；singleton 不因没有内部 pair 证据而自动得到正向或满分读数；不同候选的读数不得跨候选归一化。

## 6. 诊断证据与决定边界

本轮诊断夹具检查了以下表示能力：完整候选×作用域场可表示重叠候选、proposal extent 外读数、scope 外无 field cell、unknown/conditional 状态、弱尾、按家族覆盖、来源依赖、singleton 缺证据，以及 original/overlapping-merge/broad profile 并列观察。夹具也将 driver 与 modifier 的提议/归属输出分开记录，将不完整搜索状态与 field evidence 分开表示；对于 dangling、ambiguous、out-of-scope 互斥端点，夹具保留声明且不触发 veto。这些结果只说明诊断夹具能表达这些区别，不证明生产归属场、互斥传播、证据映射、recipe 因果效果或真实强度读数已经有效。生产路径上的互斥传播尚未验证。

以下结论仍未建立：

- 当前输入消费者对上述用户确认规则的实现一致性；
- 任一生产候选 recipe 或 evidence driver/modifier 的现实因果效果；
- 提议证据复用于归属证据是否会因具体归属算子而抬高读数；当前依赖比较只暴露来源重合，合成 readout 不能估计因果膨胀；
- 可跨家族共享的强度量尺、数值读数映射、生产 profile 聚合器、权重或阈值；
- 真实场景的盲审可解释性、心理有效性或概率校准。

详见[协议执行结果](evidence/grouping-strength-design-protocol-results.md)。它允许本 spec 规定非二值场的结构与状态契约，不支持冻结现实强度公式。真实场景审阅和搜索成本测量仍是后续验证门。

## 7. 非目标

本 spec 不批准 Bayesian posterior、ML/聚类 selector、概率强度、合成标签拟合、唯一 recipe/winner、数值阈值、公共 API、UI 或生产实现。它也不把 Stage A/D6 候选恢复分数改称为归属场强度。

## 8. 实现前验收

实现计划可以据本 spec 编排工作，但生产实现开始前必须完成以下审阅门：

1. 统一输入身份语义或明确记录并获批各消费者的边界差异；以通用组、空组、重复、dangling、共享对象构成的最小反例验收。
2. 让 candidate discovery、完整 scope attribution field、来源依赖、状态、闭包状态和 profile coverage 有明确记录与可复放诊断。
3. 对同源、移除提议证据、独立/留出证据三臂比较，使用真实或可辩护的读数规则；若无独立数据，保留 leakage 结论未决。
4. 在未参与规则设计且盲化 authored group 名称的合适真实场景中审阅解释性；没有合适场景则明确保留未决。
5. 只有在证据映射和 profile 读法均有依据后，另行审阅是否冻结数值 `M`。不得以构造 fixture 的算术通过替代现实量尺证据。

完成这些验收后，才可考虑把标量映射、recipe 选择或生产门槛纳入后续 spec。
