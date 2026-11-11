# 距离衰减开发笔记

日期：2026-11-11。状态：**讨论草案，尚未冻结衰减公式或实现。首轮只使用欧几里得距离。**

## 工作线与范围

- jj workspace：`group-distance-decay`，路径 `D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/group-distance-decay`。
- 本地 bookmark：`codex/group-distance-decay`；基线 `d0e7e73a0585e8011220d8c7dccb4ab16a6508e5`；首个 change ID：`zuwxrrnywlowmywroomxvnuwpkvtwlln`。Owner 是唯一版本写入者；本轮首个提交只新增本笔记，不推送、不合并。
- 继承[目标边界](grouping-goal-alignment.md)和[证据包最小规范](../superpowers/specs/2026-10-30-evidence-package-minimal-standard.md)。本研究接续[大 checklist 的距离交付](../superpowers/plans/2026-10-26-group-attribution-evidence-field-implementation.md)，不改写既有阶段、不提前勾选验收。
- 只讨论家具组整体之间的关系。保留纯轴、组间关系、合力、hierarchy 及全部原始距离；距离条件结果只能具名追加。场允许重叠，不生成唯一硬分组或边界。

## 已确认的要求

1. 衰减连续发生；不人为设置有效半径、近远阈值、截断距离或邻居数量。不把自动取均值、中位数或第几个近邻伪称没有尺度假设。
2. 房间扩大或增添无关家具、但该组对几何和通路未变时，该组对的距离响应应不变。整体场可以因其他有效关系而改变；缓存也可以因全量失效策略而需要重新核验。
3. 单位换算不改变结果；不能用全房最大距离、家具数量或全场距离分布暗中改变原组对的量尺。
4. 距离项可以选择一个或多个距离。**首轮选择集只有 `euclidean_distance`；不读取 `path_distance` 的数值、不以其渠道可用性作为纯欧氏计算条件。**共享包级 freshness 仍按既有契约执行。
5. 原始米值是描述量，不是越大越支持的证据。派生支持须非负、越大越支持，并保留原值、状态、公式、尺度和来源；数值归一到 `[0,1]` 不等于已经客观校准。

## 距离选择与未来组合口

复用现有 `EvidencePackageChannelReference` / `EvidencePackageDependency`，不新增包框架、注册表或专用距离类型。

| 位置 | 本轮规定 | 后续扩展边界 |
| --- | --- | --- |
| 选择 | 每个实际无序组对选择一个完整的 `package/output/target/channel` 引用 | 可选择多个具名引用；同名渠道的不同组对必须分开定位 |
| 读取 | 固定质心到质心 `euclidean_distance`，单位 m | 核对源、端点组对、分析平面、域/范围、单位以及各自查询语义是否相容 |
| 解释 | 原始距离通过具名、带版本的衰减函数产生距离响应 | 每个距离先保留自己的响应，再进入显式组合函数；原始距离与分项响应均不得丢弃 |
| 组合 | 单输入恒等：`H({w_E}) = w_E` | 多输入必须声明组合方法、版本、输入角色、参数和状态策略；没有这些声明就不产出联合数值 |
| 输出 | 原始距离引用 + 响应定义/尺度 + 状态 + lineage | 联合结果具名追加；它不是新的独立票数，也不能把同一距离重复计权 |

推荐的数据流为 `选择距离 → 分别解释/衰减 → 显式组合 → 可选地调制方向支持`。这是接口草案，不是新增运行时 API。每段计算、函数版本、实际依赖与产物仍由现有渠道/输出函数管理。

首轮设计唯一选定的配方是 `single/identity`；多距离的语义现在写明，业务实现继续暂缓：

| 具名配方 | 对已解释响应的计算 | 声明命题 | 启用状态 |
| --- | --- | --- | --- |
| `single/identity` | `H(w)=w` | 只采用所选距离的接近支持 | 首轮唯一选用，待实现 |
| `joint/all-min` | `H(w_1,...,w_n)=min(w_1,...,w_n)` | 每个声明的接近条件都必要，取最弱支持 | 未来可选，未启用、非默认 |
| `alternative/any-max` | `H(w_1,...,w_n)=max(w_1,...,w_n)` | 输入明确是替代条件，其中一个支持就足够 | 未来可选，未启用、非默认 |

