# Post-contract IFC and automatic-space exploration handoff

本 prompt 在 Checkpoint A 收口获批准后，交给新 session 执行。不是 production implementation 授权。

## 原话与目标

用户原话（完整保留）：

> 我先完成收口设计，然后让另一个session边做边探索如何？例如，我设计中，space是自动算出来的，隔出来的，不是定义的。如果可以，你给prompt

本次目标：在真实 IFC 上核验已经冻结的基础描述，同时用 design-only 实验探索自动形成的空区；交回可见结果和可裁决设计，不完成最终 selector。

## 开始前

项目：`D:/PROJECTS/understandOtherPackage/order_analyzer`。

先读 `AGENTS.md`、`docs/indoor_layout_evaluation_matrix_architecture_memory.md`，然后：

- `docs/superpowers/plans/2026-09-29-d6-contract-repair-ifc-shadow-validation.md`（包含最新第 8 节）；
- `docs/project/evidence/d6-h2-contract-repair-checkpoint.md`（若未存在，核查实际收口记录）；
- `docs/project/evidence/d6-inferred-group-candidate-field-owner-decision.md` 与最新 H2 review/report；
- `docs/project/d6-overall-self-description-design-table.md`；
- `docs/project/d6-group-self-description-implementation-design-review.md`；
- `docs/project/evidence/d6-live-blender-input-inspection-2026-09-29.md`。

检查 HEAD、dirty work、审阅记录与本次用户授权。若 A 未批准，报告缺失的裁决并停止，不代替 owner 批准。历史 go、测试通过和本 prompt 的存在不等于 gate 已通过。

实际读取相关技能并报告使用结果：Spec Kit assess/clarify 用于能力和决策缺口（不机械重启已有流程或覆盖 decision）；Superpowers executing-plans/verification 用于冻结步骤；experimental-design、scientific-critical-thinking、scientific-visualization 用于设计实验。必要时补充研究，但只引用已核实来源，原文不可得就明确标记。

## 两类工作不得混淆

**冻结部分：** exact furniture-group 资格、成员观测、context 分离、已有几何公式、provenance 与已批准状态；按批准契约验证。其他对象可以构成 occupancy/边界/参照，但不是 furniture nodes。External affordance 不能由家具类型生成。

**未冻结部分：** 自动分析范围、空区几何/场、空区结构分解与角色推断。允许最小设计脚本和方案比较，不得边写边悄悄冻结为生产默认规则。现有 domain 缺失时的 unavailable 契约继续有效；新推导的 domain candidate 单独记录，不静默注入 production scene。

## 阶段 1：真实几何 smoke check

1. 重读 `adapters/ifc_bonsai.py`、`features/group_self_description.py`、现有投影/preview helpers 和相关测试。列出可复用接口与性能限制；不复制旧 pipeline 作为新基础。
2. 只读核查当前 IFC 路径、schema、strict groups、成员、units、representation、opening/domain capability。现场记录不是验收常量。真实源目前为 `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`。
3. 优先核验三个 authored groups，取样前记录选择规则和 source IDs。比较 Analysis source geometry、world placement、米单位和最终投影，避免重复 transform；Body 仅审计。保存无效、holes、multipart、missing 等限制。
4. 使用现有 standalone 描述，展示真实轮廓、中心、frame/axis 与关系 witness。若现有 adapter 必须全量 tessellation，先记录成本并选最小只读设计途径；不能假装已有 selective API。缺依赖不安装，生产缺陷不绕过。
5. 每步有数值断言与图像审查。输入链路失败就交回可见失败样本，不继续在错误几何上做 space 实验。未通过 sample 不代表整场景通过。

## 阶段 2：自动 space 设计实验

开始编码前写一页实验计划，列出问题、输入、对照、输出与失败条件；这是探索，不是新生产规格。

1. 分开研究四层：有依据的分析范围、occupancy complement/free-space field、空区结构、角色候选。不要要求用户预先绘制空区、标注走廊或建立 IfcSpace。
2. 审计现有 floor/wall/context/free-space/path 计算能复用什么。优先从可靠地面/围护观测研究 domain candidate；缺封闭范围时保留 open-boundary/partial/not_available。家具 hull/bbox 若作为裁剪对照，只能标为人为计算窗口，不是真实 room domain。
3. 提出最多两个适合已有数据的设计方案，再做有限对照；不为凑数实现两套完整引擎。不能把旧 region fallback、人工分组结果或待推断 groups 当作基础空区真值。
4. 家具与 context 共同影响物理占用；context 的通道阻隔需有证据。门几何不是有效 opening relation。若研究几何洞口猜测，单列 hypothesis，不能将未知 permeability 改为 clear。
5. 先比较连续宽度/距离剖面、连通和瓶颈等可计算观测；分解方法、尺度与角色策略保持 candidate。没有固定“1.8 米分组/走廊界限”。数值 tolerance、采样分辨率与相对尺度允许存在，但必须有单位、理由和敏感性对照，不能伪装成无参数模型。
6. 走廊、活动区等最终自动角色能力仍在目标中，不删除或永久 deferred；本次给出已可判断的角色 evidence、剩余问题和下一项能解决它的实验。未形成可靠角色规则时，不强制赋唯一标签；deterministic support 不是 probability。
7. 对同一输入至少比较尺度/分辨率变化，并用小型受控 fixture 检查平移/旋转、变宽间隔、阻隔变化、缺失边界。真实模型用于适用性与输入检查，synthetic 用于可手算性质；都不宣称真实语义准确率。多个局部图不当作独立场景样本。
8. 保持基础空区观测不依赖 inferred membership 的无循环 baseline；空区不是家具组成员。家具组是否由同一空间结构组织起来仍是后续设计，不在此实现 production selector、Bayesian 或 ML。

## 可视化与交付

- 仅用 `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`；不修改或保存用户当前模型。用独立 disposable diagnostic scene 和真实 source geometry，叠加层标为 derived/design-only。
- 提供一张 source 全景、一张三个组几何核验图、一张自动空区方案/剖面对照。PNG 与可打开 blend，必要时补 SVG；缺能力明确显示。实际查看渲染，不以 exit 0 代替图像检查；把图片展示给用户。
- 只允许 `scripts/design/group_level/` 中必要脚本及 fixtures、对应 `docs/project/evidence/` 记录。新脚本每个函数 English-first docstring，关键计算解释原因。
- 大型 JSON、blend、PNG 放 `outputs/design/ifc_space_exploration/`，manifest 保存绝对路径、bytes/hash、重建命令。提交脚本、小型 evidence 和 MD，不自动提交大二进制。
- 新建 `docs/project/evidence/d6-ifc-auto-space-exploration-record.md`，记录用户原话、核实事实、解释、假设、每一步决策、实验结果与 APPROVE/REVISE/DEFER 建议。
- 全程禁改 `features/`、`adapters/`、正式 `test/`、NeutralSceneV2、公共 API、依赖、源 IFC。不得修生产代码来让 probe 通过。
- 源 IFC 前后 hash 一致；核查 JSON、hash、数值重现、图层/source IDs 和 diff scope。只暂存明确路径，禁止 blanket staging/回滚他人修改；分阶段提交，报告未提交内容。
- 运行阶段出现 15 分钟无进展、内存不足或需扩范围时暂停并提出最小方案，不对 37-node graph 穷举，不无限扩大实验。

完成交回：commit/HEAD、实际技能、命令/退出码、测试、图片绝对路径、source-to-output provenance、当前限制、推荐方案及下一道审批项。

STOP FOR REAL IFC / AUTO-SPACE DESIGN REVIEW
