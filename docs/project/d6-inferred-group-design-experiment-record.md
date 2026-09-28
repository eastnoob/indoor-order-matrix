# D6 Task 3d inferred-group design experiment record

**状态：设计实验；不冻结算法、不进入 Task 3c、不修改 production code。**

本轮只比较家具组之间的几何候选。IFC 是 3D、Z、clearance 和 barrier 的主 fixture；SVG 只作为相同 canonical 2D facts 的等价 oracle。所有数值来自 synthetic fixture，不能解释为心理效度、Bayesian prior、真实场景准确率或人的感知标签。

## 运行与证据

- Fixture manifest：[inferred_group_experiment_fixtures.json](../../scripts/design/group_level/inferred_group_experiment_fixtures.json)
- Probe：[run_inferred_group_experiment.py](../../scripts/design/group_level/run_inferred_group_experiment.py)
- Probe evidence：[d6-inferred-group-design-experiment.json](evidence/d6-inferred-group-design-experiment.json)
- 2D 候选对照：[d6-inferred-group-candidates.svg](evidence/d6-inferred-group-candidates.svg)
- 3D/Z/barrier channel 对照：[d6-inferred-group-channels.svg](evidence/d6-inferred-group-channels.svg)
- 现有 v1 group-level probe：`scripts/design/group_level/run_group_level_probe.py`；本轮另行运行其断言，不改它的算法。
- Follow-up fixture manifest：[inferred_group_followup_fixtures.json](../../scripts/design/group_level/inferred_group_followup_fixtures.json)
- Follow-up probe：[run_group_level_followup_probe.py](../../scripts/design/group_level/run_group_level_followup_probe.py)
- Follow-up evidence：[d6-inferred-group-design-followup.json](evidence/d6-inferred-group-design-followup.json)
- E10 canonical 2D oracle：[d6-e10-bim-acceptance-svg-2d-canonical.json](evidence/d6-e10-bim-acceptance-svg-2d-canonical.json) / [SVG](evidence/d6-e10-bim-acceptance-svg-2d-canonical.svg)
- E10b independent SVG fixture：[e10b_independent_svg_fixture.svg](../../scripts/design/group_level/e10b_independent_svg_fixture.svg)，由现有 `adapters/svg_scene.py` 实际加载。

命令：

```text
pixi run python scripts/design/group_level/run_inferred_group_experiment.py --fixtures scripts/design/group_level/inferred_group_experiment_fixtures.json --output docs/project/evidence/d6-inferred-group-design-experiment.json --visual-dir docs/project/evidence
```

fixture SHA-256：`28d8cf6ccfb5dcdf3068a82a6e615a7768a93328df1433426e57a3944d5c2a36`。

Follow-up command：

    pixi run python scripts/design/group_level/run_group_level_followup_probe.py --fixtures scripts/design/group_level/inferred_group_followup_fixtures.json --output docs/project/evidence/d6-inferred-group-design-followup.json --svg-output docs/project/evidence/d6-e10-bim-acceptance-svg-2d-canonical.svg --svg-json-output docs/project/evidence/d6-e10-bim-acceptance-svg-2d-canonical.json

Follow-up evidence schema remains d6-inferred-group-design-followup/v3; fixture schema is d6-inferred-group-followup-fixtures/v5; fixture SHA-256 is recorded in that evidence file.

## 共同规则

第一轮 membership 只使用 physical support、2D gap、3D clearance、Z compatibility 和 wall/opening barrier。`trend`、`frame`、`coherence`、`strength` 不读入边判定。每个 channel 独立记录 value、status、reason；relation edge 不等同 authored membership。

### E1：connected-components 对 complete-link / max-span

