# v2.2 连续几何与采样评价网格桥接计划

## 1. 核心判断

OCTA/SVG 中的图形是连续几何对象。桌子不是评价网格里的若干格子，桌子只是被评价网格采样后，会在 debug map 中表现为若干 occupied cells。

因此，图形不需要对齐采样网格。它可以落在采样格中间、跨越采样格、偏移，也可以旋转或表达成 polygon。评价网格只负责解释、debug 与 reachability 近似，不定义家具本体，也不应决定核心连续几何冲突是否存在。

当前路线应表述为：

```text
continuous geometry + sampled evaluation grid
```

而不是：

```text
furniture = grid blocks
```

## 2. 三层桥接模型

### 2.1 OCTA/SVG：连续视觉形态

职责：

- 渲染用户看到的图形。
- 保持 OCTA 原生的 shape / size / orientation / position 语义。
- 允许同一种图形在不同网格位置重复出现。

当前状态：

- `Table(size=...)` 可被转换为 OCTA cell。
- `_stim.Show()` 输出 SVG 图形。
- 图形尺寸不是采样格数量，而是连续空间中的宽高。

### 2.2 SceneModel / Rect / Polygon：连续空间表达

职责：

- 把用户输入和 OCTA 布局转换为连续空间对象。
- 表达实体 id、type_id、role、位置、尺寸、朝向、profile override。
- 作为 grid backend 与未来 polygon backend 的共同输入。

当前状态：

- `SceneModel` 已存在。
- `Rect` 支持 axis-aligned bbox、RoadBand 与 ClearanceBand。
- `Polygon` 支持 rotated furniture footprint 与 AffordanceBand polygon。
- `_build_scene_model()` 已处理 `fit_to_layout=True` 下的 cell center 与 align/offset。

后续方向：

- 继续扩展 `Polygon` 或 `ShapeGeometry` 表达圆、异形边界和更复杂 SVG/path。
- 不把 polygon 暴露成普通用户必须写的输入格式。

### 2.3 SpatialGridBackend：采样解释、debug 与 reachability 近似

职责：

- 将连续空间按 `resolution` 采样成解释网格。
- 生成 occupied / affordance / road / clearance / conflict 的 debug map，帮助理解连续几何判定的来源。
- 保留 BFS reachability 等天然适合网格近似的问题。

关键原则：

- `resolution` 只影响采样精度，不改变图形本体定义。
- 图形不需要与采样格边缘对齐。
- 同一个图形在不同 resolution 下可能覆盖不同数量的采样格，但仍是同一个连续图形。
- road-affordance / road-furniture / clearance-furniture 等核心冲突应先由连续几何判定，再 rasterize 到 sampled grid 做解释。
- `resolution=20` 与 `resolution=10` 不应改变连续冲突是否存在；它们只改变 sampled cells 的数量与显示细节。

### 2.4 Road / RoadBand / ClearanceBand：通行空间与净空检查

职责：

- `Road` 是用户层通行空间/道路语义对象，承载 `axis`、`between`、`width`、`offset`、`level`、`priority` 等意图。
- `RoadBand` 是内部连续通行空间几何，首批可用 axis-aligned rectangle 表达。
- `ClearanceBand` 是内部净空检查几何，由 `AisleProfile.min_width` 或 `Road.min_clearance` 生成。
- `RoadAxis` 不作为核心公开类；它只作为 `Road` 的内部字段或 helper，用于把语义位置换算成连续几何。
- `RoadBand / ClearanceBand` 与 furniture bbox、affordance band 处在同一连续几何层。
- sampled road / clearance cells 只是 `SpatialGridBackend` 对连续几何的采样评价结果，不是道路或净空本体。

关键原则：

- `AisleProfile.min_width` 表达最小通行净空要求，不是道路实体宽度。
- 道路/通行空间不等于 analysis grid。
- 道路可以有自己的宽度、偏移、层级和优先级，即便它最终会被采样到 grid cells。
- 当前 object-centered bbox halo corridor 是 `ClearanceBand` 的 temporary MVP 近似，用于快速暴露净空不足和通行冲突。
- 后续 notebook 应先画连续 `RoadBand / ClearanceBand`，再叠加 sampled road / clearance / conflict cells。

### 2.5 RoadNetwork：semantic grid 轴网道路系统

职责：

- `RoadNetwork` 是一组 road intents，不是 sampled grid。
- 对 3x3 semantic grid，默认可生成 4 条 vertical axes + 4 条 horizontal axes，共 8 条 road axes。
- 每根 axis 都可以有 `enabled / width / min_clearance / offset / level / priority`。
- `RoadNetwork` 展开后仍生成 `RoadBand / ClearanceBand` 连续几何，再由 `SpatialGridBackend` 采样。

road-road 合并规则：

- road-road overlap 默认 boolean union，不生成 violation。
- road-road intersection 是 circulation node / intersection，不是 conflict。
- union 区域的 `width` 取 max。
- union 区域的 `min_clearance` 取 max。
- union 区域的 `priority` 取 max。
- source road IDs 保留到 metadata，用于 notebook debug 和后续解释。

