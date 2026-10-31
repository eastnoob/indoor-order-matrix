# 组场层级归并决策笔记

日期：2026-10-31
状态：**历史决策基线；已被 2026-11-01 owner-reviewed frozen hierarchy spec superseded。**

## Supersession notice

本文件保留 2026-10-31 的讨论、未冻结候选和 readiness 记录，不再定义当前规则。现行圆周方向族规则、精确输入/输出、状态、namespace、缓存 seam、指定 retained IFC 验收和实现边界以 [`2026-11-01-group-axis-field-hierarchy-design.md`](../superpowers/specs/2026-11-01-group-axis-field-hierarchy-design.md) 为准；执行顺序和命令以 [`2026-11-01-group-axis-field-hierarchy-implementation.md`](../superpowers/plans/2026-11-01-group-axis-field-hierarchy-implementation.md) 为准。本文中的 complete-link、多条件关系门、formal/nonformal promotion、`compressed` 建议和“至少三组”建议仅作历史，不能由实现者继续采用。

**执行状态续记（2026-11-01）：**`.16.1-.16.3` 已实现并完成指定 retained replay 与索引预览，具体来源指纹、输出计数、freshness 和未覆盖范围见 [`group-axis-field-hierarchy-v1.md`](evidence/group-axis-field-hierarchy-v1.md)。当前接受材料为 `outputs/design/group_axis_field_hierarchy_ifc/replay_v2/` 与 `outputs/design/group_axis_field_hierarchy_preview/run_20261101T101331Z/`；v1/旧预览保留为历史。本记录中的历史候选和 checklist 不再表示当前实现状态；owner 于 2026-11-01 最终 GO，`.16.4` 与总体 `.16` 已在 retained-source/offline 范围内完成，不代表用户现实有效性审阅。

**历史问题及当前更正：**旧预览的 HTML `JSON.parse` 曾舍入大 rational numerators；当前预览以十进制字符串显示精确有理数对，原 machine integer pairs 保持完整。v2 已补 frozen-contract 的 anchor contribution mass/fraction、按 positive contributors 判定 `anchor_only`、zero/no-axis unavailable、canonical modulo endpoint、有效 descriptor admission、profile leaf-cell coverage/status counts、residual known mass/mean 与原始 cell target refs。实际 retained IFC 的支持与拓扑不变；当前预览 17 项 artifact hashes 与 14 项 input hashes 均匹配，索引完整。旧失败记录和产物不覆盖、不删除。

**离线视觉解释（2026-11-01 owner handoff）：**owner 已查看 v2 report/status/direction metadata 及三张 PNG，接受 H204 的 G10/G12 是两个 anchor 而非硬成员、全部 37 行仍有支持，以及 H159/H174 是共享 27 个参考轴的重叠且互不包含 top families。H174 的窄 lifespan `[89.9999974008,90)` 只表示尺度区间，不表示稳健性。浏览器 file URL policy 阻止本地 HTML，未绕过，因此 browser/live UI 未接受。实际 singleton 子集已测，但不是原始 37-group fullscene 的观察；missing/invalid/zero/cancellation/ties/其他 planes 仍未在该 fullscene 观察。

**最终 owner 接受（2026-11-01）：**独立 read-only replay audit 已返回，无 blocker：核对 314,167 项实际 source refs、1,332 项 residual summaries，retained S/J/topology 与 v1 相等；107 个 retained 文件未变，17 项 artifact hashes 与 14 项 input hashes 均匹配。owner 最终 GO 接受本次 retained-source/offline 交付，`.16.4` 与总体 `.16` 完成。此前等待 audit/GO 的状态是当时历史，不是当前阻塞；本结论不宣称 browser/live UI、用户审阅或现实 cluster validity 通过。

## 目标

把一批“以家具组为行、以参考轴为视图”的基础场，自动整理成可重叠的上层
`FieldFamily`/父场，同时保留小场、原始证据和来源。系统不要求用户手工挑选
场，也不把结果压成硬分组。

## 已确认的边界

