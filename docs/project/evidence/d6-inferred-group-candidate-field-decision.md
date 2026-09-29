# D6 inferred-group candidate-field decision record

日期：2026-09-29
范围：candidate-field design probe 的设计审查，不进入 implementation design、production selector 或公共 API。

## 结论

本 checkpoint **保持 STOP FOR DESIGN REVIEW**。探针已经证明可以并列保存多种尺度视图、聚合视图、空间角色证据和冲突状态，但尚未证明其中任何一个规则可以成为生产选择器。下一阶段可以设计 membership-level candidate estimand；关系 edge 是其输入证据层，space-role 是并行证据层。

## 已核实事实与 provenance

- 8 个 fixture family 已运行：`gap-jump`、`minority-mixed`、`geometry-conflict`、`space-conflict`、`bridge-chain`、`overlapping-candidates`、`missing-invalid`、`context-perturbation`。
- D0、D1 已运行；B1 Bayesian 与 M1 ML 均明确为 `not_run`。
- D0 保持 `candidate_view_status=deferred`、`candidate_views=null`；没有写入 formal membership edge。
- invariance、missing/invalid propagation、hard veto、context separation、overlap/ambiguity/unassigned assertions 已通过。
- 外部 truth 文件的状态是 `external_computational_truth_not_consumed_by_probe`，不是人工标签，也不是心理真值。
- 设计 artifact manifest 状态为 `design_only_stop_for_design_review`，并声明没有修改 production selector、formal edge、公共 API、`NeutralSceneV2` 或测试。
- D1 的 space profile 来自设计 fixture 的关系/角色输入；当前生产实现尚未完成自由空间、连通性、瓶颈和阻隔的独立计算。因此空间证据可以保留，但不能据此冻结生产规则。

依据文件：

- [experiment record](d6-inferred-group-candidate-field-experiment.md)
- [experiment evidence](d6-inferred-group-candidate-field-experiment.json)
- [artifact manifest](d6-inferred-group-candidate-field-artifact-manifest.json)
- [fixture registry](../../../scripts/design/group_level/inferred_group_candidate_field_fixtures.json)
- [computational truth record](../../../scripts/design/group_level/inferred_group_candidate_field_truth.json)

## 逐项裁决

