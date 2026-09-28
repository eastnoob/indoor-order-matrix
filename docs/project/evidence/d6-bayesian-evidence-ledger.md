# D6 Bayesian 场景自描述证据账本

- 研究日期：2026-09-28
- 增量范围：只新增 Bayesian/空间统计/模型比较证据；D3–D5 账本保持不变。
- 证据等级：`full_text`、`official`、`abstract_only`、`inaccessible`、`engineering_inference`。
- 第二轮：2026-09-28 原文获取与修订。17 篇既有论文均已取得可核查全文；另新增 2 篇相邻证据。full_text 表示核读了列出的关键方法/评价章节，不表示逐字阅读所有讨论与补充材料。
- 重要规则：获取渠道、PDF 版本、阅读深度与结论强度分别记录；下载成功不等于方法已经验证。人工信息按先验、训练、评价分别审计，不以“无人心理评分”代替“完全无人工信息”。

## E-D6-BAY-001 — Bayesian Hierarchical Grouping

- **research question**：A；几何/对象关系自身能否产生层次分组和不确定性？
- **exact title**：*Bayesian Hierarchical Grouping: Perceptual Grouping as Mixture Estimation*。
- **authors/year**：Vicky Froyen, Jacob Feldman, Manish Singh，2015。
- **DOI/stable source**：<https://doi.org/10.1037/a0039540>；用户提供全文 `C:/Users/tianf/Downloads/froyen2015.pdf`。
- **source type**：计算模型论文，*Psychological Review* 122(4), 575–597。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：二维图像元素、点阵点、轮廓片段、形状边界采样点。
- **observed variables**：元素坐标 `x_n`；对曲线对象还包括到生成曲线的垂直距离（rib length）。
- **latent variables**：对象数 `K`、分配 `c_n`、每个成分参数 `θ_k`、层次树、tree slice/grouping hypothesis。
- **prior**：Dirichlet-process mixing prior；对象参数先验；曲线 compactness 的平方弧长惩罚、straightness 的总曲率惩罚、rib length 的 normal-inverse-chi-squared 先验（页 579–580）。
- **likelihood**：混合模型 `p(x_n|φ)=Σ_k p(x_n|θ_k)p(c_n=k|p)`；曲线对象用垂直于曲线的 Gaussian rib likelihood（式 1、9）。
- **hierarchical level**：BHC/BHG 自底向上构造树；每次合并比较单对象假设与树一致的多对象假设（页 578–579）。
- **spatial dependence structure**：Delaunay 邻接限制候选合并；这是计算邻接和感知对象假设，不是 GIS CAR/ICAR 自相关。
- **posterior output**：`p(c_j|D,α,β)`、MAP 分组、tree-slice 概率、`p(x*|D,c_j)` posterior predictive（式 7–8）。
- **evaluation protocol**：dot lattice、contour grouping、part decomposition、shape completion；部分结果与 Feldman 等人的人类判断比较，并报告 LRT/BF/R²（页 581–588）。
- **human data used**：是；论文用人类感知数据评估模型，但模型本身可以仅以图像元素计算。
- **transfers to this project**：无人工标签的几何点/边界混合；层次分组后验；把 missing/contradictory geometry 表达为预测分布或低信息状态的设计启发。
- **does not transfer**：不能把 posterior 当作人的分组概率；不能把视觉 `Prägnanz`、轮廓或形状部件直接当作家具 `IfcGroup`、活动区或心理 order。
- **locator**：PDF pp. 576–581, 586–588；式 1–10；摘要 pp. 575–576。
- **confidence**：模型结构 high；迁移到家具 medium；心理解释 low/不迁移。
- **follow-up need**：用纯几何 synthetic truth 重写对象类、先验和评价；不复用人类数据拟合。

## E-D6-BAY-002 — Bayesian hierarchical clustering

- **research question**：A；是否有不依赖 ad-hoc 距离的概率层次分组先例？
- **exact title**：*Bayesian hierarchical clustering*。
- **authors/year**：K. Heller, Zoubin Ghahramani，2005。
- **DOI/stable source**：<https://doi.org/10.1145/1102351.1102389>；Consensus record：<https://consensus.app/papers/bayesian-hierarchical-clustering-heller-ghahramani/c0c05bcf8f5750d5a28c9c2a055e8acc/>。
- **source type**：机器学习方法论文，ICML 2005。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：一般数据点/特征向量；实验覆盖 4 个真实数据集、1 个合成 Gaussian-mixture 数据集和二维 toy 数据。
- **observed variables**：数据特征向量；正文用 Gaussian component marginal likelihood 作为合并证据。
- **latent variables**：聚类分配、树结构、合并深度、Dirichlet-process mixture 成分。
- **prior**：Dirichlet-process mixture prior；组件参数采用共轭 Gaussian model 的先验设定。
- **likelihood**：cluster marginal likelihood；每次合并比较单一 cluster 与两个子 cluster 的 Bayesian hypothesis test。
- **hierarchical level**：agglomerative tree；合并用 Bayesian hypothesis test。
- **spatial dependence structure**：无专门空间依赖结构。
- **posterior output**：测试点 predictive distribution、归属概率、合并概率、推荐树深度。
- **evaluation protocol**：5-fold dendrogram-purity 与 linkage baseline 比较；另报告预测分布、归属/合并概率和推荐树深度。
- **human data used**：否；真实数据的类别标签只用于 dendrogram-purity 评价，不是人类感知评分。
- **transfers to this project**：可以借鉴“合并应由边际似然/模型证据决定，并输出树深度和成员不确定性”。
- **does not transfer**：没有家具几何、轴、顺序或空间自相关假设；不能直接选择 IFC group。
- **locator**：作者公开 PDF，§2–§4、Figure 1–3、Table 1–2；另见 Consensus record。
- **confidence**：模型结构 high；迁移到家具层次关系 medium-low。
- **follow-up need**：保留其 greedy/O(n²) 和“不纳入 tree uncertainty”的限制；若采用 BHC，需在项目 synthetic truth 上重新验证。

## E-D6-BAY-003 — Bayesian geometric modeling of indoor scenes

- **research question**：A；是否能仅从场景几何/布局数据推断对象和房间潜变量？
- **exact title**：*Bayesian geometric modeling of indoor scenes*。
- **authors/year**：Luca Del Pero, Joshua Bowdish, Daniel Fried, Bonnie Kermgard, Emily Hartley, Kobus Barnard，2012。
- **DOI/stable source**：<https://doi.org/10.1109/CVPR.2012.6247994>；机构摘要：<https://experts.arizona.edu/en/publications/bayesian-geometric-modeling-of-indoor-scenes/>。
- **source type**：CVPR 2012 生成式几何场景模型。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：室内场景图像/几何、房间 box、窗/门/画框和对象实例。
- **observed variables**：对象尺寸、相对尺寸、位置、房间几何及相机相关观测；摘要未完整列出观测接口。
- **latent variables**：对象类别/存在、尺寸、相对比例、位置、房间布局和相机参数。
- **prior**：对象 size、relative dimensions、locations 的先验。
- **likelihood**：联合生成式场景模型；具体图像/几何 likelihood 未在摘要中给出。
- **hierarchical level**：房间、框架对象和家具对象的联合场景层次。
- **spatial dependence structure**：对象与房间/对象类别之间的相对位置先验；不是 CAR/ICAR。
- **posterior output**：MCMC 对离散对象增删和连续参数的后验样本，房间布局估计和几何识别。
- **evaluation protocol**：room layout estimation 与 recognition benchmark；摘要未给出 synthetic truth 细节。
- **human data used**：否；但 benchmark 的对象类别或标注可能来自人工，摘要无法确认训练/验收路径。
- **transfers to this project**：说明 geometry-only latent scene description 在计算上有先例；可借鉴联合 size/pose/room context 的显式 provenance。
- **does not transfer**：相机/图像/类别识别目标、训练数据和 benchmark 语义不能变成 IFC 家具 order 或心理指标。
- **locator**：摘要；机构记录中的 Abstract 段落。
- **confidence**：几何生成式方向 medium；具体公式和数据流 low。
- **follow-up need**：取得正文后核对 likelihood、对象类别是否人工监督、以及 geometry-only 实验设置。

