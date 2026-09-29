# D6 H2 membership-level holdout recovery

日期：2026-09-29。状态：design-only，STOP FOR DESIGN REVIEW。

仅 `generalization_holdout`：8 family × seed 303/404 × 11 scale views × 4 aggregation views = 704 视图。
`development_reference` 仅调试；`replication_only`、`invariance_only` 未计分。B1、M1 = `not_run`。

## 硬门槛与解释边界

16/16 holdout 的 authored/context separation、veto、状态传播、
invariance/reproducibility、truth isolation 已通过。candidate probe 只读取 H1b fixture manifest 和已注册 recipe。
评分阶段单独读取 computational truth；此 truth 是 evaluation-side structural truth，非人的正确答案或心理效度。
singleton/unassigned、overlap、ambiguity 均保留在 candidates JSON；无 formal membership edge。

`geometry-conflict` 输入含非规范键 `TALL|ROUNDISH`；现有 probe 用排序后的 pair key 查询，
因此这条 space relation 在该 family 被视为 `not_available`。H2 未修改输入或 recipe。

## 分层结果

完整 704 行含 family、seed、scale 参数、aggregation、四类 output evidence status 与 truth-member status。
每行记录 pairwise precision/recall/F1、每个 truth set 对所有 emitted set 的 Jaccard 分布、
member/ambiguous-overlapping/unassigned coverage、candidate status counts 与 veto diagnostics。
空 truth 或空预测的无定义指标写 `null`，不伪装为 0。下表 F1 是两 seed、同一 recipe 类全部注册参数的范围；
仅描述差异，不是 winner 排名或验收阈值。

