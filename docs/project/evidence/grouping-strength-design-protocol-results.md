# 分组归属证据场协议执行结果

- 日期：2026-10-26
- 范围：design-only 逻辑诊断；不修改生产实现，不选择生产量尺
- 总结：协议矩阵已执行并归档；表示规则可进入 spec 定稿。真实解释性与读数校准仍未验证。

## 诊断矩阵

| 项目 | 结果 | 证据与边界 |
|---|---|---|
| I1–I4 输入资格与身份 | **存在已复现的不一致；待按已确认规则统一** | [前序诊断](grouping-strength-design-diagnostic.md)已复现通用组误纳入、空组/重复/dangling/shared 处理差异。`AuthoredGroup`、canonical contract、`analysis_scene_view` 与 `group_self_description` 尚未共享一个输入身份语义；本轮不改生产代码。 |
| C1 driver / modifier | **表示检查通过；实际 recipe 作用未决** | follow-up fixture 中移除 driver 会改变 proposal extent，移除 modifier 保持 extent、改变 attribution channel。该夹具只验证两类结果可分开记录，不证明生产 recipe 的因果作用。 |
| C2 有效互斥端点 | **候选层暂时支持** | Stage A/D6 保留有效端点 veto 和来源；没有验证归属强度场上的完整 veto 传播。 |
| C3 失效、歧义、越界端点 | **诊断规则检查通过；生产路径未验证** | follow-up runner 仅对唯一且位于冻结 scope 内的两个端点应用 veto。dangling、ambiguous、out-of-scope 声明保留为未决且不 veto。 |
| S1 unknown / conditional | **状态表示通过；读数资格未决** | 场切片保留状态、原因和空读数，不转成零；尚未选定哪些证据映射可产生标量。 |
| S2 incomplete search | **状态分层表示通过；与现有搜索器的接线未验证** | follow-up fixture 将 `search_status=incomplete` 与 computed/unknown field cells 分开，并禁止宣称闭包；这是契约诊断，不是生产搜索器验收。 |
| F1 proposal extent 与完整场域 | **表示检查通过** | 场切片对两个候选各保留全部 3 个 scope 内单元，共 6 格；extent 外单元仍有读数并可标记边界张力。follow-up 的候选 profile 视图也覆盖完整 scope。 |
| F2 scope 外实体 | **表示检查通过** | `GX` 不生成 field cell；作为 scope 外事实以来源和原因保留。 |
| D1 提议/归属证据依赖 | **依赖暴露通过；是否造成强度膨胀未决** | same-source、proposal-source ablated、名义 holdout 三个视图可比较。fixture 的 readout 是预置的合成输入，不能据此估计因果膨胀或确认真正独立性。 |
| P1 强核心 / 弱尾 | **算术表达通过** | 合成向量得到均值 `0.44`、中位数 `0.5125`、最弱成员 `0.15`；仅验证 profile 能显示弱尾。 |
| P2 分家族覆盖与依赖去重 | **覆盖表示通过** | follow-up 显示 geometry `2/4`、semantic `1/4`；同一物理 source 被多个 cell 引用时只计一个 unique source。没有据此选择家族融合权重。 |
| P3 singleton / 低覆盖 | **状态表达通过** | singleton 没有内部 pair 时无标量，scope 内每格仍保留明确状态和原因；不自动当作满分。 |
| P4 原组 / 重叠合并 / 全域候选 | **profile 对照表达通过** | 使用同一组预置成员读数并列计算 original、overlapping merge、broad profile；不跨候选归一化。它只验证呈现能力，不选择统计量。 |

## 重放与范围

- 场切片运行器 4 项自检通过；follow-up 运行器 7 项自检通过。两个设计 JSON 均进行重复重放，逻辑输出一致。
- 既有 D6 当前 fixture 的两次重放及 206 项聚焦测试记录在[前序诊断](grouping-strength-design-diagnostic.md)。旧 D6 记录中的 fixture hash 与当前 fixture 不同，来源差异仍未解决；历史文件未改。
- 未重跑 Stage A 的 37 节点成本基线，也未做真实场景盲审。它们不用于证明本协议中的逻辑表示规则。

## 结论

协议验证了**目标表示可以保留并行、重叠、非二值的归属证据场**，并可报告范围外张力、状态、来源覆盖与 profile 弱尾；它没有验证真实证据到强度读数的映射。可据此定稿非概率强度 spec 的边界与数据契约，但不能冻结数值公式、权重、候选 winner、真实量尺或实现验收阈值。输入消费者的不一致必须作为后续实现的明确约束；真实场景解释性和同源泄漏效应仍待验证。

协议产物：

- [场切片报告](group-attribution-field-slice.md)及 [JSON](group-attribution-field-slice.json)
- [follow-up JSON](group-attribution-protocol-followup.json)
- [协议](../grouping-strength-design-experiment-protocol.md)
