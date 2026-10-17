# Tasks: Analyzer 完整工作流补齐

日期：2026-10-19。状态：任务已生成，实施未开始；所有实现复选框保持未完成。

**Input**：[spec](spec.md)、[plan](plan.md)、[research](research.md)、[data-model](data-model.md)、[workflow contract](contracts/workflow.md)、[quickstart](quickstart.md)。

**Organization**：按 spec 的 US1–US5 分组，五组均为 P1 必需范围。测试来自 R01–R12 明确要求的验收；先补能揭示缺口的断言并记录失败，再实现，已有行为继续作为回归。

## 格式、路径与执行边界

- 格式：`- [ ] Tnnn [P?] [USn?] 描述及文件路径`；`[P]` 只表示满足依赖后可在不同文件并行，不表示本轮启动代理。
- 下列路径均相对**实施用 task-owned jj workspace 根目录**。该 workspace 尚未创建；当前文档位于主仓库。T001–T003 对应 plan 的 T0，不把当前主树误作已具备交付接口的基线。
- 优先 jj，安装命令及帮助先验证；只读检查使用 `jj --ignore-working-copy`。保留无关 dirty work；不授权提交、推送、合并或生产部署。jj 不可用时记录具体原因再用 Git fallback。
- Pixi 管理项目环境；native 验证仅使用 `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`。所有 IFC/Blend authoring 验证使用独立 disposable fixtures；每次 native 运行使用 quickstart 规定的新输出目录。
- 不新增围合算法、通用对象/结果框架、IFC class、FieldStatus 或 `room_analysis_model` 公共形状。B3 保持 OPEN。新增项目函数遵守 AGENTS 的英文 docstring 与重要计算说明要求。
- 数据约束引号逐字引用 data-model；具体接口和序列化版本以 T0 恢复的实际代码为准。constitution 仍是未批准模板，不擅自批准或套用占位原则。

## Phase 1: Setup — 恢复可审计基线

**目标**：得到可导入、可复现已知缺陷的最小工作流闭包；不整树复制历史工作区。

- [ ] T001 验证已安装 jj 的 workspace/只读命令及帮助，记录主工作区与 delivery/workflow007 的 revision、dirty 范围和既有授权边界，再建立 task-owned jj workspace；按 `specs/008-analyzer-workflow-completion/quickstart.md` 验证 Pixi/指定 portable，记录到 `outputs/spec008-setup/baseline.json`。
- [ ] T002 从 sibling `order_analyzer_spec004_delivery` 审计有界 imports/config/tests/fixtures/exports 闭包，将 addon、camera/live/session/capture/result-wire、request 及其实际依赖恢复到隔离副本；核对 `pixi.toml`、`pixi.lock`、`blender_addon/order_analyzer_ui/__init__.py`、`features/analysis_requests.py`，逐文件记录完整 SHA256/来源 revision/dirty 差异；单独解释 workflow007 冲突的取舍而非复制冲突或无关改动，更新 `outputs/spec008-setup/baseline.json`。（依赖：T001）
- [ ] T003 在恢复副本执行导入及现有定点检查，重现 `test/test_physical_occupancy_resolution.py::test_furniture_exclusion_vetoes_direct_group_and_affordance_contribution` 的 support_area=4.0/期望 None 失败，保留 view 排除、physical inventory 保留 A/B 的通过证据；输出 `outputs/spec008-setup/baseline-tests.txt`，若实际状态不同则记录差异并追查来源，不改断言或伪造预期失败。（依赖：T002）

**Checkpoint**：基线文件、依赖与实际字节可追溯，已知失败的真实状态明确，之后才改功能。

## Phase 2: Foundational — 共同身份、失效与验收前置

**目标**：复用现有 session/Region/version，固定共同验证数据，不建立第二套状态机。此阶段完成后才进入故事实现。

