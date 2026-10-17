# B3 空间场交付设计记录

- 日期：2026-10-09
- 状态：有界 synthetic comparison 与 connectivity comparison 已接受；历史 band diagnostic 保留。Owner 已批准 [conditional field handoff and physical occupancy plan](b3-space-field-handoff-and-occupancy-plan.md) 的顺序路线，Package A 已 OWNER ACCEPTED（fixed datum0 / eye1.6 / world-XY conditional discrete delivery）。[B1 native facts](evidence/b3-native-source-qualification.md) 已完成（21 focused tests passed，collector exit 0，13 records，无 source/item failures），owner 已按 final note 的 transport/material 限制接受。原始索引断开不证明 physical gaps，float32 multiset inequality 不证明 material loss。Owner 已查看全部五张 final PNG，接受 [frozen-capture identification views](evidence/b3-unresolved-source-identification-views.md) 用于识别对象，无需继续 rendering 或 verification；图中没有赋予 material semantics 或 whole-object envelope。Owner 已接受通用 selected-domain boundary 规则和 `run_20261009T083535Z_c914e2`：被确认的门、窗及类似 infill 按封闭分析边界处理，不产生 interior occupancy 或 uncertainty。Door #6231 的 unresolved qualification 仅保留为历史原始 source evidence；B2 未 promoted。Owner 将 counter #1992252、Assembly A (#2032485/#2053009/#2082638) 与 Assembly B (#3269286/#3237875/#3236022) 排除于 furniture-level analysis，但其 physical volume 必须参与 occupancy 与下游 free-space analysis；source facts、原始 meshes、A 与 immutable field/source packages 均保留。此前已接受的 2D display hull package 保留为历史；2D-only route 误读了用户要求的维度。最新要求明确为三个真正闭合的 **3D 凸包 mesh proxies**，每个完整 assembly/object 独立以全部 full-height world-XYZ vertices 执行已安装 SciPy 1.17.1 ConvexHull，不能把 XY hull 挤出为 prism。已交付三份普通 OBJ triangle meshes、3D original + translucent hull/facets preview、metadata/manifest/execution，见 [3D proxy evidence](evidence/b3-unresolved-source-identification-views.md) 与 `outputs/design/b3_deferred_convex_meshes/run_20261008T225203Z_aa8aaa/`，owner 已审查 script、final preview、execution 与 mesh metadata 并接受三个 ordinary closed 3D convex meshes 及其 XYZ hull、outward/incidence/positive-volume evidence、compact OBJ export 和 original source association。用户选择的 convex approximation 刻意填满 internal gaps/concavities，三份 mesh substitutes 现通过 `run_20261009T091601Z_242b33`（OWNER ACCEPTED）作为 occupancy-only 障碍参与空间场；counter 和 plants 均不参与 furniture/group/trend/orientation/affordance analysis。Exit 0；tetrahedron + interior point self-check、exact membership、outward winding、每条 edge 两个 incident faces 与 nonzero volume checks 通过，但不认证 original exact physical material 或 world completeness。无需新增 registry/framework/production contract。B3 仍为 OPEN。

## 已接受的方向

B3 的最终交付必须是空间场，或可审计的离散近似（可查询或带坐标、值和 mask 的样本）。多边形只能作为构造、检查和追溯的中间表示；仅完成多边形差集不能关闭 B3。空间场不能被一个含义不清的“自由/支持”总分替代。

当前接受的起点是：保留 3D 源几何和高度语义，先做探索；主分析平面规则已确定：IFC storey-bound datum + eye-height offset；本来源 datum 0 m、当前 eye offset 1.6 m，故主平面为 world z=1.6 m。有界 synthetic stage 1–3 comparison 已完成，owner 已接受其 diagnostic evidence，包括 connector、point-contact 和 directional reconstruction discrepancies；未选择 production resolution。实际来源的 partial diagnostic 已交付 review，仍需后续字段与生产决策。