## E-D6-BAY-004 — Understanding Bayesian Rooms Using Composite 3D Object Models

- **research question**：A；对象自身的细粒度几何是否能支撑场景生成和关系推断？
- **exact title**：*Understanding Bayesian Rooms Using Composite 3D Object Models*。
- **authors/year**：Luca Del Pero, Joshua Bowdish, Bonnie Kermgard, Emily Hartley, Kobus Barnard，2013。
- **DOI/stable source**：<https://doi.org/10.1109/CVPR.2013.27>；Consensus record：<https://consensus.app/papers/understanding-bayesian-rooms-using-composite-3d-object-pero-bowdish/d4f82157dba25d3cae96e5bc3f02eeed/>。
- **source type**：CVPR 2013 Bayesian generative scene model。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：室内图像和可组合的 3D 对象部件（例如椅腿、座面、靠背）。
- **observed variables**：2D 投影颜色/几何、部件观测和对象上下文；具体字段未在摘要中完整列出。
- **latent variables**：对象、部件、姿态、房间布局和上下文关系。
- **prior**：对象/部件组合与上下文关系的生成假设；具体分布未在摘要中给出。
- **likelihood**：2D 投影颜色分布的 likelihood，强调凹对象不能简单用 bounding box；其余 likelihood 未在摘要给出。
- **hierarchical level**：房间 → 对象 → 可复用部件；上下文关系可提出“桌子周围/下方的椅子”。
- **spatial dependence structure**：部件与对象上下文关系；不是空间随机场。
- **posterior output**：对象/布局重建和识别结果；推断机制细节未在摘要中给出。
- **evaluation protocol**：两个 benchmark 数据集上的 room-layout estimation 和 object recognition。
- **human data used**：否（benchmark 标注来源不明，不能据摘要排除人工标注）。
- **transfers to this project**：支持保留 MassPatch/部件几何来源、避免把复杂家具强行压成 box 的建模原则。
- **does not transfer**：颜色投影、视觉识别、椅子-桌子语义不能直接成为 authored group 或心理边界。
- **locator**：摘要；CVPR 2013 元数据记录。
- **confidence**：细粒度几何方向 medium；具体 posterior/likelihood low。
- **follow-up need**：需要全文确认对象部件先验和训练/测试是否有人工类别标签。

## E-D6-BAY-005 — Manhattan Frame Model

- **research question**：A；能否从人造环境几何自身推断潜在轴结构，并保留多模态轴？
- **exact title**：*The Manhattan Frame Model—Manhattan World Inference in the Space of Surface Normals*。
- **authors/year**：Julian Straub, O. Freifeld, Guy Rosman, J. Leonard, John W. Fisher，正式卷期 2018（online/会议传播年份存在差异）。
- **DOI/stable source**：<https://doi.org/10.1109/TPAMI.2017.2662686>；Consensus record：<https://consensus.app/papers/the-manhattan-frame-model—manhattan-world-inference-in-straub-freifeld/7770c9437b6751cab4102a59b7682698/>。
- **source type**：几何方向推断/概率混合模型，*IEEE TPAMI*。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：人造环境的表面法向量。
- **observed variables**：单位球面上的 surface normals。
- **latent variables**：一个或多个 Manhattan frames、轴方向、混合成分数。
- **prior**：概率 MF/MMF 模型；具体先验未在摘要中给出。
- **likelihood**：球面上的 probabilistic MF mixture；具体分布未在摘要中给出。
- **hierarchical level**：single MF → mixture of Manhattan Frames；全局多尺度推断。
- **spatial dependence structure**：法向量方向混合，不是对象邻接或 CAR/ICAR。
- **posterior output**：single-frame MAP；MMF 的 MAP 与 split/merge Metropolis–Hastings MCMC 样本。
- **evaluation protocol**：不同尺度的人造环境；摘要未列出 synthetic truth/标定细节。
- **human data used**：否。
- **transfers to this project**：多模态轴、轴符号/对称性、未知成分数和 split/merge 是 latent-axis 设计的直接启发。
- **does not transfer**：surface-normal Manhattan 假设不能直接套用家具中心线、relative order 或 authored group。
- **locator**：摘要/Consensus fetch record。
- **confidence**：潜在轴方法 medium；迁移到家具 low-medium。
- **follow-up need**：确认正文中的轴可辨识性、退化场景和 synthetic 评价。

## E-D6-BAY-006 — Hierarchical Modeling for Spatial Data Problems

- **research question**：B；GIS/空间统计中的层次模型到底描述哪些空间单位和潜变量？
- **exact title**：*Hierarchical Modeling for Spatial Data Problems*。
- **authors/year**：A. Gelfand，2012。
- **DOI/stable source**：<https://doi.org/10.1016/j.spasta.2012.02.005>；Consensus record：<https://consensus.app/papers/hierarchical-modeling-for-spatial-data-problems-gelfand/b999cb19ee6357659911c0e1709cb225/>。
- **source type**：空间统计综述/方法论文，*Spatial Statistics* 1, 30–39。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：point-referenced geostatistical observations、point-pattern events、时空观测。
- **observed variables**：带地理坐标的响应、事件位置、环境暴露或物种观测。
- **latent variables**：空间过程、物种分布、暴露/天气过程及预测变量。
- **prior**：分层 Bayesian specification；具体先验未在摘要中给出。
- **likelihood**：point-referenced 与 point-pattern likelihood；摘要未列出具体 family。
- **hierarchical level**：观测层 → 空间过程层 → 预测/数据融合层。
- **spatial dependence structure**：点参考过程和点模式结构；不是默认家具邻接。
- **posterior output**：full inference with associated uncertainty、空间预测和数据融合。
- **evaluation protocol**：环境/生态应用；摘要未给出统一 synthetic protocol。
- **human data used**：否（但具体应用数据需逐篇核查）。
- **transfers to this project**：明确“观测层、潜在场、预测层”分离；提醒场景自描述必须声明空间单位和潜变量。
- **does not transfer**：地理连续场、生态过程和观测误差假设不能自动成为家具关系。
- **locator**：摘要/Consensus fetch record。
- **confidence**：方法范围 medium；具体模型 low。
- **follow-up need**：只在需要选择点参考、点模式或 areal 模型时再取对应全文。

## E-D6-BAY-007 — Gaussian processes in spatial statistics

- **research question**：B；Gaussian process 是否能作为空间潜场/梯度的计算先例？
- **exact title**：*Spatial statistics and Gaussian processes: A beautiful marriage*。
- **authors/year**：A. Gelfand, E. Schliep，2016。
- **DOI/stable source**：<https://doi.org/10.1016/j.spasta.2016.03.006>；Consensus record：<https://consensus.app/papers/spatial-statistics-and-gaussian-processes-a-beautiful-gelfand-schliep/47ac766e9c7f5e5ab4eca42f5365a146/>。
- **source type**：空间统计综述，*Spatial Statistics* 18, 86–104。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：多变量地理位置观测、方向数据、时空数据和极值。
- **observed variables**：固定空间位置上的响应/协变量。
- **latent variables**：连续 spatial random field、梯度、方向场或多变量潜场。
- **prior**：Gaussian process prior；具体 covariance/hyperprior 未在摘要中给出。
- **likelihood**：分层 geostatistical likelihood；具体 response family 未在摘要给出。
- **hierarchical level**：回归/观测层 → GP 空间过程 → prediction/data-fusion 层。
- **spatial dependence structure**：由 covariance kernel/GP 表达连续空间依赖。
- **posterior output**：潜在场的后验与空间预测；摘要强调 Bayesian MCMC/Gibbs 框架。
- **evaluation protocol**：综述二十年模型工作，未给出单一统一的 synthetic 评价。
- **human data used**：否（领域应用可能不同，摘要无法逐例确认）。
- **transfers to this project**：若项目定义了体素/采样点和尺度，GP 可表达连续 trend/场的后验不确定性。
- **does not transfer**：没有明确定义的连续域时，不能把家具对象图自动当作 GP；kernel 选择会引入强先验。
- **locator**：摘要/Consensus fetch record。
- **confidence**：GP 作为空间潜场先例 medium；家具迁移 low-medium。
- **follow-up need**：若采用 GP，先设计尺度、kernel、边界和对象到场的观测映射。

