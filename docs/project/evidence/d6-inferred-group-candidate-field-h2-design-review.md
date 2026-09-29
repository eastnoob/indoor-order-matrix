# D6 inferred-group candidate-field H2 design review

日期：2026-09-29。范围：仅 design-probe、registry、fixtures 和 evidence；不进入 production implementation。

**总裁决：REVISE。停止在 design review。**

H2 probe 已完成 aggregation 语义拆分并重跑 holdout scoring：16 个 generalization holdout、11 个 scale views、5 个 aggregation views，共 880 个 scoring rows；16/16 hard gates 通过。该结果足以批准并列 diagnostic evidence 的结构和 provenance，不足以冻结 candidate selector、threshold、scale winner、aggregation winner 或心理效度解释。

## Findings

1. `all_pairs` 原来同时承载两个不兼容含义：probe 实际输出 selected-relation graph 的 connected structure，而 registry 文字描述 all internal pair requirement。registry、probe、H2 runner 现已拆为 `selected_relation_connected` 和 `all_internal_pairs`，不再同名异义。
2. 新 aggregation semantics fixture 保留 selected chain `A-B`、`B-C`、`C-D`，显式保留未选 `A-C`、`A-D`、`B-D`，并覆盖 missing、invalid、partial internal-pair 变体。fixture 同时记录 expected membersets、relation ids、status 和 overlap policy。
3. `all_internal_pairs` 的设计语义是：候选成员集合中的每个无序内部 pair 都必须是 selected、存在 available relation record、状态为 computed/valid，并有有限 normalized gap。缺少 required pair 时不静默通过；合法的 maximal pair sets 可以重叠，未覆盖成员保留 singleton/unassigned。
4. status matrix 已区分 relation 无法计算、required pair 不完整导致 candidate partial、无内部 relation 的 singleton/unassigned；`missing`、`not_available`、`partial` 不转换为数值 0，也不伪装为 computed。
5. canonical space-key fixture 现在覆盖 reverse-only source 和 canonical/reverse 双来源冲突。probe 保留 canonical pair、全部原始 source keys、source records 和 conflict 状态；多来源冲突不静默选择一个来源。
6. truth isolation 仍成立：candidate probe 不读取 computational truth；truth 只在 scoring 阶段使用，并且只表示 evaluation-side computational structure，不是人的正确答案、心理效度或 posterior probability。

## Aggregation decision

| recipe id | 描述对象 | 输入 | 输出与失败情形 | overlap / unassigned / ambiguous | 裁决 |
|---|---|---|---|---|---|
| `selected_relation_connected` | selected relation graph 的连通结构 | authored group ids、当前 scale 选中的 relation ids | 每个 connected component 一个 candidate；只保留 selected relation ids；bridge chaining 可能把局部链合并；无 selected edge 时没有多成员 candidate | 单个 view 内 component 不重叠；跨 view 可重叠；孤立成员 singleton/unassigned；多诊断 view 可 ambiguous | **APPROVE，design diagnostic；REVISE 仅指旧 id 已拆除** |
| `all_internal_pairs` | 严格 all-internal pair requirement | candidate member combinations、selected ids、relation availability/status/missingness、finite normalized gaps | 每个内部 pair 都必须满足 selected/available/computed-valid；missing/invalid/partial required pair 排除更大集合；没有 required pair 时不能成为 computed candidate | maximal 合法集合可重叠；未覆盖成员 singleton/unassigned；多个合法集合可 ambiguous | **APPROVE，design diagnostic；不得当作 production rule** |
| `complete_link_diagnostic` | selected graph 的 maximal cliques | group ids、selected pair graph | maximal clique；chain 通常退化为 pair cliques；未选或缺失 pair 阻止更大 clique | clique 可共享节点；孤立成员 unassigned；多个 clique 可 ambiguous | **APPROVE，diagnostic/witness only** |
| `max_span` | gap-bound bounded cohesion candidate | selected relation ids、available normalized gaps、当前 scale gap bound | maximal connected candidates，内部 available gaps 的 max 不超过 bound；缺 bound 或 gap 不可用时不输出合格集合 | maximal candidates 可重叠；无合格集合的成员 unassigned；多个集合可 ambiguous | **APPROVE，diagnostic only** |
| `min_gap` | selected pair witness | selected pair ids及其 relation evidence | 每条 selected pair 一个二成员 witness；不能表达 group-level closure | 天然允许 overlap；没有 selected pair 的成员 unassigned；并列 pair 是 witness，不是 partition | **APPROVE，witness only** |

