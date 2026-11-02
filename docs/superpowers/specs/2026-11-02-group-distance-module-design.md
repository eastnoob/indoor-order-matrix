# 家具组距离计算模块设计（frozen for implementation）

Date: 2026-11-02
Status: **Frozen for implementation, 2026-11-03; production implementation and real IFC visualization pending**

本草案定义一个可被多个证据包复用的家具组距离计算模块。它本身不是证据包：只计算并报告距离，不替消费者把距离转成支持度、势、衰减、强度或归属。首版同时保留质心直线距离与自由空间约束的质心混合距离。

2026-11-02 的独立审阅覆盖了输入接缝、固定端点、接入格资格、网格接口代理、Dijkstra 路径语义、并列规则和状态优先级；本次 owner grill 又把确定性路径恢复、来源回溯、全量组对对账和峰值内存记录补成了明确的实现门。2026-11-03 owner 已按用户授予的文字 spec acceptance 权限接受修正后的设计和 readiness；真实 IFC 运行及用户视觉审阅仍属后续实现验收。

## 1. 目标和边界

模块回答两个家具组在同一分析平面中相隔多远，以及在当前离散自由空间里是否存在连接两组的最短路线。它应当：

- 把每个家具组作为一个整体；成员家具只用来构成组几何与物理占用，不单独输出距离关系。
- 在完整合格组范围内为每个无序组对计算关系读数。组对只是查阅地址，不是配对、聚类、同组判断或归属边。
- 复用场景提供的 `AnalysisPlane`、预解析物理占用和现有 `FreeSpaceField` 网格；不另造场景、障碍物、自由空间或独立网格。
- 保留每种距离及其来源、状态、单位、网格参数和算法版本；不把不同距离压成一个分数。
- 允许势包或其他消费者选择是否使用距离。消费者拥有自己的规则；距离计算不依赖势包启用。

此模块不定义人的身体宽度、可通行性、家具组边界、距离衰减、近远阈值、距离归一化、跨包融合或势包的距离条件函数。当前 `FreeSpaceField` 是投影占用判断，不等于经过人体净宽校验的真实行走空间。

## 2. 现有基础和缺口

- `features/free_space_field.py:FreeSpaceField` 在既定 frame/domain/grid 上查询单元是否被解析后的物理几何占用；按正面积交叠判定占用，并保留已知、条件、未知、域外、无效和不可用状态。它不计算邻接、连通或最短路，也没有公开网格元数据/域几何读取接口。当前只要存在 accepted substitute，FreeSpaceField 可能把全场 free sample 标为 `CONDITIONAL`；存在 unresolved occupancy source 时，当前实现会保守地把所有未被已知实体占用的 cell 标为 `UNKNOWN`，不提供局部 unknown footprint。
- `features/geometry_views.py` 提供既有平面投影；`features/neutral_scene_views.py` 解析物理占用来源。占用与家具资格独立，墙、柱等实体若进入物理占用也会阻断路线。
- `features/scene_evaluator.py:_sampled_bfs_distances` 与 `features/affordance/grid_backend.py` 有旧的 4 邻域 BFS/网格连通实现，但其栅格阈值和输入不是本模块要复用的自由空间语义，不能拿旧距离代理冒充新距离。
- Pixi 已锁定 `networkx`。搜索后端不限制实现语言：可由 Python 调用 C/C++，候选包括 SciPy/igraph 稀疏图核、`python-tcod` 与 Boost.Graph。首版已选 installed NetworkX 3.6.1；`heapq` 及原生候选只在实际基线失败后重新裁决。接入格有不同初始代价，可由虚拟源边或带初值的多源接口表达；不得把它们全设为零。隐式邻接是节省内存的实现偏好，不是距离语义约束；显式稀疏图可纳入实测比较。当前没有指定 IFC 性能基准，不声称任何候选更快，也不增加依赖。
- `EvidencePackage.evaluate(source_envelopes)` 当前没有组几何或自由空间场接缝。本设计不改变这个共享签名。底层距离模块应接收由同一次 scene-view 解析得到的显式只读输入，并返回有类型的 pair distance observations；将来若证据包要消费它，由包侧 adapter 映射到既有 `FieldResultEnvelope` / `EvidenceChannelRecord`。当前不存在通用输入 adapter；指定 10500 IFC 已有 S4 确认域，但仍没有已构建的可复用 `FreeSpaceField` 实例或冻结生产网格。该 IFC 将来的网格必须由同一 IFC、同一分析域和经审阅的网格参数建立，不能借用独立 B3 inspection 网格或隐式另选分辨率。距离模块自身不是证据包。

