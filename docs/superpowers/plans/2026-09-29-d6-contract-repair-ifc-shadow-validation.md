# D6 Contract Repair and IFC Shadow Validation Execution Plan

> For agentic workers: use `superpowers:executing-plans` task-by-task. This is a design-validation execution plan, not a production implementation plan. Complete Checkpoint A and stop; Checkpoint B requires an explicit continuation after review.

**Goal:** 收口现有 candidate-field 诊断契约，并在真实 IFC 几何上给 owner 看见结果、限制和规则差异。

**Architecture:** 重用现有 IFC adapter 与 standalone group description；候选比较仍在 design scripts 中。原始 IFC、authored membership、context 与 derived overlays 分离；Blender 只显示已计算的输出，不决定分组。

**Tech Stack:** 项目现有 Pixi/Python、IfcOpenShell、Shapely；指定 portable Blender。禁止为本阶段安装依赖。

**Spec:** `docs/project/d6-overall-self-description-design-table.md`；`docs/project/evidence/d6-inferred-group-candidate-field-owner-decision.md`；当前 H2 design review。

日期：2026-09-29。本计划不替代已有 owner decision，不授予 implementation design 或生产实现权限。

## 1. 来源与当前事实

- 用户要求：设计与落实分开；逐步检查；能够看到真实 IFC/Blender 结果；家具组是最小节点；context 不成为节点；空区是独立的描述对象。
- 当前代码事实：`describe_group_relations(scene)` 已接受 NeutralSceneV2，计算组的平面几何、frame/axis 和 member-pair observations；`candidate_views=None`；空间测量、3D/Z、barrier 聚合未实现。
- 当前实验事实：工作区 H2 已拆出五个 aggregation id，并有 880 scoring rows；此前已提交版本为 704 rows。880 版有未提交及未跟踪文件，不可当成已经批准的版本。
- 当前裁决事实：并列 diagnostics 与三个 scale 方向已批准；状态和候选规则尚需复核；production implementation design 为 DEFER。
- 外部证据：本轮不新增学术推断，不把 synthetic computational truth、F1 或视觉认可当成真实分组准确率、posterior 或心理效度。
- 已核实资源：真实 IFC 文件约 409 MB；旧 E10 报告记载 37 个 furniture groups、95 furniture、11 walls、6 doors、0 openings/voids/fills。这些计数是待本次重核的历史记录，不是无条件验收常量。

## 2. 全局边界

- 禁止修改 `features/`、`adapters/`、正式 `test/`、NeutralSceneV2、public API、依赖、源 IFC；不实现生产 selector、Bayesian/ML、空区角色模型。
- IFC group 资格严格是 `IfcGroup.ObjectType == "furniture_group"`；普通 group、名称、图层、邻近和旧 region 不创建节点。
- affordance 只能来自外部输入；door geometry 不等同有效 opening relation。
- 不重写原始需求或既有裁决；新增记录必须区分事实、观察、解释、建议和 owner 待决定项。
- 所有新函数有 English-first docstring；投影、归一化、采样和证据桥接解释原因。
- Blender 只使用 `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe`，在独立 disposable scene 中运行，不改当前打开模型。
- 禁止以 bbox/矩形重画代替真实投影而不标明；禁止把未测量 channel 填为 zero/clear/computed。
- 新的设计校验放在 design script 自检查中，不修改正式测试来迁就 probe。

## 3. 工作区与 Git

- 开始记录 HEAD、`git status --short`、相关工作区 diff，以及使用文件的 SHA-256。未提交内容是输入状态，不得回滚或默认认领。
- 已有未跟踪 review/fixtures 必须实际读取；记录 reviewed working-tree hashes，而不只引用旧 commit。
- 不自动创建 worktree：当前修订不全在提交中，新 worktree 会遗漏它们。建议新 session 使用同一项目目录，期间其他 session 不写这些文件。
- 提交只使用明确路径；禁止 `git add .`、`git add -A`。执行者可以在核查后提交明确授权的设计修订；无关未跟踪文件保持原样。
- 每个 checkpoint 独立提交；报告 commit、文件列表、运行命令、退出码及仍未提交的文件。新二进制不自动纳入 Git；在 artifact manifest 中记录路径、bytes、hash、重建命令，声明本地保存并非长期归档。

