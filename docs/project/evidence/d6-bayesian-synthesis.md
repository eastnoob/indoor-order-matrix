# D6 Bayesian 场景自描述证据综合

- 研究日期：2026-09-28
- 状态：增量文献综合；不选择生产模型、不改变生产接口、不启动 Task 3b 或 Task 4。
- 证据账本：[`d6-bayesian-evidence-ledger.md`](d6-bayesian-evidence-ledger.md)
- 检索记录：[`d6-bayesian-search-log.md`](d6-bayesian-search-log.md)
- 依据：D3–D5 证据链、当前 clean-room spec、Task 3c 计划、relative-order design experiment，以及本轮新增证据。

## 1. 当前证据真正支持什么？

### Bayesian 模型用于场景自描述

**支持到方法学可能性，不支持家具布局结论。** Froyen 等人的 BHG 从无标签图像元素建立混合成分和分组层次，并为多个分解提供 posterior probability；用户 PDF 中 pp. 576–581 给出 mixture、Dirichlet-process prior、Gaussian/rib likelihood 与层次树，pp. 586–588 展示部件分解和 completion。它可以只读取几何/图像元素计算，但论文也拿人类分组判断做模型评估，不能把其心理结论迁移到家具布局。Del Pero 等人的室内几何模型也建立对象、房间和相机的联合生成式模型，但当前可核查来源只到摘要，且其对象类别/benchmark 是否依赖人工标注仍未查清。[E-D6-BAY-001](d6-bayesian-evidence-ledger.md#e-d6-bay-001-bayesian-hierarchical-grouping) [E-D6-BAY-003](d6-bayesian-evidence-ledger.md#e-d6-bay-003-bayesian-geometric-modeling-of-indoor-scenes)

### 从几何推断轴、顺序、trend 或 grouping

**有相邻先例，家具 estimand 尚未被验证。** BHG/BHC 支持从元素坐标推断分组；Straub 等人从表面法向量混合推断一个或多个 Manhattan frame，说明轴可以作为潜变量、也可能多模态。Del Pero 的摘要展示由室内几何和对象相对位置构建潜在房间布局。现有证据没有证明这些方法可以发现“家具应有的顺序”，也没有证明家具 trend 与 inferred axis 是同一 quantity。BHG 的 group 是生成模型成分；`IfcGroup` 是作者化来源关系，两者不能等同。[E-D6-BAY-001](d6-bayesian-evidence-ledger.md#e-d6-bay-001-bayesian-hierarchical-grouping) [E-D6-BAY-002](d6-bayesian-evidence-ledger.md#e-d6-bay-002-bayesian-hierarchical-clustering) [E-D6-BAY-005](d6-bayesian-evidence-ledger.md#e-d6-bay-005-manhattan-frame-model)

**reference order 与 latent order 必须分开。** 当前 deterministic `relative-order` 的问题是“给定外部 reference order 和显式 axis 后，投影几何是否符合该序列”。它不推断内在顺序。Bayesian 未来可以估计 latent order，但那是新的 estimand；若要同 deterministic 结果比较，应在 synthetic truth 中共同给定正确的轴和序列，或者把竞争问题改写成双方都预测同一个 latent quantity。不能在 Bayesian 估计失败时静默填入被测输入。

### 空间层次依赖

**空间统计确有成熟先例，但空间单位和依赖图由研究问题决定。** Areal disease mapping 的 ICAR/BYM 使用区域邻接图和结构化随机效应；geostatistics 的 GP 表达连续域相关；空间点过程以事件位置、研究域和相互作用刻画聚集/排斥。它们的观测单位分别是区域响应、固定地理位置的响应或随机事件点，不是家具对象天然具有的“空间自相关”。把家具关系变成 graph/field 会引入需要公开声明的邻接阈值、尺度和边界规则；ICAR 的区域邻接、GP 的距离 kernel、点过程的互动半径不能互换。[E-D6-BAY-006](d6-bayesian-evidence-ledger.md#e-d6-bay-006-hierarchical-modeling-for-spatial-data-problems) [E-D6-BAY-007](d6-bayesian-evidence-ledger.md#e-d6-bay-007-gaussian-processes-in-spatial-statistics) [E-D6-BAY-008](d6-bayesian-evidence-ledger.md#e-d6-bay-008-bym2icar-scaling) [E-D6-BAY-010](d6-bayesian-evidence-ledger.md#e-d6-bay-010-posterior-predictive-assessment-for-spatial-point-patterns)

### Synthetic-only evaluation

**支持把 synthetic computational truth 作为项目内模型评价，不支持把它当心理真值。** ICAR model-selection 工作比较了空间/非空间结构，并在已知独立生成数据时检查模型概率；空间点过程工作用模拟点模式做 posterior prediction 和模型检查；SBC 工作用模型生成的数据检查推断器的后验计算是否校准。这些做法能检验算法对已声明 generative model 的 recovery、校准和稳健性。它们不能证明生成假设适合真实家具，也不能证明一个场景 posterior 对人有意义。[E-D6-BAY-009](d6-bayesian-evidence-ledger.md#e-d6-bay-009-objective-bayesian-model-selection-with-icar) [E-D6-BAY-010](d6-bayesian-evidence-ledger.md#e-d6-bay-010-posterior-predictive-assessment-for-spatial-point-patterns) [E-D6-BAY-011](d6-bayesian-evidence-ledger.md#e-d6-bay-011-aggregationrepulsion-point-process-with-abc) [E-D6-BAY-013](d6-bayesian-evidence-ledger.md#e-d6-bay-013-simulation-based-calibration)

### Deterministic/Bayesian competition

**方法学上支持进行竞争，不能因为有 posterior 就判 Bayesian 胜出。** ICAR 模型选择用独立/空间数据的 synthetic truth 检查空间依赖选择；Piironen–Vehtari 讨论小样本 CV 搜索带来的选择偏差，并要求把最终 predictive evaluation 与搜索过程分开。项目的确定性和 Bayesian 候选应先共享输入、truth、扰动和 estimand，再比较 recovery、invariance、robustness、identifiability、calibration、reproducibility 与 computational cost。任何一个候选都可能不适用；“posterior 存在”只说明模型给出条件不确定性，不说明假设或输出有效。[E-D6-BAY-009](d6-bayesian-evidence-ledger.md#e-d6-bay-009-objective-bayesian-model-selection-with-icar) [E-D6-BAY-017](d6-bayesian-evidence-ledger.md#e-d6-bay-017-bayesian-predictive-model-selection-and-projection)

### Fusion

**仅有同一 estimand 的预测分布融合先例。** Yao 等人的 stacking 组合候选模型对同一预测量给出的 predictive distributions，用 proper scoring rule / leave-one-out 表现确定权重；它不是对不同 descriptor 数值求普通平均，也不声称获胜模型就是真模型。若确定性候选只输出一个 point descriptor，Bayesian 候选输出轴/顺序/趋势/分组的后验，那么首先应保持独立输出。只有当双方给出同一 quantity、同一状态/单位、可在 synthetic held-out truth 上用共同评分比较时，才有 fusion design 的入口。权重、模型身份、后验不确定性、融合目标与 benchmark 必须保留。[E-D6-BAY-015](d6-bayesian-evidence-ledger.md#e-d6-bay-015-stacking-of-predictive-distributions) [E-D6-BAY-016](d6-bayesian-evidence-ledger.md#e-d6-bay-016-bayesian-hierarchical-stacking)

### 方法学可能性与本项目事实

| 结论 | 证据级别 | 对本项目的含义 |
|---|---|---|
| 可从无标签几何构造混合/层次分组模型 | 文献方法先例 | 可设计一个 geometry-only 候选；不是家具分组已被验证。 |
| spatial GP、ICAR、point-process 模型能刻画空间依赖 | GIS/空间统计先例 | 先定义观测单位、邻接/距离和尺度，再决定是否借鉴。 |
| synthetic truth、posterior predictive、SBC 可检查计算模型 | 方法学证据 | 作为本项目内部候选模型的最低验证层。 |
| Bayesian 方法优于 deterministic relative-order | **不支持** | 需要共同 estimand 和同一 benchmark 才能比较。 |
| Bayesian posterior 是人的感知概率 | **不支持** | posterior 只条件于项目声明的模型与场景数据。 |
| 家具布局已有直接验证的 Bayesian latent-order 模型 | **本轮未找到** | 账本保留证据缺口；不能声称不存在所有相关研究。 |

## 2. 当前证据不支持什么？

- 不能推出心理感知效度，也不能推出人会觉得某场景有序、舒适、连贯或符合 Gestalt。
- 不能把 posterior probability 说成“人认为该布局有序的概率”；它是给定 observed geometry、prior、likelihood 和模型结构后的计算不确定性。
- 不能把 BHG/视觉模型的 Bayesian grouping 直接写成作者化 `IfcGroup`。前者是推断出的生成成分；后者是 IFC 中的显式来源关系。
- 不能把 GIS 的 CAR/ICAR 区域邻接直接套到家具对象。家具接触、距离邻近、同组和共享趋势是不同图定义，必须分别声明。
- 不能在没有 synthetic truth、identifiability 检查和 posterior calibration 时声称模型正确。先验驱动的稳定 posterior 也可能对应不可辨识或错设模型。
- 不能把对象类别/图像识别论文里的人工类别标签、benchmark 或人类判断偷偷当成项目内的训练目标。当前项目内部仍不使用人工标签、评分或心理因变量。
- 不能将不同 estimand（axis、reference order、latent order、trend、group membership）强制合成一个标量。只有同一 estimand 才进入 fusion 讨论。

## 3. 对当前设计的影响

### 候选接口/estimand 对照

| 项目 | deterministic baseline | Bayesian candidate | 是否可比较 |
|---|---|---|---|
| 输入 | canonical geometry + explicit `AxisSpec` + external `reference_order` | canonical geometry + declared generative model、prior、likelihood 和 provenance | 只有 canonical geometry、frame、unit、成员和缺失语义相同才可比 |
| 潜变量 | 无；axis 与 reference sequence 是外部给定条件 | 候选分别声明 latent axis、latent order、trend、grouping；首轮只应选一个 estimand | 仅相同 latent quantity 可比 |
| 输出 | `relative-order` point descriptor + status/completeness | posterior draws/distribution + interval/entropy/multimodality + status/reasons | 不因都叫 order 就自动等价；需先定义共同 summary/score |
| 评估 | hand oracle、精确 tolerance/tie 语义、几何不变量 | synthetic truth recovery、prior/posterior predictive checks、SBC/calibration、identifiability、重现性 | 共享 synthetic scene 与 perturbation 时可比较；不能用人类评分 |
| 缺失数据 | 当前契约按 missing geometry 排除并保留 partial/missing reason；输入 axis/order 缺失为 `not_evaluated` | posterior 随信息减少而变宽或多模态；全部不可用时 `not_available`；不可辨识/不足时 `undefined` 并附 reason | 可比较退化状态和 coverage；禁止以 0 替代缺失 |
| provenance | algorithm/version/parameters、axis/reference 来源、frame/unit/tolerance | model/version、prior/likelihood、inference algorithm/sampler、seed、diagnostics、source geometry | 共同字段可放在结果外层；模型专属细节保留各自 provenance |
| 融合 | 不适用；条件 point result | 仅在同一 estimand 且共同 synthetic predictive score 验证后讨论 BMA/stacking/其他规则 | 默认不融合；模型身份、权重、预测不确定性、组合依据需保留 |

### synthetic truth 的最小设计建议

这是后续 Task 3c 的工程设计建议，不是已经运行的实验，也不是论文报告结果。采用可复现参数化几何构造器，为每个 scene 写出与推断器分离的生成参数：

| 场景族 | 已知 truth | 关键扰动/反例 | 应检查的量 |
|---|---|---|---|
| 单轴单序列 | axis angle/sign、reference sequence、对象代表点 | 平移、旋转、单位缩放、反转轴、tied anchors | axis recovery、order relation recovery、旋转/平移变换下的约定不变量 |
| 多轴或无唯一轴 | 两个竞争方向或各向同性点集 | 近等强轴、正方形/圆形布局、成员方向冲突 | posterior multimodality、可辨识性、低信息状态；不能硬选唯一轴 |
| 分层组 | 已知组成员、组内/组间方向和间距参数 | 跨组近邻、重叠组、改变 IFC authored membership | latent group recovery；禁止把推断组伪装成 authored group |
| 几何表示变化 | 同一实心对象/面积/质心 | 三角网格细分、不同顶点采样密度、MassPatch 分解 | tessellation invariance 或已声明的尺度敏感性 |
| 缺失/矛盾成员 | 原始完整 scene truth | 删除对象几何、遮蔽部分面、插入离群/反向成员 | coverage、posterior spread、partial completeness、稳定的失败 reason |
| 空间依赖结构选择 | 独立、局部聚集、排斥三种生成机制 | 图邻接半径/边界、固定与扰动 graph | false-positive spatial effect、model probability/calibration、posterior predictive discrepancy |

建议将参数生成器版本、scene seed、真值文件和扰动 recipe 与 model output 分开保存。用一组场景开发/选择模型，另用固定 holdout scene 评价；同一批 truth 不应既选先验和权重又报告最终胜出。数据生成真值只代表预先声明的 computational world，不代表真实家具空间的唯一生成机制。

### 与 relative-order、AxisSpec、trend 的边界

| 设计问题 | 建议契约（仅供后续设计评审） |
|---|---|
| Bayesian 可否提供 `AxisSpec`？ | 可以作为候选估计结果，但必须带 frame、方向约定、posterior/可信区间、model provenance 和 identifiability。AxisSpec 的“输入事实”与“模型估计”应可区分来源；不要改变当前显式轴基线的含义。多峰或无方向时不能强制压成单一 `unit_vector`。 |
| `reference_order` 是否改成 latent variable？ | 当前 `relative-order` 仍保留外部 `reference_order`。latent order 应作为独立 descriptor/latent result 定义；如果要比较二者，就用 synthetic truth 中的已知顺序比较 recovery，不能把推断顺序回填成自己的 reference 再给自己打分。 |
| Bayesian 推断失败时的状态 | 沿用合同状态词汇：输入/模型声明缺失为 `not_evaluated`；几何全部缺失为 `not_available`；足够数据下不可辨识、对象数不足或纯 tie 为 `undefined`；数值/几何非法为 `invalid`。posterior 已计算但高熵/多模态可以是 `computed`，同时显式标 `low_information`/`multimodal`、诊断和 completeness；是否允许该子状态需在后续合同中决定。不能输出伪精确 MAP 当成功。 |
| 两候选是否共用 `DescriptorResult`？ | 可共用外层身份、status、reason、support/completeness 和 provenance 约定；Bayesian distribution/latent samples 与 deterministic scalar 的值载荷不同，不应把 posterior 压成一个 scalar 来迎合旧结果字段。当前不改接口，只建议保留 descriptor-specific payload 的设计空间。 |
| 如何防止 Bayesian 自动挑最有利轴造成循环论证？ | 不用“在同一场景上挑使 relative-order 分最高的轴，再把该分数当验证”。轴推断只按其预注册 generative likelihood/prior 得到；在独立 synthetic holdout 上用真值评估 axis recovery 与 order descriptor。若目标就是联合推断轴和顺序，则把联合量、选择复杂度和模型比较都写入 estimand，并和独立确定性 oracle 比较，不能事后选轴/调参。 |
| trend estimator 与 Bayesian latent-axis 边界 | 当前 `authored_group_local_trend` 从显式 authored group 的成员几何总结方向/strength，是确定性组级 trend descriptor；latent-axis 模型从 scene geometry 估计轴的分布，可以跨 authored group 或模型化分组。两者输入成员集合、层级和 estimand 不同，应分开命名和输出。只有双方都估计同一个方向 quantity 且有共同 truth 时才进行数值竞争。 |
| posterior 如何表达 missing geometry、ties、contradictory members？ | Missing geometry 应作为观测缺失/成员排除并保留原因，让 posterior 变宽；所有关键几何缺失用 `not_available`。ties 是 pairwise relation 概率或偏序关系，不以任意稳定排序打破。Contradictory members 可形成混合/多峰 posterior 或低 posterior predictive fit；若模型假设不能解释冲突，报告 lack-of-fit，不要通过加大方差掩盖。 |

### 候选模型竞争次序

首轮不需要同时上 CAR、GP、point process、BHG 和 scene-generation 大模型。最小可审查比较可保留：

1. **D0 条件确定性基线**：现有 explicit `AxisSpec + reference_order` 的 relative-order 语义，输入和状态严格按 D6 定义。
2. **B1 latent-axis candidate（候选，不推荐默认启用）**：对象 geometry-derived directional evidence 上的轴方向混合模型；先定义角度等价类、轴符号、各向同性退化和 likelihood，再以 synthetic truth 比较 axis recovery。Straub 的法向混合只提供结构启发，不作为现成家具模型。
3. **B2 hierarchical grouping candidate（仅在研究 group estimand 时）**：对象级 geometry signatures/关系的 mixture 或层次模型；分组输出与 authored `IfcGroup` 完全分开。BHG/BHC 仅提供分组计算先例，不预设家具生成组件。
4. **spatial random-effect candidate**：只有当数据明确是带 unit 的 areal/voxel/graph response，并且目标是同一连续/邻接 latent field 时，才单独与无 spatial effect 模型比较；不能把它当 B1/B2 的默认附加层。

这只是按研究问题分支的设计，不是模型选择结论。若 deterministic 与 Bayesian 不估计相同的 estimand，先并列保留，暂不比一个综合分数，也不做 fusion。

## 4. Grill-me 反向审查

| 检查问题 | 本文处理 |
|---|---|
| 是否把 Bayesian 方法可能性写成项目事实？ | 没有。使用“可候选、尚未验证、工程建议”等标记；direct IFC-furniture evidence gap 单独登记。 |
| 是否把 GIS 空间模型等同于家具关系？ | 没有。分别写出 areal response、固定坐标观测、随机点和对象几何，并指出 graph/kernel 需要重新声明。 |
| 是否把 latent scene description 与 human perception 混淆？ | 没有。明确区分 computational posterior 与人的感知概率；Froyen 人类评估只记作不能迁移边界。 |
| 是否把 reference order、trend axis、Bayesian latent axis 混为一谈？ | 没有。外部序列、作者组内方向摘要和待估潜轴按三个 estimand 处理。 |
| 是否把模型融合写成普通加权平均？ | 没有。要求 same estimand、共同评分、synthetic holdout；默认保留独立输出。 |
| 是否遗漏 synthetic truth、identifiability 或 posterior calibration？ | 纳入最小 synthetic fixture 族、SBC、posterior predictive discrepancy、多峰轴和退化情况。 |
| 是否保留 D3–D5 原证据链？ | 保留。仅新增 D6 文件，没有修改旧证据文档。 |
| 关键结论是否有原文定位？ | 17 篇既有记录已通过 ScanSci 或作者/公开版本核读关键方法与评价章节；新增长文记录给出页码/章节，BIM 记录给出官方 HTML 行段。 |
| 是否存在“摘要结果当全文”问题？ | 账本区分 `full_text`、`official` 和 `inaccessible`；全文条目只把核读章节的结论升级，未核读部分仍保守表述。 |

## 5. 当前结论

Bayesian scene-self-description 值得作为项目外部实验可消费的**竞争候选**，其理由是几何混合分组、潜在轴、空间场以及 synthetic posterior checking 都存在各自的计算先例。现有证据没有确定最适合家具布局的模型，也没有证明 Bayesian 相对 D0 更好。Task 3c 应先锁定一个明确 estimand（建议先独立讨论 latent axis 或 latent grouping，不同时联合所有层），建 synthetic truth 并检查可辨识性，再与 deterministic 条件基线竞争。模型失败时保留状态与 provenance；若估计不同量，输出并列；若估计同一量且共同 benchmark 支持，才考虑保留不确定性的 posterior predictive fusion。

本任务未修改生产代码或接口；不启动 Task 3b/Task 4，不设计真人实验，不把任何 posterior 当心理变量。

## 6. 第二轮原文核读后的修订

ScanSci 原文获取后，证据强度从摘要级提升为可核查正文级，但迁移结论同时变窄。BHC 的正文给出 Dirichlet-process mixture、边际似然合并、预测分布、synthetic/real 数据和 5-fold purity；它还明确算法是贪心的、复杂度为 O(n²)，并没有纳入树结构不确定性。因此 BHC 可支持“概率层次分组是可计算候选”，不能支持“完整 Bayesian 分组后验已经解决”。

Del Pero 2012/2013 的正文进一步显示，室内场景模型的观测是单幅图像边缘、orientation/color 等，先验来自家具目录、图像训练信息和人工拟合，评价依赖 Hedau/UCB 的人工 masks/类别。它们是 geometry-informed scene reconstruction 的方法先例，但不满足本项目 canonical geometry 自描述、无人工标签的内部训练和验收边界。Straub 的正文显示多轴 MF/MMF 确实输出 MAP、RJMCMC samples 和未知混合数，但 NYU V2 的 MF 数量评价使用人工 annotator，且模型针对表面法向量，不是家具中心线或顺序。

因此，本项目中的“无人”应只写成：推断和验收不使用人的心理评分、参与者或人工 order label；外部论文的训练图像、类别先验和人工 benchmark 必须逐项隔离。证据账本已把这些来源按先验、训练、评价记录。

新增的 Structured Graph VAE 是家具关系图的直接相邻证据：节点包含 class/pose/size/shape，边包含 relative location/orientation，latent prior 按节点生成顺序建模，实验在 3D-FRONT 上与 iid prior 比较。不过它是数据集训练的生成模型，节点 order 是参数化需要，不能当作从一个场景发现的物理 order。新增 BIM Composite Object 论文则把 IfcSpace、host/child、clearance 和规则布局明确为 authored/parametric 来源；它没有 posterior，反而为 latent grouping 与 authored group 的边界提供直接 BIM 证据。

修订后的停止条件是：不再为了增加论文数量泛扩搜索。只有 owner 选定一个具体 estimand，并要求该 estimand 的直接 IFC/BIM 先例时，才继续定向查找；否则下一步应是 Task 3c 的 synthetic probe，检验 D0 与一个明确的 B1 或 B2 候选，而不是继续堆叠不同领域的 Bayesian 术语。

## 7. EBK 定向补充后的结论

EBK 补充了一个新的候选类型：**给定空间点和标量 response，预测未观测位置的连续空间场，并传播参数与预测不确定性**。Gribov–Krivoruchko 的 EBK 原文明确包含 empirical prior、局部模型、模型合并、非平稳性、测量误差和 prediction interval；其评价使用 simulation、RMSPE/RMSSPE、CRPS 和区间覆盖。ArcUser 原文进一步明确 EBK 用多个 semivariogram 候选及 Bayes 权重传播相关结构估计误差。Le–Zidek 则提供 fully Bayesian kriging comparator，把协方差不确定性纳入 posterior predictive。

“家具组作为一个点”可行，但只在点定义先固定时成立：代表位置、group-level response、空间 support、组内汇总和重叠处理都必须进入数据契约。此时 EBK 估计的是组点上的空间 response，不是组成员关系；它不产生 `IfcGroup` membership、latent order 或 relative-order reference sequence。组点过度压缩组内几何时，预测结果只能解释为 group-level field，不能解释为家具布局整体结构。

Pan–Hu–Shen 的 MRF-PPM 原文补出第三条边界：它把空间图邻接和 product-partition prior 合并，用 posterior 直接恢复 latent spatial groups，并在 synthetic、降水和收入面板数据上评价。但它需要重复 response/covariates 和已知空间图；不能直接当作单个 IFC 场景的 geometry-only 分组器。

因此候选竞争应分成三条：

1. **空间 response 预测**：deterministic interpolation、EBK、CAR/ICAR、GP 可在共同 group-point、response 和 holdout synthetic scenes 上比较。
2. **组/顺序发现**：BHC、latent-axis 或 graph model 单独比较；不把 EBK 的预测不确定性当作分组后验，也不把 EBK 分数与 relative-order 分数直接加权。
3. **空间 latent grouping**：MRF-PPM 类模型单独比较；要求明确图邻接、重复 response 和 partition estimand。

当前不继续泛扩 EBK 文献。下一步只有在 owner 确定 group-level response（例如 clearance field、distance-to-boundary field 或其他连续量）后，才值得实现 EBK/CAR/GP 的同 estimand synthetic comparison。

本轮证据增量已经完成。尚未选择 Bayesian 生产模型，尚未实现 Bayesian 代码；下一步是 owner 审查 Task 3c 的首要 estimand。

STOP FOR DESIGN REVIEW