这些是命题组合语义，不是普适融合定律，不声明证据独立、概率含义或客观校准。不能仅因渠道可用就自动选择 all 或 any；也不能先平均原始距离，再把它冒充逐项解释后的组合。

三种配方均要求单输入恒等、输出 `[0,1]`、连续、对每路支持非递减；每路距离响应自身须随距离非增，因此距离增加不会增强联合支持。同角色对称输入应置换不变，重复同值不改变结果（幂等）。端点 `0/1` 表示声明命题的无支持/满支持，不是客观概率。

min/max 有平台：`min(.9,.4)=min(.7,.4)=.4`，所以不保证每路变化都严格改变标量。**组合标量不能完整传达所有渠道，必须保留全部原始距离与分项响应向量；展示或消费联合值时仍可追溯它们。**

欧氏与路径的特殊支配关系须显式记录：同端点、同平面、同单位的有效路径有 `d_P >= d_E`；若两者采用相同的递减核和尺度，则：

```text
w_P <= w_E
min(w_E,w_P) = w_P
max(w_E,w_P) = w_E
```

当前路径由质心偏移段加自由空间折线组成；上述不等式不要求路径已经证明最短，但须核对数值及浮点容差。因此 E+path 不是两条独立票数；不得只为强迫两路影响标量而发明不同尺度。

均值、乘积和 soft OR 均不作为默认配方。重复同一事实也会改变它们的值：`mean(.2,.8)=.5`、重复 `.8` 后为 `.6`；`.4*.4=.16`，soft OR `1-(1-.4)^2=.64`，均非新增独立事实。其他配方留待其命题和重复处理有依据时再设计。

沿用既有依赖契约，拒绝重复完整 `package/output/target/channel` 引用，绝不因重复得到额外票数。不同引用也不自动代表独立事实。

空选择集或任一必需输入缺失、unknown、outside、invalid、stale/unavailable 时不产出联合数值；保留分项和原因，不填零、不假装无限远、不临时删项或改变分母。partial 的使用条件须由配方声明，未声明不放行。当前距离包会把 raw `unreachable` 映射为共享 `computed`，但值可为 `None`；因此 `computed` 单独不足，必须核对 `raw_status` 及有限非负原始值。确证不可达如何支持某命题仍未裁定，纯欧氏输出不靠路径失败裁定。

配方直接归现有渠道/输出函数所有，最少记录：

```text
recipe_id/version + 输入角色与完整渠道引用
每路 kernel/version + 参数/尺度 + 原始值和响应
operator/version + 角色语义 + 必需输入/状态策略
实际 lineage + 既有 output/cache identity
```

角色按明确顺序绑定；同角色对称输入按完整引用规范排序，以维持身份稳定。上述内容参与既有输出/缓存身份，不新增类、注册表或组合框架。原缓存中的未选渠道继续保留；不把包级 freshness 改成渠道级架构。首轮欧氏计算不依赖路径数值或状态，既有包级 freshness 校验除外。

## 上一轮衰减草案：保留尺度响应，不先定唯一范围

一种待比较的表达是：

```text
d_E(g,a) = 两个家具组整体投影 union 的固定质心间欧氏距离
w_E(g,a; ell) = exp(-d_E(g,a) / ell), ell > 0
C_E(g,a; ell) = A(g,a) * w_E(g,a; ell)
```

`A(g,a)` 是已有源轴视图中 g 对参照组 a 的方向支持，不新造方向总分；a 是参照家具组，不是场区域。`ell` 与距离同单位，是响应曲线的尺度坐标，**不是已选好的有效半径**。先完整保留 `d_E` 和函数定义；查询尺度不重新计算几何距离。欧氏组对缓存只有非自组对，自项语义另循原势包规则，不伪造自组对缓存。

在固定 `ell`、有限非负距离和有效输入下，该候选数学上连续、落在 `[0,1]`，且距离越大响应越弱；相同距离在相同尺度使用同一函数。单位换算必须同时换算 d 与 ell。整体布局实际放大不是单位换算，不能擅自宣称固定物理尺度下结果仍不变。数值下溢不能被解释为硬边界或无归属。