## 4. Checkpoint A：验证并收口现有设计修订

**输入：** 当前 registry/probe/H2 runner、semantics/status/key fixtures、H2 evidence、owner decision。

**允许修改：** 现有 `scripts/design/group_level/` 的 candidate-field probe/runner/相关 fixture；对应 H2 evidence/diagnostic SVG。新增 `docs/project/evidence/d6-h2-contract-repair-checkpoint.md`。

**交付：** 一个可审阅的 diagnostic contract matrix、最小回归断言、重跑结果和有限裁决建议；不是 production contract。

- [ ] A1. 先核对当前已做修订，不重复重做已通过的 880 版。列出哪些 owner 要求已满足，哪些还没有。
- [ ] A2. 每个 recipe 明确输入必需 channel、可选 channel、selected 与 eligible 的区别。保留 `selected_relation_connected` 和 `all_internal_pairs` 两个不同 id；`min_gap` 仅作 witness。
- [ ] A3. 给出 relation/candidate 两层状态矩阵：missing、invalid、partial、not_available、conflict；说明 required/optional channel 的传播；unknown 不等于 zero；soft disagreement 不等于 hard veto。
- [ ] A4. 明确每种 recipe 的 maximal 范围、overlap、ambiguous、singleton/unassigned；shared authored member 是 dependency diagnostic，不是自动合组证据。
- [ ] A5. 检查现有 `_numeric_gap` 使用最小 member gap 的简化是否被清楚记录；不升级为正式 group gap。检查 rank ties 是否被 ID 排序影响；若有，明确标注限制并用最小反例展示，不宣称重命名不变性。
- [ ] A6. 现有 assertions 缺什么就补什么：selected-but-ineligible 的 missing/invalid/partial；多个 maximal sets；singleton 无内部 pair；canonical/reverse conflict。先运行反例确认缺陷，再最小修订并重跑。
- [ ] A7. 运行 H2 `probe -> score -> visual -> report -> record -> manifest -> verify`；若输入/规则改变，明确为探索性重跑，不伪装预注册结果；不得调参选 winner。
- [ ] A8. 保留原 owner decision，写 checkpoint report 和逐项 APPROVE/REVISE/DEFER 建议，提交本范围文件，停止。

验证命令：

```powershell
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py probe
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py score
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py visual
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py report
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py record
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py manifest
pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py verify
pixi run pytest test/test_group_self_description.py test/test_canonical_layout_contract.py test/test_canonical_layout_geometry.py -q
git diff --check
git diff --cached --check
git diff --cached --name-only
```

**A 验收：** registry/实现/断言/报告一致；最小反例与现有 H2 检查通过；禁止范围无修改；未选 winner。计数以实际 runner 为准，当前预期是 880 rows、16 holdout hard gates。

**A 停止标记：** `STOP FOR CONTRACT REVIEW`。由总控审阅后明确授权 B；通过 A 不等于批准生产实现。

## 5. Checkpoint B：真实 IFC 只读影子验证与可视化

**前置条件：** A 的证据一致性通过总控审阅；无需先选唯一分组规则，但未冻结内容必须继续标注 diagnostic。

**输入：** `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`，及 A 审阅的 registry/probe。

**只读接口：** `load_ifc_neutral_scene(source, *, ifc_module=None, analysis_domain_source_id=None) -> NeutralSceneV2`；`describe_group_relations(scene) -> dict`；`build_preview_manifest(scene, matrix) -> dict`、`write_preview_script(scene, matrix, target) -> Path`。

**最少新增文件：**

- `scripts/design/group_level/run_ifc_candidate_field_shadow.py`：导入、审计、证据桥接、局部诊断、manifest 与自检查。
- `scripts/design/group_level/render_ifc_candidate_field_shadow.py`：只读 JSON 输出并调用/复用 source preview，增加候选覆盖层、camera 和渲染。
- `docs/project/evidence/d6-ifc-candidate-field-shadow-report.md`。
- `docs/project/evidence/d6-ifc-candidate-field-shadow-artifact-manifest.json`。
- 大型中间 JSON、PNG、SVG、blend 与日志放入 `outputs/design/ifc_candidate_field_shadow/`；禁止自动提交大文件。