- **Hypothesis：** connected-components 能保留局部邻接，但会把桥接链压成一个组；complete-link/max-span 能暴露组内最大跨度限制。
- **候选方案：** (a) normalized-gap graph 的 connected-components；(b) complete-link 的 maximal cliques；(c) hard partition 下选择覆盖最多节点的 max-span 候选。
- **Fixture：** `bridge_chain`：A-B、B-C 的 normalized gap 均约 `0.353553`，A-C 为 `1.414214`，D 孤立；`long_row`：L1-L4 的相邻边均存在。
- **Invariant：** 平移、正比例缩放和 member id 重命名不改变边集合；不允许 lexical order 代替空间关系；连接图与 candidate 生成分开记录。
- **Failure cases：** bridge chain 被 connected-components 合并为 `[A,B,C]`；complete-link 产生 `[A,B]`、`[B,C]`；hard partition 有两个同覆盖率解；strict complete-link 把 `long_row` 拆成相邻 pair。
- **Decision rule：** 若目标是连通性，保留 CC 作为 baseline；若要求每一组满足最大组内 gap，才允许 complete-link/max-span。出现同覆盖率 partition 时输出 `ambiguous`，不按 id 选解。
- **Result：** CC=`[[A,B,C],[D]]`；complete-link 与本 fixture 的 max-span candidates 都是 `[[A,B],[B,C]]`；hard partition 两解分别 `[[A],[B,C]]` 和 `[[A,B],[C]]`，D 均 `unassigned`。long row 的 CC 是四节点一组，complete-link/max-span 是三条 pair clique。
- **Unresolved questions：** 最终目标是几何连通还是最大跨度受限；是否保留 overlapping candidate；max-span 阈值是否需要多尺度报告；最终 selector 是否允许 ambiguous 输出。

### E2：2D gap、3D clearance、Z-level compatibility、wall/opening barrier

- **Hypothesis：** 2D plan proximity 不能单独决定家具组关系；不同楼层和闭合墙应阻断，开口应作为独立可审计的通道状态。
- **候选方案：** 仅 2D gap；2D gap+3D clearance；再加 Z compatibility；再加 wall/opening barrier。
- **Fixture：** `levels_and_barriers`：FLOOR_A/FLOOR_B 2D gap `0.4`、被 `closed_wall` 阻断；FLOOR_A/STACKED 2D overlap 但 Z 不兼容；WALL_A/WALL_B gap `0.4`、穿过 `open_wall`。
- **Invariant：** 2D 与 3D channel 不互相覆盖；`blocked` 与 `opening` 不折叠为同一 boolean；SVG 不承担这些 3D/阻隔事实。
- **Failure cases：** 仅 2D 会错误保留 FLOOR_A/STACKED；忽略 barrier 会保留 FLOOR_A/FLOOR_B；把 opening 当 wall 会误拒绝 WALL_A/WALL_B。
- **Decision rule：** formal edge 至少要求有效 physical support、2D channel、3D clearance、Z compatibility 和 barrier channel 都可用且未阻断；缺 channel 返回显式 status，不当作通过。
- **Result：** FLOOR_A/FLOOR_B：2D gap=`0.4`、clearance=`0.4`、Z compatible、barrier=`blocked`、formal edge=`false`；FLOOR_A/STACKED：2D overlap=`true`、clearance=`1.0`、Z compatible=`false`；WALL_A/WALL_B：gap=`0.4`、clearance=`0.4`、barrier=`opening`、formal edge=`true`。
- **Unresolved questions：** Z compatibility 是区间相交、容差接触还是 level id 兼容；barrier 是否按 channel/行走方向区分；clearance 采用 AABB、mesh 或 route-width 语义；缺少某个 3D/Z/barrier channel 时的 `not_available` 传播仍未单独 fixture 化。

### E3：shared authored member

- **Hypothesis：** 一个 physical member 同时属于两个 authored groups 时，组间零 gap/overlap 是依赖证据，不是足够的 inferred membership 证据。
- **候选方案：** 把 shared member 当普通 pair；排除 shared pair；保留 pair 但加 `shared_member_dependency`，禁止 formal edge。
- **Fixture：** `shared_member`：G1 和 G2 都包含 `SHARED`，各自另有一个独有 member。
- **Invariant：** authored membership 全量保留；SHARED 在两个组内各自计入 support，但不能跨组去重或制造独立邻接；共享 provenance 不被丢弃。
- **Failure cases：** 普通 pair 规则会把共同 member 的零 gap 当作 G1-G2 关系；跨组去重会改变两个组的 additive support。
- **Decision rule：** 输出 shared member ids、zero gap/overlap 和 dependency provenance；shared-only contact 不得生成 formal membership edge。
- **Result：** G1/G2 的 2D gap=`0`、overlap=`true`、3D overlap=`true`，`shared_members=[SHARED]`，`formal_membership_edge=false`，edges 为空。
- **Unresolved questions：** shared member 是否能在后续模型中作非充分支持；多个 shared members 的依赖图是否需要独立 component；support/union 是否跨 authored groups 做审计汇总。

