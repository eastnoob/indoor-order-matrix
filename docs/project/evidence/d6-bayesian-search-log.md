# D6 Bayesian 场景自描述检索日志

- 研究日期：2026-09-28
- 任务：为“无人参与的 Bayesian 场景自描述、确定性模型与 Bayesian 模型竞争/融合”补齐增量证据。
- 范围：空间层次模型、CAR/ICAR、Gaussian process、空间点过程、几何场景生成/分组、后验预测检查、simulation-based calibration、模型比较与融合。
- 明确排除：生产 Bayesian 代码、真人实验、人工标签作为本项目目标、修改 `features/`、`adapters/`、`test/`，以及把感知模型直接改写成家具指标。

## 实际读取和使用的技能

| 技能 | 实际用途 |
|---|---|
| `literature-review` | 先定义检索范围、记录查询和访问日期、按主题综合而不是逐篇罗列。 |
| `paper-lookup` | 按 DOI/标题核对来源、区分检索结果与可复核正文，并记录空缺字段。 |
| `nature-skills:nature-academic-search` | 采用 T1→T2→T3 来源路由；使用 CrossRef 做 DOI 元数据交叉核对；记录检索失败和降级。 |
| `nature-skills:nature-ref-verifier` | 对标题、作者、年份和 DOI 做字段级核查；特别记录 Consensus 年份与 CrossRef 年份冲突。 |
| `scientific-critical-thinking` | 将“论文展示了什么”与“项目可以推导什么”分开，并审查可辨识性、混淆、外推边界。 |
| `experimental-design` | 把 synthetic truth、扰动因素、评价量和决策规则先写清楚；不把视觉上合理当作计算验证。 |
| `citation-management` | 用 DOI、稳定 URL 和 CrossRef 返回值生成可复核的引用记录。 |
| `grill-me` | 用反向问题逐条检查 Bayesian 可能性是否被误写成项目事实、是否混淆 reference order/latent axis/trend，以及 fusion 是否被简化成平均。 |
| `pdf` | 对用户提供的 `C:/Users/tianf/Downloads/froyen2015.pdf` 做本地全文提取和页码定位。 |

## 检索与核验步骤

### 1. 项目内部材料

读取了 `AGENTS.md`、D3–D5 evidence ledger/search log/synthesis、`d6-relative-order-design-experiment.md`、当前 clean-room spec、当前 plan，以及两份 raw requirements。旧文件未被改写。

### 2. 用户提供 PDF

使用 Pixi 环境中的 `pdftotext -layout` 提取 `froyen2015.pdf`。本地文件显示：

- Vicky Froyen、Jacob Feldman、Manish Singh，**Bayesian Hierarchical Grouping: Perceptual Grouping as Mixture Estimation**，*Psychological Review* 122(4), 575–597，2015。
- DOI：`10.1037/a0039540`。
- 页 576–579：混合模型、Dirichlet process prior、BHC/BHG 树、后验分组假设和 posterior predictive。
- 页 580–581：曲线对象的 compactness/straightness 先验、rib-likelihood 和超参数。
- 页 581–583：dot lattice、contour grouping 与人类判断对比。
- 页 586–588：part decomposition、completion 和 posterior predictive uncertainty。

该记录因此标为 `full_text`。论文中的感知实验与人类判断只作为“不可迁移边界”记录，不作为家具布局证据。

### 3. Consensus 检索

Consensus 规则要求：搜索结果不能直接引用，必须先用 `consensus_fetch(id)` 获取完整记录。本次先后执行了以下主题检索，并抓取了下表所列结果：

| 查询 | 主要结果 |
|---|---|
| `Bayesian spatial point process latent interaction synthetic data posterior predictive check` | Leininger & Gelfand 2017；Vihrs, Møller & Gelfand 2021；空间点过程 posterior predictive/ABC/global envelope。 |
| `Bayesian hierarchical model GIS spatial random effects CAR ICAR geostatistics` | Gelfand 2012；Gelfand & Schliep 2016；Riebler et al. 2016；Porter et al. 2024；Peruzzi et al. 2020。 |
| `Bayesian model comparison deterministic baseline posterior predictive checks simulation calibration model averaging stacking` | Piironen & Vehtari 2016；Yao et al. 2018；Yao et al. 2021；Conn et al. 2018；Modrák et al. 2025。 |
| `Bayesian latent spatial order axis inference geometric arrangement objects scene layout` | Del Pero et al. 2012、2013；Straub et al. 2018；Froyen et al. 2015；BHC/GENESIS 等几何或场景潜变量先例。 |
| `Bayesian hierarchical clustering Heller Ghahramani 2005 posterior grouping` | Heller & Ghahramani 2005；Froyen et al. 2015。 |

