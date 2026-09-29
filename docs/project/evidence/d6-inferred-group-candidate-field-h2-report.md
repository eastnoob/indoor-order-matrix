# D6 H2 membership-level holdout recovery

日期：2026-09-29。状态：design-only repair/re-run，STOP FOR DESIGN REVIEW。

仅 `generalization_holdout`：8 family × seed 303/404 × 11 scale views × 5 aggregation views = 880 视图。
`development_reference` 仅调试；`replication_only`、`invariance_only` 未计分。B1、M1 = `not_run`。

## 硬门槛与解释边界

16/16 holdout 的 authored/context separation、veto、状态传播、
invariance/reproducibility、truth isolation 已通过。candidate probe 只读取 H1b fixture manifest 和已注册 recipe。
评分阶段单独读取 computational truth；此 truth 是 evaluation-side structural truth，非人的正确答案或心理效度。
singleton/unassigned、overlap、ambiguity 均保留在 candidates JSON；无 formal membership edge。

本 repair 分离 aggregation 语义：`selected_relation_connected` 保留选中的关系连通结构，`all_internal_pairs` 要求每个内部无序 pair 都 selected/available/computed-valid 且 gap 有限；`max_span` 实际检查候选内部最大 pairwise gap，
`complete_link_diagnostic` 保留 maximal-clique 对照，`min_gap` 仅保留 pair witness，不解释为 group partition。
`max_span` 的 gap 上界来自 gap-rank bound；其他 scale 用已选关系的最大 gap 作诊断参照，绝不把 space-profile bound 当作 gap。
独立 semantics fixture 断言三者输出不同；没有据此选择 winner、scale、threshold 或 production selector。
registry 已拆分 `selected_relation_connected` 与 `all_internal_pairs`；两者均为 design-only diagnostics，不选择 winner。
该文字与修订语义的冲突留待 design review；不把修订后的探索结果称为预注册规则验证。

`geometry-conflict` 保留 H1b 原始 `TALL|ROUNDISH` 字节。probe 查询在设计边界 canonicalize 为 `ROUNDISH|TALL`，
并保留 `source_pair_id` 与 `key_normalized` provenance；受影响的 `space_profile_rank` 结果已重算。
seed 303 的 q=.5/.75 profile bound 从 .72146709/.72146709 变为 .534910515/.6281888025；
seed 404 从 .66264227/.66264227 变为 .490664895/.5766535825。两 seed 的 selected relation 均仍为 `CUBE|TALL`。

## 分层结果

完整 880 行含 family、seed、scale 参数、aggregation、四类 output evidence status 与 truth-member status。
每行记录 pairwise precision/recall/F1、每个 truth set 对所有 emitted set 的 Jaccard 分布、
member/ambiguous-overlapping/unassigned coverage、candidate status counts 与 veto diagnostics。
空 truth 或空预测的无定义指标写 `null`，不伪装为 0。下表 F1 是两 seed、同一 recipe 类全部注册参数的范围；
仅描述差异，不是 winner 排名或验收阈值。

