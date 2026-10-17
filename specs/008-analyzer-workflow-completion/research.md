# Phase 0 Research — Analyzer workflow completion

日期：2026-10-19。结论来自当前仓库、交付 jj workspace 及指定 portable 内已安装 Bonsai/IfcOpenShell 源码的只读审计；研究代理分别核查基线/参与策略、camera、B4/Space。没有启动 native authoring 或复跑功能测试。

本文件区分“已选择技术路径”和“仍需运行时证明”。D1–D4 沿用 [spec](spec.md)，不存在待补充的产品选择；native 事务/几何正确性是实施验收门槛。

## 1. 实施基线与最小依赖闭包

**Decision**：以 sibling `order_analyzer_spec004_delivery` 为审计和有界恢复来源；先在 task-owned jj workspace 准备 imports、配置、测试、fixture 和 export 闭包，再实现 008。记录 revision 和实际字节，避免以历史 revision 代替 dirty 文件状态。

**Rationale**：当前 `default@ead59e14` 缺 addon、camera/session/live/request 等接口；delivery `spec004-delivery@4b332704` 已有 Spec003–007 的部分工作流。`workflow007@1a271593` 的 `features/analysis_requests.py` 有冲突，且其实际 addon/session/request 字节不同，不能作为可直接集成的干净基线。只读版本检查使用 `jj --ignore-working-copy`；不把其他工作区 dirty 改动一并 checkpoint。

审计识别样本如下，实施时须重算完整 SHA256，而不是只比较这些短前缀：

| delivery 文件 | 字节数 | 已观察 SHA256 前缀 |
| --- | ---: | --- |
| `blender_addon/order_analyzer_ui/__init__.py` | 99058 | `06EDC343767E` |
| `adapters/bonsai_analysis_plane.py` | 9842 | `4CB606DC1E1C` |
| `adapters/blender_analysis_session.py` | 49523 | `A4025B3B1135` |
| `features/analysis_requests.py` | 38373 | `B1DDBB5B4D8A` |

**Alternatives considered**：整树复制会覆盖无关 dirty work；只拷 addon 会缺 imports/fixtures；只按 revision 选取会遗漏交付副本实际未记录字节；直接使用 workflow007 会传播冲突。均不采用。

## 2. Camera 的原生创建与采用

**Decision**：new drawing 走本机链路 `bim.add_drawing → bonsai.core.drawing.add_drawing → Drawing.create_camera`；existing drawing 复用 `read_camera_binding`、`plane_from_camera`、`refresh_camera_plane`。在原 native 动作完成处取得准确 entity/object refs，再绑定 OA plane。

**Rationale**：已审计的 `adapters/bonsai_analysis_plane.py` 已实现 CameraBinding/native GUID/SI pose，但 addon 的 SetupPlane 只生成 OA UUID/revision，实际 `_analysis_plane` 仍依赖手动 world XY/Z，尚不满足交互要求。native Add Drawing 同时创建 camera、IfcAnnotation/DRAWING、DRAWING group、property/document 关系，属于显式 IFC authoring；采用与读取已有 camera 不写 IFC。

**Alternatives considered**：手动 Z、当前 viewport、激活旧 camera 都不等于创建/转换；通过“对象名称差集”猜返回结果会误认并发或临时对象，不采用。取消/失败恢复必须覆盖该 native 动作实际创建的关联实体，而不仅是 Blender camera。

本机依据：portable `bonsai/bim/module/drawing/operator.py:AddDrawing`、`bonsai/core/drawing.py:add_drawing`、`bonsai/tool/drawing.py:create_camera`。

## 3. Plane 身份、姿态和查询能力

**Decision**：plane composition 只组合既有 CameraBinding 和 AnalysisPlane；native pose 为事实，显式 refresh 产生可追溯修订并使依赖结果失效。水平面按受支持 query 使用；倾斜不静默投平。exact world-XY section 保留 canonical WORLD_XY_BASIS 限制。

**Rationale**：camera binding 能表达的正交右手姿态范围，比 `features/analysis_requests.py:_unsupported_reason` 当前允许的 query 范围更大。读取成功不代表可以执行所有 section/band。保存的 GUID/pose/revision 用于复核，不能在重开时自动视为 live 已确认。

**Alternatives considered**：建立第三种通用 plane 对象、自动把旋转/倾斜变成 WORLD_XY、camera 移动后继续使用旧确认，都违背身份与能力契约。

## 4. 底面、B4 剖切与高度

**Decision**：保留 `adapters/bonsai_live.py:StructuralContext` 的 `datum_z_m`、`cut_z_m`、storey_ref 和 selected_wall_refs；camera plane Z、Space datum、B4 cut offset/absolute Z、extrusion height 分别表达。storey 与 slab 是底面二选一。slab-only 输入通过唯一 native storey 关系取得楼层，无须重复选择同一 storey。

authored height 采用最小明确映射：唯一有效的 `Qto_BuildingStoreyBaseQuantities.GrossHeight` / `IfcQuantityLength`。quantity 自带 Unit 优先，否则用项目长度单位；记录 entity/path/原值/unit/SI/provenance。缺失、歧义或无效则提示并允许 manual height；manual 为有限且严格大于零的长度。此自动映射不扩展到名称模糊匹配的自定义属性。

**Rationale**：native `ifcopenshell/util/schema/ifc4_properties.json` 区分 GrossHeight 与 NetHeight 的含义；明确量比相邻楼层 Elevation 差可追溯。D1 不允许 elevation 推断，也不允许默认 3m/RL3 或以零标高作为层高。D2 要求 slab 的真实变换后水平上表面：共面的三角片可以合成一个面，倾斜、多级、多个顶高程或楼层关系冲突明确拒绝。不能以 bbox/maxZ 判断。

