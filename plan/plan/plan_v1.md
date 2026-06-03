# 实施计划 v1（基于 idea260529）

## 1. 目标

以最小改动启动实现，先交付可运行的 MVP：

- 在现有 `OrderAnalyzer` 上扩展多分量评分（`base_order`、`intra`、`inter`、`rel`、`total`）。
- 保持与现有 API 兼容，历史调用不失效。
- 为后续 boundary、outlier、递归层级预留接口。

## 2. 合理性评判

### 2.1 合理

- 分层扩展方向正确：从视觉一致性扩展到关系与语义一致性。
- 评分结构可解释：分量分 + 总分有利于调试与阈值校准。
- 技术路线低风险：复用 OCTA 主干，新增关系层。

### 2.2 不合理或风险

- 权重和阈值尚未定标，可能导致不稳定。
- 抽象属性评分协议未冻结，输入易漂移。
- boundary 隐式识别误检风险较高。
- 递归层级复杂度需要后置，先做二层。

## 3. 架构（v1）

### 3.1 输入标准化层

- 统一 cell 字段：`shape`、`attr`、`orientation`、`role`、`group`。
- `role` 缺省时由 `shape` 推断（rect->table, circle->chair）。

### 3.2 计算层

- 基础分引擎：沿用 `Order.CalculatePatternDeviants`。
- 关系引擎：计算 chair-table 的距离、方位、朝向、数量、归属子分。
- 组内引擎：每组一致性（方向与角色结构）。
- 组间引擎：组间方向一致性与相位一致性。

### 3.3 聚合层

- 采用可配置权重输出 `total`。
- 缺失分量时自动重归一化，避免无效扣分。

### 3.4 输出层

- 输出统一报告结构：
  - 基本信息
  - 分量分
  - 关系子分
  - 最终总分

### 3.5 实施原则（OCTA 优先）

- 默认优先复用 OCTA 现成能力，避免重复实现。
- 只有当 OCTA 无法覆盖需求时，才在封装层新增最小自实现逻辑。
- 新增逻辑必须标注替代关系：复用了什么 OCTA 接口，补了什么缺口。
- 当前已知可优先复用的方向：pattern deviant、pattern congruency、pattern type/direction congruency。

## 4. Todo 路线图（按阶段）

### Stage 1: 关系评分 MVP

- [x] 新增关系识别与子分计算（distance, bearing, orientation, quantity, assignment）
- [x] 在 report 返回多分量结果（scores/details/weights）

### Stage 2: 组内/组间评分

- [x] 加入 intra/inter 计算与 total 聚合
- [x] 保持 calculate_order 兼容行为不变

### Stage 3: 测试与稳定

- [x] 增加典型样例测试（test/test_order_analyzer_mvp.py）
- [x] 跑通基础回归（pixi run pytest test/test_order_analyzer_mvp.py -q）
- [x] 输出布尔违背明细（deviance_by_feature / deviance_matrix / deviance_cells）
- [ ] 校准默认权重与阈值（已决定暂缓，不阻塞后续开发）

### Stage 4: 扩展预留

- [ ] 预留 boundary/outlier 接口字段
- [ ] 准备几何入口识别方案草案（v1 不实现）

## 5. 检查点

1. CP-1（接口兼容）

- 历史调用 `calculate_order(features=(...))` 返回值不变。

1. CP-2（分量可解释）

- `report()` 必须包含 `base_order`、`intra`、`inter`、`rel`、`total`。

1. CP-3（关系可读）

- 报告包含关系子分明细与对象统计。

1. CP-4（可执行）

- 至少 2 组示例输入可跑通，且分值符合直觉排序。

## 6. 执行 Todo（持续更新区）

### 6.1 已完成

- [x] 评判 idea 合理性与风险
- [x] 定义 v1 架构边界
- [x] 实现关系评分模块
- [x] 实现 intra/inter 模块
- [x] 实现 total 聚合策略
- [x] 扩展 report 输出结构
- [x] 内部函数补充中英混合注释
- [x] 新增并通过 2 个 MVP 测试用例
- [x] 新增布尔违背明细输出（维度计数与逐格 0/1）
- [x] 扩展并通过 5 个 MVP 测试用例
- [x] 冻结输入 schema（v1）并实现矩阵结构校验
- [x] 抽出网格语义层输出（role/group grid 与计数）
- [x] 扩展并通过 8 个 MVP 测试用例
- [x] 拆分 analyzer 单文件为多模块（schema / math_utils / analyzer）
- [x] 新增 Table 领域类并支持对象输入到分析器
- [x] Table 支持 shape 属性并完成对象输入重演示
- [x] 支持固定尺寸网格布局（layout_size + fit_to_layout + unit_scale）
- [x] 抽出独立 layout 模块承载布局策略

