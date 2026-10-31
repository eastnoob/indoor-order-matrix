# Occupancy, analysis-plane, and free-space policy note

Date: 2026-11-01
Status: **Documentation note; no implementation change**

这份笔记固定当前占用与自由空间的边界，避免把“分析平面”“剖切平面”“中心点”和“路径”混成同一个规则。本文只描述已检查到的代码与受控的后续命名；未冻结的策略不会被写成当前实现。

## Current state

### `role-neutral physical occupancy`

`physical occupancy` 是物理实体是否占用空间的查询，不依赖家具资格、家具组、趋势、朝向或服务范围。家具、墙、柱、隔断、柜台、植物等只要有合格的实体几何，就可以成为占用证据；被排除出家具分析的对象仍可阻挡自由空间。

物理占用先经过 `_resolved_physical_occupancy` 解析原始源、合格替代几何、覆盖关系和未知状态，再供自由空间使用。缺失、失败或未决的源不会被当成已知空闲。

### `AnalysisPlane`

`AnalysisPlane` 当前首先是坐标系和法向量框架：它规定如何把几何投影到分析坐标中。它**不自动等于**实体剖切面，也不自动表示某个高度的行走或视线截面。

当前 IFC 适配器明确提供 `ifc-world-plan`：原点为 `(0, 0, 0)`，基为正交世界 XYZ，分析单位为米。这个平面是当前 IFC 计算的输入事实；当前代码没有把 IFC 相机自动转换成 `AnalysisPlane`。相机驱动的分析平面属于后续适配器/工作流能力，不能从当前自由空间结果倒推出已经存在。

因此，“物体在平面以下”不能作为通用占用规则。对任意倾斜或相机定义的平面，这个说法可能把与查询无关的下方几何算进来，也无法说明平面处是否真的有实体。

### Current `FreeSpaceField`

当前 `FreeSpaceField` 是二维、精确网格单元查询，消费已经解析好的分析平面组件：

```text
resolved physical occupancy
  -> whole_height_projection
  -> positive-area cell overlap
  -> FreeSpaceField(bool)
```

当前默认查询可称为 `whole_height_projection`：`plan_projection(..., height_band=None)` 将有效物理占用几何投影到 `AnalysisPlane`。网格单元只要与占用几何存在**正面积交叠**，就标为占用；点接触、零面积线接触或单个点不会决定单元占用。

这表示平面上的实体投影/足迹，不等同于某一高度的行走碰撞，也不等同于完整三维自由体积。

## Recommended policy

### Named query strategies

后续如需区分不同空间问题，应使用明确命名的查询策略：

- `whole_height_projection`：当前默认；用于平面足迹和占用投影。
- `exact_section`：在明确的分析平面上做实体截面查询；需要明确平面、基准、单位和资格状态。
- `height_band_projection`：对明确的高度区间做正垂直重叠查询；用于身体、视线或其他高度带。

`exact_section` 与 `height_band_projection` 目前是**拟议的后续策略，尚未冻结为通用默认**。B3 的世界 XY、`z=1.6 m` 截面是受限的设计/证据路径，不能被当作所有场景的通用高度规则。

### Occupancy is geometric, not point based

中心点不负责决定“是否占用”。占用必须继续由几何与查询的交叠决定，因为细长、凹形、悬空、分离或多孔的对象都可能在中心点附近没有实体，却仍然占用查询区域。

距离模块当前草案提议：对合格组投影 union 取**固定几何质心**，即使它落在组外、空洞或多个不连通组件之间也不吸附、不替换为 representative point、不拆成多个端点。质心落在占用或域外位置不改变端点；自由空间混合距离通过组边缘的全部候选自由格接入，并把质心到接入点作为独立偏移。该规则尚待用户审阅，未冻结；只适用于组距离查询，其他用途是否需要锚点、如何选择仍待单独设计。

### Unknown propagation

`unknown` 只能保持为 `unknown`，不能被转成 `free`。只有经过查询资格证明的几何缺失或不存在，才可以产生该查询下的条件性空结果；缺少源、失败的截面、未定位的不确定性或不完整覆盖都不能证明空闲。

### Free space and paths are separate

`FreeSpaceField` 回答“这个分析网格单元是否被物理占用”。它不负责路径、连通性或最短路。路径/连通性是下游消费者，可以在明确的自由空间状态、邻接规则和不确定性传播规则上另行计算。

