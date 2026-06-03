# v2.1 对象模型收敛计划：家具类型、实例与网格放置

## 1. 背景与问题

当前 `Table(...)` 已经可以直接作为 `OrderAnalyzer` 的 cell 输入，也能携带 `id`、`align`、`affordance`、`aisle` 等字段。但它同时表达了两件事：

- 家具类型：形状、尺寸、默认可供性规则。
- 家具实例：这个格子里的对象 id、位置、对齐、偏移、局部 override。

在 demo 中写 9 次 `Table(...)` 会让人误以为定义了 9 种桌子。真实语义应该是：定义一种标准桌子，把它重复放进 3x3 网格，再单独修改 `[0][1]` 这个实例。

这属于表达层架构问题。它不是 geometry 精度问题，也不需要立刻用 polygon 解决。

## 2. 目标

- 对齐 OCTA 的使用直觉：先定义一个元素样式，再在网格中重复。
- 区分类型、实例、网格放置三层概念。
- 保留现有 `Table(...)` 直接输入兼容性。
- 让后续 affordance、aisle、repair、generation 都能基于清晰的实例模型继续扩展。

## 3. 三层模型

### 3.1 FurnitureType / TableTemplate

职责：描述一种家具的默认属性。

建议字段：

- `shape`
- `size`
- `type_id`
- `attr`
- `orientation`
- `affordance`
- `aisle`
- `metadata`

示例：

```python
standard_table = TableTemplate(
    size=(64, 44),
    type_id="table.default",
    affordance={"usable_edges": ("right",), "edge_depth": {"right": 36}},
)
```

### 3.2 FurnitureInstance / Placement

职责：描述某个类型在某个位置上的实例化结果。

建议字段：

- `id`
- `row`
- `col`
- `align`
- `offset`
- `orientation`
- `affordance_override`
- `aisle_override`

示例：

```python
placement = Placement(row=0, col=1, id="t12", align="right")
```

### 3.3 FurnitureGrid / TableGrid

职责：批量实例化模板，并输出 `OrderAnalyzer` 可读的 matrix。

建议最小 API：

```python
grid = TableGrid(3, 3, fill=standard_table)
grid.place(0, 1, align="right")
matrix = grid.to_matrix()
```

也可以支持索引风格：

```python
grid[0, 1].align = "right"
```

首批建议优先实现 `place()`，因为它更明确，也更容易测试。

### 3.4 Road / TableGrid.road

职责：用一个用户层 `Road` 概念表达通行空间意图，而不是让用户手动画 sampled grid。

建议最小 API：

```python
grid = TableGrid(3, 3, fill=standard_table)
grid.road(axis="vertical", between=(0, 1), width=80, min_clearance=80)
matrix = grid.to_matrix()
```

RoadNetwork API 草案：

```python
grid = TableGrid(3, 3, fill=standard_table)
grid.enable_road_network(width=80, min_clearance=80)
grid.road(axis="vertical", index=1, width=100)
grid.road(axis="horizontal", index=2, enabled=False)
layout = grid.to_layout()
```

建议语义：

- `axis` 表达道路轴线方向，首批支持 `"horizontal"` / `"vertical"`。
- `between` 表达道路位于哪些 semantic 大格之间，例如 `(0, 1)` 表示第 0 与第 1 条列/行边界之间的通道意图。
- `index` 表达 semantic grid line 编号；3x3 grid 有 4 条 vertical lines 与 4 条 horizontal lines，因此 index 范围是 0..3。
- `width` 表达连续通行空间宽度，不是 sampled grid cell 数量。
- `min_clearance` 表达最小通行净空要求；缺省时默认等于 `width`。
- `offset` 表达道路带相对默认轴线的连续偏移。
- `enabled=False` 表示禁用某根 road axis。
- 后续可增加 `level`、`priority`、`serves`，用于多等级路网和冲突决策。

重要原则：

- `TableGrid.road(...)` 只记录用户层 `Road` intent。
- `TableGrid.enable_road_network(...)` 是 RoadNetwork 入口，用于给每根 semantic grid line 批量生成 road intent。
- 当前 `grid.road(axis="vertical", between=(0, 1), ...)` 兼容保留；后续推荐使用 `index` 表达具体 semantic grid line。
- 内部后续应生成 `RoadBand / ClearanceBand` 连续几何，再交给 `SpatialGridBackend` 采样。
- `RoadAxis` 只作为内部字段或 helper，不要求用户实例化。
- sampled road / clearance cells 是评价/解释结果，不应反向污染用户 API。
- road-road overlap 默认自动 boolean union，不作为 conflict；road/clearance 只与 furniture、affordance、obstacle 打架。

## 4. 兼容与迁移策略

