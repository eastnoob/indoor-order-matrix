# D6 H2 contract repair — Checkpoint A

日期：2026-09-29。执行范围：计划第 4 节 A1–A8。基线 HEAD：`2c0f14d1dc044bf255c1ebfdb1052149d71e3ab8`。本报告是 **design-only 执行记录与复核建议**，不是 owner approval、production contract 或 Checkpoint B 授权。

## A1. 输入与 owner 要求

复用工作区已有未提交的 880-row H2 repair；没有从旧 704-row commit 重做。审阅了当前 registry、probe、H2 runner、aggregation/status/canonical-key fixtures、H2 report/review、owner decision。当前工作树的设计输入 hash 由 `d6-inferred-group-candidate-field-h2-candidates.json` 的 `candidate_probe_inputs`、H2 repair artifact manifest 及 visual manifest 记录；`verify` 复核其源 hash。工作区另有无关及后续阶段文件，未认领。

已满足 owner 的设计修订方向：`selected_relation_connected` 与 `all_internal_pairs` 分开；五种 aggregation 和三种 scale 并列；严格内部 pair 规则、reverse-only key 规范化与双来源 conflict provenance、无 formal membership edge、truth isolation、overlap 与 singleton 输出均有诊断证据。`min_gap` 仅为 pair witness。未满足的冻结条件：最终 candidate estimand、跨状态/冲突传播政策、ambiguous 的正式判定、space channel 与 barrier 的生产 requiredness、生产 acceptance rule 尚待 owner 裁决；implementation design 继续 DEFER。

## A2. Recipe channel contract

`selected` 表示当前 scale view 选中了 relation key；`eligible` 表示该 relation 还满足相应 aggregation 的数据要求。两者不等价。没有被选中的 valid pair 也不能进入 `all_internal_pairs`。

| Recipe | 必需输入 | 可选/诊断输入 | 当前输出语义 |
|---|---|---|---|
| `relative_gap_rank` | relation `computed`、有限 normalized gap；inclusive-linear quantile | space、semantic、barrier、veto | 选出 gap 不高于当前相对 bound 的 pair |
| `local_persistence_window` | 同上，双端邻居 rank、声明的 window/persistence | 同上 | 局部稳定 pair；等 gap 按 ID 排序 |
| `space_profile_rank` | space record `computed`、有限 profile；当前相对 bound | 几何 gap、semantic、barrier、veto | 选出 profile 不低于 bound 的 pair；conflict/unavailable 不参与 rank |
| `selected_relation_connected` | selected relation keys、authored group IDs | relation 数值和状态用于证据传播 | selected graph 的多节点连通分量；可显示 selected-but-ineligible 边 |
| `all_internal_pairs` | 每个内部无序 pair 均 selected、有 relation record、`computed` 且 normalized gaps 有限 | space/semantic 负证据 | 严格合法的 maximal member sets；缺一 pair 即不扩大集合 |
| `complete_link_diagnostic` | selected pair graph | relation 状态、gap | selected graph maximal cliques；仅诊断 |
| `max_span` | selected graph 连通、当前 gap bound、全部内部 pair 的可用 gap | space/semantic 负证据 | 有界跨度的 maximal connected sets；仍是诊断 |
| `min_gap` | selected pair key 及现存 relation record | gap、space/semantic 证据 | 二成员 pair witness；不作 group partition |

三种 scale 的相对参数来自已注册 registry；本次没有选择 winner、默认尺度或阈值。shared authored member 仅是 dependency diagnostic，不能自动证明两个家具组合并。

## A3. Relation/candidate 状态矩阵

| 证据情形 | Relation / channel 层 | Candidate 层及 strict `all_internal_pairs` | 规则 |
|---|---|---|---|
| selected key 缺 relation record (`missing`) | 保留 `required_relation_absent`；无数值 | connected diagnostic 为 `partial`；strict 排除；无其他覆盖则 singleton `unassigned` | unknown 不填 0 |
| `invalid` | 原状态与原因保留 | connected 可见但 `diagnostic_only`，evidence `invalid`；strict 排除 | invalid 不改写 missing |
| `partial` | 原状态与缺失原因保留 | connected `partial`；strict 排除 | 不升级 computed |
| `not_available` | 未测量通道保持不可用 | 若 selected，connected `partial` 且 strict 排除；无 selected edge 则 singleton `unassigned` / evidence `not_available` | 不当 zero/clear |
| canonical/reverse `conflict` | 保留全部 source keys/records；profile `null` | space-profile scale 不选择该 pair；其他几何诊断保留 conflict 负证据 | 不静默任选一方 |
| 普通 semantic disagreement | soft negative evidence | 不直接 veto | 不等于 explicit mutual exclusion |
| explicit mutual exclusion | source refs 保留 | candidate-level veto diagnostic，不改 authored membership | 不由普通标签差异推断 |

Required channel 缺失阻止相应 scale/strict recipe 计算；optional channel 缺失保留缺失状态和 provenance，不改变已计算的其他通道。当前矩阵是待审的诊断建议，尤其 conflict 对最终 candidate selector 的策略未冻结。