Package A 的最小 production reach 仅为一个显式选择 lattice 的 validated dict loader、一个 focused test file 和普通 Python consumer 检查；不新增对象模型、query engine、CLI、依赖或默认 resolution，也不修改 live `_analysis_domain_handoff` 的 `formal_field=not_available`。A acceptance 后已授权 B1：先核对 frozen IFC length/SHA，再检查 13 个 exact STEP/GlobalId/Body/item refs 的原始索引、Closed、mapped lineage、placements/units、native/capture transport 与 source-semantic blockers。仅运行新 B focused tests 和 targeted collector，实际失败可修复；不运行 full importer/tessellation、旧 audit、repair、section/solid engine、Blender、field regeneration 或 dependency/Git/agent/chat 操作。最终 completeness 仅面向 frozen qualified imported inventory/domain，不要求 exhaustive world completeness。完整条件、逐源分支、consumer contract 与停止条件以 continuation plan 为准。

Package A 实现为 [`features/discrete_space_field.py`](../../features/discrete_space_field.py) 的 `load_discrete_space_field(package_dir, *, spacing_m, origin_offset_m)`，返回原始 field metadata、selected variant、source sections 和 manifest dicts。Sibling payload hashes、显式 lattice、height/provenance、tri-state/missingness 校验失败时抛出错误，不生成 empty result。新 [`test/test_discrete_space_field.py`](../../test/test_discrete_space_field.py) 最终 **50 passed in 2.12 s**；一次普通 Python real consumer 成功读取 0.25 m/[0,0] 的 **3888 samples / 3323 in domain / 3015 conditional empty / 308 unknown / 565 outside** 和 **358 source records**，两份 payload hashes 一致，未导入 `scripts.design`。完整记录与 runnable consumer 见 continuation plan。Complete physical clearance 仍全为 null；原始 artifacts、live status 和 exported model shape 未改。

## 已确定的分析平面与诊断限制

Exact eye-plane contract 是主分析规则。现有 1.55–1.65 m eye band 仅是 comparison evidence，不能替代 world z=1.6 m 主平面；lower-height 与 overhead queries 仅作 auxiliary diagnostics，不是竞争分析平面。历史 synthetic open-interior section 的严格条件 `z_min < plane_z < z_max` 排除 exact top/bottom face；新增 actual-mesh 路径在固定 z=1.6 上计算原始 indexed triangle edge intersections，vertex/coplanar contact 保持 unresolved。[PRIMARY eye-plane evidence](evidence/b3-primary-eye-plane-field.md) 提供有条件资格化的真实 subset，完整 physical occupancy 仍不可用，且不认证 exact arithmetic。上述几何层不建立 body envelope、sightline visibility、perception、walkability 或规范性人体测量标准。

地面参考采用与 IFC STOREY 概念关联的 slab surface；所有分析高度从已资格化的 level elevation 加 offset 得出，几何 slab z 仅供 audit。实际来源的 Level 1 datum 已由人工确认为 analysis world z=0.0 m，参考基面为地板上平面，当前已确定的 1.6 m eye offset 对应主分析平面 world z=1.6 m。Synthetic fixture 明确 authored elevation 为 0.0 m，附带 units、frame、source role，绝不声称已资格化实际 IFC。Comparison band 总厚度默认为 0.10 m。脚本 `--floor-datum` 配置 synthetic level elevation；`--eye-height`、可选 `--eye-band` 均使用相对该 datum 的 offset。未显式覆盖 band 时，调整 eye offset 会同步移动 band。