## E-D6-BAY-008 — BYM2/ICAR scaling

- **research question**：B；ICAR/CAR 如何表达区域图上的结构化空间依赖，并处理先验可解释性？
- **exact title**：*An intuitive Bayesian spatial model for disease mapping that accounts for scaling*。
- **authors/year**：A. Riebler, S. H. Sørbye, D. Simpson, H. Rue，2016。
- **DOI/stable source**：<https://doi.org/10.1177/0962280216660421>；Consensus record：<https://consensus.app/papers/an-intuitive-bayesian-spatial-model-for-disease-mapping-riebler-sørbye/4f75fedf1a4356a98e0c5c9210ab65f7/>。
- **source type**：空间层次模型方法论文，*Statistical Methods in Medical Research* 25, 1145–1165。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：areal disease-mapping units（区域计数/协变量；摘要未列完整观测表）。
- **observed variables**：区域响应、固定效应协变量和邻接图。
- **latent variables**：structured ICAR spatial effect、unstructured effect、BYM/BYM2 hyperparameters。
- **prior**：scaled spatial component 和 interpretable penalised-complexity hyperpriors。
- **likelihood**：疾病制图的区域响应模型；具体分布未在可访问摘要中写明。
- **hierarchical level**：区域响应 → fixed/unstructured/structured random effects → hyperparameters。
- **spatial dependence structure**：ICAR/BYM 图结构；结构化与非结构化效应存在混淆风险。
- **posterior output**：空间效应、超参数和模型选择指标；摘要重点是可解释 shrinkage。
- **evaluation protocol**：simulation study、与既有参数化比较和应用示例。
- **human data used**：否；疾病数据不等于人类评分，但观测单位可能是人口区域。
- **transfers to this project**：只有在明确定义对象/区域图后，才可借鉴 scaling、先验解释和“结构效应/非结构效应分离”。
- **does not transfer**：疾病区域的 adjacency、Poisson 等语义不能直接替代家具接触/相邻/遮挡关系。
- **locator**：摘要/Consensus fetch record。
- **confidence**：ICAR/先验设计 medium；家具迁移 low。
- **follow-up need**：必须做 graph sensitivity、独立效应混淆和 prior predictive 检查。

## E-D6-BAY-009 — Objective Bayesian model selection with ICAR

- **research question**：C；Bayesian spatial model 是否能与“无空间依赖”候选竞争，并用 synthetic truth 检查结构选择？
- **exact title**：*Objective Bayesian Model Selection for Spatial Hierarchical Models with Intrinsic Conditional Autoregressive Priors*。
- **authors/year**：Erica M. Porter, Christopher T. Franck, Marco A. R. Ferreira；正式出版 2024（Consensus 索引为 2023）。
- **DOI/stable source**：<https://doi.org/10.1214/23-BA1375>；Consensus record：<https://consensus.app/papers/objective-bayesian-model-selection-for-spatial-porter-franck/6a0b20da4b675871a3a5178a0ceae831/>。
- **source type**：Bayesian model-selection 方法论文，*Bayesian Analysis* 19, 985–1011。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：county-level median household income 与 neighborhood residential crime rate；另有 simulated areal data。
- **observed variables**：区域响应、回归协变量、区域邻接图。
- **latent variables**：固定效应/回归变量选择、ICAR spatial random effect、是否需要空间结构。
- **prior**：automatic reference priors；fractional Bayes factors 使用最小 training size。
- **likelihood**：Gaussian hierarchical model with ICAR random effects。
- **hierarchical level**：区域响应 → fixed effects + ICAR spatial effects → model structure。
- **spatial dependence structure**：ICAR 邻接图；可在模型空间中与独立结构竞争。
- **posterior output**：posterior model probabilities、协变量结构选择、空间模型结构选择。
- **evaluation protocol**：simulation study；当数据真正 independent 时应给空间模型低 posterior probability；另有两个真实区域应用，并与 DIC/WAIC 比较。
- **human data used**：否。
- **transfers to this project**：直接支持“确定性/空间候选必须先竞争、不能默认加入空间依赖”，以及用 synthetic truth 检验结构选择。
- **does not transfer**：ICAR graph 与区域收入/犯罪的语义不能直接套在家具对象；Bayes factor 选择也不能代替 descriptor validity。
- **locator**：摘要；CrossRef 正式卷期与 *Bayesian Analysis* 目录。
- **confidence**：模型竞争与 synthetic selection high（摘要明确）；家具迁移 medium-low。
- **follow-up need**：需要全文核对 prior 对 graph size 的敏感性、model identifiability 和可比较的 estimand。

## E-D6-BAY-010 — Posterior predictive assessment for spatial point patterns

- **research question**：B/C；如何用空间后验样本做 model criticism、模型选择和 synthetic calibration？
- **exact title**：*Bayesian Inference and Model Assessment for Spatial Point Patterns Using Posterior Predictive Samples*。
- **authors/year**：Thomas J. Leininger, A. Gelfand，2017。
- **DOI/stable source**：<https://doi.org/10.1214/15-BA985>；官方机构记录：<https://scholars.duke.edu/publication/1241820>；Consensus record：<https://consensus.app/papers/bayesian-inference-and-model-assessment-for-spatial-point-leininger-gelfand/6560b5681a7a51b488eb5b29167a001c/>。
- **source type**：空间点过程 Bayesian inference/model assessment，*Bayesian Analysis* 12(1), 1–30。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：给定域内的事件数量和事件位置（spatial point pattern）。
- **observed variables**：事件点位置、事件数、研究域。
- **latent variables**：intensity、聚集/抑制过程、生成点模式。
- **prior**：Poisson、log-Gaussian Cox、Gibbs 等 generative models 的先验；具体超先验未在摘要给出。
- **likelihood**：Poisson/LGCP/Gibbs point-process likelihood；具体公式未在摘要给出。
- **hierarchical level**：生成点过程 → observed point pattern → posterior predictive point patterns。
- **spatial dependence structure**：intensity、cluster/inhibition point-process interaction。
- **posterior output**：posterior point patterns、Bayesian residuals、empirical coverage、prior/posterior predictive samples。
- **evaluation protocol**：Monte Carlo prior-predictive checks、simulation study、two real datasets；model choice 使用 predictive MSE、coverage 和 ranked probability score。
- **human data used**：否。
- **transfers to this project**：后验预测应复现空间摘要/关系统计；可用于 missing/contradictory geometry 的模型检查和同 estimand 比较。
- **does not transfer**：事件点的随机生成机制不能默认解释家具对象；不能把点过程 posterior 直接叫作 order 或人类感知。
- **locator**：官方机构摘要 lines 22–25；摘要中列出的 simulation/model-choice 方法。
- **confidence**：model-checking principle high；具体 likelihood/prior medium-low。
- **follow-up need**：若采用 point-process candidate，需取正文确定边界校正、summary statistics 和 coverage 定义。

## E-D6-BAY-011 — Aggregation/repulsion point process with ABC

