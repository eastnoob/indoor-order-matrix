# D6 H1 holdout review decision

日期：2026-09-29

## 裁决

**REVISE。暂不进入 H2 holdout recovery scoring。**

H1 的 schema、边界、seed 记录和 truth provenance 写得清楚，且没有越界修改 production code；但当前的 32 个“replica”不是新的几何/关系样本。每条记录的 `materialization` 都明确写成：

> deterministic seed record referencing the immutable source fixture

因此 `303/404` 目前只是对同一 source fixture 的 seed metadata/hash 记录。它们可以验证记录可复现，不能验证算法对未见布局的泛化，也不能作为真正的 holdout scoring 输入。

## 已批准的部分

- fixture-family split 单位为完整 fixture，不按 member/pair 拆分；
- development seeds `101/202`、holdout seeds `303/404` 的命名和 provenance；
- truth 由 evaluation side 保存，candidate probe 不读取 truth；
- hard veto、singleton/unassigned、`computed/partial/invalid/not_available` 的分类契约；
- translation、rotation+frame、unit-scale、ID/traversal reorder 的不变性边界；
- 不运行 scoring、不选择 recipe、阈值或 production selector；
- 不修改 production code、API、adapter、测试或依赖。

## 必须修订的部分

### 1. 真实 seed-conditioned materialization

每个 family 的 development 和 holdout seed 必须生成实际 fixture 内容，而不是只引用 source fixture id。至少要有可审计的几何、关系、空间角色或 context 变体；变体应保持该 family 的结构条件，同时让 holdout 包含 development 未见的数值组合。

每条 replica 至少需要：

- 完整输入 fixture 或不可变的 materialized fixture path；
- authored group/member geometry、类型/属性、context、space relation 的实际值；
- 生成参数及其 seed digest；
- family invariants 与允许变化的 nuisance 参数；
- 与 source fixture 的关系说明。

### 2. truth 必须由结构条件推导

当前 truth candidate sets 在不同 seed 间直接复制。修订后需要说明 candidate set、veto 和 status target 如何从每个 materialized replica 的结构条件得到，避免“复制 truth”与输入没有关系。truth 仍然只能由 evaluation side 读取，不能反馈给 candidate probe。

### 3. 明确“holdout”资格

若某个 family 只允许结构保持、数值不变，那么它可以作为 invariance/replication check，但不能计入泛化 holdout。文档应分别标记：

- `replication_only`；
- `invariance_only`；
- `generalization_holdout`。

只有最后一类才可进入 recovery scoring。

## 下一步 H1b

只做 holdout materialization 与 truth-derivation 修订：

1. 生成真实的 32 个 seed-conditioned fixture；
2. 写出独立 truth manifest；
3. 验证 seed 可复现、family invariants、development/holdout 内容差异和 provenance；
4. 不运行 candidate scoring；
5. 不选择 recipe、阈值、Bayesian/ML 模型或 production selector；
6. 完成后再次 `STOP FOR DESIGN REVIEW`。

当前 H1 的 hash、JSON parse 和 `git diff --check` 通过，只证明文档/记录一致性，不能抵消上述 holdout validity blocker。

**STOP FOR DESIGN REVIEW**