Coordinate projection/support frame 与 analysis reference/query 必须分开。已确认的 live S3 是 B4 world XY datum0 cut1.5 的横向 scope；eye1.6 查询不会自动重建或重新确认其范围。[已完成的 source qualification](evidence/b3-space-field-source-qualification.md) 记录 Level 1 `IfcBuildingStorey #13`（`2udSq8mkbQwxg0XrW$uM_r`）的 `Elevation=None` 且 `ObjectPlacement=None`；`IfcSlab #4884` 由 containment relation `#3556490` 关联，source unit scale 为 0.001 m/source unit。Storey-bound 0.0 m datum 和地板上平面 reference 是明确的人工确认分析输入，不是已写入的 IFC property 或几何 fallback；未修改源文件。Slab placement world z=-0.3 m、mesh top 约 0 m 仅作 audit。后续 [frozen capture qualification](evidence/b3-real-source-capture-qualification.md) 已验证 38 个历史结构记录和 354 个 actual Body meshes；capture 阶段的 complete occupancy 与 exact section unsupported assessment 保留为历史证据；新 conditional subset 不建立完整 occupancy 或 S3 vertical extent，当前 live S3 binding 未再次核验。禁止 slab extrema 或 scene bounds 的纯几何替代，原有 S3 horizontal scope/projection evidence 保留其原始用途。

Canonical 脚本为 [`scripts/design/space_field/run_b3_space_field_exploratory.py`](../../scripts/design/space_field/run_b3_space_field_exploratory.py)。本轮 stage-3 synthetic 证据为 `outputs/design/b3_space_field_exploratory/run_002/result.json`，见 [sampling comparison note](evidence/b3-space-field-sampling-comparison.md)。历史 `b3_eye_height_baseline/run_001` 保留但未接受，本轮也不关闭 B3。

## 分阶段路线、依赖和验收证据

### 1. Synthetic eye-reference revision

无额外阶段依赖。交付带单位的 3D synthetic fixtures：显式 authored level elevation、历史 synthetic eye-offset sensitivity、open-interior horizontal section、positive-overlap 对照，以及 lower/overhead queries。保留完整 absolute source z 范围、相对 offset/absolute query heights 和 band/projection provenance。

验收证据：empty、fully occupied、vertical obstacle、low/high blocker、overhang、narrow gap、touching/point contact、disconnected pockets、missing/invalid 的 fixture manifest。过滤前先验证 obstacle list、非有限高度和几何；valid empty 必须与 missing/invalid 分开。补齐冗余 overhang、完整 sensitivity variants、holes/source geometry/provenance、narrower support 与 wider canopy 的证据。

### 2. 中间几何和原始场通道

依赖阶段 1。交付按高度带生成的 domain、boundary、occupancy polygon 中间物，以及可查询场或完整样本。保存 holes、source geometry/id、provenance、status、missingness、query、spacing、origin 和算法版本。

至少并行记录 domain mask、occupancy/blocker mask、occupancy clearance、独立 boundary clearance，以及诊断性的 group-support Gaussian。保留 clipped/raw area 的区别；Gaussian 使用固定物理 bandwidth 做比较，但不把它升级为生产常数。不能把缺失输入编码为空场、零值或有效空 obstacle list。

### 3. 分辨率、原点和几何连通比较

依赖阶段 2。把 Shapely/vector floating-point 几何参考与多种 scene-relative resolution、origin variant 的采样结果并列。这里的“几何参考”不是 certified exact arithmetic。

证据必须包含 mask、面积、净空、component、narrow-gap、point-contact 和 touching 的变化，并保留 query/spacing/origin。分别报告 open-interior geometric connectivity、sampled 4-neighbor adjacency、sampled 8-neighbor adjacency；这些都不是 route、walkability 或 accessibility 结论。观察到的敏感性只阻断受影响的稳定性主张，不阻断整个实验。

`run_002` 在 short bounding extent /8、/16、/32 的 spacing 下分别保留 zero/quarter-spacing shifted origin 的完整 indexed point samples；10×8 m fixture 的 spacing 为 1.0、0.5、0.25 m。Integer lattice bounds 包含 shifted origin 对应的负 index。Plane 与 band 使用同一 domain 和固定 2.0 m physical Gaussian bandwidth，保留各自 masks/clearances/topology 与共享坐标 mask disagreement。Point-center 面积估计非 conservative；重构 center-labeled cells 仅用于诊断，clip 到含 holes 的 exact domain，并单独报告 symmetric difference、false-free、false-occupied 与未覆盖 domain 面积，防止 signed area error 抵消。8-neighbor 使用全部 diagonal adjacency，无隐含 corner-cut filter。Boundary clearance 包括 domain holes；occupancy clearance 保留已有 raw height-qualified mass 距离语义（包括 domain 外质量），两者为并行诊断。