### 6.2 进行中

- [ ] 设计参数化权重方案（当前阶段先冻结为 OCTA 风格布尔违背计分）

### 6.3 待开始

- [ ] 扩展 boundary/outlier 接口字段
- [ ] 增加更多场景测试（含位置扰动与空值边界）
- [ ] 设计语义层到关系层的接口边界文档（避免后续耦合）
- [ ] 引入属性驱动可供性档案（affordance profile registry）
- [ ] 引入家具间可供区自动避让（并排/拼接）
- [x] 引入可供区与通道占比约束评分（hard + soft）
- [x] 收敛家具对象模型：区分家具类型、家具实例、网格放置
- [x] 更新 demo 表达：用一个标准桌子类型填充 3x3，再对单格实例做 override
- [x] 固定连续图形与采样评价网格的中间路线
- [x] 设计 PolygonBackend / HybridBackend 与 SpatialGridBackend 的衔接方案
- [x] 实现 SVG/OCTA 图形与采样评价网格的兼容桥接和 overlay 可视化
- [x] 引入 Road 用户语义对象，并在内部生成 RoadBand / ClearanceBand 连续几何
- [x] 引入 RoadNetwork 轴网级道路系统：每根 semantic grid line 都有 road 属性，并自动合并 road-road overlap
- [x] 引入 ContinuousConflictEvaluator，用连续几何判定 furniture / affordance / road / clearance 的核心冲突
- [x] 引入连续面积口径的 Affordance Coverage，让 coverage 评分不再依赖 sampled cell 数量

### 6.4 暂缓（不阻塞）

- [ ] 校准默认权重与阈值（延期到后续版本，当前口径保持冻结）

## 7. 风险与回退

- 若关系识别不稳定：先仅启用距离与朝向分，其他子分降权。
- 若组间相位不稳定：先返回方向一致性，暂不启用相位分。
- 若总分波动大：临时固定权重并冻结版本。

## 8. 进度更新规则（强制）

每次完成一项工作后，必须同步更新本文件：

1. 将对应 todo 从 [ ] 改为 [x]。
2. 在第 9 节新增一条工作记录（日期、改动、验证、结果）。
3. 若有新增任务，追加到 6.3 待开始，不覆盖历史记录。
4. 若计划变更，必须在记录里写明原因与影响范围。

## 9. 当前工作记录

### 2026-05-30

- 完成内容
  - 实现多分量评分与关系评分 MVP（base_order/intra/inter/rel/total）
  - 扩展 report 输出结构（scores/details/weights）
  - 补充内部函数必要注释（中英混合）
  - 新增测试文件 test/test_order_analyzer_mvp.py
- 验证
  - 运行 pixi run pytest test/test_order_analyzer_mvp.py -q
  - 结果: 2 passed
- 当前状态
  - Stage 1 完成
  - Stage 2 完成
  - Stage 3 部分完成（权重阈值校准未完成）

### 2026-05-30（决策补充）

- 决策
  - 当前实现先沿用 OCTA 思路：每个选中特征维度按元素做布尔级别违背判定，再聚合为全局分数。
  - 参数化权重与更细粒度连续评分保留到后续阶段引入，不在当前口径内混入。
- 影响范围
  - 现有 calculate_order 与 report 的基础分解释口径保持稳定。
  - 后续新增参数化逻辑必须以可配置开关方式接入，避免破坏当前默认行为。

### 2026-05-30（实施原则补充）

- 决策
  - 确认采用 OCTA 优先策略：先复用，再补缺口，不重复造轮子。
- 落地
  - 在架构章节新增“实施原则（OCTA 优先）”。
- 影响范围
  - 后续任务默认先对齐 OCTA 接口能力，再决定是否新增封装层实现。

### 2026-05-30（布尔违背明细落地）

- 完成内容
  - 在 report 中新增 deviance_by_feature、deviance_matrix、deviance_cells。
  - deviance_by_feature 使用 OCTA CalculatePatternDeviants 做维度级统计。
  - 逐格 0/1 明细仅在 OCTA 无直接接口时做最小本地实现。
  - 新增 3 个测试（shape-only、orientation-only、多维 OR 聚合）。
