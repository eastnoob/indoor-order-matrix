# D6 Three-Group Real IFC Smoke Check: Execution Prompt

将下方 prompt 交给独立执行会话。用户派发此 prompt 时，仅授权本任务；本文件存在本身不是执行授权。总控本轮只写计划，没有运行 IFC/Blender。

```text
请在 D:\PROJECTS\understandOtherPackage\order_analyzer 执行 D6 三个真实 IFC 家具组的只读输入 smoke check 与 Blender 可视化。

先读 AGENTS.md、docs/indoor_layout_evaluation_matrix_architecture_memory.md，然后完整阅读：
1. docs/project/evidence/d6-h2-contract-repair-controller-review.md
2. docs/superpowers/plans/2026-09-30-d6-real-ifc-three-group-smoke.md
3. docs/project/evidence/d6-live-blender-input-inspection-2026-09-29.md
4. docs/superpowers/plans/2026-09-29-d6-contract-repair-ifc-shadow-validation.md 第 8 节
5. 计划中列出的 IFC adapter、standalone descriptor、scene contract 和 preview helpers。

当前有效裁决是 Checkpoint A APPROVE，基线 9a38ea89336c521ff6e076982e986ec27f4f9a53。
旧 report/owner decision 中的 REVISE 是历史，不重开 A 修复循环。
总控 review 当前可能未跟踪：记录实际文件/hash；若未能找到，报告缺少裁决记录，不伪造批准。
这个任务不授权完整 B、自动 space、候选比较、production selector 或接口设计。

按新计划的三个任务顺序执行，逐步自检查，不为每个内部小步骤另造审批门；数值失败、资源/API 阻断或需要扩范围时停止交回。
实际读取并使用 executing-plans、verification-before-completion，以及适用的项目 scientific-visualization / uncertainty-and-units；报告实际作用和结果，不把读取技能说成运行了不存在的命令。
Spec Kit assess 已有项目决定，不覆盖它，不机械重启 intake，不把旧 go 当作生产许可。
不自行创建/派发其他 session 或 subagent。

源 IFC：outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc。
先冻结 metadata inventory，再选 source identity 排序的前三个非空且 exact ObjectType == furniture_group 的 IfcGroup。失败也保留，不换成好看的样本。
保留所有 authored members、shared/duplicate/unresolved provenance；成员不是新节点。普通 group、名称、图层和邻近不造节点。

现有 public IFC loader 没有三组选取接口，并遍历全部 IfcProduct。
只重用实际存在的私有 extraction/typed-scene helpers 构建设计样本；不得假装这是 public adapter 全链路验收，不 monkeypatch、不修源 IFC、不全量 tessellate。
Analysis 是计算来源；Body 是源模型视觉审计。缺 Analysis 不能用 Body 静默补上。
明确 mm/源单位→SI world metre→analysis plane 链，检查 placement/unit 没有重复应用；每组至少一个成员作独立 local/world 检查，不用同一个 helper 重跑冒充交叉验证。
直接调用 describe_group_relations(NeutralSceneV2 sample)，不经 synthetic/legacy 重建。
candidate_views=null、candidate_view_status=deferred；组级 aggregation/gap/contact/overlap/formal edge 保持现有 null/deferred。不把 design probe 的 false 当 descriptor 的 null。
空间、Z、3D、barrier 未测量仍 unavailable。Context 本轮只 inventory，不计算场景占用；三组图不是完整房间。
自动 space 仍是最终目标，但本次不计算、不要求用户画 corridor/IfcSpace，也不以 sample bbox/hull 冒充 domain。

只允许新建计划列出的两个 scripts/design/group_level/ 脚本、一个 smoke report 和一个 artifact manifest。
禁止修改 features/、adapters/、test/、NeutralSceneV2、public API、依赖、现有 H2 evidence、源 IFC 或用户当前 Blender 模型；禁止安装依赖。
使用 Pixi。Blender 只用 D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe，独立 background/factory-startup，序列化文件跨运行时传递。

必须交付真实 Body sample 图，以及真实 Analysis 轮廓/center/frame/axis 核验图和可打开的 disposable blend。
复用源 mesh preview；新方向 overlay 不套旧 region/trend 字段、不伪造 strength、probability、group envelope。
检查 source IDs、mesh topology/坐标、camera/labels 和 PNG 像素，再实际看图；exit 0 不是可视验收。
源 IFC 前后 SHA-256 相同；保存单位/placement 误差、missing/invalid/partial、实际能力限制和 local-only artifacts 的 hash/bytes/重建命令。

Git：开始记录 HEAD/status，保留全部既有未跟踪文件。只 stage 计划明确允许的新四个交付文件，审计 staged diff 后提交；不 blanket-stage、不回滚、不 push。大 JSON/PNG/blend/log 放 outputs/design/ifc_three_group_smoke/，不自动纳入 Git。

最终返回 commit/HEAD、修改文件、实际 skills、命令/退出码、自检查与 focused pytest、源 hash、三组 IDs/来源映射、单位/placement 核验、局限及 APPROVE/REVISE/DEFER 建议。
嵌入两张 PNG 的绝对路径，让用户看到，而不是只给 manifest。用户不承担执行实验或分组标注。
然后停止：STOP FOR THREE-GROUP IFC INPUT REVIEW。
不自行进入完整 B、自动 space、production integration、candidate selector 或 Bayesian/ML。
```