### 4. 实际 domain 和输入资格化

依赖前述 synthetic 证据足以暴露真实输入问题。建立 actual domain、furniture/context occupancy、source revision、floor datum、单位和 analysis frame 的资格化记录。B4 S3 记录的用户确认面积为 **206.520923482 m2**，有两个结构洞；B4 capture 只有 structure，不能推定家具存在，因此尚不足以资格化 B3 occupancy。

证据包括 source identity/revision、domain capability、各 channel status 和未解决限制。没有合格 analysis domain 时，field、free-space 和 topology 必须保持 `not_available`；scene bounds 不能代替 domain。

### 5. Manifest 和 Blender 检查

依赖 manifest 已序列化。manifest 至少包括 source/revision、units、analysis frame、floor datum、height queries、geometry refs、raw channels、masks/samples、status、missingness 和算法版本。只使用批准的 portable Blender：`D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe`。

验收证据是 source overlay 与 derived overlay 可区分且可追溯。Blender 只是输出检查面；manifest 成功不等于 Blender runtime 已执行，也不等于场语义正确。

### 6. 字段决策和最小 handoff

依赖阶段 1–5。基于证据由 owner review 审查已确定眼高平面上可靠 real-mesh occupancy 的缺口、missingness/status、projection/geometry capability 与 domain/boundary 参与规则和最小 production handoff；再运行受影响的 checks。只有存在 field 或可审计离散证据、provenance/missingness 可查、几何连通与采样邻接已分开，且这些决定完成 review，B3 才可关闭。

不要求用 full block、heterogeneous graph、route 或 Bayesian 实现来关闭这个有界 B3。

## PRIMARY exact-height discrete field 交付

新增 design-only [`run_b3_eye_plane_field.py`](../../scripts/design/space_field/run_b3_eye_plane_field.py) 使用 frozen actual Body meshes 与固定 world z=1.6 m，保留历史 S3 面积 206.5209234821732 m² 和两个洞。完整 indexed samples、source sections、数值 gap 与 connected-shell audit、fresh output 和批准 Blender inspection 见 [证据记录](evidence/b3-primary-eye-plane-field.md)。本次检查 A immutable index 全部 366 entries；历史 B attempts 和已接受 synthetic `run_002` 保留原始用途。

353 个 non-slab meshes 中：34 个 conditional qualified sections、306 个可证明 plane-empty、13 个 open/nonmanifold unresolved。15 个退化 chair meshes 完全低于眼高：保留 `source_geometry_status=invalid_degenerate_mesh`，同时记录可证明的 plane-empty，不删除 triangle。34 个 qualified sources 共 67 个原始 connected shells：26 个单 shell sources、3 个 walls 分别为 2/4/5 shells、5 个 doors 各有 6 shells（2 个 crossing、4 个低于 plane）；其 plane interiors 未检出 nesting 或 positive-area overlap，原始 signed volumes 全正。Orientation 仅作 audit；有交叠或嵌套的 compound interiors，无论朝向，均为 unknown，不推定 XOR、physical union 或 cavity。仅对已审计的 disjoint plane interiors，在每个原始 shell 内 deduplicate ray hits，再合并 component parity；由此修复 5 个 doors，保留原 whole-object failure probes。任何 component vote disagreement 仍为 unknown。

Qualified raw area 为 22.392615629752758 m²，S3-clipped subset 为 0.014987329164664116 m²，clipped unknown support 为 19.069186870135574 m²。0.5/0.25 m spacing 各含 zero/quarter-spacing shift，四个 lattices 均未命中极小的 positive subset。Samples 保存 true/false/null occupancy、unresolved source ids、boundary ambiguity 与独立 domain-boundary/raw-subset distances；false 仅表示当前条件下的 empty，complete physical clearance 为 null。两张 PNG 已实际查看，Blender exit 0；独立 `.blend` 未交互重开。Owner 已接受该有界 conditional qualification 与 localized unknown；下一步为 primary-plane geometric vs sampled connectivity（保留 unknown），之后决定 minimal field handoff。本 package 无进一步实现，仍不关闭 B3。

