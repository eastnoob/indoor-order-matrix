# 家具分组归属场：设计审查

更新：2026-10-25。当前在设计审查；未获批前不恢复拟合、不实现算法、不接生产/UI。AuthoredGroup 是输入事实，不是 ground truth。

当前结论：目标边界可以先固定；候选 recipe、成员归属算法、证据量尺和弱尾读数保留为实验决策点。下文公式是待比较方案，不是已批准算法或概率模型。

## 目标与建议定义（待审）

- 最小单元采用来源可追的显式家具 `AuthoredGroup`（IFC `ObjectType=furniture_group`；其他 adapter 提供等价标记），组内家具不拆分；候选由完整单元组成，可跨组组合、重叠、嵌套，也可覆盖全域。authored membership 不是 ground truth。空组不成为节点；重复成员只计一次但保留审计；未解析成员保留为输入事实并将受影响证据标为 invalid/partial。多个合格组共享家具时保留所有节点身份和依赖，不用 first-wins，也不自动视为互斥。未归入合格组的家具保留为 unassigned/unknown。候选是组织可能性的描述场，不是最终硬分区。
- 候选提议与成员归属是两个算子。提议记录 `P=(recipe, scope, extent, closure_status, proposal_evidence)`；每个 recipe 说明多类证据分别驱动扩展还是只改软归属强度，允许某些候选主要由一个驱动扩展、其他证据仍作软影响。明确互斥是已同意的硬否决例外。“尽”是固定 recipe 下的包含极大，不是全局最大；不同 recipe 的重叠极大候选保留，全域候选也允许。只有未知的**驱动证据**可能改变扩展判断时才标 `conditional`；软影响证据未知只影响归属状态。搜索截断标 `incomplete`，不可宣称已闭包。
- 用户确认家具组是最小单元，候选需表达其成员归属强度。沿用原 Stage A–D 的 E(g,k,s)：g 为作用域内 AuthoredGroup，k 为候选，s 为尺度/查询；E 保存逐证据渠道的观察、支持/反对、状态、来源/依赖和解释，构成结构化“场”。候选 proposal_extent 是该 recipe 的提议边界，不等于硬成员真值；M_k(g,s) 是从 E 派生的非概率归属强度读数，只有映射/融合有依据时才压为标量，否则保留分家族证据与状态。全域仅指已冻结作用域内的合格 AuthoredGroup；范围外单元单列为边界张力，scope 外不是零。Field kernel 可承载 E，不决定候选或 M。
- 证据分三种用途并保留来源/状态：①提出候选和扩展闭包；②评价单元对候选的支持、反对、未知、冲突；③候选与柱网、墙体、其他候选的下游势契合。第三类只读，不回写成员归属。一个原始事实可被不同算子引用，但不能因此被默认当成多条独立证据重复加权。
- 组强度是 proposal_extent 内成员归属强度的分布读数，不另造稳定性总分。均值与已知覆盖率是首要读数；中位数、弱尾、离散度及未知/冲突数作为候选 profile 项比较。未知不当作 0；extent 外归属单列，供观察边界张力。

## 证据家族与用途

| 证据 | 可见用途 | 当前事实 / 边界 |
| --- | --- | --- |
| 组对几何原始观察：边界间隙、接触、重叠；适用时的高度/净空 | 可作为组对关系观察或候选提议的底料；只有经单独定义后才进入归属场 | `group_self_description` 保留跨组家具对的平面观察；3D/Z unavailable，组级聚合、`positive_support`、强度及 formal edge 仍为 `null/deferred`。这些几何量不等同于“势一致”或归属支持；tolerance 是数值判定精度，不是分组感知阈值 |
| 语义/功能与显式关系 | 类型/功能证据作软支持、反对或冲突；有目标且来源可核的明确互斥才可 veto | 当前类型完全不同时只是 `soft_negative`；`mutual_exclusion` 仅保存原始声明及来源，尚未核验声明是否指向当前单元对，暂不能据此执行硬 veto |
| 局部支持 / 组织势 | 作为候选×家具组层面的待诊断证据，观察某组是否得到邻域、空间、几何、语义及跨尺度关系的共同支持 | 2026-09-29 已批准为设计方向：区分“少数元素混入周边”与“少数元素形成独立势”；要求多通道相互作用，不让单一属性独揽。具体观测映射、交互规则和量尺未定，目标归属场尚未实现 |
| 布局 pattern（队列、网格、成对、聚类等） | **暂定确认**为候选级证据或 recipe 条件；只有候选家具组到 pattern 槽位的映射可审计时，才进入成员归属证据 | `position_grammar` 给组级拟合和成员到槽位残差；未经候选单元映射，不直接给归属强度。`position-confidence` 混合拟合、规模、槽位数与 authored bonus，不能当 membership score。OCTA 的家具到理想槽位映射尚未定义 |
| 自由空间连通、瓶颈、墙体/开口关系 | 区分组间空隙几何、实际连通/可通行空间，以及候选形成后的空间契合；各用途需分开 | 有些房间/活动区域级读数已实现，但尚未映射到 AuthoredGroup 归属场；`group_self_description` 的组级自由空间、连通和瓶颈仍 unavailable/deferred |
| 下游势契合：候选与柱网、墙体、路径或其他候选的协调 | 候选成形后的只读评估，不回写成员归属 | 原始布局目标提出区域/家具组整体“势”的连续 alignment；与组对距离不同，也与候选内的局部归属支持不同。当前没有统一的 candidate-to-context potential compatibility 量尺 |
| missing / invalid / partial / conflict / provenance | 约束可计算性、覆盖率和审计 | 是状态与来源，不得被改写成 0、支持、反对或 clear |

## 数学方案草案（未批准）

