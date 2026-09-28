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

**STOP FOR GRILL-ME DISCUSSION**