| 项目 | 决定 | 记录的规则、参数或范围 | 理由与限制 |
|---|---|---|---|
| 1. 下一阶段 estimand | **approved（仅下一阶段设计）** | 目标为 **membership-level candidate view**。edge-level relation 是输入证据；space-role-level 是独立并行证据。 | 探针的结果单位是成员集合，且能保留重叠、歧义和未分组；单纯 edge 不能表达这些候选集合。space-role 尚未由生产自由空间计算支持。生产 membership selector 仍 deferred。 |
| 2. scale recipe | **approved（并列实验）** | 保留 `relative_gap_rank`：`q={0.25,0.50,0.75}`，`inclusive_linear`，以当前 fixture 的 computed normalized gaps 计算；`local_persistence_window`：`window={1,2,3}`、`persistence={1,2}`，按端点邻居 rank 并要求至少 p 个窗口保持；`space_profile_rank`：`q={0.50,0.75}`，对可用 profile 取 inclusive quantile，缺失保持 missing。 | 三者都已预注册并能揭示尺度敏感性。没有选择其中一个进入生产；任何新参数或新 recipe 必须另行停止审查。 |
| 3. aggregation recipe | **approved（并列诊断）** | `all_pairs`：保留所有选中内部 pair；`max_span`：内部最大 normalized gap 不超过当前 scale bound；`min_gap`：每个选中 pair 形成二成员候选；`complete_link_diagnostic`：选中 pair graph 的 maximal cliques。 | 并列输出能暴露 chaining 与整体紧密度的冲突；当前不产生 formal edge，也不选择默认聚合。 |
| 4. candidate status | **approved（仅设计输出）** | 允许 `overlapping`、`ambiguous`、`weak`、`unassigned`。允许 singleton 作为显式单成员身份/未分组诊断；不把 singleton 自动解释为正向 inferred group。 | 探针已经观测到这些状态；孤立节点均为 `unassigned`。未来生产语义必须另行规定 singleton 是否消费。 |
| 5. empty-space role | **approved（独立 evidence）** | `corridor_candidate`、`activity_space_candidate`、`separator_space`、`connector_space` 作为空间场/关系证据；不直接加入 authored furniture membership。 | 空间角色可作分隔、连接或协变量，但不能反写家具组成员关系。当前 fixture role 不是生产自由空间算法的验收结果。 |
| 6. production selector | **rejected（本 checkpoint）/ deferred（未来设计）** | 不批准唯一 selector、默认尺度、默认聚合或 production API；candidate view 保持 design-only。 | 配方会产生不同候选；尚无冻结 estimand、holdout 阈值或完整空间场实现。实现 selector 会把探针结果误写成技术规格。 |
| 7. B1 Bayesian | **deferred** | 允许下一阶段围绕 membership-level estimand 设计，但必须先单独冻结：estimand、prior、likelihood、spatial dependence、identifiability、calibration。当前 `not_run`。 | 现有证据支持把 Bayesian 作为可研究方法，不支持当前家具布局的具体先验、后验或概率解释。`co_membership_evidence` 仍是确定性证据，不能当概率。 |
| 8. M1 ML | **deferred** | 必须先预注册 feature representation、算法、超参数、seed、validation target 和不依赖 truth leakage 的训练/验证切分。当前 `not_run`。 | 没有目标标签、独立验证目标或预注册模型；不批准以聚类结果挑选“最佳”分组规则。 |
| 9. synthetic holdout 与 acceptance | **approved（作为门槛框架；数值阈值 deferred）** | 按 fixture family/seed 划分 development 与 holdout，禁止按 member/pair 随机拆分。holdout 至少覆盖 gap-jump、minority、geometry-conflict、space-conflict、bridge、overlap、missing-invalid、context 及 invariance。 | 先冻结可审计的门槛，再冻结模型数值标准；当前不虚构一个跨模型通用的 precision/F1 阈值。 |

## 后续验证门槛

任何未来 candidate selector 或 B1/M1 原型都必须先通过以下硬门槛：

1. authored eligibility 与 context separation 不变；普通 group、名称、图层和 context 不得偷建 furniture node。
2. mutual-exclusion veto 永不被违反，并保留 veto source reference。
3. `missing`、`invalid`、`partial`、`not_available` 保持分类传播，不以零、默认中心或默认 clearance 填补。
4. translation、rotation+frame、positive unit-scale、ID/traversal reorder 保持 canonical relation signature 和可复现排序。
5. overlap、ambiguity、weak、unassigned 和 singleton diagnostic 不被静默折叠为单一硬分组。
6. 不读取 computational truth 文件来生成候选；truth 只能在 holdout 评估侧使用。
7. 报告 membership-level pair/set recovery（按 fixture family、recipe 和状态分层），至少包含 pairwise precision/recall/F1 或 set Jaccard/coverage，并单独报告 ambiguous/unassigned coverage；不得只报一个总体分数。

上述定量指标目前是**报告项目**，不是已批准的通过阈值。B1 还需 proper predictive score、区间覆盖、simulation-based calibration 或 posterior predictive checks；M1 还需 held-out recovery、稳定性和敏感性分析。只有在 estimand、selector 和 holdout 规则全部冻结后，才能提出生产验收阈值。

## 明确不构成的结论

- 本记录没有选择 K-means、Bayesian 或任何 ML 算法。
- 本记录没有把 `strength`、`co_membership_evidence` 或 recipe agreement 解释为概率或心理可信度。
- 本记录没有证明空间角色对应人的走廊、活动区或分组感知。
- 本记录没有批准 IFC/SVG 之外的新 adapter、3D clearance、opening barrier 或 production path graph 实现。

**STOP FOR DESIGN REVIEW**