因此，对“selected-relation connected structure / all-internal-pair requirement / 拆成两个 recipe id”的最终建议是：**拆成两个 recipe id**。这同时保留当前 probe 行为和严格语义的独立可审计性，避免从同一分数反推两个不同 estimand。

## Scale decision

| scale recipe | 描述什么 | 何时失效或不充分 | 裁决 |
|---|---|---|---|
| `relative_gap_rank` | 当前 fixture computed normalized gaps 的全局相对排序 | pair 数少、离群值、composition/distribution drift；缺失 gap 不应伪装为大 gap | **APPROVE 并列保留；不选 winner** |
| `local_persistence_window` | 每个 endpoint 的邻居 rank 及跨声明窗口的局部稳定性 | degree 不均、ties、小邻域、window/persistence 交互；局部稳定不等于全局 cohesion | **APPROVE 并列保留；不选 winner** |
| `space_profile_rank` | available empty-space profile 的相对支持排序 | domain/profile 缺失、profile validity、barrier/veto 交互未冻结；空间 role 可能与 proximity 不同 | **APPROVE 并列保留；不选 winner** |

三个 scale recipe 描述不同对象，现有证据支持继续并列运行，不支持选择默认尺度或数值 threshold。

## Boundary and status decisions

| 项目 | 裁决 | 依据 |
|---|---|---|
| canonical space-key normalization | **APPROVE（design-only）** | reverse-only 可 canonicalize；双来源冲突保留全部 provenance 并显式为 conflict；不静默选择来源 |
| truth isolation | **APPROVE** | probe `truth_consumed=false`；scoring 才读取 truth；输入 hash 对齐 |
| missing/invalid/partial/not_available | **REVISE before implementation** | 分类传播已验证，但 required/optional channel、candidate-level partial 提升和 conflict 对 scale selection 的正式契约仍未冻结 |
| candidate-field vs formal membership | **APPROVE（boundary）** | 所有 candidate records 保持 `formal_membership_edge=false`；candidate 不改写 authored membership 或 public API |
| deterministic evidence vs probability/psychological validity | **APPROVE（boundary）** | schema/report 明确 deterministic support 不是 probability；computational truth 不是人的正确答案或心理效度 |
| aggregation registry | **APPROVE for design probe; REVISE before any contract freeze** | 五个 recipe id 已唯一、可复现且 provenance 完整；不批准 production selector |
| scale registry | **APPROVE as parallel diagnostics** | 三个 recipe 可复现并列运行；不批准默认尺度 |
| implementation design entry | **DEFER** | 尚未冻结 candidate estimand、overlap/maximal policy、space-channel requiredness、status contract 或 acceptance rule |

## Minimal follow-up before another design review

1. 保留现有 chain fixture，并增加至少一个同时拥有多个 maximal all-internal sets 的案例，明确 overlap 和 ambiguous 的期望输出。
2. 为 `all_internal_pairs` 增加 relation unavailable、invalid、partial 各一条 selected-but-ineligible pair，确认 strict rejection 与 singleton/unassigned 传播一致。
3. 明确 space profile 的 validity/status/barrier 与 aggregation 的 required/optional channel contract；继续禁止把 missingness 变为数值。
4. 如果要进入 implementation design，先冻结 candidate estimand、formal boundary、status vocabulary、provenance schema 和 deterministic acceptance fixture；不得从 H2 F1 或 candidate-set overlap 选择 winner。

## Evidence

- H2 candidate probe：五个 aggregation ids、status matrix、canonical provenance/conflict assertions、truth isolation、seed reproducibility。
- H2 scoring：`scored_view_count=880`、`holdout_replica_count=16`、`aggregation_difference_assertion.passed=true`、16/16 hard gates。
- H2 report、experiment record、repair artifact manifest 与五张 deterministic SVG 均标注 design-only、无 winner/threshold、B1/M1=`not_run`。

**STOP FOR DESIGN REVIEW**