- [ ] T004 [P] 在 `specs/008-analyzer-workflow-completion/quickstart.md` 固定可复现输入、期望和线/面积/体积数值容差及单位/来源，说明复用的现有 fixture 或测试内生成位置；覆盖米/毫米、quantity override、scene scale/object transform、凹 shell/holes/非零 base、斜面/多级 slab 和拒绝矩阵。遵守“在运行前固定并记录 fixture 的线/面积/体积容差、单位和来源；B4 gap-closing 容差不自动成为 extrusion 几何误差许可”。（依赖：T003）
- [ ] T005 [P] 在 `test/test_blender_analysis_session.py`、`test/test_blender_analysis_regions.py` 增加两个薄组合绑定的兼容缺省、source/project/plane/query/domain 改变失效及历史保留断言；验证“沿用现有 session 失效与复核状态；显式采用/refresh 后才可确认；重开为 requires_recheck”和“沿用 Region confirmation；source/plane/query/domain 改变则失效；保存重开不自动恢复旧确认”。（依赖：T003）
- [ ] T006 在 `adapters/blender_analysis_session.py`、`adapters/blender_analysis_result_wire.py` 的既有 mappings/version 机制补共同 identity/revision/provenance 与失效交接，使 T005 通过；遵守“native object/entity 引用只在运行时使用，不序列化 Python 指针或 Blender 名称作为权威身份”，不扩大公共结果形状。（依赖：T004、T005）

**Checkpoint**：共同基础可用，US1–US4 可用各自 fixtures 独立验证；共享源码文件的修改仍须串行。

## Phase 3: US1 — 原生 camera 到分析平面（P1，首个增量）

**Goal**：两条 camera 入口和 refresh 产生准确、可复核的 AnalysisPlane；R01/R02、D3/D4。

**Independent Test**：仅 disposable drawing 场景，验证 new/adopt/refresh、移动/替换/删除/项目切换、unsupported pose/query 和取消/恢复，不依赖 B4 或 Space。

### Tests

- [ ] T007 [P] [US1] 在 `test/test_bonsai_analysis_plane.py` 增加 native project/GUID/object 对应、geometry_author 与 display-only 资格、SI pose/正交右手 basis、倾斜拒绝、exact world-XY canonical basis、refresh revision 与四种垂直参数分离的断言，先记录缺口。（依赖：T006）
- [ ] T008 [P] [US1] 在 `test/test_blender_analysis_ui.py`、`test/test_blender_analysis_session.py` 增加 new/adopt/refresh 动作、非 camera/错误来源拒绝、依赖确认失效及 adopt/read/refresh 前后 IFC 不变的测试。（依赖：T006）
- [ ] T009 [P] [US1] 在 `test/bim/run_analysis_plane_bonsai_smoke.py` 增加 native Add Drawing 的成功、取消、开放/已 finalize 失败、无关活动事务拒绝与恢复失败阻断断言；快照 entity/relationship、camera/annotation/group/document、Blender 数据/links、history/redo、cursor/selection/container，验证重试及成功 undo/redo，不以总数相等代替资源身份检查。（依赖：T006）

### Implementation

- [ ] T010 [US1] 在 `adapters/bonsai_analysis_plane.py` 复用 read_camera_binding/plane_from_camera/refresh_camera_plane 完成准确 native 读取与能力拒绝；落实“原生 IFC 身份；验证 native entity/object 的一一对应及 drawing-camera 资格；名称仅展示”、“既有 native-backed camera pose、单位/来源及 revision；display-only binding 不得用于 author/refresh”和“OA 分析身份；原点 SI、正交右手 basis；由 native pose 转换，禁止静默投平”。（依赖：T007）
- [ ] T011 [US1] 在 `adapters/bonsai_analysis_plane.py` 的窄 native 入口接通 `bim.add_drawing → bonsai.core.drawing.add_drawing → Drawing.create_camera`，准确取得返回 refs 并实现本操作有界恢复；区分 open discard 和 finalized history，不依赖 wrapper 自动回滚、不无界 undo；恢复失败阻断成功发布/自动保存，取消不残留关联资源。（依赖：T009、T010）
- [ ] T012 [US1] 在 `blender_addon/order_analyzer_ui/__init__.py`、`adapters/blender_analysis_session.py` 接线 new/adopt/refresh、来源展示和失效；fingerprint 遵守“用于比较相机移动、替换、删除、项目切换及重开；不代替 native truth”；保持 camera Z 与 Space base、B4 cut、extrusion height 独立，不以手动 Z/viewport/激活旧 camera 替代创建。（依赖：T008、T011）
- [ ] T013 [US1] 运行 `test/test_bonsai_analysis_plane.py`、受影响 UI/session 定点测试及 `test/bim/run_analysis_plane_bonsai_smoke.py` 的 008 断言；证据写入本次新建运行目录的 `camera/report.json`，真实证明 R01/R02 的 native 创建/恢复与只读入口边界，失败则本故事不通过。（依赖：T012）

