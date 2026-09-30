# 编程 Agent Prompt：D6 家具组与空间自描述第一切片

你负责实现 D6 第一条 production evidence 切片。开始前必须阅读：

1. `AGENTS.md`
2. `docs/indoor_layout_evaluation_matrix_architecture_memory.md`
3. `docs/project/d6-overall-self-description-design-table.md`
4. `docs/project/d6-group-self-description-implementation-design-review.md`
5. `docs/superpowers/plans/2026-09-29-group-self-description-first-slice.md`
6. 当前现有实现：`features/scene_inference.py`、`features/neutral_scene_views.py`、`features/scene_contract.py`

正式计划已由独立 reviewer 审核通过，最近修订提交为 `6ce04fb`。严格按计划 Task 1 → Task 5 执行；每完成一个 Task 都停止并回报，未经复核不要跳到下一 Task。

## 目标

实现一个独立 helper：

```python
describe_group_relations(scene: AnalysisSceneInput) -> dict[str, object]
```

它只输出：

- eligible authored furniture-group geometry；
- group-pair member observations；
- 已有空间/context observations；
- local-neighborhood evidence。

它不选择 inferred-group selector，也不生成唯一 partition。

## 必须遵守的边界

- `NeutralSceneV2.authored_groups` 中只有 `group_role == "furniture_group"` 才有资格成为家具组节点。
- legacy mapping 只接受明确的 `object["furniture_group"]` 或 `metadata["furniture-group"]`。
- 不得使用普通 `group_refs`、名称、图层、邻近、旧 region fallback 或 `_group_membership()` 兼容行为创建家具组。
- context 保持 context，可以提供已有空间/方向参照，但不成为 furniture-group node。
- trend 只能读取 canonical analysis proxy（例如 IFC `Analysis` 或外部 affordance/proxy geometry）；IFC `Body`/本体几何只用于 provenance 和可视化，永远不得作为 trend 计算输入，也不得在 proxy 缺失时静默 fallback 到 `Body`。
- 每个功能替身必须有稳定唯一的 `substitute_id`，并带有 `source_object_id`、`consumer`/功能、`substitute_kind`、`analysis_role` 和 provenance；名称不能单独授权语义。一个物体可以有多个功能替身，但 trend 只能接受 role/kind 与 trend contract 匹配的 proxy。
- 不修改 `NeutralSceneV2`、adapter、`room_analysis_model` shape 或 IFC/SVG 生产路径。
- 不实现 connected-components、complete-link、max-span、candidate selector、唯一 partition、Bayesian、心理阈值或 IFC 写回。
- 不新增依赖。

## 冻结公式与状态

- `support_area = Σ A_i`。
- `center = Σ(A_i*c_i)/ΣA_i`。
- `within = Σ(A_i/A)*C_i_within`。
- `between = Σ(A_i/A)*(c_i-center)(c_i-center)^T`。
- `covariance = within + between`。
- 有效简单 polygon 用 shoelace 面积、中心和二阶矩；holes 在本切片为 `invalid`，reason=`unsupported_holes`；多个简单 component additive 汇总；不做 union。
- `group_frame` 使用 `4θ`，`group_axis` 使用 `2θ`；directional weight=`area*anisotropy`。
- 本切片 `strength=null`，`strength_status="deferred"`。
- member-pair 的 raw gap/contact/overlap/normalized gap 单独计算并保留 witness。
- 不选择 group-level `min/max/any/all-pairs/union` 聚合；group-level gap/contact/overlap/positive-negative summaries 和 `formal_membership_edge` 必须为 `null`，`aggregation_status="deferred"`。
- group-level `overlap_area` 保留字段；本切片为 `null`，`union_area_status="deferred"`。
- domain-dependent 空间字段在无 `AnalysisDomain` 时为 `not_available`，不能返回零。
- 顶层必须是 `schema="group-self-description-evidence/v1"`，`candidate_view_status="deferred"`，`candidate_views=null`。
- group/geometry status：`computed | partial | not_available | invalid | not_evaluated`。
- pair/channel status：`computed | partial | not_available | invalid | not_computable | diagnostic_only | not_evaluated`。
- 不得把 invalid 改写为 missing，也不得把 unavailable 填成 0。

## 执行方式

### Task 1

先创建 `test/test_group_self_description.py`，写出 eligibility、geometry、pair/context、domain-missing 的失败测试，然后运行：

```bash
pixi run pytest test/test_group_self_description.py -q
```

确认测试因 helper 不存在而失败后停止回报。

### Task 2

创建 `features/group_self_description.py`，实现严格资格筛选、representative geometry、frame/axis 描述和状态传播。先只让 Task 1 测试通过，再运行 focused tests 并停止。

### Task 3

实现 member-pair observations 和 local-neighborhood。不得把 pair observation 升级为 membership edge。运行：

```bash
pixi run pytest test/test_group_self_description.py test/test_neutral_scene_analysis_regression.py -q
```

通过后停止。

### Task 4

只增加声明的 planar acceptance 测试：使用仓库内 `scripts/design/group_level/e10b_independent_svg_fixture.svg` 和确定性 NeutralScene fixture；不要依赖外部 `outputs/` 路径。SVG 只比较声明的 2D facts；不要宣称 SVG 有 Z/3D/opening capability。运行计划中指定的 adapter tests 后停止。

### Task 5

保持 standalone helper 边界。本计划不修改 `features/scene_inference.py`，不改公共 model/API。运行：

```bash
pixi run pytest -q
git diff --check
```

回报 changed files、focused tests、full suite、status/capability 限制和未实现的 candidate selector，然后停止。

## 遇到歧义时

如果实现需要自行决定 pair 聚合、semantic field 路径、空间阈值、context 新标记、候选 selector、Bayesian prior 或公共 API，请停止并提出设计问题，不要自行补规格。

每个新增函数必须有 English-first docstring；几何、状态、provenance 和 serialization 逻辑必须有解释“为什么”的英文注释。
