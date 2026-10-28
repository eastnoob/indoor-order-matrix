# 组级势包：家具组到场的支持映射

状态：**2026-10-30 owner 已审阅的设计草案，待用户审阅；source-axis 场生成、支持与软视图汇总尚未实现。**既有全场 axis resultant 和组间四通道关系已实现，本稿不把它们改名为归属。

本稿是[身份与生成协议](2026-10-30-group-axis-potential-field-identity-and-generation-protocol.md)的接口摘要；该协议取代早先“先等外部场身份/参考轴，再实现支持”的 owner 草案。完整结构化 `E` 与通用 `M` 的边界仍见[目标文档](../../project/grouping-goal-alignment.md)。

## 最小输入输出

| 模板项 | 势包首版设计 |
| --- | --- |
| source | 实际 `overall_group_axis` 的角度、PCA clarity、状态、scope/query/plane 和完整来源；`layout_axis`、单体渠道保持 audit/suppressed |
| reference producer | 每个可用实际组轴生成一个 anchored reference view `k`；全部可用轴保留，不挑轴、不近似合并 |
| target set | 全部合格 scope 组 × 全部可用 anchor；允许重叠、无固定 K/区域/半径/阈值/winner |
| logical identity | scene namespace、不可变 anchor group ID、query/plane identity、recipe ID |
| content identity | 规范化 scope/query/plane、源轴/envelopes 和版本；无 timestamp/revision，edit/undo 同内容可复用 |
| output function | 包内函数经既有 `EvidencePackage` 输出契约校验；`evaluate(source_envelopes)` 签名不变，不加 proposal envelope 框架 |
| lineage | 每个 cell 引用行组与 anchor 的 `overall_group_axis`；保留全部输入及 pair channels，不把同源派生量重复投票 |
| visualization | 同一指定 IFC 平面下每个视图单独着色，完整矩阵/状态/profile/manifest 可定位；freshness 复用 whole-package 协议 |

没有 proposed extent 时记录 absent/unspecified，不伪造 inside/outside 或边界张力。参考视图不是推断出的真实组织簇，参考列数不是估计场数。

## 包内支持口径

```text
S(g,alpha) = c_g × cos²(theta_g−alpha), modulo 180°
theta_k = actual overall_group_axis of anchor k
delta = minimum undirected angle gap, [0°,90°]
direction_alignment = cos²(delta)
axis_field_support = c_g × direction_alignment
```

保留角度、`c_g`、delta、alignment、anchor clarity、状态/覆盖及来源。支持是 `[0,1]` 的非概率、越大越支持读数，只是完整证据的参考条件投影；不替代 `E` 或通用 `M`。anchor clarity 单列，不再乘入；clarity 是几何各向异性，不是已校准的角度不确定性。

自引用 cell 计算为 `c_k`，标 `self_reference=true`、`excluded_from_nonself_profile=true`。不重估 source-axis 参考方向；LOO 轴只留给未来 derived-reference recipe。组间共享来源仍可存在，non-self 不代表统计独立。缺失、invalid、undefined/degenerate 不填零；有效方向的零 clarity 才产生已知零支持。没有可用轴时没有参考列，保留原因和覆盖诊断。

## 两种下游读法

1. 完整 scope 支持向量与 **non-self profile**：排除 anchor，对已知值求算术均值，附 valid/expected、coverage 与状态；`expected=N_scope−1`。有效零支持计入覆盖，未知不补零，partial 均值明确标记。singleton 均值不可用，覆盖率不适用。不称其为候选强度。
2. 只读软视图方向：`Q_k=Σ_valid g∈scope S(g,k) exp(i2theta_g)`，描述包含自身；方向 `arg(Q_k)/2`，一致性 `|Q_k|/ΣS`。报告总支持、覆盖、positive weight count、self included/weight/fraction；仅自身有正权重标 anchor_only，不称 consensus。零总支持为 not_available/no_positive_support；抵消为 direction null/ambiguous、coherence 0；缺失覆盖与方向状态分开。仅用数值容差，不再乘 clarity。它不更新参考轴、不回写支持、不作支持验证，也不加最终场强度分数。

组对 `axis_angle_gap`、`direction_similarity`、`clarity_similarity`、`clarity_support` 与全场 resultant 全部保留为各自渠道，不成为额外票。标量 `Σc cos²` 只有常数与 doubled-angle 一阶谐波，交叉方向可使该汇总变平；完整矩阵必须保留。此结论不把 Q 误称为只依赖同一阶矩；Q 也不作 mode detection。仅轴证据不能区分空间分离的平行集合。

非空 scope 无可用 anchor 时输出引用真实轴渠道的 scope-level not_available 诊断；empty scope 由 caller 在 evaluate 前报告 unavailable，不放宽 core 非空契约。新只读描述允许标记后的 singleton coherence 1，不改变旧全场 helper 对少于两个正贡献不报 coherence 的行为。

## 当前执行门

先审阅本稿及身份协议，再维护主计划 2B.6a.12 的实现/指定 IFC checklist。计划复用保留的 37 个可用组轴和投影：预期 1,369 cells（37 self、1,332 non-self），尚不是新 recipe 的验证结果；不创建模拟场景或重提 IFC。几何包、跨包融合、Frame、Form+Scale、排列和 UI 保持后移。
