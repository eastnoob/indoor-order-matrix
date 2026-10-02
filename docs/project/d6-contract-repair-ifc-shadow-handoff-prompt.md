# D6 New Session Handoff Prompt

请在 `D:\PROJECTS\understandOtherPackage\order_analyzer` 执行 D6 design-validation 任务，不做 production implementation。

先读 `AGENTS.md`、`docs/indoor_layout_evaluation_matrix_architecture_memory.md`，然后完整阅读：

1. `docs/superpowers/plans/2026-09-29-d6-contract-repair-ifc-shadow-validation.md`
2. `docs/project/d6-overall-self-description-design-table.md`
3. `docs/project/evidence/d6-inferred-group-candidate-field-owner-decision.md`
4. 当前工作区的 `docs/project/evidence/d6-inferred-group-candidate-field-h2-design-review.md`、H2 report、registry/probe、semantics/status/key fixtures。

请先确认实际可发现的全局与项目 skills。使用合适的 `executing-plans`、`verification-before-completion`；可视化阶段读取项目 `scientific-visualization`。Spec Kit assess 用于判断证据/授权边界，不机械重启 intake，不覆盖现有 decision，也不把 historical go 当作当前生产许可。报告实际读了哪些技能、用来解决什么问题，不声称调用了不存在的命令。

**本次只授权 Checkpoint A。** 现有 880-row 修订已有部分未提交/未跟踪文件；先审计并复用，不重复从旧 704-row commit 开始。保留其他 session 的修改，不回滚，不 `git add .`。对计划所列状态、conflict、overlap/maximal/ambiguous/singleton/unassigned 规则做最小收口、断言与重跑，给裁决建议，不冒充 owner 冻结。

不得修改 `features/`、`adapters/`、正式 `test/`、NeutralSceneV2、public API、依赖、源 IFC；不实现生产 selector、Bayesian/ML 或空区角色模型。不选 winner、不调阈值改善 holdout 分数。H2 中的 minimum member gap 只是 diagnostic 简化，必须明确记录。

完成 A 后提交明确属于本任务的设计文件，返回：

- commit、HEAD 与 reviewed working-tree hashes；
- 改了什么/复用了什么；
- 实际命令、退出码、rows/gates/hash/schema 和范围审计；
- relation/candidate 状态矩阵与逐项 APPROVE/REVISE/DEFER 建议；
- 尚存问题和进入 B 的阻断项。

然后停止：`STOP FOR CONTRACT REVIEW`。不得自动执行 B、implementation design 或生产开发。

总控批准继续后，请在同一 session 按同一计划执行 B：用真实 IFC 经现有 adapter/description 只读计算，做全景基础观测和最多 8 节点的小子图 candidate 对照，提供真实 source mesh 的 Blender PNG/SVG/blend。当前穷举算法禁止直接跑 37 节点全图。不以 bbox、旧预期边或 synthetic 图替代真实模型输出；缺失空间/Z/barrier channel 如实显示。只允许指定 portable Blender，不改用户当前打开场景。

B 完成后交回真实图片的绝对路径、源 IFC 前后 hash、数据来源/单位/placement 抽查、候选 scope、能力限制、验证和 commit，并停止：`STOP FOR REAL IFC DESIGN REVIEW`。用户不承担标注实验；视觉意见只能帮助发现模型或目标偏差，不能成为准确率或心理效度声明。