## PRIMARY eye-plane connectivity 有界比较

新增 design-only [`run_b3_eye_plane_connectivity.py`](../../scripts/design/space_field/run_b3_eye_plane_connectivity.py) 只读取 owner-accepted `run_20261008T211817Z_095de3` serialized field/source sections，保留 world z=1.6 m、历史 S3 两个洞、tri-state masks、per-source boundary ambiguity、positive-over-unknown 和原 sample IDs。新 [connectivity evidence](evidence/b3-primary-eye-plane-connectivity.md) 记录独立 geometric open interiors、4-neighbor、unrestricted 8-neighbor，以及 membership、missed/merged/split、unassigned boundary samples 和诊断 edge crossings/contacts。未知 samples 不成为 graph vertices；诊断不滤除 graph edges。

S3 comparison 使用已接受的 serialized S3-clipped occupied/unknown targets，不再次 clip raw geometry。Owner 已确认这一选择在 scope 内；raw geometry 仍保留原 audit/distance 用途。最初 raw-difference attempt 的 per-source interior boundary residual 与原始 error/null reference 保留，不能声称两条 floating-point 操作路径 certified identical；guard 未删除，也无 tolerance/repair。Point-center 面积非 conservative，clipped cells/directional differences 只作 diagnostics。Focused 新 test file 含 corner-tangent domain boundary contact regression；不扩展 production interface 或实现 handoff，不关闭 B3。最小 step-6 讨论仍为 serialized conditional tri-state samples/provenance/status handoff，connectivity 独立保留为 diagnostics，待 owner 决定 consumer、boundary/unassigned exposure 和 adjacency。

**OWNER ACCEPTED**：final run 为 `outputs/design/b3_eye_plane_connectivity/run_20261008T214917Z_5c7dab/`。Owner 已审查 runner/tests、final counts/memberships、directional areas、edge diagnostics、final PNG 和 completed evidence；acceptance 以已接受的 serialized S3-clipped targets 与 floating-point open-interior reference 为条件。Conditional-empty geometric component 只有一个，面积 187.43674928287297 m²。四个 lattices 的 geometric/4/8 counts 为 1/1/1、1/1/1、1/2/1、1/2/1；0.25 m 的 4-neighbor membership 分别为 3014+1 和 2975+3，属于同一 reference 的 sampled split，不是 vector isolated pocket。全部 7482 conditional-empty vertices 每种 adjacency 的 memberships 已核对；missed/merged/unassigned 均为零。8-neighbor count 相同仍保留 unknown/hole/domain-boundary crossings/contacts，不能据 count 宣称稳定。Final affected focused tests 为 11 passed，runner exit 0；两个 completed PNG 各看一次，final 图修正 subplot padding。Interrupted slow attempt、raw-reference unavailable/original residual/error 和 rendering history 全部保留，细节见 evidence。Unrestricted 4/8 adjacency 和 reconstructed cells 不提升为 production topology、routes 或 certified empty cells。Ruling 后只更新文档，无进一步实现或 reruns。**OWNER ACCEPTED — B3 OPEN；下一步与 user 讨论 stage 6 field contract/minimal handoff。**

## 历史实际来源 band partial diagnostic 交付

主分析平面为 world z=1.6 m。现有 attempt labels（包括 `provisional_eye`）保留为历史 diagnostic metadata，未因标签变更而重新生成。[Attempt 004 evidence](evidence/b3-real-source-field-diagnostic.md) 保存 eye `[1.55, 1.65] m` 与独立 lower `[0.45, 0.55] m` 的完整 indexed samples：0.5/0.25 m spacing，各含 zero/quarter-spacing shifted origin。历史 S3 面积 206.5209234821732 m²、两个洞和原始精度保留；源 meshes 已是 world metres，不做第二次缩放，slab support 不参与 occupancy，canonical Analysis policy 不变。