### E4：partial / missing / invalid

- **Hypothesis：** missing 与 invalid 必须区分：partial 可以保留诊断关系，但 invalid 不能被静默排除为 missing。
- **候选方案：** 全部排除；missing 继续 computed；missing 形成 partial relation、invalid 仅 diagnostic。
- **Fixture：** `status_mix`：VALID 完整；PARTIAL 含一个 valid 和一个 `projection_absent`；INVALID 含 `non_finite_geometry`。
- **Invariant：** 不补零、不伪造 center/area/angle；reason 保留 member id；status 是 categorical exact match。
- **Failure cases：** 把 invalid 当 missing 会让 INVALID 参与 candidate；把 partial 当 complete 会把不完整关系写成正式 edge；全部缺失不能返回 numeric geometry。
- **Decision rule：** valid+missing => `computed/partial`，relation `partial`，不可支持 formal edge；invalid => `invalid/diagnostic_invalid`，不进入 candidate generation；无 usable support => `not_available`。
- **Result：** PARTIAL summary 为 `status=computed`、`completeness=partial`、support=`1.0`；PARTIAL/VALID relation status=`partial`、`formal_membership_edge=false`；MISSING/VALID relation status=`not_available`；INVALID/VALID status=`diagnostic_invalid`，formal edge=`false`。
- **Unresolved questions：** partial node 是否允许进入任何多阶段 candidate graph；invalid diagnostic 的消费边界；缺失 3D channel 与缺失 plan geometry 是否使用同一 status。

### E5：additive support、overlap、union

- **Hypothesis：** additive support、pairwise overlap 和 polygon union 是不同 estimand；首阶段可以记录前两者而不假装 union 已冻结。
- **候选方案：** (a) additive area；(b) pairwise overlap diagnostic；(c) union area 作为正式 denominator。
- **Fixture：** `overlap_union`：两个 `2×2` rectangles 相交面积 `2`。
- **Invariant：** overlap 不静默从 additive support 或 normalized-gap denominator 扣除；union 的 holes、self-intersection、多重重叠语义未决时返回 status。
- **Failure cases：** additive support=`8` 被误写成 union=`6`；pairwise overlap 被误解释为去重 union；多重 overlap 用 pairwise 求和会重复计数。
- **Decision rule：** 首阶段保留 additive support 和 pairwise overlap observation；`union_area_status=deferred/diagnostic_only`，任何 union denominator 变更都开新设计门。
- **Result：** additive support=`8.0`，pairwise overlap=`2.0`，diagnostic union=`6.0`，union 不改变本轮 membership denominator。
- **Unresolved questions：** pairwise overlap 是否去重；多重重叠的 union 拓扑；union 进入 representative、gap normalization 还是仅审计。

### E6：hard partition、overlapping candidate、unassigned、ambiguous

- **Hypothesis：** candidate schema 需要表达多种输出状态，否则会把歧义或孤立节点强行塞进 hard partition。
- **候选方案：** 只返回 hard partition；保留 maximal-clique overlapping candidates；允许 `unassigned` 和 `ambiguous`。
- **Fixture：** `bridge_chain` 同时产生 CC、maximal cliques 和 hard partition options。
- **Invariant：** 未达到 edge 条件的节点可 unassigned；多个同分候选不按 lexical/id 解决；overlapping candidates 不伪装成 disjoint partition。
- **Failure cases：** CC 隐式强制 `[A,B,C]`；complete-link 强行选 `[A,B]` 或 `[B,C]`；D 被错误 singleton-authored group 化。
- **Decision rule：** candidate record 显式写 `mode`、members、supporting edges、unassigned、ambiguity；最终 production output policy 暂缓。
- **Result：** overlapping=`[A,B]`、`[B,C]`；hard partition 两个并列解，`ambiguous=true`；D=`unassigned`；CC 仅 baseline。
- **Unresolved questions：** production 首 slice 是否允许重叠；ambiguous 是否输出候选集还是阻断；unassigned 是否进入后续 region/path 层。

