# Free-space prerequisite checklist and execution protocol

> **For agentic workers:** Use the project [verified-agent-workflow skill](../../../skills/verified-agent-workflow/SKILL.md): Spec Kit consistency/gap assessment, Superpowers task execution, independent acceptance and review, then the designated writer's local jj commit. Decide visual necessity per correctness question; do not require a picture or user approval per task.

**Goal:** 在目标 IFC 场景中管理一个世界 Z=1.6 m 的分析平面物体，按选定楼板顶面到该平面的高度带计算 S3 自由空间，持久缓存，并提供下游可验证的读取接口。

**Architecture:** 延续已有 freespace 工作线，复用 native drawing-camera / `AnalysisPlane`、高度带投影、`FreeSpaceField` 和结果存取链。补齐物体管理、datum 接线、参与范围审计和缓存命中流程；距离算法继续由距离工作线拥有。

**Tech Stack:** Pixi / Python 3.12、现有几何依赖、Blender/Bonsai、IfcOpenShell、Blender MCP、Jujutsu；不新增依赖或调度框架。

**Spec:** 本文件的“任务语义”记录本轮用户要求；已有架构依据为 `docs/indoor_layout_evaluation_matrix_architecture_memory.md`、`docs/software-architecture.md` 和 `specs/008-analyzer-workflow-completion/`。旧文档与本轮用户要求冲突时，保留历史记录并更新当前任务说明。

**Date / status:** 2026-11-04；Tasks 0–6 完成。最终全范围规格/质量审查 PASS、无产品缺口；本地接受提交 `9ff90182`（change `qurnkros`，parent `a19bfc85`）保存已独立验收的最终交付，后续仅记录本次接受与清单状态。四次真实运行、独立进程生成哨兵、必要视图和实际读取均通过；用户视觉接受单独记录，不据沉默推断。

## Workspace and scope

- 清单最初存放在 `D:/PROJECTS/understandOtherPackage/order_analyzer`；本轮执行副本与配套 skill/记忆在下述实施工作区维护。
- 实施工作区是 `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache`，jj workspace 为 `free-space-cache`。起始 change `vvnuuksk` / revision `e77e4b99` 是历史基线；最终交付 change `qurnkros` / commit `9ff90182`，parent `a19bfc85` 为独立验收后的 codec 修正。接受记账 change 为 `qpslwnyq`。只读 revision 不证明全部磁盘字节，实际候选以冻结 hash 为准。
- 主工作区尚未集成 sibling 的全部 addon/request/session 功能。下列实现位置与测试路径均以 freespace 工作区为根，不得把它们写成主树现成能力。
- 保留 `D:/PROJECTS/understandOtherPackage/order_analyzer_group_distance` 的独立修改；不以其六文件 path-band 草稿作为本任务基线。
- 自由空间交付包含可读取的结果与输入校验；距离算法、路线接入、666 对距离重算和距离预览验收属于后续距离任务。

## Global constraints / 任务语义

1. 当前实例的分析平面标高为 **世界 Z=1.6 m**，不是楼板顶面以上再加 1.6 m。标高与来源必须记录在对象和请求中。
2. 分析平面可以是场景/IFC 中受管理的对象，提供位置、坐标系和高度；它自身不进入物理占用。不能仅因对象名包含 plane 就排除普通物体。
3. 本次使用选定楼板的唯一合格水平上表面作为下界，分析平面作为上界；使用现有有限高度带投影。不能以全高投影或零厚度截面替代。
4. 楼板的原始物理事实保留。承托面以下部分和只接触下界的部分不阻挡这个查询；不得按 IfcSlab 类别全局删除楼板，也不得删除楼板伸入查询带的实体。
5. 上下界从世界坐标转换到所用平面的局部 Z；现有 UI 的世界 Z=0 假设必须由实际 slab datum 替换。未验证的倾斜、多级或歧义 datum 明确拒绝，不能悄悄压平。
6. 参与范围来自已经确认的 S3，保留 shell、holes、来源和确认身份。物体投影与域有交集即可进入参与/审计，包含边界接触；单元是否 occupied 仍取决于正面积交叠。
7. 缺失或失败几何保持 unknown/unavailable；不能默认为 free。既有 substitute、exact boundary-member 和 provenance 规则必须保留。
8. 精确剖切保留独立接口，本次不扩展其功能。缓存结果与预览都不能反向定义物理事实。
9. Pixi 管理环境；所有新增/修改的项目函数具备英文 docstring，关键几何/adapter 步骤说明原因；不改公开 room-analysis-model 结构。
10. Blender 只使用 `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`，真实场景交互使用已有 Blender MCP。
11. jj 优先；只读历史检查使用 `jj --ignore-working-copy`。同一工作副本只有一个代码写入者，版本变更由主控统一执行；保留无关 dirty work。
12. 当前提交范围是通过验收后的本地提交。远端推送、合并和发布沿用已有单独授权边界。
13. 每项 brief 记录可视化 `required / omitted / reuse` 及正确性依据。仅当数值断言、源身份、测试或日志不足以确认空间关系/用户意图时生成并交给用户查看；能直接验证的步骤省略，依赖未变化的已验证视图可复用。图不能代替占用、缓存等行为断言；交付图片不自动新增审批门槛。

