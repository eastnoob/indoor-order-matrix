# D6 家具组到 inferred group：grill-me 讨论笔记

- **日期：** 2026-09-29
- **状态：** 讨论中；不批准生产算法、不修改生产代码。
- **用途：** 记录本主题每一步的重要判断、用户原话、项目核实事实、解释和未决问题。后续讨论继续追加本文件，不另起平行决策记录。
- **技能：** 已读取并按 `grill-me` 的逐步追问方式进行；结合 `experimental-design` 设计可区分的 synthetic comparison，结合 `scientific-critical-thinking` 分离证据、解释和假设。

## 1. 本轮用户原话

> 2是最好的，但是后面早晚要处理，不能老是悬置

> 每一步的决策都要记录在一个md笔记中，当前这个问题很难决策，我考虑究竟是用机器学习解决还是贝叶斯解决。我们可以讨论

原始长篇需求仍保留在项目原始需求记录中。本笔记不替代原话，也不把暂定想法改写为已批准技术规格。

## 2. 已确认的讨论决策

### 2.1 空间角色输出

- 空间实体允许同时保留多个角色候选。
- 当前采用方案 2：输出多个角色及其证据；暂不强制选择单一主角色。
- `primary_role` 属于后续观察项，不是当前核心输出。
- 角色示例：`corridor_candidate`、`activity_space_candidate`、`separator_space`、`connector_space`。
- “宽/窄”不是固定绝对阈值；它只是待形式化的相对几何证据。
- 角色候选不是人的心理判断概率。

### 2.2 空间实体与家具组边界

- authored furniture group 仍是家具分析的最小节点。
- 空空间是独立的派生 `SpaceCandidate`，不是家具组成员。
- 空间实体可以作为家具组之间的分隔、连接或内部空间证据。
- 更高层 scene candidate 可以同时引用家具组和空间实体，但必须分别记录 furniture members 与 space references。

### 2.3 Inferred group 当前仍在设计

- 已冻结：家具组几何、方向、组间距离、接触、重叠、Z、clearance、阻隔等关系证据。
- 仍在设计：如何由这些关系合成 inferred group，以及如何处理空间角色、类型标签和几何相似性之间的冲突。
- 不把 connected-components、complete-link、max-span、K-means 或 Bayesian 任一者自动写成最终规则。

## 3. 项目核实事实

- 架构记忆中的 `AnalysisDomain` 是负空间计算前提；缺失时负空间及依赖拓扑应为 `not_available`，不能当作零。
- 当前代码已有 `negative_space`、`gap_path`、`activity_region_candidate` 和路径图，但这些属于历史/现有推断实现；clean-room D6 设计仍需重新定义其边界。
- 当前 `required_path_width` 是外部需求参数，不等于系统自动推断出的“走廊宽度”。
- `semantic_type`/家具类型是事实输入，可以作为证据通道；不能直接变成硬分组标签。
- E8b 已证明不同组合同一几何关系会产生不同结果；测试本身不能选择研究目标。
- Bayesian 证据支持 geometry-only latent grouping、uncertainty、missingness 和 synthetic calibration 的方法学可能性；不支持家具 inferred group 已有验证模型。
- 项目禁止使用人工标签、心理评分或人类因变量作为本项目算法输入或模型选择目标。

## 4. 当前解释，不是已批准规格

目前最合理的结构是：

```text
authored furniture groups
  → group geometry/trend
  → pairwise relation evidence
  → independent space candidates and role evidence
  → inferred-group / scene candidates
```

`SpaceCandidate` 先输出连续几何和拓扑描述，再给出多个角色候选。角色融合方式尚未决定。

## 5. 机器学习 vs Bayesian：当前讨论框架

### 5.1 机器学习可能提供什么

- 无监督或自监督方法可以从几何、类型和关系特征学习表示或聚类。
- 监督机器学习需要训练标签；当前项目没有人工 inferred-group 标签，不能偷偷假设标签存在。
- 无监督聚类仍需要选择相似度、簇数、尺度或目标函数；它不会自动知道“走廊”和“活动空间”的含义。
- 机器学习输出的 cluster 不能自动解释为可信度、空间角色或人的理解。

### 5.2 Bayesian 可能提供什么

- 可以把空间角色、组间 edge 或层次结构作为潜变量。
- 可以显式表示 missingness、geometry uncertainty、类型证据和空间依赖。
- 可以输出多角色、低信息、多峰或 `undefined`，与当前状态契约较匹配。
- posterior 是给定模型、先验和场景观测后的计算不确定性，不是心理概率。
- Bayesian 仍需要声明 likelihood、prior、尺度和生成假设；它不会自动发现唯一正确的 group。

