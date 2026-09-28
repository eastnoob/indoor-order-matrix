# D6 Task 3d：E8b/E10b 证据收口与总控裁决

- 日期：2026-09-28。
- 状态：本轮证据审查收口；Task 3d 整体仍为 **REVISE / STOP FOR DESIGN REVIEW**。
- 授权范围：设计文档与证据审查；不进入 Task 3c、implementation design、descriptor API 或生产代码。
- 本文是总控基于核查作出的设计裁决，不把总控建议写成用户原话或用户对最终产品范围的批准。

## 1. 需求与本轮范围

用户最新原话：

> 为何你不收口。还是说继续做就行

总控理解：直接完成本轮复核与文档收口，不再让用户转交重复的文档任务。收口证据不等于全部算法设计完成，也不等于允许开始实现。

家具组是最小分析节点；家具是组内观测。场景自描述、家具组之间的 inferred grouping，以及 deterministic/Bayesian 方案竞争仍是项目目标。本轮没有将最终产品缩减为只有 pairwise graph，也没有删除后续 grouping 或 Bayesian 任务。用户不承担运行、标注或心理实验；可选视觉审阅属于设计反馈，不充当计算真值。

## 2. 审查来源和证据边界

已读取主设计、迁移表、clean-room spec/plan、[实验记录](d6-inferred-group-design-experiment-record.md)、[follow-up evidence](evidence/d6-inferred-group-design-followup.json)、artifact manifest 和 follow-up probe 的聚合、断言及 SVG adapter 核查代码。

- E8b 数值来自确定性 synthetic fixtures，展示规则分歧，不证明某条规则符合唯一真实分组。
- E9 验证所列缺失/invalid/partial channel 的行为；候选规则下的 `formal_edge=true` 不是正式组级 selector 已批准。
- E10 是实际 IFC 的只读解析、单位和 placement/bbox 审计，不等于新的生产 IFC adapter 或 mesh clearance/barrier 算法已验收。
- E10b 确实调用现有 SVG adapter，但比较对象是独立 SVG fixture 的声明预期值。它不是同一场景分别经过 IFC/SVG adapters 后的完整差分验收。
- 本轮未新增文献检索；计算复核不扩大既有学术证据的结论。

## 3. 分项裁决

| 对象 | 裁决 | 生效范围与理由 |
|---|---|---|
| authored nodes 与 pairwise observations 分层 | 批准设计边界 | 保留全部 member pairs、witness、excluded reasons、shared dependency、frame/unit/tolerance/provenance；不得覆盖 authored membership。字段清单不是 production schema。 |
| E8b any/min/max/all-pairs 比较 | 批准本轮比较证据；暂缓正式 selector | near/far 6 pairs 中只有 1 个 eligible，min 0.4、max 13.0；不同规则回答不同问题。分歧保留 `ambiguous`；组级 `formal_edge=false` 的理由是政策未冻结，不是几何关系不存在。 |
| shared-only / disconnected split | 批准仅诊断 | shared-only 不制造独立 membership 证据；拆分图不更改 authored 节点。 |
| E9 状态 | 批准已测边界 | required missing 不变成 clear/zero；invalid 不改成 missing；partial 保留不完整性。批准不扩展为任意下游消费政策，也不冻结所有任务必须使用同一 required-channel 集合。 |
| E10 IFC primary audit | 批准已审计事实 | IFC4、37 strict furniture groups、95 furniture、11 walls、6 doors，毫米转米比例 0.001；当前样本 opening/void/fill 关系均为 0。 |
| E10 opening/barrier | 暂缓验收 | door geometry 不是 opening relation。缺关系保持 `not_available`；不能以 synthetic opening 或 SVG opening 替代实际 IFC 验收。 |
| E10b SVG adapter 加载及分离矩形 2D 对照 | 批准已测结果 | 2 groups、3 furniture、1 opening；A1/A2 raw gap 0.4、normalized gap 0.2773500981，仅针对该 fixture 和其归一化定义。 |
| E10b contact/overlap 一般语义 | 退回修订 | 当前 probe 把边界接触归入 overlap；分离矩形断言不足以验收接触、穿插或一般 multi-part geometry。见下一节。 |
| 完整 IFC/SVG parity | 暂缓 | 仍缺同场景、独立输入、显式对应的双 adapter 对照；当前 bbox center、member gap 不等于 group representative 和组级 normalized-gap 契约已冻结。 |

## 4. 独立复核发现：contact/overlap 未分离

`scripts/design/group_level/run_group_level_followup_probe.py::_adapter_pair_facts()` 使用非负分离距离 `dx/dy`，再以 `dx <= tolerance and dy <= tolerance` 判 overlap，以 `gap <= tolerance and not overlap` 判 contact。由于 `gap = hypot(dx, dy)`，满足 contact 距离条件时必满足上述 overlap 条件，因此 contact 无法为 true。

可复现反例：矩形 `[0,0,1,1]` 与 `[1,0,2,1]` 仅共享一条边；正面积交集为 0，当前公式输出 overlap=true、contact=false。本轮独立算术检查复现了该结果。原 fixture 中两个矩形分离，因此它的 false/false 断言仍成立，不能据此宣称接触语义已验收。

此缺陷位于设计 probe，本轮不修改脚本。下一设计修订应先明确 overlap 是否指正面积相交、contact 是否指无正面积相交的边界接触，以及容差邻近如何单列；至少覆盖 separated、edge-touch、corner-touch、positive-area-overlap 和 tolerance 两侧。用面积与边界事实建立独立 oracle，不能仅复制当前 boolean 公式。首轮可限定轴对齐矩形，必须声明该限制。

## 5. 后续顺序与退出条件

1. **小范围 probe 修订**：修复上一节语义缺口，补最小反例，更新 evidence/hash，独立复核。停止于设计审查；不改生产代码。
2. **完成合成 group 的目标设计**：由总控提出可计算的目标和设计表，例如局部连通、全组紧密或多尺度层级分别描述什么。说明长排、桥接、局部近而其余远等案例为何应合并、保留重叠或不裁决。先写目标，再决定哪个实验能区分方案；不得因测试通过或视觉喜好直接选 min/all-pairs。用户只需审阅重要目标取舍，不需提供标签。
3. **保留 Bayesian 竞争**：继续已登记的 frame/edge estimand、依赖与 missingness 设计。概率模型不能替代 group-edge 含义的定义；尚不实现，也不从 synthetic 阈值生成 prior。
4. **补实际来源验收**：opening 关系和双 adapter 同场景 parity 各自作为有明确输入的验证任务；没有输入就保留暂缓，不反复运行同一缺失样本。
5. 目标、算法选择、状态、公式/归一化、验收范围组成完整设计表并通过审阅后，才进入 implementation design。不得从本轮有限批准自动跳阶段。

停止增加无判别目标的 E8 样本；这不禁止为明确的新假设做实验。当前只是证据批次收口，最终 inferred-group 功能没有被放弃。

## 6. 本轮工具与验证记录

- 读取并评估 `speckit-assess-decide`：适用于项目级 assessment verdict；本轮只收口 Task 3d 局部证据，不重跑项目 assessment，不宣称产生新的 Spec Kit `go`。
- 读取 `grill-me`：其文件仅要求 `/grilling`，本轮采用反向审查问题核对“断言通过是否足以批准接口、parity 和 selector”；未声称存在或运行独立 `/grilling` 命令。
- 验证结果在本轮实际执行后记录；不沿用执行 session 的通过声明作为独立复核结论。

**STOP FOR DESIGN REVIEW — 不进入 Task 3c、implementation design、descriptor API 或 production code。**