| Family | Scale recipe | Aggregation recipe | F1 range | Output patterns |
|---|---|---|---|---:|
| bridge-chain | `relative_gap_rank` | `all_pairs` | 0.667–1.000 | 3 |
| bridge-chain | `relative_gap_rank` | `max_span` | 0.667–1.000 | 3 |
| bridge-chain | `relative_gap_rank` | `min_gap` | 0.667–1.000 | 3 |
| bridge-chain | `relative_gap_rank` | `complete_link_diagnostic` | 0.667–1.000 | 3 |
| bridge-chain | `local_persistence_window` | `all_pairs` | 0.500–0.800 | 3 |
| bridge-chain | `local_persistence_window` | `max_span` | 0.500–0.800 | 3 |
| bridge-chain | `local_persistence_window` | `min_gap` | 0.500–0.800 | 3 |
| bridge-chain | `local_persistence_window` | `complete_link_diagnostic` | 0.500–0.800 | 3 |
| bridge-chain | `space_profile_rank` | `all_pairs` | 0.667–1.000 | 2 |
| bridge-chain | `space_profile_rank` | `max_span` | 0.667–1.000 | 2 |
| bridge-chain | `space_profile_rank` | `min_gap` | 0.667–1.000 | 2 |
| bridge-chain | `space_profile_rank` | `complete_link_diagnostic` | 0.667–1.000 | 2 |
| context-perturbation | `relative_gap_rank` | `all_pairs` | 1.000–1.000 | 1 |
| context-perturbation | `relative_gap_rank` | `max_span` | 1.000–1.000 | 1 |
| context-perturbation | `relative_gap_rank` | `min_gap` | 1.000–1.000 | 1 |
| context-perturbation | `relative_gap_rank` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `all_pairs` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `max_span` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `min_gap` | 1.000–1.000 | 1 |
| context-perturbation | `local_persistence_window` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `all_pairs` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `max_span` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `min_gap` | 1.000–1.000 | 1 |
| context-perturbation | `space_profile_rank` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| gap-jump | `relative_gap_rank` | `all_pairs` | 0.727–0.889 | 3 |
| gap-jump | `relative_gap_rank` | `max_span` | 0.727–0.889 | 3 |
| gap-jump | `relative_gap_rank` | `min_gap` | 0.727–0.889 | 3 |
| gap-jump | `relative_gap_rank` | `complete_link_diagnostic` | 0.727–0.889 | 3 |
| gap-jump | `local_persistence_window` | `all_pairs` | 0.667–1.000 | 3 |
| gap-jump | `local_persistence_window` | `max_span` | 0.667–1.000 | 3 |
| gap-jump | `local_persistence_window` | `min_gap` | 0.667–1.000 | 3 |
| gap-jump | `local_persistence_window` | `complete_link_diagnostic` | 0.667–1.000 | 3 |
| gap-jump | `space_profile_rank` | `all_pairs` | 0.400–0.667 | 3 |
| gap-jump | `space_profile_rank` | `max_span` | 0.400–0.667 | 3 |
| gap-jump | `space_profile_rank` | `min_gap` | 0.400–0.667 | 3 |
| gap-jump | `space_profile_rank` | `complete_link_diagnostic` | 0.400–0.667 | 3 |
| geometry-conflict | `relative_gap_rank` | `all_pairs` | 0.667–1.000 | 2 |
| geometry-conflict | `relative_gap_rank` | `max_span` | 0.667–1.000 | 2 |
| geometry-conflict | `relative_gap_rank` | `min_gap` | 0.667–1.000 | 2 |
| geometry-conflict | `relative_gap_rank` | `complete_link_diagnostic` | 0.667–1.000 | 2 |
| geometry-conflict | `local_persistence_window` | `all_pairs` | 0.667–0.800 | 2 |
| geometry-conflict | `local_persistence_window` | `max_span` | 0.667–0.800 | 2 |
| geometry-conflict | `local_persistence_window` | `min_gap` | 0.667–0.800 | 2 |
| geometry-conflict | `local_persistence_window` | `complete_link_diagnostic` | 0.667–0.800 | 2 |
| geometry-conflict | `space_profile_rank` | `all_pairs` | 0.667–0.667 | 1 |
| geometry-conflict | `space_profile_rank` | `max_span` | 0.667–0.667 | 1 |
| geometry-conflict | `space_profile_rank` | `min_gap` | 0.667–0.667 | 1 |
| geometry-conflict | `space_profile_rank` | `complete_link_diagnostic` | 0.667–0.667 | 1 |
| minority-mixed | `relative_gap_rank` | `all_pairs` | 0.571–1.000 | 5 |
| minority-mixed | `relative_gap_rank` | `max_span` | 0.571–1.000 | 5 |
| minority-mixed | `relative_gap_rank` | `min_gap` | 0.571–1.000 | 5 |
| minority-mixed | `relative_gap_rank` | `complete_link_diagnostic` | 0.571–1.000 | 5 |
| minority-mixed | `local_persistence_window` | `all_pairs` | 0.500–1.000 | 4 |
| minority-mixed | `local_persistence_window` | `max_span` | 0.500–1.000 | 4 |
| minority-mixed | `local_persistence_window` | `min_gap` | 0.500–1.000 | 4 |
| minority-mixed | `local_persistence_window` | `complete_link_diagnostic` | 0.500–1.000 | 4 |
| minority-mixed | `space_profile_rank` | `all_pairs` | 0.500–0.800 | 3 |
| minority-mixed | `space_profile_rank` | `max_span` | 0.500–0.800 | 3 |
| minority-mixed | `space_profile_rank` | `min_gap` | 0.500–0.800 | 3 |
| minority-mixed | `space_profile_rank` | `complete_link_diagnostic` | 0.500–0.800 | 3 |
| missing-invalid | `relative_gap_rank` | `all_pairs` | null | 1 |
| missing-invalid | `relative_gap_rank` | `max_span` | null | 1 |
| missing-invalid | `relative_gap_rank` | `min_gap` | null | 1 |
| missing-invalid | `relative_gap_rank` | `complete_link_diagnostic` | null | 1 |
| missing-invalid | `local_persistence_window` | `all_pairs` | null | 1 |
| missing-invalid | `local_persistence_window` | `max_span` | null | 1 |
| missing-invalid | `local_persistence_window` | `min_gap` | null | 1 |
| missing-invalid | `local_persistence_window` | `complete_link_diagnostic` | null | 1 |
| missing-invalid | `space_profile_rank` | `all_pairs` | null | 1 |
| missing-invalid | `space_profile_rank` | `max_span` | null | 1 |
| missing-invalid | `space_profile_rank` | `min_gap` | null | 1 |
| missing-invalid | `space_profile_rank` | `complete_link_diagnostic` | null | 1 |
| overlapping-candidates | `relative_gap_rank` | `all_pairs` | 0.667–1.000 | 3 |
| overlapping-candidates | `relative_gap_rank` | `max_span` | 0.667–1.000 | 3 |
| overlapping-candidates | `relative_gap_rank` | `min_gap` | 0.667–1.000 | 3 |
| overlapping-candidates | `relative_gap_rank` | `complete_link_diagnostic` | 0.667–1.000 | 3 |
| overlapping-candidates | `local_persistence_window` | `all_pairs` | 0.667–0.800 | 3 |
| overlapping-candidates | `local_persistence_window` | `max_span` | 0.667–0.800 | 3 |
| overlapping-candidates | `local_persistence_window` | `min_gap` | 0.667–0.800 | 3 |
| overlapping-candidates | `local_persistence_window` | `complete_link_diagnostic` | 0.667–0.800 | 3 |
| overlapping-candidates | `space_profile_rank` | `all_pairs` | 0.667–1.000 | 2 |
| overlapping-candidates | `space_profile_rank` | `max_span` | 0.667–1.000 | 2 |
| overlapping-candidates | `space_profile_rank` | `min_gap` | 0.667–1.000 | 2 |
| overlapping-candidates | `space_profile_rank` | `complete_link_diagnostic` | 0.667–1.000 | 2 |
| space-conflict | `relative_gap_rank` | `all_pairs` | 1.000–1.000 | 1 |
| space-conflict | `relative_gap_rank` | `max_span` | 1.000–1.000 | 1 |
| space-conflict | `relative_gap_rank` | `min_gap` | 1.000–1.000 | 1 |
| space-conflict | `relative_gap_rank` | `complete_link_diagnostic` | 1.000–1.000 | 1 |
| space-conflict | `local_persistence_window` | `all_pairs` | 1.000–1.000 | 2 |
| space-conflict | `local_persistence_window` | `max_span` | 1.000–1.000 | 2 |
| space-conflict | `local_persistence_window` | `min_gap` | 0.667–1.000 | 2 |
| space-conflict | `local_persistence_window` | `complete_link_diagnostic` | 1.000–1.000 | 2 |
| space-conflict | `space_profile_rank` | `all_pairs` | 1.000–1.000 | 1 |
| space-conflict | `space_profile_rank` | `max_span` | 1.000–1.000 | 1 |
| space-conflict | `space_profile_rank` | `min_gap` | 1.000–1.000 | 1 |
| space-conflict | `space_profile_rank` | `complete_link_diagnostic` | 1.000–1.000 | 1 |