直线距离和自由空间路径距离也应保留为不同通道；路径算法不能反过来改变占用场的语义。

### Fixed-centroid group distance (design proposal; detailed draft under review)

家具组距离模块的草案要求固定组质心作为端点，不吸附到某个可变边缘点；同时分别保留质心直线欧氏距离和“固定质心端点偏移 + 自由网格路线 + 另一端偏移”的混合距离。两种读数含义不同，不能互相替代。详细的 footprint/access、网格边界、状态传播和搜索规则以[距离模块设计草案](../superpowers/specs/2026-11-02-group-distance-module-design.md)为单一审阅稿；以下只记当前共同边界，不再另立一套算法版本。

```text
D_hybrid(A, B) = min_access_pairs(
    source_centroid_to_access_offset
    + free_space_route
    + target_access_to_centroid_offset
)
```

这是尚待用户审阅的模块设计，不是当前实现。接入格、偏移、网格图和不确定状态的完整定义只维护在距离模块草案中。任何距离模块实现都必须把欧氏读数、混合距离和混合距离分项分别记录；无路线时不得退回欧氏距离作为答案。

## Unresolved items

以下问题仍需单独冻结，本文不替它们做实现决定：

1. 通用 `exact_section` 的截面资格、退化截面、开放/非流形几何和边界接触语义。
2. 通用 `height_band_projection` 的高度带来源、容差和身体/视线 profile。
3. 分析平面由 IFC 相机、世界平面还是其他明确基准提供时，如何记录 datum、单位和变换。
4. 其他非距离查询若需要家具组锚点，是否采用与距离模块相同的固定几何质心仍未决定；距离草案的端点规则只对该模块有效。
5. 固定质心投影、组边界接触方格和多组件组的访问集合如何在真实 IFC 上稳定提取。
6. 何时可以从局部未知升级为完整自由空间或完整清除度声明。

这些问题不能用“平面以下”这一泛化规则代替。

## Impact scope

本笔记只澄清语义和命名，不改变：

- `FreeSpaceField` 的构造、布尔输出或正面积交叠判定；
- 现有 IFC 源身份、替代几何、来源追踪、状态和未知传播；
- 现有 `whole_height_projection` 默认路径；
- B3 受限截面证据包及其历史输出；
- 路径、连通性、最短路或家具组证据包的实现。

## Code and document references

- [`features/geometry_views.py`](../../features/geometry_views.py)：`plan_projection` 及高度带投影辅助函数。
- [`features/free_space_field.py`](../../features/free_space_field.py)：`FreeSpaceField`、正面积单元交叠和查询状态校验。
- [`features/affordance/grid_backend.py`](../../features/affordance/grid_backend.py)：现有 4 邻域可达性基线；仅作历史/MVP 参考。
- [`features/scene_evaluator.py`](../../features/scene_evaluator.py)：现有采样 BFS 距离代理；尚不是家具组固定质心距离实现。
- [`pixi.toml`](../../pixi.toml)：现有 `networkx` 依赖；A*/Dijkstra 仅作为后续实现候选。
- [`features/neutral_scene_views.py`](../../features/neutral_scene_views.py)：`_resolved_physical_occupancy` 与物理占用来源解析。
- [`docs/project/physical-occupancy-policy-plan.md`](physical-occupancy-policy-plan.md)：物理占用、来源覆盖、高度查询和未知传播的完整政策记录。
- [`docs/indoor_layout_evaluation_matrix_architecture_memory.md`](../indoor_layout_evaluation_matrix_architecture_memory.md)：共享场内核、自由空间边界和当前 whole-height 约束。
- [`docs/software-architecture.md`](../software-architecture.md)：场、自由空间、截面和连通性之间的架构边界。
- [`docs/project/evidence/b3-primary-eye-plane-connectivity.md`](evidence/b3-primary-eye-plane-connectivity.md)：B3 受限截面与连通性诊断；连通性尚未升级为生产路径拓扑。
- [`docs/project/b3-shared-occupancy-enrollment-plan.md`](b3-shared-occupancy-enrollment-plan.md)：B3 共享占用登记及其范围限制。

## Verification record

本次只进行了文档和代码语义检查，未运行测试、未重算 IFC、未生成新可视化，也未修改 API 或实现代码。固定质心混合距离仍是设计提案；剩余风险是：通用 exact section、height-band、完整占用覆盖、访问集合提取和路径拓扑仍未冻结，不能从本笔记推断它们已经实现。
