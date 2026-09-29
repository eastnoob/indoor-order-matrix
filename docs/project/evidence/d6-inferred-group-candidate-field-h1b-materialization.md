# D6 H1b real seed-conditioned materialization

状态：`design_only_stop_for_design_review`。本修订只生成真实不同的 seed-conditioned fixture 内容和独立 truth derivation；不运行 holdout recovery scoring。

## 修订目标

H1 的 seed records 只引用 immutable source fixture，不能证明 holdout 输入不同。H1b 为八个 family 各生成 development `101/202` 与 holdout `303/404` 的完整 materialized fixture，包含实际 `groups`、member geometry/type/status、`context`、`space_relations` 和 `space_field`。每个 replica 保存生成参数、seed material/digest、source template hash 和 materialized content hash。

## Evaluation roles

| 内容 | role | 是否可进入未来 recovery scoring |
|---|---|---|
| immutable source template | `replication_only` | 否 |
| declared translation/rotation+frame/positive-unit-scale/ID-traversal transforms | `invariance_only` | 否；只做不变性检查 |
| development seeds `101/202` | `development_reference` | 否；仅开发/敏感性输入 |
| holdout seeds `303/404` | `generalization_holdout` | H1b 阶段不运行；未来才可作为 holdout 输入 |

## Seed-conditioned generation

每个 replica 的 seed material 是 `d6-h1b/materialized-fixture/v1|{family}|{split}|{seed}`，由 SHA-256 派生 deterministic PRNG。公共 nuisance 参数包括正尺度、平移、每 authored group 的小幅 jitter 和 space profile delta；family-specific structural conditions 保持不变。每个 family 的四个 materialized content hash 均不同，且 holdout hash 不等于 development hash。

H1b 的数值变化用于构成未见的几何/关系组合，不把 source template 的绝对坐标当作 truth。family invariants 仍由结构规则约束：gap-jump 保留最大结构间隔，bridge 保留 profile-supported A-B/B-C 与孤立 D，overlap 保留共享节点，space-conflict 保留显式 veto，missing-invalid 保留状态类别，context 只改变参照证据。

## Independent truth derivation

truth manifest 对每个 materialized replica 独立保存 `input_content_sha256`、derived candidate sets、veto pairs、singleton/unassigned diagnostics、status targets 和 derivation observations。推导只读取 materialized fixture 的几何、状态、空间 profile/role 与显式 mutual-exclusion 属性；不读取 candidate output、recipe winner、score 或任何人工/心理标签。truth 是 evaluation-side computational structure，不代表真实场景准确率。

## Materialization audit

| Family | Development content hashes | Holdout content hashes | Truth derivation |
|---|---|---|---|
| gap-jump | `d01e396abe9d`, `80ecae7a043d` | `835ee0d69fd1`, `83f0698ac737` | per-replica structure-derived rule |
| minority-mixed | `60b267b575bb`, `b5a07904e791` | `d6743daa4497`, `1affead045dd` | per-replica structure-derived rule |
| geometry-conflict | `c0ea9d5773a9`, `c5ea008a4545` | `2ce553923bbc`, `95a60c4c6b63` | per-replica structure-derived rule |
| space-conflict | `1ca2083559d5`, `b2e696b30699` | `6879f32ffc5f`, `b405ad6ee482` | per-replica structure-derived rule |
| bridge-chain | `db6d2a685789`, `4f617ad0baa5` | `c446e12accb6`, `6952195cc631` | per-replica structure-derived rule |
| overlapping-candidates | `6c1e43e9c7f2`, `5ef6bef83868` | `814ef1d0cc7a`, `ece9168ff879` | per-replica structure-derived rule |
| missing-invalid | `b57551f9a8b6`, `4cdf664e710e` | `be3de771ea42`, `a76949d2810e` | per-replica structure-derived rule |
| context-perturbation | `8dfc3578253b`, `64cf3676c770` | `506cd240d3de`, `e69cf075a434` | per-replica structure-derived rule |

验证内容：32 个完整 replica，seed digest 可重算，四个 family 内每个 replica content hash 唯一；holdout 与 development 使用不同数值输入。candidate probe 尚未运行 H1b fixture，holdout scoring 保持 `not_run`。

## Owner decisions still open

- 是否批准 `generalization_holdout` 角色进入 H2，以及 H2 的 recovery metric bundle。
- 是否接受各 family 的结构推导规则作为 computational truth contract，尤其是 minority chain、geometry alternatives 和 context perturbation 的消费语义。
- 是否冻结任何 scale/aggregation recipe、数值 threshold、singleton policy 或 production selector；H1b 不做选择。
- Bayesian prior/likelihood/spatial dependence/calibration 与 ML representation/algorithm/validation target 仍未批准。
- 空间 role 如何在未来报告中保持独立于 furniture membership，仍待 owner 决定。

**STOP FOR DESIGN REVIEW**