**Checkpoint**：平面功能可单独演示；native 恢复证明不可用时不能标记 new camera 已完成。

## Phase 4: US2 — 直接采用已有 IfcSpace（P1）

**Goal**：从视口或原生列表明确使用合格已有 Space；R03、D3。

**Independent Test**：fixture plane + 既有 IfcSpace，两个入口均通过；错类型、缺几何、错层、重复身份、不支持几何均拒绝，完全不填 B4/slab/新建高度。

### Tests

- [ ] T014 [P] [US2] 在 `test/test_bonsai_live.py`、`test/test_blender_analysis_capture.py` 增加已有 Space 的 GUID/source/object/storey、单一有效 shell/holes 与全部资格拒绝矩阵，验证采用不写 IFC、不要求 B4/height。（依赖：T006）
- [ ] T015 [P] [US2] 在 `test/test_blender_analysis_ui.py`、`test/test_blender_analysis_regions.py` 增加视口选择和源列表选择后点击使用的断言，以及展示名称变化不改变身份、domain 改变使确认失效的测试。（依赖：T006）

### Implementation

- [ ] T016 [US2] 在 `adapters/bonsai_live.py`、`adapters/blender_analysis_capture.py` 复用 canonical capture → authored_space_domain；身份遵守“指向唯一 native source；canonical source/ref 与 GUID 一致，名称仅展示”，storey 遵守“验证所属层；缺失、冲突或与当前目标层不一致时拒绝采用，不按名字猜”，domain 遵守“支持的单一有效几何及 shell/holes；存观察 digest/版本用于 freshness，回读 native 后才能确认当前性”。（依赖：T014）
- [ ] T017 [US2] 在 `blender_addon/order_analyzer_ui/__init__.py`、`adapters/blender_analysis_session.py` 将两种选择交给相同 Space composition/Region 采用入口；遵守“复用现有 Region/domain；来自 `authored_space_domain` 的资格校验和 canonical geometry”、“区分采用既有 Space 与 created_from_b4；后者保留 candidate/session/frame/outline digest 和 authoring 参数来源”和“只记录本次确实使用的参数；既有 Space 直接采用无需先填 B4 基准或人为重建拉伸高度”。（依赖：T015、T016）
- [ ] T018 [US2] 运行 US2 的 live/capture/UI/Region 定点测试，并用 `test/bim/run_blender_analysis_workflow_smoke.py` 的 authored_ifcspace fixture 仅检验采用阶段，输出新运行目录的 `existing-space-adopt/report.json`；fixture plane 可替代 US1 运行结果，不把缺 free-space 闭环算本故事失败或完成 R12。（依赖：T017）

**Checkpoint**：已有 Space 采用独立可用；UI 中没有无意义的新建参数前置。

## Phase 5: US3 — B4 完整轮廓到原生 Space（P1）

**Goal**：保留 B4 既有能力，基准/高度 OR，完整 shell/holes 显式 native authoring；R04–R09、D1–D3。

**Independent Test**：fixture plane，storey-only/base=0 与 slab-only 分别成立；authored/manual 各成立；两种墙模式和完整 UI 不退化；凹 shell/holes/非零 base 的 native round-trip 一致，取消/故障恢复无残留且可重试。

### Tests

