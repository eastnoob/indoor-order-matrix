# 家具组关系历史审计与当前边界

日期：2026-10-28

这份记录把早期 2D 实现与当前 IFC 组证据包逐项对照。目的不是把旧算法一锅端搬进当前场，而是确认哪些已经属于家具组/组对关系，哪些属于别的分析层。

## 当前结论

- 家具组是当前公开证据的最小单位；组对是当前关系证据的最小单位。
- 单体家具方向通道 `member_frame`、`member_axis` 暂时静音。底层计算、绑定和旧 v1 输出保留为审计与回溯材料。
- 组对几何中的 member-pair gap/contact/overlap 保留为可重放审计事实；在组级聚合规则审阅前，不把它们解释为组级答案。
- `group_self_description` 已有的 semantic soft-negative、显式互斥声明和对称 `local_neighborhood` 继续作为组对关系库存记录；当前包只把它们登记进 provenance，不生成 veto、formal edge、support 或 strength。
- `position_grammar`、`column_grid`、region-shape 和 inter-region network 的目标层不同，暂不并入 `furniture_group_pair` geometry envelope。

## 历史对照表

| 历史来源 | 关系/算法 | 输入与目标层 | 当前处理 |
| --- | --- | --- | --- |
| `nwtxqtluyzro` / `6911662`，`features/group_self_description.py` | 组对 member-pair boundary gap、contact、positive-area overlap、witness/status | IFC/NeutralScene 投影几何；目标是 `furniture_group_pair` | 保留；member-pair 仅 audit-only，组级聚合继续 deferred |
| 同上 | factual type mismatch（soft negative）、`mutual_exclusion` 原始声明 | 组对成员事实标签；目标是组对语义关系 | 保留在 relation provenance；不执行硬 veto |
| 同上 | 对称 `local_neighborhood` | 组对关系图；不选邻居、不生成 membership edge | 保留为历史关系库存；不选边 |
| `pwstwmuwzwlo` 及后续 trend 记录 | group frame / overall axis / layout axis | 组整体 geometry；目标是 `furniture_group` | 当前 trend 包 active；member-frame/member-axis suppressed |
| `position_grammar.py`（6fd824e→02513af→e1f942a） | authored / line / pair / grid / cluster position grammar | ActivityRegion/RoomScope 中的家具组中心与槽位 | 保留独立证据域；不塞入组对几何包 |
| `column_grid.py` 与 2026-07-15 设计 | branch/system/bay、C_global、C_local_profile | Region ↔ ColumnGrid 外部结构关系 | 保留独立证据域；不当作组对距离或同组判定 |
| 早期 region-shape / SpatialNetwork 原型 | region shape、inter-region gap/path network | SVG 场景区域或区域网络 | 暂不并入；单位、scope 和目标层不同 |

## 当前代码承载方式

`features/group_geometry_relation_field.py` 的每个 Envelope 仍以稳定的家具组对为 target。三个几何通道保留原始 member-pair 列表和 source witness，但明确标记 `member_pairs_role = audit_only`，并在观察中写出 `group_pair_aggregation.status = deferred`。Envelope provenance 另记录 semantic relation、local neighborhood，以及 position/column-grid 的未接入理由。

`features/group_trend_alignment_field.py` 的 active channel 只有 `overall_group_axis` 和 `layout_axis`。`member_frame` 与 `member_axis` 继续从底层描述中取得，但写入 `suppressed_channels` 和 audit 字段，不再进入公开 `channel_set`。旧 v1 IFC 产物和 148 张图不删除，作为历史粒度结果保留；新的 runner 使用 v2 schema，并只绘制两个 active channel。

## 未决事项

当前没有批准 `min/mean/any/all/union` 中任何一个组级聚合规则，也没有批准距离衰减、势相似度、强度、candidate、formal edge 或 winner。下一步只能在真实 IFC 平面图上逐项审阅组级聚合所需的输入和状态覆盖，再决定是否形成新的 active relation channel。
