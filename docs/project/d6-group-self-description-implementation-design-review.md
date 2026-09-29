# D6 家具组与空间自描述：implementation-design review 草案

- 日期：2026-09-29
- 状态：待 owner review；不修改 production code
- 上游设计：[d6-overall-self-description-design-table.md](d6-overall-self-description-design-table.md)
- E11：[d6-self-description-competition-experiment-record.md](d6-self-description-competition-experiment-record.md)
- 目标切片：relation observations + spatial-field observations + local-neighborhood view
- 明确不做：candidate selector、唯一 partition、Bayesian inference、心理效度校准、IFC 写回

## 1. 第一条实现切片

第一条实现只回答：

> 对已经具备资格的 authored furniture groups，系统能否在统一 analysis frame 中输出可审计的 group geometry、group-pair relation、允许的 context/space observations，以及每个 group 的 local-neighborhood view？

它不回答“哪些组最终应该合并”。因此第一条切片不创建 inferred membership，不调用 connected-components 作为产品结果，不将 inter-region gap-path graph 当作 group graph。

## 2. 现有代码复用边界

| 现有能力 | 第一切片处理 | 理由 |
|---|---|---|
| `analysis_scene_view()` | 复用 | 已负责 Neutral Scene 到 planar consumer view 的转换、analysis plane 和 domain capability |
| `furniture_groups()` | 只复用其 authored-group 入口和 member provenance，representative 输出需重新收口 | 现有 group extent/trend 语义不能自动等同新设计 |
| `boundary_semantics()` | 复用为 boundary/opening evidence source | 保留四个 boundary channel，不引入旧 weighted grouping strength |
| `inferred_region_candidates()` | 第一切片不调用作为 group candidate selector | 当前节点和目标语义是 activity-region candidates，非 clean-room inferred-group selector |
| `inferred_region_gap_paths()` / gap-path graph | 保留为独立 inter-region evidence | 不反写 furniture-group membership |
| `position_grammar` / legacy region inference | reference_only | 不进入首轮 membership 或 local-neighborhood edge |
| IFC/SVG adapters | 不改动 | 只验证它们提供的 Neutral facts 是否足够 |

首切片建议新增一个职责单一的 inference helper module，而不是继续扩大已经很长的 `scene_inference.py`。它读取现有 planar view，输出独立 evidence mapping；是否挂接到公共 `infer_scene_evidence()` 由 review 后再决定。

首切片实现契约已经进一步收紧：资格直接检查 `NeutralSceneV2.authored_groups[*].group_role == "furniture_group"`；legacy mapping 只接受显式 `furniture_group`/`metadata["furniture-group"]`。有效简单 polygon component 使用 shoelace 面积、中心和二阶矩；holes 返回 `not_computable`，多个简单 component additive 汇总，union 延后。group pair 只输出 `member_pair_observations`，不在本切片选择 min/max/any/all-pairs/union 聚合，group-level gap/overlap/edge 保留 `null` 并标记 `aggregation_status="deferred"`。`analysis_frame.plane` 是 plane name，`basis` 单独保存；顶层 schema 固定为 `group-self-description-evidence/v1`。具体冻结契约以 implementation plan 的 Frozen First-Slice Contract 为准。

## 3. 建议的内部接口（待 review）

```python
def describe_group_relations(
    scene: AnalysisSceneInput,
) -> dict[str, object]:
    """Return relation-layer and local-neighborhood evidence only."""
```

返回值只是一份 inference evidence mapping，不改变 `NeutralSceneV2`、adapter payload 或 `room_analysis_model` shape：

```text
{
  "schema": "group-self-description-evidence/v1",
  "schema": "group-self-description-evidence/v1",
  "analysis_frame": {"name": "...", "plane": "...", "basis": [...], "origin": [...], "unit": "..."},
  "eligibility": [...],
  "group_geometry": [...],
  "group_relations": [...],
  "space_observations": {...},
  "local_neighborhood": [...],
  "candidate_view_status": "deferred",
  "candidate_views": null,
  "capabilities": {...},
  "uncertainties": [...],
  "provenance": {...}
}
```

`candidate_views` 在第一切片必须为 `null`，并由顶层 `candidate_view_status="deferred"` 明确表示 selector 尚未实现；不能用空列表伪装“没有候选”。

## 4. 输出字段设计

### 4.1 Eligibility

每个 source object 只按现有显式 furniture-group relation 判断：

```text
eligible_group_id
member_object_ids
membership_provenance
excluded_context_object_ids
completeness_status
```

普通 `IfcGroup`、名称、图层、邻近和旧 region 不得生成 eligible group。context 对象保留 source id、geometry ref 和 provenance，但不进入 group node list。

### 4.2 Group geometry

每个 eligible group 输出：

```text
target_layer = "furniture_group"
target_id
geometry_status = computed | partial | not_available | invalid | not_evaluated
support_area
center
within_member_covariance
between_member_covariance
covariance
excluded_member_reasons
geometry_completeness
group_frame
group_axis
directional_member_support
coherence
strength
uncertainty = absent/recorded, never zero-filled
```

首阶段 `support_area` 是 additive area；overlap 是独立 relation observation，不从 denominator 静默扣除；polygon union 继续 deferred。含 holes 的 polygon 在首阶段返回 `not_computable`，不能静默填洞；多个简单 component 只做 additive aggregation。invalid member 不能被改写成 missing。

### 4.3 Group relation