- 验证
  - 运行 pixi run pytest test/test_order_analyzer_mvp.py -q
  - 结果: 5 passed
- 当前状态
  - Stage 3 继续推进中（仅剩权重阈值校准）

### 2026-05-30（权重校准延期）

- 决策
  - 权重校准暂时完全跳过，不作为当前迭代阻塞项。
  - 后续可按兼容方式接入参数化权重，不改变当前默认行为。
- 影响范围
  - 当前开发主线继续推进（boundary/outlier 与测试扩展）。
  - 未来接入时必须使用可选配置开关，确保向后兼容。

### 2026-05-30（基础层收敛落地）

- 完成内容
  - 增加输入 schema 冻结与标准化（schema version v1）。
  - 增加矩阵结构校验（非空、规则矩阵、元素必须为 dict、ideal 与 actual 尺寸一致）。
  - 在 report 输出 schema 信息与 semantic 网格信息（role/group grid、counts）。
  - 增加 3 个基础测试（默认值语义、非规则矩阵报错、尺寸不一致报错）。
- 验证
  - 运行 pixi run pytest test/test_order_analyzer_mvp.py -q
  - 结果: 8 passed
- 当前状态
  - 基础层收敛完成，可继续推进关系层接口边界与后续扩展。

### 2026-05-30（模块拆分重构）

- 完成内容
  - 新增 features/schema.py：输入 schema、矩阵校验、特征映射与标准化。
  - 新增 features/math_utils.py：通用数学与矩阵工具函数。
  - 精简 features/analyzer.py：保留主流程与评分编排逻辑，移除重复工具实现。
- 验证
  - 运行 pixi run pytest test/test_order_analyzer_mvp.py -q
  - 结果: 8 passed
- 当前状态
  - 代码结构更清晰，后续继续拆分关系层与报告层成本降低。

### 2026-05-30（Table 类接入与重演示）

- 完成内容
  - 新增 features/entities.py，提供 Table 类与 to_cell 转换。
  - schema 层支持 dict 与对象输入（实现 to_cell 即可接入）。
  - 顶层导出 Table，便于后续统一输入风格。
  - 在 notebook 增加 Table 类重演示单元并成功渲染图形。
- 验证
  - 运行 pixi run pytest test/test_order_analyzer_mvp.py -q
  - 结果: 9 passed
  - notebook 输出: order=0.7778, deviants=2, deviance_cells 对齐预期
- 当前状态
  - dict 输入与对象输入并行可用，不影响既有流程。

### 2026-05-30（Table.shape 属性落地）

- 完成内容
  - Table 新增 shape 属性，并通过 to_cell 传递到分析器。
  - 新增测试：shape 变化触发 shapes 违背，但语义角色仍保持 table。
  - notebook 新增 Table.shape 对照单元并成功渲染。
- 验证
  - pytest: pixi run pytest test/test_order_analyzer_mvp.py -q
  - 结果: 10 passed
  - notebook 输出: shape order=0.75, deviants=1, role_counts={'table': 4}
- 当前状态
  - Table 已具备“形态属性化 + OCTA 一致渲染/缩放”能力。

### 2026-05-30（固定尺寸网格系统落地）

- 完成内容
  - 在 OrderAnalyzer 新增 layout_size、fit_to_layout、unit_scale 参数。
  - 支持将网格格点按固定尺寸铺满，并保持元素在格点中心。
  - 支持绝对尺寸元素与统一比例缩放共同生效。
  - notebook 新增 1350x850 固定网格演示单元。
- 验证
  - pytest: pixi run pytest test/test_order_analyzer_mvp.py -q
  - 结果: 15 passed
  - notebook 输出: layout spacing (scaled)=[42,45], layout size (scaled)=[135.0,85.0], order=1.0
- 当前状态
  - 已具备“固定画布尺寸内摆放对象”的可执行能力，兼容原有 API。

### 2026-05-30（layout 模块化重构）

- 完成内容
  - 新增 features/layout.py，集中管理尺寸解析、单元 bbox 解析、固定画布几何与中心点布局。
  - analyzer 改为调用 layout 模块，保留评分编排职责。
  - 保持现有 notebook 与测试调用方式不变。
- 验证
  - pytest: pixi run pytest test/test_order_analyzer_mvp.py -q
  - 结果: 15 passed