- 保留 `Table(...)` 作为直接 cell 输入。
- 新增的 `TableTemplate` / `TableGrid` 是上层表达，不替代底层 schema。
- `TableGrid.to_matrix()` 输出的仍是当前 cell dict 或 `Table` cell-like 对象。
- `OrderAnalyzer` 不需要知道用户是手写 matrix，还是由 `TableGrid` 生成 matrix。
- `SceneModel` 继续作为内部空间分析结构，不直接暴露给普通 notebook demo。

## 5. 实施阶段

### Phase 1：轻量表达层

- 新增 `TableTemplate` 或等价模板对象。
- 新增 `TableGrid`，支持 `fill` 和 `place(row, col, **overrides)`。
- `to_matrix()` 生成每格唯一实例 id，例如 `r0_c0` 或 `t11`。
- 支持单格 override：`align="right"`、`offset`、`affordance`、`aisle`。

### Phase 2：Demo 改写

- 将 `simple_3x3_table_affordance_demo.ipynb` 改成：
  - 定义一个 `standard_table`
  - `TableGrid(3, 3, fill=standard_table)`
  - `grid.place(0, 1, align="right")`
  - `OrderAnalyzer(grid.to_matrix(), ...)`
- 输出仍包含 OCTA SVG、`order`、`scores`、`deviance_cells`、`affordance`、`aisle`。

### Phase 3：生成/修复预留

- repair/generation 不直接操作 `Table(...)` cell，而是操作 `Placement`。
- geometry/polygon 后端读取 `TableGrid.to_scene_model()` 或 `OrderAnalyzer` 内部生成后的 `SceneModel`。
- 在 polygon 前先稳定对象模型，避免几何层和表达层互相污染。

### Phase 4：路网意图表达

- 增加 `TableGrid.road(axis, between, width, min_clearance=None, offset=0, level="primary", priority=0)` 或等价 API。
- `TableGrid` 保存用户层 `Road` intent，不在用户层暴露 sampled road / clearance cells。
- analyzer/geometry bridge 将 `Road` intent 转换为 axis-aligned `RoadBand / ClearanceBand`。
- notebook 展示顺序保持为：OCTA/SVG 原生图形 -> continuous bbox/affordance/road/clearance band -> sampled occupied/affordance/road/clearance/conflict cells。

### Phase 5：RoadNetwork 轴网级表达

- 增加 `TableGrid.enable_road_network(width, min_clearance=None, enabled=True, level="primary", priority=0)`。
- 对 3x3 grid，默认生成 8 条 road intents：4 vertical + 4 horizontal。
- 增加 `TableGrid.road(axis, index, **overrides)` 作为单根 axis override；保留 `between` 参数兼容单条 Road MVP。
- `to_layout()` 输出 `roads` 时可将 RoadNetwork 展开为多条 `Road` intent。
- road-road overlap 在内部自动 union；union 后再生成 sampled road / clearance cells。
- union 区域的 `width / min_clearance / priority` 默认取 max，source road IDs 保留到 metadata。

## 6. 测试计划

- `TableTemplate` 填充 3x3 后，每个实例有唯一 id。
- 所有实例共享同一个默认 `type_id` 和 affordance profile。
- `[0][1]` override `align="right"` 不影响其他格子。
- `TableGrid.to_matrix()` 可直接传给 `OrderAnalyzer`。
- `OrderAnalyzer(...).report(features=("positions",), include_affordance=True)` 能输出位置偏差、可供性分数和通道分数。
- `TableGrid.road(axis="vertical", between=(0, 1), width=80, min_clearance=80)` 能生成稳定 `Road` intent，且不要求用户直接编辑采样网格。
- 同一 `Road` intent 在不同 `resolution` 下的 `RoadBand / ClearanceBand` 几何不变，只改变 sampled road / clearance cells 数量。
- road band 与 affordance band 重叠时，能在 report/debug map 中解释冲突来源。
- `enable_road_network()` 为 3x3 生成 8 条 road intents。
- `grid.road(axis="horizontal", index=2, enabled=False)` 禁用单根 axis 后输出减少一条。
- 两条 road 相交时 debug 中是 union/intersection，不出现 road-road violation。
- union 后 sampled road cells 数量小于或等于逐条 road cells 简单相加，避免重复计数。
- notebook 能看到完整 3x3 轴网 road network，而不是单条 road。
- 旧的 `Table(...)` 直接输入测试继续通过。

## 7. 当前决策

- 先修表达层架构，再做 geometry / polygon。
- 首批不引入复杂继承体系，保持小型 dataclass/helper 风格。
- `place()` 作为首选 API；索引赋值可后续补。
- `road()` 作为首选路网 API；`Road` 是用户语义对象，`RoadBand / ClearanceBand` 是连续几何，不是 grid cells。
- `enable_road_network()` 是下一阶段首选入口；单条 `road()` 保留作为 override 和兼容路径。
- RoadNetwork 中 road-road overlap 自动 boolean union，不作为冲突。
- 不把 `SceneModel` 暴露给普通用户 notebook。