## Recipe disagreement

- `bridge_chain:holdout:303`：44 视图，9 种 candidate-set 输出。
- `bridge_chain:holdout:404`：44 视图，9 种 candidate-set 输出。
- `context_perturbation:holdout:303`：44 视图，1 种 candidate-set 输出。
- `context_perturbation:holdout:404`：44 视图，1 种 candidate-set 输出。
- `gap_jump:holdout:303`：44 视图，12 种 candidate-set 输出。
- `gap_jump:holdout:404`：44 视图，12 种 candidate-set 输出。
- `geometry_conflict:holdout:303`：44 视图，5 种 candidate-set 输出。
- `geometry_conflict:holdout:404`：44 视图，5 种 candidate-set 输出。
- `minority_mixed:holdout:303`：44 视图，9 种 candidate-set 输出。
- `minority_mixed:holdout:404`：44 视图，8 种 candidate-set 输出。
- `missing_invalid:holdout:303`：44 视图，2 种 candidate-set 输出。
- `missing_invalid:holdout:404`：44 视图，2 种 candidate-set 输出。
- `overlapping_candidates:holdout:303`：44 视图，5 种 candidate-set 输出。
- `overlapping_candidates:holdout:404`：44 视图，4 种 candidate-set 输出。
- `space_conflict:holdout:303`：44 视图，3 种 candidate-set 输出。
- `space_conflict:holdout:404`：44 视图，3 种 candidate-set 输出。

全部分歧与每条 emitted set 保存在 scoring JSON；`all_pairs`、`max_span`、`complete_link_diagnostic`
在现有 D1 probe 中共用 maximal-clique 枚举，部分输入因此输出相同。该现象不是聚合规则等价性的证明。

## Provenance 与范围

- 输入及 candidate JSON 的 SHA-256 见 scoring JSON `input_hashes`。
- 现有 D1 recipe registry 与 probe 在起始 Git 状态为未跟踪文件；复现本提交须保留其记录的字节与 hash。
- 5 张确定性 SVG 的路径、大小和 SHA-256 见 visual manifest。Blender 可选诊断未运行。
- 无数值 threshold、recipe winner、production selector、公共 API 或依赖变更。

**STOP FOR DESIGN REVIEW**
