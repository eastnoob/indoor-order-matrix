# D6 membership-level candidate estimand and synthetic holdout design

状态：design-only；完成本阶段后继续 STOP FOR DESIGN REVIEW。

依据：[D6 decision record](d6-inferred-group-candidate-field-decision.md)、[candidate-field experiment](d6-inferred-group-candidate-field-experiment.md)、[fixture manifest](../../../scripts/design/group_level/inferred_group_candidate_field_fixtures.json)。本阶段不修改 production code、公共 API、测试、NeutralSceneV2 或 adapters。

## Membership-level estimand

实验单位是一个完整 synthetic fixture。对 fixture 中的 authored furniture-group 节点集合 `G`，每条 candidate 输出一个成员集合 `C_k ⊆ G`，并附带 `scale_descriptor`、aggregation recipe、channel vectors、space-role references、missingness、evidence status、candidate status 和 provenance。

`R_ij` relation edge 只是输入证据；space role 是并行证据。estimand 是 candidate member set，不是一个必须覆盖所有节点的 partition。允许多个 `C_k` 重叠，也允许节点只输出为 `unassigned` 或 singleton diagnostic。singleton 不解释为正向 inferred group。

候选支持定义为 deterministic support：

```text
co_membership_evidence(C_k) =
  (selected internal pair count,
   computed internal pair count,
   supporting channel vectors)
```

它不是 probability。候选永远不写 `formal_membership_edge`；hard mutual-exclusion veto 优先于几何支持并保留 source references。`missing`、`invalid`、`partial`、`not_available` 保持分类状态，不做零填补或默认几何填补。

## Registered comparison surface

继续并列运行 manifest 中已注册的三类 scale recipe：

- `relative_gap_rank`：`q={0.25,0.50,0.75}`，inclusive linear quantile，使用 computed normalized gaps；
- `local_persistence_window`：`window={1,2,3}`、`persistence={1,2}`，按端点邻居 rank，要求在至少 `p` 个声明窗口保持；
- `space_profile_rank`：`q={0.50,0.75}`，对 available profile 使用 inclusive quantile，缺失 profile 保留 missing。

每个 scale view 再并列运行：

- `all_pairs`：候选内部所有 pair 都必须在当前选中关系中；
- `max_span`：内部最大 normalized gap 不超过当前 scale bound；
- `min_gap`：每条选中 pair 保留为二成员 candidate；
- `complete_link_diagnostic`：当前选中 pair graph 的 maximal cliques，仅作 diagnostic。

这些 recipe 只产生可审计对照。不会从 recipe agreement、最小 gap、connected component 或任一分数中选 production selector。

## Synthetic holdout

holdout 的 split unit 是完整的 generated fixture，而不是 member 或 pair。每个 family 使用独立 seed replica：development seeds 为 `101, 202`，holdout seeds 为 `303, 404`。八个 family 都必须在 development 和 holdout 出现：gap-jump、minority-mixed、geometry-conflict、space-conflict、bridge-chain、overlapping-candidates、missing-invalid、context-perturbation。translation、rotation+frame、positive unit scale、ID/traversal reorder 作为每个 split 的 invariance checks。

候选机制只接收 fixture manifest；truth 文件只由 evaluation side 读取。当前 checkpoint 只冻结 estimand、split 规则和报告指标，尚未物化 generated seed replicas 或 owner-approved truth targets，因此 holdout scoring 的状态是 `not_run`。

## Holdout metrics

所有指标按 fixture family、seed、scale recipe、aggregation recipe 和 evidence status 分层报告，不压成单一总体分数：

1. Pairwise precision/recall/F1：把 emitted candidate 内部 pair 的并集与 computational-truth pair 的并集比较；仅作描述性 recovery，不作为 selector 分数。
2. Candidate-set Jaccard：对每个 truth candidate set，报告它与所有 emitted candidates 的 Jaccard 分布；不选择一个“最佳 candidate”写回输出。
3. Member coverage：至少出现在一个 emitted candidate 中的 truth member 比例。
4. Ambiguous/overlapping coverage：只在 ambiguous 或 overlapping 输出中出现的 truth member 比例。
5. Unassigned coverage：只被输出为 unassigned 的 truth member 比例。
6. Status-stratified recovery：computed、partial、invalid、not_available 分开统计，禁止插补。

当前不设 numerical pass threshold、不比较 recipe winner、不运行 Bayesian posterior 或 ML clustering。若后续 owner 冻结 threshold，必须追加新的 design review 记录。

## Current probe result

现有 probe 结果保持有效：8 个 fixture family、11 个 scale views/fixture、44 个 aggregation views/fixture；D0/D1 assertions、hard veto、missingness、overlap/ambiguity/unassigned、context separation 和 invariance checks 均通过。B1 与 M1 继续为 `not_run`。

**STOP FOR DESIGN REVIEW**