### 5.3 当前暂不裁决

尚未决定：

- 是否需要学习表示；
- 是否有可接受的 synthetic computational truth 来训练或评价模型；
- Bayesian 的潜变量是 `space_role`、`group_edge`、`candidate_structure`，还是分开建模；
- 机器学习和 Bayesian 是否竞争同一 estimand；
- 是否允许 hybrid（学习几何表示，Bayesian 负责角色/关系不确定性）。

## 6. 下一轮必须回答的问题

先不选算法，先确定模型要回答的量：

1. 我们要预测的是空间角色、家具组之间的 edge、inferred-group candidate，还是三者分层输出？
2. 这些量是否有 geometry-only synthetic truth？
3. 没有人工标签时，什么结果才算 computationally recovered？
4. 类型证据与几何/拓扑证据冲突时，是否必须保留分通道结果和冲突状态？
5. 模型失败时，最终允许输出多峰/ambiguous，还是必须给主标签？

## 7. 当前停止点

本轮只确认：角色并列输出优先；primary role 暂缓；机器学习与 Bayesian 需要围绕同一明确 estimand 比较。未选算法，未实现模型，未进入 production design。

## 8. 路径澄清（2026-09-29）

用户确认的主路径仍是：

```text
已确定的 furniture-group nodes
→ 已确定的 group geometry/trend
→ 已确定并保留的 group relation evidence
→ 仍在设计的 inferred-group synthesis
```

本轮讨论的 `SpaceCandidate`、空间角色和多角色输出没有替代 inferred-group synthesis。它们属于 synthesis 的关系上下文：空空间可以解释组间分隔、连接或内部空间，但不改变家具组是最小家具节点，也不单独成为项目首要模型目标。

因此后续 grill 顺序修正为：

1. 定义 inferred group 要表达的对象；
2. 定义空空间如何作为分隔/连接证据；
3. 比较关系合成规则；
4. 最后再判断 deterministic、Bayesian、机器学习或 hybrid 哪种方法适合。

**当前路径未改变；空间角色是 inferred-group 设计的一部分，不是另起任务。**

## 9. Inferred group 的工作判断（2026-09-29）

### 用户补充

用户同意先设计和比较空间角色推断，并指出：

> 组在我的愿景中，甚至可以没有一个明确的边界，而是一个场，一个概率组合

### 总控判断

“几何上可以合并”与“被同一空间结构组织”不应被当成两个互斥产品目标：

1. **几何关系是观察层。** 距离、接触、重叠、Z、clearance、阻隔、方向和类型相似性提供可审计 evidence channels。
2. **空间角色是组织层。** 空空间的连续性、宽度分布、瓶颈、连通性、边界和邻接家具组，形成 `SpaceCandidate` 及其 role evidence。
3. **inferred group 是软组织场。** 它描述家具组节点在同一空间组织中的关联强度、可能的多尺度组合和不确定性，不默认输出清晰 partition 或唯一边界。

因此，若必须说明优先级：**组级解释优先采用空间组织场；几何关系是其基础观测和必要证据，类型/几何相似性是附加证据通道。** 这不是让空间标签覆盖几何，而是让“同一空间结构”成为 group-level estimand，避免把几何相似家具隔着明显空间分隔强行合并。

冲突时保留分通道结果：例如几何相似性高、空间分隔强，则输出“相似但空间组织分离”；几何相似性低、共同空间组织强，则允许形成较弱或多峰的 inferred association。不得把冲突压成一个无 provenance 的分数。

### 暂定模型对象

```text
P(organization relation / soft membership
  | group geometry, space-role evidence, type evidence, missingness, uncertainty)
```

这只是 estimand 方向，不是已批准公式、prior 或 Bayesian 实现。确定性版本可先输出连续 evidence vector 和多尺度候选；Bayesian 版本可输出 edge/posterior 或 soft membership。两者必须保留各自 provenance，不能把强度字段叫作概率。

### 为什么不先把它做成纯几何聚类

- 纯几何相似会把被宽阔连续空间分隔的相似家具误合并；
- 纯路径/空间标签会把几何上无关的家具仅因同处一块空区而合并；
- 场模型允许关系强弱、重叠候选、多峰和无明确边界，同时保留两类失败原因。

因此当前不是选择“几何”或“空间结构”，而是决定：几何负责观测，空间场负责高层组织解释。