- [ ] B1. 记录文件 hash、bytes、Pixi/Blender 版本及可用内存；检查依赖，缺失则报告，不安装。不重复导出源 IFC。
- [ ] B2. 用现有 IFC adapter 实际解析，保留 schema/unit/placement/geometry/membership/context/provenance 审计。重核历史计数，差异有解释才继续；导入异常不能改源文件绕过。
- [ ] B3. 直接把 NeutralSceneV2 交给 `describe_group_relations`。不经 synthetic `_scene` 重建，不复制 shared member，不丢 multipart/holes 或 unresolved refs，不根据 group 名称分组。
- [ ] B4. 保存完整节点与基础关系状态、world/analysis 坐标及投影链。抽查至少 3 个有 usable geometry 的组，比较 IFC world vertices、平面投影和图中位置，防止单位/placement 被重复应用。抽查值与误差记录在报告。
- [ ] B5. 证据桥接仅为 design-only 数据转换，复用已检查的 relation/scale/aggregation helpers。逐字段声明来源；不把旧 region/affordance/path 的结果偷换成新空间场。profile/domain/barrier/Z 没有可靠值时为 not_available；不得给每对写入默认值来凑齐三个 recipe。
- [ ] B6. full-scene 保留 37 组的实际计数对应基础观测和可安全计算的 scale/connected diagnostic。先检查运行成本；组数发生变化时仍按实际数量报告。
- [ ] B7. 穷举 aggregation 仅比较预先声明的小子图，最多 8 节点/子图：从有 usable center 的组按 source id 排序选前 3 个不同 anchor，各取按中心距离排序的最近 8 个 eligible group ids；重复子图只保留一次。这是计算/展示采样，不是 inferred membership。保存 anchor、ids、selection basis、缺失排除和边界截断。
- [ ] B8. 默认使用 full-scene scale 结果再截取 induced graph；不悄悄重算成局部尺度。若另外比较局部尺度，必须另一个 run id 和明确 scope。穷举只运行小子图；不能声称这是全场景 maximal candidate 或真实 generalization 验收。
- [ ] B9. 对同一输入保留并列诊断，不挑一个最好看的 winner。报告 chaining、overlap、歧义、孤立和缺失情况；没有空间字段的 scale 显式 not_run/not_available。
- [ ] B10. Blender 使用真实 tessellated source meshes；authored nodes、context、group direction、selected relations、candidate views 分集合/图层，源 id 与 JSON 一一对应。不得使用旧 renderer 硬编码的预期角度或边作为真实输出。
- [ ] B11. 至少交付 source 全景、一个局部候选对照、缺失/能力状态面板；PNG、SVG 和可打开 blend。头部标明 recipe/参数/scope/单位，coherence 和支持度不命名为 probability。无空区模型时明确显示未计算，不拿白色背景冒充空区角色结果。
- [ ] B12. 渲染后实际查看 PNG：非空、模型完整、overlay 不遮蔽关键几何、legend 与来源准确。自动检查 mesh/overlay/source-id counts 和 image pixels；退出码 0 不单独作为视觉验收。保留 Blender stdout/stderr/exit code。
- [ ] B13. 保存 hash/bytes/重建命令/局部集合/provenance/限制；校验源 IFC hash 前后相同、no production diff、JSON parse、manifest hashes、重复运行的数值与集合稳定性。blend/渲染可非字节相同，不虚称二进制重现。
- [ ] B14. 提交小型脚本/报告/manifest；返回图片绝对路径，让总控和用户可以看到，不要求用户做标注实验。停止，给 implementation design 的 APPROVE/REVISE/DEFER 建议，不自行开启实现。

给上述两个 design-only 脚本采用明确 CLI，创建时在报告中验证：

