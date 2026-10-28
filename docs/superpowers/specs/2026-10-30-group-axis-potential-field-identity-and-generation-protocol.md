# 组级势场：身份与生成协议

状态：**2026-10-31 已实现并通过指定 IFC 保留来源回放；owner 接受当前实现范围，用户查看矩阵与代表场平面图后答复“不错，我理解了”。认可仅限当前可重叠参考支持视图，不代表现实归属校准、hierarchy 或浏览器交互验收。**

本协议只服务 `overall_group_axis` 势包。它增补[目标边界](../../project/grouping-goal-alignment.md)，不替代完整结构化证据 `E(g,k,s)` 或最终通用归属投影 `M_k(g,s)`。几何、Frame、Form+Scale、排列、跨包融合和 UI 保持后移。通用声明复用[证据包最小规范](2026-10-30-evidence-package-minimal-standard.md)。

## 核心：连续响应与真实轴参考视图

对冻结 scope 内家具组 `g`，以其整体 PCA 无向主轴 `theta_g` 与清晰度 `c_g` 定义：

```text
S(g, alpha) = c_g × cos²(theta_g − alpha), alpha modulo 180°
k = 一个实际可用 overall_group_axis 所提供的锚定参考视图
theta_k = 该 anchor 家具组的实际轴角度
Support[g,k] = S(g, theta_k)
```

`S` 是参考方向条件下的轴支持读数，非负、范围 `[0,1]`、越大越支持；不是概率、物理力或已校准的现实强度。0°/180° 等价，90° 为正交。清晰度是几何各向异性，不是已校准的角度不确定性。

代数依据：对 trace>0 的 2D PCA covariance C，`T=C/tr(C)=((1−c)/2)I+c uuᵀ`，u 为主轴单位向量。故对参考轴单位向量 a，`S=c(u·a)²=aᵀ[T−((1−c)/2)I]a`，即去掉各向同性基底后的方向投影；这不校准 membership/置信度，也不为 undefined/degenerate 源轴补零。

首版固定 **source-axis producer**：所有可用的实际 `overall_group_axis` 都提供一列参考视图，同一 query/plane 的全部合格家具组保留为行。无需人为场数 `K`、固定区域、邻域半径、阈值或虚构角度；不选 winner、不做 mode detection，也不把全场 resultant 改名为 `k`。不同视图可重叠，行不跨场归一。

这些是可使用的轴支持场视图，不是发现的真实组织簇。完全平行的参考列仍按 anchor 身份保留，可标为相同方向的 aliases/views；不把它们变成多票，也不增加近似合并算法。只有组轴证据时，空间分离的平行组织不可区分。

## 来源、身份与缓存

```text
实际组轴 envelopes
  → 固定 source-axis producer 生成参考视图身份/轴来源
  → 全 scope Support[g,k]
  → non-self profile 与只读软视图方向描述
```

这只是包内计算步骤，不新增 proposal envelope 框架或第二套 field kernel。`EvidencePackage.evaluate(source_envelopes)` 签名不变；producer 从实际 source envelopes 读取 anchor 身份与参考轴。首版不先实现 external/derived proposal modes。

| 身份项 | 首版约定 |
| --- | --- |
| logical `field_id` | scene namespace、不可变 anchor group ID、query/plane identity、recipe ID；不含当前角度或运行时间 |
| reference | anchor 的 `overall_group_axis`、实际角度、clarity、状态及完整来源链 |
| scope | 同一 query/plane 下全部合格家具组的规范化身份集合 |
| extent | `proposal_extent` absent/unspecified；不虚构 inside/outside、边界张力或候选主 profile |
| content fingerprint | 规范化 scope、query/plane 数据、源轴/envelope 内容与身份、recipe/output/schema 版本；排除 timestamp 和递增 revision |

编辑使相关内容指纹改变；撤销回相同内容时恢复原指纹，允许复用原缓存。scene namespace 与源内容指纹分开，不能每次编辑都重建逻辑场身份。freshness 复用现有协议，首版仍为 whole-package invalidation，输出 `recompute_required`、原因和受影响目标；不承诺局部重算。

所有源 envelope、原始/派生渠道、状态与 provenance 完整保留。`(g,k)` 输出经现有 `EvidenceOutputChannel.derived_from` 引用 `g` 与 anchor 的 `overall_group_axis`；同一来源去重引用。共享物理来源仍记录依赖，non-self 不意味着统计独立。组对四通道继续保留，不作为支持或 resultant 的额外票。

## 每个 cell 的最小读数

```text
target = (field_id, group_id)
group_axis_angle, group_clarity
anchor_group_id, reference_axis_angle, anchor_clarity
delta = 最小无向夹角 [0°,90°]
direction_alignment = cos²(delta)
axis_field_support = group_clarity × direction_alignment
status, coverage, source_ids, reference_axis_provenance, formula_version
self_reference, excluded_from_nonself_profile
```

anchor clarity 单列保留，不再乘入支持；不能把组对 `min(ca,cb)` 偷换成上述函数。原始角度/清晰度与方向相似值始终可回查，支持投影不丢弃其他证据渠道。

