# D6 候选合成与空间场交互实验记录

- 日期：2026-09-29
- 实验编号：E11
- 状态：design probe complete；不批准 production selector
- Fixture：[self_description_competition_fixtures.json](../../scripts/design/group_level/self_description_competition_fixtures.json)
- Runner：[run_self_description_competition_probe.py](../../scripts/design/group_level/run_self_description_competition_probe.py)
- Evidence：[d6-self-description-competition-probe.json](evidence/d6-self-description-competition-probe.json)

## 1. 目的

比较“少数标签混入”“少数标签形成独立势”“几何强冲突”“空间阻隔”“普通语义差异”“明确互斥”“context 参照”和缺失/非法状态，检查总体设计是否能把不同证据保留在正确通道中。

本实验不寻找人的 ground truth，也不证明某种候选合成算法正确。probe 中的 support 数值只是可审计的临时计算，用于检查通道交互和状态传播；`formula_scope=probe_only_not_production`。

## 2. 设计

实验单位是完整 fixture。fixture 内的 group pair 和 candidate 是同一布局中的重复观测，不作为独立统计样本。每个 candidate 同时输出：

- geometry similarity、normalized gap proximity；
- semantic compatibility / soft negative / unavailable；
- domain、barrier 和 context alignment reference；
- geometry mismatch、semantic disagreement、barrier 等 negative evidence；
- explicit mutual-exclusion conflicts；
- status 和 provenance。

预先声明的设计不变量：

1. 普通标签差异可以产生软负证据，但不能自动 veto candidate。
2. 明确 mutual exclusion 在 candidate level veto，即使存在共同邻居也不能绕过。
3. 几何差异应保留为 geometry negative evidence，不被相同标签抵消。
4. closed wall 是独立 space conflict，不被 2D proximity 隐藏。
5. domain/semantic 缺失是 `not_available`，不是负证据。
6. invalid geometry 不改写为 missing 或 usable support。
7. context 保持 candidate eligibility，但可提供允许的 alignment reference provenance。

## 3. 观测结果

| Fixture | 观察 | 解释边界 |
|---|---|---|
| `minority_mixed` | `R2+C1` 保持 `computed`，semantic=`-0.25`，没有硬 veto | 标签差异可作为软负证据；不证明该 candidate 应最终保留 |
| `independent_minority` | `C1+C2` 的 gap proximity 高于跨标签 `R2+C1` | 少数群的局部空间支持可与标签数量分开；仍需多尺度实验 |
| `geometry_conflict` | 同标签的 `A+B` geometry similarity=`0.0625`，geometry mismatch=`0.9375` | 标签不能消除强几何差异 |
| `space_barrier` | 近邻 `A+B` 状态为 `space_conflict`，barrier channel=`blocked` | 2D gap 和空间阻隔必须分通道 |
| `semantic_conflict` | `A+B` 为 `vetoed_mutual_exclusion`；普通标签差异本身仍只为 soft negative | candidate-level hard constraint 可阻止共同邻居绕过 |
| `context_reference` | candidate 仍为 `computed`，context alignment provenance 保留 | context 可影响允许的空间参照，不成为家具节点 |
| `missing_channels` | semantic 和 space 均为 unavailable/neutral channel | 缺失不能惩罚对象，也不能伪造同类 |
| `invalid_geometry` | candidate 状态为 `invalid` | invalid 不得改写为 missing |

证据 JSON 中 8/8 个预设断言通过。该结果只能证明 probe 实现了预先写明的计算性质，不选择 `connected-components`、complete-link、max-span、Pareto 或 Bayesian 作为最终合成器。

## 4. 当前裁决

本实验支持将以下内容进入总体设计的 **interaction contract**：

- 语义差异、几何差异、空间分隔和 context 参照必须分通道保存；
- 普通语义差异是软负证据；
- 明确互斥是 candidate-level veto；
- 缺失、invalid、space conflict 和 context provenance 分开表达；
- 候选输出保留 competing candidates、overlap/unassigned/ambiguous 的空间。

本实验不支持冻结以下内容：

- support 通道的固定权重或总分；
- `gap proximity` 的生产阈值；
- 多尺度的默认尺度；
- 空间角色的 `primary_role`；
- 某个 candidate selector 或唯一 partition；
- Bayesian prior、posterior calibration 或心理解释。

## 5. 后续设计门

下一步不再扩大语义 brainstorming，而是把本记录和总体设计表合并成 implementation-design review 草案，重点审查：

1. relation layer 和 local-neighborhood 的字段是否足够；
2. 空间角色 field 的最小表示是否能在 domain 缺失时正确返回 `not_available`；
3. candidate view 是否只作为命名、可追溯的对照输出；
4. 是否需要一个独立的多尺度 probe 来决定尺度 provenance，而不是默认选择某个算法。

**STOP FOR DESIGN REVIEW**