- [ ] T019 [P] [US3] 新增 `test/test_bonsai_space_authoring.py` 的 datum/height/单位/轮廓测试：0 base、唯一 slab native 关系与水平上表面、共面三角片、斜面/多级拒绝、GrossHeight 唯一有效量与 Unit override、manual 有限正值、缺量不以 elevation/NetHeight/默认值补齐、无效环/MultiPolygon/stale 拒绝，采用 T004 固定期望。（依赖：T006）
- [ ] T020 [P] [US3] 在 `test/test_bonsai_live.py`、`test/test_blender_analysis_ui.py`、`test/test_candidate_preview.py` 增加 normal 清 selected scope、内部未选墙继续影响、开放边界拒绝、timer/cancel/cache/eye/area/tolerance/closed aperture/current-attempt-refusal-stale/residual 保留及 Analyze/preview/eye/选择不写 IFC 的断言。（依赖：T006）
- [ ] T021 [P] [US3] 在 `test/bim/run_blender_analysis_workflow_smoke.py` 增加直接调用窄 adapter 的 008 几何和恢复 fixture；覆盖凹 shell/洞、坐标/单位/非零 base，以及 curve/profile/entity/class/storey/assignment/switch/round-trip 故障点、open/finalized、无关活动事务、恢复失败、重试/undo/redo；复用 T009 的检查维度，不新增通用恢复框架或虚构 CLI fault 参数。（依赖：T006）

### Implementation

- [ ] T022 [US3] 新增 `adapters/bonsai_space_authoring.py` 的窄 datum 解析并接 `adapters/bonsai_live.py` 的 StructuralContext；storey 遵守“明确 storey_ref 与已验证变换后的 SI 底面；`0.0 m` 合法，不等于 height”；slab 遵守“选定 slab_ref、唯一 native storey 关系、变换后水平上表面及 SI datum；共面三角片可共享平面，倾斜/多级/歧义拒绝”，slab-only 自动解析唯一关系，不取 bbox/maxZ。（依赖：T019）
- [ ] T023 [US3] 在 `adapters/bonsai_space_authoring.py` 实现 authored/manual 高度 OR；遵守“`Qto_BuildingStoreyBaseQuantities.GrossHeight` 的唯一有效 `IfcQuantityLength`；记录 entity/ref/path、原数值、quantity Unit 或 project length unit、SI 值”、“用户明确输入的有限正长度，携带输入单位和 SI 值；authored 缺失/无效/歧义时可直接使用”和“native project/storey/slab/quantity refs、转换来源及已观察 revision；无相邻 Elevation 相减、NetHeight 替代或默认高度”。（依赖：T022）
- [ ] T024 [US3] 在 `adapters/bonsai_live.py`、`adapters/blender_analysis_session.py` 的既有 B4 handoff 传入合法 datum 和模式，遵守“复用 `StructuralContext.datum_z_m/cut_z_m/storey_ref/selected_wall_refs`；记录 cut offset 与 absolute cut 的关系，不以 camera Z 或 extrusion height 覆盖”；保留现有 service/reducer/索引/缓存，两种墙模式均通过 T020。（依赖：T020、T023）
- [ ] T025 [US3] 在 `blender_addon/order_analyzer_ui/__init__.py` 接 storey/slab 与 authored/manual OR 表单及来源展示；遵守“storey 或 selected slab，二选一；切换使旧候选/确认失效”和“authored quantity 或 manual，二选一；显式记录实际使用来源，无隐式合并/叠加”；保留 T020 中所有 B4 控件和诊断，slab-only 不重复强制选层。（依赖：T024）
- [ ] T026 [US3] 在 `adapters/blender_analysis_session.py`、`adapters/bonsai_space_authoring.py` 冻结既有 candidate document 的 source/capture/session/attempt/candidate/frame、墙范围、datum/height/units、B4 参数/version/digest；遵守“shell/holes 坐标有限、闭合、有效，面积为正；内环在 shell 内且互不相交/接触，不接触 shell”、“一个 candidate 对应一个 Polygon；意外 MultiPolygon 或损坏环明确拒绝，不做 hull/buffer/丢片段修复”和“digest 保留环的几何与拓扑；按 native API 约定整理闭合点重复和环方向时，不得改变轮廓语义或重新围合”。（依赖：T023、T024、T025）
- [ ] T027 [US3] 在 `adapters/bonsai_space_authoring.py` 实现仅属本操作的 transaction key/边界与 owned IFC/Blender resources/links/UI 状态恢复；拒绝无关活动事务，分别处理 open discard 和已 finalize 的有界恢复；不替换 active IFC、不无界 undo/按名称删除；恢复失败阻断成功发布和自动保存，恢复数据不进入公共导出。（依赖：T021、T026）
- [ ] T028 [US3] 在 `adapters/bonsai_space_authoring.py` 实现 structural-local → world SI → product-local → IFC units 的一次长度转换，native closed polyline + profile(outer_curve, inner_curves) + extrude，再接 representation assignment/switch、class/collector/storey placement；保留全部 holes，从 datum 向 +Z 拉伸 height，不使用 seed 重围合或 exterior-only polygon helper。（依赖：T027）
- [ ] T029 [US3] 在 `adapters/bonsai_space_authoring.py` 依据 T004 容差回读 native representation，逐环比较 topology/边界/净面积/base/top/volume；验证后仅返回准确 entity/GUID/object，再由 `adapters/blender_analysis_capture.py` canonical recapture；校验失败走恢复，不发布临时 mesh。（依赖：T028）
- [ ] T030 [US3] 运行 `test/test_bonsai_space_authoring.py` 和 `test/bim/run_blender_analysis_workflow_smoke.py` 的 adapter-only geometry/fault fixtures，输出新运行目录的 `space-authoring/report.json`；逐项证明原实体/关系/数据块/links/history/redo/UI 状态恢复、无关操作保留、再试一份及成功 undo/redo；仅 catch/CANCELLED/总数一致不通过，未证明前不得接成功发布。（依赖：T029）
- [ ] T031 [US3] 在 `blender_addon/order_analyzer_ui/__init__.py`、`adapters/blender_analysis_session.py` 将旧 seed-only/名称猜测创建交接替换为显式确认冻结 sketch → 窄 adapter → 精确 refs → US2 相同 authored_space_domain 采用；拒绝重复提交；遵守“source、plane、storey/slab、height、query 或 B4 参数改变后，旧 sketch/confirmation stale，必须重新准备/复核”和“内部 label/seed 仅供 UI 选择，不能替代 shell/holes。临时 sketch/preview 对象标记为展示产物，不进入 physical inventory”。（依赖：T025、T030）
- [ ] T032 [US3] 运行 US3 的 adapter/live/UI/session/candidate 定点回归及 `test/bim/run_blender_analysis_workflow_smoke.py` 的 008 native 创建检查，输出新运行目录的 `b4-space/report.json`；覆盖全部 datum/height OR、两种墙模式、只读操作 IFC 不变、明确确认才写、精确返回与 recapture，不能由旧 smoke PASS 或 seed 成功替代 R04–R09。（依赖：T031）