### E7：IFC 主 fixture 与 SVG 等价 2D fixture

- **Hypothesis：** 对同一 canonical 2D facts，IFC 与 SVG 应产生相同的 2D evidence；SVG 不应被要求复现 3D/Z/clearance/barrier。
- **候选方案：** 全量 IFC/SVG parity；仅声明等价的 2D parity；SVG 仅截图/视觉比对。
- **Fixture：** `equivalent_sources.ifc_primary` 是主 fixture；`svg_equivalent_2d` 使用相同 frame、unit、group membership、plan centers/sizes，但不提供 `z_intervals`。
- **Invariant：** correspondence source-independent；不按 STEP/XML traversal、lexical id 或 viewBox 猜对应和单位；status/provenance 的比较是 exact categorical。
- **Failure cases：** 要求 SVG 提供 Z 会把 capability 缺失误报成 parity failure；按 viewBox 当米会改变 gap；全量 parity 会夸大 SVG 范围。
- **Decision rule：** 比较 frame、unit、membership、plan geometry、representative status、2D pair channels；3D/Z/clearance/barrier 只由 IFC 验收。
- **Result：** 可比较 keys=`analysis_frame`、`membership_kind`、`pair_2d`、`plan_centers`、`plan_sizes`、`representative_status`、`unit`；mismatches=`{}`；IFC-only=`z_intervals`；2D parity=`pass`。
- **Unresolved questions：** 当前 IFC 是 canonical metadata fixture，不是实际 STEP/IFC parse；IFC/SVG fixture 的最终文件和 owner；canonical correspondence manifest；最终 tolerance acceptance 与签名。

### E8b：多成员 group-pair 聚合

- **Hypothesis：** 同一 group pair 的多个 member pairs 不能默认由最小 gap 或最小 clearance 代表；any、极值 witness、independent summary 和 all-pairs 必须同时可审计。
- **Candidate rules：** any witness；min-gap/min-clearance witness；max-gap/max-clearance constraint；all-pairs conjunctive；independent min/max；pairwise summary + group-level status；disconnected member split diagnostic。每个候选都保留全部 member-pair observations、witness pair、excluded pairs、formal edge、status 和 provenance。group-level formal edge 在本轮保持 false，因为聚合政策未冻结。
- **Fixture：** near_far_multi_member（一个近 pair、多个远 pairs）、overlap_plus_far、multi_z_levels、disconnected_members、unequal_rotated_transform、partial_member_support、no_usable_members、shared_member_dependency。覆盖近/远、overlap/非 overlap、不同 Z、组内 disconnected、unequal size、rotation/translation/positive scale、traversal/id rename 和 shared member。
- **Invariants：** 每一条 pair observation 保留 member-pair provenance、shared_member_dependency、geometry completeness、analysis frame、unit、tolerance、source provenance；missing/invalid 不产生数值；ID 和遍历顺序不改变 pairwise summary；共享 member 不形成 self-pair formal edge。
- **Failure cases：** near/far 的 any 和 min witness 为 true，而 max/all-pairs 为 false；overlap_plus_far 的 overlap count 为 1 且 max-gap witness 为 false；multi_z_levels 仅 2/4 pairs Z-compatible；disconnected_members 的 min gap 为 0.4、max gap 为 7.6，并产生 diagnostic_only split；partial support 为 partial；无可用 pair 为 not_available；shared-only pair 为 diagnostic_only、标记 dependency 且 formal false。聚合候选意见不一致时 group-level status 为 ambiguous。
- **Decision rule：** 先保留 pairwise observations 和 summary extrema；任何正式 group edge 需要后续冻结的聚合规则，不能把最小 gap 默认提升为 membership 规则。当前建议继续实验，暂不批准 any/min/max/all-pairs 中任一规则。
- **Observed result：** near_far、overlap_plus_far、multi_z_levels、disconnected_members 均呈现候选规则分歧并输出 ambiguous；partial/no-usable 分别输出 partial/not_available；transform checks 的 rotation_translation、positive_scale_normalized、member_traversal、id_rename 全部为 true；每条候选规则均有 witness_pair 与 excluded_pairs；shared_member_ids 为 SHARED_1，状态为 diagnostic_only 且 formal_edge 为 false。
- **Unresolved question：** 组级关系是否要求 all-pairs、是否采用可解释的 independent summary、disconnected member 是否应拆成 candidate，及 barrier/Z 的 group-level 合取范围。