每个 query 保留 189 个 eligible-mesh diagnostic projection records（包括 valid-empty helper result）与 164 个 unsupported records。与 A 完全一致的 positive-area in-scope unsupported candidates 为 eye 10、lower 72。Complete occupancy、exact section、known-free 和 complete occupancy distance 保持 null；actual XY vertex hull 仅表示 conservative uncertainty support，不是 occupancy。Raw diagnostic projection distance 与 domain-boundary distance 均以 metres 独立保存；无 qualified group，因此 Gaussian 为 not_available。

Eye clipped approximation 仅 0.014987329164664116 m²，四个 lattices 都没有命中 projection；GEOS directional reconstruction failure 保留 actual error 与 null/not_available，没有新 slicing backend、精度修复或 area-only retry。Lower clipped approximation 为 10.70892965338737 m²，其 vector complement 为两个 components，四个 4/8-neighbor sampled complements 都为一个；lower symmetric reconstruction error 为 2.0889273192694957–3.072677383046719 m²，reference 只是同一 approximation，不是 physical truth。

Derived union 记录 input/union/output validity、geometry/leaf types 和 area delta。本次 union 没有使用 `make_valid`，没有移除 nonpolygon components；重复 polygon union 的 3.55e-15/1.07e-14 m² floating-point delta 原样记录，raw per-source geometry/provenance 保留。批准的 portable Blender 5.2.0 LTS exit 0，生成三张 source/query PNG 和独立 `.blend`，另有三张 Matplotlib PNG。六张图均已实际查看，agent inspection 不代表 owner acceptance；partial diagnostic 不关闭 B3。

对 unchanged lower complement 的 focused inspection 得到两个 component areas：195.81199198035506 m² 与 0.0000018484299999996234 m²（约 1.84843 mm²）。因此 2-versus-1 count discrepancy 包含 microscopic sliver，不能据此声称有 material isolated pocket；未设 tolerance、修复几何或重新生成 field/render。

## 明确保留的后续决定

不冻结 normative anthropometric standard、body size、route width、final resolution、stability tolerance、production API、user-facing label 或 Bayesian prior。Bayesian 对比仅是原始通道可检查后的可选 design-only follow-up，不是 promotion 或 acceptance item。也不把历史 diagnostics 改写为 passed。

## 当前事实与限制

[`d6-b4-live-blender.md`](evidence/d6-b4-live-blender.md) 是已有证据记录，不代表当前 live state 已再次核验。架构边界见 [`indoor_layout_evaluation_matrix_architecture_memory.md`](../indoor_layout_evaluation_matrix_architecture_memory.md)；多层方向见 [`d6-multilayer-space-field-block-graph-design.md`](d6-multilayer-space-field-block-graph-design.md)；输入资格和缺失传播见 [`space-field-ifc-neutral-scene-input-contract.md`](space-field-ifc-neutral-scene-input-contract.md)。两份 B3 文档互相链接，探索计划中的 staged route 是本记录的英文对应说明。

## 3D proxy acceptance 与 occupancy-only handoff

三份 3D convex mesh 的 geometry generation 已完成并获 owner 接受。Owner 已明确 physical occupancy 与 furniture eligibility 独立：三份已接受的 proxy 必须作为七个原 source 的 occupancy-only 替身参与下游 free space；counter 和 plants 均不参与 furniture/group/trend/orientation/affordance inference，不再等待参与决策。此前 2D artifacts 作为历史保留。Original source limitations、accepted A 与 B1 不变；B3 仍为 OPEN。

## 历史 3D convex proxy comparison-only package（OWNER ACCEPTED）

