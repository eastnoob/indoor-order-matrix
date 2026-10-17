# Analyzer 完整工作流补齐 — 需求基线

日期：2026-10-19。来源：用户本线程重贴的原始工作流，以及后续“B4 自己构造 sketch、交给 Bonsai 拉伸”的明确纠正。
状态：D1–D4 已按用户原会话答复冻结；Phase 0/1 设计和 speckit-tasks 任务拆分已完成，实现与验收待执行。本状态不表示用户已审阅新生成的全部设计或功能已完成。

## 范围与现状

文档权威位置在主仓库。本轮实现审计基线是 sibling `order_analyzer_spec004_delivery`，不是当前主仓库代码；主仓库尚缺该交付副本的一些接口。实施前必须先恢复其明确的依赖闭包到可追溯的 jj 工作副本，不得整树覆盖历史 dirty work。
已有：B4 整层/选墙双入口、候选缓存/面积/eye/进度、原生 IfcSpace 列表采用、Region 保存/复核、FreeSpaceField、CameraBinding 底层读取、有限高度带查询。
缺口：相机 UI 接线、楼板独立基准、空间高度二选一、B4 完整轮廓交 Bonsai authoring、家具参与策略一致性、真实闭环验收。

## 用户意图与验收要求

| ID | 要求 | 验收条件 |
| --- | --- | --- |
| R01 | 设置分析平面复用 Bonsai drawing camera 的实际创建交互 | 新建采用 native Add Drawing 链路；用户能建立有身份/姿态的分析平面；取消不留下半成品 |
| R02 | 选择已有 Bonsai camera 转换为平面 | 选择相机后一键使用；复用 read_camera_binding/plane_from_camera；保存和显式刷新后身份/修订可追溯 |
| R03 | 已有 IfcSpace 直接采用 | 从视口选择或源列表选择并点击使用；错误类型/缺几何/错层明确拒绝；不要求先运行 B4 |
| R04 | B4 基准是 storey 或选定 slab | 两条可选基准路径，缺失另一项不形成无意义双重前置；slab 的楼层关系仍需明确验证 |
| R05 | 空间高度来自楼层高度或用户输入 | OR 关系；长度单位正确；高度有限且 >0；楼层标高、B4 剖切高度、空间拉伸高度分别表达 |
| R06 | 普通模式用相关层墙；选墙模式仅推断选墙包围的区域 | 复用现有 B4，两模式都可用；内部未选隔墙继续有效；开放边界拒绝；记录实际节约与未节约的成本 |
| R07 | 保留 B4 现有 UI | 进度条、候选容器、面积、单选、eye、容差、闭门窗规则、current/attempt/stale/残差诊断都保留 |
| R08 | B4 轮廓成为我们自己的 sketch，再用 Bonsai native representation/extrude 创建 Space | 外轮廓、holes、选定底面和高度传入 authoring；不能只传 seed 后重新围合；生成几何验证与输入轮廓一致 |
| R09 | 原生 Space 只在显式确认后创建 | Analyze/preview/eye/选择不写 IFC；失败原子回滚；成功返回准确 IfcSpace 身份并可接入分析 |
| R10 | 家具组分析目标与物理占用分离 | 复用明确 furniture_group 声明与参与策略；排除家具分析不删除占用；不得由名称/图层/邻近创造组 |
| R11 | 在目标空间与分析平面上运行自由空间 | 使用现有 request/field/resolver；组目标信息可追溯，其他物理实体继续占用；unknown 不冒充 free；抬平面不偷偷改 whole-height 范围 |
| R12 | 三阶段形成可用闭环 | 平面→采用或推断空间→自由空间；保存/重开保留身份并要求复核，不自动恢复旧确认；完整新建与已有 Space 各通过一次 |

## 用户故事与实施分组

以下五组按既有 R01–R12 划分实施和独立验证边界，均为 P1 必需范围；顺序表达依赖与增量交付，不新增产品优先级差异。完整完成仍需五组全部验收。

| 故事 | 优先级 | 用户目标 / 要求 | 独立验收 |
| --- | --- | --- | --- |
| US1 | P1 | 新建或采用原生 drawing camera，得到可刷新、可追溯的分析平面；R01/R02 | 在 disposable drawing 场景验证 new/adopt/refresh、姿态拒绝和失败恢复，无须运行 B4 或创建 Space |
| US2 | P1 | 从视口或源列表直接采用已有 IfcSpace；R03 | 用 fixture plane 和已有 Space 验证两入口及资格拒绝，不要求 B4、slab 或新建高度 |
| US3 | P1 | 选择合法基准和高度，将完整 B4 轮廓显式创建为原生 Space；R04–R09 | 用 fixture plane 检验 storey/slab、authored/manual OR、两种墙模式、shell/holes 几何及取消/故障恢复，无须先跑自由空间 |
| US4 | P1 | 在目标空间和平面上执行参与策略一致的自由空间分析；R10/R11 | 用受控 plane/domain/家具 fixtures 检验 group/trend/affordance/target veto、物理占用及 query，不以新建 Space 为前置 |
| US5 | P1 | 新建和已有 Space 两条路径均能保存重开并复核；R12 | 集成 US1–US4，分别完成 plane→Space→free-space→save/reopen，保留身份/历史并恢复 requires_recheck |

## 已冻结的用户选择

- D1：只使用明确、有单位和 provenance 的 authored 楼层高度；缺失/无效/歧义时使用手动高度。不以相邻楼层标高差推断层高。两条路径是 OR；零标高是有效底面，不是层高。
- D2：slab 基准是用户选定 slab 的水平上表面。必须验证其唯一高程及楼层归属；倾斜、多级或无法可靠识别时明确拒绝，不取 bbox 顶面或静默投平。
- D3：本轮引入 plane/space 两种薄组合绑定。原生 camera/IfcSpace 的身份与几何权威保留；OA 只存分析身份、修订和必要溯源，不新增 IFC class 或通用对象框架。
- D4：Set Camera 提供“新建 Bonsai drawing camera”与“选择已有 drawing camera 并转换/绑定分析平面”两条入口。手动 Z、当前 viewport 或激活旧相机不替代它。当前完整工作流仅接纳受支持的水平平面；倾斜姿态明确拒绝，不静默改平。底层 CameraBinding 可记录的姿态范围不等于每个 query 都已支持；exact world-XY section 继续遵守 canonical basis 能力限制。

本机已核实创建链路为 `bim.add_drawing → bonsai.core.drawing.add_drawing → Drawing.create_camera`；已有相机采用复用 `read_camera_binding/plane_from_camera/refresh_camera_plane`。研究依据与技术边界见 [research.md](research.md)，数据及 UI/authoring 契约见 [data-model.md](data-model.md) 与 [contracts/workflow.md](contracts/workflow.md)。

## 约束

不新增围合/占用算法、通用对象框架或结果注册表。不更改 room_analysis_model 公共导出。保留 B3 OPEN。
Pixi 管理环境；只用指定 portable Blender。生产 IFC authoring 必须显式，自动验证用独立 disposable IFC/Blend。jj 优先，提交/推送/合并不在本次授权范围。

## 当前阶段

speckit-plan Phase 0/1 和 speckit-tasks 已完成，实施任务见 [tasks.md](tasks.md)。下一阶段先执行 T001–T003，恢复可验证基线，再按故事逐项实现；验证入口见 [quickstart.md](quickstart.md)。任务生成阶段未执行生产 IFC 写入、代码集成或部署。
