# v2.4 ContinuousConflictEvaluator 连续几何冲突评价计划

## Summary

下一阶段引入 `ContinuousConflictEvaluator`，把核心冲突判定从 sampled grid 推回连续几何本体：先判断 `Furniture footprint Polygon`、`AffordanceBand Polygon`、`RoadBand / ClearanceBand` 之间是否真实 overlap，再把结果 rasterize 到 `SpatialGridBackend` 作为 notebook/debug 解释。

这一步不是删除 sampled grid。`SpatialGridBackend` 继续负责 sampled explanation、debug heatmap、BFS reachability 和 notebook overlay；它不再作为 road-affordance / road-furniture / clearance-furniture 等核心冲突的 source of truth。

## 1. Architecture

核心链路：

```text
TableGrid / RoadNetwork intent
  -> SceneModel continuous geometry
  -> ContinuousConflictEvaluator
  -> structured violations / bottlenecks
  -> rasterize conflict sources to SpatialGridBackend debug cells
```

连续几何本体：

- `Furniture footprint Polygon`：家具主体的真实连续占用，包含 rotation。
- `AffordanceBand Polygon`：家具 local edge 生成的可供区域，随家具 orientation 一起旋转。
- `RoadBand / ClearanceBand`：道路与最小净空的连续矩形区域，首批保持 axis-aligned `Rect`。

sampled grid 的位置：

- sampled grid is explanation/approximation, not conflict source of truth。
- `resolution=20` 与 `resolution=10` 不应改变 continuous conflict 是否存在。
- `resolution` 只改变 debug cells 数量、热力图颗粒度和 BFS 近似精度。

## 2. Evaluator Targets

首批 `ContinuousConflictEvaluator` 只处理最关键的空间关系，避免一次性把 geometry 系统做重：

- `RoadBand / ClearanceBand` vs `Furniture footprint Polygon`
  - `ClearanceBand` 被 furniture footprint 占用时，输出 hard bottleneck。
  - `RoadBand` 与 furniture footprint overlap 时，按 road blocked / circulation blocked 记录。
- `RoadBand / ClearanceBand` vs `AffordanceBand Polygon`
  - road/clearance 与 affordance overlap 时，输出 soft `affordance_road_conflict` 或 `affordance_clearance_conflict`。
  - 后续 profile 可把特定 affordance/road 关系提升为 hard。
- `Furniture footprint Polygon` vs `AffordanceBand Polygon`
  - 其他家具阻挡某家具 affordance 时，输出 affordance blocker。
  - owner 自身 footprint 与自己的 affordance band 不算 blocker。

road-road 关系：

- road-road overlap 不生成 violation。
- road-road intersection 是 circulation node / intersection。
- 精确连续 union 后续再补；本阶段只保证 road-road 不被误报为 conflict。

## 3. Geometry MVP

不引入 `shapely`，先用轻量几何 helper 覆盖 MVP：

- `Rect` vs `Rect`
- `Rect` vs `Polygon`
- `Polygon` vs `Polygon`

相交判定可沿用当前轻量逻辑：

- 任一 polygon vertex 在另一 geometry 内。
- 任一 rect corner 在 polygon 内。
- 任一边段与另一 geometry 边段相交。
- 纯边界接触是否算冲突，应保持现有 `Rect.intersects()` 的语义：零面积贴边不作为 overlap。

后续如果圆桌、SVG path 或复杂 polygon 增多，再考虑引入更完整的 geometry backend。

## 4. Report And Debug

公共 report 结构尽量保持兼容：

- `affordance.violations` 继续承载 affordance blocker 与 affordance/road soft conflict。
- `aisle.bottlenecks` 继续承载 road/clearance hard bottleneck。
- `aisle.objects[...]` 可保留 sampled explanation 字段，但新增 continuous source metadata。

建议新增 debug source：

- `continuous_conflicts`
- `continuous_bottlenecks`
- `rasterized_conflict_cells`

debug grid 仍可显示 sampled conflict cells，但这些 cells 来自连续冲突结果的 rasterized explanation，而不是作为原始判定来源。

## 5. Implementation Steps

当前状态：以下 MVP 已落地；本节保留为实现记录与后续维护索引。