**本节是总控工作判断，待后续 synthetic comparison 和设计审查验证；不进入生产实现。**

## 10. 双层场定义（2026-09-29）

用户同意保留两层场：

1. **空间场**：定义在 `AnalysisDomain` 上，描述空区的连续性、宽度分布、瓶颈、连通、分隔和空间角色证据。
2. **组关系场**：定义在 authored furniture-group graph 上，描述组与组之间的软关联、重叠候选、多尺度关系和不确定性。

两层通过家具组与空间实体的邻接、边界、穿越和阻隔关系连接。空间实体不是家具组成员；组关系场不能替代空间场，空间场也不能静默改写 authored membership。

这是一项已确认的设计方向，不是 production API、概率公式或算法选择。

## 11. “场”与“group”的区别（2026-09-29）

用户追问：

> 什么意思，场和group的意思不同吗？

是，不同：

- **家具组（authored group）**：输入事实。例：一桌四椅。成员边界由 IFC/SVG authored membership 给出。
- **inferred group**：对若干 authored furniture groups 的高层关系解释。它可以是软的、重叠的、多尺度的，不必有一条绝对边界。
- **空间场（space field）**：定义在分析空间上的连续证据分布。每个位置或局部区域都有占用、空闲、宽度、连通、阻隔和角色支持等值；它本身不是一组家具。
- **组关系场（group-relation field）**：定义在家具组节点或组对上的连续关系证据。它描述 A 与 B 的关联强弱、分隔或连接支持；它本身也不是一个已经选定的 group partition。

可以用一个比喻理解：

```text
场 = 地图上的连续“势”或证据分布
group = 从这些证据中描述出来的一组对象或软关联
```

因此当前设计不是“场和 group 二选一”：先保留场，再从场与组间关系中产生 inferred-group candidates。若证据没有形成清晰边界，输出软关联/多候选/ambiguous，而不是伪造硬边界。

## 12. 单向结构裁决（2026-09-29）

用户询问：

> 你认为这种单向结构合理吗？

### 总控判断

**作为第一阶段的计算基线，单向结构合理；作为最终场景理论，过于严格。**

推荐拆成三层：

```text
F0 基础空间场
  = AnalysisDomain + physical occupancy + blockers
        ↓
组间 relation evidence
        ↓
F1 组织/角色场 + inferred-group candidates
```

- `F0` 不读取 inferred group，避免“先分组、再用分组生成支持分组的空间”的循环论证。
- 组间关系读取 `F0`，同时保留距离、接触、重叠、Z、阻隔、类型和几何相似等分通道证据。
- `F1` 可以读取组关系、类型和空间几何，表达 separator、connector、corridor/activity 等角色候选，并产生软 inferred-group 关联。
- `F1` 不回写或修改 `F0`。基础 occupancy、domain 和 blocker 仍是可追溯事实/基础派生证据。

严格的最终单向模型仍有局限：组的形成会影响“内部空间”和“组间空间”的解释，空间角色也会反过来影响组关联。因此后续 Bayesian 或联合模型可以研究 `F1` 与 group structure 的联合推断或迭代更新，但必须把反馈路径、收敛/不可辨识状态和 provenance 单独设计，不能偷偷加入首版。

当前确认：**首版使用无循环的分层单向基线；最终模型保留联合推断的研究入口。**

**STOP FOR GRILL-ME DISCUSSION**

## 13. 空间场的基础观测与家具组语义（2026-09-29）

### 本轮用户原话

> 我同意你的建议，写笔记，对于问题：空间场的基础观测应优先使用哪些量——自由空间距离、连通性、瓶颈宽度、边界开放度，还是还要加入家具类型和方向？ 回答该问题我建议你阅读当前已经实现的代码，我认为其实就是客观与主观，客观，即你说的这些自由空间距离等等的；主观，即可以要求每一个家具组带有特定的标签，正如我所说，例如名字不同，不同一类，则可能互斥。但是任何一种属性都不能独挑大梁，也不应给予主观的权重，而是要相互作用，例如我说的，一堆正常桌椅里面混入两三个舒适桌椅，但是由于舒适桌椅之间没有成势，而且两者在几何上，以及自身几何特征（面积体积啊之类的，虽然不太好可以设计其他的东西）差距不大，那么还是可以和周边打成一组的，就像围棋，这两个棋子在一大片白棋内，被吃了，没有气。当前这只是一个例子，你说的每一项都很重要，基于这些做思考。你可以任意调用网络资源搜索与技能来做

### 已核实的当前实现事实

