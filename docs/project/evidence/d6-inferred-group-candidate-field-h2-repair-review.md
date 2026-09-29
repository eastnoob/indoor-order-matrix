# D6 H2 Repair Review

日期：2026-09-29
审阅提交：`ed2f825c2a849e7553be4d32cef9b94c486e3aee`
范围：H2 design-only repair/re-run；不进入 production implementation。

## 总体裁决

**ACCEPT WITH LIMITATIONS；批准进入下一次 design review。**

本次 repair 已解决上一轮的主要实验缺陷：三个 aggregation recipe 不再共用同一 maximal-clique 实现，且有独立 fixture 证明它们可产生不同结果。H2 仍然只是 design evidence，不产生 production selector、winner、threshold、Bayesian/ML 模型或心理效度结论。

## 逐项裁决

| 项目 | 裁决 | 理由 |
|---|---|---|
| 16 个 generalization holdout、704 views | approved | 评分范围保持不变，未混入 development、replication-only 或 invariance-only。 |
| 16/16 hard gates | approved | authored/context separation、hard veto、状态传播、invariance/reproducibility、truth isolation 均通过。 |
| aggregation semantics repair | approved as exploratory | `all_pairs`、`max_span`、`complete_link_diagnostic` 已分别执行连通结构、最大 gap 约束和 maximal-clique 对照；`min_gap` 保持 pair witness。 |
| aggregation difference assertion | approved | 独立 semantics fixture 证明三种 aggregation 输出可区分。 |
| canonical unordered space-key lookup | approved | 保留原始 `TALL|ROUNDISH` 字节，并以 `source_pair_id` 与 `key_normalized` 记录规范化来源；受影响 space-profile 结果已重算。 |
| scale recipe comparison | approved as exploratory | 三个 scale recipe 并行保留；未选择 winner 或 threshold。 |
| SVG diagnostics | approved | 作为几何/变量诊断使用；不构成心理效度或真实场景准确率证据。Blender 仍不必在此 checkpoint 运行。 |
| B1 / M1 / production selector | deferred | 均明确为 `not_run` 或 `not_modified`。 |

## 必须在下一次 design review 处理的问题

### Registry 语义文字不一致：REVISE BEFORE FREEZE

原 registry 对 `all_pairs` 的文字仍写作“all internal pair keys must be selected”，而本 repair 的有效实验语义是“selected-relation connected structure”。报告已经显式记录该差异，因此不影响本次 repair 作为实验运行；但在下一次 design review 中必须做出明确裁决：

1. 将 registry 文字改为连通结构语义；或
2. 恢复 all-internal-pair 语义并重新设计 probe；或
3. 将两者拆为不同 recipe id，避免同名异义。

在该问题裁决前，不得把 `all_pairs` 写入 production contract，也不得据 H2 结果选择 aggregation winner。

## 不批准的结论

- 不批准任何 scale 或 aggregation winner；
- 不批准数值 threshold 或 production selector；
- 不批准将 deterministic support、F1、Jaccard 或 candidate status 解释为概率、置信度或心理感知效度；
- 不批准把 evaluation-side computational truth 当作人的正确分组；
- 不批准进入 `features/`、`adapters/`、`NeutralSceneV2`、公共 API 或 Bayesian/ML 实现。

## 下一步

批准进入下一次 design review，范围仅限：

1. 裁决 registry 与 `all_pairs` 的正式语义；
2. 比较三个 scale recipe 与四个 aggregation recipe 的输出结构和失败模式；
3. 明确哪些结果仍保持 candidate-field / diagnostic-only；
4. 决定是否需要新的 fixture 或实验后，才考虑 implementation design。

**STOP FOR DESIGN REVIEW**