- 推荐总体形式是候选假设集合及每个候选的结构化证据场，而非硬分区。候选记录可写为 H=(recipe, scope, proposal_extent, closure_status, proposal_evidence, E)；E(g,k,s) 沿用原设计的逐单元、逐候选、逐尺度证据记录。M_k(g,s) 是可选的强度投影，不与 E 混为一层，也不天然等于概率。模糊关系可表示已定义量尺上的可重叠归属强度，但不生成候选、不提供证据量尺或融合公式；无可辩护共同量尺时保留分渠道读数。FieldResultEnvelope 可承载 E 的状态、来源与依赖，但不负责推断。
- E 的定义域先按原设计固定为冻结 scope 内全部合格 AuthoredGroup；scope 外记录为 outside/uncovered，不填零。逐单元 M_k(g,s) 则是待验证的强度投影：候选内 g 暂以它对其余 extent 单元的关系作对照，候选外 g 暂以它对 extent 全体的关系显示边界张力。无可用比较为 not_available，单成员候选不因被提出就自动得 1。算术均值只适用于已映射到共同尺度的 pairwise 证据；pattern 等整体证据不能强行拆成 pair。AuthoredGroup 对等权，重复共享物理来源只记依赖、不重复投票。E 的范围已定；M 的尺度、映射和组间汇总仍须实验，不是已批准量尺。
- 独立证据家族的映射与融合也待实验裁决：先规定各家族支持、反对、中性和 unknown 的可解释锚点，再比较透明的家族等权融合与保留分家族向量的读法。若量尺无法辩护，就不伪造单一合成值。互斥保留为独立 `vetoed` 状态；只有来源可追且两端唯一解析到当前 AuthoredGroup 对时才硬否决。未经真实数据校准的数值叫规则强度，不叫概率；不使用合成标签拟合权重。
- Pattern 或整体布局证据默认是候选级证据/扩展驱动，不强行均摊给成员；只有候选单元到 pattern 槽位的对应关系可审计时，才生成成员级分数。extent 外单元若 M 很高，报告为边界张力，供其他 recipe 提出更大候选；不静默扩展当前候选。单成员候选若 recipe 明确提出，可保留，但没有可比较的组内关系时其关系型 M 应为 `not_available`，不因被列入 extent 自动得 1。
- 组强度是 proposal_extent 内 `M(C,u)` 的 profile，不是独立稳定性分数：至少保留成员值向量、均值和成员分数可用率；弱尾与离散度作补充读数。需同时报告每成员的有效/预期比较数，以及按证据家族计算的已知/预期唯一 pair 覆盖；所有成员都有部分均值不代表证据完整。弱尾读数（min、低分位数或弱成员均值）的取舍由小组、单弱成员和缺失值实验决定；未知/冲突数单列且不计为零。范围外成员的归属值单列，不进候选主 profile。
- 默认枚举重叠的局部候选，不强制全域互斥 partition，也不归一化成赢家。多个 recipe 下的极大候选全部保留；这里的“多解”是多种可能组织，不等于成员关系含糊。只有下游任务要求选择唯一互斥且覆盖完整的组合时，才另设 configuration 层；此时才需要表达选择歧义。

职责拆为六块：①单元目录/资格；②原始证据适配与来源/依赖登记；③recipe 候选提议与闭包；④候选×单元归属场及家族融合；⑤成员分布 profile；⑥柱网/墙体/组间势契合消费者。前五块构成分组推断，最后一块单向消费候选。数学工具是集合闭包（pairwise 对称规则可用 maximal-clique 特例）、模糊关系、家族内稳健汇总和描述统计；工程上复用现有 evidence channel / `FieldResultEnvelope` 承载状态与 provenance，不把 field kernel 当算法。泛化全子集搜索可能指数增长；recipe 未说明单调性时，不能仅靠单步扩展宣称 maximal，需检查更大扩展或标记 `incomplete`。不新增依赖。

## RGB 弱合并手算（构造值，非标签/算法结果）

设同色组对支持 `e=.90`，红—绿跨色支持 `.50`，任一颜色与蓝色跨色支持 `.15`。为检查表示能力，暂用以下未批准的基线：候选内单元 `u` 的归属参照值是它对候选内其他单元关系值的均值；候选外单元则对候选全部成员取均值。两者的比较集合和分母分别是 `|C|-1` 与 `|C|`。这是候选内/外可比性的实验起点，不等于已决定的归属量尺。

| 候选 | 各候选成员的关系列表 → `M(C,u)` | 成员值 profile：均值 / 中位数 / 最弱值 |
| --- | --- | ---: |
| `R={R1,R2}`（`G`,`B` 同理） | `R1,R2: [.90] → .90` | `.90 / .90 / .90` |
| `R∪G` | 每个红/绿单元：`[.90,.50,.50] → .633` | `.633 / .633 / .633` |
| `R∪G∪B` | 红/绿各：`[.90,.50,.50,.15,.15] → .44`；蓝各：`[.90,.15,.15,.15,.15] → .30` | `.393 / .44 / .30` |

因此这个基线能同时保留强原组、较弱的红绿合并以及更弱的全域合并；全域候选的成员值 profile 为 `[.44,.44,.44,.44,.30,.30]`。候选外值另作边界张力读数：对 `C_R`，每个绿单元为 `[.50,.50] → .50`，每个蓝单元为 `[.15,.15] → .15`；对 `C_{R∪G}`，蓝单元为四个 `.15` 的均值。它们不进入候选内组强度 profile。此例只验证表示，不选择算法或现实证据映射。

### 小型“尽”规则诊断（单一边界证据的对照基线）

暂用“候选内所有 pair 支持均达到 `α`”作扩展谓词，穷举六节点子集并保留 inclusion-maximal 候选：

| 尺度 `α` | 极大候选 | 候选内归属 profile（均值 / 中位数 / 最弱值） |
| --- | --- | --- |
| `.90` | `R, G, B` | 各 `.90 / .90 / .90` |
| `.50` | `R∪G, B` | `R∪G: .633 / .633 / .633`；`B: .90 / .90 / .90` |
| `.15` | `R∪G∪B` | `.393 / .44 / .30` |

这项六节点穷举诊断表明，不同尺度各自保留极大候选，能同时表达强原组、较弱嵌套合并和全域假设；同一尺度内，较小集合会被可扩展的超集取代。相同成员集合可共享集合身份，但保留 recipe/尺度来源。它只验证构造算术，不验证现实边界或度量解释。独立复核确认表中算术一致，并指出还应对照“提议与归属复用同一证据”及“归属使用独立/留出证据”，检查候选筛选是否抬高自身归属读数。多条件 recipe、软影响、明确互斥，以及 unknown/conflict 下的闭包状态仍待比较。

两个小型敏感性检查补充了 profile 的必要读数：给 `R∪G` 加一个对四个成员均只有 `.15` 支持的桥接单元后，四个核心成员各为 `.5125`、桥接成员 `.15`，profile 均值 `.44`、中位数 `.5125`、最弱值 `.15`、总体标准差 `.145`。均值单看会遮住弱尾。另设四单元互相支持 `.90`，但 `A-B` 关系未知：四个单元的已知值均值都仍为 `.90`，四个单元分数都可计算，但该单一关系家族中仅观察到 `5/6` 个唯一 pair；A、B 各 `2/3` 个预期比较可用，C、D 各 `3/3`。因此 profile 要同时显示成员分数分布、每单元有效/预期比较数、可计算成员数/候选成员数和按家族统计的唯一 pair 覆盖率；仅报均值或“有分数的成员比例”会隐藏证据缺口。这些是表示诊断，不是现实校准。

再对单元级 `M` 汇总器作敏感性对照，按“profile 均值 / 中位数 / 最弱值”报告：强原组在 pair-mean、pair-median、pair-min 三种情况下均为 `.90/.90/.90`；`R∪G` 分别为 `.633/.633/.633`、`.50/.50/.50`、`.50/.50/.50`；全域候选分别为 `.393/.44/.30`、`.383/.50/.15`、`.15/.15/.15`。pair-min 会被任一弱关系拖低全部单元，单独用作 `M` 会抹掉红绿和蓝的归属差异；它更适合作 profile 的弱尾读数。pair-mean 与 pair-median 都保留强组高于合并组，但刻度和蓝组弱尾不同。当前建议把 pair-mean 作为首个可解释基线，保留原始关系列表、状态/覆盖和 profile 的中位数/弱尾作并列诊断；median 留作敏感性对照。该建议只按“所有已知关系都影响强度、单个弱关系不硬否决”的目标性质筛选，仍需真实场景审阅才能决定其现实解释性。