| Family | Scale recipe | Aggregation recipe | F1 range | Output patterns |
|---|---|---|---|---:|
| bridge-chain | `relative_gap_rank` | `selected_relation_connected` | 0.500–0.800 | 2 |
| bridge-chain | `relative_gap_rank` | `all_internal_pairs` | 0.667–1.000 | 3 |
| bridge-chain | `relative_gap_rank` | `complete_link_diagnostic` | 0.667–1.000 | 3 |
| bridge-chain | `relative_gap_rank` | `max_span` | 0.667–1.000 | 3 |
| bridge-chain | `relative_gap_rank` | `min_gap` | 0.667–1.000 | 3 |
| bridge-chain | `local_persistence_window` | `selected_relation_connected` | 0.500–0.800 | 3 |
| bridge-chain | `local_persistence_window` | `all_internal_pairs` | 0.500–0.800 | 3 |
| bridge-chain | `local_persistence_window` | `complete_link_diagnostic` | 0.500–0.800 | 3 |
| bridge-chain | `local_persistence_window` | `max_span` | 0.500–0.800 | 3 |
| bridge-chain | `local_persistence_window` | `min_gap` | 0.500–0.800 | 3 |
| bridge-chain | `space_profile_rank` | `selected_relation_connected` | 0.667–0.800 | 2 |
| bridge-chain | `space_profile_rank` | `all_internal_pairs` | 0.667–1.000 | 2 |
| bridge-chain | `space_profile_rank` | `complete_link_diagnostic` | 0.667–1.000 | 2 |
| bridge-chain | `space_profile_rank` | `max_span` | 0.667–1.000 | 2 |
| bridge-chain | `space_profile_rank` | `min_gap` | 0.667–1.000 | 2 |
| context-perturbation | `relative_gap_rank` | `selected_relation_connected` | 1.000–1.000 | 1 |
| context-perturbation | `relative_gap_rank` | `all_internal_pairs` | 1.000–1.000 | 1 |
| context-perturbation | `relative_gap_rank` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| context-perturbation | `relative_gap_rank` | `max_span` | 1.000–1.000 | 1 |
| context-perturbation | `relative_gap_rank` | `min_gap` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `selected_relation_connected` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `all_internal_pairs` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `max_span` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `min_gap` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `selected_relation_connected` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `all_internal_pairs` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `max_span` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `min_gap` | 1.000–1.000 | 1 |
| gap-jump | `relative_gap_rank` | `selected_relation_connected` | 0.571–1.000 | 2 |
| gap-jump | `relative_gap_rank` | `all_internal_pairs` | 0.727–0.889 | 3 |
| gap-jump | `relative_gap_rank` | `complete_link_diagnostic` | 0.727–0.889 | 3 |
| gap-jump | `relative_gap_rank` | `max_span` | 0.727–0.889 | 3 |
| gap-jump | `relative_gap_rank` | `min_gap` | 0.727–0.889 | 3 |
| gap-jump | `local_persistence_window` | `selected_relation_connected` | 0.571–1.000 | 3 |
| gap-jump | `local_persistence_window` | `all_internal_pairs` | 0.667–1.000 | 3 |
| gap-jump | `local_persistence_window` | `complete_link_diagnostic` | 0.667–1.000 | 3 |
| gap-jump | `local_persistence_window` | `max_span` | 0.667–1.000 | 4 |
| gap-jump | `local_persistence_window` | `min_gap` | 0.667–1.000 | 3 |
| gap-jump | `space_profile_rank` | `selected_relation_connected` | 0.400–0.857 | 3 |
| gap-jump | `space_profile_rank` | `all_internal_pairs` | 0.400–0.667 | 3 |
| gap-jump | `space_profile_rank` | `complete_link_diagnostic` | 0.400–0.667 | 3 |
| gap-jump | `space_profile_rank` | `max_span` | 0.400–0.667 | 3 |
| gap-jump | `space_profile_rank` | `min_gap` | 0.400–0.667 | 3 |
| geometry-conflict | `relative_gap_rank` | `selected_relation_connected` | 0.667–0.800 | 2 |
| geometry-conflict | `relative_gap_rank` | `all_internal_pairs` | 0.667–1.000 | 2 |
| geometry-conflict | `relative_gap_rank` | `complete_link_diagnostic` | 0.667–1.000 | 2 |
| geometry-conflict | `relative_gap_rank` | `max_span` | 0.667–1.000 | 2 |
| geometry-conflict | `relative_gap_rank` | `min_gap` | 0.667–1.000 | 2 |
| geometry-conflict | `local_persistence_window` | `selected_relation_connected` | 0.667–0.800 | 2 |
| geometry-conflict | `local_persistence_window` | `all_internal_pairs` | 0.667–0.800 | 2 |
| geometry-conflict | `local_persistence_window` | `complete_link_diagnostic` | 0.667–0.800 | 2 |
| geometry-conflict | `local_persistence_window` | `max_span` | 0.667–0.800 | 2 |
| geometry-conflict | `local_persistence_window` | `min_gap` | 0.667–0.800 | 2 |
| geometry-conflict | `space_profile_rank` | `selected_relation_connected` | 0.667–0.667 | 1 |
| geometry-conflict | `space_profile_rank` | `all_internal_pairs` | 0.667–0.667 | 1 |
| geometry-conflict | `space_profile_rank` | `complete_link_diagnostic` | 0.667–0.667 | 1 |
| geometry-conflict | `space_profile_rank` | `max_span` | 0.667–0.667 | 1 |
| geometry-conflict | `space_profile_rank` | `min_gap` | 0.667–0.667 | 1 |
| minority-mixed | `relative_gap_rank` | `selected_relation_connected` | 0.667–1.000 | 2 |
| minority-mixed | `relative_gap_rank` | `all_internal_pairs` | 0.571–1.000 | 5 |
| minority-mixed | `relative_gap_rank` | `complete_link_diagnostic` | 0.571–1.000 | 5 |
| minority-mixed | `relative_gap_rank` | `max_span` | 0.571–1.000 | 5 |
| minority-mixed | `relative_gap_rank` | `min_gap` | 0.571–1.000 | 5 |
| minority-mixed | `local_persistence_window` | `selected_relation_connected` | 0.500–1.000 | 3 |
| minority-mixed | `local_persistence_window` | `all_internal_pairs` | 0.500–1.000 | 4 |
| minority-mixed | `local_persistence_window` | `complete_link_diagnostic` | 0.500–1.000 | 4 |
| minority-mixed | `local_persistence_window` | `max_span` | 0.500–1.000 | 4 |
| minority-mixed | `local_persistence_window` | `min_gap` | 0.500–1.000 | 4 |
| minority-mixed | `space_profile_rank` | `selected_relation_connected` | 0.500–1.000 | 3 |
| minority-mixed | `space_profile_rank` | `all_internal_pairs` | 0.500–0.800 | 3 |
| minority-mixed | `space_profile_rank` | `complete_link_diagnostic` | 0.500–0.800 | 3 |
| minority-mixed | `space_profile_rank` | `max_span` | 0.500–0.800 | 3 |
| minority-mixed | `space_profile_rank` | `min_gap` | 0.500–0.800 | 3 |
| missing-invalid | `relative_gap_rank` | `selected_relation_connected` | null | 1 |
| missing-invalid | `relative_gap_rank` | `all_internal_pairs` | null | 1 |
| missing-invalid | `relative_gap_rank` | `complete_link_diagnostic` | null | 1 |
| missing-invalid | `relative_gap_rank` | `max_span` | null | 1 |
| missing-invalid | `relative_gap_rank` | `min_gap` | null | 1 |
| missing-invalid | `local_persistence_window` | `selected_relation_connected` | null | 1 |
| missing-invalid | `local_persistence_window` | `all_internal_pairs` | null | 1 |
| missing-invalid | `local_persistence_window` | `complete_link_diagnostic` | null | 1 |
| missing-invalid | `local_persistence_window` | `max_span` | null | 1 |
| missing-invalid | `local_persistence_window` | `min_gap` | null | 1 |
| missing-invalid | `space_profile_rank` | `selected_relation_connected` | null | 1 |
| missing-invalid | `space_profile_rank` | `all_internal_pairs` | null | 1 |
| missing-invalid | `space_profile_rank` | `complete_link_diagnostic` | null | 1 |
| missing-invalid | `space_profile_rank` | `max_span` | null | 1 |
| missing-invalid | `space_profile_rank` | `min_gap` | null | 1 |
| overlapping-candidates | `relative_gap_rank` | `selected_relation_connected` | 0.667–0.800 | 3 |
| overlapping-candidates | `relative_gap_rank` | `all_internal_pairs` | 0.667–1.000 | 3 |
| overlapping-candidates | `relative_gap_rank` | `complete_link_diagnostic` | 0.667–1.000 | 3 |
| overlapping-candidates | `relative_gap_rank` | `max_span` | 0.667–1.000 | 3 |
| overlapping-candidates | `relative_gap_rank` | `min_gap` | 0.667–1.000 | 3 |
| overlapping-candidates | `local_persistence_window` | `selected_relation_connected` | 0.667–0.800 | 3 |
| overlapping-candidates | `local_persistence_window` | `all_internal_pairs` | 0.667–0.800 | 3 |
| overlapping-candidates | `local_persistence_window` | `complete_link_diagnostic` | 0.667–0.800 | 3 |
| overlapping-candidates | `local_persistence_window` | `max_span` | 0.667–0.800 | 3 |
| overlapping-candidates | `local_persistence_window` | `min_gap` | 0.667–0.800 | 3 |
| overlapping-candidates | `space_profile_rank` | `selected_relation_connected` | 0.667–0.800 | 2 |
| overlapping-candidates | `space_profile_rank` | `all_internal_pairs` | 0.667–1.000 | 2 |
| overlapping-candidates | `space_profile_rank` | `complete_link_diagnostic` | 0.667–1.000 | 2 |
| overlapping-candidates | `space_profile_rank` | `max_span` | 0.667–1.000 | 2 |
| overlapping-candidates | `space_profile_rank` | `min_gap` | 0.667–1.000 | 2 |
| space-conflict | `relative_gap_rank` | `selected_relation_connected` | 1.000–1.000 | 2 |
| space-conflict | `relative_gap_rank` | `all_internal_pairs` | 1.000–1.000 | 1 |
| space-conflict | `relative_gap_rank` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| space-conflict | `relative_gap_rank` | `max_span` | 1.000–1.000 | 1 |
| space-conflict | `relative_gap_rank` | `min_gap` | 1.000–1.000 | 1 |
| space-conflict | `local_persistence_window` | `selected_relation_connected` | 1.000–1.000 | 2 |
| space-conflict | `local_persistence_window` | `all_internal_pairs` | 1.000–1.000 | 2 |
| space-conflict | `local_persistence_window` | `complete_link_diagnostic` | 1.000–1.000 | 2 |
| space-conflict | `local_persistence_window` | `max_span` | 1.000–1.000 | 2 |
| space-conflict | `local_persistence_window` | `min_gap` | 0.667–1.000 | 2 |
| space-conflict | `space_profile_rank` | `selected_relation_connected` | 1.000–1.000 | 1 |
| space-conflict | `space_profile_rank` | `all_internal_pairs` | 1.000–1.000 | 1 |
| space-conflict | `space_profile_rank` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| space-conflict | `space_profile_rank` | `max_span` | 1.000–1.000 | 1 |
| space-conflict | `space_profile_rank` | `min_gap` | 1.000–1.000 | 1 |