**Alternatives considered**：强制 storey+slab 双填、自动 Elevation 相减、NetHeight 偷换 GrossHeight、取 slab 顶点最大 Z，均拒绝。未来其他高度字段必须另行明确映射，不在 008 增加配置框架。

## 5. 精确 B4 sketch 到 native profile/extrusion

**Decision**：复用 B4 既有 GeoJSON Polygon；冻结 shell、全部 holes、frame、datum、height、source/candidate identity 与 tolerances，再交一个窄的 `adapters/bonsai_space_authoring.py`。使用 native `ShapeBuilder.polyline(..., closed=True)`、`profile(outer_curve, inner_curves=...)`、`extrude(profile, magnitude)` 和 native representation assignment/switch、class/collector/storey placement。

**Rationale**：当前 `_create_space_from_bonsai_seed` 只改 cursor XY 后调用 `bim.generate_space`，会重新依赖可见对象围合；`_handoff_new_space_to_edit` 又按名称猜新对象。两者都未传完整 sketch。更低一级的 `Spatial.set_space_representation_from_polygon` 也不能直接复用：其 `get_2d_vertices_from_polygon` 只读取 exterior，孔洞会丢失。native ShapeBuilder 的 inner_curves 则可生成 `IfcArbitraryProfileDefWithVoids`。

转换路径明确为 structural-local → world SI → product-local → IFC 长度单位，单位换算只做一次。候选必须为一个有效 Polygon，保留凹角和洞；意外 MultiPolygon、无效/相交/越界/接触内环拒绝，不用 buffer(0)、凸包或删除小片段来掩盖问题。成功前比较 native 回读几何的 ring topology、边界、净面积、底/顶高程和体积；bbox 或一个内部 seed 不足以通过。

**Alternatives considered**：`bim.generate_space`、exterior-only helper、自研第二套围合、mesh-only Space、按名称发现返回对象，均不采用。创建成功后 canonical recapture，并经既有 `authored_space_domain` 与“采用已有 Space”同一路径进入分析。

## 6. Native 事务恢复

**Decision**：在任何 native 写入前预检并记录操作前边界、native transaction key/history、IFC/Blender links、当前临时 UI 状态和本操作拥有的对象资源；拒绝在另一个无关 native transaction 正在进行时开始。失败只恢复本操作范围，区分尚开放与已 finalize 的事务，再恢复对象/mesh/camera/collection、链接与临时状态。camera 新建与 Space authoring 都适用。

**Rationale**：已审计 `IfcStore.execute_ifc_operator` 在异常时执行 `end_top_level_operator` 后 re-raise，不能推论“抛异常即已回滚”。`file.discard_transaction` 只能撤销开放事务；`IfcStore.undo()` 不提供边界时会遍历历史。必须使用经过 fixture 证明的精确本操作边界，禁止无界 undo、只删 mesh、替换整个 active IFC 或以 CANCELLED 当恢复证明。

**Alternatives considered**：自动依赖 wrapper rollback、失败时继续发布半成品、删除按名字找到的对象、撤销无关历史，均不采用。恢复实现若失败，必须明确报错并要求复核、阻止后续成功发布/自动保存；该错误报告不能算作 R09 已通过。

**实施证明门槛**：profile/entity/representation assignment/switch/round-trip 等阶段故障注入；验证 IFC entities/relationships、Blender datablocks/links、undo/redo 边界均恢复，重试只生成一份有效结果，既有用户操作不受损。该项目前是待证明的 native 集成风险，不是已完成验证。

## 7. 家具分析资格与物理占用

**Decision**：使用 `features/neutral_scene_views.py:furniture_analysis_participation` 的 shared included/excluded/unknown 规则，在 direct group、trend、affordance、target 消费前一致执行 veto。unset 沿用既有语义，不自行改成 excluded。原始 authored group/member refs 与 physical_occupancy inventory 保留。

**Rationale**：`group_self_description.py:_neutral_inputs/_group_geometry/_trend_geometry` 可绕过 analysis view。已记录回归 `test_furniture_exclusion_vetoes_direct_group_and_affordance_contribution`：view 排除和 physical inventory 保留均通过，但 support_area 实为 4.0、应为 None。无 eligible members 时 support_area=None、member_geometry=[]、trend unavailable；不以零或 fabricated target 替代。

**Alternatives considered**：删除 excluded 物理实体、由名称/图层/邻近创造 furniture_group、只在 UI 过滤、通过改断言接受已知失败，都不采用。

## 8. B4、query、持久化和验证

**Decision**：保留 B4 normal/selected-wall 双入口和现有 service/reducer；normal 清理旧 selected_wall scope，selected-wall 只限制候选范围，相关未选内部墙仍参与。保留 timer/cancel/cache/eye/area/tolerance/closed aperture/current-attempt-refusal-stale/residual diagnostics。free-space 沿用 request/field/resolver 的身份与 unknown 语义；whole-height 不因 camera Z 变化暗改范围，section/band 必须显式选择。

**Rationale**：局部墙范围可减少局部结构计算，但不表示全场 source capture 成本消失。slab datum 是基准，不是自动免除所有 slab occupancy 的支持关系；SupportBinding 继续按具体 source 使用。持久化沿用现有 session/Region/result 文档，重开保留身份与历史但 requires_recheck。

**Alternatives considered**：第二套 B4、通用 result registry、从 display mesh 重建权威结果、沿用旧阶段 PASS 作为 008 闭环证据，都不采用。验证入口见 [quickstart](quickstart.md)，接口与验收映射见 [contracts/workflow.md](contracts/workflow.md)。