**Checkpoint**：完整轮廓和恢复都已在 native fixture 证明后，才允许把新建 Space 当可采用结果；自由空间尚不由此自动确认。

## Phase 6: US4 — 家具资格与自由空间（P1）

**Goal**：共享 furniture veto 到所有目标消费者，保留物理事实和既有 query/Field 语义；R10/R11。

**Independent Test**：受控 scene + plane/domain fixtures，无须 US3 authoring；included/excluded/unknown/unset、空 eligible 集、direct group/trend/affordance/target、其他占用及三类 query 均有明确结果。

### Tests

- [ ] T033 [P] [US4] 在 `test/test_physical_occupancy_resolution.py` 保留 T003 原失败断言并扩展 participation 四态、空/混合 eligible members、raw authored refs 与 source-specific SupportBinding；证明排除家具目标仍保留 A/B 物理占用，选 slab datum 不使所有 slabs 免占用。（依赖：T006）
- [ ] T034 [P] [US4] 在 `test/test_group_self_description.py`、`test/test_affordance_aisle.py`、`test/test_analysis_requests.py` 增加 direct group/trend/affordance/target 旁路和 whole-height/section/finite-band、抬 plane、unsupported basis、unknown 的断言；不得由名称/图层/邻近创造 authored group。（依赖：T006）

### Implementation

