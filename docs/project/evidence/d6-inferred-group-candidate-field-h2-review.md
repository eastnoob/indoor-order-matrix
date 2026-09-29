# D6 H2 Holdout Scoring Review

日期：2026-09-29
审阅提交：`3d25fdab92fb2814b8dc2bba0dee56e0ec795d28`
范围：H2 design-only holdout scoring；不进入 production selector、Bayesian/ML 实现或公共 API。

## 总体裁决

**ACCEPT WITH LIMITATIONS**。

H2 可作为“holdout 实验管线和证据边界已基本成立”的设计证据接受，但不能作为 aggregation recipe 已被有效比较、已选出 winner 或已足以冻结 production 规则的证据。后续 design review **有条件批准**：先完成 aggregation semantics repair/re-run，再进入完整的 recipe/selector design review。

## 已批准证据

| 项目 | 裁决 | 理由 |
|---|---|---|
| generalization holdout 范围 | approved | 仅计分 16 个 holdout replicas；development、replication-only、invariance-only 未混入评分。 |
| truth isolation | approved | candidate probe 不读取 truth；truth 只在 scoring 阶段使用，且标明为 evaluation-side structural truth。 |
| hard gates | approved | 16/16 通过 authored/context separation、hard veto、状态传播、invariance/reproducibility 和输出保留检查。 |
| scale recipes 并行记录 | approved as exploratory | `relative_gap_rank`、`local_persistence_window`、`space_profile_rank` 均被并行保留；结果只能描述差异，不能据此选 winner。 |
| 状态与候选保留 | approved | overlap、ambiguity、weak、unassigned、singleton 和缺失/无效状态未被静默压成单一答案。 |
| 指标定义 | approved as descriptive | undefined denominator 使用 `null`；F1、Jaccard、coverage 仅用于描述性恢复结果，不是心理效度、概率或真实场景准确率。 |
| SVG 可视化 | approved | 5 张 SVG 足以作为确定性几何/变量诊断；不构成心理证据或 production accuracy 证明。Blender 在本 checkpoint 不必运行。 |

## 必须修订的证据

### 1. Aggregation comparison：REVISE / blocker

当前 `run_inferred_group_candidate_field_probe.py` 中，`all_pairs`、`max_span`、`complete_link_diagnostic` 都调用 `_maximal_cliques(...)`；因此三者在当前 probe 中是同一实现路径的不同标签。报告虽已诚实记录该限制，但这意味着：

- 当前 H2 不能证明三种 aggregation 语义等价；
- 当前 H2 的 F1、candidate-set 输出和 recipe disagreement 不能被解释为三种 aggregation 规则的有效比较；
- 不得基于这些结果选择 `all_pairs`、`max_span` 或 `complete_link_diagnostic`。

后续最小修订要求：

1. 明确并实现 design-probe 层面的语义分离：
   - `all_pairs`：保留选中关系及其候选结构，不冒充 maximal-clique 规则；
   - `max_span`：实际计算并应用候选内部最大 pairwise gap 约束；
   - `complete_link_diagnostic`：保留 maximal-clique / complete-link 对照；
   - `min_gap`：继续作为 pair witness 对照，并明确其非 group partition 语义。
2. 增加至少一个会使三种规则产生不同结果的 fixture assertion。
3. 重新运行 holdout scoring，并更新 report、scoring JSON、visual manifest 与 hash。

这一步仍是 design experiment，不是 production implementation。

### 2. 非规范 space key：重要限制，需修复后重跑相关结果

`geometry-conflict` 中的 `TALL|ROUNDISH` 不是规范化 space key；当前排序后的 pair-key 查询使该 relation 进入 `not_available`。该状态被明确保留，且未修改输入，因此不否定整个 H2，但会限制对 `space_profile_rank` 在该 family 上的解释。

后续应统一 canonical key 或新增独立 fixture，并至少重跑受影响的 space-profile 视图。

## 不批准的结论

本审阅不批准以下结论：

- 任何 scale recipe winner；
- 任何 aggregation recipe winner；
- 数值 threshold 或 production selector；
- Bayesian prior、likelihood、posterior 或 ML 模型；
- deterministic strength/F1/Jaccard 被解释为概率、置信度或心理感知效度；
- H2 truth 被解释为人的正确分组或真实场景准确率。

## 下一步门槛

状态保持 **STOP FOR DESIGN REVIEW**，但可启动一个窄范围的 **aggregation semantics repair/re-run checkpoint**。该 checkpoint 完成并通过独立复核后，才进入完整的 scale/aggregation design review；在此之前不修改 `features/`、`adapters/`、`NeutralSceneV2`、公共 API 或 production selector。

## Provenance

- H2 report：`docs/project/evidence/d6-inferred-group-candidate-field-h2-report.md`
- H2 scoring：`docs/project/evidence/d6-inferred-group-candidate-field-h2-scoring.json`
- H2 experiment：`docs/project/evidence/d6-inferred-group-candidate-field-h2-experiment.json`
- H2 visual manifest：`docs/project/evidence/d6-inferred-group-candidate-field-h2-visual-manifest.json`
- aggregation implementation under review：`scripts/design/group_level/run_inferred_group_candidate_field_probe.py`

**STOP FOR DESIGN REVIEW**