## Confirmed inputs

- IFC：`D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`。
- 原始 IFC SHA-256：`1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`。若另存含平面对象的新 IFC，记录新文件 hash 与原始来源关系，不能要求修改后仍等于旧 hash。
- 承托楼板 GlobalId：`2mbfCNlr9T48ZweNBN3dyn`；历史观测世界 Z 约为 -0.3..0.0 m。实际计算必须重新验证上表面，不能用该近似值代替 datum 读取。
- 确认域：右侧家具大厅和左侧连接通道 S3，历史面积 `207.24092382549588 m²`，37 个家具组均相交。
- 域证据的实际位置为 `D:/PROJECTS/understandOtherPackage/order_analyzer_group_distance/outputs/design/group_distance_ifc/domain_correction_inspection/confirmed_domain_manifest.json` 和同目录的 `confirmed_domain_result.json`。2026-11-04 路径检查确认两者在距离工作区，主工作区与 freespace 工作区没有这两份文件；Task 0 从这个实际位置验证来源、hash 与绑定，再作为只读输入使用。
- 旧 `run_v2_corrected_domain` 为全高投影，0 free；保留为历史反例，不能冒充本次高度带结果。

## Reuse map

以下为已检查到的复用位置，不等于本任务已验收。

| 责任 | 现有实现 | 本次缺口 |
| --- | --- | --- |
| 平面坐标与原生绑定 | `features/scene_contract.py:AnalysisPlane`、`adapters/bonsai_analysis_plane.py` | 满足实际平面物体需求的生命周期及与现有 camera binding 的一致性 |
| 楼板上表面 | `adapters/bonsai_space_authoring.py:resolve_slab_datum` | 接入 freespace 请求下界 |
| 高度带投影与请求 | `features/geometry_views.py:plan_projection`、`features/analysis_requests.py`、`blender_addon/order_analyzer_ui/__init__.py:_make_analysis_request` | 替换硬编码 ground，贯通请求和调用方 |
| 占用资格与域 | `adapters/blender_analysis_capture.py`、`adapters/ifc_bonsai.py`、`features/neutral_scene_views.py`、`features/free_space_field.py` | 分析平面排除和完整的含边界参与审计 |
| 结果持久化与读取 | `adapters/blender_analysis_session.py`、`adapters/blender_analysis_result_wire.py` | 根据当前语义内容 key 查找、命中、跳过生成及失效处理 |

## Master checklist

### Task 0: 核定原工作线与具体实施计划

- [x] 记录 workspace/change、基线、相关实际文件 hash、已有修改归属；确认实施工作区可写，保留无关改动。
- [x] 核对真实调用方、测试、fixture/config 和 exports；更新实施工作区架构图里与本任务直接相关的过期说明。
- [x] 主控在每项实施前形成 task brief：目标、读取/修改文件、精确接口、验收断言、测试命令、依赖、完成标准及可视化判定/理由；记录每条工作线的 jj workspace/base/change、候选文件 hash 和版本写入者。brief 由本文件的目标导出，不能扩展到距离算法。
- [x] 对需求、架构、计划和任务做 Spec Kit 式覆盖/一致性检查；有完整正式 feature artifacts 时使用对应 skill，否则在现有清单中记录等效评估，不虚称已运行正式命令。
- [x] 独立 agent 复核语义、依赖顺序和测试覆盖；完成基线测试并记录真实输出，不把旧 checkpoint 的通过数当本轮结果。

