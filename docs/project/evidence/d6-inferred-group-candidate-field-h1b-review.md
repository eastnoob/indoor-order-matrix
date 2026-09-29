# D6 H1b materialization review decision

日期：2026-09-29

## 裁决

**APPROVE：H1b 可进入 H2 holdout recovery scoring。**

这次 materialization 已经修复 H1 的核心问题：holdout 不再只是 seed metadata，而是实际的 seed-conditioned fixture 输入。

## 核实结果

- 8 个 family × 4 个 replica = 32 个完整 materialized fixture；
- development 使用 `101/202`，holdout 使用 `303/404`；
- 32 个 `materialized_content_sha256` 全部唯一；
- truth manifest 有 32 个对应 replica；
- 32/32 个 truth `input_content_sha256` 与 fixture content hash 匹配；
- holdout 与 development 的 geometry/context/space 输入实际不同；
- family structural invariants 保持；
- truth derivation 只读取 materialized input、状态、space profile/role 和显式 mutual exclusion；
- candidate probe 未读取 truth；
- `replication_only`、`invariance_only`、`generalization_holdout` 已区分；
- 未运行 scoring、未选择 recipe/threshold/selector，未修改 production code、API、adapter、测试或依赖。

H1b 的验证证明的是 materialization 和 truth provenance 正确，不是算法准确率，也不是心理效度。

## 批准的 H2 范围

H2 可以运行已注册的全部 scale/aggregation 组合，并输出分层 recovery report：

1. 只把 `generalization_holdout` 作为 holdout 结果；`development_reference` 只能用于调试/一致性检查；`replication_only` 与 `invariance_only` 不计入泛化分数。
2. 使用已注册的 3 类 scale recipe 及其参数和 4 类 aggregation recipe；不得新增 recipe 或修改参数。
3. 按 family、seed、scale、aggregation、evidence status 分层报告 pairwise precision/recall/F1、candidate-set Jaccard、member coverage、ambiguous/overlapping coverage、unassigned coverage 和 status-stratified recovery。
4. 先运行硬门槛：authored/context separation、hard veto、状态传播、invariance/reproducibility、truth isolation、overlap/ambiguity/unassigned 保留。
5. 报告 recipe disagreement；不得从 holdout 结果挑选 winner、调整参数或写入 production selector。
6. 不运行 Bayesian posterior 或 ML clustering；B1/M1 仍为 `not_run`。

## H2 尚不批准的事项

- production selector、默认尺度、默认 aggregation；
- 数值 acceptance threshold；
- singleton 的生产消费语义；
- Bayesian prior/likelihood/spatial dependence/calibration；
- ML algorithm、hyperparameters 或训练目标；
- 把 computational truth、recovery 分数解释为心理感知效度。

H2 完成后应再次停止在 `STOP FOR DESIGN REVIEW`，由新的结果决定是否需要继续实验或开始 implementation design。

**STOP FOR DESIGN REVIEW**
