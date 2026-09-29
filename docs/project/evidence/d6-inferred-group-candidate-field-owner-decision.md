# D6 Inferred-Group Candidate Field Owner Decision

日期：2026-09-29
依据：H2 repair、独立 H2 design review 及相关 scoring/probe/fixture/manifest。

## Owner 裁决

### 1. Aggregation 拆分：**APPROVE（design contract direction）**

接受拆分为：

- `selected_relation_connected`：被当前 scale 选中的关系边形成的连通候选结构；
- `all_internal_pairs`：候选成员集合的全部内部无序 pair 均满足冻结的 selected/available/valid 规则。

两者描述不同对象，不能继续共用 `all_pairs` 这个含义不明确的 recipe id。`all_internal_pairs` 的具体 missing/invalid/partial 规则仍需后续 fixture 冻结，因此本项批准的是方向，不是 production API 批准。

### 2. 五种 aggregation 并列 diagnostics：**APPROVE**

继续并列保留：

- `selected_relation_connected`；
- `all_internal_pairs`；
- `max_span`；
- `complete_link_diagnostic`；
- `min_gap`。

当前不选择 winner。`min_gap` 仍只解释为 pair witness，其他 aggregation 仍是 candidate-field diagnostics，不是 formal membership edge。

### 3. 三种 scale recipe 并列保留：**APPROVE**

继续并列保留：

- `relative_gap_rank`；
- `local_persistence_window`；
- `space_profile_rank`。

不选择默认 scale、数值 threshold 或跨场景 winner。三者描述不同的相对几何/空间证据，不能用当前 H2 F1 直接决定默认规则。

### 4. 状态契约：**REVISE**

当前证据足以接受这些状态名称作为设计候选：

- `missing`；
- `invalid`；
- `partial`；
- `not_available`；
- `conflict`。

但暂不冻结最终传播规则。必须补充 status matrix，明确：

- relation-level 与 candidate-level 的传播差异；
- required/optional channel；
- `all_internal_pairs` 对 missing、invalid、partial 的处理；
- conflict 是否为 hard veto、diagnostic-only 或两者分层；
- singleton/unassigned 无内部 relation 时的状态。

任何状态都不得静默填零、改写为 computed 或互相替代。

### 5. overlap、maximal candidate、ambiguous、singleton/unassigned：**REVISE**

当前方向接受，但还没有足够冻结为实现契约：

- overlap candidate 可以保留；
- maximal candidate 的定义需要按 recipe 分开；
- 多个合法 maximal set 的 ambiguous 表达需要固定；
- singleton/unassigned 必须保留，但需明确其 evidence/status；
- candidate 不得自动变成 formal membership edge。

必须补充 aggregation semantics fixture 和 status matrix fixture，明确 membersets、relation ids、status、overlap policy 及无覆盖成员的输出。

### 6. 进入 implementation design：**DEFER**

当前不进入 implementation design，不修改生产代码、公共 API、adapter、`NeutralSceneV2`、Bayesian 或 ML 模型。

只有在以下条件满足后，才重新审查是否进入 implementation design：

1. 完成 recipe id 拆分并更新 registry；
2. 完成 `all_internal_pairs` 语义 fixture；
3. 完成 status matrix 与 conflict propagation fixture；
4. 冻结 overlap/maximal/ambiguous/unassigned 规则；
5. 重新运行 probe、H2 scoring、hash/schema 与范围审计。

## 下一步授权范围

允许进行下一轮 **design-only contract repair and re-run**，范围限于 registry、probe、fixtures、evidence 和 diagnostic SVG。不得据此选择 winner、threshold 或 production selector。

**STOP FOR DESIGN REVIEW**