- 当前状态
  - 布局策略与评分逻辑已解耦，后续扩展 layout 规则不会挤占 analyzer 主流程。

## 10. v2 规划（属性驱动可供性）

### 10.1 设计目标

- 可供性从 shape 解耦，改为每件家具自带 profile（实例级可覆盖）。
- 支持家具与家具之间的可供区交互（自动避让、拼接边失活、冲突回退）。
- 在不破坏现有 order 口径前提下，引入可供性子分与可解释扣分原因。

### 10.2 大致实现阶段

1. Phase A：数据模型
- 新增 `affordance_profile` 结构（可坐边、活动深度、通道需求、并排策略、优先级）。
- 新增类型注册表（type_id -> 默认 profile），支持实例 override。

1. Phase B：几何推导
- 从 profile 生成边级可供区（edge bands）和保留区。
- 计算家具间相对关系（并排、拼接、近邻），执行自动避让重写。

1. Phase C：约束与评分
- hard 约束：通道不足、可供区被完全侵占、关键边无可达性。
- soft 约束：覆盖率不足、余量不足、冲突面积比例。
- 输出 `affordance_score` 与 `affordance_violations`（位置 + 原因 + 严重度）。

1. Phase D：兼容接入
- 默认关闭（feature flag），逐步灰度开启。
- report 增加 v2 字段，不改现有基础字段语义。

### 10.3 覆盖率问题（风险与判定口径）

- 可供区覆盖率（Affordance Coverage Ratio）
  - 定义：有效可供面积 / 需求可供面积。
  - 风险：不同桌型需求差异大，统一阈值易误伤。
  - 方案：按 type_id 分桶阈值，支持 profile 自定义阈值。

- 通道占比（Aisle Share Ratio）
  - 定义：实际预留通道宽度 / 最小需求通道宽度。
  - 风险：并排拼接时通道重复计算或双重扣分。
  - 方案：先执行拼接边失活，再计算单侧有效通道，避免重复计量。

- 交互冲突率（Interaction Conflict Ratio）
  - 定义：冲突区域面积 / 可供总面积。
  - 风险：局部小冲突被放大，影响整体分数稳定性。
  - 方案：引入局部裁剪与权重上限（cap），并提供位置级解释。

### 10.4 测试面率（覆盖面）要求

- 几何覆盖：方桌/圆桌/异形桌，含不同朝向与偏移。
- 交互覆盖：并排、拼接、错位近邻、边界贴近。
- 评分覆盖：仅 soft 违规、hard 违规、混合违规。
- 兼容覆盖：v1 关闭 flag 时结果应与当前版本一致。

### 2026-05-30（v2 计划落地）

- 完成内容
  - 增补“属性驱动可供性”v2 规划章节。
  - 明确实现阶段、覆盖率风险口径与测试覆盖面要求。
- 当前状态
  - 处于方案冻结前阶段，可进入数据结构草案与最小原型实现。

## 11. v2.1 规划（对象模型收敛：类型 vs 实例 vs 网格放置）

### 11.1 问题判断

- 当前 `Table(...)` 同时承担“家具类型”和“格子实例”两层含义。
- 在 notebook 中写 `Table("t11")...Table("t33")` 容易被理解为定义了 9 种桌子，而真实意图只是同一种桌子的 9 个实例。
- 这与 OCTA 原生“定义一个元素样式，然后在网格中重复”的心智模型不一致。

### 11.2 目标

- 一个标准桌子类型可以填充 3x3 网格。
- 单个格子只覆盖实例参数，例如 `align="right"`、`offset`、局部 affordance override。
- `OrderAnalyzer` 仍接收 matrix，不破坏当前 `Table(...)` 直接作为 cell 输入的兼容方式。

### 11.3 三层模型草案

- `FurnitureType / TableTemplate`
  - 定义形状、尺寸、`type_id`、默认 `affordance/aisle profile`。
- `FurnitureInstance / Placement`
  - 定义实例 `id`、`row/col`、`align`、`offset`、局部 override。
- `FurnitureGrid / TableGrid`
  - 批量放置一个模板，并生成 `OrderAnalyzer` 可读的 cell matrix。

### 11.4 实施顺序