第一次并行请求遇到 Consensus rate limit；随后改为串行请求并成功抓取。已抓取的 Consensus IDs 和 DOI 见 evidence ledger。Consensus 记录只用于发现和摘要级核对，不能替代正文。

### 4. Web/官方来源与 DOI 核对

- Duke Scholars 的 Leininger–Gelfand 记录提供作者、期刊、年份、页码和摘要，并链接 DOI。
- Columbia 的 Yao et al. stacking 公开电子重印提供摘要和方法入口；本任务只把摘要可支持的结论写入账本。
- CrossRef `works/<DOI>` 逐条核对 DOI、标题和出版年份。需要特别保留的年份差异：Vihrs et al. Consensus 记录为 2020、CrossRef 正式卷期为 2021；Porter et al. Consensus 记录为 2023、CrossRef 正式卷期为 2024；Yao et al. Consensus 记录为 2017、正式出版为 2018；Modrák et al. Consensus 记录为 2022、正式出版为 2025。账本以正式出版元数据为主，并保留 online-first/索引差异。
- 没有因为摘要或搜索片段不可得而补写公式；字段无法从可访问来源确认时明确写为 `not stated in accessible abstract`。

## 检索结果的分级原则

- `full_text`：正文或用户提供的本地全文已读取，并有页码/公式/章节定位。
- `official`：官方标准、机构页面或出版方页面直接可读；若只有摘要，另外标注为摘要级结论。
- `abstract_only`：只有摘要、机构元数据或 Consensus 完整记录，没有可核查正文。
- `inaccessible`：目标来源未能取得，不能据此写方法或结果。
- `engineering_inference`：由上述证据和当前项目契约推导出的设计建议，不是文献事实。

## 主要检索来源

1. Froyen et al. 2015 本地 PDF：`C:/Users/tianf/Downloads/froyen2015.pdf`。
2. Consensus canonical records（每条记录均先 `fetch`）：见 `d6-bayesian-evidence-ledger.md`。
3. CrossRef DOI metadata：`https://api.crossref.org/works/<DOI>`。
4. Leininger & Gelfand institutional record：`https://scholars.duke.edu/publication/1241820`。
5. Yao et al. open reprint：`https://sites.stat.columbia.edu/gelman/research/published/stacking.pdf`。

## 本轮结论边界

检索到的是可迁移的计算结构：混合/层次分组、空间随机效应、点过程后验预测、模型检查、synthetic calibration 和同一预测量上的 stacking。没有找到一篇直接验证“IFC 家具布局由自身几何推断 Bayesian order 并具有心理效度”的论文；因此该命题在后续 synthesis 中只作为待验证的工程候选。

## 第二轮：ScanSci 原文获取与范围修正（2026-09-28）

用户明确允许使用 ScanSci 的灰色渠道后，按 scansci-pdf skill 先做 health/sources/setup 诊断，再以 17 个 DOI 批量下载。任务最终因服务 300 秒超时而返回错误，但 Downloads 目录已写入 17/20 个成功条目；其中 9 条有逐篇结果记录，另有 OA/缓存文件已完成。成功来源包括 oa_url、LibGen、Sci-Hub(browser)、SemanticScholar(arXiv) 和 local_cache。原始 PDF 与文本提取均保存在用户目录 `C:/Users/tianf/Downloads/d6-bayesian-scansci/`，没有写入项目仓库。

已核读并提升到 full_text 的既有记录包括 Heller 2005、Del Pero 2012/2013、Straub 2018、Gelfand 2012/2016、Riebler 2016、Porter 2024、Leininger 2017、Vihrs 2022、Peruzzi 2020、Modrák 2025、Conn 2018、Yao stacking 2018、Yao hierarchical stacking 2022、Piironen–Vehtari 2017。证据账本记录了 PDF 版本、扫描文本状态和关键章节；未取得文字层的 Heller ScanSci 副本改用作者公开版本核读。

原文使三个判断收紧：Del Pero 的场景先验来自家具目录和图像训练信息，CVPR 评价依赖人工 ground-truth；Straub 用人工 MF 数量标注和 camera/scene ground truth 做部分评价；BHC 明确是给定贪心树的近似推断，未包含完整 tree uncertainty。因而“无人”现在只表示本项目不使用人的心理评分/参与者作为目标，不能表示这些外部论文都没有人工训练、类别或评价信息。

