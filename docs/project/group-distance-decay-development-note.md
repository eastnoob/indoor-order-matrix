# 距离衰减开发笔记

日期：2026-11-11。状态：**讨论草案，尚未冻结衰减公式或实现。首轮只使用欧几里得距离。**

## 工作线与范围

- jj workspace：`group-distance-decay`，路径 `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/group-distance-decay`。
- 本地 bookmark：`codex/group-distance-decay`；基线 `d0e7e73a0585e8011220d8c7dccb4ab16a6508e5`；首个 change ID：`zuwxrrnywlowmywroomxvnuwpkvtwlln`。Owner 是唯一版本写入者；本轮首个提交只新增本笔记，不推送、不合并。
- 继承[目标边界](grouping-goal-alignment.md)和[证据包最小规范](../superpowers/specs/2026-10-30-evidence-package-minimal-standard.md)。本研究接续[大 checklist 的距离交付](../superpowers/plans/2026-10-26-group-attribution-evidence-field-implementation.md)，不改写既有阶段、不提前勾选验收。
- 只讨论家具组整体之间的关系。保留纯轴、组间关系、合力、hierarchy 及全部原始距离；距离条件结果只能具名追加。场允许重叠，不生成唯一硬分组或边界。

## 已确认的要求

1. 衰减连续发生；不人为设置有效半径、近远阈值、截断距离或邻居数量。不把自动取均值、中位数或第几个近邻伪称没有尺度假设。
2. 房间扩大或增添无关家具、但该组对几何和通路未变时，该组对的距离响应应不变。整体场可以因其他有效关系而改变；缓存也可以因全量失效策略而需要重新核验。
3. 单位换算不改变结果；不能用全房最大距离、家具数量或全场距离分布暗中改变原组对的量尺。
4. 距离项可以选择一个或多个距离。**首轮选择集只有 `euclidean_distance`；不读取 `path_distance` 的数值、不以其渠道可用性作为纯欧氏计算条件。**共享包级 freshness 仍按既有契约执行。
5. 原始米值是描述量，不是越大越支持的证据。派生支持须非负、越大越支持，并保留原值、状态、公式、尺度和来源；数值归一到 `[0,1]` 不等于已经客观校准。

## 距离选择与未来组合口

复用现有 `EvidencePackageChannelReference` / `EvidencePackageDependency`，不新增包框架、注册表或专用距离类型。

| 位置 | 本轮规定 | 后续扩展边界 |
| --- | --- | --- |
| 选择 | 每个实际无序组对选择一个完整的 `package/output/target/channel` 引用 | 可选择多个具名引用；同名渠道的不同组对必须分开定位 |
| 读取 | 固定质心到质心 `euclidean_distance`，单位 m | 核对源、端点组对、分析平面、域/范围、单位以及各自查询语义是否相容 |
| 解释 | 原始距离通过具名、带版本的衰减函数产生距离响应 | 每个距离先保留自己的响应，再进入显式组合函数；原始距离与分项响应均不得丢弃 |
| 组合 | 单输入恒等：`H({w_E}) = w_E` | 多输入必须声明组合方法、版本、输入角色、参数和状态策略；没有这些声明就不产出联合数值 |
| 输出 | 原始距离引用 + 响应定义/尺度 + 状态 + lineage | 联合结果具名追加；它不是新的独立票数，也不能把同一距离重复计权 |

推荐的数据流为 `选择距离 → 分别解释/衰减 → 显式组合 → 可选地调制方向支持`。这是接口草案，不是新增运行时 API。每段计算、函数版本、实际依赖与产物仍由现有渠道/输出函数管理。

本轮不选多距离组合公式：不默认求和、平均、等权、乘积或 soft OR。未来组合 `H` 至少须声明 `[0,1]` 输出及端点含义，并在其他输入固定时保持“距离增加不增强支持”；是否对称、补偿或要求共同成立由其命题决定。相同单位不代表欧氏距离与路径距离是两条独立证据。

缺失、unknown、outside、invalid、stale 和 unavailable 不填零、不假装无限远，不临时删掉必需输入或改变分母。未来确证不可达的路径如何影响组合须单独定义；纯欧氏输出不靠路径失败来裁定。缓存未选中的渠道仍保留，不能因本轮不用就删除。

## 上一轮衰减草案：保留尺度响应，不先定唯一范围

一种待比较的表达是：