验收产物：工作区/文件基线、逐项任务 brief、当前项的基线测试报告。职责冲突或缺失依赖必须在这里处理。

### Task 1: 通用分析平面物体管理

涉及：`adapters/bonsai_analysis_plane.py`、addon 调用方、capture/IFC source-role 识别；对应 `test/test_bonsai_analysis_plane.py`、`test/test_blender_analysis_capture.py`、`test/test_ifc_bonsai_adapter.py`。

- [x] 先核验现有 native drawing-camera 是否可承载需求，确定可见平面物体与原生绑定的最小组合；`IfcBuildingElementProxy + OM_AnalysisPlane` 不是已经决定的实现。
- [x] 实现创建/查找复用/更新：稳定身份、世界高度、位置与来源一致；重复调用不增加重复对象，冲突或多个候选给出明确诊断。
- [x] 证明平面对象在 live capture 与 IFC 重新读取两条路径均不进入 occupancy，普通物体不受错误的名称匹配影响。
- [x] 检查对象、绑定与存储恢复的一致性；中途失败不能留下被误认为成功的对象或绑定。
- [x] 独立验收通过，完成规格/质量审查，再由主控执行该项本地 jj 提交并附证据。

可视化判定：对象身份、标高、复用次数和占用排除通过数值/行为断言检查，不为创建和复用分别出图。若原生变换与真实可见位置尚有不确定性，在 Task 5 合并生成必要场景视图；已验证同一几何可复用。

验收：创建一次、复用一次、更改高度、重复身份冲突、保存恢复和占用排除均有可检查结果；未确认的真实可见位置单独作为 Task 5 待验事项，不伪称已经通过。

### Task 2: slab datum 到有限高度带的完整接线

涉及：`adapters/bonsai_space_authoring.py`、`features/analysis_requests.py`、addon `_make_analysis_request`；对应 `test/test_bonsai_space_authoring.py`、`test/test_geometry_views.py`、`test/test_analysis_requests.py`、`test/test_blender_analysis_ui.py`。

- [x] 将被验证的选定 slab 上表面接入请求下界；上界读取受管理的 1.6 m 世界标高平面。
- [x] 使用现有 plane-local 变换与三角面裁剪，移除这条查询路径中的世界 Z=0 硬编码。
- [x] 验收非零楼板标高、仅接触下界、部分进入高度带、完全在上界以上、缺失/歧义 datum 和下界不低于上界的处理。
- [x] 确认 exact-section 接口与原有 whole-height 调用保持其原有语义。
- [x] 独立测试与审查通过后提交。

可视化判定：datum、局部变换、垂直交叠和截断规则优先用独立数值预期与测试确认。只有真实楼板/平面映射仍不确定时，在 Task 5 增加侧视图；不为填满图例制造真实场景未出现的实体或状态。

验收：请求中有来源明确的世界/局部高度带，floor contact 不制造整域障碍，伸入查询带的实体仍占用；实际场景映射在 Task 5 核验。

### Task 3: S3 内的物体参与审计与自由空间

涉及：`features/analysis_requests.py`、`features/neutral_scene_views.py`、`features/free_space_field.py` 及既有域 handoff；对应 `test/test_analysis_requests.py`、`test/test_free_space_field.py`。

- [x] 使用 S3 的实际确认绑定与精确投影域，不能使用旧 S4 或家具 bbox 代替。
- [x] 通过 inclusive intersection 记录域内、跨边界、仅边界接触和排除原因；保留原始 source ID 与 substitute 来源。
- [x] 保留正面积 cell/domain/occupancy 交叠规则；边界点/线接触进入审计，但不独自把整格变为 occupied。
- [x] 验收孔洞、跨边界物体、仅接触域边界、失败几何和未知来源；保持原有精确 boundary-member 排除规则。
- [x] 独立测试与审查通过后提交。

Task 3 实现独立验收：314 passed；另有 54 个独立几何案例、3 项审计不变量和 6 项孔洞序列化往返通过。真实 S3 新绑定及有限高度带结果已在 Task 5 独立核验：同一精确 S3、原 11 面墙、零几何差异；首次/重复/恢复均为 14,047 known-empty、7,023 occupied、3,372 outside。