- **research question**：B/C；能否在 likelihood 不可写时用可模拟模型、ABC 和 posterior prediction 区分聚集与排斥？
- **exact title**：*Approximate Bayesian inference for a spatial point process model exhibiting regularity and random aggregation*。
- **authors/year**：Ninna Vihrs, Jesper Møller, A. Gelfand；正式卷期 2021（Consensus 索引为 2020）。
- **DOI/stable source**：<https://doi.org/10.1111/sjos.12509>；Consensus record：<https://consensus.app/papers/approximate-bayesian-inference-for-a-spatial-point-vihrs-møller/98385da103f15ac4834740b7aa804115/>。
- **source type**：空间点过程 Bayesian/ABC 方法论文，*Scandinavian Journal of Statistics* 49(1), 185–210。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：空间点模式。
- **observed variables**：点的位置和研究域。
- **latent variables**：同时包含 aggregation 与 repulsion/regularity 的潜过程。
- **prior**：doubly stochastic model 的先验；摘要未列具体参数先验。
- **likelihood**：结合 Strauss process 与 log-Gaussian Cox process；闭式 likelihood 不可得。
- **hierarchical level**：潜随机强度/交互过程 → 点模式 → ABC posterior。
- **spatial dependence structure**：吸引/聚集与排斥/规则性。
- **posterior output**：ABC posterior、posterior predictions、global envelopes。
- **evaluation protocol**：simulated point patterns + real data；用 posterior prediction/global envelope 验证。
- **human data used**：否。
- **transfers to this project**：支持把“规则性”拆成可生成的 interaction assumptions，并把模型检查放在 synthetic perturbation 中。
- **does not transfer**：点模式的 interaction radius 和 Strauss/LGCP 解释不能直接当家具间距或视觉分组。
- **locator**：摘要/Consensus fetch record；年份以 CrossRef 正式卷期为准。
- **confidence**：synthetic posterior validation high；家具语义 low。
- **follow-up need**：需在对象图上明确定义 pairwise relation 后才能讨论是否使用 ABC。

## E-D6-BAY-012 — Meshed Gaussian process

- **research question**：B；空间层次随机场如何扩展到大量位置并保留可重复计算？
- **exact title**：*Highly Scalable Bayesian Geostatistical Modeling via Meshed Gaussian Processes on Partitioned Domains*。
- **authors/year**：Michele Peruzzi, Sudipto Banerjee, A. Finley，2020。
- **DOI/stable source**：<https://doi.org/10.1080/01621459.2020.1833889>；Consensus record：<https://consensus.app/papers/highly-scalable-bayesian-geostatistical-modeling-via-peruzzi-banerjee/96cf51d71d3a539d865fd06b123107df/>；代码线索：`github.com/mkln/meshgp`。
- **source type**：可扩展 Bayesian geostatistics，*JASA* 117, 969–982。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：大规模 geostatistical locations；示例是 Serengeti NDVI 时空数据。
- **observed variables**：空间/时空位置上的多变量响应。
- **latent variables**：multivariate spatiotemporal random effects。
- **prior**：partitioned-domain meshed GP/DAG spatial process；具体超先验未在摘要给出。
- **likelihood**：分层 geostatistical likelihood，配合 Gibbs sampler；具体 family 未在摘要给出。
- **hierarchical level**：domain partition → DAG/meshed GP → random effects → observations。
- **spatial dependence structure**：tessellated domains + sparsity-inducing DAG。
- **posterior output**：空间随机效应后验；大规模矩阵缓存与并行 Gibbs 更新。
- **evaluation protocol**：large synthetic 与 real data；与 state-of-the-art 方法比较，含 NDVI 应用。
- **human data used**：否。
- **transfers to this project**：分块、缓存、可并行后验计算和 synthetic/real 双重 benchmark 的工程启发。
- **does not transfer**：tessellation/DAG 不是家具对象关系；规模优化不能代替 estimand 和 graph 的科学定义。
- **locator**：摘要；代码仓库线索只作 follow-up，不作为方法正文证据。
- **confidence**：计算架构 medium-high；家具空间语义 low。
- **follow-up need**：若布局体素化，先做 partition sensitivity 和 boundary artifact 检查。

## E-D6-BAY-013 — Simulation-based calibration

- **research question**：C；怎样验证 Bayesian 推断实现和 posterior approximation 本身是否校准？
- **exact title**：*Simulation-Based Calibration Checking for Bayesian Computation: The Choice of Test Quantities Shapes Sensitivity*。
- **authors/year**：Martin Modrák, Angie Moon, Shinyoung Kim, Paul-Christian Bürkner, Niko Huurre, Kateřina Faltejsková, A. Gelman, A. Vehtari；正式出版 2025（Consensus 索引为 2022）。
- **DOI/stable source**：<https://doi.org/10.1214/23-BA1404>；Consensus record：<https://consensus.app/papers/simulationbased-calibration-checking-for-bayesian-modrák-moon/f15067adcdb955f4b91f401ff51396c7/>。
- **source type**：Bayesian computation validation 方法论文，*Bayesian Analysis*。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：从 generative model 重复模拟的数据集；方法本身不限定空间单位。
- **observed variables**：每次模拟的数据和由推断器生成的 posterior draws。
- **latent variables**：已知模拟参数、posterior rank/校准统计量。
- **prior**：先从 prior 生成参数和数据；另讨论 conditional/posterior SBC。
- **likelihood**：由被测模型给出；方法不限定 family。
- **hierarchical level**：generative truth → inference algorithm → posterior approximation → rank/calibration check。
- **spatial dependence structure**：无专门空间结构。
- **posterior output**：SBC rank/coverage/敏感性结果，指出 test quantity 选择会漏检某些问题。
- **evaluation protocol**：重复 simulation；multivariate normal 与 ordered-simplex/HMC case study。
- **human data used**：否。
- **transfers to this project**：Bayesian candidate 必须在 synthetic truth 上做 SBC；不能只看 sampler 运行成功或 posterior 有数值。
- **does not transfer**：SBC 只能验证计算/模型自洽，不能验证家具语义或心理效度。
- **locator**：摘要/Consensus fetch record。
- **confidence**：校准原则 high；本项目具体 test quantity 待设计。
- **follow-up need**：把 axis/order/tie/missingness 作为 data-dependent test quantities，避免只检验参数 rank。

## E-D6-BAY-014 — Bayesian model checking

- **research question**：C；Bayesian hierarchical model 是否必须做 prior/posterior predictive 和空间残差检查？
- **exact title**：*A guide to Bayesian model checking for ecologists*。
- **authors/year**：P. B. Conn, Devin S. Johnson, Perry J. Williams, S. Melin, M. Hooten，2018。
- **DOI/stable source**：<https://doi.org/10.1002/ecm.1314>；Consensus record：<https://consensus.app/papers/a-guide-to-bayesian-model-checking-for-ecologists-conn-johnson/f803a5756ea95fb0ba1a4885081ba8a8/>。
- **source type**：Bayesian model checking 综述/方法指南，*Ecological Monographs*。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：层次生态数据；含 simulated spatiotemporal counts 和多个真实数据案例。
- **observed variables**：计数、检测/观测数据、时空位置和层次 covariates。
- **latent variables**：生态过程、观测误差、层次随机效应。
- **prior**：prior predictive distribution/check；具体模型先验依案例而定。
- **likelihood**：多个 hierarchical likelihood；摘要未限定单一 family。
- **hierarchical level**：数据、过程、观测误差和空间/时间层次。
- **spatial dependence structure**：检查 residual spatial/temporal autocorrelation。
- **posterior output**：posterior predictive p-values、CV PIT、pivot discrepancy、targeted diagnostics。
- **evaluation protocol**：simulation case + real case studies；指出普通 posterior predictive p-value 对细微 lack-of-fit 不敏感。
- **human data used**：否。
- **transfers to this project**：直接支持 prior predictive、posterior predictive、空间残差和 targeted discrepancy 的检查组合。
- **does not transfer**：生态观测误差和 abundance 语义不能解释家具 order；model check 不是有效性证明。
- **locator**：摘要/Consensus fetch record。
- **confidence**：模型检查原则 high；具体实现 medium。
- **follow-up need**：为每个 descriptor 预先声明 discrepancy，避免事后挑选最有利统计量。

## E-D6-BAY-015 — Stacking of predictive distributions