算法参考： [Dijkstra 定义](https://networkx.org/documentation/stable/reference/algorithms/shortest_paths/dijkstra.html)与 [NetworkX 多源接口](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.weighted.multi_source_dijkstra.html)。算法与实现库分开裁决；C/C++ 原生核与 Python 实现必须遵守相同距离定义。

2026-11-02 算法审查范围已扩展到 C/C++，撤回此前“采用 `heapq`”的过早结论。SciPy/igraph 可通过虚拟源保留浮点接入偏移，状态/来源可由 adapter 沿路径恢复；不能仅因这些不是库的原生输出而排除它们。`python-tcod` 接近现成隐式网格引擎，但整数代价需要另行审阅量化误差；Boost.Graph 可定制距离标签，却需要 C++ 图接口及调用边界。2026-11-03 guarded probe 已核验 NetworkX 3.6.1 的稳定并列恢复与 Windows/Pixi 接入并由 owner 选定为首版后端；没有添加依赖或执行 IFC 距离运行。完整记录见 [`distance-algorithm-package-review-2026-11-02.md`](../../project/evidence/distance-algorithm-package-review-2026-11-02.md)。

## 3. 查询身份和固定几何

### 3.1 查询范围

**2026-11-02 用户确认的前置规则：**先选定墙体围合区域，其在选定相机 `AnalysisPlane` 上的投影才是分析范围。初始 IFC 无 drawing camera、IfcSpace 或已确认域；现已在隔离工作区复用 Spec008 的 native drawing/camera 与选墙 B4/显式确认工作流，完成 S4 确认；不以楼板、家具包围盒或画布代替。现有 `_inferred_mesh` 已将完整 shell/holes 还原为 world SI support，request 再投影到选定 plane，不另作重复坐标变换。主树尚缺该依赖闭包，先按[相机与墙围合前置计划](../plans/2026-11-02-wall-domain-camera-prerequisite.md)完成有界恢复与真实输入验收，再推进距离实现；没有域不等于不可达。

一次距离计算绑定同一次 scene-view 解析得到的组整体投影、`AnalysisPlane`、预解析物理占用、自由空间 domain/grid、家具组 scope 和算法版本。显式输入须携带并校验 scene/source identity、plane/frame、linear units、domain identity/content fingerprint、grid origin/spacing/shape、occupancy/source fingerprint 和 group-geometry fingerprints；不可只凭 domain ID 认定几何相同。不得在距离模块内另选平面或静默重采样。网格矩形必须完整覆盖有效分析域；若 domain 缺失/无效、网格未覆盖，或网格/占用输入无法查询，混合距离状态分别为 `INVALID` 或 `NOT_AVAILABLE`，不得据此报告 `unreachable`。覆盖检查以网格外框几何完整 `covers(domain)` 为准。

S4 域接缝必须消费确认结果本身（当前产物为 `s4_confirm_result.json` 的 `analysis_domain`/`domain_geometries`），并同时校验 `s4_confirmed_manifest.json` 的 source hash、plane/frame、request identity、candidate identity 和 confirmed-domain identity。manifest 中指向的旧 `domain_result.json` 可能仍是 `status=not_available`、`analysis_domain=null` 的尝试记录，不能被距离适配器当作已确认域；若确认结果和 manifest 绑定不一致，先返回 `NOT_AVAILABLE` 并停止距离计算。历史 `ifc-world-plan` 的 pair artifacts 也不能充当 S4 camera-plane 结果。

距离适配器还必须显式冻结 `GridDescriptor`：`grid_id`、分析平面局部坐标中的 `origin`、`spacing`、`n_rows`、`n_cols`、row/column 轴方向、cell polygon 规则、domain content fingerprint 和 occupancy content fingerprint。`FreeSpaceField` 当前的 `query_context` 只校验 `domain_id`/`frame`，且 whole-height 查询要求 `plane=None`；这不足以证明一个旧网格与 S4 camera plane 相同。因而不能仅凭现有 `FreeSpaceField.evaluate` 接口接入距离。实现时必须由同一次 scene-view 显式产生并校验 `AnalysisPlane + GridDescriptor + occupancy fingerprint` 的 handoff，或增加只读元数据接口；任何缺失或不一致都返回 `NOT_AVAILABLE`，不得把旧 `ifc-world-plan` 网格静默套到 S4 组投影上。

输入 handoff 的 query fingerprint 还必须包含实际 `FieldQuery` 的 `domain_id`、`frame`、`plane`、`height_band`、`demand`、`tolerance`、`revision`，以及 `FreeSpaceField` 的 algorithm/schema version、`query_context`、unresolved source IDs、validated support hashes、occupancy source IDs 和 row/column index convention。距离首版要求 whole-height planar query（`plane=None`、`height_band=None`、`demand=None`），但仍要把这些字段写入 fingerprint 并校验；不能因“当前值为空”而省略它们。

当前 `analysis_scene_view` 可提供组投影组件、物理占用及 unresolved source IDs；`FreeSpaceField` 构造方持有网格参数和 domain geometry，但没有公开只读元数据接缝。通用距离输入 adapter 因而尚不存在。指定 IFC 的现有 retained axis/geometry 记录也不是可复用的自由空间网格实例。实现时由调用方在同一解析路径中显式组装 immutable input，或增加仅暴露所需元数据的窄只读接口；网格的 spacing/origin/shape 必须成为明示、可追溯输入，不得读私有字段、借用 B3 网格或静默重采样。该接缝及指定 IFC 网格来源都是实现前置项，不影响计算语义设计。

当前指定 IFC 回放输入仍为：

```text
outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc
SHA-256: 1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077
```

每次真实回放前须重新核验源路径、长度、SHA-256、IFC identity、单位和分析平面；不匹配即停止，不以旧缓存、新 IFC、SVG、模拟几何或预置距离替代。

### 3.2 家具组中心

对组的所有合格整体投影几何取 union，使用该 union 的二维几何质心 `c_g` 作为固定锚点。质心可能落在凹形组外部、组内部空洞或不连通组件之间；首版不将其吸附到边缘或另一个代表点，也不改成多个分量锚点，因为那会改变约定端点。不能建立有效面积投影或有限质心时，不补造中心；缺失输入属于 `NOT_AVAILABLE`，已提供但零面积、非有限或畸形几何属于 `INVALID`。此项是距离模块的明确规则，并取代占用/自由空间旧笔记中“质心不在组内时选 representative point”及“多组件组保留多个锚点”的建议；其他用途的锚点规则不在本 spec 内裁定。

如果组投影缺失，相关距离为 `NOT_AVAILABLE`；若投影存在但几何无效、面积为零或质心非有限，相关距离为 `INVALID`。不以 `PARTIAL` 捏造单端点距离。

欧氏通道和混合距离都引用同一个 `c_g`。如此定义使端点稳定；质心到边界的连接量是几何偏移，不声称家具内部可行走。

## 4. 输出的两种距离

### 4.1 质心直线欧氏距离

```text
D_euclid(A, B) = ||c_A - c_B||_2
```

它只读两个固定质心，不看墙体、家具占用、自由空间连通性或距离网格。单位采用分析平面的线性单位，IFC 回放统一转换并记录为米。它始终作为独立基准保留，不替代路线距离。

### 4.2 自由空间约束的质心混合距离

```text
D_hybrid(A, B) = min over access cells a,b of
    offset_A(a) + route_free(a,b) + offset_B(b)
```

该式定义 observed-free 图上的已知混合距离。Optimistic graph 另算的 lower bound 是不确定性诊断，不替代此距离，也不作为已知距离值。

- 组足迹格 `footprint_cells(g)` 是完整覆盖分析域内，同一网格中与“组投影 union ∩ domain”**正面积相交**的所有格子；其规则沿用物理占用的正面积口径。已知接入格是这些足迹格的 4 邻格中，`FreeSpaceField.evaluate` 返回 `ESTABLISHED/CONDITIONAL` 且值为 `False` 的格子。仅角点相邻不构成接入。每一个合格候选都参与，不先挑一个边缘格；按 `(row, column, shared_edge)` 稳定排序。
- 另行保留乐观接入候选：足迹格的 4 邻格中状态为 `UNKNOWN` 的格子。它们不能形成已知距离，但在 optimistic lower-bound 搜索中可暂按潜在 free 使用，以免把未知接入误报成不可达。`INVALID`、`NOT_AVAILABLE`、占用格及域外格不作为接入候选；若必需查询输入出现 invalid/unavailable，按输出状态表处理。
- 每个候选由“足迹格、自由格、两者共享的完整栅格边”唯一标识；离散接入点取共享边中点，明确称为**栅格接口代理点**。已知接入格必须同时满足：其样本为 `ESTABLISHED/CONDITIONAL + False`，且格心符合 observed-free 图的节点资格；未知接入格必须同时满足：其样本为 `UNKNOWN`，且格心符合 optimistic 图的节点资格。两类候选各自沿用对应路线图的资格规则，不能只因它邻接组足迹就作为接入。`offset_g(a)` 是质心到代理点的二维欧氏长度，加代理点到自由格格心的半格长度。两段只是端点几何修正，不是通行路径；首版不检查它们是否被分析域覆盖，也不检查其可行走性。若多个足迹格导向同一个自由格，仍保留各接入边，因为偏移可能不同。
- 占用、域外、`INVALID`、`NOT_AVAILABLE` 格不作路线节点。`UNKNOWN` 只作为 optimistic lower-bound 图的候选节点/接入格，绝不冒充已知 free。`CONDITIONAL + False` 可进入已知可用路线，但所选最优路径若依赖该类格，距离必须标为条件性 `PARTIAL` 并附其来源。`FreeSpaceField` 当前可能让全场 free samples 都成为 `CONDITIONAL`；必须按所选路径/接入实际依赖判状态，不以无关格子的条件状态污染该组对。
- observed-free 路线节点是**格心位于分析域内**且查询状态为 free（`ESTABLISHED` 或 `CONDITIONAL`）的格子。两个 4 邻接路线节点之间仅当连接其格心的线段被同一个精确分析域完整覆盖时才建边。由此排除域外格心及跨越凹边界/域洞的连接。占用状态按 `FreeSpaceField` 对对应格与 domain 交集的既有正面积规则读取。
- observed-free 路线只沿这些节点计算。optimistic 图沿用相同边规则，并额外将 `UNKNOWN` 格心作为潜在节点。首版使用 4 邻域，横/纵格心间边权是对应分析平面中的实际距离；规则方格为一个 spacing。禁止对角捷径和角点穿越。
- 距离取端点偏移与自由路线总和最小的接入组合。距离比较始终先比较未舍入的累计值；仅数值精确相等时，优先选择条件性格较少者，再按固定的组身份、row、column、栅格边顺序择一。组对按身份排序后固定方向计算，使选择不受输入记录顺序影响。不另算并列接入组合数或等长路线数。

这是“固定组质心 + 自由空间中段”的**离散网格近似距离**，不应命名或解释为连续自由空间中的精确最短路，也不是从质心到质心全程可通行的人行路线。它测量固定中心到离散自由网格接入边的端点偏移、格心图中的绕障距离以及目标端点偏移。网格分辨率会影响结果，必须随结果报告。不得把 `D_euclid` 混进 `D_hybrid`，不得用它替代无路可达的情况。

### 4.3 首版搜索算法

使用**加权 Dijkstra**。对稳定顺序中的每个源组，将其所有接入格心以对应 `offset_source` 作为虚拟源边权，一次求到自由空间图中所有可达格心的最短距离；再对每个目标组取 `distance[cell] + offset_target(cell)` 的最小值。网格边权非负；邻接图无向。一次源搜索可服务其余全部目标组，因此对 `n` 组最多按源组执行 `n` 次 Dijkstra，而不是每个无序组对单独跑 A*。对全部无序组对输出一条距离记录，而不是建立配对结果。NetworkX 可复用为图算法依赖，首版选用已安装的 NetworkX 3.6.1，不新增依赖；后续仅在实际 IFC 性能无法完成验收时，按同一数学/状态合同重新裁决后端。

首版后端选择与 arithmetic/tie 次序统一以 §4.4 为准；项目适配层在紧边 predecessor DAG 上恢复稳定代表，不能采用库的任意单一路径。组对按稳定身份固定方向；不加 epsilon、不修改物理边权。Dijkstra 只给定图上的最短解；它不证明连续几何最短。每个组对执行两种图查询：

1. **Observed-free graph：**节点/接入只含值为 free 的 `ESTABLISHED` 或 `CONDITIONAL` cells。求得的最短值为当前可计算路径。精确等长时优先选 conditional cells 较少者，再按上方固定顺序打破并列。若代表最优接入/路线经过 conditional cell，则该已知距离为条件性结果，状态为 `PARTIAL` 并记录依赖来源。
2. **Optimistic graph：**在 observed-free graph 上加入 `UNKNOWN` cells 和 unknown access candidates，按潜在 free 计算加权最短路，只作为下界诊断，不作为已知距离或路线。

若 observed-free 有路，输出其数值与分项；当 optimistic lower bound 比 observed-free 值低超过 `tau = max(ulp(D_observed), ulp(D_optimistic), ulp(grid_spacing))` 时，标 `PARTIAL`（unknown 可能改善最优距离）。两值差在 `tau` 内视作数值并列；unknown 只能形成并列路线、不改变可报告距离，保留 tie-uncertainty 标记但不因此降级。若代表 observed-free 路径本身经过 conditional cell，即使 optimistic 下界没有更低，状态仍为 `PARTIAL`。`tau` 只判断已知值与未知下界的浮点并列，不修改距离值，也不影响路线/接入平局排序。若 observed-free 无路而 optimistic graph 有路，输出 `unknown` 和 optimistic lower bound，不填已知距离。两图都无路，且输入有效、域/网格完整覆盖时，才输出“在本离散查询域内不可达”。这也涵盖只有 unknown 接入格的组。远离候选连通路线、不能改善可达性或下界的 unknown 不影响该组对状态。任何必需输入或实际查询返回 `INVALID`/`NOT_AVAILABLE` 时，不把对应格子默认为占用或 free，也不据此声称 unreachable；按下方统一状态规则分别返回 `INVALID`/`NOT_AVAILABLE`。

### 4.4 适配层的确定性并列恢复和来源回溯

图算法库只负责产生标量距离标签；项目适配层负责把标签恢复成一个可复放的代表路径。实现必须满足以下固定顺序，不能把库返回的任意 predecessor 当作最终结果：

1. 所有 cell 使用不可变 `CellKey=(row,column)`；接入候选使用 `AccessKey=(group_id, footprint_cell, free_cell, shared_edge)`；边使用两个端点的字典序 `EdgeKey`。邻接、接入和组对都按这些 key 排序后再交给后端。相同自由格的重复接入先按 `offset` 取最小值，精确并列时按 `AccessKey` 取一个，并保留被淘汰候选的审计记录。
2. NetworkX 3.6.1 的 scalar label 是首版数值权威。适配层读取 `dijkstra_predecessor_and_distance`，仅以精确 `distance[u] + weight == distance[v]` 的 predecessor 候选恢复代表路径；固定二进制浮点加法顺序是虚拟源 offset 后逐边累加。每条物理网格边必须使 label 严格增加，否则以 numerical contract failure 停止该搜索；不静默删除边。不得另行重排加法来决定最优路径，不加 epsilon、不改边权，正常路径不执行第二次 Dijkstra。
3. 在按 `(distance, CellKey)` 递增的 predecessor DAG 上选代表。Observed-free 的每格恢复 key 为 `(conditional_cell_count, source_access_key, full_cell_path_key)`；optimistic 为 `(unknown_cell_count, conditional_cell_count, source_access_key, full_cell_path_key)`。组对目标候选的最终 key 分别为 `(backend_source_label + target_offset, conditional_cell_count, source_access_key, cell_path_key, target_access_key)` 和 `(lower_bound, unknown_cell_count, conditional_cell_count, source_access_key, cell_path_key, target_access_key)`。先比较未舍入 binary64 距离，只有精确相等才比较次级 key。条件/未知计数按选中路径中的不同 cell 计一次，source/target access cell 是路径端点，不重复加计。实现记录 Python/NetworkX 版本与 arithmetic version `networkx-binary64-left-add/1`。
4. 选中后保留 `source_offset`、按路径边序的 `route_edge_sum`、`target_offset`、权威 `backend_hybrid_label = backend_source_label + target_offset`、`canonical_recomposed_sum = (source_offset + route_edge_sum) + target_offset`，以及 `residual = backend_hybrid_label - canonical_recomposed_sum`。精确复放同一后端加法序必须等于权威 label；分项重新分组的 binary64 加法允许产生显式 residual，不再要求两种加法顺序逐 bit 相等。计算 `rounding_bound = 2 * gamma_(edge_count+3) * sum_abs_terms`，其中 `gamma_k = k*eps/(1-k*eps)`、`eps=2^-52`，报告 residual 及以 `ulp(backend_hybrid_label)` 为单位的 residual；非有限值、`k*eps>=1` 或 residual 超过该界是 contract failure。该界只核验算术，绝不参与路线选择或状态判定。`tau` 仅用于 unknown lower-bound 状态判断。
5. 每个 cell 保存其实际查询状态和 source refs；每条路线边保存 domain coverage、grid geometry 和 occupancy query refs。选中观察只回溯实际经过的 cell/edge、两端组 union/centroid、接入候选和输入 manifest；无关 unknown/conditional 单元不得污染该 pair 的 lineage。optimistic lower-bound 另外列出实际使下界成立的 unknown cells/accesses，并明确它不是已知路线。

这套恢复规则允许使用 NetworkX、SciPy、igraph 或原生 C/C++ 核，但后端选择不能改变路径 key、状态传播、来源链或组对排序。后端只要无法满足上述 adapter contract，就不能仅凭“能算出距离”被选为生产实现。

`conditional_cell_count` 包括 source access free cell、路线中实际经过的 cell 和 target access free cell 中状态为 `CONDITIONAL` 的单元；端点代理点本身没有独立状态。optimistic lower-bound 仅为诊断，但其代表下界也按 `(lower_bound, unknown_cell_count, conditional_cell_count, source_access_key, cell_path_key, target_access_key)` 稳定选择，其中 `unknown_cell_count` 同时计入 unknown access 和 unknown route cells。这样不会把一个未选中的 conditional/unknown 单元算进 pair 的状态或 lineage。

## 5. 输出契约

底层模块为每个全范围无序组对（`n(n−1)/2`，不含自身对角线）返回一个稳定、有类型的 `GroupPairDistanceObservation`；组对是查阅地址，不是配组。观察记录中保留：

- `center_to_center_euclidean`：独立的计算状态、数值（如可用）、单位和两个中心的 source refs；它只依赖两个有效组质心，不因自由空间 unavailable/unreachable 而失效。
- `centroid_free_space_hybrid`：带模块内状态标签的有限距离、`unknown`、`unreachable`、`outside`、`not_available` 或 `invalid`；无可用距离数值时不填零。`unknown`/`unreachable` 是此距离观察的结果类别，不新增共享 `FieldStatus`。组投影没有与分析域正面积相交时为 `outside`，不误报为 `unreachable`。
- 若 hybrid 有数值：仅为被选中的最优接入组合记录 `source_centroid_to_access_offset`、`free_space_route_distance`、`target_access_to_centroid_offset`、两侧足迹格/自由接入格/共享边及格心、一条代表路线和使用到的状态/来源。三项及 binary64 residual/ULP 诊断必须按 §4.4 对账，不要求重新分组的三项加法与 backend label 逐 bit 相等。若多个接入组合同为最小，按稳定的 group ID、row、column、edge 顺序选择一个用于呈现，不另输出并列计数。
- 若 observed-free 无路但 optimistic 有路，保留 `optimistic_lower_bound` 及导致下界的未知 access/cells；不把它当作已知距离或已知路径。
- 组级几何审计至少保留 `union_area`、`component_count`、`centroid_inside_union` 和 `centroid_source_ref`。这些字段解释凹形、空洞或不连通组的固定质心为何可能不在实体内部；它们不改变端点规则，也不把质心吸附到边界。
- hybrid 状态统一按以下顺序判定，4.3 节与本契约共用此规则：①必需输入或有效几何明确无效（包括输入/域/网格/占用查询为 `INVALID`，以及投影存在但无效、零面积或质心非有限）→ `invalid`；②必需投影、域、网格或占用查询缺失，网格未完整覆盖域，或所需查询为 `NOT_AVAILABLE` → `not_available`；③输入有效但任一组 footprint 与 domain 无正面积相交 → `outside`；④observed-free 有路，且所选最优路线依赖 conditional cell，或 optimistic lower bound 比 observed-free 距离低超过 `tau` → `partial`；⑤observed-free 有路且达到 optimistic 下界（差值在 `tau` 内视作并列）→ `computed`，若存在同值 unknown 替代则附 tie-uncertainty 标记；⑥observed-free 无路而 optimistic 有路 → `unknown`；⑦两图均无路 → `unreachable`。`invalid` 与 `not_available` 是输入层/查询层失败，不是路径类别；`outside`、`unknown`、`unreachable` 是有效查询结果类别。欧氏通道独立判定：只依赖两组有效质心，因此自由空间不可用、unknown 或 unreachable 不会使其失效；缺失组投影映射为 `not_available`，无效组投影映射为 `invalid`。消费者映射到共享状态时，`unreachable` 是完整有效查询结果（`COMPUTED`），`unknown`/`partial` 映射为 `PARTIAL`，缺失/无效映射为相应状态。消费者的包级状态不得隐藏距离观察状态。
- analysis plane、frame、单位、网格 spacing/origin/shape、domain、占用来源状态、组几何 refs、源 IFC 身份、算法与 schema 版本，以及依赖指纹。

pair 的状态只由其**依赖闭包**决定。闭包至少包括两端组 union/centroid、两端 footprint/access 查询、source-to-target 搜索实际访问的 cell/edge、精确 domain coverage 查询、相关 occupancy/source records 以及 optimistic lower-bound 用到的 unknown candidates。全局 scene/source/plane/grid/occupancy handoff 缺失或无效时，所有受影响 pair 分别为 `not_available` 或 `invalid`；闭包之外的无关 cell 即使 `INVALID`/`NOT_AVAILABLE` 也不得污染该 pair。闭包内的 `INVALID`/`NOT_AVAILABLE` 不能被当作 occupied、free 或 unknown：它们按状态优先级返回，并在 lineage 中列出具体 query/cell/source。这样既不把全场任意坏单元扩大成全量失败，也不把决定连通性的缺失输入伪装成 `unreachable`。

两个读数的极性为描述性：距离是物理量，不是“越大越支持”的证据值；模块不做倒数、归一化、截断或支持变换。每个 pair target 的 identity 由按字典序排序的两个 group identity 确定；source refs 仍按组来源保留。组/占用记录顺序不得影响结果。若势包之后要让“更近”提供更强内聚，它必须自行定义并审阅单调变换，输出作为新增且可追溯的通道，同时保留本模块的两种原始距离及势包纯轴通道。

组几何、网格、平面或占用依赖改变时，相关距离缓存即失效；恢复到同一规范化输入内容（例如编辑后撤销回原模型）可以复用相同结果。该规则复用现有 package freshness/input fingerprint 原则，不在本设计中新增持久缓存系统或 UI。

## 6. 可视化和验证门

实现交付必须全部来自上方指定 IFC，并对所有实际读数生成可索引平面图：底图是真实 IFC 组投影/身份；每个视图能分别看见质心连线与自由空间折线路径、端点偏移、接入单元、被占用/未知的路径节点和单位/分辨率图例。应提供全 pair 的距离矩阵或列表、逐 pair 可定位路线视图与 manifest；样例截图仅作阅读示例，不能替代全结果覆盖。路径数据、manifest、图面数量须相互核验，运行前后 IFC hash 一致。

全量组对验收必须先从稳定排序的 `group_ids` 生成 `expected_pair_ids = combinations(group_ids, 2)`，并满足 `len(expected_pair_ids) = n(n−1)/2`、pair index 与该集合双向相等、每个 `pair_id` 恰有一个 JSON observation 和一个 route-view locator。没有路线的 `unknown`、`unreachable`、`outside`、`not_available` 或 `invalid` pair 也必须有可定位的结果条目；不能用“没有图”表示缺失。矩阵/行表、JSON、route view 和 manifest 的 pair 集合必须逐项对账。

全量运行按源组批处理：每个 graph mode 至多执行 `n` 次 source search，保留一个 source 的 distance/predecessor state，完成其余目标组的 pair observations 后释放，再处理下一个 source；不得无说明地保留 `n × grid_cells` 的完整距离矩阵。验收记录实际 node/edge 数、source-run 数、峰值内存、运行时间和是否采用批处理；本阶段不预设未经测量的秒数阈值，但无法完成 37 组/666 组对或无法记录峰值资源时不得通过。

只验证源中实际出现的状态。真实 IFC 没有的 disconnected / unknown / conditional / tie 情形，记录为未覆盖，不造测试场景补齐。允许针对非空间数据结构做确定性逻辑检查，但不得新建模拟家具、模拟 IFC、布局或预置几何/距离，且不得将这种检查称为 IFC 现实有效性证据。

首版验证重点：

1. 固定源身份、分析平面和单位一致；质心与投影几何引用可追溯。
2. 所有组对覆盖正确且排序确定；欧氏距离矩阵对称，主对角线按不适用处理。
3. 路径每个节点都为可用 free cell、相邻步满足选定拓扑、累加距离与报告分项一致；路径不得穿占用/unknown/域外单元。
4. 两种距离分开保留；不可达或不确定路线不回退到欧氏距离。
5. 多次使用同一指纹 IFC 与同一输入重建得到同一规范化结果/identity；编辑回原内容允许复用，依赖改变时 stale。
6. 全 pair 指标和状态均可从 IFC 平面图及 manifest 定位；未覆盖状态诚实列出。

距离专用交付最小结构固定为：

1. run/source/plane/grid manifest，记录 IFC 指纹、S4 域身份、37 个组身份和预期的 666 个无序组对身份；
2. 稳定 pair index，将 `pair_id` 双向映射到 JSON observation 和逐 pair route view；
3. 完整的欧氏/混合距离矩阵或行表，并明确对角线语义；
4. 每个 pair 的路径节点、边、端点偏移、接入格、占用/unknown 依赖和距离分项和；
5. coverage/reconciliation report，核对 observations、图面、manifest 数量、重复/缺失 pair、输入与输出 hashes；
6. 未覆盖状态清单和同源平面图审阅记录。

这些是结果对账格式，不要求每个 pair 必须单独生成一个文件；可以使用分幅图或索引化视图，但每个 pair 必须可定位。

## 7. 后续势包接入

距离模块是可选的下游输入，不是启用势包的前置条件，也不是现有势包的替代品。势包当前保留的轴角、清晰度、组间轴关系、合力及 hierarchy 结果保持不变。后续如决定让距离影响“同向但相隔很远”的内聚，应另写一次短设计：确定用 `D_euclid` 还是 `D_hybrid`、distance 对象/查询 scope、包内单调变换、与现有方向支持如何并列/组合、不可达与 unknown 如何影响结果，并经用户审阅后才实现。该规则不得反向影响本距离模块或要求几何包必须启用。

## 8. Frozen readiness decisions and implementation boundary

本稿建议的首版规则为：组 union 几何质心为两通道共同端点；footprint 按正面积格交定义；全部 4 邻接自由候选及共享边中点进入端点修正；格心和格心边段受精确分析域约束；4 邻域加权 Dijkstra；自由空间段与两个端点偏移分开输出；只有把 unknown 暂按潜在可通后仍无连接，才报告当前离散域内 unreachable。以下八项在 2026-11-03 经 owner 接受，文字设计已冻结；不要求用户再次审阅文字。执行证据见后端探针和 owner grill 记录：

1. 是否接受格心路线图与精确域几何的 `covers` 约束作为边界语义；结果明确称为离散近似，不称连续最短路。
2. 是否接受足迹格按组 union 正面积交定义，全部 4 邻接自由格按共享边候选，端点偏移通过共享边中点和自由格格心分段定义。更精确连续几何接入属于后续另行讨论，不与栅格接入口径混用。
3. 是否接受 4 邻域加权 Dijkstra 作为全 pair 批处理基线。其网格方向偏差应在指定 IFC 图面中展示；A* 不用于首版全 pair 批处理。
4. 是否接受两图距离判断与状态优先级：observed-free（包括 conditional free）先求已知可用路径，optimistic 图再把 unknown 接入格/路线格视为潜在 free 并求加权下界；只有完整有效的域覆盖和 optimistic 图也无路才输出 unreachable。已知距离是否受 unknown 影响按 lower bound 是否低于 observed-free 值超过浮点并列容差判断。
5. 是否接受以有类型的 pair observation 作为距离模块接口；`FieldResultEnvelope` 只在未来 consumer adapter 需要时使用。
6. 是否接受网格必须完整覆盖分析域作为 hybrid 计算与 unreachable 判定前置条件；未覆盖一律 `NOT_AVAILABLE`，不以 `PARTIAL` 或静默截断替代。

7. 是否接受适配层拥有确定性并列恢复和 lineage，而不是直接采用后端 predecessor；首版固定 NetworkX binary64 label 和紧边 DAG 恢复，不加第二次搜索；异常 label/复放失败是可诊断 contract failure。
8. 是否接受全量 pair 以 `expected_pair_ids` 双射对账，并以逐源批处理控制峰值内存；资源阈值先记录真实 IFC 测量，不预设未经测量的性能承诺。

.17.4a/.17.8/.17.9 的实现前可行性已完成并获 owner acceptance。完整的 37 组/666 pair 运行、生产 S4/grid/occupancy adapter 和资源测量是实现验收，不倒置为 readiness 前必须存在的结果。以上不是实现已完成的声明。独立实施计划是 `2026-11-03-group-distance-module-implementation.md`；按该计划持续维护全流程 checklist。真实 IFC 运行生成 S4 camera-plane 图面后，再请用户做视觉审阅；视觉审阅用于现实结果验收，不替代 `.17.9` 的实现前 readiness，也不能把旧平面或模拟数据当作通过证据。

## 9. 代码与文档锚点

- 当前自由空间：[`features/free_space_field.py`](../../../features/free_space_field.py)；[`features/geometry_views.py`](../../../features/geometry_views.py)；[`features/neutral_scene_views.py`](../../../features/neutral_scene_views.py)
- 当前网格连通历史：[`features/scene_evaluator.py`](../../../features/scene_evaluator.py) 的 `_sampled_bfs_distances`；[`features/affordance/grid_backend.py`](../../../features/affordance/grid_backend.py)
- 共享输出与状态：[`features/field_core.py`](../../../features/field_core.py)
- 势包当前边界：[`features/group_axis_potential_field.py`](../../../features/group_axis_potential_field.py)；[`docs/project/group-potential-and-trend-design-note.md`](../../project/group-potential-and-trend-design-note.md)
- 占用/自由空间底层规则：[`docs/project/occupancy-analysis-plane-and-free-space-policy-note.md`](../../project/occupancy-analysis-plane-and-free-space-policy-note.md)
- 设计与执行顺序：[`group attribution / evidence field plan`](../plans/2026-10-26-group-attribution-evidence-field-implementation.md) 的 `.17` checklist