1. 先实现轻量表达层，不碰 polygon / exact geometry。
2. 更新最简 3x3 demo：定义一个标准桌子类型，填充网格，再修改 `[0][1]` 实例为 `align="right"`。
3. 在类型-实例模型稳定后，再让 geometry/polygon 后端读取实例化后的 `SceneModel`。

### 2026-06-01（对象模型收敛计划补充）

- 完成内容
  - 记录“家具类型 vs 家具实例 vs 网格放置”的架构问题。
  - 明确当前 `Table(...)` 兼容保留，新 API 作为更干净的上层表达接入。
  - 新增详细计划文档：`plan/plan/plan_v2_object_instance_model.md`。
- 影响范围
  - 当前 affordance/aisle 实现不推翻。
  - 后续优先修表达层，再推进 geometry / polygon。

## 12. v2.2 规划（连续图形 + 采样评价网格）

### 12.1 核心原则

- OCTA/SVG 图形本体是连续几何对象，不是评价网格中的格子块。
- `SpatialGridBackend` 是采样解释、debug heatmap 与 reachability 近似工具；road-affordance / road-furniture 等核心几何冲突不应最终由 resolution 决定。
- 图形无需与采样格对齐；它可以偏移、跨格，后续也可以旋转或表达为 polygon。
- 改变 `resolution` 只改变采样精度，不改变家具图形本体定义。

### 12.2 当前路线判断

- 当前实现已经在走“连续图形 + sampled evaluation”的中间路线。
- `Table(size=...)` 和 OCTA 渲染负责连续视觉形态。
- `SceneModel/Rect` 负责连续空间表达。
- `SpatialGridBackend` 把连续空间采样成解释网格，用于 notebook 可视化、debug map 与 BFS reachability；连续冲突应先由几何对象判定，再 rasterize 成 sampled cells 做解释。

### 12.3 后续升级方向

- 当前连续几何已经包含 furniture footprint polygon、AffordanceBand polygon、RoadBand Rect 与 ClearanceBand Rect。
- `ContinuousConflictEvaluator` 将成为下一阶段核心：先用连续几何判定冲突，再把冲突来源 rasterize 到采样网格做 notebook/debug 解释。
- `PolygonBackend / HybridBackend` 后续用于提升圆桌、异形桌、复杂边界和更精细 road geometry 的表达精度。
- polygon / continuous backend 不推翻采样网格，而是把采样网格收敛为解释层和 reachability 近似层。

### 2026-06-01（连续几何与采样评价路线补充）

- 完成内容
  - 记录“图形是连续几何，网格是采样评价工具”的架构原则。
  - 明确当前不是“家具=格子块”，而是通过采样网格评价连续图形。
  - 新增详细计划文档：`plan/plan/plan_v2_geometry_sampling_bridge.md`。
- 影响范围
  - 当前 `SpatialGridBackend` 继续作为 MVP 评价后端保留。
  - 后续 polygon / hybrid backend 作为精度增强接入，不否定当前路线。

### 2026-06-01（v2.1 表达层与 notebook 依赖收尾）

- 完成内容
  - 新增 `TableTemplate / TableGrid` 轻量表达层，用一个桌子类型生成多个网格实例。
  - 更新 `test/simple_3x3_table_affordance_demo.ipynb`：定义一个标准桌子类型，填充 3x3，再对 `[0][1]` 实例执行 `align="right"` override。
  - 补齐 notebook 正式执行依赖：`nbformat` 与 `nbclient`。
  - 将 v2.1 对象模型、demo 表达、连续图形采样路线、Polygon/Hybrid 衔接方案对应 TODO 标记为完成。
- 验证
  - 运行 `pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q`
  - 运行 `pixi run python -c "...使用 nbformat/nbclient 顺序执行 simple_3x3_table_affordance_demo.ipynb..."`
- 当前状态
  - `Table(...)` 直接输入继续兼容。
  - demo 已转向 “template -> grid -> instance override -> render/report/grid visualization” 的用户心智模型。
  - 下一步建议先推进 SVG/OCTA 连续图形与采样评价网格兼容桥接，再做评分解释增强。

### 2026-06-01（SVG/OCTA 与采样评价网格桥接可视化）

- 完成内容
  - 新增 `features/affordance/visualization.py`，将 `SceneModel` bbox、semantic grid、sampled occupied / affordance / conflict / reachable 图层画在同一 SVG 坐标系。
  - 更新 `test/simple_3x3_table_affordance_demo.ipynb`，新增 geometry bridge overlay 与 resolution comparison 两个 SVG 输出。
  - 保留 OCTA `_stim.Show()` 原生 SVG，用 notebook 同时展示“连续图形”和“采样评价网格”。