### E9：缺失 channel 传播

- **Hypothesis：** missing、invalid 和 partial 必须保持 categorical status；缺失 channel 不能被重写为 clear、false 或 zero，且只让声明为 formal 的 channels 阻断 formal edge。
- **Candidate rules：** required formal channel 缺失返回 not_available；组支持不完整返回 partial；invalid geometry 返回 diagnostic_only；external_affordance 缺失仅 diagnostic；所有 formal channels computed 才允许 formal edge=true。
- **Fixture：** all_channels_available、missing_2d_geometry、missing_3d_clearance、missing_z_interval、missing_wall_barrier、missing_external_affordance、invalid_geometry、partial_group_support。
- **Invariants：** 每个 channel 独立保留 value/status/reason；pair provenance、analysis frame、unit、tolerance 和 source provenance 始终存在；formal_edge 只由 formal channels 决定。
- **Failure cases：** missing 2D/3D/Z/barrier 均为 not_available 且 formal false；invalid_geometry 为 diagnostic_only 且 formal false；partial_group_support 为 partial 且 formal false；missing_external_affordance 仍可 computed/formal true，但 diagnostic_only=true。
- **Decision rule：** geometry_2d、clearance_3d、z_compatibility、wall_opening_barrier 是本轮 formal membership 必要条件；external_affordance 只能诊断。缺失不补零、不视为 clear，不进入正式 edge。
- **Observed result：** 八个 case 的状态和断言均通过，所有 required missing/invalid/partial case 的 formal_edge 均为 false。
- **Unresolved question：** partial channel 是否允许进入后续 candidate graph，以及不同下游消费者是否需要比本轮三态更细的 reason taxonomy。

### E10：真实 IFC4 fixture 审核

- **Hypothesis：** 真实 IFC4 只能按 exact IfcGroup.ObjectType=furniture_group 进入候选；普通 IfcGroup 仅保留 provenance；3D、Z、clearance 和 wall/opening channel 由 IFC 验收，SVG 只核对声明的 canonical 2D facts。
- **Candidate rules：** 递归搜索可解析 IFC；选择第一个含 exact furniture_group ObjectType 的 IFC 作为 primary；记录所有样本 inventory；对 group、GlobalId、ObjectType、单位、placement、显式 tessellation、walls、doors、openings 和关系计数做 read-only audit；SVG oracle 从 IFC canonical 2D boxes 派生。
- **Fixture：** 实际主样本 outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc，schema IFC4，IfcOpenShell 0.8.5，LENGTHUNIT=IfcSIUnit/MILLI/METRE，scale=0.001，37 个 strict furniture_group、95 个 IfcFurniture、11 个 IfcWall、6 个 IfcDoor、0 个 IfcOpeningElement、0 个 IfcRelVoidsElement、0 个 IfcRelFillsElement；inventory 同时发现 bim_acceptance.ifc 等普通 IfcGroup 样本，其 ObjectType 不是 furniture_group，不进入候选。
- **Invariants：** selection 不使用 filename、group name、layer、普通 IfcGroup 或旧 fallback；原始 tessellation/placement 的毫米值显式乘 0.001 转为米；placement 应用于设计审计 bbox；SVG JSON 只比较 frame/unit/group membership/plan geometry 等 canonical 2D keys；3D/Z/clearance/barrier 不由 SVG 验收。
- **Failure cases：** 主样本没有 opening/void/fill relation，故 wall/opening barrier 为 not_available；ordinary-group acceptance 样本不能伪装成家具组；把 raw millimetre tessellation 当 metre 会产生数量级错误；derived SVG 不能作为 independent adapter acceptance。
- **Decision rule：** IFC parse 证据可批准为 primary 3D/Z/clearance geometry audit；opening barrier、shared authored member 和 independent SVG adapter acceptance 暂缓；SVG 仅作为 derived 2D oracle。
- **Observed result：** actual IFC parse 成功，37/37 groups 严格通过 ObjectType 检查，主样本成员 GlobalId 为 95 unique（shared authored member=0）；follow-up inventory 逐样本保留 IfcGroup GlobalId、ObjectType、candidate_status 和 provenance，普通 IfcGroup 只作为 not_candidate provenance；furniture/wall bbox、placement 和单位记录在 follow-up evidence；canonical 2D SVG oracle 已生成，independent_adapter_check=false。
- **Parse command/result：** `pixi run python scripts/design/group_level/run_group_level_followup_probe.py --fixtures scripts/design/group_level/inferred_group_followup_fixtures.json --output docs/project/evidence/d6-inferred-group-design-followup.json --svg-output docs/project/evidence/d6-e10-bim-acceptance-svg-2d-canonical.svg --svg-json-output docs/project/evidence/d6-e10-bim-acceptance-svg-2d-canonical.json`；exit code 0，status 为 `real IFC4 parsed; strict furniture_group candidate audit complete`。
- **Unresolved question：** 需要带 IfcOpeningElement 或可审计 void/fill relation 的真实 IFC4 fixture；还需真实 shared-member 场景和独立 SVG adapter acceptance 才能关闭对应设计门。