已生成独立可由现有 A loader 读取的 v1 比较包：`outputs/design/b3_proxy_eye_plane_comparison/run_20261009T074009Z_ff323e/`。现有 358 条原始 source records/errors 完整保留，追加三条 proxy records；仅三份已接受的普通 OBJ 在 world z=1.6 m 用现有 `section_source` 新做切片，均为 `qualified_closed_section`。比较情景只对被三份合格 proxy 代表的七个原 source ID 去除 uncertainty contribution；测试覆盖 qualification failure 回退和已证明 plane absence 的覆盖条件。五项 focused tests 全部通过，runner exit 0，现有 A loader 已读取新包，0.25 m / [0,0] 左右对照图已检查。Owner 已审查并**接受此有界 comparison-only package**；此接受不代表 canonical enrollment，也不授权 B2。

该 lattice 的 baseline 为 outside 565、conditional empty 3015、unknown 308、occupied 0；proxy comparison 为 outside 565、conditional empty 3054、unknown 0、occupied 269。308 个原 unknown 中 269→occupied、39→conditional empty。S3-clipped occupied area 从 0.014987329164664116 变为 16.359239442311818 m²；unknown-support area 从 19.069186870135574 变为 0.020499982357023327 m²。Door #6231 的原始 unresolved 状态及局部 uncertainty support 保留；全部四个 lattice 都没有 sample 命中这块剩余 support。因此 sampled unknown 为零是采样遗漏，不表示 door 已解决或 occupancy 已完整。五个外侧窗原始记录不变。Proxy 是用户选择的 3D 凸包近似，会填充原始空隙与凹处；不证明原始材料体积、植物方向或 complete physical clearance。所有 proxy 的 canonical enrollment 仍为 `deferred_excluded`，complete occupancy/clearance 继续为 null，B3 仍 OPEN。

共享 NeutralScene 与 B3 comparison 现使用同一个 exact-identity resolver。用户确认的 [S3 boundary membership declaration](evidence/b3-domain-boundary-membership.json) 绑定已接受的 scope/source revision 和 source-sections hash；Door #6231 的 ID 只作为 input membership data，不是算法中的 STEP-number 或 class 分支。被精确声明为 selected-domain boundary member 的门、窗及类似 infill 按封闭分析边界处理，不贡献 interior occupancy 或 interior uncertainty；原始 source facts 和 qualification errors 保留。

Owner 已接受的新 comparison package 为 `outputs/design/b3_proxy_eye_plane_comparison/run_20261009T083535Z_c914e2/`，保留前次已接受 package 作为历史。现有 A loader 已读取，preview 已检查，七项 B3 focused tests 与 65 项 NeutralScene regression tests 通过。358 条原始 records/errors、S3 几何、四种 lattice 的 status counts、domain masks 和 boundary distances 不变。0.25 m / [0,0] 为 outside 565、conditional empty 3054、occupied 269、sampled unknown 0；clipped occupied area 仍为 16.359239442311818 m²，active clipped unknown support 从 0.020499982357023327 降为 0 m²。Door 的原始 unresolved 状态仅保留为历史 source evidence；非 boundary member 的 uncertainty 不变。七个 proxy overrides 仍仅用于 comparison，canonical enrollment 仍为 `deferred_excluded`。不声称 complete physical occupancy/clearance；B2/live promotion 未改变，B3 仍 OPEN。

## 当前 occupancy-only handoff — OWNER ACCEPTED

用户已确定通用不变量：physical volume 必须进入 occupancy 和下游 free-space analysis，与 furniture eligibility 独立。`outputs/design/b3_occupancy_only_handoff/run_20261009T091601Z_242b33/` 使用三份已接受、已资格化的 3D convex proxy sections，各一次替代七个原 counter/plant sources；counter 与 plants 均不参加 furniture/group/trend/orientation/affordance analysis。现有 A loader 已读取该包。0.25 m / [0,0] 下为 occupied 269、conditional empty 3054、outside 565；clipped occupied area 16.359239442311818 m²、unknown support 0 m²、conditional free area 190.1616840398615 m²。先前接受的 comparison 为历史；原始 source errors 与独立的 boundary-member 规则保留。127 项 focused tests 通过，final generator 与 loader check exit 0。不声称 complete physical occupancy/clearance；B2/live formal_field 未 promoted，B3 仍 OPEN。