- **research question**：C；同一 estimand 的多个候选是否可以在比较后融合？
- **exact title**：*Using Stacking to Average Bayesian Predictive Distributions (with Discussion)*。
- **authors/year**：Yuling Yao, Aki Vehtari, Daniel Simpson, Andrew Gelman；正式出版 2018（Consensus 索引为 2017）。
- **DOI/stable source**：<https://doi.org/10.1214/17-BA1091>；公开重印：<https://sites.stat.columbia.edu/gelman/research/published/stacking.pdf>；Consensus record：<https://consensus.app/papers/using-stacking-to-average-bayesian-predictive-yao-vehtari/346e109a0940557dbdc3bf8436393cfc/>。
- **source type**：Bayesian model combination 方法论文，*Bayesian Analysis* 13(3), 917–1003。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：候选模型对同一预测量的 predictive distributions；模拟数据与真实数据案例。
- **observed variables**：训练数据、候选模型的 posterior predictive density。
- **latent variables**：stacking weights；这些权重不是默认的 posterior model probabilities。
- **prior**：权重在 simplex 上并可正则化；BB-pseudo-BMA 是近似替代，具体先验细节需全文核对。
- **likelihood**：候选模型各自的 posterior predictive；组合目标用 proper scoring rule/LOO predictive density。
- **hierarchical level**：候选模型 → LOO predictive distributions → weighted predictive mixture。
- **spatial dependence structure**：原论文无专门空间依赖。
- **posterior output**：组合后的 predictive distribution 与权重。
- **evaluation protocol**：simulation + real-data applications；与 BMA、stacking of means、pseudo-BMA 比较。
- **human data used**：否。
- **transfers to this project**：只有当 deterministic/Bayesian 输出被提升为同一 probabilistic estimand，才讨论 scoring-rule 约束的融合；保留各模型权重、身份和不确定性。
- **does not transfer**：不能把不同 quantity（order、trend、grouping）的数值做加权平均；不能把 BMA/stacking 当作模型正确性证明。
- **locator**：公开摘要；正式论文第 917–1003 页的可用版本入口。
- **confidence**：同 estimand 融合 high；本项目 descriptor 融合仍为 engineering inference。
- **follow-up need**：先定义共同 predictive quantity 和 synthetic held-out scoring，再决定是否需要 fusion。

## E-D6-BAY-016 — Bayesian hierarchical stacking

- **research question**：C；模型性能随输入区域变化时，融合权重是否需要分层/局部变化？
- **exact title**：*Bayesian Hierarchical Stacking: Some Models Are (Somewhere) Useful*。
- **authors/year**：Yuling Yao, Gregor Pirvs, Aki Vehtari, A. Gelman，2021。
- **DOI/stable source**：<https://doi.org/10.1214/21-BA1287>；Consensus record：<https://consensus.app/papers/bayesian-hierarchical-stacking-some-models-are-somewhere-yao-pirvs/a4b00b538ce85aec8fe94621ab013300/>。
- **source type**：Bayesian model-combination 方法论文，*Bayesian Analysis* 17, 1043–1071。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：带输入条件的多模型预测；抽象上可对应不同空间区域/场景子集。
- **observed variables**：输入特征、真实响应和各候选模型预测。
- **latent variables**：随输入变化且 partial-pooled 的 stacking weights。
- **prior**：structured priors/hyperprior；具体形式未在摘要中给出。
- **likelihood**：组合预测模型；具体 response family 未在摘要中给出。
- **hierarchical level**：全局/局部输入 → partial-pooled weights → predictive mixture。
- **spatial dependence structure**：原论文不是家具空间模型；输入可以是 structured covariates。
- **posterior output**：局部权重后验和组合预测。
- **evaluation protocol**：理论界、simulation 和 applied problems。
- **human data used**：否。
- **transfers to this project**：如果同一 estimand 在不同空间子域由不同模型更适合，可以讨论局部权重；必须保留模型身份与空间条件。
- **does not transfer**：不能用局部权重把多个不同 descriptor 拼成“总 order 分数”。
- **locator**：摘要/Consensus fetch record。
- **confidence**：条件融合原则 medium-high；家具应用 low。
- **follow-up need**：先证明场景子域是同一 estimand 的重复预测任务，而不是不同 descriptor。

## E-D6-BAY-017 — Bayesian predictive model selection and projection

- **research question**：C；模型选择、CV 和 model uncertainty 如何防止选择诱导偏差？
- **exact title**：*Comparison of Bayesian predictive methods for model selection*。
- **authors/year**：Juho Piironen, Aki Vehtari；正式出版 2016（Consensus 索引为 2015）。
- **DOI/stable source**：<https://doi.org/10.1007/s11222-016-9649-y>；Consensus record：<https://consensus.app/papers/comparison-of-bayesian-predictive-methods-for-model-piironen-vehtari/91862a1a132f5cc5b482aa6275e83365/>。
- **source type**：Bayesian predictive model-selection 比较论文，*Statistics and Computing* 27, 711–735。
- **full-text status**： full_text。
- **evidence grade**： full_text。
- **data unit**：regression/classification observations；simulation 与 real data。
- **observed variables**：响应、候选 predictors 和候选子模型输出。
- **latent variables**：变量子集/子模型及其参数不确定性。
- **prior**：模型依赖的 Bayesian priors；摘要未列具体分布。
- **likelihood**：regression/classification likelihood；摘要未限定单一 family。
- **hierarchical level**：候选模型空间 → predictive utility/model selection → selected/projection model。
- **spatial dependence structure**：无专门空间结构。
- **posterior output**：model uncertainty、BMA/full model 或 projection submodel；CV utility 估计。
- **evaluation protocol**：simulated + real data；检查 CV 高方差、selection-induced bias 和外部评估。
- **human data used**：否。
- **transfers to this project**：支持把模型竞争和最终评价分开；不能用同一 synthetic fixture 既调选择规则又报告最终性能。
- **does not transfer**：回归变量子集选择不等于 axis/order/grouping 选择；不能直接提供空间语义。
- **locator**：摘要/Consensus fetch record。
- **confidence**：竞争/外部评价原则 medium-high；家具 descriptor 迁移 medium。
- **follow-up need**：为 Bayesian candidate 预注册比较量和独立 synthetic test split。

## E-D6-BAY-018 — Evidence boundary: no direct IFC-furniture Bayesian descriptor

- **research question**：A–D；当前检索是否已找到直接的 IFC 家具、无人工标签、Bayesian order/grouping 自描述证据？
- **exact title**：不是论文；本轮检索空缺记录。
- **authors/year**：不适用。
- **DOI/stable source**：不适用；检索日志和以上结果可复核。
- **source type**：`inaccessible`/evidence gap record。
- **full-text status**：`inaccessible` for the unlocated direct precedent。
- **evidence grade**：`inaccessible`。
- **data unit**：没有可确认的 IFC 家具 Bayesian 自描述数据集。
- **observed variables**：没有可确认的 canonical IFC geometry + object relation protocol。
- **latent variables**：没有可确认的 axis/order/group/trend estimand。
- **prior**：没有可确认的家具场景先验。
- **likelihood**：没有可确认的家具场景 likelihood。
- **hierarchical level**：没有可确认的 IFC 家具空间层次模型。
- **spatial dependence structure**：没有可确认的家具对象 graph/CAR/GP 定义。
- **posterior output**：没有可确认的家具 descriptor posterior。
- **evaluation protocol**：没有可确认的 synthetic truth、identifiability 或 posterior calibration protocol。
- **human data used**：未知；不能据空缺推断不存在。
- **transfers to this project**：只能把上面的方法组件作为候选结构；本项目必须自己定义 estimand、truth 和 status contract。
- **does not transfer**：不能把“Bayesian + space + hierarchy”的关键词拼成直接先例。
- **locator**：本轮查询、Consensus fetch、CrossRef 和官方/机构结果见 search log。
- **confidence**：空缺判断 medium；不能据此声称领域中绝对不存在相关工作。
- **follow-up need**：若 owner 要求“直接 IFC 证据”，需要继续查 BIM/IFC/indoor-layout 专门数据库或由 owner 提供原文。

## 账本级结论

