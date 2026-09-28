# D6 Task 3d：inferred group 目标语义设计表

- 日期：2026-09-28
- 状态：设计候选；**STOP FOR DESIGN REVIEW**
- 范围：定义 inferred-group 要描述的对象，再决定 selector；不实现算法。
- 输入：E8b/E9/E10/E10b、Bayesian evidence synthesis、clean-room contract。
- 人类参与：不需要人工标签、排序、评分或视觉 ground truth。视觉图只可作可选可解释性检查。

## 1. 核心裁决

当前计算证据不能唯一识别“家具组之间应形成哪一种 inferred group”。E8b 的 near/far、bridge、multi-Z 和 disconnected fixtures 显示：`any`、minimum witness、maximum span、all-pairs 和 connected-components 会对同一几何事实给出不同语义。它们不是同一个目标的不同实现。

因此推荐一个统一处理管线，但保留多个明确的描述视图：

```text
authored furniture-group nodes
        ↓
统一 pairwise relation observations
        ↓
edge evidence + status + provenance
        ├─ local-neighborhood view
        ├─ bounded-cohesion candidate view
        └─ connectivity/chaining diagnostic view
```

这不是同时保留一堆互相竞争的生产算法。统一的输入、几何测量、状态和 provenance 先冻结；视图语义分别声明。只有 owner 之后明确某一视图为产品主描述，才允许把它写成 canonical inferred-group result。

## 2. 目标候选比较

| 目标 | 它描述什么 | 主要输出 | 适合的 cases | 不能推出 | 裁决 |
|---|---|---|---|---|---|
| 几何连通 | 节点可由合格 pairwise edge 链接到同一连通分量 | connectivity component、未分组节点 | 需要表达局部连接或桥接链 | 不表示全组紧密；桥接链会合并远端节点 | 仅 chaining diagnostic baseline |
| 全组紧密 | 候选组内所有必要关系满足 bounded gap/clearance 约束 | complete-link/max-span candidate；可重叠 | 需要每个成员都接近其余成员 | 不能证明功能相同；阈值和尺度未由心理效度决定 | 保留为 cohesion candidate view |
| 局部邻近 | 每个 authored group 的邻居集合和边证据 | pairwise edges、ranked/thresholded neighborhood | 不确定是否应合并时 | 不产生唯一 partition | 首阶段主描述层 |
| 多尺度层级 | 同一场景在多个声明尺度下的局部邻居和 cohesion candidates | scale-indexed views、overlap、ambiguous、unassigned | 长排、桥接、局部近而其余远 | 不把某一尺度说成唯一真实组 | 推荐的 group synthesis 方向，尺度待设计 |
| 趋势一致 | 方向/frame 证据相似 | group_frame、group_axis、coherence | 描述方向组织 | 不证明 membership；不能反向决定首轮 edge | 独立 descriptor，首轮禁用 |
| 仅关系图 | 场景的可审计 group-to-group 几何关系 | pair records 和 edge statuses | 输入不足、目标未确定 | 不提供 inferred group | 保守 fallback，始终保留 |

## 3. 推荐的统一描述结构

首阶段不定义单一 `inferred_group` 真值，而定义三个输出层：

### 3.1 Relation layer：必须存在

节点固定为 authored `IfcGroup.ObjectType == "furniture_group"`。每个 group pair 记录：

- raw/normalized boundary gap；
- contact、positive-area overlap、near；
- member-pair provenance、witness、excluded pairs；
- center、size、support_area；
- 3D clearance/overlap；
- Z-band/level compatibility；
- wall/opening barrier；
- status、reason、analysis frame、unit、tolerance、source provenance。

这层不需要选择 grouping objective，因此可先进入实现设计。

### 3.2 Local-neighborhood view：第一种自描述

它回答：“每个 authored furniture group 与哪些其他 group 存在什么几何关系？”

它允许未分组节点、缺失 channel、ambiguous relation 和 shared-member diagnostic。它不生成 hard partition，也不把最近邻自动当作同组。`normalized_boundary_gap` 是主要连续描述；关系状态仍为 categorical evidence。

### 3.3 Candidate view：第二种自描述