**这还没有解决自然定标。**指数形状也是模型假设；保留多尺度只是没有先挑唯一尺度，不等于已找到唯一客观强度，也不等于用户接受多尺度作为最终结果。不得偷选一个 ell、对任意尺度区间平均，或让显示采样范围成为算法截断。若后续必须产出单个数值，尺度或消去尺度的规则仍需有可辩护依据。

## 条件尺度分析与单一 IFC 试验选择（2026-11-11）

若无其他输入，无量纲函数仅有长度 `d>0`，任意单位换算不变要求 `F(c*d)=F(d)`，故它只能在正距离上恒定；非恒定无量纲衰减需要额外尺度。这不排除有量纲的 `1/d`、`1/d²`，但它们在 `d=0` 奇异，也不是已归一、有界可比的支持。

用户条件为：若有足够充分理由可用组整体尺寸作参照；这是有条件的试验许可，不是公式或视觉验收。Owner 仅选一套可回退的真实 IFC **试验定义**，含义是“间距相对于两个家具组整体的分布尺度”：

```text
U_g = 家具组实际投影 union；A_g = area(U_g)；c_g = centroid(U_g)
rho_g² = (1/A_g) * ∫[U_g] ||x-c_g||² dA
ell(g,h) = sqrt(rho_g² + rho_h²)
q(g,h) = d_E(g,h) / ell(g,h)
w(g,h) = exp(-q(g,h))
```

`rho` 是组整体的面积均方根半径；选平方和根（RSS）而非半径求和，是因为两个 union 按占用面积均匀独立取点并各自中心化后，`E[||(X_g-c_g)-(X_h-c_h)||²]=rho_g²+rho_h²`；未中心化的点差均方还包含 `d_E²`。这只是定义几何尺度的恒等式，不是概率归属，也不声称两条证据独立；不需要真的随机采样。

只接受有限、有效、正面积的整体 union；孔洞不计、重叠只计一次，不换成成员中心采样、PCA 轴长或凸包。`ell` 必须有限且为正；失败保留原因而不产数值，不加任意 epsilon。`d=0` 时 `w=1` 只表示质心重合，不表示同组或几何相同。

固定组形状时，距离增大使响应连续严格下降；米/毫米换算、整体平移旋转、等比例缩放均不改变 `q,w`。无关家具或房间边界变化不改这两个组的几何和距离时，响应不变；单组绕自身质心刚体旋转不改 `rho`。尺度不读取全场分布，不设有效半径、阈值、邻居数或拟合系数；指数曲线本身仍是试验假设。

此尺度各向同性，会忽略长薄组的方向差异，分散或远离主体的小块可能抬高尺度；文献没有裁定面积尺度、分布尺度和方向尺度谁适合家具组，不能把本选择称为唯一自然定标。