## A4–A6. 候选规则、限制和最小反例

Connected recipe 只求 selected graph 连通分量，单 view 内分量不重叠，但 chaining 可以合并远端节点。Strict all-internal 与 complete-link 分别在 eligible graph 和 selected graph 上求 maximal cliques；二者可产生重叠 maximal sets。`max_span` 在声明 bound 内枚举 maximal connected sets，也可重叠。`min_gap` 每条 selected pair 独立输出 witness，不定义 maximal group。多个合法 maximal sets 原样并列；同一成员可在多个候选中，view/candidate 的 ambiguity 仅为诊断标记。无多成员候选覆盖的 authored node 显式输出 `unassigned` singleton，`candidate_relation_ids=[]`、evidence `not_available`。所有输出的 `formal_membership_edge=false`。

已执行的最小断言包括：链 `A-B-C-D` 下 connected 为四节点、strict 为三个 pair、`max_span` 为两个重叠三节点；分离 `A-B`/`C-D` 同时保留两个 maximal sets；selected-but-ineligible 的 missing/invalid/partial/not_available 在真实 `_aggregate()` 输出中留在 connected 诊断并被 strict 排除；无 relation 的单节点保留；reverse-only `TALL|PLAIN` 规范化，冲突的 `TALL|ROUNDISH`/`ROUNDISH|TALL` 保留两条原始记录和 `null` profile；invalid 数值 gap 与 conflict profile 不进入 scale rank。

`_numeric_gap([0.2, 0.8]) == 0.2` 是 **minimum member-gap diagnostic shortcut**，不是正式 group gap。等 gap 的 A→B/C 按 ID 排为 B=1、C=2；仅把 B 重命名为 Z 后变为 C=1、Z=2，说明当前 tie 排序只保证确定性，不具备 ID-rename invariance。进入生产设计前须定义 gap 聚合与 tie 语义。上述反例均为 synthetic/design self-check，不能证明真实家具分组准确率或心理效度。

## A7. 探索性重跑与范围核验

本次输入/规则及状态传播相较旧提交均已改变，因此以下是 **exploratory re-run**，不是预注册效果验证。

| 命令 | 结果 |
|---|---|
| `pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py probe` | exit 0；32 replicas、16 holdout、11 scale views、5 aggregation views |
| 同脚本 `score` | exit 0；880 holdout scoring rows、16 hard-gate records |
| 同脚本 `visual` | exit 0；5 SVG |
| 同脚本 `report`、`record`、`manifest`、`verify` | 均 exit 0；`verify` 核对 JSON/schema、880 rows、16 hard gates、source hashes、5 SVG/XML hashes |
| `pixi run pytest test/test_group_self_description.py test/test_canonical_layout_contract.py test/test_canonical_layout_geometry.py -q` | exit 0；52 passed |
| `git diff --check` | exit 0（仅有 LF→CRLF 提示） |

五张 SVG：`d6-h2-gap-jump-seed303.svg`、`d6-h2-bridge-chain-seed303.svg`、`d6-h2-overlapping-candidates-seed303.svg`、`d6-h2-space-conflict-seed303.svg`、`d6-h2-missing-invalid-seed303.svg`，均位于 `docs/project/evidence/`；路径、bytes、SHA-256 与 recipe/scale 见 visual manifest。评分侧读取 evaluation-side computational truth；probe 的 `truth_consumed=false`。F1 只描述 synthetic holdout 结构，不能选择 winner。B1/M1 均 `not_run`。

## A8. 交回总控的逐项建议

| 项目 | 建议 | 审阅重点 |
|---|---|---|
| 两个 aggregation id 分拆、五种并列 diagnostics、三种并列 scale | **APPROVE** design-only 方向 | 检查 registry/实现/反例一致；不批准 winner |
| strict `all_internal_pairs`、selected/eligible、singleton/overlap 诊断 | **APPROVE** 本次设计反例作为审阅材料 | maximal 与 ambiguous 的正式输出契约仍待 owner 决定 |
| 最终 relation/candidate status matrix、conflict 和 required/optional 传播 | **REVISE** before contract freeze | 本次反例已覆盖关键路径；需 owner 决定生产 estimand 与缺失/冲突政策 |
| minimum member-gap、ID tie policy | **REVISE** before production | 当前限制已显式记录；不能宣称 group gap 或重命名不变性 |
| production selector、implementation design、Bayesian/ML、Checkpoint B | **DEFER** | 本次 A 执行通过不构成 owner approval 或下一阶段授权 |

范围审计：本次只改 candidate-field design probe/runner/fixtures 与对应 H2 evidence/SVG，并新增本报告。未修改生产代码、正式测试、API、依赖、源 IFC；未执行 Blender/IFC/自动 space。owner decision 保持原样。提交使用明确路径；无关 dirty/untracked 文件不纳入。

STOP FOR CONTRACT REVIEW
