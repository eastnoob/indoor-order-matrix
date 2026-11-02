# 家具组距离计算模块设计草案

Date: 2026-11-02
Status: **Owner draft; design only; independent review findings processed; not frozen or implemented**

本草案定义一个可被多个证据包复用的家具组距离计算模块。它本身不是证据包：只计算并报告距离，不替消费者把距离转成支持度、势、衰减、强度或归属。首版同时保留质心直线距离与自由空间约束的质心混合距离。

2026-11-02 的独立审阅覆盖了输入接缝、固定端点、接入格资格、网格接口代理、Dijkstra 路径语义、并列规则和状态优先级；发现的矛盾已在本稿中收口。用户审阅与 readiness 尚未完成，因此这些规则仍是 owner draft，不能当作已冻结契约。

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
- Pixi 已锁定 `networkx`。搜索后端不限制实现语言：可由 Python 调用 C/C++，候选包括 SciPy/igraph 稀疏图核、`python-tcod` 与 Boost.Graph。`heapq` 只是低集成成本备选，尚未选定。接入格有不同初始代价，可由虚拟源边或带初值的多源接口表达；不得把它们全设为零。隐式邻接是节省内存的实现偏好，不是距离语义约束；显式稀疏图可纳入实测比较。当前没有指定 IFC 性能基准，不声称任何候选更快，也不增加依赖。
- `EvidencePackage.evaluate(source_envelopes)` 当前没有组几何或自由空间场接缝。本设计不改变这个共享签名。底层距离模块应接收由同一次 scene-view 解析得到的显式只读输入，并返回有类型的 pair distance observations；将来若证据包要消费它，由包侧 adapter 映射到既有 `FieldResultEnvelope` / `EvidenceChannelRecord`。当前不存在通用输入 adapter；指定 10500 IFC 也没有已确认可复用的 `FreeSpaceField` 实例或冻结网格。该 IFC 将来的网格必须由同一 IFC、同一分析域和经审阅的网格参数建立，不能借用独立 B3 inspection 网格或隐式另选分辨率。距离模块自身不是证据包。