## 现有工作盘点

| 现有内容 | 可复用之处 | 处置边界 |
| --- | --- | --- |
| `NeutralSceneV2.authored_groups` 与 `group_self_description` | 前者是可追来源的单元来源；后者保留逐成员对几何观察及语义/互斥原始证据 | authored group 是输入，不是真值；关系聚合、强度和 formal edge deferred，`candidate_views` 仍为空 |
| 旧 `features/scene_inference.py:furniture_groups()` | 家具 affordance extent、显式 `furniture_group` key、extent overlap、朝向/frame 证据，以及 downstream serializer 可作 hard-rule baseline 和证据生产 | 按精确语义 key 生成单一不重叠分区；union bbox 与 overlap 不能表示替代候选、全域归属场或组强度。保留作基线/证据源，不作 ground truth |
| D6 候选诊断 | 多尺度/聚合 recipe、重叠/嵌套/歧义/缺失反例，可作 proposer 对照材料 | 保留为 diagnostics；owner decision 只批准并列方向，要求按 recipe 定义 maximal、补状态传播；implementation design 仍 deferred，合成 truth 不选 winner |
| 旁支 `order_analyzer_group_inference_stage_b/features/group_inference_field.py` | 52 项聚焦测试通过；可复用 `FieldResultEnvelope`、状态/来源、几何/语义/互斥/空间/pattern 证据和审计输出 | 复用证据生产/封装，不沿用其目标形状：只枚举 AuthoredGroup 两两 union；target 是 `(original_object_id, pair_candidate_id)`，仅覆盖 union 内原始家具对象；没有 `(candidate, AuthoredGroup)` 全域场、标量归属度或组强度，projection 为 unknown、aggregation deferred，不写 formal membership edge 或生产 `candidate_views` |
| `field_core` / `FieldResultEnvelope` | 承载证据通道、状态、来源、缓存身份 | kernel 不生成候选、不融合归属、不算组强度 |
| Stage B successor 拟合/预测诊断 | 只复用状态/来源接口和可迁移失败反例 | 暂停把合成标签拟合推进为目标算法；predictive check 只判断该模型与其生成机制是否自洽，既不生成目标候选全集、规则归属场和组强度 profile，也非本目标实现前置或真实正确性证明 |

行动判定：保留 AuthoredGroup 身份与原始证据、旧硬分组作为对照、FieldResultEnvelope 状态/来源接口及 D6 反例；暂缓 Stage B 合成标签拟合路线；按目标重设计候选×AuthoredGroup 的完整归属场、recipe 闭包和组 profile。只有逻辑不变量与表示/profile 实验支持其设计后，才开始实现。

## 近期代码审查补充

- 单元资格当前实现不一致：`AuthoredGroup` 只验证引用格式，允许空/重复引用；`analysis_scene_view` 还接纳全家具成员的通用组，并用 `setdefault` 将共享家具压到首组；`group_self_description` 只接受显式 `furniture_group`，且测试保留共享成员依赖。基于原 Stage A–D 节点定义、IFC adapter 标记和现有测试，本笔记建议把“来源可追的显式家具组标记”定为唯一资格规则；不以成员碰巧全是家具推断资格。空组不建节点，重复 refs 只计一次并留审计，dangling refs 不删事实但使相关证据 invalid/partial；跨合格组共享家具保留双重 authored membership，归属统计按共享来源去依赖化。资格/身份是输入契约裁定；共享物理关系如何影响具体归属强度仍须实验。旧 `furniture_groups()` 按显式 key 或 region/group key fallback 建唯一硬分区；可作对照和证据源，不是 `AuthoredGroup` 场、候选枚举或 ground truth。
- `group_self_description` 给出成员对原始/面积归一距离、接触/重叠和语义类型差异；组级聚合仍 deferred。它把 `mutual_exclusion` 的原始值和来源记入 conflicts，但不校验其目标端点，现阶段只能视为待解释的冲突声明。
- `position_grammar` 是组级布局 pattern 证据；现有 `_fit` 是残差映射，`position-confidence` 混合成员数、槽位数和 authored bonus，不能直接当成员归属强度。Pattern 也不天然等价于对称 pair compatibility；只有能映射到候选内具体单元/槽位的 residual 才可能成为成员级证据。
- 当前空间观察主要说明作用域/通道是否可用；free-space、connectivity、bottleneck 和 barrier 的分组测量仍 unavailable/deferred。旁支证据场可复用状态、来源及若干证据生产，但只覆盖两两 authored-group union 中的原始对象，不能提供目标所需的完整 `(candidate, AuthoredGroup)` 场或强度。

原始 Stage A–D 总设计已在 sibling 工作区找到：[设计规格](D:/PROJECTS/understandOtherPackage/order_analyzer_group_inference_stage_b/docs/superpowers/specs/2026-10-22-group-clustering-evidence-field-design.md)（节点/候选/场定义见 §3，阶段安排见 §10）和 [Stage A 计划](D:/PROJECTS/understandOtherPackage/order_analyzer_group_inference_stage_b/docs/superpowers/plans/2026-10-22-group-clustering-stage-a.md)。原计划以合格 `AuthoredGroup` 为节点，候选允许重叠、嵌套、竞争和未覆盖；这与当前确认的最小单位相符。它把候选提议与成员场分开，也明确候选不是成员关系真值。Stage A 已覆盖的候选对照、嵌套/重叠、共享来源、缺失状态和 pattern conditioning 检查，不能推成完整 candidate×unit 归属场或组 profile 已实现。

### D6 / Stage A 覆盖审计（2026-10-25）

- D6 已有多类 fixture、相对尺度视图、并列 aggregation diagnostics、holdout 计算性 recovery 与 invariance/status/veto/overlap/unassigned 断言；owner decision 未批准 selector、阈值或 production API，recipe maximal、ambiguity 和状态传播仍需契约。它提供候选生成对照与失效案例，不提供完整 candidate×`AuthoredGroup` 归属场或成员 profile。Stage A decision 还保留一项 H2 verifier hash mismatch（12/13 匹配，来源未解）；这不推翻 A2/A3 的有限诊断结论，但不能写成全验证通过。
- Stage A 补充了候选提议/闭包对照、37-node 有界成本测量及 pattern 条件泄漏诊断，且明确不实现生产聚类或强度。它并未覆盖：重复/重叠 `AuthoredGroup` 输入如何资格化、软影响与候选边界的完整合同、proposal 外单元归属场，以及由成员归属分布读出的组强度 profile。
- 所以当前不是“D6 什么都没做”，而是它已完成 design-only 的候选与状态诊断；也不是“分组目标已经完成”，因为核心归属场/profile 尚无实现。D6 的 Bayesian/synthetic-label 路线不作为本目标前置。