- 验证
  - 运行 `pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q`
  - 运行 `pixi run python -c "...使用 nbformat/nbclient 顺序执行 simple_3x3_table_affordance_demo.ipynb..."`
- 当前状态
  - demo 已能直接看到 OCTA/SVG 图形、SceneModel bbox 与 sampled grid 的映射关系。
  - 后续可在此基础上做评分解释增强或 polygon/hybrid backend 精度升级。

### 2026-06-01（Aisle reserved corridor 与可供区冲突 MVP）

- 完成内容
  - `SpatialGridBackend` 新增 aisle corridor 与 aisle/affordance conflict owner tags。
  - `AisleEvaluator` 从单纯 BFS reachability 扩展为 reserved corridor 评价，`AisleProfile.min_width` 开始参与评分。
  - `aisle` 报告新增 per-object corridor 统计、`debug.aisle`、`debug.aisle_conflict`、`aisle_blocked` 与 `affordance_aisle_conflict`。
  - notebook 新增 aisle corridor / conflict 可视化输出，并打印 `aisle.objects["t12"]` 与 debug cell 计数。
- 验证
  - 运行 `pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q`
  - 运行 `pixi run python -c "...使用 nbformat/nbclient 顺序执行 simple_3x3_table_affordance_demo.ipynb..."`
- 当前状态
  - 通道已经从“可达性”升级为“可达性 + 保留区 + 与可供区冲突”的 MVP。
  - 后续可继续推进通道路径 corridor、通道骨架或 polygon corridor。

### 2026-06-01（v2.3 Road / Clearance / Circulation 语义收敛）

- 完成内容
  - 明确 `AisleProfile.min_width` 表达最小通行净空要求，不是道路实体宽度。
  - 明确 `Road` 是用户层通行空间/道路语义对象，负责承载 axis、between、width、offset、level、priority 等意图。
  - 明确 `RoadBand / ClearanceBand` 是内部连续几何：前者表达通行空间，后者表达净空检查区域。
  - 明确 sampled grid cells 只是 `SpatialGridBackend` 的评价与解释结果，不是道路或净空本体。
  - 将当前 object-centered bbox halo corridor 标记为 `ClearanceBand` temporary MVP，不作为长期道路模型。
- 影响范围
  - 当前 aisle halo 逻辑暂不删除，可作为 fallback 或 legacy MVP 保留。
  - 后续 notebook 应先展示连续 `RoadBand / ClearanceBand`，再展示 sampled road / clearance / conflict cells。
  - `Road` 和 `TableGrid.road(...)` 将作为用户层路网意图入口；`RoadAxis` 只作为内部字段或 helper，不要求用户实例化。

### 2026-06-01（RoadNetwork 轴网级道路系统补充）

- 当前状态
  - 单条 `Road` MVP 已能表达用户层 road intent，并生成连续 `RoadBand / ClearanceBand` 与 sampled debug layers。
  - 但真实目标不是单条 road demo，而是整个 semantic grid 的轴网道路系统。
- 下一步目标
  - 对 3x3 semantic grid 自动生成 4 条 vertical axes + 4 条 horizontal axes，共 8 条可配置 road axes。
  - 每根 semantic grid line 都应拥有 road 属性：`enabled / width / min_clearance / offset / level / priority`。
  - road-road overlap 不作为冲突；默认执行 boolean union，并保留 source IDs 作为 metadata。
  - road/clearance 只与 furniture、affordance、obstacle 等异类空间进入 conflict / bottleneck。
- 合并策略
  - union 区域的 `width` 取 max。
  - union 区域的 `min_clearance` 取 max。
  - union 区域的 `priority` 取 max。
  - `level` 与 source road IDs 保留到 debug metadata，方便 notebook 解释。

### 2026-06-03（RoadNetwork MVP 完成与 continuous conflict 转向）

- 完成内容
  - `TableGrid.enable_road_network(...)` 已作为 RoadNetwork MVP 落地，可为 3x3 semantic grid 展开 4 条 vertical axes + 4 条 horizontal axes。
  - 已支持单根 axis override，例如调整 width / min_clearance / priority，或禁用某根 horizontal / vertical axis。
  - `OrderAnalyzer` 可读取 `TableGrid.to_layout()` 输出的 road intents，并生成连续 `RoadBand / ClearanceBand` 与 sampled road / clearance debug layers。
  - notebook 已能看到完整 3x3 轴网 road network，而不是单条 road demo。