可视化判定：相交、正面积和 unknown 规则由独立测试确认；新真实结果与已确认 S3 的投影对齐若无法仅靠绑定/数值确认，在 Task 5 用同一张俯视叠加图检查。局部图只针对实际疑点生成，不强制每种状态一张图。

验收：参与对象清单可追溯，free/occupied/unknown/outside 的值和理由能够逐格检查；真实源与投影的对齐单独在 Task 5 核验，不能重复要求用户确认未变化的 S3 选区。

### Task 4: 内容缓存的命中、恢复与失效

涉及：`features/analysis_requests.py`、`adapters/blender_analysis_session.py`、`adapters/blender_analysis_result_wire.py`；对应 `test/test_analysis_requests.py`、`test/test_blender_analysis_session.py`、`test/test_blender_analysis_runtime.py`。

- [x] 复用现有完整序列化、精确 ResultRef、恢复逻辑与原子写；不创建平行结果框架。
- [x] 内容身份覆盖 source、domain/confirmation、plane 几何语义、slab datum、query、高度带、grid、schema/algorithm；区分内容身份和单调审计 revision。
- [x] 按当前内容 key 查找合法结果；命中直接读取，证明没有调用投影/自由空间生成函数。
- [x] 验收首次生成、二次命中、进程/文件恢复后命中、关键输入变更失效、内容恢复后的复用，以及损坏/缺失/旧版本缓存的拒绝与恢复行为。
- [x] 确认生成或写入失败不破坏上一份有效结果；unknown/conditional/provenance 完整往返。
- [x] 独立测试与审查通过后提交。

Task 4 独立规格/质量验收 PASS：416 passed；额外独立进程验证了六处生成调用禁用、revision 恢复、完整样本状态/差异与失败保护。真实 Blender/S3 缓存验收仍在 Task 5。

可视化判定：`omitted`。缓存正确性由实际 result key/hash、恢复结果、生成函数调用次数及失效断言确认；不生成缓存命中/失效状态图，也不因重复读取相同几何而重复渲染。

验收：缓存命中有调用记录或计数证据；变更后未命中是正确重算，不能靠图片或显示状态文字证明。证据记录关联实际结果文件与测试日志。

### Task 5: Blender MCP 真实场景验收

先决条件：Tasks 1–4 已验收；读取项目 `skills/ifc-bim-conversion-workflow/SKILL.md`，并核验实际加载代码与目标 IFC 项目身份。

- [x] 通过 MCP 检查当前 Blender/Bonsai 中的源项目、单位、坐标、S3 和目标 slab；处理与指定输入不一致的实际状态。
- [x] 调用已实现的通用功能创建或复用世界 Z=1.6 m 平面，检查原生映射和自身占用排除；再次调用仍复用同一对象。
- [x] 计算正确 S3 的有限高度带自由空间，保存完整结果、参与审计、counts、身份/参数 manifest，并判断哪些真实空间关系仍需视图验证。
- [x] 独立验收 agent 核对真实源、标高、datum、域确认、样本和输出；选取实际可解释的 free/occupied/boundary 样本，未出现的状态单独记为未观测。
- [x] 按剩余正确性问题生成最少必要视图并交给用户查看：首次真实平面/源域/新自由空间对齐需要核实时，用俯视叠加图；datum/标高映射有疑点时加侧视图；边界有疑点才加局部图。一张图可覆盖多个问题，已有依赖一致的已验证视图可复用。
- [x] 分开记录技术验收、图片交付和用户反馈；仅当用户明确要求批准或尚有必须由用户裁定的空间意图时，保留对应待确认门槛。已确认的 S3 不重复审批，用户未回复不能当作接受；发现实际错误则修复并重新验证受影响结果。
- [x] 二次执行证明缓存命中并跳过生成；改变一个实际输入证明失效。所有临时变更都记录并恢复；保存副本与重新打开验证不得覆盖用户未保存工作。
- [x] 修正真实 24,442-cell 验收暴露的共享来源记录重复遍历：独立规模检查覆盖首次序列化、缓存重绑与文档验证，保留完整样本和所有拒绝规则；独立审查后集成，再更新原生加载 hash 与实际验收。
- [x] 记录原始 IFC 和带平面对象的新保存文件的身份关系、恢复验证，以及按上述判定生成的必要视图或复用引用；通过后提交任务自有代码/文档与验收清单。