- [ ] T035 [US4] 在 `features/neutral_scene_views.py`、`features/group_self_description.py` 复用 furniture_analysis_participation 修复 _neutral_inputs/_group_geometry/_trend_geometry 的共享 veto；遵守“excluded/unknown 在家具目标分析中执行 shared veto；unset 保留既有行为”和“无 eligible members 时 support_area=None、member_geometry=[]、trend unavailable”，保留 raw refs 和 physical inventory。（依赖：T033）
- [ ] T036 [US4] 逐一追踪 `features/group_self_description.py`、`features/affordance/evaluator.py` 的实际 affordance/target 调用者，仅修复已证实的资格旁路，使 T034 的消费者断言通过；若现有入口已遵守共享策略则复用并记录，不增加平行 eligibility 类型或改占用算法。（依赖：T034、T035）
- [ ] T037 [US4] 在 `features/_analysis_domain_handoff.py`、`features/analysis_requests.py`、`adapters/blender_analysis_session.py` 交接明确 domain/plane/group/source/query identity，复用 request/field/resolver；遵守“SupportBinding 只作用于明确的 source 与关系；slab datum 选择不把所有 slabs 排除”和“whole-height/section/finite-band 沿用既有 request 身份，camera Z 改变不隐式切换 query；unknown 继续携带 diagnostics/provenance，不能当 free”。（依赖：T036）
- [ ] T038 [US4] 在 `blender_addon/order_analyzer_ui/__init__.py` 的既有 free-space 动作展示当前 plane/Space/明确组目标与 query，只有有效确认才运行，unsupported/unknown 保留诊断和其他物理实体占用；不新增结果注册表或从 preview 重建 Field。（依赖：T037）
- [ ] T039 [US4] 运行 `test/test_physical_occupancy_resolution.py`、`test/test_group_self_description.py`、`test/test_affordance_aisle.py`、`test/test_analysis_requests.py` 及受影响 session/UI 回归，将 T003 原断言的转绿及 occupancy 不变证据写入 `outputs/spec008-eligibility/regression.txt`，不删除历史失败。（依赖：T038）

**Checkpoint**：目标资格和占用分离，query/unknown 语义完整，可对 fixture domain 独立完成自由空间分析。

## Phase 7: US5 — 两条路径保存重开闭环（P1）

**Goal**：集成 US1–US4，既有/新建 Space 各完成一次完整闭环；R12。

**Independent Test**：两份独立 disposable IFC/Blend，分别 plane→adopt/create Space→free-space→save；新进程重开为 requires_recheck，重新 resolve/capture/显式复核后才运行当前分析。

### Tests

- [ ] T040 [US5] 在 `test/test_blender_analysis_session.py`、`test/test_blender_analysis_runtime.py`、`test/test_blender_analysis_regions.py` 增加旧文档缺省/迁移、两种 Space origin、plane/domain/query/revision/provenance round-trip、历史可读而确认不恢复，以及 native 身份删除/替换/项目切换的拒绝测试。（依赖：T013、T018、T032、T039）

### Implementation

- [ ] T041 [US5] 在 `adapters/blender_analysis_session.py`、`adapters/blender_analysis_result_wire.py`、`adapters/blender_analysis_capture.py` 完成既有 save/load/version 的薄绑定接线并通过 T040；遵守“还原身份、参数、历史结果与 provenance；requires_recheck”和“不得从展示 mesh 重建权威 Field/result，也不改变 `room_analysis_model` 公共形状”，重开重新验证后才能显式确认。（依赖：T040）
- [ ] T042 [US5] 在 `test/bim/run_blender_analysis_workflow_smoke.py` 扩展 008 的完整 smoke/reopen 断言和准确源/参数报告：保存 `saved_copy.blend`，重开输出在其同级 `reopen`；保存后有身份、重开后无旧确认、历史结果可读、复核后可重跑，沿用 quickstart 已核实 CLI 参数。（依赖：T041）
- [ ] T043 [P] [US5] 按 `specs/008-analyzer-workflow-completion/quickstart.md` 用 `test/bim/run_blender_analysis_workflow_smoke.py` 的 selected_walls + native-create-space 路径执行完整闭环和新进程 reopen，输出本次新运行目录的 `new-space/report.json`、`new-space/saved_copy.blend`、`new-space/reopen/report.json`，含 shell/holes/base/height/返回 GUID 对照。（依赖：T042）
- [ ] T044 [P] [US5] 按 `specs/008-analyzer-workflow-completion/quickstart.md` 用 `test/bim/run_blender_analysis_workflow_smoke.py` 的 authored_ifcspace 路径执行完整闭环和新进程 reopen，输出独立新运行目录的 `existing-space/report.json`、`existing-space/saved_copy.blend`、`existing-space/reopen/report.json`；不得要求 B4 或新建高度。与 T043 使用隔离进程/文件、只读取脚本。（依赖：T042）
- [ ] T045 [US5] 使用 `test/bim/run_blender_analysis_workflow_smoke.py` 在保存副本上补做 camera/Space 删除、移动/几何替换、项目/来源不符和 query 改变的 reopen/recheck 拒绝检查，写入新运行目录的 `recheck/report.json`；验证旧结果只作历史、不能自动恢复确认或发布当前成功。（依赖：T043、T044）