它回答：“在声明的空间尺度和 cohesion 规则下，哪些 authored nodes 可以组成候选组？”

首轮只输出 candidate records，不输出唯一真实分组。允许 overlapping candidates、unassigned 和 ambiguous。connected-components、complete-link/max-span、any/min/max 只能作为带名称的候选规则，不能互相覆盖或静默合并。

## 4. Deterministic / Bayesian 对齐

| 层 | Deterministic | Bayesian | 当前状态 |
|---|---|---|---|
| frame | `group_frame`、`group_axis` | `P(group_frame \| member geometry, missingness, reliability)` | 已批准共同首模；不用于 membership |
| edge | measured gap/overlap/status | `P(group_edge \| group geometry, gap, overlap, uncertainty)` | 先做 edge-level candidate；不解释为 partition probability |
| candidate group | CC、complete-link、max-span 结果 | 只有在 group objective 明确后才定义 `P(candidate structure \| …)` | 暂不冻结，不实现 |
| fusion | point evidence | posterior distribution | 不融合不同 estimand；同一 estimand 且有 synthetic holdout 后才讨论 |

Bayesian posterior 是模型条件下的不确定性，不是“人会不会把它看成一组”的概率。`strength` 仍是确定性证据强度，不能当 posterior。

## 5. Synthetic design gate

若继续实验，必须先固定目标，再固定 expected computational property。最低 fixture family：

| family | 目标区分 | 必须观察 |
|---|---|---|
| bridge chain | 连通与全组紧密的差异 | component 合并、max-span 候选、overlap/ambiguous |
| near/far multi-member | any/min 与 all-pairs 的差异 | witness、excluded pair、group status |
| long row | 单尺度与多尺度描述 | scale-indexed candidates，不强制一个 partition |
| unequal size | normalized gap 稳健性 | denominator、尺度变化、尺寸不平衡 |
| shared member | authored 与 inferred 分离 | dependency diagnostic，不生成 self-supported edge |
| multi-Z/barrier | 2D proximity 与 3D/channel boundary 分离 | required status、formal edge 阻断 |
| missing/invalid | 信息不足与非法输入分离 | partial、not_available、diagnostic_only、invalid |

若没有目标函数或预先声明的 computational truth，实验只能证明实现一致性，不能选择目标。此时保留 relation layer 和多视图候选，不继续增加随机样本。

## 6. 进入 implementation design 的冻结条件

必须先冻结：

1. relation layer 字段、status、contact/overlap/near 语义和单位/tolerance；
2. local-neighborhood 是否作为首个 canonical descriptor；
3. candidate view 的尺度参数来源及其 provenance；
4. candidate view 是否允许 overlapping、unassigned、ambiguous；
5. 是否把 CC、complete-link、max-span 作为并列 evidence 还是选择一个主视图；
6. Bayesian edge/frame 输出是否与 deterministic 分开保存；
7. IFC/SVG 各自可验收的 canonical facts；
8. 仍缺的 opening relation 和同场景双 adapter fixture 的处理方式。

推荐冻结顺序：

```text
relation layer → local-neighborhood view → candidate-view objective
→ deterministic/Bayesian competition → production descriptor design
```

## 7. Grill-me 自检

- 测试通过不能回答“哪一种 group 定义正确”；文档不把 E8b 规则差异写成算法失败。
- 连接分量不等于功能区；complete-link 不等于心理上的组；trend 不等于 membership。
- 组级 posterior 不等于心理概率，也不自动成为 IFC authored group。
- 多尺度视图不是偷偷选择多个答案；每个 view 必须有名称、尺度、规则和 provenance。
- 当前推荐不删除 inferred grouping；只避免在目标未定义时伪造唯一 inferred-group 真值。

## 8. 结论

**推荐：统一 relation computation，加上明确分层的 local-neighborhood 与 candidate views；暂缓单一 inferred-group selector。**

本设计可进入下一次 owner design review；不能直接进入 production implementation。下一步是审阅并冻结 local-neighborhood 是否为首个 canonical descriptor，以及 candidate view 的尺度/目标语义。

**STOP FOR DESIGN REVIEW**
