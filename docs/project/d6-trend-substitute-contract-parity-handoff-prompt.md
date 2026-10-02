# Handoff Prompt: D6 Trend Substitute Contract + Legacy Parity

你是本项目的执行 session。请在
`D:\PROJECTS\understandOtherPackage\order_analyzer`
中执行以下**设计验证 checkpoint**，完成后必须停止，不得自行进入 production implementation 或选择 trend winner。

## 先读和遵守

先阅读：

- `AGENTS.md`
- `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- `docs/project/d6-group-level-self-description-design.md`
- `docs/project/d6-overall-self-description-design-table.md`
- `docs/project/d6-group-self-description-programming-prompt.md`
- `docs/project/evidence/d6-ifc-three-group-smoke-report.md`
- `docs/project/evidence/d6-trend-direction-design-probe.md`
- `docs/superpowers/plans/2026-09-30-d6-trend-substitute-contract-parity.md`
- `features/analysis_substitute_discovery.py`
- `features/geometry_substitutes.py`
- `features/group_self_description.py`
- `features/scene_inference.py` 中的 `_pca_frame_stats`、`_furniture_group_frame`、`_member_frame_consensus`
- 当前 trend probe 和 renderer

## 目标

把以下三项放入一个可复核 checkpoint：

1. 建立 design-only 的共用 substitute registry；
2. 补齐真实 IFC Analysis 替身的类型化 provenance；
3. 对同一批 Analysis 几何直接调用旧 `_furniture_group_frame`，完成 legacy parity 对照。

最终比较 A/C/D 与旧实现，但不选择 winner：

- A：`member_orientation_consensus`，成员自身朝向共识；
- C：`area_weighted_total_covariance_pca`，整个家具组占据几何的总体方向；
- D：`between_member_centroid_pca`，成员中心排列方向；
- B/legacy：旧 point-cloud PCA 及 `_furniture_group_frame` 的最终输出和内部诊断。

## 不允许做的事

- 不修改 `features/`、`adapters/`、`test/`、NeutralSceneV2、公共 API 或依赖。
- 不修改源 IFC：
  `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`
- 不修改用户当前打开的 Blender/Bonsai 文件。
- 不使用 Body 几何计算 trend；Body 只能作为 provenance 和视觉审计。
- 不通过对象名称、普通 group、图层、source label 或显示标签授权替身语义。
- 不把 `strength`、`coherence` 当概率。
- 不决定 C 是否成为正式 trend，不决定 threshold，不实现 Bayesian/ML，不实现 selector 或 automatic space。
- 不运行 `git add -A`、`git add .`、`git clean`、`git reset` 或回滚其他未跟踪内容。

## 执行步骤

### 1. 建立 registry

在 `scripts/design/group_level/` 下建立 registry JSON 和只读 Python helper。至少定义：

- `trend_analysis`：接受 `consumer=trend`、`substitute_kind=MassPatch`、`analysis_role=analysis_geometry_substitute`；
- 可选的 `clearance_analysis`、`path_analysis`、`body_audit` 仅在现有证据需要时定义。

registry 必须把稳定语义和可编辑显示配置分开：

- 稳定：`contract_key`、consumer、accepted kind、accepted role；
- 可编辑：display label、颜色、线型。

实例不能只依赖 registry。每个实例必须有：

```text
substitute_id
source_object_id
consumer
substitute_kind
analysis_role
provenance
```

实现并测试：

- 接受完整 Analysis 替身；
- 拒绝缺字段、错误 consumer、错误 kind、错误 role、Body-only、label-only 和重复 substitute ID；
- 显示名变化不能改变语义匹配。

### 2. 补齐真实 IFC typed provenance

继续使用真实 IFC 和现有 exact qualification：

```text
IfcGroup.ObjectType == "furniture_group"
```

完整盘点 37 个 exact furniture groups，按当前确定性策略选出 3 个完整 Analysis-footprint groups。保留所有跳过组及其 `unsupported_holes`、missing、invalid、partial 原因。

每个 Analysis substitute 记录：

- 唯一 `substitute_id`；
- `source_object_id`；
- `consumer="trend"`；
- `substitute_kind="MassPatch"`；
- `analysis_role="analysis_geometry_substitute"`；
- 原始 IFC representation/property 引用；
- source IFC SHA-256；
- 提取方法；
- world transform 已应用的事实；
- `visibility_policy="analysis_only"`；
- 与 registry 的 `contract_key`。

没有完整 typed binding 的记录不得静默降级到 Body 或名称匹配。

### 3. 直接 legacy parity

对同一批 Analysis 投影几何构造旧函数所需的 `members` 和 `extents`，直接调用：

```python
features.scene_inference._furniture_group_frame(members, extents)
```

不要修改该函数。结果中必须分别保存：

1. 旧函数最终输出：`angle`、`strength`、`basis`；
2. 旧函数内部几何 PCA：`geometry_angle`、`clarity`、extent/point provenance；
3. B 的 point-cloud 输入和 point count；
4. A、C、D 的结果。

特别说明：旧函数在成员 frame support 大于零时，最终 basis 是 `member_frame_consensus`；point-cloud PCA 只是 geometry diagnostic/fallback。不能把旧函数最终输出与 C 误称为同一个量。

角度比较必须遵守：

- A 的 frame：modulo 90°；
- A 的 axis、B、C、D 和旧 PCA：modulo 180°。

不要把 89.987° 之类的边界值静默四舍五入成另一个 estimand；应记录其等价关系和数值误差。

### 4. 重新运行 probe 和 Blender

用同一份 JSON 结果驱动 Blender。Blender 只能读取结果和 registry，不得重新计算方向或决定 winner。

至少生成：

- synthetic comparison PNG；
- real IFC comparison PNG；
- `.blend`；
- JSON provenance；
- visual manifest；
- artifact manifest。

图中必须同时显示 Analysis footprint、面积加权中心、A/C/D/legacy 向量、contract label、invalid/partial 状态和必要 provenance。颜色之外还要有文字或线型区分。

### 5. 验证

至少执行：

```powershell
pixi run pytest scripts/design/group_level/test_trend_substitute_registry.py -q
pixi run python scripts/design/group_level/run_trend_direction_probe.py
pixi run pytest test/test_group_self_description.py test/test_blender_preview.py -q
git diff --check
```

以及：

- registry/schema JSON 解析；
- parity assertions；
- source IFC SHA-256 before/after；
- artifact hash；
- Blender portable exit code；
- PNG 非空、尺寸和人工视觉检查；
- 显式 Git scope audit。

## 交付

交付以下内容：

- registry JSON/helper 和其测试；
- 更新后的 typed trend probe 结果；
- legacy parity report；
- synthetic/real IFC PNG 和 `.blend` 路径；
- artifact/visual manifest；
- 一份报告，明确区分 observed facts、interpretation、limitations 和 owner decisions。

报告必须明确：

- 本 checkpoint 证明了哪些输入和计算事实；
- 哪些只是设计候选；
- 哪些组因 holes/invalid 被跳过；
- 没有证明全模型准确率、心理效度或 production winner。

完成后必须在报告末尾写：

`STOP FOR TREND ESTIMAND REVIEW`

并等待 owner 决定：

1. 是否把 C 定义为总体 trend；
2. 是否保留 A 作为成员方向描述；
3. 是否保留 D 作为布局排列描述；
4. B 是否永久只作 legacy diagnostic；
5. registry 是否允许进入 production implementation design。