- 家具组是最小公开分析单位；单体家具层继续 suppressed/audit。
- 场是软的组织可能性。家具组可以同时属于多个场，场之间可以重叠、嵌套或只覆盖部分范围。
- 每个有效 `overall_group_axis` 可以产生一个基础锚定视图；完整作用域的合格家具组都保留为行。
- `0°` 与 `180°` 等价。基础支持仍使用既有 `S(g,k)=clarity_g×cos²(δ)` 语义。
- 原始场、原始渠道、状态、来源、缓存身份和 lineage 永远保留；上层归并只能追加派生记录。
- 基础场不是最终真实组织簇；axis-only 不能区分空间上分离但方向平行的集合。
- 不允许固定 `K`、固定区域、winner、单次贪心吞并或用户手工配组。

## 推荐的归并形态

```text
基础场（每个 anchor 一份）
    → 场之间的关系记录
    → 多尺度的 FieldFamily / 父场
    → 持久场与别名/压缩关系
```

父场是派生观察，不是新的参考轴；它不能回灌成新的 `k`，也不能替换任何
原始基础场。代表轴如需显示，使用家族 medoid 或明确的代表引用，不使用“总
支持最高者吞并其他场”的规则。

## 场之间要保留的关系通道

归并关系是多通道关系，不是新的证据包支持分数。首版可比较：

1. **方向冗余**：两个 anchor 的无向轴方向相似度。
2. **非自身 profile 相似**：比较两个场对共同作用域的 non-self 支持 profile；排除各自 self cell。
3. **共同有效覆盖**：共同拥有可比较读数的作用域比例。
4. **unique residual**：某场中不能由另一个场解释的独特支持；它是小场保留的重要证据。
5. **持久性**：关系在不同尺度或稳定扰动下是否保持。

若需要一个归并资格读法，可先把这些通道作为并列条件，例如
`A=direction_similarity`、`P=profile_similarity`、`C=common_valid_coverage`，
并记录 `min(A,P,C)` 作为保守的关系门。但这只是归并层的关系摘要，不能替换
任何包内原始通道、不能再作为额外证据票，也不能直接叫作支持、概率或强度。

`P` 没有共同有效的 non-self 行时必须是 `not_available`；不得用零或仅凭方向
相似补齐。所有缺失、invalid、partial、conditional 和 incomplete 状态继续逐
通道保留。

## 归并算法候选

- 采用保守的 **complete-link** 家族关系：家族关系由家族内最弱的关系决定，避免
  一个桥接场把多个不相似小场串成一条链。
- 输出多个尺度/完整层级，不预设最终家族数量；停止点和显示尺度必须是记录中的
  派生状态，而不是隐藏的人工常数。
- 允许场重叠。归并只产生“同一 FieldFamily 的关系”，不产生唯一 membership。
- 只在方向、profile、coverage 足够冗余，且 unique residual 很低、状态覆盖足够时，
  才可把一个场标记为 `alias` 或 `compressed`。压缩是显示/存储派生关系，原始叶场仍保留。
- 不使用 Louvain/Leiden、Infomap、固定分辨率模块度或固定 `K` 作为唯一归并器；它们
  的分辨率和网络假设会吞掉小结构，不符合当前场语义。

## 小场生存规则

- 原始基础场永远保留，至少可作为 `anchor_only` 诊断视图。
- 基础场是否晋升为正式上层持久场，不能只看总支持或方向最强；至少要同时检查：
  核心规模、有效 non-self 支持、跨尺度持久性、共同覆盖和 unique residual。
- 一两个家具组组成的小场不能仅因方向相同或支持很高就自动成为正式大组场；但只要
  它有独特方向、独特支持成员、稳定 residual 或明确局部一致性，就必须保留，不能被
  大场吞掉。
- “至少 3 个不同 `AuthoredGroup`”目前只能作为工程诊断建议，不能冻结为建筑学规则
  或正式资格门。
- 规模不能按 `support>0` 的数量计算；`cos²` 尾部很宽，必须使用另行定义的核心读数。
- 共享物理来源、anchor alias 或重复引用不能增加独立投票数。
- 不能证明小场被父场冗余解释时，默认保留小场并标明未决/残差状态。

## 边界和异常

- singleton：保留为基础/`anchor_only`，没有内部 profile 时不制造强度或一致性结论。
- two-group：可以形成诊断家族，但不能仅凭基数晋升为正式持久场；需要通过关系、覆盖
  和稳定性门。