## Recipe disagreement

- `bridge_chain:holdout:303`：55 视图，9 种 candidate-set 输出。
- `bridge_chain:holdout:404`：55 视图，9 种 candidate-set 输出。
- `context_perturbation:holdout:303`：55 视图，1 种 candidate-set 输出。
- `context_perturbation:holdout:404`：55 视图，1 种 candidate-set 输出。
- `gap_jump:holdout:303`：55 视图，14 种 candidate-set 输出。
- `gap_jump:holdout:404`：55 视图，15 种 candidate-set 输出。
- `geometry_conflict:holdout:303`：55 视图，5 种 candidate-set 输出。
- `geometry_conflict:holdout:404`：55 视图，5 种 candidate-set 输出。
- `minority_mixed:holdout:303`：55 视图，10 种 candidate-set 输出。
- `minority_mixed:holdout:404`：55 视图，8 种 candidate-set 输出。
- `missing_invalid:holdout:303`：55 视图，1 种 candidate-set 输出。
- `missing_invalid:holdout:404`：55 视图，1 种 candidate-set 输出。
- `overlapping_candidates:holdout:303`：55 视图，5 种 candidate-set 输出。
- `overlapping_candidates:holdout:404`：55 视图，4 种 candidate-set 输出。
- `space_conflict:holdout:303`：55 视图，3 种 candidate-set 输出。
- `space_conflict:holdout:404`：55 视图，3 种 candidate-set 输出。

全部分歧与每条 emitted set 保存在 scoring JSON；aggregation difference assertion 已通过。
`candidate_relation_ids` 保留 emitted structure 的 selected pair evidence；`min_gap` 明确为 pair witness。

## Provenance 与范围

- 输入及 candidate JSON 的 SHA-256 见 scoring JSON `input_hashes`。
- D1 recipe registry 与 probe 在起始 Git 状态为未跟踪文件；本提交将纳入两者，确保复现 H2。
- 5 张确定性 SVG 的路径、大小和 SHA-256 见 visual manifest；每张图标注 geometry/variable diagnostic only。Blender 本 checkpoint 未运行。
- 无数值 threshold、recipe winner、production selector、公共 API 或依赖变更。

**STOP FOR DESIGN REVIEW**