- 组轴缺失、无效或退化：保留 cell 及原因，角度/支持不可用，不填零。
- clarity 为 0 但方向有效：保留方向读数，支持为已知 0；不得把 unknown 改成此类 0。
- 非空 scope 但无可用 anchor：零个有效参考视图，输出引用实际输入轴渠道的 scope-level not_available 诊断，不制造默认场；empty scope 由 caller 在 evaluate 前报告 unavailable，不放宽共享 core 的非空 envelope/output 契约。
- 自身 cell 可计算：`Support[k,k]=c_k`，标 `self_reference=true`、`excluded_from_nonself_profile=true`；这是参考定义产生的读数。
- source-axis 参考无需 leave-one-out 重估方向。LOO 仅属于未来另行审阅的 derived-reference recipe。

## profile 与软视图方向描述

每个 `k` 保存完整 scope 支持向量。**non-self profile** 排除 anchor，报告已知值算术均值、valid/expected 数、覆盖率、状态计数及缺失原因；`expected=N_scope−1`。有效零支持计入覆盖，未知不填零；部分覆盖的均值标 `partial`，无已知值时均值不可用。singleton 的 non-self 均值不可用、覆盖率不适用，不能报告满覆盖。没有 extent 就不称其为候选强度或 extent 内/外 profile。

另给一个下游只读的软视图方向描述，以回答“把这个场视图当单位，其总体势怎样”：

```text
w_gk = Support[g,k]
Q_k = Σ_valid g∈scope w_gk × exp(i × 2 × theta_g)  # 描述包含自身
view_direction = arg(Q_k)/2
view_coherence = |Q_k|/Σw_gk
```

同时报告总支持、valid/expected 覆盖、`positive_weight_count`、`self_included=true`、`self_weight` 与 `self_weight_fraction`（总支持大于 0 时）。仅 anchor 有正权重时可计算描述方向/一致性，但标 `anchor_only`，不能称 consensus。总支持为 0 时方向/一致性为 `not_available/no_positive_support`，原始零支持仍是 computed；方向抵消时方向 null/ambiguous、一致性为 0，只用数值容差，不引入感知阈值。缺失造成的 partial coverage 与方向状态分开。

这里只用支持权重一次，不能再乘 clarity 或调用会再次乘 clarity 的旧汇总 helper。旧全场 helper 对少于两个正贡献不给 coherence；本只读描述允许正确标注的 singleton resultant/coherence 1，不改变旧诊断语义。它不更新 `theta_k`，不验证支持是否成立，不回写场，也不新增最终 field-strength 总分。non-self profile 仍排除自身；两种读法保留原始向量。

## 数学能力与参考边界

标量 `F(alpha)=Σ_g c_g cos²(theta_g−alpha)=C/2+Re[exp(−i2alpha)R]/2`，其中 `C=Σc_g`、`R=Σc_g exp(i2theta_g)`，只有常数项与 doubled-angle 一阶谐波；等权交叉方向可能使 F 变平/原 resultant 抵消。因此完整响应矩阵必须保留，不能把标量汇总解释成多方向 mode 分解或真实场数量。`Q_k` 是另一种含支持权重的方向描述，不声称它只有相同的一阶矩，也不由它发现 mode。参考支持投影、完整 `E`、通用 `M` 与只读方向描述不能互相替代。

- [Ferraro & Giordani, *Soft clustering*, DOI 10.1002/wics.1480](https://doi.org/10.1002/wics.1480)：借鉴软支持表达；fuzzy 行和为 1、possibilistic 的 gamma/fuzzifier 都不直接采用。见[保留的全文阅读](../../project/evidence/research/Ferraro2020_Soft.md)。
- [SciPy circmean](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.circmean.html)：参考 mean-resultant argument；180°周期/加权为本设计数学适配，不声称该 API 提供本方案，抵消时不采用实现相关角度。
- [scikit-fuzzy c-means](https://github.com/scikit-fuzzy/scikit-fuzzy/blob/master/skfuzzy/cluster/_cmeans.py)：参考矩阵组织；固定 cluster count 与跨 cluster 归一假设不采用。研究留档见[融合研究笔记](../../project/evidence-field-fusion-kernel-research-note.md)。这些参考不证明支持已校准为 membership。

## 指定 IFC 验证与结果审阅

已复用指定 IFC 指纹 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077` 下保留的组轴 envelopes 与同源平面几何；未重提 IFC、未创建模拟布局。回放实际产出 **37×37=1,369 cells，37 self、1,332 non-self**、37 个 non-self profile 和37 个只读软方向描述；证据目录为 `outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z/`，详见[回放记录](../../project/evidence/group-axis-source-axis-field-v1.md)。

每个参考视图输出同一 IFC 平面上的完整组支持/状态图，标明 anchor、自身读数和来源；另存完整矩阵、profile、只读方向描述、contract/status 与 manifest。图不能用硬边界、阈值边或单色 winner 代替支持。测试/回放检查完整范围、0°/180°、状态不补零、来源不丢失、non-self 分母、仅一次清晰度、顺序稳定和 edit/undo 缓存；未被真实源覆盖的分支如实记未覆盖。

2026-10-31，用户查看最终矩阵和代表场 IFC 平面图后答复“不错，我理解了”，owner 接受当前结果语义；[可视化记录](../../project/evidence/group-axis-source-axis-visual-preview-v1.md)保留图面、数值检查和浏览器交互未验证的限制。执行状态由[主计划 checklist](../plans/2026-10-26-group-attribution-evidence-field-implementation.md)持续维护：.11a/.12（含 .12.6）已完成；下一项 .14 冻结 hierarchy/merge spec，再做 .15 implementation plan，两项仍未完成。当前验收不批准归并算法或其他证据包。