- `features/scene_inference.py` 已有活动区域候选、负空间 gap path、路径连通与空间网络相关计算；路径宽度目前来自外部设置，不能当作项目内已经证明的心理阈值。
- `features/neutral_scene_views.py` 将 `physical_occupancy`、`paths` 和 `analysis_domain` 分开保存；没有显式 `AnalysisDomain` 时，负空间拓扑不能被默认为可计算。
- `adapters/ifc_bonsai.py` 和 `adapters/svg_scene.py` 读取显式 furniture-group、类型/容器关系、作者提供的 affordance 和空间域 provenance；适配器不会根据家具名称自动生成 affordance。
- 现有 `position_grammar`、旧 region 推断和 path graph 是可复用的参考与证据来源，不是本 clean-room inferred-group 规则的既定答案。

### 对“客观 / 主观”的解释

本项目中“主观”不应直接写成心理主观性。更准确的名称是 **authored semantic evidence（作者提供的语义证据）**：家具组标签、名称、用途或显式角色，以及它们的来源、可靠性和是否明确互斥。它可以表达设计者的分类意图，但不等同于人的感知，也不能单独决定 inferred group。

“没有气”可以暂译为 **局部支持不足**，而不是固定的计数阈值：一个少数标签组若没有空间连续性、邻域支持或几何上的自洽关系，就应产生弱支持、冲突或孤立候选；若它与周围组在几何、空间场和局部关系上持续一致，则标签差异只能保留为语义冲突/修饰证据，不能自动把它踢出周围组织。这个比喻仍是待验证假设，不是算法定义。

### 首轮观测分层建议

首轮不选择“客观”或“主观”其中一方，而是保留可追溯的多通道观测：

1. **基础空间场（F0）**：相对于 `AnalysisDomain` 的自由空间距离/clearance、连通性、瓶颈剖面、边界开放度或可穿越性、占用与阻隔、Z/层级兼容。它描述家具之间和周围空间的组织条件。
2. **家具组几何场**：组面积或体积、中心、外形/尺度、协方差、组内方向框架、组间相对几何相似性。优先使用同一场景内的相对差异和多尺度变化，不写死“1.8 米”等绝对分组线。
3. **作者语义场**：家具组的类型、名称、用途或显式角色，以及标签之间的兼容/冲突关系、来源和可靠性。标签是证据通道，不是硬分组标签；只有明确记录为互斥的语义关系，才可能成为强分隔证据，仍需与几何和空间证据一起审查。
4. **上下文支持场**：局部邻域支持、同类/异类支持、跨尺度持续性、竞争候选之间的分离程度。它是把“混入少数元素”和“形成独立势”区分开的候选量，目前只允许作为待实验的描述量。

这些通道不应先压成一个固定加权分数。首轮设计应输出各通道的值、来源、缺失状态、冲突状态和交互诊断；后续才比较确定性合成、图模型或 Bayesian soft membership。任何 `strength` 仍表示确定性几何证据强度，不能被解释为方向或分组的概率。

### 与用户例子的对应

“少量 cozy chair 混入大量普通桌椅”的最小反例应至少比较两种布局：

- 少量 cozy 组彼此不连续，且与周围组在面积、形状、方向和自由空间关系上没有稳定分界：应保留标签差异，但其独立组织支持较弱，允许被周围 inferred-group candidate 吸收或保持 ambiguous。
- 少量 cozy 组形成连续的空间/几何势，并被相对宽的空区、瓶颈或边界开放度分隔：应提高独立 candidate 的支持，即使标签数量很少。

这不是“数量达到某个阈值就分组”，而是用同一场景内的相对关系和跨尺度稳定性描述是否形成势。实验需要检查该描述在标签翻转、ID 重命名、平移/旋转、缺失和无 `AnalysisDomain` 时是否保持可解释。

### 当前暂定裁决与边界

- **批准作为设计方向**：空间场基础观测同时包含客观空间/几何通道和作者语义通道；所有通道通过交互共同解释，任何单一通道不能独挑大梁。
- **暂不批准**：具体权重、概率先验、K-means、Bayesian 公式、绝对距离阈值、标签硬互斥规则、最终 `primary_role` 或 production API。
- **下一步**：先设计一组最小 synthetic comparison，分别改变空间关系、几何相似性和标签支持，观察各通道及其交互是否能表达“少数混入”与“形成独立势”的差异；结果由设计 probe 和记录审查，不把 probe 直接升级为实现。

**STOP FOR GRILL-ME DISCUSSION**