阶段状态：A 的有限候选/模式诊断完成，只获准进入 B 设计；B 初始合成成员模型未通过强度门，成员强度仍为 `null/not_evaluated`（[B 决策](D:/PROJECTS/understandOtherPackage/order_analyzer_group_inference_stage_b/docs/project/evidence/group-clustering-stage-b-decision.md)）。后续 successor 仍是 development-only，最新 smoke fit 未收敛、`production_ready=false`（[successor 规格](D:/PROJECTS/understandOtherPackage/order_analyzer_group_inference_stage_b/docs/superpowers/specs/2026-10-24-group-membership-successor-factorization.md)）；C 的生产实现与 D 的真实模型/消费者证明均未完成。Stage B 结果说明这条合成标签概率路线目前不成立，不能说明按证据规则给出非概率强度也不可能。

重要语义差异：原计划把跨尺度/扰动下的候选变化也称为 stability；当前目标中的组内稳定/松散应直接由候选内成员归属强度分布读出。前者最多保留为可选敏感性诊断，不能替代组 profile，也不另造稳定性总分。Stage B successor 的 primitive-node 输入尚未证明映射为本目标的 `AuthoredGroup → candidate` 归属场。

数学/工具初筛（来源已核对）：模糊关系最贴近“候选×单元、允许重叠的分级归属”表示，但不会自行提供本项目的证据量尺或组强度算法。`fcaR` 可做 fuzzy formal concept / closure，或作为候选提议研究工具；它需要先把证据编码成形式背景，不能直接替代归属场。`scikit-fuzzy` 的 c-means 需给定簇数，且在簇之间归一对象隶属度，与候选互不排斥、强度不要求和为 1 的目标不同。此次初筛未发现可直接端到端复用的现成模块；不新增依赖。