```text
d_E(g,a) = 两个家具组整体投影 union 的固定质心间欧氏距离
w_E(g,a; ell) = exp(-d_E(g,a) / ell), ell > 0
C_E(g,a; ell) = A(g,a) * w_E(g,a; ell)
```

`A(g,a)` 是已有源轴视图中 g 对参照组 a 的方向支持，不新造方向总分；a 是参照家具组，不是场区域。`ell` 与距离同单位，是响应曲线的尺度坐标，**不是已选好的有效半径**。先完整保留 `d_E` 和函数定义；查询尺度不重新计算几何距离。欧氏组对缓存只有非自组对，自项语义另循原势包规则，不伪造自组对缓存。

在固定 `ell`、有限非负距离和有效输入下，该候选数学上连续、落在 `[0,1]`，且距离越大响应越弱；相同距离在相同尺度使用同一函数。单位换算必须同时换算 d 与 ell。整体布局实际放大不是单位换算，不能擅自宣称固定物理尺度下结果仍不变。数值下溢不能被解释为硬边界或无归属。

**这还没有解决自然定标。**指数形状也是模型假设；保留多尺度只是没有先挑唯一尺度，不等于已找到唯一客观强度，也不等于用户接受多尺度作为最终结果。不得偷选一个 ell、对任意尺度区间平均，或让显示采样范围成为算法截断。若后续必须产出单个数值，尺度或消去尺度的规则仍需有可辩护依据。

## 复用位置、缓存与首轮观察

- [共享核心](../../features/field_core.py)：`EvidencePackageChannelReference`、`resolve_evidence_package_channel`、输出及 freshness 校验。
- [距离包](../../features/group_distance_evidence_package.py)：现有 `euclidean_distance` / `path_distance` 两通道；原始渠道定义和缓存均不改。
- [势包](../../features/group_axis_potential_field.py)：已有纯方向支持；距离调制尚未实现。
- [最新距离交付证据](evidence/group-distance-ifc-v1.md#two-channel-distance-evidence-publication--2026-11-07)：37 组、666 对、1,332 个距离输出。实际缓存位于 `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge_proxy/outputs/design/group_distance_ifc/run_global_full_current_20261106_merged/distance_evidence_package/group_distance_package_output.json`；不要把 sibling 产物说成本工作区已经生成。

未来结果身份须绑定选择的渠道引用、完整输入内容、衰减/组合函数版本及实际使用的尺度；复用现有内容指纹与 freshness，不只相信旧 `fresh` 收据。改变衰减函数不要求重新寻路；原距离可否复用仍须校验真实依赖。未选路径不作为数值输入，包级失效边界不在本轮改成渠道级失效。

保存读回放行数值前须独立提供 `current_source_envelopes`，核对 `target/query/channel_set/cache_identity/raw_status/value/support/source_ids`；上下文缺失为 unavailable，来源、query 或 plane 不匹配则拒绝。旧 `fresh` 收据不能替代这道现有检查。

首轮视觉目标：仅用指定真实 IFC 的欧氏距离，先看同一批组对的原始距离和候选响应曲线；若展示几个尺度切片，明确它们只是图面采样，未被选为事实或生产默认。不得新造模拟布局来获得理想衰减效果。未对齐势与距离的源、组身份、分析平面及范围前，只能看距离响应，不能将两套旧缓存直接相乘。

## 持续维护 checklist

执行中每完成一项都补充真实证据并更新勾选；发现偏离或未决先记录，不用实现结果反向改掉要求。

- [x] 新建独立 jj workspace / bookmark；首个新增文件是本开发笔记。
- [x] 记录用户约束、仅欧氏首轮、单距/多距输入口及未决组合边界。
- [x] 保存上一轮多尺度候选，明确没有冻结公式或解决自然定标。
- [x] 独立审查（2026-11-11）：SPEC PASS / QUALITY Approved；7 个本地链接及代码定位核验通过，补齐独立 `current_source_envelopes` 放行门。未运行算法、IFC 或 Blender。
- [ ] 裁定首轮衰减表达及可视化口径；需要方向调制时先核对同源、同平面和同范围。
- [ ] 实现最小欧氏试验，复用已认证缓存；记录函数版本及输入身份。
- [ ] 用指定 IFC 产出欧氏对照图；核验连续性、单调性、单位换算及无关场景变化不改组对数学响应；区分技术检查与用户视觉结论。
- [ ] 根据观察回到自然定标问题；多距离组合继续暂缓，不因接口预留而提前实现。

本轮仅建立工作线与笔记，不表示试验、主线整合、距离调制势或视觉验收已完成。
