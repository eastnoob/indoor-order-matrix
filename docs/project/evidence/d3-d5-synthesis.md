# D3–D5 综合报告与 D8–D10 切片建议

## 结论摘要

本轮形成 32 条证据记录：20 条官方文档核验、7 条全文来源（5 条外部感知/空间统计论文和 2 条动作空间 BIM 原文）、4 条摘要级来源、1 条不可访问记录。负责人提供的 Protonotarios 2014 与 Wagemans 2012 PDF 已逐节核验；证据仍不能支撑“家具布局指标具有心理感知效度”。

建议一个窄的 D8–D10 纵向切片：

> **IFC4 → NeutralScene → SVG oracle：相对顺序 + 作者化 IfcGroup 局部趋势。**

切片只消费：IfcFurniture/可识别家具产品、IfcObjectPlacement 链、选定 Body/Plan 几何、IfcRelAssignsToGroup、统一单位和显式分析平面。输出 `relative_order`、`authored_group_local_trend` 及其 provenance/geometry_status。它是工程可重复性试验，不是感知实验，也不包含 inferred group、affordance 生成、通道/路径、视觉复杂度或 Bonsai UI 验收。

## 证据到决策矩阵

| 候选输入/输出 | 事实来源 | 本项目计算 | 结论 | 切片 |
|---|---|---|---|---|
| 产品 GlobalId、IfcFurniture/type | E-IFC-007 | 读取实体与标签 | IFC 事实；缺失保留 unknown | 是 |
| 世界坐标 | E-IFC-001/002 | 展开 placement chain | IFC 事实 + 坐标变换 | 是 |
| Body/Plan 几何 | E-IFC-002、E-SW-001 | 选上下文、记录 settings | 软件行为；不是语义区 | 是 |
| authored group | E-IFC-004 | 按显式成员计算局部趋势 | IFC 关系事实；不等于相邻/可用 | 是 |
| relative-order | E-IFC-001、E-GEO-003、E-INF-001 | 世界空间投影、序列偏差/容差 | 工程描述子，轴/阈值待确认 | 是 |
| local trend/orientation | E-GEO-002、E-INF-001 | MassPatch 中心与 PCA 候选轴 | 工程描述子；退化时 undefined | 是 |
| bbox/convex hull | E-GEO-001 | 几何摘要/边界候选 | 几何事实，不是 affordance | 可作为中间量 |
| distance/overlap/clearance | E-GEO-003、E-IFC-008 | 几何谓词 + 项目阈值 | 约束结果，不是人的可用区 | 否 |
| graph/path | E-GEO-004 | 需先定义 graph domain | 无域不计算 | 否 |
| IfcSpatialZone/IfcZone | E-IFC-005 | 只保留明确来源的区域 | Zone 不产生自有几何；不生成 affordance | 否 |

| Pset_SpaceOccupancyRequirements | E-BIM-001/002 | IFC 空间活动/占用事实 | 可记录活动人数/面积/净空；不是家具 affordance | 后续 |
| derived action-space collider | E-BIM-004/005 | 从动作测量或角色 profile 生成派生体 | 可作为 authored/derived geometry；不是 IFC 原生 furniture schema | 否（后续） |
| IfcSpace extension proposal | E-BIM-003 | 研究型扩展线索 | 摘要级，不能进入 IFC4 事实合同 | 否 |
| IfcCovering/SurfaceFeature | E-IFC-006 | 可作表面/边界候选 | 不等于视觉/行为边界 | 否 |
| visual complexity/symmetry perception | E-PER-001/002 | 不纳入工程分数 | 外部背景，不能迁移效度 | 否 |
| point-pattern order/J-function | E-PER-003/004 | 不直接采用 | 点模式心理量表和 J-function 只在其刺激/点过程范围内成立，非家具验证 | 否 |
| Gestalt grouping/continuity | E-PER-005 | 仅保留术语和外部背景 | 全文综述明确存在任务/刺激依赖；不证明家具边界或连续性算法 | 否 |
| Bonsai live import | E-SW-003/004 | 暂不执行 | 文档行为已知，现场行为未验证 | 否 |

## D3 术语裁决