Task 5 独立规格/质量验收 PASS：四次真实运行按 miss/hit/miss/hit 完成，恢复后全部 24,442 个格子的值/状态与首次一致；独立进程六处生成禁用仍命中，必要实际对齐图已交付。最终接受提交 `9ff90182`，详细输入/ref/hash/限制见证据账本。

验收：实际场景的正确查询与缓存行为成立；必要视图已交付并与来源/数值一致，任何影响正确性的用户意图分歧已解决。图片交付不自动阻塞其余独立开发，也不替代实际测试；用户视觉接受单独如实记录。

### Task 6: 下游读取契约与最终回归

涉及：现有 result wire / session reader 和对应 headless consumer tests；以现成接口为先，不修改距离 kernel。

- [x] 提供可重复调用的读取入口或现有调用示例，按当前输入检查身份/新鲜度并读取 exact result/sample；调用方不依赖私有字段或预览 mesh。
- [x] 独立 agent 验收缓存恢复、域/plane/query 不匹配拒绝、旧结果不能冒充 current，以及 unknown/conditional 状态往返。
- [x] 运行受影响回归，进行一次全范围独立审查，核对 master checklist 与真实产物一致。
- [x] 主控确认最终文件 hash 与测试/审查所验代码一致，完成最终本地 jj 提交；保存提交 ID、测试记录、结果路径和下游读取说明。
- [x] 更新实施工作区架构与状态，列出真实场景未观测分支。距离模块得到输入后另行继续，不能据此勾选距离任务的路线/用户视觉验收项。

Task 6 独立实际 reader 验收与全范围规格/质量审查 PASS、无产品缺口。复用最后受影响回归 866 passed / 1 existing skip；34 个源码/测试/配置文件 hash 稳定。读取指南、实际 current/historical 示例、7 类拒绝及未观测分支均已记录，最终接受提交 `9ff90182`。

验收：一个独立 headless consumer 能验证并读出结果；交付包无需依赖本聊天的记忆。

## Autonomous execution loop

每项按以下顺序连续推进，不逐项等待用户回复：

1. **Controller plans:** 读取当前 checklist 与 ledger，核对实际调用方，写当前 task brief。新增非平凡行为先给独立可判断的测试断言；复用已有断言时不机械重复造测试。
2. **Implementer develops:** 新的实现 agent 只拿当前 brief、必要接口和项目约束，进行最小修改与自测。不得提交、改变版本指向或修改无关文件。
3. **Freeze candidate:** 记录允许修改文件的实际字节 hash 与差异包；暂停代码写入。测试和审查针对这个确定候选，而非不稳定的共享目录。
4. **Independent verifier tests:** 另一 agent 真实运行当前项指定的验收/回归，记录 cwd、环境、命令、退出码、通过/失败数、完整日志路径和候选 hash。不能仅复述实现者报告。几何边界值由需求/独立计算确定，不能用同一函数生成期望值。
5. **Reviewer reviews:** 独立 reviewer 读取需求、候选差异和验收报告，分别给出规格符合性与代码质量结论；验证边界语义、调用方贯通和实际证据。
6. **Fix and verify:** 有失败或实质缺口，交回实现者修复；受影响检查和审查重新执行。代码变化使旧候选证据失效。不能为了完成而降低语义或把未解决的重要问题算作通过。
7. **Controller commits:** 验收和两项 review verdict 均通过、候选字节未变化后，单一版本写入者使用 jj 对任务自有改动做本地提交，记录 ID，再勾选清单并进入下一项。
8. **Final review / converge:** 按实际代码和产物逐条复查需求，追加有来源的剩余工作并完成，不能删除要求以宣称收敛。有完整 Spec Kit feature 时按其前提使用 converge，否则在本清单记录等效缺口评估。完成全范围 review；真实 IFC 验收与下游 reader 测试不能由纯单元测试代替。

实现、verifier、reviewer 的角色分离；每项可复用 verifier 做规格/质量审查以减少上下文开销，但其不能同时是该候选的实现者。读取互相独立的审查可以并行，任何共享文件写入保持串行。

## Visualization delivery protocol

每项先明确正确性问题，再判断直接证据是否足够；按 [工作流 skill](../../../skills/verified-agent-workflow/SKILL.md) 记录 `visual: required / omitted / reuse` 与理由。空间计算本身不意味着必须出图。