- 当前发现
  - sampled grid 已触及评分边界：窄 road、AffordanceBand polygon、旋转家具 footprint polygon 与粗 `resolution` 组合时，会出现过度解释或漏解释。
  - 即使 area-intersection sampling 比 center-point sampling 更合理，它仍然只是 sampled explanation，不应决定连续几何冲突是否存在。
  - 同一连续 overlap 在 `resolution=20` 与 `resolution=10` 下，是否存在冲突不应改变；变化的只能是 debug cells 数量和显示精细度。
- 下一步
  - 新增 `plan/plan/plan_v2_continuous_conflict_evaluator.md`。
  - 引入 `ContinuousConflictEvaluator`：用连续几何先判定 `Furniture footprint Polygon`、`AffordanceBand Polygon`、`RoadBand / ClearanceBand` 之间的核心冲突。
  - `SpatialGridBackend` 保留为 notebook overlay、debug heatmap、BFS reachability 与 sampled explanation 工具。

### 2026-06-03（ContinuousConflictEvaluator MVP 完成）

- 完成内容
  - 新增 `features/affordance/continuous_conflict.py`，用连续几何判断 `Furniture footprint Polygon`、`AffordanceBand Polygon`、`RoadBand / ClearanceBand` 的核心 overlap。
  - `evaluate_spatial_access()` 先运行 continuous conflict，再把结果合并回既有 `affordance.violations`、`aisle.bottlenecks` 与 debug 结构。
  - overlay 中玫瑰红冲突图形来自 continuous overlap polygon；sampled conflict cells 只作为 notebook/debug 解释。
  - 增加入口标记：当前 reachability 入口仍是左边界 MVP，不是 RoadNetwork 本体。
  - sampled occupied 阻挡改为 50% 面积覆盖阈值，避免旋转家具擦边时把整格错误阻断。
  - 补充关键注释，明确 continuous conflict、sampled debug layers、entry/reachability 与 occupancy threshold 的边界。
- 验证
  - 运行 `pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q`
  - 结果：63 passed
- 当前状态
  - road-affordance / clearance-furniture / affordance-furniture 的“是否冲突”已不再由 sampled grid 决定。
  - `SpatialGridBackend` 继续服务 notebook overlay、BFS reachability、debug heatmap 与 sampled explanation。
  - 仍待收敛：`affordance.coverage` 目前还有 sampled-cell 口径，应在下一步转向 continuous area coverage。
- 下一步
  - 引入连续面积口径的 Affordance Coverage：用连续可供区域面积、连续 blocker / conflict 面积计算 coverage 与扣分。
  - sampled affordance cells 保留为浅黄色解释图层，但不再作为 coverage 评分本体。

### 2026-06-03（Continuous Affordance Coverage 完成）

- 完成内容
  - `Polygon` 新增连续面积计算，旋转家具与旋转 affordance band 的面积不再依赖采样格。
  - `AffordanceEvaluator` 将 `coverage`、`required_area`、`blocked_area`、`effective_area` 切换为 continuous-area 口径。
  - `affordance.backend` 更新为 `continuous`，并在对象结果中输出 `coverage_backend="continuous"`。
  - sampled affordance cells 继续作为 notebook/debug explanation；`resolution` 只影响显示颗粒度，不再决定 coverage score。
  - notebook 新增 `affordance.objects.t12/t33` 面积字段与 r=20/r=10 coverage 稳定性输出。
- 验证
  - 运行 `pixi run pytest test/test_order_analyzer_mvp.py test/test_affordance_aisle.py -q`
  - 结果：66 passed
  - 使用 `nbformat/nbclient` 顺序执行并保存 `test/simple_3x3_table_affordance_demo.ipynb`
- 当前状态
  - road/clearance/furniture/affordance 的冲突存在性与 affordance coverage 评分都已回到连续几何本体。
  - `SpatialGridBackend` 继续负责 sampled explanation、debug heatmap 与 BFS reachability。
- 下一步
  - 评估是否引入显式 `Entry / AccessPoint`，替代当前左边界默认入口 MVP。
  - 或继续推进连续 geometry backend 的面积 union / blocker 去重，避免多个 blocker overlap 同一区域时只靠 cap 处理。
