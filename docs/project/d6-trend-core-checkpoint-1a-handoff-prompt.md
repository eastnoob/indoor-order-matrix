# Handoff Prompt: D6 Trend Core Checkpoint 1A

你是本项目的执行 session。请在
`D:\PROJECTS\understandOtherPackage\order_analyzer`
中执行 **Trend Core Checkpoint 1A**。

这一阶段只实现已批准设计中的核心 trend 描述和 typed substitute resolver，
完成后必须停止。不要进入 IFC adapter 集成、自动 space、candidate selector、
Bayesian/ML 或下一阶段 implementation。

## 必须先读

- `AGENTS.md`
- `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
- `docs/project/evidence/d6-trend-estimand-owner-review.md`
- `docs/project/evidence/d6-trend-implementation-design-review.md`
- `docs/project/evidence/d6-trend-substitute-contract-parity.md`
- `docs/project/evidence/d6-trend-direction-design-probe.md`
- `features/group_self_description.py`
- `features/analysis_substitute_discovery.py`
- `features/geometry_substitutes.py`
- `features/scene_contract.py` 中的 `SourceObject` 和 `NeutralSceneV2`
- `test/test_group_self_description.py`

## 本 checkpoint 的目标

将以下四个明确含义的描述加入 group evidence：

```text
trend_descriptors.overall_group_axis  # C：总体几何方向
trend_descriptors.member_frame        # A：成员四角度 frame
trend_descriptors.member_axis         # A：成员二角度 axis
trend_descriptors.layout_axis         # D：成员中心排列方向
```

保留现有 `group_frame` 和 `group_axis` 的 A 兼容语义，不得把它们静默改成 C。

## 严格边界

- 本阶段允许修改：
  - `features/analysis_substitute_discovery.py`
  - `features/group_self_description.py`
  - `test/test_group_self_description.py`
  - 必要的新 focused test 文件
- 不修改：
  - `adapters/ifc_bonsai.py`
  - `adapters/svg_scene.py`
  - `NeutralSceneV2` dataclass 定义
  - `room_analysis_model`、公共 API、依赖、源 IFC、用户当前打开的 Blender 文件
- 不运行 `git add -A`、`git add .`、`git clean`、`git reset` 或回滚其他未跟踪内容。
- 不把 Body 几何作为 trend fallback。
- 不用名称、图层、普通 group、`source_role` 单独授权 trend 语义。
- 不实现 automatic space、inferred-group selector、Bayesian、ML 或心理效度。

## Task 1：typed substitute resolver

优先扩展已有 `features/analysis_substitute_discovery.py`，不要创建第二套发现机制。

添加一个最小的、可审计的 resolver，接口可以采用：

```python
resolve_function_substitute(
    scene: NeutralSceneV2,
    source_object_id: str,
    consumer: str,
) -> dict[str, object]
```

要求：

1. 从 source object's `factual_properties["OM_FunctionSubstitutes"]` 读取 typed binding；
2. 每个 binding 必须有：

   ```text
   substitute_id
   consumer
   substitute_kind
   analysis_role
   representation_identifier
   provenance
   ```

3. `consumer == "trend"` 时只接受：

   ```text
   substitute_kind == "MassPatch"
   analysis_role == "analysis_geometry_substitute"
   representation_identifier == "Analysis"
   ```

4. `substitute_id` 必须解析到 scene 中独立的 Analysis SourceObject；
5. 该对象必须有 `source_role == "analysis_substitute"` 和 geometry refs；
6. Body、label-only、错误 kind、错误 role、错误 representation、缺 geometry、重复或多候选必须返回明确状态；
7. 不得根据 `:analysis` 后缀、对象名称或字典顺序单独选择替身；
8. 返回结果必须保留 selected substitute id、source id、reason 和 provenance。

不要在本阶段修改 IFC adapter 去生成这些绑定；用最小的 NeutralScene 测试 fixture 验证 resolver。真实 IFC binding 在 Checkpoint 1B 单独处理。

## Task 2：实现 C/A/D 描述输出

在 `features/group_self_description.py` 中复用已有 representative geometry，不重写 shoelace、center、within/between covariance。

### C：`overall_group_axis`

- 输入：完整、有效的 typed trend Analysis geometry；
- covariance：`within_member_covariance + between_member_covariance`；
- center：已有面积加权 group center；
- direction：major eigenvector，modulo 180°；
- strength：

  ```text
  (lambda_primary - lambda_secondary)
  / (lambda_primary + lambda_secondary)
  ```

- basis：`area_weighted_total_covariance_pca`；
- 各向同性或零 trace：`angle=None`、`direction_status="undefined"`；
- C 的 strength 是确定性几何证据，不是 probability。

### A：`member_frame` 和 `member_axis`

保留当前 A 公式和语义：

- 每个成员由 Analysis polygon covariance 得到自身方向；
- 权重为 `area * member_anisotropy`；
- `member_frame` 使用 4θ，modulo 90°；
- `member_axis` 使用 2θ，modulo 180°；
- coherence 是确定性 resultant concentration，不是概率。

现有 `group_frame`、`group_axis` 继续保持 A 兼容值。

### D：`layout_axis`

- 输入：成员 centroid 的 `between_member_covariance`；
- direction：major eigenvector，modulo 180°；
- strength：同样使用 eigenvalue anisotropy；
- 单成员、重合中心或各向同性：`angle=None`、`direction_status="undefined"`；
- basis：`between_member_centroid_pca`。

## Task 3：状态传播

formal `trend_descriptors` 必须遵守：

- `computed`：全部 required Analysis members 有效；
- `partial`：保留状态，正式 descriptor angle 为 `null`；usable subset 只能放在 diagnostic evidence；
- `invalid`：正式 descriptor angle 为 `null`，不能用有效 sibling 凑成完整组；
- `not_available`：没有可用 typed Analysis geometry；
- `not_evaluated`：没有 eligible authored furniture group；
- 不得把 missing、invalid 或 undefined 改写成零角度或零 strength。

不要改变当前 group relation、space observation、candidate view 或 inferred-group 行为。

## Task 4：测试

至少新增或修改测试覆盖：

1. typed Analysis accepted；
2. Body provenance rejected；
3. wrong consumer/kind/role/representation rejected；
4. missing/duplicate/ambiguous substitute binding；
5. C 的面积加权中心和 covariance PCA；
6. C 的平移不变性、旋转行为、tessellation invariance；
7. C 的 isotropic undefined；
8. A frame/axis harmonic difference；
9. D 与 A 不同的“身体方向 vs 成员排列” fixture；
10. invalid/partial/not_available 不产生 formal numeric descriptor；
11. 旧 `group_frame`/`group_axis` 兼容语义没有被改写；
12. JSON serialization 使用 `allow_nan=False`。

## 验证命令

```powershell
pixi run pytest test/test_group_self_description.py -q
pixi run pytest scripts/design/group_level/test_trend_substitute_registry.py -q
pixi run pytest -q
git diff --check
```

如果全套测试因本 checkpoint 之外的既有未跟踪文件或环境问题失败，记录准确失败原因，不修改无关内容。

## 交付

交付：

- typed resolver 实现和 focused tests；
- `trend_descriptors` 输出示例；
- 测试和完整验证结果；
- 修改范围审计；
- 一份简短报告，区分 observed result、implementation limitation 和下一阶段 adapter 工作。

不要提交源 IFC、PNG、`.blend` 或其他大型生成文件，除非已有任务明确允许。

完成后必须停止在：

`STOP FOR TREND CORE CHECKPOINT 1A REVIEW`

并等待总控 session 审查。不要自行开始 Checkpoint 1B 的 IFC adapter integration。