范围扩展后新增两条相邻记录：Chattopadhyay et al. 2022 的 Structured Graph VAE（arXiv:2204.04867，取得全文）提供 3D-FRONT 家具关系图和 autoregressive latent prior，但其生成顺序不是物理 relative order；Lee et al. 2026 的 BIM Composite Object 论文提供 IfcSpace、host/child hierarchy、clearance 和规则布局边界，但没有 Bayesian posterior。它们补强了“图/规则/作者关系与 latent grouping 必须分开”的边界，没有改变直接 IFC Bayesian order 证据仍缺失的结论。

针对 IFC/BIM、家具相对顺序和 latent layout 的窄检索没有产生满足“单个 canonical geometry、无人工标签、Bayesian axis/order/group、可校准”的直接论文；ScanSci OpenAlex 查询多次超时，随后改用官方页面、作者公开 PDF、arXiv 和 Web 搜索复核。下一轮不再泛扩 GIS/Bayesian 文献，只有在 owner 指定具体 estimand（latent axis、latent grouping、latent order 或 spatial field）时定向补查。

## 第三轮：EBK / Bayesian kriging 定向补充（2026-09-28）

本轮由 owner 指定 EBK，并特别提出“一个家具组可以作为一个点”。Consensus 先搜索并 fetch 了 EBK、ArcGIS EBK、Bayesian kriging 和 spatial latent-group 记录；随后用 ScanSci 批量获取可读原文。

### Consensus 记录

- Gribov & Krivoruchko 2020，*Empirical Bayesian kriging implementation and usage*，DOI `10.1016/j.scitotenv.2020.137290`；Consensus ID `7b72c1e50a895593bdc25440f1e1eedb`。
- Krivoruchko 2012，*Empirical Bayesian Kriging Implemented in ArcGIS Geostatistical Analyst*；Consensus ID `357ab03fcf20533b924cb36f3e15e0fe`，无 DOI/全文定位。
- Krivoruchko & Gribov 2019，*Evaluation of empirical Bayesian kriging*，DOI `10.1016/j.spasta.2019.100368`；ScanSci 搜索结果确认。
- Le & Zidek 1992，*Interpolation with Uncertain Spatial Covariances: A Bayesian Alternative to Kriging*，DOI `10.1016/0047-259X(92)90040-M`；Consensus ID `6806fea4aa7c5a79a59531668f780448`。
- Pan, Hu & Shen 2020，*Identifying Latent Groups in Spatial Panel Data Using a Markov Random Field Constrained Product Partition Model*，DOI `10.5705/ss.202021.0247`；作为空间 latent-group 相邻记录检索到，但 ScanSci 未找到 PDF，未写入全文级结论。

### ScanSci 结果

- Gribov 2020：Sci-Hub(browser) accepted journal pre-proof，全文可读。
- Krivoruchko & Gribov 2019：ScanSci accepted manuscript，全文可读。
- Le & Zidek 1992：Sci-Hub(browser) 全文可读。
- Pan et al. 2020：owner 提供 `C:/Users/tianf/Downloads/2012.10541v1.pdf`，已核读 arXiv v1 全文，升级为 `full_text`。
- ArcGIS 2012：owner 提供 `C:/Users/tianf/Downloads/Empirical Bayesian Kriging.pdf`，已核读 ArcUser Fall 2012 全文；确认该杂志文章无 DOI，升级为 `full_text`。

### 对“家具组作为点”的修正

EBK 的点是带坐标和响应值的观测单位。家具组可以作为点，但必须预先定义：代表位置（质心、锚点或功能中心）、响应量（连续场值或 group-level scalar）、空间 support/尺度、组内几何如何汇总、重叠组如何处理。EBK 可在这些点之间预测连续 spatial response，并输出预测不确定性；它不会从组点本身发现 `IfcGroup`、latent membership 或 relative order。Pan–Hu–Shen 的 MRF-PPM 则提供另一条路径：把家具组点放入已知空间图，直接对 partition/latent group 建模；这需要重复 response 或 covariates，不能直接替代单场景几何模型。

因此本轮把 EBK 纳入“空间 response 预测候选”，不纳入“家具分组/排序候选”。若以后比较 EBK、CAR/ICAR、GP 或 deterministic baseline，必须使用同一 group-point 定义、同一 response、同一尺度和独立 held-out synthetic scenes。

本轮证据增量已经完成。尚未选择 Bayesian 生产模型，尚未实现 Bayesian 代码；下一步是 owner 审查 Task 3c 的首要 estimand。

STOP FOR DESIGN REVIEW
