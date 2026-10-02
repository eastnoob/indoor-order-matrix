# D6 Space-Field Design Handoff Prompt

你是本项目的外部设计与实验执行 session。当前只做 **空间场（space field）第一切片的设计、研究和可执行探针**，不要进入 production implementation。

## 目标与边界

项目目标是用可计算指标描述家具布局，为后续实验提供自变量；不声称心理感知效度，也不要求真人实验。

已确定：

- authored furniture group 是家具分析的最小节点；单个家具不是自动节点；
- 家具组的几何、趋势、成员关系和组间物理关系分别保留；
- 空间/空区域是独立的派生对象，可表达 connector、separator、openness、bottleneck 等空间角色证据；它不是家具组成员；
- 空间场必须从显式 `AnalysisDomain` 和有效几何派生；缺少 domain 时应为 `not_available`；
- 2D canonical geometry 是第一切片，3D、Z、clearance 和 opening capability 必须单独报告；
- 不允许用固定语义阈值直接规定“宽于 X 就是走廊”；宽窄只能作为连续证据或待验证假设；
- 不允许把 probe、Bayesian posterior、确定性 strength 或可视化结果写成心理效度、真实准确率或 production policy。

## 先读并核对

先读：`AGENTS.md`、`docs/indoor_layout_evaluation_matrix_architecture_memory.md`、`docs/project/d6-overall-self-description-design-table.md`、`docs/project/evidence/d6-b1-r2-model-selection-gate.md`、`docs/project/evidence/d6-b1-r1-design-repair-record.md`、`docs/project/evidence/d6-ifc-trend-checkpoint-1b-report.md`。

核对现状（只读）：`features/scene_inference.py`、`features/group_self_description.py`、`features/analysis_substitute_discovery.py`、`features/canonical_layout_geometry.py`、`adapters/ifc_bonsai.py`、`adapters/svg_scene.py`，以及仓库中已有的 clearance、free-space、path、grid、domain 工具。不要凭文件名臆造接口。

明确区分：用户原话、项目已核实事实、外部证据、你的解释、待验证假设。不要悄悄改写历史设计记录。若 B1/R1 证据有缺陷，标为限制；不要声称 Bayesian 已验证、已校准或当前主线必需。

## 必须实际检查并记录的技能

先发现并读取全局、插件和项目 `.agents/skills`（若存在）的实际 `SKILL.md`。至少评估并按需使用：

- `speckit-assess-intake/define/research/shape/decide`：只用于这个有界的空间场设计问题；若前置目录或输入契约不满足，报告原因，不伪造已执行；
- `experimental-design`：固定 fixture、变量、不变量、独立重复单位、oracle、holdout 与 acceptance criteria；
- `scientific-critical-thinking`：检查证据边界、不可推出结论和替代解释；
- `scientific-visualization`：检查采样、几何、边界、角色证据和 provenance 的可视表达；
- `verification-before-completion`：重跑探针、hash、范围审计、diff 检查并记录结果；
- 必要时使用 `literature-review` 或同等学术检索技能，但不得编造文献或接口。

在最终记录中列出：实际调用的技能、用于解决的问题、产出；未发现、不可运行或不适合的技能及理由。

## 设计任务

1. 比较最小可行的空间表示：精确多边形/图几何、均匀多分辨率栅格，以及必要时的自适应表示。不要预先认定栅格是最终模型。
2. 定义 `AnalysisDomain`、分析平面、单位、占用/障碍/可见性几何来源、holes/disconnected/invalid/missing 状态。
3. 设计第一组 fixture：宽空间与窄瓶颈、均匀间距中的 gap jump、闭墙与开口、斜边界/曲边界、holes/disconnected domain、多尺寸障碍、缺失或非法 domain、不同 grid origin/rotation。
4. 为每个 fixture 建立独立的几何或拓扑 oracle；oracle 不能只是复制被测算法的输出。
5. 比较多分辨率、原点偏移、旋转、单位缩放、几何公差、拓扑稳定性、面积/距离误差、内存和运行时间。最细分辨率不自动是真理；若不收敛或拓扑不稳定，必须输出明确状态和限制。
6. 设计连续空间证据：free-space distance/clearance、connectivity、bottleneck profile、boundary openness、occupancy、barrier、local alignment。空间 role 先作为证据或候选，不直接写死为 corridor/activity-area 标签。
7. 保持空间场与家具组 relation field 分离：空间观察可以供后续 candidate inference 使用，但不能反写 authored membership、占用事实、domain 或 blocker。
8. 2D 为主；如能使用真实 IFC，只做只读小样本输入审计和可视化，不虚构 `IfcSpace`、opening 或 Z 能力。SVG/Blender 可用于展示采样、几何和场证据，但源 IFC/用户 blend 不得修改。

## 允许修改与禁止事项

允许新增或修改：`docs/project/` 设计记录、`docs/project/evidence/`、`scripts/design/space_field/` 探针与 fixtures、`outputs/design/` 可视化和 manifest。

禁止：修改 `features/`、`adapters/`、`NeutralSceneV2`、公共 API、正式测试、依赖、源 IFC 或用户 Blender 文件；禁止实现 production selector、自动 space、Bayesian/ML 生产模型；禁止选择最终 resolution、semantic threshold、winner recipe 或心理标签规则。

## 交付物与停止点

提交：设计表/决策记录、探针计划和脚本、fixtures/oracles、结果 JSON、PNG/SVG/Blender 可视化（可行时）、artifact manifest、资源/限制报告、范围审计和 Git commit。只提交明确路径，保留既有 dirty/untracked 内容，不使用破坏性 Git 命令。

结束时必须写明：已批准、仍待 owner 决定、失败或不可用的输入，以及哪些结果只是 diagnostic。完成后停止并输出：

**STOP FOR SPACE FIELD DESIGN REVIEW**

不要自行进入 implementation design 或生产实现。下一阶段将由 owner 审阅本批证据后，另开“implementation design → tests → integration/Blender acceptance”任务。