输入须取同一已认证场景/平面/组身份下的完整 union。[`_group_geometry`](../../features/group_distance.py#L312) 已以整体 union 计算质心和 `union_area`；现有欧氏输出不能仅靠面积与质心恢复该二阶矩，需从核验后的输入几何计算并记录实际来源，不能宣称已经缓存 `rho`。本轮不重算距离，不实现代码；保持既有原始米值、纯轴及全部旧渠道。

固定几何来源：[保留的 input bundle](D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge/outputs/design/group_distance_ifc/run_v4_eight_neighbor/input_bundle.json)，SHA-256 `28e5304317ef52519d4c6d8c37ff17495032ec331f63e8333d7f15df72a1f93d`；沿用 [`run_group_distance_ifc.py:416`](../../scripts/design/group_level/run_group_distance_ifc.py#L416) 的 `retained_input` 指纹核对，再由 `_group_geometry` 取得实际 union。同 bundle 的独立内存审计得到 37 个有效 union 的 RMS 半径（Pixi exit 0），只证明输入可计算，`rho` 仍非现有缓存输出，未运行衰减。

当前距离为 camera plane、旧势包为 world plane；未对齐 source、plane、scope 与组身份前，只试距离响应，禁止直接相乘。后续产物记录 `d_E`、`rho_g/rho_h`、`ell`、`q`、`w`、几何指纹和函数版本，沿用现有状态/lineage/cache 规则。

支持与限制的直接依据：

- [Gillam (1981)](https://doi.org/10.1037//0096-1523.7.4.884)：PubMed 原摘要核验，线条分组取决于分离相对于线长；支持相对尺寸的启发，不验证家具组或 RSS 尺度。
- [Zucker & Davis (1988)](https://doi.org/10.1068/p170229)：出版社原摘要核验，点尺寸与间距比例影响分组；不移植其中视觉条件或阈值，不支持某条家具衰减曲线。
- [Zelnik-Manor & Perona (2004), §2](https://papers.nips.cc/paper/2619-self-tuning-spectral-clustering.pdf)：原 PDF 核验，局部尺度来自第 K 邻居（文中实验 `K=7`）；引入邻居数，新增其他点可改固定组对尺度，故不满足本轮无邻居选择及无关变化不改响应的要求。

## 复用位置、缓存与首轮观察

- [共享核心](../../features/field_core.py)：`EvidencePackageChannelReference`、`resolve_evidence_package_channel`、输出及 freshness 校验。
- [距离包](../../features/group_distance_evidence_package.py)：现有 `euclidean_distance` / `path_distance` 两通道；原始渠道定义和缓存均不改。
- [势包](../../features/group_axis_potential_field.py)：已有纯方向支持；距离调制尚未实现。
- [最新距离交付证据](evidence/group-distance-ifc-v1.md#two-channel-distance-evidence-publication--2026-11-07)：37 组、666 对、1,332 个距离输出。实际缓存位于 `D:/PROJECTS/understandOtherPackage/order_analyzer_free_space_distance_bridge_proxy/outputs/design/group_distance_ifc/run_global_full_current_20261106_merged/distance_evidence_package/group_distance_package_output.json`；不要把 sibling 产物说成本工作区已经生成。

未来结果身份须绑定选择的渠道引用、完整输入内容、衰减/组合函数版本及实际使用的尺度；复用现有内容指纹与 freshness，不只相信旧 `fresh` 收据。改变衰减函数不要求重新寻路；原距离可否复用仍须校验真实依赖。未选路径不作为数值输入，包级失效边界不在本轮改成渠道级失效。

保存读回放行数值前须独立提供 `current_source_envelopes`，核对 `target/query/channel_set/cache_identity/raw_status/value/support/source_ids`；上下文缺失为 unavailable，来源、query 或 plane 不匹配则拒绝。旧 `fresh` 收据不能替代这道现有检查。

## 外部依据与设计边界（2026-11-11）

- **模糊交并语义：** [Yager (1979), *A measurement-informational discussion of fuzzy union and intersection*](https://doi.org/10.1016/S0020-7373(79)80016-4) 的摘要/索引核验支持在 ordinal membership 下采用 min/max 的交/并语义，不证明它们是所有证据融合的普适规则。[Zadeh (1965)](https://doi.org/10.1016/S0019-9958(65)90241-X) 仅作原始文献线索，本轮未取得全文，不列为全文核验依据。
- **接近分组（摘要/索引核验）：** [Kubovy & Wagemans (1995)](https://doi.org/10.1111/j.1467-9280.1995.tb00597.x) 对点阵知觉分组提出带实验参数的指数距离吸引函数；[Kubovy, Holcombe & Wagemans (1998)](https://doi.org/10.1006/cogp.1997.0673) 分析多稳态点阵分组，报告相对分组强度近似随相对点距指数下降。这些支持感知分组中的候选形式，实验对象与参数都不是家具组的米制定标。
- **心理距离（原文 p.1317、p.1321 核验）：** [Shepard (1987)](https://doi.org/10.1126/science.3629243) 讨论心理空间中的概化概率随心理距离指数衰减；心理距离及该命题不能直接移植为家具间物理米距的事实。
- **实现参考（固定提交源码实读）：** 官方 [scikit-fuzzy `fuzzy_and`/`fuzzy_or`](https://github.com/scikit-fuzzy/scikit-fuzzy/blob/be7e344f3ce65845e39922aa5fc1af7412d01944/skfuzzy/fuzzymath/fuzzy_logic.py#L83-L134) 以 `np.fmin`/`np.fmax` 实现 min/max；官方 [scikit-learn `RBF`](https://github.com/scikit-learn/scikit-learn/blob/98408191f7e021819b5b39c82db92c116ed03619/sklearn/gaussian_process/kernels.py#L1421-L1541) 展示带 length scale 的平方指数核，[`Matern(nu=.5)`](https://github.com/scikit-learn/scikit-learn/blob/98408191f7e021819b5b39c82db92c116ed03619/sklearn/gaussian_process/kernels.py#L1683-L1692) 对应候选 `exp(-d/ell)`。它们不决定本项目的语义、尺度或状态门；NumPy 官方 [`fmin`](https://numpy.org/doc/stable/reference/generated/numpy.fmin.html)/[`fmax`](https://numpy.org/doc/stable/reference/generated/numpy.fmax.html) 在一侧 NaN、另一侧数值有效时返回有效侧，两侧均 NaN 才返回 NaN，不能替代“必需输入缺失则不产联合值”的校验。当前标量运算不需新增依赖。

结论：保留 `raw → per-channel response → explicit named combination → provenance/status/cache`。首轮 `identity + Euclidean` 仅为待实现选择；指数衰减仍是候选，不冻结，也不称为家具布局的客观定律。自然尺度仍未解决。

首轮视觉目标：仅用指定真实 IFC 的欧氏距离，先看同一批组对的原始距离和候选响应曲线；若展示几个尺度切片，明确它们只是图面采样，未被选为事实或生产默认。不得新造模拟布局来获得理想衰减效果。未对齐势与距离的源、组身份、分析平面及范围前，只能看距离响应，不能将两套旧缓存直接相乘。

## 持续维护 checklist

执行中每完成一项都补充真实证据并更新勾选；发现偏离或未决先记录，不用实现结果反向改掉要求。

- [x] 新建独立 jj workspace / bookmark；首个新增文件是本开发笔记。
- [x] 记录用户约束、仅欧氏首轮、单距/多距输入口；本轮细化 identity、all/min、any/max 的语义、限制、状态与缓存契约，多距配方未启用。
- [x] 保存上一轮多尺度候选，明确没有冻结公式或解决自然定标。
- [x] 初版独立审查（2026-11-11）：SPEC PASS / QUALITY Approved；7 个本地链接及代码定位核验通过，补齐独立 `current_source_envelopes` 放行门。该记录不代表本轮修订已重新通过独立验收。
- [x] 本轮数学审查：Pixi 内存标量断言 1,251 项通过（exit 0）；检查恒等、范围、单调、交换/幂等、响应变换、路径支配与重复反例。连续性按算子代数核对，有限采样不充当证明；修订独立设计审阅 PASS，仅修正选用/已实现的措辞区分；无 IFC、Blender 或业务实现验收。
- [x] 外部依据审查（2026-11-11）：Yager/Kubovy 为摘要/索引核验，Shepard 为原文核验，GitHub/NumPy 为源码/官方文档实读；Zadeh 仅未全文核验线索。独立引用审查已修正 Yager DOI 和 Matern 源码位置；仍未解决家具米制自然尺度。
- [x] Owner 裁定单一试验尺度/曲线：整体 union 的 RMS 半径 RSS + 欧氏指数响应；有条件、可回退，非最终自然定标或生产公式冻结。
- [x] 本轮单一试验设计独立复核：SPEC PASS / QUALITY Approved；候选 SHA-256 `A0E39F185E6EE461E45E9AC672C058D358428A82C8DEFB98B4827ED74FCFD0E8`，8 个本地链接检查 exit 0；输入 readiness 不等于衰减验收，尺度依赖与图面交接尚待完成。
- [ ] 核验试验输入几何、缓存身份与可视化交接口径；需要方向调制时先核对同源、同平面和同范围。
- [ ] 实现最小欧氏试验，复用已认证缓存；记录函数版本及输入身份。
- [ ] 用指定 IFC 产出欧氏对照图；核验连续性、单调性、单位换算及无关场景变化不改组对数学响应；区分技术检查与用户视觉结论。
- [ ] 根据观察回到自然定标问题；多距离组合实现继续暂缓，其可选配方与接口设计已明确，不因预留而提前实现。

本轮仅细化设计笔记，不表示公式冻结、自然定标、试验、主线整合、距离调制势或视觉验收已完成。