冲突边界：

- road/clearance 与 furniture overlap 才是 hard bottleneck 或 clearance blocked。
- road/clearance 与 affordance overlap 是 soft conflict，除非后续 profile 明确要求 hard。
- road/clearance 与 obstacle/boundary overlap 可作为 hard violation。
- road-road overlap 不进入 conflict / bottleneck。

## 3. 当前 MVP 边界与转向

当前实现已经在走连续图形与采样评价的中间路线，并且已经具备以下连续几何本体：

- `Furniture footprint Polygon`
- `AffordanceBand Polygon`
- `RoadBand / ClearanceBand` axis-aligned `Rect`

仍然存在的边界：

- 圆桌/椭圆桌在空间评价里暂未精确按曲线采样。
- road-road union 首批主要依赖 sampled cell set 去重，还不是精确连续布尔。
- sampled grid 对窄 road、旋转 polygon、affordance edge band 的解释会受 `resolution` 影响。
- grid-based conflict 可以作为解释层，但不适合作为 road-affordance / road-furniture 等最终几何判定来源。

这些是采样解释边界，不是连续几何路线错误。下一步应引入 `ContinuousConflictEvaluator`：连续几何先判定冲突，再 rasterize 到 `SpatialGridBackend` 生成 debug cells。

## 4. 后端演进路线

### 4.1 GridBackend

用途：

- notebook / debug map 可视化解释。
- BFS reachability 与通行连通性近似。
- 将连续几何和连续冲突结果 rasterize 成 sampled cells，用于 score explanation。

保留原因：

- reachability / aisle BFS 天然适合网格。
- 分数来源容易解释。
- 与未来 polygon 不冲突。

边界：

- 不再作为 road-affordance / road-furniture / clearance-furniture 的最终冲突本体。
- `resolution` 改变只应改变解释细节，不应改变连续冲突是否存在。

### 4.2 PolygonBackend

用途：

- 精确表达旋转矩形、圆、异形桌、边界和障碍物。
- 生成更准确的 affordance 区域。
- 支持 CAD / SVG / path 等更复杂几何输入。

注意：

- PolygonBackend 不替代用户 API。
- PolygonBackend 不应推翻 `SceneModel`。
- PolygonBackend 是连续几何层的精度增强。

### 4.3 HybridBackend

用途：

- 先用 continuous geometry / polygon 计算精确区域和核心冲突。
- 再 rasterize 到采样网格，用于 reachability、debug map 和评分解释。

建议方向：

```text
SceneModel
  -> ContinuousConflictEvaluator 判定核心 overlap / blocker / bottleneck
  -> rasterize 到 SpatialGridBackend
  -> BFS / coverage explanation / debug map
```

这条路线可以同时保留几何精度和网格解释性。

## 5. 测试与验收方向

后续实现时应补充以下测试：

- 偏移桌子不贴采样格边缘时，仍能产生 occupied / affordance / conflict。
- `RoadBand` bbox/geometry 不随 `resolution` 改变。
- `ClearanceBand` bbox/geometry 不随 `resolution` 改变。
- 修改 `resolution` 只改变 sampled road / clearance cells 数量，不改变道路本体宽度、净空要求和位置。
- road band 与 affordance band 重叠时，能产生 affordance/aisle conflict。
- 同一连续 road-affordance overlap 在 `resolution=20` 与 `resolution=10` 下都应判定存在冲突。
- `resolution` 改变只影响 sampled conflict cells 数量，不改变 continuous conflict result。
- 修改 `resolution` 会改变采样格数量，但不改变 `Rect` / 图形本体尺寸。
- 同一 `SceneModel` 可被 GridBackend 和未来 PolygonBackend 读取。
- polygon/hybrid 结果与 grid MVP 结果在简单 axis-aligned 场景下保持一致或近似一致。
- debug map 明确标注采样网格是评价结果，不是家具本体。
- debug map 明确区分 continuous `RoadBand / ClearanceBand` 与 sampled road / clearance cells。
- 3x3 RoadNetwork 默认生成 8 条 road axes：4 vertical + 4 horizontal。
- road-road overlap 在 debug 中表现为 union/intersection，不出现 road-road violation。
- union 后 sampled road cells 数量小于或等于逐条 road cells 简单相加，避免重复计数。

## 6. 当前决策

- 继续保留 `SpatialGridBackend` 作为采样解释、debug heatmap 与 reachability 近似后端。
- 不把家具建模为格子块。
- 不把 road/aisle 建模为格子块；`RoadBand / ClearanceBand` 是连续几何，grid 是评价采样。
- RoadNetwork MVP 已落地；下一步不是继续扩大 sampled scoring，而是引入 `ContinuousConflictEvaluator`。
- continuous geometry / polygon 是冲突判定本体，sampled grid 是解释层。
- 当前 aisle halo 不删除，先作为 fallback 或 legacy MVP。
- road-road overlap 不算 conflict；精确连续 union 后续再补，当前优先解决 road/clearance 与 furniture/affordance 的连续冲突判定。