1. 最强的 scene-only 计算先例是 Froyen/BHG、BHC、Del Pero 的几何生成模型和 Straub 的潜在轴混合模型；它们支撑“可以从观测几何提出潜变量”这一方法学可能性。
2. 最强的空间模型验证先例是 Leininger–Gelfand、Vihrs–Møller–Gelfand、Porter–Franck–Ferreira 和 Modrák 等，它们支撑 synthetic truth、posterior predictive、model selection 和 SBC，而不支撑家具语义。
3. 最强的融合先例是 Yao 等 stacking；它只支持同一 predictive estimand 上的组合，并不支持把 order、trend、grouping 压成一个未经定义的总分。
4. 没有一条记录可以证明人会觉得某种家具布局“有序、舒适或整体”；这类结论必须继续留在项目外部实验范围。

## 工程推断记录（不是文献事实）

### E-D6-ENG-001

- **evidence grade**：`engineering_inference`
- **research question**：C/D；如何把 deterministic baseline 与 Bayesian candidate 放入同一设计门？
- **claim**：先固定共同 canonical geometry、synthetic truth、扰动和 estimand，再比较 recovery、invariance、robustness、identifiability、calibration、reproducibility 和计算成本；不要因 posterior 存在而默认升级。
- **basis**：E-D6-BAY-009、010、013、014、017 与当前 clean-room contract。
- **locator**：本账本上述条目；`docs/superpowers/specs/2026-09-27-clean-room-layout-descriptor-contract-design.md` 的 Bayesian track。
- **source type/full-text status**：工程推导；不适用。
- **transfer boundary**：这是项目设计建议，不是任何一篇论文的直接结论。
- **confidence**：medium-high 作为审查流程建议；模型具体优劣未知。
- **follow-up need**：Task 3c synthetic probe 和 owner review。

### E-D6-ENG-002

- **evidence grade**：`engineering_inference`
- **research question**：D；何时允许 fusion？
- **claim**：若输出估计不同 quantity（例如 latent axis、reference-order consistency、authored-group trend、group membership），保留独立输出；只有相同 estimand、相同单位/状态和共同 held-out synthetic scoring 时，才讨论 posterior predictive stacking 或其他融合。
- **basis**：E-D6-BAY-015、016 与当前 `DescriptorResult`/`AxisSpec`/`reference_order` 契约。
- **locator**：本账本 E-D6-BAY-015/016；clean-room spec 的 Candidate competition and fusion 段落。
- **source type/full-text status**：工程推导；不适用。
- **transfer boundary**：stacking 文献讨论同一预测量的 predictive distributions，不能直接授权 descriptor scalar 加权。
- **confidence**：high 作为接口边界建议；融合方法本身未在本项目验证。
- **follow-up need**：定义共同 predictive quantity、模型身份和融合 provenance 后再做实验。

### E-D6-ENG-003

- **evidence grade**：`engineering_inference`
- **research question**：D；Bayesian candidate 如何与当前 relative-order 连接？
- **claim**：Bayesian 可作为 `AxisSpec` 或 latent-result 的推断来源，但不能静默替换显式 axis/reference_order；多峰、纯 tie、missing 或 contradictory members 应保留低信息/不可辨识状态，不能强制输出唯一轴或零分。
- **basis**：E-D6-BAY-001、005、010、013 与 `d6-relative-order-design-experiment.md`。
- **locator**：本账本 E-D6-BAY-001/005/010/013；`docs/project/d6-relative-order-design-experiment.md` 的 Data contract/status 段落。
- **source type/full-text status**：工程推导；不适用。
- **transfer boundary**：状态名、载荷和 provenance 需要后续合同评审，不是现有生产接口变更。
- **confidence**：medium-high。
- **follow-up need**：为 posterior multimodality、pairwise ties、missingness 和 contradictory members 增加 synthetic fixtures。

## E-D6-BAY-019 — Structured Graph Variational Autoencoders for Indoor Furniture Layout Generation

- **research question**：A；是否有以家具对象关系图和潜变量生成室内布局的相邻计算先例？
- **exact title**：*Structured Graph Variational Autoencoders for Indoor Furniture layout Generation*。
- **authors/year**：Aditya Chattopadhyay, Xi Zhang, David Paul Wipf, Himanshu Arora, René Vidal，2022。
- **DOI/stable source**：arXiv:2204.04867；<https://arxiv.org/abs/2204.04867>。
- **source type**：室内家具图生成/graph VAE；非 Bayesian spatial model，作为相邻 probabilistic latent-graph 证据。
- **full-text status**：`full_text`；作者 arXiv v3 22 Jul 2022 PDF 已核读。
- **evidence grade**：`full_text`。
- **data unit**：3D-FRONT 室内 scene graph；room/furniture nodes 与 room-room、room-furniture、furniture-furniture edges。
- **observed variables**：对象类别、位置、orientation、size、3D shape descriptor；边属性含 relative location/orientation 与 functional/geometric relationships。
- **latent variables**：每个 furniture node 的 latent Z；room-aware layout distribution p(GF|GR,T,nF)。
- **prior**：room-conditioned autoregressive linear-Gaussian prior p(Z|nF,GR,T)，按 latent node order 产生依赖；encoder qφ 为 diagonal Gaussian。
- **likelihood**：decoder factorizes shape/orientation/location/size/category distributions；训练目标是 ELBO 加 constraints。
- **hierarchical level**：room graph → latent furniture graph → generated furniture graph；不是 IFC authored hierarchy。
- **spatial dependence structure**：完整 attributed graph 的 edge relationships；prior 的顺序是生成 latent 的计算顺序，不是场景中发现的 relative order。
- **posterior output**：approximate posterior qφ(Z|G,T,nF)、sampled layouts 和 latent traversal；不输出模型校准的家具 order posterior。
- **evaluation protocol**：3D-FRONT 约 14k rooms，80:20 split；与 iid/non-autoregressive priors 和 ATISS 比较 category KL、real-vs-synthetic scene classifier、generation time；训练使用 shape descriptors 和 7 个 super-categories。
- **human data used**：数据集和 ShapeNet/PointNet 预训练 shape descriptors 含人工类别/资产信息；没有人的舒适/有序评分。
- **transfers to this project**：支持把对象关系、相对方向和形状作为共同 graph input，并把 latent graph generation 与 authored grouping 分开。
- **does not transfer**：这是监督/数据集驱动的生成模型，不是从单个 canonical IFC 场景无标签发现 axis/order；latent node order 是模型参数化，不是物理顺序真值。
- **locator**：PDF pp. 4–8，§3.1–3.4、式 1–8；pp. 9–10，§4 与 Table 1。
- **confidence**：图 latent/生成结构 high；本项目 scene-self-description 迁移 medium-low。
- **follow-up need**：若保留为相邻证据，只需提取 graph schema 与 status/provenance 启发；不要把它加入 Bayesian order 候选。

## E-D6-BAY-020 — Automated modeling to high level-of-detail composite object using spatial BIM objects and properties