### E10b：真实 IFC 与独立 SVG adapter

- **Hypothesis：** IFC 继续承担 3D、Z、clearance 和 wall/opening channel；独立 SVG 只有在经过现有 adapters/svg_scene.py 实际加载后，才能比较声明的 2D facts。SVG 不得补写 IFC 缺失的 opening relation，也不得声称提供 Z 或 3D clearance。
- **Candidate rules：** IFC audit 记录 opening/void/fill、门墙关系、shared member、多楼层和 Z compatibility；SVG adapter audit 比较 analysis frame、source/analysis unit、explicit furniture-group membership、plan geometry、representative status、center/area、raw/normalized gap、正面积 overlap、零间隙 contact、容差内 near、provenance/status；未声明的混合 channel 保持 not_available。
- **Fixture：** `e10b_independent_svg_fixture.svg` 是独立 authored SVG，含两个 `svg_group_alpha` members、一个 `svg_group_beta` member、一个 wall 和一个 explicit opening；通过 `load_svg_neutral_scene(... source_length_unit=m, analysis_length_unit=m)` 加载。它不由 IFC canonical JSON 派生。
- **Invariants：** adapter 的 source/analysis units、analysis plane、WCS、group_refs、geometry refs、object/geometry adapter provenance 必须可追溯；比较只限 SVG 声明的 2D keys；SVG capability flags 对 height/volume 为 false；door geometry 不转换为 opening relation。
- **Failure cases：** 主 IFC 仍有 0 IfcOpeningElement、0 IfcRelVoidsElement、0 IfcRelFillsElement，故 `actual IFC opening relation unavailable`；6 个 IfcDoor 只作为 door geometry 记录；derived E10 SVG 不计入独立 parity；SVG 的 Z、3D clearance、wall/opening barrier 均为 not_available。
- **Decision rule：** E10 opening gate 暂缓；E10b 的 independent SVG adapter parity 可在声明的 2D keys 上批准，但不能外推到 3D/Z/barrier；IFC 与 SVG 的不重叠能力继续分开报告。
- **Observed result：** existing adapter 实际加载成功，adapter version 为 svg-scene-adapter/0.4.0；group membership、三个 furniture center/area、A1/A2 raw gap=`0.4`、normalized gap、separated overlap/contact/near、representative status 和 provenance 均通过断言；另以五个轴对齐反例验证 edge-touch、corner-touch、positive-area-overlap 和 tolerance-near；opening count=`1`；independent_adapter_check=`true`；planar-only channel 明确排除 Z/clearance/barrier。
- **Unresolved question：** 需要带 IfcOpeningElement/void/fill 的真实 IFC4 fixture、带对应 authored 2D facts 的 independent SVG pair，以及 shared-member/多楼层 parity fixture；owner 仍需决定是否把 planar parity 作为独立 acceptance 门。

## E8–E10 逐项建议