- 无可用轴：输出 `not_available` 及真实来源原因，不构造参考轴或伪造零支持。
- 失效、退化、未知或 incomplete：关系只在可比较通道上计算，其他通道保留状态，不补零。
- 父场不反馈为新参考轴，不重新投票，不改变基础场的缓存身份。
- 当前 axis-only 不能证明空间边界、功能、围合、行为或真实房间；这些须等待其他证据包。

## 与当前计划的关系

这份笔记位于 `g→k` source-axis 支持层之后、跨包融合和其他证据包之前。它补充
“基础场如何自动形成上层场”的设计方向，不修改已经审阅的 axis-only 原始通道、组间
关系层或 evidence-package 最小标准。

当时建议的实现位置（截至 2026-10-31 尚未创建；现已按 frozen spec 实现并验证）：

- `features/group_field_hierarchy.py`
- `test/test_group_field_hierarchy.py`
- `scripts/design/group_level/run_group_field_hierarchy_ifc.py`

当前实现与验证证据见上述 `.16.4` 执行状态续记。

## 是否已经可以作为计划

**历史结论：当时可以作为设计讨论输入，不能直接作为 implementation plan。该门已由 2026-11-01 冻结 spec 和独立 .15 plan 取代。**

这里的“不能直接作为计划”是指：它已经回答了“系统应保持什么语义、哪些东西不能做”，但还没有把每个可执行判断写成确定的输入、输出、公式、状态和验收命令。当前笔记可以作为计划的上游约束和 checklist 依据，不能让实现者据此自行补齐关键规则。

还缺少以下必须冻结的确定性规则：

1. 核心规模、核心成员和“足够小/足够强”的精确定义；不能用 `support > 0` 计数。
2. 方向、profile、coverage 的缺失、tie、容差和关系门规则。方向与 profile 都来自同一轴支持矩阵，不能被误写成互相独立的证据票。
3. complete-link 的层级生成、重叠家族、停止条件和多尺度输出格式；complete-link 只能给出候选层级，不能单独决定正式场。
4. `unique residual` 与 persistence 的可复算定义，以及它们怎样阻止小场被父场吞并。
5. 无合法上层场、singleton、two-group 和 alias/compressed 的最终状态语义。
6. 父场的 `g→field` 支持、参考轴显示、profile 口径、状态传播和 child→parent 来源链。
7. source/output/cache/edit-undo 与现有 freshness 契约的具体接线。
8. 重叠的机器可读表示；单棵 complete-link 树不能自动表达同层的所有重叠候选。
9. 指定 IFC 的运行入口、完整平面图/manifest 验收和测试边界。

## 历史 checklist（截至 2026-10-31；已由 frozen spec 与 implementation plan supersede）

- [ ] 用户审阅本笔记，确认“基础场保留 + 自动多尺度归并 + 小场残差生存”方向。
- [ ] 冻结核心规模、关系门、residual、persistence、alias 和停止条件，形成独立 spec。
- [ ] 将父场输出、重叠关系、状态、来源和缓存身份写入 evidence-package 契约补充。
- [ ] 在 `g→k` 支持层通过审阅和指定 IFC 回放后，才实现 hierarchy builder。
- [ ] 为 hierarchy 写执行计划，明确文件、接口、测试、IFC 平面图和 checklist 维护方式。
- [ ] 实现后再用指定 IFC 验收；不创建模拟家具、模拟场景或预置读数。

### 评估结论（2026-10-31）

- **作为设计决策笔记：通过。** 语义边界、保留原则、小场生存方向和待冻结问题已足够让 owner 审阅下一阶段设计。
- **作为 spec：未通过。** 关键谓词和输出合同仍有多处可由实现者自行解释。
- **作为 implementation plan：未通过。** 尚未定义逐文件任务、接口签名、测试命令、IFC 图面验收和执行期 checklist 门槛。
- **当前允许的下一步：** 只冻结独立的 Field hierarchy / merge spec；在 spec 审阅通过前，不创建 hierarchy builder、不运行新的归并 IFC 结果。

本笔记的完成只证明“设计基线已形成”，不证明归并算法已经批准、实现或通过现实
解释性验证。