```powershell
pixi run python scripts/design/group_level/run_ifc_candidate_field_shadow.py --ifc outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/ifc_candidate_field_shadow
& 'D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe' --background --python scripts/design/group_level/render_ifc_candidate_field_shadow.py -- --input-dir outputs/design/ifc_candidate_field_shadow --output-dir outputs/design/ifc_candidate_field_shadow
```

这两个 CLI 是本计划要求新增并校验的 design-script 接口，不声称它们现在已经存在。

**B 验收：** 真实 source-to-output 可追溯；单位/placement 抽查通过；明确展示实际几何及局部并列候选；缺失能力如实；源文件不变；无生产路径修改。

**B 停止标记：** `STOP FOR REAL IFC DESIGN REVIEW`。

## 6. 资源、复核与重规划

- 新 session 串行执行；总控负责 A/B 独立证据复核。用户只需看到图并指出明显模型错位或目标偏差，不承担测试、分组标注或实验执行。
- 不承诺分天完成：A 是一次有限收口；B 是一次有限真实模型诊断。按 checkpoint 而不是默认 Spec Kit 步骤计进度。
- 首次 IFC 导入/投影运行记录耗时和峰值内存；单个运行 15 分钟无进展或内存不足时报告 blocking stage 和日志，不反复完整重跑。允许诊断日志中的一次明确重试；之后暂停并提出缩小几何处理范围的方案。
- 不对 37 节点运行现有穷举 maximal-clique/max-span；需要全图候选时另做性能/算法设计，不在本任务安装新引擎。
- 实际 geometry 或状态不被 first slice 支持时，输出 invalid/not_available 并展示；禁止修复 production code 掩盖限制。若没有足够 usable 节点，交回最小失败样本和可见源模型，不编造候选。
- 使用 `verification-before-completion` 报告实际命令和结果；使用 scientific visualization 审查显示真实性；若需要补充研究，另列研究问题，不让学术检索无限延长本 checkpoint。
- 已读取 Spec Kit assess-decide 和现有 assessment decision；本轮不覆写它、不重新启动 intake、不把历史 go 当作生产许可。必要的新正式阶段裁决由总控在证据收齐后完成。

## 7. 总控自检查

- [x] 承接当前未提交修订，避免把旧 704 和当前 880 混为一谈。
- [x] A/B 分别有范围、检查、交付、Git 策略和停止点。
- [x] 保留新描述与旧 scene_inference 边界；未批准生产 selector。
- [x] 真实 IFC/Blender 是本轮交付，不再只返回 synthetic scoring。
- [x] 409 MB 输入与指数候选枚举有资源上限；局部证据不冒充全场景结果。
- [x] 完整/partial/invalid、shared member、multipart、空区缺失及门/opening 不被桥接吞掉。
- [x] 本文件仅规划；尚未执行 A/B，也未冻结 owner 未决项。

## 8. Owner clarification: automatic space derivation

2026-09-29 用户原话：

> 我先完成收口设计，然后让另一个session边做边探索如何？例如，我设计中，space是自动算出来的，隔出来的，不是定义的。如果可以，你给prompt

解释与边界：space geometry/field 及其角色是系统推导的对象，不要求用户先定义 `IfcSpace`、画走廊或提供角色标签。必须区分分析范围、剩余自由空间、空区结构和空间角色；当前 adapter 只接受显式 domain 是当前实现限制，不是最终需求。几何范围可以研究自动提取，但 source canvas、家具 hull/bbox 不得静默升级为真实 domain；证据不足要保留开放边界或 unavailable。

不改变 A 的收口职责或停止点。A 获批准后，真实模型探索先做三个 source-linked furniture groups 的单位/placement/轮廓 smoke check，再决定是否扩大到 B 的全景或局部候选对照；无需立刻运行全模型 geometry extraction。具体最小提取途径须先审计现有 adapter/helper，禁止把新采样接口描述成现有 API。

自动 space 属于独立、design-only 的后续探索，不由 A 通过自动授权。交接使用 `docs/project/d6-post-contract-ifc-space-exploration-prompt.md`：记录实验设计后做少量可复现 probe，自检查、可视化并停在设计复核；不修改 production domain contract，不实现角色 selector。该 prompt 的阶段 1/2 执行须由用户在 A 收口批准后派发。