- **research question**：A/D；IFC/BIM 家具组合与 authored spatial relation 是否有直接工程相邻证据？
- **exact title**：*Automated modeling to high level-of-detail composite object using spatial BIM objects and properties*。
- **authors/year**：Jin-Kook Lee, Dahngyu Cho, Youngchae Kim, Yunjeong Mo 等，2026（online 2025）。
- **DOI/stable source**：<https://doi.org/10.1038/s41598-025-32433-9>；官方全文页 <https://www.nature.com/articles/s41598-025-32433-9>。
- **source type**：Scientific Reports BIM composite-object / rule-based parametric layout；不是 Bayesian 论文。
- **full-text status**：`official`；Nature 官方全文 HTML 与摘要/方法段可读；PDF 下载被 cookie gate 阻断，本条不标 full_text。
- **evidence grade**：`official`。
- **data unit**：IfcSpace/Revit room objects、furniture composite objects、space attributes 和 design-rule table。
- **observed variables**：space GUID/area/topology、space type/function、number of users、object area/movability/hierarchy/clearance/wall-likelihood。
- **latent variables**：没有 Bayesian posterior；host object 与 composite grouping 是按规则决定的 authored/parametric state。
- **prior**：无概率 prior；规则来自住宅设计指南与既有布局。
- **likelihood**：无统计 likelihood；按 space division、object selection、host-first alignment 与 clearance rules 生成布局。
- **hierarchical level**：space → host/composite object → child furniture placement。
- **spatial dependence structure**：显式 pairwise relations、clearance、wall proximity、host hierarchy；不是 CAR/GP。
- **posterior output**：参数化 composite-object layout；无 posterior uncertainty。
- **evaluation protocol**：Revit/Dynamo prototype、living-room scenarios；可行性/演示为主，不是 Bayesian calibration 或 synthetic latent-order recovery。
- **human data used**：设计指南、用户输入（space function/number of users）和人工定义规则；研究未做本项目意义上的心理评分验证。
- **transfers to this project**：直接提醒 \`IfcSpace\`、authored group、host/child hierarchy、clearance 和 provenance 是输入/规则来源，不能被 latent grouping 偷换。
- **does not transfer**：规则驱动与用户输入不支持“场景自身 Bayesian 自描述”；页面/摘要也不能证明 IFC 序列、order 或 posterior。
- **locator**：官方全文 lines 65–83、91–125、159–180、190–229、231–251（Nature 页面行号）；PDF 未取得。
- **confidence**：IFC/BIM authored relation boundary high；Bayesian relevance none。
- **follow-up need**：作为边界证据保留，不继续扩大到一般 BIM layout 论文，除非 owner 具体要求 IFC 关系 schema。

## E-D6-BAY-021 — Empirical Bayesian kriging implementation and usage

- **research question**：B/C；当空间观测稀疏、非平稳、非高斯或含测量误差时，经验贝叶斯空间预测如何表达参数与预测不确定性？
- **exact title**：*Empirical Bayesian kriging implementation and usage*。
- **authors/year**：Alexander Gribov, Konstantin Krivoruchko，2020。
- **DOI/stable source**：<https://doi.org/10.1016/j.scitotenv.2020.137290>；ScanSci 原文 `C:/Users/tianf/Downloads/d6-ebk-scansci/Gribov2020_Empirical.pdf`。
- **source type**：经验贝叶斯地统计/EBK 方法论文，*Science of the Total Environment* 722, 137290。
- **full-text status**：`full_text`；ScanSci Sci-Hub(browser) 获取的 journal pre-proof，已核读关键方法、模拟和评价章节。
- **evidence grade**：`full_text`。
- **data unit**：带坐标的采样点 `s_i`，每点有标量观测 `z_i`；允许 coincident data 与 individual measurement error。
- **observed variables**：`z_i = y(s_i) + ε_i`；坐标、协变量、局部邻域和测量误差信息。
- **latent variables**：空间过程 `y(s)`、均值/趋势、半变异函数或协方差参数、局部模型与预测值。
- **prior**：通过 unconditional simulations 构造 informative empirical prior；Bayes 公式把 prior 更新为 posterior。
- **likelihood**：局部 Gaussian/变换后的空间过程模型；支持 nonstationarity、非高斯观测变换和局部模型合并。
- **hierarchical level**：观测值 → 空间过程与协方差/趋势参数 → 局部模型集合 → 目标位置 posterior prediction。
- **spatial dependence structure**：距离邻域、局部半变异函数/协方差、移动窗口和子区域模型；不是 CAR/ICAR 邻接图。
- **posterior output**：目标位置预测均值、预测标准误、prediction distribution 和区间；模型参数 posterior 由经验 prior 与数据共同决定。
- **evaluation protocol**：一项 simulation 与两个高变异数据 case study；比较 prediction accuracy 和 prediction standard error，含 RMSPE/RMSSPE 与区间覆盖诊断。
- **human data used**：否；环境/地理测量数据，无心理评分或人工 order label。
- **transfers to this project**：若一个家具组被定义为一个带代表坐标的空间点，EBK 可预测该组位置上的某个连续标量场或 group-level response，并保留预测不确定性。
- **does not transfer**：EBK 不负责发现家具组、决定 `IfcGroup` membership 或推断 relative order；它需要先给定点、响应变量和空间支持。把组质心当点会丢失组内几何，必须记录代表点和 support 规则。
- **locator**：摘要；§2.1–§2.3 prior/posterior、subsetting/merging；§3 prediction；§4 simulation/evaluation。
- **confidence**：EBK 预测结构 high；家具组点迁移 medium；order/grouping 直接迁移 low。
- **follow-up need**：先定义 group representative point、response quantity、support/尺度和 held-out scene，再与 deterministic spatial baseline 比较。

## E-D6-BAY-022 — Evaluation of empirical Bayesian kriging

- **research question**：B/C；EBK 的 empirical prior、预测精度和不确定性覆盖是否经过受控验证？
- **exact title**：*Evaluation of empirical Bayesian kriging*。
- **authors/year**：Konstantin Krivoruchko, Alexander Gribov，2019。
- **DOI/stable source**：<https://doi.org/10.1016/j.spasta.2019.100368>；ScanSci 原文 `C:/Users/tianf/Downloads/d6-ebk-scansci/Krivoruchko2019_Evaluation.pdf`。
- **source type**：EBK 方法评价论文，*Spatial Statistics*，article 100368。
- **full-text status**：`full_text`；ScanSci 获取 accepted manuscript，已核读方法、simulation、case study 和 validation diagnostics。
- **evidence grade**：`full_text`。
- **data unit**：空间采样点的 precipitation 或 satellite land-surface-temperature 观测。
- **observed variables**：点坐标、观测值、局部邻域和可选 covariates；模型为 `z_i = y(s_i)+ε_i`。
- **latent variables**：空间过程、协方差/半变异参数、经验 Bayesian bootstrap prior、预测值和预测误差。
- **prior**：Bayesian bootstrap 构造 informative prior；EBK 不要求用户手工指定完整 prior 参数。
- **likelihood**：IRFK/LMM 地统计模型；支持局部/全局非平稳性、数据变换和测量误差。
- **hierarchical level**：观测点 → 空间过程与协方差/趋势参数 → empirical prior/posterior → 局部或全局 prediction。
- **spatial dependence structure**：局部邻域、半变异函数/协方差和子集模型；依赖距离与邻域，不是 CAR/ICAR 图邻接。
- **posterior output**：预测值、预测标准误、90% prediction interval 与 predictive diagnostics。
- **evaluation protocol**：两项大型 simulation；真实 South Africa 年降水和 daytime land-surface-temperature 数据；与多种 R 中的地统计模型比较，使用 RMSPE、RMSSPE、CRPS 和 prediction-interval coverage。
- **human data used**：否；使用环境与遥感测量，不使用心理或人工 order 评分。
- **transfers to this project**：支持“同一空间 response 上比较 deterministic、普通 Bayesian、EBK”的评价门；尤其提醒同时检查误差大小与区间覆盖。
- **does not transfer**：EBK 在复杂环境场上的较好表现不能证明它适合家具语义；模型优劣依赖 response、点密度、邻域和尺度。
- **locator**：摘要；§2 EBK prior；§3 simulation；§4 precipitation case；§5 satellite comparison；Table 4 与 prediction diagnostics。
- **confidence**：评价协议 high；家具 group-level response 迁移 medium-low。
- **follow-up need**：在独立 synthetic furniture-group scenes 上复现实验，禁止直接移植环境数据的参数。

## E-D6-BAY-023 — Interpolation with uncertain spatial covariances: a Bayesian alternative to Kriging

- **research question**：B/C；完全 Bayesian 的空间插值如何把协方差参数不确定性传递到预测区间？
- **exact title**：*Interpolation with Uncertain Spatial Covariances: A Bayesian Alternative to Kriging*。
- **authors/year**：Nhu D. Le, James V. Zidek，1992。
- **DOI/stable source**：<https://doi.org/10.1016/0047-259X(92)90040-M>；ScanSci 原文 `C:/Users/tianf/Downloads/d6-ebk-scansci/Le1992_Interpolation.pdf`。
- **source type**：完全 Bayesian 空间插值方法论文，*Journal of Multivariate Analysis* 43, 351–374。
- **full-text status**：`full_text`；ScanSci Sci-Hub(browser) 获取并核读全文。
- **evidence grade**：`full_text`。
- **data unit**：gauged sites 的空间场观测与 ungauged sites 的待预测值；可扩展到时间重复观测。
- **observed variables**：离散空间位置、场值、协变量和先验协方差结构。
- **latent variables**：空间随机场、均值/回归参数、协方差矩阵及其层级超参数。
- **prior**：层级协方差先验与共轭结构；把参数不确定性显式留在 posterior。
- **likelihood**：多元正态及相关层级模型；预测分布由观测和协方差 posterior 联合产生。
- **hierarchical level**：gauged observations → spatial field/covariance parameters → hyperparameter prior/posterior → ungauged-site predictive distribution。
- **spatial dependence structure**：参数化空间协方差矩阵，按站点距离/协方差关系连接 gauged 与 ungauged sites；可扩展时间相关，不是 MRF 邻接。
- **posterior output**：ungauged locations 的 posterior predictive distribution、均值和可信区间。
- **evaluation protocol**：理论推导、空间/时间插值和模型 misspecification 下的稳健性讨论；不是家具数据评价。
- **human data used**：否。
- **transfers to this project**：作为 EBK 的 fully Bayesian comparator，支持把 group-level response 的 covariance uncertainty 纳入预测区间。
- **does not transfer**：仍是插值问题；不能由空间 covariance 自动产生家具 group membership、axis 或 order。
- **locator**：摘要与 pp. 351–371；§1–§2 hierarchical model；Theorem 2.3 predictive distribution。
- **confidence**：完全 Bayesian 插值结构 high；家具语义迁移 low。
- **follow-up need**：若比较 EBK 与 fully Bayesian kriging，必须固定相同 group point、response、support 和 holdout。

## E-D6-BAY-024 — Empirical Bayesian Kriging Implemented in ArcGIS Geostatistical Analyst

- **research question**：B；ArcGIS EBK 的工程定位是否是带预测不确定性的自动空间插值器？
- **exact title**：*Empirical Bayesian Kriging Implemented in ArcGIS Geostatistical Analyst*。
- **authors/year**：Konstantin Krivoruchko，2012。
- **DOI/stable source**：ArcUser Fall 2012 原文：用户提供 `C:/Users/tianf/Downloads/Empirical Bayesian Kriging.pdf`；相关 Esri 页面：<https://www.esri.com/about/newsroom/arcuser/a-little-more-about-two-geostatistical-methods>；该杂志文章无 DOI。
- **source type**：GIS/ArcGIS 方法说明，ArcUser technical article。
- **full-text status**：`full_text`；用户提供的 ArcUser PDF 已核读全文。
- **evidence grade**：`full_text`。
- **data unit**：空间采样位置与环境变量观测。
- **observed variables**：已观测位置的环境数值，待插值位置无观测。
- **latent variables**：真实半变异函数/空间相关结构、未观测位置的场值和预测误差。
- **prior**：通过反复模拟和 Bayes 权重形成半变异函数模型分布；默认使用 intrinsic random function of order 0 与 power model。
- **likelihood**：基于空间距离/方向的 semivariogram 与局部 kriging 模型；可对数据做局部 Gaussian transformation。
- **hierarchical level**：观测位置/数值 → 多个 semivariogram 候选 → Bayes 权重 → 未采样位置的 kriging prediction。
- **spatial dependence structure**：距离与方向决定 semivariogram；大数据按邻近子集建局部模型，再合并重叠子集预测，不是 CAR/ICAR 图邻接。
- **posterior output**：未采样位置的预测值、prediction standard error 和加权 semivariogram spectrum。
- **evaluation protocol**：Fukushima 137Cs 土壤污染示例；大数据时按邻近子集建模并合并预测。文章报告 ArcGIS 10.1 Geostatistical Analyst 实现和 extensive testing，但不是家具 synthetic calibration。
- **human data used**：否；文章描述环境测量，无心理评分或人工 order label。
- **transfers to this project**：补强 EBK 的工程语义：它用多个 semivariogram 候选及 Bayes 权重传播相关结构估计误差；家具组可作为带代表坐标的点。
- **does not transfer**：默认 EBK 仍预测点位置上的标量空间场；它不定义家具组 membership、组内 support 或 relative order。
- **locator**：用户 PDF pp. 1–4，Kriging 与 Introducing Empirical Bayesian Kriging；pp. 5–7，subsets、nonstationarity 和 Fukushima example。
- **confidence**：ArcGIS EBK 机制 high；家具 group-point 迁移 medium。
- **follow-up need**：若复刻 ArcGIS 参数行为，记录 subset size、overlap、邻域和 power semivariogram 参数；不要把软件默认值当项目真值。

## E-D6-BAY-025 — Identifying latent groups in spatial panel data using a Markov random field constrained product partition model

- **research question**：B；空间依赖是否可以直接进入 latent group partition prior，并在 posterior 中恢复空间组？
- **exact title**：*Identifying latent groups in spatial panel data using a Markov random field constrained product partition model*。
- **authors/year**：Tianyu Pan, Guanyu Hu, Weining Shen，2020 arXiv version；正式刊载 2023。
- **DOI/stable source**：<https://doi.org/10.5705/ss.202021.0247>；arXiv `2012.10541v1`；用户提供全文 `C:/Users/tianf/Downloads/2012.10541v1.pdf`。
- **source type**：MRF-PPM 非参数 Bayesian spatial clustering；不是 EBK 插值。
- **full-text status**：`full_text`；用户 arXiv v1 已核读方法、理论、simulation 与两个 real-data application 章节。
- **evidence grade**：`full_text`。
- **data unit**：N 个空间位置；每个位置有重复时间观测、response 和 covariates。
- **observed variables**：`Y_i(t_j)`、`X_i(t_j)`、空间图 `G_N` 与邻接边。
- **latent variables**：空间位置 partition `C`、cluster assignment `c_i`、组共享回归参数 `θ_c`。
- **prior**：MRF prior 与 product partition model prior 的乘积；MRF 使用已知空间图，PPM cohesion 表达组内相似性。
- **likelihood**：组内共享参数的 regression likelihood `f_{θ_c}(Y_i|X_i)`；允许时间相关结构。
- **hierarchical level**：空间位置/重复观测 → partition 与 cluster assignment → 组共享回归参数 → posterior partition 与 cluster-wise inference。
- **spatial dependence structure**：已知无向图邻接；空间平滑参数 `λ` 控制相邻位置同组倾向。
- **posterior output**：partition posterior、cluster-wise parameters、marginal likelihood 和组恢复结果；提供 clustering consistency 理论。
- **evaluation protocol**：两类 48-state synthetic partition，1000 MCMC iterations/replication；US precipitation 与 California county median-income applications，使用 marginal likelihood 选 `λ`。
- **human data used**：否；使用气候、经济和行政空间面板数据，无心理评分或人工 order label。
- **transfers to this project**：这是“家具组作为空间单元并推断 latent group”的更直接先例；可以把 furniture group representative point 放进图，另以 group-level response 建模。
- **does not transfer**：模型假设重复 response/covariates 和已知空间图；它不是从单个 IFC 场景的几何直接发现物理组，也不输出家具 order。
- **locator**：PDF pp. 1–5 摘要/动机/模型；pp. 6–13 理论与 marginal likelihood；pp. 14–22 simulation；pp. 23–31 precipitation/income applications。
- **confidence**：latent spatial grouping 结构 high；家具 group-point 迁移 medium；单场景 geometry-only 迁移 low。
- **follow-up need**：若采用此方向，先定义 group-level repeated response 或替代 response，并固定 spatial graph 与 authored-group 边界。

本轮证据增量已经完成。尚未选择 Bayesian 生产模型，尚未实现 Bayesian 代码；下一步是 owner 审查 Task 3c 的首要 estimand。

STOP FOR DESIGN REVIEW