| 实验 | 建议 | 理由与限制 |
|---|---|---|
| E8b 多成员聚合 | 需继续实验 | 已覆盖 witness、max constraint、all-pairs、excluded pair、split diagnostic、shared dependency、变换和缺失支持；不得默认最小 gap，all-pairs 也尚未被批准。 |
| E9 缺失传播 | 可批准当前 status 边界 | required formal channels 阻断 edge，external affordance 仅诊断；partial 下游消费仍未冻结。 |
| E10 IFC4 审核 | 可批准 IFC primary audit；opening 门暂缓 | 真实 IFC4 已解析且单位/placement 已核对；主样本缺 opening relations，door geometry 不等于 opening relation。 |
| E10b SVG adapter parity | 可批准声明的 2D parity；3D/Z/barrier 暂缓 | 现有 adapters/svg_scene.py 已实际加载独立 SVG fixture；只接受 frame/unit/group/plan/center/area/gap/正面积 overlap/零间隙 contact/near/provenance/status；一般旋转 polygon 语义仍未冻结。 |

## 推荐设计表（供总控独立复核）

| 设计面 | 本轮推荐 | 依据 | 保留限制 |
|---|---|---|---|
| candidate baseline | 先生成独立 pairwise relation graph；CC 只作 chaining baseline | E1 明确暴露链式合并 | 目标函数尚未决定，不能选默认 selector |
| candidate comparison | 同时比较 complete-link/max-span maximal cliques、hard partition options | E1 能表达长链、重叠和歧义 | 阈值、多尺度和长排语义未冻结 |
| 首轮 channels | 2D gap + 3D clearance + Z compatibility + barrier 分 channel | E2 证明单一 2D gap 会误纳 stacked/closed-wall | 3D mesh、route width、方向性 barrier 未覆盖 |
| shared member | 仅 diagnostic dependency；不生成 formal edge | E3 零 gap/overlap 不能区分依赖与新 membership | 后续模型能否使用非充分支持未决 |
| status policy | partial/missing 保留 relation 但不可支持 edge；invalid 仅 diagnostic | E4 保留 status 和失败原因 | partial graph 的下游消费未决 |
| representative | additive support + pairwise overlap observation；union 延后 | E5 得到 `8 / 2 / 6` 三个不同量 | 多重 overlap/holes/self-intersection 未决 |
| output expression | schema 允许 hard partition、overlap、unassigned、ambiguous | E6 避免强行单一答案 | production 首 slice 输出政策未冻结 |
| IFC/SVG | IFC 主验收；SVG 只做 canonical 2D oracle | E7 2D exact parity，3D capability 分开 | fixture 文件、tolerance、负责人需 owner 签名 |
| trend use | 首轮 membership 禁止 trend/frame/coherence/strength | 防止同一方向证据循环自证 | 后续若启用需独立目标和证据 |

## 自评与停止门

本轮完成了 E8b 的数值验证、失败案例、witness/excluded pair 和 disconnected split diagnostic，以及 E10b 的现有 SVG adapter 实际加载、2D 对照和 contact/overlap/near 轴对齐反例。设计 probe 只验证 synthetic computational properties 和声明的 adapter 事实；它没有心理效度、Bayesian prior、真实准确率或 production API 含义。没有修改 `features/`、`adapters/`、正式测试、IFC/SVG 生产路径或 production API。

独立复核保留四项设计限制：多成员聚合政策尚未冻结；主 IFC 缺少 opening/void/fill relation；真实样本未覆盖 shared authored member，shared dependency 仍由 synthetic fixture 验证；SVG parity 只覆盖独立 planar facts，不能关闭 3D/Z/barrier 门。它们是后续设计门，不改变本轮 evidence 的状态语义。

验证命令和结果由总控 session 独立复核：JSON 解析、现有 group-level probe 断言、本 probe 断言、`git diff --check`、范围审计。复核完成前不进入下一阶段。

**STOP FOR DESIGN REVIEW**

实验由我自行设计、执行、验证并先自评，不要求用户操作软件、运行脚本、标注场景或参加实验。用户意见只用于设计决策，不作为算法输入、训练标签或心理效度证据。未获下一阶段授权前保持 STOP FOR DESIGN REVIEW。
