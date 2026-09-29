# Prompt: D6 inferred-group candidate-field design experiment

你负责为 D6 设计“inferred group candidate field”实验，不负责实现 production selector。

## 先读

1. `AGENTS.md`
2. `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
3. `docs/project/d6-overall-self-description-design-table.md`
4. `docs/project/d6-group-self-description-implementation-design-review.md`
5. `docs/superpowers/specs/2026-09-29-inferred-group-candidate-field-design.md`
6. `features/group_self_description.py`
7. `features/neutral_scene_views.py`
8. `features/scene_contract.py`
9. `docs/project/evidence/d6-bayesian-synthesis.md`
10. `docs/project/d6-inferred-group-design-experiment-record.md`

这是设计 checkpoint。不要修改 `features/`、`adapters/`、`NeutralSceneV2`、
`room_analysis_model`、公共 API 或生产测试。不要安装依赖。不要实现正式
candidate selector、唯一 partition、Bayesian production model 或 ML production
model。

## 目标

建立一个可审计的 deterministic design probe，比较以下机制：

- D0：evidence-only relation/local-neighborhood view；
- D1：使用同场景相对尺度和 persistence 的 multi-scale relation-field candidate view；
- B1：latent-membership Bayesian contract/feasibility record；本 checkpoint 不运行 posterior prototype；
- M1：仅在已有依赖可用时运行的 ML/community diagnostic。

若 B1/M1 需要安装依赖、补造 prior、补造训练标签或选择未批准的模型，记录
`not_run` 与原因，不自行替代模型。

## 冻结边界

- Authored furniture group 是唯一家具节点来源。
- context 只能改变空间/参照证据，不能成为家具节点。
- 空区是独立的空间场对象，可有多个 `space_role` candidates。
- relation evidence、space-field evidence、semantic evidence 必须分列。
- 普通类型差异是 soft negative；显式 `factual_properties["mutual_exclusion"]`
  是 candidate-level hard veto。
- missing、invalid、partial、not_available 不得互相改写，也不得填零。
- `co_membership_evidence` 不是 probability；Bayesian posterior 必须单独存放。
- 不使用固定的绝对距离阈值，不把最近邻自动当作同组。
- 不强制唯一 partition；必须能够表达 overlapping、weak、ambiguous、unassigned。
- 不把 inferred membership 写回 authored membership、route path 或 public model。

## Task 1：设计 fixture 与 truth

在 `scripts/design/group_level/` 创建确定性 fixture manifest，至少覆盖：

- gap jump：均匀—相对宽间隔—均匀；
- minority mixed：少数标签融入周边或形成局部势；
- geometry conflict：同类型但尺度/形状/方向不同；
- space conflict：相似家具组被空区、墙或 opening 分隔；
- bridge chain：A-B、B-C 支持而 A-C 弱；
- overlapping candidates；
- missing domain、missing geometry、invalid geometry、partial member；
- context perturbation；
- translation、rotation+frame、unit scale、ID/traversal reorder。

每个 fixture 单独保存 computational truth。truth 不得被 candidate mechanism 读取，
成员和 pair 不是独立统计样本。truth 是算法评估用的生成参数或结构标签，
不是人工标签，也不是心理真值；输出审计必须确认机制没有读取 truth。

## Task 2：运行 D0/D1 probe

复用 `describe_group_relations()` 的 evidence 输出。

D1 只能实验性地产生 candidate views：

- 必须并列报告具名 scale recipes：`relative_gap_rank`、
  `local_persistence_window`、`space_profile_rank`；每个 recipe 保存参数和
  provenance，agent 不得默选 quantile、窗口宽度或 persistence 规则；
- 不能写死米数阈值；
- 保留完整 positive/negative vectors、space role refs、missingness、conflicts；
- candidate aggregation 也必须并列报告 `all_pairs`、`max_span`、`min_gap`、
  `complete_link_diagnostic` 等具名 recipe；不允许把其中一个偷偷选成正式规则；
- CC 只能作为 chaining diagnostic；complete-link/max-span 只能作为 bounded-cohesion
  对照；不得选为正式规则；
- 输出 candidate status、provenance 和 supporting observations；
- 不生成 production `formal_membership_edge`。

`co_membership_evidence`、positive/negative vectors 和 `space_role_refs` 必须
稳定排序，保留 channel/status/source refs；它们不是 probability。对每个
candidate 同时输出 `evidence_status` 与 `candidate_status`：invalid required
channel 必须是 `invalid + diagnostic_only`；partial 必须保留 reason；mutual-
exclusion veto 必须保留 source refs，即使最终是 `unassigned`。

## Task 3：记录 B1/M1 可行性边界

不要为了“比较算法”而虚构 Bayesian 或 ML 结果。

对 B1 至少记录：

- estimand 是 edge、membership 还是 role；
- prior、likelihood、spatial dependence 和 missingness 如何声明；
- 是否能表达 multimodality、低信息和不可辨识；
- 是否能做 synthetic calibration / posterior predictive check。

本 checkpoint B1 强制为 `not_run`，除非 owner 在新的设计记录中明确批准
estimand、prior、likelihood 和 spatial dependence；不得自行运行 posterior。

对 M1 至少记录：

- 输入特征和表示；
- 是否有训练目标或独立 computational truth；
- 对 hyperparameter、表示变化和 cluster 数的敏感性；
- 是否能保留 evidence provenance 和 ambiguous output。

没有预注册 feature representation、algorithm、hyperparameters、seed 和
validation target 时，M1 必须为 `not_run`；即使运行，也只能是
`diagnostic_only`，不得选择“最佳 clustering”作为结论。

## Task 4：输出实验记录

创建：

- `docs/project/evidence/d6-inferred-group-candidate-field-experiment.md`
- `docs/project/evidence/d6-inferred-group-candidate-field-experiment.json`
- `docs/project/evidence/d6-inferred-group-candidate-field-artifact-manifest.json`

实验记录必须区分：

- verified repository facts；
- design assumptions；
- observed probe outputs；
- interpretation；
- unresolved decisions；
- external evidence limits。

至少报告：

- invariance；
- reproducibility；
- overlapping/ambiguous/unassigned preservation；
- hard veto precedence；
- empty-space role separation；
- relative-scale sensitivity；
- missing/invalid propagation；
- explanation/provenance completeness；
- B1 的 calibration/identifiability（若运行）；
- dependency and computational limits。

## Task 5：验证与停止

运行适用的 design probe assertions、JSON 解析、`py_compile`、manifest hash 和：

```bash
git diff --check
```

审计修改范围：不得有 `features/`、`adapters/`、`test/`、依赖或公共 API 变更。

提交后停止并回报：

- changed files；
- 每个机制实际运行或 `not_run` 的原因；
- fixture/truth 数量；
- probe assertions；
- 未冻结的 selector 决策；
- 是否建议进入 implementation-design review。

遇到以下问题必须停止提问，不得自行补规格：candidate evidence 聚合、固定尺度、
空区 primary role、Bayesian prior/likelihood、ML 训练目标、唯一 partition、
production API 或 psych validity。

**STOP FOR DESIGN REVIEW**