每个 eligible group pair 输出一个稳定 pair record。首阶段只输出 member-pair observations，不选择 `min`、`max`、`any`、`all-pairs` 或 union 作为 group-level 聚合：

```text
target_layer = "furniture_group_pair"
target_id
group_a
group_b
member_pair_observations
raw_boundary_gap = null
normalized_boundary_gap = null
contact
overlap
overlap_area = null
aggregation_status = "deferred"
member_pair_witnesses
3d_clearance / 3d_overlap / z_compatibility = capability or not_available
barrier_observation
space_channel_status
semantic_channel_status
positive_support
negative_evidence
shared_member_dependency
status
reason
analysis_frame / unit / tolerance
source_provenance
```

这里的 `status` 表示观测可计算性或关系冲突，不是“已确认同组”。`formal_membership_edge` 在第一切片不作为 canonical output；若保留诊断字段，必须明确 `diagnostic_only`。

### 4.4 Space observations

空间观测只在显式 `AnalysisDomain` 可用时计算 domain-dependent channel；没有 domain 时传播 `not_available`，不能把 scene bounds 当 domain。第一切片只序列化已有 `analysis_domain`、`channel_evidence`、boundary/opening、occupancy/blocker provenance 和 context alignment reference，不新增 raster free-space、connectivity、bottleneck width 或 primary-role selector。

首切片只输出 observation，不生成唯一角色：

```text
domain_status
free_space / clearance observation
connectivity observation
bottleneck profile
boundary openness / permeability channels
occupancy and barrier provenance
local alignment context references
role_support_vector
role_conflicts
space_role_candidates
```

context 不需要新增用户标签。指标根据已有几何、位置、高度和来源决定是否可作为参照；参照来源用 provenance 标注。灯具、柜台、斜墙等不会成为家具组节点。

### 4.5 Local-neighborhood

local-neighborhood 是第一切片唯一的 group-level view：

```text
group_id
neighbor_group_id
relation_id
positive_support_vector
negative_evidence_vector
semantic_conflicts
space_conflicts
missingness
status
candidate_competition_refs
```

它不返回 partition，不把最近邻自动变成 membership，不调用 trend/frame/coherence/strength 反向决定首轮 relation。

## 5. 状态和可计算性

| 情形 | 输出规则 |
|---|---|
| usable geometry + required channels | `computed` |
| usable geometry with optional missing channel | relation retained; missing channel `not_available` |
| required domain missing | domain-dependent fields `not_available`; geometry-only relation remains separately auditable |
| invalid geometry | `invalid` / `not_computable`; valid sibling support only diagnostic |
| no eligible authored group | empty node list with explicit `not_evaluated` reason |
| explicit mutual exclusion | relation may remain measured, candidate membership later vetoed |
| context object | context provenance only; may affect permitted space observation |

## 6. Tests required before integration

实现时每个小任务都必须有独立检查：

1. **Eligibility test**：只有 exact furniture-group marker 进入 node list；普通 group/context 不进入。
2. **Representative geometry test**：additive area、area-weighted center、within/between covariance 和 invalid/missing 状态。
3. **Pair relation test**：gap/contact/positive-area overlap/near、3D/Z 和 member witness 分通道。
4. **Context test**：斜墙/墙体/柜台可改变允许的空间观察，但不会改变 eligibility 或 authored membership。
5. **Domain capability test**：无 AnalysisDomain 时空间 topology/status 为 `not_available`，不能返回计算零值。
6. **Semantic test**：普通 label mismatch 是 soft negative；explicit mutual exclusion 只记录冲突，第一切片不生成 candidate selector。
7. **Invariant test**：ID rename、输入遍历顺序、平移/旋转和 IFC/SVG declared-2D facts 不改变 canonical relation semantics。
8. **Regression test**：已有全套测试保持通过；旧 inter-region gap-path graph 的节点语义不变。

## 7. IFC / SVG 验收边界

- IFC 是主来源，负责 3D、Z、clearance、真实 opening relation 和 barrier capabilities。
- SVG 只验声明的 2D canonical facts：group eligibility、plan geometry、center/area、gap、contact、positive-area overlap、status/provenance。
- SVG 不补 IFC 缺失的 opening/void/fill、Z、3D clearance 或 mixed barrier result。
- tolerance、analysis plane、unit 和 source/analysis transform 必须随 evidence 记录。

## 8. 后续 candidate slice（不在本轮实现）

只有第一切片通过 review，才设计第二条切片：

```text
relation/local-neighborhood evidence
  → named candidate views
  → multi-scale competition
  → explicit mutual-exclusion filtering
  → approved deterministic synthesis
```

第二条切片仍不默认 CC、complete-link、max-span 或固定加权分数；每个 view 必须带 objective、scale、provenance、failure state。Bayesian 层位于 deterministic synthesis 之后。

## 9. Review questions

进入 implementation plan 前只需 owner review 以下四项：

1. 是否批准第一条切片只实现 relation observations、space observations 和 local-neighborhood，不实现 candidate selector？
2. 是否批准 `describe_group_relations()` 作为内部 evidence helper，而暂不改变公共 model shape？
3. 是否批准 `candidate_views=null` 配合 `candidate_view_status="deferred"` 表示 selector 尚未实现？
4. 是否批准上述 IFC/SVG canonical facts 和 domain-missing 传播边界？

**STOP FOR IMPLEMENTATION-DESIGN REVIEW**