**Checkpoint**：两条路径都具备真实 smoke/reopen 证据；任一仅旧版 PASS 均不算 R12 完成。

## Phase 8: Polish & Cross-Cutting — 交付与实际运行证据

**目标**：只做本 feature 必需回归、加载/交互/性能证明与文档同步，不追加无关清理。

- [ ] T046 按 `specs/008-analyzer-workflow-completion/quickstart.md` 运行已受影响的 Pixi 回归集合及新增 `test/test_bonsai_space_authoring.py`，核对 imports/fixtures/config/exports 与公共形状兼容；失败只修本 feature 引入的问题，保留命令/环境/结果到 `outputs/spec008-acceptance/pixi-tests.txt`。（依赖：T045）
- [ ] T047 在独立 disposable native 新进程核验待交付 addon/adapters 的实际加载 `__file__` 与完整 SHA256，使用 `test/bim/run_analysis_plane_bonsai_smoke.py`、`test/bim/run_blender_analysis_workflow_smoke.py` 将加载路径/字节与 T002 manifest 及最终实现比较，记录 `outputs/spec008-acceptance/loaded-modules.json`；operator 注册或旧进程状态不算实现已加载，不改生产安装。（依赖：T046）
- [ ] T048 按 `specs/008-analyzer-workflow-completion/quickstart.md` 的真实窗口流程验收两条 camera、已有 Space 视口/列表、B4 两模式、基准/高度 OR 和 progress/cancel/candidate/eye/area/diagnostics/overlay/GPU，记录动作、输入、实际结果及截图引用到 `outputs/spec008-acceptance/ui-gpu.md`；仅使用 T047 证明的代码和指定 portable，headless 不替代此项。（依赖：T047）
- [ ] T049 用 `test/bim/run_blender_analysis_workflow_smoke.py` 及 T048 场景记录 full capture、B4 preparation、局部选墙过滤、候选查询、authoring 各段 source 数/耗时/cache/cancel，写入 `outputs/spec008-acceptance/timings.json`；如实区分节约与仍发生的成本，不把 selected-wall 等同全场加载为零，不新增未测速度承诺。（依赖：T048）
- [ ] T050 依据实际通过证据同步 `docs/software-architecture.md`、`docs/indoor_layout_evaluation_matrix_architecture_memory.md`、`specs/008-analyzer-workflow-completion/checklist.md`、`specs/008-analyzer-workflow-completion/quickstart.md` 的实现位置、验收命令和 R01–R12 证据链接；仅勾选真正通过项，保留未通过/未执行、R10 历史与 B3 OPEN，并核对本任务清单完成状态。（依赖：T049）

## Dependencies & Execution Order

### 故事依赖

```text
T001 → T002 → T003 → {T004, T005} → T006
                                        ├─ US1 T007–T013 ─┐
                                        ├─ US2 T014–T018 ─┤
                                        ├─ US3 T019–T032 ─┼→ US5 T040–T045 → T046–T050
                                        └─ US4 T033–T039 ─┘
```

US1–US4 的**独立验收**均可用共同基础和自己的 fixtures，不要求先跑其他故事。生产闭环合并在 US5。默认按编号顺序推进；并行只在已满足任务行内依赖且写入文件/运行状态互不冲突时成立。

### 故事内与共享文件约束

- 所有故事先完成对应测试缺口记录，再补实现；每条任务行内列出的依赖为执行前置，不跨过检查门槛。
- `blender_addon/order_analyzer_ui/__init__.py`、`adapters/blender_analysis_session.py` 和 `adapters/bonsai_live.py` 被多个故事使用，其实现修改串行整合，不将不同故事标签视作不同文件。
- `test/bim/run_blender_analysis_workflow_smoke.py` 的 T021、T042 等编辑串行；T043/T044 执行时只读已冻结脚本，并使用隔离 Blender 进程和独立新输出目录。
- T011/T027 的恢复实现与 T013/T030 的 native 证明是写入入口的完成门槛；T031 的 Space 成功发布接线依赖 T030，不能把错误报告或取消标志算作原子恢复。
- 真实 UI/GPU、native headless 和 Pixi 分别验收；任务完成不自动产生提交/推送/合并授权。