算法参考： [Dijkstra 定义](https://networkx.org/documentation/stable/reference/algorithms/shortest_paths/dijkstra.html)与 [NetworkX 多源接口](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.weighted.multi_source_dijkstra.html)。算法与实现库分开裁决；C/C++ 原生核与 Python 实现必须遵守相同距离定义。

2026-11-02 算法审查范围已扩展到 C/C++，撤回此前“采用 `heapq`”的过早结论。SciPy/igraph 可通过虚拟源保留浮点接入偏移，状态/来源可由 adapter 沿路径恢复；不能仅因这些不是库的原生输出而排除它们。`python-tcod` 接近现成隐式网格引擎，但整数代价需要另行审阅量化误差；Boost.Graph 可定制距离标签，却需要 C++ 图接口及调用边界。选择前仍须核验稳定并列路径恢复、Windows/Pixi 接入和适配总成本；尚未选库、编译、运行 IFC 或添加依赖。完整记录见 [`distance-algorithm-package-review-2026-11-02.md`](../../project/evidence/distance-algorithm-package-review-2026-11-02.md)。

## 3. 查询身份和固定几何

### 3.1 查询范围

**2026-11-02 用户确认的前置规则：**先选定墙体围合区域，其在选定相机 `AnalysisPlane` 上的投影才是分析范围。指定 IFC 无 drawing camera、IfcSpace 或已确认域；先复用 Spec008 的 native drawing/camera 与选墙 B4/显式确认工作流，不以楼板、家具包围盒或画布代替。现有 `_inferred_mesh` 已将完整 shell/holes 还原为 world SI support，request 再投影到选定 plane，不另作重复坐标变换。主树尚缺该依赖闭包，先按[相机与墙围合前置计划](../plans/2026-11-02-wall-domain-camera-prerequisite.md)完成有界恢复与真实输入验收，再推进距离实现；没有域不等于不可达。

一次距离计算绑定同一次 scene-view 解析得到的组整体投影、`AnalysisPlane`、预解析物理占用、自由空间 domain/grid、家具组 scope 和算法版本。显式输入须携带并校验 scene/source identity、plane/frame、linear units、domain identity/content fingerprint、grid origin/spacing/shape、occupancy/source fingerprint 和 group-geometry fingerprints；不可只凭 domain ID 认定几何相同。不得在距离模块内另选平面或静默重采样。网格矩形必须完整覆盖有效分析域；若 domain 缺失/无效、网格未覆盖，或网格/占用输入无法查询，混合距离状态分别为 `INVALID` 或 `NOT_AVAILABLE`，不得据此报告 `unreachable`。覆盖检查以网格外框几何完整 `covers(domain)` 为准。

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

使用**加权 Dijkstra**。对稳定顺序中的每个源组，将其所有接入格心以对应 `offset_source` 作为虚拟源边权，一次求到自由空间图中所有可达格心的最短距离；再对每个目标组取 `distance[cell] + offset_target(cell)` 的最小值。网格边权非负；邻接图无向。一次源搜索可服务其余全部目标组，因此对 `n` 组最多按源组执行 `n` 次 Dijkstra，而不是每个无序组对单独跑 A*。对全部无序组对输出一条距离记录，而不是建立配对结果。NetworkX 可复用为图算法依赖，也可在规则网格上用现有环境写小型 heap-based Dijkstra；两者都必须满足同一图定义，spec 不把某个库当作距离语义。

计算由 Dijkstra 前驱恢复一条稳定代表路径；Dijkstra 的路径比较先按未舍入的累计距离，精确并列时按条件性格数量、再按 row/column 字典序的完整 cell 路径择一。组对最终候选比较先按未舍入的混合距离，精确并列时按所用条件性格数量，再按固定的 source access、cell 路径、target access 顺序择一。平局选择不修改边权、不加 epsilon；`tau` 仅用于下文判断未知下界是否可能改善已知距离，不用于路径或接入组合排序。Dijkstra 只给定图上的最短解；它不证明连续几何最短。每个组对执行两种图查询：

1. **Observed-free graph：**节点/接入只含值为 free 的 `ESTABLISHED` 或 `CONDITIONAL` cells。求得的最短值为当前可计算路径。精确等长时优先选 conditional cells 较少者，再按上方固定顺序打破并列。若代表最优接入/路线经过 conditional cell，则该已知距离为条件性结果，状态为 `PARTIAL` 并记录依赖来源。
2. **Optimistic graph：**在 observed-free graph 上加入 `UNKNOWN` cells 和 unknown access candidates，按潜在 free 计算加权最短路，只作为下界诊断，不作为已知距离或路线。

若 observed-free 有路，输出其数值与分项；当 optimistic lower bound 比 observed-free 值低超过 `tau = max(ulp(D_observed), ulp(D_optimistic), ulp(grid_spacing))` 时，标 `PARTIAL`（unknown 可能改善最优距离）。两值差在 `tau` 内视作数值并列；unknown 只能形成并列路线、不改变可报告距离，保留 tie-uncertainty 标记但不因此降级。若代表 observed-free 路径本身经过 conditional cell，即使 optimistic 下界没有更低，状态仍为 `PARTIAL`。`tau` 只判断已知值与未知下界的浮点并列，不修改距离值，也不影响路线/接入平局排序。若 observed-free 无路而 optimistic graph 有路，输出 `unknown` 和 optimistic lower bound，不填已知距离。两图都无路，且输入有效、域/网格完整覆盖时，才输出“在本离散查询域内不可达”。这也涵盖只有 unknown 接入格的组。远离候选连通路线、不能改善可达性或下界的 unknown 不影响该组对状态。任何必需输入或实际查询返回 `INVALID`/`NOT_AVAILABLE` 时，不把对应格子默认为占用或 free，也不据此声称 unreachable；按下方统一状态规则分别返回 `INVALID`/`NOT_AVAILABLE`。

## 5. 输出契约

底层模块为每个全范围无序组对（`n(n−1)/2`，不含自身对角线）返回一个稳定、有类型的 `GroupPairDistanceObservation`；组对是查阅地址，不是配组。观察记录中保留：

- `center_to_center_euclidean`：独立的计算状态、数值（如可用）、单位和两个中心的 source refs；它只依赖两个有效组质心，不因自由空间 unavailable/unreachable 而失效。
- `centroid_free_space_hybrid`：带模块内状态标签的有限距离、`unknown`、`unreachable`、`outside`、`not_available` 或 `invalid`；无可用距离数值时不填零。`unknown`/`unreachable` 是此距离观察的结果类别，不新增共享 `FieldStatus`。组投影没有与分析域正面积相交时为 `outside`，不误报为 `unreachable`。
- 若 hybrid 有数值：仅为被选中的最优接入组合记录 `source_centroid_to_access_offset`、`free_space_route_distance`、`target_access_to_centroid_offset`、两侧足迹格/自由接入格/共享边及格心、一条代表路线和使用到的状态/来源。三项必须相加等于 hybrid 数值。若多个接入组合同为最小，按稳定的 group ID、row、column、edge 顺序选择一个用于呈现，不另输出并列计数。
- 若 observed-free 无路但 optimistic 有路，保留 `optimistic_lower_bound` 及导致下界的未知 access/cells；不把它当作已知距离或已知路径。
- hybrid 状态统一按以下顺序判定，4.3 节与本契约共用此规则：①必需输入或有效几何明确无效（包括输入/域/网格/占用查询为 `INVALID`，以及投影存在但无效、零面积或质心非有限）→ `invalid`；②必需投影、域、网格或占用查询缺失，网格未完整覆盖域，或所需查询为 `NOT_AVAILABLE` → `not_available`；③输入有效但任一组 footprint 与 domain 无正面积相交 → `outside`；④observed-free 有路，且所选最优路线依赖 conditional cell，或 optimistic lower bound 比 observed-free 距离低超过 `tau` → `partial`；⑤observed-free 有路且达到 optimistic 下界（差值在 `tau` 内视作并列）→ `computed`，若存在同值 unknown 替代则附 tie-uncertainty 标记；⑥observed-free 无路而 optimistic 有路 → `unknown`；⑦两图均无路 → `unreachable`。`invalid` 与 `not_available` 是输入层/查询层失败，不是路径类别；`outside`、`unknown`、`unreachable` 是有效查询结果类别。欧氏通道独立判定：只依赖两组有效质心，因此自由空间不可用、unknown 或 unreachable 不会使其失效；缺失组投影映射为 `not_available`，无效组投影映射为 `invalid`。消费者映射到共享状态时，`unreachable` 是完整有效查询结果（`COMPUTED`），`unknown`/`partial` 映射为 `PARTIAL`，缺失/无效映射为相应状态。消费者的包级状态不得隐藏距离观察状态。
- analysis plane、frame、单位、网格 spacing/origin/shape、domain、占用来源状态、组几何 refs、源 IFC 身份、算法与 schema 版本，以及依赖指纹。

两个读数的极性为描述性：距离是物理量，不是“越大越支持”的证据值；模块不做倒数、归一化、截断或支持变换。每个 pair target 的 identity 由按字典序排序的两个 group identity 确定；source refs 仍按组来源保留。组/占用记录顺序不得影响结果。若势包之后要让“更近”提供更强内聚，它必须自行定义并审阅单调变换，输出作为新增且可追溯的通道，同时保留本模块的两种原始距离及势包纯轴通道。

组几何、网格、平面或占用依赖改变时，相关距离缓存即失效；恢复到同一规范化输入内容（例如编辑后撤销回原模型）可以复用相同结果。该规则复用现有 package freshness/input fingerprint 原则，不在本设计中新增持久缓存系统或 UI。

## 6. 可视化和验证门

实现交付必须全部来自上方指定 IFC，并对所有实际读数生成可索引平面图：底图是真实 IFC 组投影/身份；每个视图能分别看见质心连线与自由空间折线路径、端点偏移、接入单元、被占用/未知的路径节点和单位/分辨率图例。应提供全 pair 的距离矩阵或列表、逐 pair 可定位路线视图与 manifest；样例截图仅作阅读示例，不能替代全结果覆盖。路径数据、manifest、图面数量须相互核验，运行前后 IFC hash 一致。

只验证源中实际出现的状态。真实 IFC 没有的 disconnected / unknown / conditional / tie 情形，记录为未覆盖，不造测试场景补齐。允许针对非空间数据结构做确定性逻辑检查，但不得新建模拟家具、模拟 IFC、布局或预置几何/距离，且不得将这种检查称为 IFC 现实有效性证据。

首版验证重点：

1. 固定源身份、分析平面和单位一致；质心与投影几何引用可追溯。
2. 所有组对覆盖正确且排序确定；欧氏距离矩阵对称，主对角线按不适用处理。
3. 路径每个节点都为可用 free cell、相邻步满足选定拓扑、累加距离与报告分项一致；路径不得穿占用/unknown/域外单元。
4. 两种距离分开保留；不可达或不确定路线不回退到欧氏距离。
5. 多次使用同一指纹 IFC 与同一输入重建得到同一规范化结果/identity；编辑回原内容允许复用，依赖改变时 stale。
6. 全 pair 指标和状态均可从 IFC 平面图及 manifest 定位；未覆盖状态诚实列出。

## 7. 后续势包接入

距离模块是可选的下游输入，不是启用势包的前置条件，也不是现有势包的替代品。势包当前保留的轴角、清晰度、组间轴关系、合力及 hierarchy 结果保持不变。后续如决定让距离影响“同向但相隔很远”的内聚，应另写一次短设计：确定用 `D_euclid` 还是 `D_hybrid`、distance 对象/查询 scope、包内单调变换、与现有方向支持如何并列/组合、不可达与 unknown 如何影响结果，并经用户审阅后才实现。该规则不得反向影响本距离模块或要求几何包必须启用。

## 8. 未冻结项与裁决建议

本稿建议的首版规则为：组 union 几何质心为两通道共同端点；footprint 按正面积格交定义；全部 4 邻接自由候选及共享边中点进入端点修正；格心和格心边段受精确分析域约束；4 邻域加权 Dijkstra；自由空间段与两个端点偏移分开输出；只有把 unknown 暂按潜在可通后仍无连接，才报告当前离散域内 unreachable。下列细节仍需用户审阅，若用户否决则先修订 spec：

1. 是否接受格心路线图与精确域几何的 `covers` 约束作为边界语义；结果明确称为离散近似，不称连续最短路。
2. 是否接受足迹格按组 union 正面积交定义，全部 4 邻接自由格按共享边候选，端点偏移通过共享边中点和自由格格心分段定义。更精确连续几何接入属于后续另行讨论，不与栅格接入口径混用。
3. 是否接受 4 邻域加权 Dijkstra 作为全 pair 批处理基线。其网格方向偏差应在指定 IFC 图面中展示；A* 不用于首版全 pair 批处理。
4. 是否接受两图距离判断与状态优先级：observed-free（包括 conditional free）先求已知可用路径，optimistic 图再把 unknown 接入格/路线格视为潜在 free 并求加权下界；只有完整有效的域覆盖和 optimistic 图也无路才输出 unreachable。已知距离是否受 unknown 影响按 lower bound 是否低于 observed-free 值超过浮点并列容差判断。
5. 是否接受以有类型的 pair observation 作为距离模块接口；`FieldResultEnvelope` 只在未来 consumer adapter 需要时使用。
6. 是否接受网格必须完整覆盖分析域作为 hybrid 计算与 unreachable 判定前置条件；未覆盖一律 `NOT_AVAILABLE`，不以 `PARTIAL` 或静默截断替代。

以上不是实现已完成的声明。详细决策由用户审阅和后续实施计划冻结。

## 9. 代码与文档锚点

- 当前自由空间：[`features/free_space_field.py`](../../../features/free_space_field.py)；[`features/geometry_views.py`](../../../features/geometry_views.py)；[`features/neutral_scene_views.py`](../../../features/neutral_scene_views.py)
- 当前网格连通历史：[`features/scene_evaluator.py`](../../../features/scene_evaluator.py) 的 `_sampled_bfs_distances`；[`features/affordance/grid_backend.py`](../../../features/affordance/grid_backend.py)
- 共享输出与状态：[`features/field_core.py`](../../../features/field_core.py)
- 势包当前边界：[`features/group_axis_potential_field.py`](../../../features/group_axis_potential_field.py)；[`docs/project/group-potential-and-trend-design-note.md`](../../project/group-potential-and-trend-design-note.md)
- 占用/自由空间底层规则：[`docs/project/occupancy-analysis-plane-and-free-space-policy-note.md`](../../project/occupancy-analysis-plane-and-free-space-policy-note.md)
- 设计与执行顺序：[`group attribution / evidence field plan`](../plans/2026-10-26-group-attribution-evidence-field-implementation.md) 的 `.17` checklist