来源：Zadeh (1965), DOI `10.1016/S0019-9958(65)90241-X`; Bělohlávek (1999), DOI `10.1002/malq.19990450408`; Cordero et al. (2022), DOI `10.32614/RJ-2022-014`; [fcaR](https://github.com/Malaga-FCA-group/fcaR); [scikit-fuzzy](https://github.com/scikit-fuzzy/scikit-fuzzy)。文献支持模糊关系/FCA 作为数学工具，不替项目验证量尺或权重。

## 计划与实验决策门

### 可先固定的约束

- 最小单元是有来源、明确标记的 AuthoredGroup；它是输入事实，不是 ground truth。空组不成节点，重复成员去重但留审计，dangling 引用保留并标状态，共享成员保留在各组中且不自动互斥。
- 候选是可并存的松散组织假设，可以跨原组组合、重叠、嵌套或覆盖全域；不是硬分区。每条候选 recipe 的“尽”只表示在该 recipe 与当前证据/作用域下不能再扩展，不代表现实中唯一正确。
- 分开候选提议、候选×AuthoredGroup 归属场、组强度 profile、组与柱网/墙体/其他组的下游契合。已解析的明确互斥可硬否决；普通软证据改归属读数，不能单独删候选。未知、冲突和搜索不完整须显式保留。
- 归属强度不是概率。组级稳定/松散从组内强度分布读出，不另造稳定性总分。Field kernel 可承载状态、来源和依赖，不负责生成候选或算强度。

### 必须由实验裁定的设计点

1. 候选是由单一驱动加 modifiers 生成、由多个驱动联合闭包，还是保留多个并行 recipe？
2. 表示域按原 Stage 规格固定为冻结作用域内全部合格单元的 E(g,k,s)；待实验的是哪些证据能派生标量 M_k(g,s)，以及 extent 外强度如何表达为边界张力而不被误读成候选成员。
3. 同一证据既提出候选又评估归属时，会不会因筛选而抬高自身读数？应比较同源、移除提议证据、独立/留出 attribution 三种视图。
4. 组强度用哪些分布读数才足够：均值是否同时报告弱尾/离散和覆盖？统计范围用提议成员还是全作用域？不同证据家族能否共用数值量尺？

实验若不能区分选项，就保留并列结果或标未决，不为推进而硬选公式。

### 分阶段路线与判定门

| 步骤 | 工作与产物 | 能作出的裁定 | 不能据此声称 |
| --- | --- | --- | --- |
| 0. 复用审计（已做） | 对照 Stage A–D、D6、旧 furniture_groups、现有 FieldResultEnvelope 和证据生产；列出复用/暂缓项 | 哪些诊断与接口不用重做；哪些实现并非目标强度场 | 旧硬分组是真值，或现有场已算出目标强度 |
| 1. 逻辑契约（部分已做） | 将已有 RGB / driver-modifier / veto / unknown / bridge / 同源依赖 toy 检查整理成可重算矩阵；覆盖空、重复、dangling、共享节点和闭包截断 | 资格、状态、互斥、recipe 的边界语义；哪些候选可称 recipe-极大 | 证据权重正确或现实分组正确 |
| 2. 表示与 profile（底例已复算） | 已复算 RGB 原组/合并/全域、弱桥、missing coverage；继续对照单成员、extent 内 profile/extent 外读数及证据泄漏，并裁定最小可读 profile | 表示能否同时显出强核心、弱合并、弱成员和缺失；保留哪些最小 profile 读数 | 构造数值是真实量尺、强度已校准为概率 |
| 3. 真实解释性 | 对未参与设计且不暴露 authored-group 名称的真实场景做盲审，逐项记录候选、归属读数、证据链与异议 | 证据映射及 profile 是否可解释，哪些规则需回修 | 盲审提供普适 ground truth 或概率校准 |
| 4. 搜索成本 | 只对逻辑门通过的 recipe 测规模、运行/内存和完整性；复用 Stage A 的 37-node 结果作基线，只测新增搜索行为 | 搜索方法、适用范围与预算；超限结果标 incomplete | 运行快就代表语义正确 |

区分实验职责：逻辑 fixture 检查是否遵守目标约束；RGB 等手算/构造场景只检查 profile 表达能力；真实场景盲审检验可解释性；规模实验只回答工程可行性。真实场景不足时第 3 门保持未决，不拿构造数据代替。

### 当前进度与下一步

本轮设计诊断按[分组归属强度实验协议](grouping-strength-design-experiment-protocol.md)执行：先补齐输入资格、归属场与 profile 的可复算用例，再决定能否进入真实场景盲审。该协议是设计验证范围，不是已选定的生产强度公式。

Stage A–D 原设计和 Stage A 计划已核对：最小节点是合格 AuthoredGroup，候选可以跨节点组合、重叠、嵌套和未覆盖；当前 neutral-scene 输入路径仍有通用组误纳入及共享成员 first-wins 的实现差异。旧硬分组只能作对照。Field kernel 只承载证据状态、来源和依赖，不生成候选或成员强度。定向验证命令 pixi run pytest test/test_group_self_description.py test/test_scene_contract.py 通过，140 passed。Stage A 是有限候选与模式诊断；Stage B 合成标签强度门失败，强度仍为 null/not_evaluated，successor 未收敛且 production_ready=false；C/D 目标能力未交付。

2026-10-25 用 Pixi/Python 标准库内存自检复算了 α-cut 极大候选、RGB 的候选内成员均值、均值/中位数/最小值聚合对照、弱桥接、missing pair coverage 和 extent 外读数，全部通过。构造例支持把组强度呈现为成员归属值向量及均值，并附最弱成员和证据覆盖；pair-min 若用于每个成员的主要汇总，会把全域候选压成全员 0.15，抹去强弱差异。故 pair-mean 暂作可解释基线，低尾只作组 profile 读数。此结果只验证算术与表示能力，不验证现实量尺、家族融合或候选规则。

下一步补齐可重算逻辑矩阵：driver 与 modifier 扰动、明确互斥端点、共享/重复/dangling 输入、unknown/conditional/incomplete 闭包，以及 proposal 与 attribution 同源/独立时的读数差异。之后用独立真实场景盲审可解释性；没有合适场景就保留未决。搜索成本等 recipe 语义稳定后再测，并复用 Stage A 的 37-node 基线。未完成设计审查前不恢复拟合、不实现生产算法、不接 UI/API。

## 2026-10-26 讨论记录：排列模式、几何关系与“势一致”

本记录只澄清概念并保存当前讨论结论；**暂不重写或执行实现计划**。讨论方式：一次讨论一个概念；需要用户裁定时提出问题并暂停，收到回答后再记录和继续。计划重写留到证据概念逐项讨论完成之后。

### 找到的原始目标

- [原始评价目标](../indoor_layout_evaluation_matrix_original_prompt.md)（“区域与区域之间的 alignment 程度”及“整体空间的家具组成的势”两节）将区域间 alignment 解释为“家具组组成的总体的势是否对齐”，并要求分别思考区域、家具组、边界和路径的势，尽量输出连续值。整体空间的家具组成势还涉及柱网、路径、边界、房间轮廓，以及局部/全局和多尺度影响。
- [D6 组推断讨论记录](d6-group-inference-grill-notes.md)（“空间场的基础观测与家具组语义”一节）将更贴近成员归属的想法写成“局部支持 / 形成独立势”：空间场、组几何、作者语义和上下文支持要共同观察；少数不同标签元素可能混入周边，也可能形成独立组织。这里明确反对单一通道独断和先定固定权重。
- 历史材料已经给出“势/场”的概念定义和目标关系：它是空间或组关系上的连续组织证据，可有局部方向、吸引/约束以及组间关联、分隔或连接支持；不是物理力，也不要求硬边界或唯一 partition。尚未冻结的是完整特征、邻域/分析单位、尺度、差异度量和生产合成公式。方向/坐标框架只是势的部分描述，不能单独代表完整关系或成员归属。

### 本轮暂定结论

1. **排列模式可先作为已确认的证据家族和候选级用途。**当前可以记录 line/pair/grid/cluster 等模式拟合，或将明确的理想模式作为 recipe 条件；不据此确认成员级归属算法。成员级使用必须先有可审计的“候选家具组—模式槽位”对应。OCTA 的理想模板和家具映射仍待讨论，因此“家族/用途暂定确认”不等于“具体量尺已定”。
2. **组对间距、接触和重叠只是底层几何关系观察。**当前代码对跨组家具成员对测量平面边界 gap、contact、overlap 并保留来源 witness；尚未形成组级归属读数。它们可以成为局部支持/候选提议的输入，但“近就同势”或“远就异势”都没有被定为规则。
3. **用户记得的“势一致”有历史定义依据，且比距离更广。**D6 记录把组关系场定义为组或组对上的连续关系证据，描述关联强弱、分隔或连接；用户的“没有成势可融入、形成自身组织可成为独立候选”例子已记录。原始目标还明确列出家具组对附近有统一趋势对象（如斜墙）的本地顺从，以及区域/整体与柱网、路径、边界的势关系。它们的目标方向已有记录；具体特征、单位和量尺仍待定。
4. **实现状态仍是设计与底层观察分离。**代码已有部分组对几何、模式拟合、方向描述和区域级负空间/路径分析；但没有目标所需的局部支持归属场，也没有统一的候选—上下文势契合量尺。组关系里的自由空间/连通/瓶颈当前仍未计算。

### 用户补充：势至少有不同比较层次（2026-10-26）

用户明确补充：

1. 家具组之间的势应一致或近似一致；差异越大，对它们处在同一场中的支持越弱。
2. 局部环境有墙等对象时，要讨论家具组的势与墙或其他对象是等同/一致，还是形成差异/分野。

这与历史记录中的“组关系连续关联/分隔支持”和“局部顺从”方向一致。用户这次进一步明确了“家具组势差越大，同场支持越弱”的关系方向；现存历史资料未找到把这条方向冻结为特定差异函数或线性比例的依据。

结合原始要求和早期定义，暂建议把比较对象分三层，供用户确认：

| 层次 | 比较对象 | 它回答什么 | 现有资料状态 |
|---|---|---|---|
| 组间组织势 | 家具组与家具组 | 多个家具组是否彼此相容、共同处于同一候选/局部组织场；势差大时同场支持减弱 | 用户已明确关系方向；具体比较哪些特征、如何处理局部与整体差异仍未定 |
| 组—环境局部关系 | 家具组与附近墙、柱或其他 context | 局部家具组织是顺应、对齐、受约束，还是与环境形成差异/分野；边界还可能改变局部场和可参与范围 | 早期原始要求有斜墙方向例子，也记录了墙/边界、阻隔和遮挡的作用；具体参照规则未定 |
| 候选/区域—整体空间势 | 候选或区域整体与柱网、路径、边界、房间轮廓等 | 一个候选/区域与更大空间组织如何契合 | 历史目标明确要求此关系；它如何与前两层归属支持衔接、是否参与候选内部强度，尚未裁定 |

旧 spec 中的 region-force 例子把轴向匹配与位置 phase 分开，再给加权合成；column-grid 例子则先分别输出轴距、bay 中心距、方向三个读数。这些是早期设计草案，不是已实现或校准的比例。当前代码里的 `group_frame/group_axis.coherence` 是方向相干度；组对 gap/contact/overlap 是几何关系；二者都不能代替以上完整势关系。组关系中的 free-space、connectivity、bottleneck 读数仍标为 deferred。

因此，不应再把第三层的“存在”当成待确认项；历史目标已明确包含它。本轮仍需厘清的是，这一整体契合读数如何与候选内部的组间归属支持衔接，以及它是否只作独立下游评价。此问题未裁定前，不定公式。

### 下一项讨论

**待用户确认：**这三层划分是否符合你的意思？尤其第三层“候选/区域与柱网、路径、边界、房间轮廓的整体契合”，你认为它是势的第三层，还是应与前两层（用于形成家具组归属支持）分开？在收到裁定前，不把它写成实现指标或融合公式。

### 历史定义证据与边界

- 用户原始要求[明确把区域间 alignment 说成家具组总体的势是否一致](../indoor_layout_evaluation_matrix_original_prompt.md)，并要求连续表达；同一目标还要求思考家具组、区域、边界、路径、柱网及整体空间势，以及局部/全局和多尺度。这是目标定义，不是完整公式。
- 用户原始要求[明确提出家具对附近统一趋势对象的本地顺从](raw_requirements/source-01-b044dcf0.txt)：斜墙附近家具是否也倾斜是例子；同时明确近邻、连续量和分析单位当时尚待设计。这直接证明组—环境局部关系不是本轮新造的概念。
- D6 讨论[明确记录了“场”和组关系场的定义](d6-group-inference-grill-notes.md)：场是连续势/证据分布；组关系场作用于家具组节点或组对，描述关联强弱、分隔或连接支持；inferred group 可软、重叠、多尺度，不必有明确边界。用户随后确认的少数家具“未成势可融入、形成独立势可独立”的例子，以及空间/几何/语义通道不可独挑大梁，也属于已记录方向。
- 旧 spec 给过 SpatialForce 的方案化描述（局部主方向、attraction/constraint field），以及 region-force 的轴向与 phase 对照和柱网分项读数；旧二维代码也曾以组方向一致和组中心间隔规律组成 `inter` 分数。这些是概念草案或狭义启发式实现，不足以代表完整的非概率归属场，也未构成已校准的统一量尺。
- 当前实现边界仍需与历史原型区分：`features/analyzer.py::_score_inter` 是方向+间距 phase 的旧二维评分；当前 `features/scene_evaluator.py::_whole_space_force_rows` 明确使用 group bounding-box 方向 proxy；当前 `group_self_description` 将组强度及 free-space/connectivity/bottleneck 读数标为 deferred。它们证明有过部分量化/原型，不证明完整归属势场已实现。

### 查证：趋势已有实现（2026-10-26）

用户指出 trend 已有实现。代码核对后确认：**趋势方向及方向一致度已有多处可量化实现**，所以不能笼统说“势/趋势没有实现”；仍未实现的是把这些趋势读数统一成候选内家具组归属场的非概率支持值。

- 单家具：`features/furniture_frame.py::infer_furniture_frame` 从终端平面几何提取主/次轴、范围和方向清晰度；近方形家具可保留低方向强度。
- canonical furniture group / region：`features/scene_inference.py::_furniture_group_frame` 优先汇总最终成员几何 frame，得到角度、strength/coherence、member alignment 和 support；缺少方向性成员证据时以组几何 PCA 作回退。`_group_frame_metadata` 写出 `group-axis-angle`、`group-axis-strength`、`group-axis-support` 等。`_region_frame_mean` 再汇总组 frame，并生成 `axis-angle`、`axis-trend-strength`、`axis-member-alignment` 等区域读数。
- AuthoredGroup 关系描述：`features/group_self_description.py::_directions` 分别产出四方向 frame 和两方向 axis 的角度及 coherence；`_trend_descriptors` 保留成员 frame、整体 covariance axis、成员方向 consensus 和组内布局 axis。其趋势描述可计算，但同一返回值里的归属 `strength` 明确为 `None` / `deferred`；free-space、connectivity、bottleneck 也仍 unavailable/deferred。
- 柱网：`features/column_grid.py` 已为 branch/system 建立局部/全局 trend frame，计算 region 与柱网的 global agreement、bay 范围的 local profile，并支持 field probe evidence。它是区域—柱网关系证据，不等于家具组成员归属场。
- 旧 whole-space force 读数：`features/scene_evaluator.py::_whole_space_force_rows` 已输出组轴集中度以及组对柱网、路径、边界的轴向 agreement，但组方向使用 bbox 长轴 proxy；代码自身说明它不是加权整体势场。

架构边界也已写明：`docs/software-architecture.md` 的 “Group, region, and trend semantics” 规定 group inference 与 trend inference 分离，trend 是从最终世界坐标 `Analysis` 几何和成员 frame 得到的方向组织描述，不得增删拆并 group membership；trend 输出只作为 audit metadata。`features/position_grammar.py` 也明确将 region trend 排除在 position-only candidate 竞争之外。因此，已有趋势可作为理解组自身方向组织的量化资料，但当前架构没有让它决定候选成员归属。

因此当前能复用的“trend”读数包括方向角、方向清晰度/集中度、成员方向一致度，以及与显式柱网/环境轴的比较。这里的 strength/coherence 描述方向集中或成员 frame 一致，support 描述方向性成员证据量；这些字段都不是候选成员归属概率或归属强度。它们各自的对象、范围和量尺不同，不能未经讨论就视为同一种势；也没有现成读数直接回答“一个候选内每个家具组的归属支持是多少”。测试已覆盖单家具方向清晰度、成员几何驱动的组趋势、组内 frame/axis coherence、区域趋势和柱网 local/global profile；这些测试证明实现与接口存在，不构成现实归属解释性或量尺校准。

### 用户澄清：家具组势特征与上层组势（2026-10-26）

用户说明的概念层次如下，先记录语义，不据此补写计算公式：

1. **势1属于一个家具组自身，是该组的一种特征。**
2. **势1之间的相似性是一项关系证据。**它可支持这些家具组共同组织起来，但不是单独裁定归属的答案。
3. **由相似势1组成的上层组，具有该组自己的平均势力。**这与单个家具组所带的势1是不同层次。
4. **组内势1有多杂乱、不统一，反映趋势相似性有多强或多弱。**

这使现有趋势实现有了更明确的可能用途：它可能提供家具组自身势特征的某些可量化分量，再用于势1之间的相似性证据；上层组势及其内部一致程度则是更高层的描述。当前代码里的方向角、frame/axis coherence 可作为待映射的现有量，但尚未确认它们就是“势1”的全部或唯一内容；如何定义相似、如何表示平均势、怎样用组内离散/杂乱度表达趋势相似性仍待讨论。不得把这里的“平均”直接等同于已选定的数值聚合公式。

### 现有实现核查：势1相关读数的实际结构（2026-10-26）

代码和 D6 设计文档显示，当前已有实现不是一个单一“势1”字段，而是几类分开的确定性描述：

| 层 | 当前实现 | 实际含义 |
|---|---|---|
| 单家具特征 | `furniture_frame.infer_furniture_frame` | 由终端 `Analysis MassPatch` 的面积加权 PCA 得到主/次轴、范围、`orientation_strength`；strength 是形状方向集中度，不是组势或归属值。 |
| 组内成员方向共识 | `group_self_description._directions`、`scene_inference._member_frame_consensus` | 对有方向性的成员按几何各向异性加权，计算 `group_frame` / `group_axis` 角度与 `coherence`。`group_frame` 使用 4θ，0° 与 90° 视为同一正交 frame；`group_axis` 使用 2θ，0° 与 90° 不等价。 |
| 组整体形状轴 | `group_self_description._trend_descriptors` | `overall_group_axis` 由总 covariance PCA 得到，包含家具自身形状分布和成员中心分布；`layout_axis` 只看成员中心之间的排布。它们不是同一个 estimand。 |
| canonical group trend | `scene_inference._furniture_group_frame` | 有成员方向证据时采用 member frame consensus；否则用 affordance/member 点云 PCA 回退。输出 `group-axis-angle`、`group-axis-strength`、`group-axis-member-alignment`、`group-axis-support` 等。 |
| 上层区域趋势 | `scene_inference._region_frame_mean` | 将多个 furniture group 的 frame 用 4θ 向量平均，得到 region angle、strength、clarity 和 member alignment。这最接近“相似势组成上层平均势”，但它是区域描述，不生成新候选，也不做组间归属。 |

当前实现中的两个关键限制：

1. **权重和对象尚未统一。** `group_self_description` 的方向共识使用 `area × anisotropy`；`scene_inference` 的 canonical member frame weight 使用终端几何 aspect clarity。两者都合理地描述方向证据，但不是同一量尺。
2. **没有现成的组对趋势相似性记录。** `group_self_description._group_relations` 当前只记录成员 pair 的 gap/contact/overlap、语义负证据和状态；没有输出 group A 与 group B 的 trend distance/similarity。区域 frame mean 是多组汇总，不是 pairwise trend evidence。

一个现有实现行为的最小检查：两个同样强、一个水平一个竖直的成员，会得到 `group_frame.coherence=1.0`，因为 4θ 把正交方向视为同一 frame；同一输入的 `group_axis.coherence≈0`，因为 2θ 将水平与竖直视为不同主轴。说明“组内杂乱/趋势相似性”必须先声明比较的是 frame 还是 axis，不能只看字段名 `strength`。

D6 目标语义表已把这一边界写成：趋势一致是独立 descriptor，首轮不用于 membership；当前生产实现也遵守这一点。现有实现因此可以提供势1的候选特征和未来相似性计算的输入，但尚未实现“势1相似 → 组对证据 → 上层组平均势”的完整链路。

### 用户确认：势1采用结构化特征向量（2026-10-26）

用户确认：势1应理解为一个家具组自身的结构化特征向量，而不是单一角度或单一 `strength`。当前确认的主要分量是：

- 方向组织：`group_frame` / `group_axis` 及其角度；
- 形状轴：组整体或成员几何的主轴、各向异性和形状清晰度；
- 成员排布：`layout_axis`、成员中心分布及其组内排布结构。

这些分量共同描述一个家具组的势1。两个家具组之间的比较应产生势1相似性证据；相似势1组成上层候选后，再形成上层平均势，并保留组内势1的离散/杂乱程度。现有 `coherence`、`orientation_strength`、PCA strength 和布局轴是这些分量的候选读数，但不能直接互换或压成一个已经批准的总分。

用户进一步确认：`orientation_strength`、`coherence`、`member_support` 等字段与势1本体分开保留。它们表示方向/几何证据的集中度、支持量或观测完整性，不直接作为势1向量的本体分量；缺失/无效状态同样属于 provenance/status。这样可以分别描述“组具有什么势1”和“这个势1被当前证据支持得多完整”。

因此当前约定是：势1本体先由方向组织、形状轴和成员排布等结构特征组成；strength/coherence/support 作为伴随证据质量字段。上层平均势也应保留这两层，不得用质量字段替代势1本体，也不得把质量字段默默乘进平均势而不留下来源。

用户确认：组间势1相似性先按分通道保留，不立即压成一个总相似度。至少分别记录方向相似、形状相似和成员排布相似，并保留各通道的来源、状态与缺失/冲突信息。若未来需要整体摘要，也必须能追溯到这些分通道读数；在共同量尺和权重未定前，整体摘要不能用于候选裁决。

用户进一步确认：上层组势也按通道分别形成平均势，并保留每个通道自己的离散/杂乱度。方向、形状、成员排布分别聚合；不能先把三者压成一个总向量再只保留一个总离散度。当前 `scene_inference._region_frame_mean` 只覆盖方向 frame 的一部分，不能代表完整的上层势聚合；形状轴、布局轴及其离散度仍待设计。

用户确认方向通道同时保留两个子通道：`group_frame` 与 `group_axis`。前者使用 4θ 语义，把 0°/90° 视为同一正交 frame；后者使用 2θ 语义，把 0°/90° 视为不同无向主轴。两者分别计算组间相似性、上层平均和离散度，不互相替代，也不压成单一方向值。

### 形状与排布的分界裁定（2026-10-26）

根据现有 covariance 分解和可解释性，势1采用以下边界：

- **形状通道**使用 `within_member_covariance`，描述成员家具自身的形状分布；它对成员平移不敏感。
- **排布通道**使用 `between_member_covariance` 及 `layout_axis`，描述成员中心的空间排列；它不把家具自身尺寸误当成组内排布。
- **`overall_group_axis`** 是两者之和形成的组合诊断，保留用于整体外观/兼容性检查，但不作为形状或排布主通道，以免重复计入同一证据。

这个选择的优点是三个通道职责清楚：方向描述成员方向组织，形状描述成员自身，排布描述成员位置关系。代价是如果业务问题需要“组的外包络形状”，它不能直接由形状通道回答，必须另列组合诊断，不能偷偷把 `overall_group_axis` 当作纯形状。

用户确认：形状通道还要把**形态**与**尺度**分开保留。形态包括比例、各向异性、形状轴和清晰度；尺度包括面积、体积、主次范围等几何大小证据。尺度证据可以参与组间关系诊断，但不能未经声明并入形态相似度或替代势1本体。

### 绝对位置暂缓裁定（2026-10-26）

用户指出绝对位置可能承担其他作用，目前不是决定它是否进入势1的合适时机。因此暂不把绝对位置纳入或排除势1本体：组内相对排布仍有现成的 `between_member_covariance` / `layout_axis` 读数，绝对位置作为可独立引用的环境/区域证据保留，具体与势1、组—环境关系及上层场的衔接留待后续讨论。不得因当前未决而把绝对位置填零或当作无关证据。

### 增补开发路线（2026-10-26）

用户确认采用增补式开发，不重写现有 Stage A–D、协议、spec 或主实施计划。当前执行顺序调整为：先完成输入身份/状态门，再建立只使用**组间几何关系**的首个分组证据场；首包只包装现有成员对的边界间隙、接触、正面积重叠、重叠面积和 witness/source refs，并通过共享 `FieldResultEnvelope` / `EvidenceChannelRecord` 接入。这个场是结构化关系证据，不是支持分数、势1相似度、正式归属边、候选选择或强度。

后续 trend、语义标签、自由空间、墙体/边界、排列模式等证据必须逐个讨论其几何或标签输入、规则、状态和输出通道后，作为独立证据包接入同一 Field core；证据包可以包含自己的几何计算和逻辑，但不得把规则写入 `field_core.py`，也不得因此引入第二套 field kernel、通用插件框架或隐式 selector。每个已实现证据包都要在项目文档中记录输入、输出、状态、来源、未决边界和 focused 验证结果。

这条路线已写入[家具组归属证据场实施计划](../superpowers/plans/2026-10-26-group-attribution-evidence-field-implementation.md)的“阶段 1B”。阶段 1B 完成后先停止并审阅几何场，再讨论下一个证据包；当前不把几何关系观察描述为现实强度验证，也不改变 free-space/live promotion 的现状。

### 首个几何关系证据包的当前实现状态（2026-10-27）

`features/group_geometry_relation_field.py` 已把指定 IFC 的 authored-group
成员对观察接入共享 `FieldResultEnvelope`。它只提供边界间隙、接触和正面积
重叠三个 descriptive 通道，保留 member pair、witness、source refs、单位、
状态和 shared-member 依赖；不提供势1、支持、归属、强度或 winner。真实 IFC
初版契约测试已通过 666 个无序组对。本轮完整结果已交付：37 组、95 成员、
666 组对全部映射到对应 JSON/SVG，另有总览及来源/平面/单位 manifest；
667 张 SVG 均可解析，总览、近距、远距、接触 PNG 样本已目视审阅。
修正后的扩展契约测试在本次保留的真实 IFC scene/description 上重放通过，
不代表独立重新提取几何通过。当前源只有 computed 的间隙/接触关系；正面积
重叠、共享成员及 missing/invalid/partial 等分支仍未覆盖，不能写成已验证。
详见[首包验证记录](evidence/geometry-relation-field-package-v1.md#current-verification-and-limits)。
阶段 1B 按当前源覆盖范围完成交付。2026-10-27 用户对总览、分离组对和接触
示例的审阅范围答复“合理”，用户样本审阅门通过；未覆盖分支及其他平面的
验证限制不变。下一步先澄清阶段 2 所需的证据用途/规则；完整候选×单元
归属场、强度与下一证据包尚未推进。

### 第二个证据包：势/趋势对齐（2026-10-27）

用户同意先把已有趋势实现作为独立、可审计的第二证据包接入共享 Field core。
该包以一个 `furniture_group` 为 target，保留四个并行通道：
`overall_group_axis`、`member_frame`、`member_axis`、`layout_axis`。每个通道
分别保留 typed `Analysis` bindings、source/provenance、状态和诊断证据；现有
`strength`/`coherence` 只表示几何集中度或成员方向一致度，不是势1强度、组势、
归属支持或最终标量。当前 IFC 全量只读诊断已产生 37 个 group Envelope 和
148 张同一分析平面的 SVG，详情见[趋势证据包记录](evidence/group-trend-alignment-field-package-v1.md)。

这一步只证明已有事实可以被结构化承载，不决定四通道如何合成，也不改变组的
无硬边界设计；potential、membership、candidate、winner、权重、阈值和强度
仍未决。当前 IFC 没有出现 partial/invalid/not_available 趋势成员，因此这些
状态的传播仍由契约保留、待后续真实来源覆盖。

2026-10-27 用户补充：当前先用 world-XY，但后续需要切换。证据包的 query
必须与 `scene.context.analysis_plane` 一致，图面也使用该平面的局部坐标；
world-XY 是当前数据上下文的选择，不得写死成证据规则。相机接入本身另行处理。

### 用户确认：间隙的软关联方向与无硬边界组织（2026-10-27）

用户确认组间距离可作软关联证据：较近关联倾向较强，较远逐渐减弱。同时明确
“组本身没有边界，不存在是否同组这种情况，但是又要有组的这种定性功能，
这样才能计算总的朝向”。后续讨论不再使用“是否同组”作为上层组织的判定目标。
这里的无硬边界针对待推断的上层组织；IFC AuthoredGroup 仍保留来源声明，作为
已经确认的最小输入单元。此确认未选定衰减公式、数值量尺、阈值或成员对到组对
的聚合；接触/重叠继续独立保留，也不自动等同势一致。

### 待审草案：组织视图、软参与与总体朝向（2026-10-27）

沿用现有候选/完整作用域场，建议将上层组解释为有身份、尺度和来源的组织视图。
组织视图保留冻结 scope 内每个 AuthoredGroup 的逐通道证据；今后只有映射经审阅
后，才可形成相应软参与权重。一个输入单元可以参与多个视图，各视图读数无需
加和为 1。当前组对间隙观察不等于这份候选×单元参与分布，不能把某一行距离
直接宣布为完整上层组，也不通过阈值或连通分量制造唯一分区。

总体朝向作为组织视图的下游描述：在参与权重有依据后，分别汇总已有 frame 和
axis 方向，保留各自平均方向、离散/一致程度、覆盖、状态和来源依赖。方向
质量字段与参与程度继续分开，不默认把 coherence/strength 乘入权重。方向抵消
或缺失时保留“总体方向不明确”及原分布，不能硬造一个代表角度。组织定性可以
通过可指认的视图身份、尺度、参与分布和方向描述表达，不要求硬成员名单或
空间边界。IFC 平面展示可用各输入组的渐变参与着色与方向标记，绘图方式未实施。

现有 proposal_extent 继续只记录提议来源范围，不得作为参与度的硬截断；新设计
的总体方向拟按完整作用域的有效参与贡献汇总，与原有 extent 内 profile 分开。
若此草案获认可，须先把这个输出/汇总边界补入 spec 和 checklist，再实现。

本轮仍以间隙几何作为组织依据；已有方向描述只是待接入的下游汇总输入，不
隐式加入方向相似性证据包。若将来用方向相似性影响组织形成，需另行讨论并
记录与方向一致度读数的同源依赖，不把它当独立验证。

用户于 2026-10-27 表示“你觉得没问题我暂且同意”。因此“有身份、无硬边界、
可重叠参与的组织视图”暂作为结构基线；这不是候选 recipe、参与公式、标量 M
或新增方向包的最终批准。下一项单独讨论组织视图如何提出，以及组间距离怎样
转成各家具组的软参与程度；在这两项没有裁定前不实现归属读数。

### 待审草案：组织视图的提出方式（2026-10-27）

**术语说明：**“组织视图”不是新增的代码对象；这里仅作为计划/spec 中“候选
组织方式/候选组织视图”的通俗称呼，对应 `k`、`P=(recipe, scope,
proposal_extent, closure_status, proposal_evidence)` 和 `E(g,k,s)`。下面的
`seed/seed-set` 只是待讨论的候选提出方案，不是原计划已经批准的机制。

仅有组对关系时，系统还不知道哪些家具组共同贡献一个“总体朝向”；因此建议
先为组织视图保留可追踪的 `seed/seed-set + scale + scope + recipe` 身份。seed
可以是一个已有 AuthoredGroup，也可以是经后续规则提出的一小组起点；它只是
视图的起点，不是成员真值。冻结作用域内的每个 AuthoredGroup 都仍生成参与记录，
所以视图之间可以重叠，不能用连通分量、硬阈值或唯一分区替代它。

`proposal_extent` 只表示该视图由 recipe 提出的观察范围，不是边界；范围外但
仍在 scope 内的家具组继续保留软参与/边界张力记录。几何首包先只提供组对关系
观察，seed 如何扩展以及间隙如何映射为参与度仍待裁定。若采用这个表示，整体
朝向就能在一个有身份的视图上汇总，同时保留完整 scope 的贡献分布。