### 每条故事的并行示例

| 范围 | 已满足前置后的可并行任务 | 边界 |
| --- | --- | --- |
| Foundational | T004 与 T005 | 文档 fixture 定义与 session/Region 测试文件分离 |
| US1 | T007、T008、T009 | plane 单测、UI/session 单测和 camera native 脚本不同文件；共同依赖 T006 |
| US2 | T014 与 T015 | live/capture 与 UI/Region 测试分离；不与 US1 同文件测试编辑并行 |
| US3 | T019、T020、T021 | 新 adapter 单测、B4/live/UI 单测、workflow native 脚本分离 |
| US4 | T033 与 T034 | occupancy 单测与 group/affordance/query 单测分离；实现 T035–T038 串行 |
| US5 | T043 与 T044 | 脚本修改 T042 完成后，两个独立 native 新进程/输出目录只读执行 |

`[P]` 共 14 项，属于上述六组；它不是并行修改共享 addon/session 文件的许可。

## Implementation Strategy

1. **先恢复基线**：T001–T003 明确实际依赖与已有失败，再完成共同基础 T004–T006；不从缺接口主树直接堆功能。
2. **首个可独立展示增量 / MVP**：US1（T007–T013），可原生新建/采用/刷新平面，包含取消/失败恢复证明。它只交付平面阶段，不声称完整分析已可用。
3. **最小可用分析闭环候选**：US1 + US2 + US4，以已有 Space 跑自由空间；仍须 US5 对该路径做保存重开，才能称该路径闭环验收通过。
4. **补齐新建路径**：US3 完成 datum/height、完整 B4 sketch authoring、原生几何及恢复证明，再将两条路径汇入 US5。
5. **完整交付**：US1–US5 与 T046–T050 全部实际验收；逐条用新证据更新 checklist，不迁移旧阶段 PASS。若 native/UI 条件不可用，保留未勾选和具体缺口，不用单测代替。

## 需求到任务的追溯

| 要求 / 冻结选择 | 主要实现任务 | 关键验收任务 |
| --- | --- | --- |
| R01 native Set Camera | T010–T012 | T009、T013、T048 |
| R02 adopt/refresh/revision | T006、T010、T012、T041 | T007–T008、T013、T040、T045 |
| R03 已有 IfcSpace | T016–T017 | T014–T015、T018、T044 |
| R04 datum OR | T022、T024–T025 | T019–T020、T032、T048 |
| R05 height OR / units | T023、T025、T028 | T019、T030、T032 |
| R06 两种墙范围 | T024–T025 | T020、T032、T049 |
| R07 完整 B4 UI/诊断 | T024–T025 | T020、T032、T048 |
| R08 精确 sketch/extrusion | T026、T028–T029、T031 | T019、T021、T030、T043 |
| R09 显式写入/原子恢复 | T011、T027、T031 | T009、T013、T020–T021、T030、T032 |
| R10 furniture veto/occupancy | T035–T036 | T003、T033–T034、T039 |
| R11 plane/domain/query/Field | T037–T038 | T034、T039、T043–T045 |
| R12 两条闭环/reopen | T041–T042 | T040、T043–T048 |
| D1 authored/manual，非 elevation 差 | T023、T025 | T019、T032 |
| D2 slab 真实水平上表面 | T022、T024 | T019、T030、T032 |
| D3 两个薄组合绑定 | T006、T012、T017、T041 | T005、T040、T046 |
| D4 native new/adopt，拒绝不支持姿态 | T010–T012 | T007–T009、T013、T048 |

## 清单统计与完成口径

共 50 项：Setup 3、Foundational 3、US1 7、US2 5、US3 14、US4 7、US5 6、最终交付 5。所有 50 项均采用连续任务 ID、未完成复选框和明确文件路径；故事阶段均带对应 US 标签，其他阶段无 US 标签。

本次只生成任务和同步规划状态；功能、native 事务、实际加载字节、真实 UI/GPU 与性能均等待实施验证。