1. 新增 `features/affordance/continuous_conflict.py`
   - 定义 `ContinuousConflictEvaluator`。
   - 暴露小型 public helper，例如 `geometry_overlaps(a, b)`。
   - 必要注释写在几何相交与 owner/self-filter 逻辑处。

2. 接入 spatial access 汇总流程
   - 在 `evaluate_spatial_access()` 中先运行 continuous conflict。
   - 再把 continuous conflict source rasterize 到 `SpatialGridBackend` debug layers。
   - BFS reachability 仍由 grid 负责。

3. 保持 notebook 解释
   - overlay 同时画 continuous geometry source 与 sampled explanation cells。
   - 对 r=20 / r=10 做对比：continuous conflict count 不变，sampled cells 数量可变。

## 5.1 已落地状态

- `ContinuousConflictEvaluator` 已成为 road/clearance/furniture/affordance 冲突是否存在的 source of truth。
- `debug.continuous_conflicts` 记录连续冲突来源；玫瑰红 overlay 优先画 continuous overlap polygon。
- `clearance_conflict` 等 sampled debug matrix 来自 continuous conflict rasterize，只用于解释和高亮。
- `SpatialGridBackend` 仍保留 BFS reachability、sampled affordance/road/clearance layers 与 notebook heatmap。
- `occupied` 阻挡采样使用 50% 面积覆盖阈值，避免旋转家具小面积擦边导致 BFS 误阻断。

## 5.2 已落地：Continuous Affordance Coverage

`affordance.coverage` 已从 sampled cells 切换为连续面积口径：

- `required_area`：AffordanceBand polygon 的连续面积。
- `blocked_area`：其他 furniture footprint、RoadBand / ClearanceBand conflict 与 obstacle 对可供区的连续 overlap 面积。
- `effective_area = required_area - blocked_area`，后续可按 profile 配置 cap / priority / hard-soft 权重。
- sampled affordance cells 继续作为浅黄色 debug layer，但不再决定 coverage score。
- `resolution=20` 与 `resolution=10` 可以显示不同 sampled cells，但 continuous coverage ratio 应保持稳定或只因显示四舍五入变化。

后续剩余边界：

- 多个 blocker 重叠同一 affordance 子区域时，当前首批实现按 overlap 面积累加并 cap 到 `required_area`；后续可升级为 continuous union。
- 圆桌、复杂 SVG/path 与非凸区域仍需要 PolygonBackend / HybridBackend 扩展。

## 6. Test / Acceptance

文档验收：

- `plan_v1.md` 标记 RoadNetwork MVP 已完成。
- 文档明确写出 `SpatialGridBackend` 是解释/近似层，不是 road-affordance 冲突本体。
- 本文档包含 `ContinuousConflictEvaluator`、`Furniture footprint Polygon`、`AffordanceBand Polygon`、`RoadBand / ClearanceBand`。

后续实现验收：

- r=20 与 r=10 对同一连续 road-affordance overlap 都能判定存在冲突。
- `resolution` 改变只影响 debug cells 数量与显示，不改变连续冲突是否存在。
- `ClearanceBand` 与 `Furniture footprint Polygon` overlap 时输出 hard bottleneck。
- `AffordanceBand Polygon` 与 `RoadBand / ClearanceBand` overlap 时输出 soft conflict。
- road-road overlap 不出现在 `affordance.violations` 或 `aisle.bottlenecks` 中。
- notebook 同时展示 continuous conflict source 与 sampled explanation。

Continuous Affordance Coverage 验收：

- 同一场景在 `resolution=20` 与 `resolution=10` 下，`affordance.coverage_ratio` 基于连续面积保持一致。
- 浅黄色 sampled affordance cells 数量可随 resolution 改变，但不改变 coverage score 的本体判断。
- 旋转家具的 local affordance band 面积与 blocker overlap 面积按 polygon 计算。
- notebook 同时打印 continuous coverage 数值与 sampled debug cell 数，避免用户误以为浅黄色格子就是评分本体。

## Assumptions

- 本阶段不引入外部几何依赖。
- `RoadBand / ClearanceBand` 首批仍是 axis-aligned `Rect`。
- sampled area-intersection grid 先保留，作为比 center-point 更合理的解释层。
- Continuous conflict 已先解决“是否冲突”的稳定性；冲突面积、coverage 面积口径、扣分曲线和权重校准后续再细化。
