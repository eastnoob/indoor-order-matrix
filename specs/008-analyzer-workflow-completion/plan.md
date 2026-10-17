# Implementation Plan: Analyzer 完整工作流补齐

**Feature / setup BRANCH**: `008-analyzer-workflow-completion` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Workspace**: 文档生成仍在 jj `default`；setup 返回的 BRANCH 是 feature 标识，不表示已经创建 Git branch/bookmark。状态为 **TASKS READY / IMPLEMENTATION PENDING**。

## Summary

按 [R01–R12](spec.md#用户意图与验收要求) 补齐“原生 drawing camera → 采用已有或由 B4 创建 Space → 自由空间 → 保存重开”的工作流。复用现有 CameraBinding、AnalysisPlane、B4 service/reducer、canonical capture、AnalysisRequest 和 Field；只增加 plane/space 两个薄组合绑定，以及一个窄的 Bonsai Space authoring adapter。

新建 drawing camera 使用 Bonsai native Add Drawing；已有 drawing camera 通过显式采用/刷新绑定平面。Space 底面来自 storey 或选定 slab 的水平上表面，拉伸高度来自明确 authored storey quantity 或手动值。B4 的完整 shell/holes 冻结为 sketch 后进入可带内环的 native profile/extrusion，不再以 seed 重新围合。家具参与策略统一作用于分析消费者，同时保留物理占用。

主仓库缺少交付副本中的若干工作流接口，因此 **T0 基线恢复是实施前置条件**。Phase 0/1 设计阶段仅交付文档；后续 speckit-tasks 已生成 [任务清单](tasks.md)，T0 对应 T001–T003。代码集成、部署与 IFC 写入尚未执行。

## Technical Context

| 项目 | 设计基线 |
| --- | --- |
| Language / Version | Pixi 锁定 Python 3.12.13（`>=3.12,<3.13`）；Blender 内 Python/Bonsai 使用指定 portable 的独立运行时，不把两套解释器当成同一环境 |
| Dependencies | 现有 Blender/Bonsai/IfcOpenShell、Shapely、Pixi/pytest 及项目已有模块；不新增包管理器或第三方依赖 |
| Storage | IFC 保存原生 camera/Space 身份与几何；沿用 OA session/Region/result JSON、Blend 内嵌文档及现有 sidecar；不新增数据库 |
| Testing | Pixi 定点与回归测试；disposable IFC/Blend 原生验证、故障注入、保存重开；真实 UI/GPU 验收独立记录 |
| Platform | Windows；仅 `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe` |
| Project Type | 现有 Python 分析库 + 薄 Blender addon + native Bonsai adapters |
| Performance | 保留 timer/cancel/cache；记录 source capture、B4 preparation、局部墙过滤、候选查询和 authoring 的各段成本，不虚构整链加速或新增无依据的延迟指标 |
| Constraints | native 身份/几何权威；SI 单位交接；unsupported tilt 明确拒绝；authoring 显式且可恢复；不改变 room_analysis_model 公共导出；B3 OPEN |
| Scope | 两条 camera 入口、两条 Space 入口、两种 B4 墙范围、两种高度来源，以及 free-space 和 reopen 闭环；不新增围合/占用算法或通用框架 |

## Constitution Check

`.specify/memory/constitution.md` 仍是未批准的模板，不能把其中占位原则当作已生效 constitution。本轮依据用户已冻结选择、AGENTS、[架构记忆](../../docs/indoor_layout_evaluation_matrix_architecture_memory.md) 和 [架构图](../../docs/software-architecture.md) 进行实际约束检查；不擅自批准或修改 constitution。

| Gate | Phase 0 前检查 | Phase 1 后检查 |
| --- | --- | --- |
| D1–D4 已有用户选择 | 已冻结，无待补充产品选择 | 研究/数据/契约一致；没有改成相邻标高差、bbox 顶面或手动 Z 替代 camera |
| 层边界与最小变更 | 明确复用现有模块 | 两个薄组合绑定、一个窄 authoring adapter；无新 framework/IFC class/公共结果 schema |
| 工作区与版本边界 | 已核实 jj；主工作区 dirty，交付代码另存 | 设计先恢复有界依赖闭包；保留其他改动，不在本轮提交/推送/合并 |
| IFC 写入边界 | preview/analyze/read 与显式 authoring 分开 | native camera 新建和 Space 新建均为显式写入；其取消/失败恢复列入实施门槛 |
| 环境 | Pixi + 指定 portable | 验证指南遵守；本轮未启动 Blender 或安装环境 |
| 实际实现可用性 | 主树缺接口、workflow007 存在冲突、R10 有失败 | 均明确保留为实施前置与回归，不声称通过 native 验收 |
| 数据与诊断保全 | 物理占用、unknown、B4 diagnostics 是既有契约 | contracts 保留；保存重开恢复为 requires_recheck，不自动确认 |

结果：设计约束检查通过，后续任务拆分已完成。**native 几何、事务恢复、运行时字节及闭环验收尚未执行，不能由该设计检查替代。**

## Project Structure

### 本 feature 文档

```text
specs/008-analyzer-workflow-completion/
├── spec.md
├── checklist.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    └── workflow.md
```

`tasks.md` 由后续 `speckit-tasks` 生成，全部实现复选框保持未完成。

### 目标实现位置与依赖闭包

以下是已审计 delivery 的既有模块和计划新增位置，不表示它们已全部存在于当前主树。

| 位置 | 责任 / 变更范围 |
| --- | --- |
| `blender_addon/order_analyzer_ui/__init__.py` | 接入 native camera 创建/采用/刷新、基准/高度表单、Space 明确确认；保留完整 B4 UI 和现有异步入口 |
| `adapters/bonsai_analysis_plane.py` | 复用 CameraBinding/read/plane/refresh；验证 native 身份、姿态、单位和修订 |
| `adapters/bonsai_live.py` | 保持 StructuralContext、canonical source/storey、authored_space_domain 资格判断；支持已验证 slab datum 的交接 |
| `adapters/bonsai_space_authoring.py` | **计划新增**：基准/高度 native 解析、冻结轮廓到 native profile/extrusion、精确返回身份、几何验证及事务恢复；不做第二套围合 |
| `adapters/blender_analysis_session.py` | 薄 plane/space composition、freshness、失效/复核、确认与既有 Region/result 持久化 |
| `adapters/blender_analysis_capture.py`、`adapters/blender_analysis_result_wire.py` | 复用 capture、request/result 交接和保存读取；只补受影响字段与身份校验 |
| `features/analysis_requests.py` | 保持 query 能力、身份和拒绝语义，禁止 plane Z 偷改 whole-height |
| `features/neutral_scene_views.py`、`features/group_self_description.py` | 共享 furniture participation veto 到 group/trend/affordance 等消费者，保留 raw authored refs 与 occupancy |
| 现有 B4/domain service 与 `features/affordance/` 消费入口 | 沿用已有入口；仅在发现共享参与策略旁路时修复，不更换算法 |
| `test/test_*analysis*.py`、`test/test_physical_occupancy_resolution.py`、`test/test_candidate_preview.py` | 覆盖调用者、UI 状态、单位/几何、eligibility 和旧行为回归 |
| `test/test_bonsai_space_authoring.py` | **计划新增**的窄 adapter 定点测试；真实 IFC/Blender 恢复另由 native fixture 验证 |
| `test/bim/run_analysis_plane_bonsai_smoke.py`、`test/bim/run_blender_analysis_workflow_smoke.py` 与既有 fixtures | 扩展 008 断言、fault injection、两条 save/reopen；旧 PASS 不迁移 |
| `pixi.toml` / `pixi.lock`、既有 addon 打包与导出 | T0 审核依赖闭包与加载路径；除非实际缺依赖，不更改配置/导出；room_analysis_model 形状保持 |

## 实施顺序与交付门槛

此设计顺序已细化为 [tasks 清单](tasks.md)；实际执行以其中的任务依赖和验收门槛为准。

1. **T0：恢复可验证基线。** 以 delivery `spec004-delivery@4b332704` 为审计来源，在 task-owned jj workspace 恢复所需 imports/config/tests/fixtures/exports 闭包；同时记录 revision、文件完整 SHA256 与 dirty 差异。workflow007 的 `features/analysis_requests.py` 冲突单独对照，不整树复制、不整包纳入主工作区 dirty work。完成导入检查并重现 R10 已知失败后才开始功能修复。
2. **薄绑定与输入资格。** 在现有 session/Region 内补 plane/space composition；冻结 project/source/pose/outline/query 身份。实现 storey/slab datum 与 authored/manual height 的 OR 选择和 SI 转换；零底面合法，非正高度拒绝。
3. **Camera UI 接线。** new drawing / adopt existing / refresh；创建取消及失败恢复，精确 native identity；清楚拒绝 unsupported pose。验证 camera plane、B4 cut、Space base/height 相互独立。
4. **B4 到 native Space。** 保留两种墙模式及完整 diagnostics；冻结 shell/holes，预检后显式确认；native void-capable profile/extrude/representation/storey placement；验证几何，返回准确 entity/object，再 canonical recapture/adopt。精确事务恢复先于成功发布。
5. **家具与 free-space。** 从 shared participation 入口修复 direct group/trend/affordance/target 旁路；保留物理 inventory 和 source-specific support binding；复用现有 request/field/resolver 与有限带/剖切能力检查。
6. **闭环验收与交付证据。** 运行 [quickstart](quickstart.md)：两条 Space 路径分别经过 plane→Space→free-space→save/reopen；注入 authoring 故障验证无残留且可重试/undo/redo；独立验证 UI/GPU、计时以及实际加载文件路径/字节。

native 事务 wrapper 的异常路径不会自动回滚；若无法证明 IFC、Blender 数据及历史回到本操作前的精确边界，R09 不通过，不能将部分创建结果发布为已确认 Space。已有分析结果按现有 freshness 规则保留历史，不伪装成当前成功。

## Complexity Tracking

无须豁免的架构/复杂度违例。复用现有模型与平台；唯一新 adapter 用于隔离 native authoring 与恢复，避免把 Blender/IFC 依赖引入分析核心。详细决策、契约及验收分别见 [research](research.md)、[data-model](data-model.md)、[workflow](contracts/workflow.md) 和 [quickstart](quickstart.md)。