- `order`、`regularity`、`symmetry`、`repetition`、`clustering`、`continuity` 保留为候选词；在没有家具实验和项目阈值前，不把它们写成心理量表。
- 首片使用 `relative-order` 这个工程字段名，避免暗示“人类感知秩序”。它必须带 `analysis_axis`、`tolerance`、`coordinate_frame`、`unit` 和 `geometry_status`。
- `authored_group_local_trend` 只说明显式 IfcGroup 内几何的局部趋势；不得命名为“整体感”“视觉连续性”或“行为可用性”。

## D4 几何与 IFC 合同影响

1. 先解析单位与完整 placement chain，再把几何投影到统一世界坐标的分析平面。
2. 每个几何结果保留 `source_representation`、`representation_context`、`source_global_ids`、`algorithm`、`tolerance` 和状态。
3. 空点集、点数不足、共线、各向同性、无效多边形、不连通图分别输出 undefined/invalid/no_path；不可静默转成 0。
4. Convex hull 仅是包络候选；PCA 仅是方差方向候选；Shapely 谓词仅是平面几何关系；NetworkX 只在显式图域中求路径。
5. IFC Clearance、IfcSpatialZone、IfcCovering、IfcSurfaceFeature 和 Pset_SpaceOccupancyRequirements 都要保留原实体身份；不能把它们自动改写成家具 affordance 或心理边界。
6. 目前最接近项目需求的外部先例是 Selin & Rossi 的动作空间 IFC/3D collider 方法；它支持派生几何 provenance，不是 IFC 原生家具语义。

## D5 软件边界

- IfcOpenShell 0.8.5 的 representation/context、单位、开口扣除和网格容差必须进入 provenance；粗略 bbox 与精确几何要分开标记。
- Bonsai 文档确认 IFC 是项目源、blend 是配套文件；本轮没有执行 UI 导入，因此不宣称 live compatibility。
- 本机只观察指定便携 Blender 5.2.0 LTS 和 Pixi 锁定版本；官方 Blender 发布页 402，不作为发布页原文证据。

## 未决问题与负责人材料请求

1. 请提供 BIM 家具 affordance/clearance 直接原文（DOI、作者稿或企业 schema）；目前仍只有检索失败记录。
2. 是否允许 IFC4 通用 Clearance 作为家具约束输入？若不允许，确认 `OM_` authored affordance schema。
3. 首片字段是否采用 `relative-order` 命名？确认分析轴、容差、单位和 tie/重复处理。
4. 确认 MassPatch 来源（实体几何或已生成 neutral geometry）、PCA 退化阈值、无效几何策略。
5. 确认作者化 IfcGroup 的多组成员是否重复计数，是否保留组层级路径。
6. 确认真实 acceptance IFC 是否先独立修复；研究期间不修复 IFC。
7. 确认 Bonsai live import 是后续 gate 还是不在首片范围。
8. 若后续需要心理研究，负责人需指定家具/建筑刺激、观察者任务和外部实验，不得从本账本推导效度。
9. Chaabane 2023 的 IfcSpace 扩展研究全文仍需取得；它是最直接的活动/拓扑要求先例。

## 完成检查（执行记录）

- [x] 已阅读 AGENTS.md、Phase 0 决策、架构记忆、intake 和两份原始需求。
- [x] D3–D5 每条记录包含 source、version/year、locator、access_status、supports、does_not_support、limitations/follow_up。
- [x] 检索词、数据库/入口、成功与失败结果已写入 [search log](./d3-d5-search-log.md)。
- [x] IFC/BIM、几何算法、软件行为、心理实验和工程推断已分栏。
- [x] 未把摘要、搜索片段、README 或记忆作为原文证据。
- [x] 不可访问原文和负责人材料请求已列出。
- [x] 负责人提供的 Protonotarios 2014 与 Wagemans 2012 原文已核验并写入账本；未把其外部感知结果扩展为家具心理效度。
- [x] 未修改生产代码、未安装依赖、未修复 IFC、未执行 Bonsai 导入、未进入 D6。
- [ ] 负责人确认首片字段、容差和输入材料后，才允许进入 D6。

提交范围：仅本目录下的 `d3-d5-evidence-ledger.md`、`d3-d5-search-log.md`、`d3-d5-synthesis.md`。