| 待确认问题 | 证据选择 |
| --- | --- |
| 原生对象实际位置、源到投影的对齐或用户想要的区域无法由现有检查充分确认 | `required`：为该疑点生成并展示场景/俯视/侧视或局部图 |
| 缓存命中、哈希、调用次数、序列化、freshness 拒绝可直接断言 | `omitted`：测试和日志，不生成图 |
| 几何/坐标系/domain/query/result 相关依赖未变，且原视图已验证 | `reuse`：仅在该空间问题仍相关时引用原证据，不重复渲染 |

将 Task 1–3 的真实空间问题尽量合并到 Task 5 的必要视图；不逐项等待图片审批。视图能证明什么就标注什么：仅看图不能证明精确 1.6 m、零面积接触不占用或缓存跳过生成，这些仍由数值/行为断言确认。

视图从真实数据生成，标注坐标、单位和关键对象；其证据记录链接源、plane/domain/query、网格/算法版本和结果 hash，不要求把全部元数据塞进图片。独立 verifier 检查图与源/数值一致，主控将必要图片内联展示或打开，并说明待检查的问题。局部放大只为实际疑点生成。

用户明确要求批准或真实意图尚有分歧时才等待对应反馈，其余独立工作继续。技术验收、本地提交和用户接受分别记录；不把用户沉默或 agent 看图当作用户接受。

## Durable evidence and resumption

执行时复用 Superpowers 的每计划 ledger/brief/report 机制；按本计划 basename 隔离，不能读写别的计划的 ledger。已验收的测试/审查摘要与提交 ID 另写入版本管理的 `docs/project/evidence/free-space-prerequisite-2026-11-04.md`，不只留在忽略目录。

每项记录：`Task ID | 状态 | workspace/base/change | baseline/candidate hash | brief | 自测 | 独立验收 | spec verdict | quality verdict | visual 决策/理由 | 用户反馈（若需要） | accepted commit | artifacts | 限制`。

状态只使用 `pending / in_progress / fixing / verified / committed`；master checkbox 在证据通过且本地提交后勾选。新会话从 ledger 与实际 jj 历史核对后续跑，不重复执行已提交项。运行环境或授权边界出现真实阻塞时，留下具体证据，完成其余不依赖该阻塞的工作。

## Initial regression command

以下文件已在 freespace 工作区核实存在。由 Task 0 在该工作区执行；本次清单整理没有运行这些测试。

```powershell
$env:PYTHONNOUSERSITE='1'
$env:PYTHONPATH='D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_cache;D:/PROJECTS/understandOtherPackage/order_analyzer/OCTA_toolbox-master'
pixi run pytest test/test_bonsai_analysis_plane.py test/test_bonsai_space_authoring.py test/test_geometry_views.py test/test_analysis_requests.py test/test_free_space_field.py test/test_blender_analysis_capture.py test/test_blender_analysis_ui.py test/test_blender_analysis_session.py test/test_blender_analysis_runtime.py -q
```

每项 brief 从受影响文件中选取具体测试函数和命令；独立 verifier 重跑有意义的验收集。通过后只有出现新代码、新失败或新风险才扩大测试。IFC EXPRESS 全量验证此前被取消，不能记为已通过。

## Skills and workflow provenance

本地已安装并核对：

- `superpowers:writing-plans`：按目标、文件、接口与验收拆任务。
- `superpowers:subagent-driven-development`：连续逐任务派工、持久 ledger、任务 review、修复回路与最终 review。
- `superpowers:requesting-code-review`：独立规格/质量检查。
- `superpowers:verification-before-completion`：以本轮真实命令和输出支撑验收与提交。

网上对照来源为官方 `obra/superpowers` 仓库及其同名 `skills/*/SKILL.md`。本地安装版本与网上主分支内容可能不同，执行以本地实际文件、用户要求和项目规则为准。

Spec Kit 的本地 analyze/converge skills 用于一致性与实际缺口收敛；遵守其输入前提和只读/追加职责。复用项目 `verified-agent-workflow` skill 统一适配：SDD 示例中的实现者先 commit 改为独立验收后由主控提交；每条工作线/任务遵守 jj-first；不能套用通用 finishing 流程自动合并、推送或删除仍需保留的工作区/验收证据。无需安装新依赖、创建自动化服务或引入工作流框架。
