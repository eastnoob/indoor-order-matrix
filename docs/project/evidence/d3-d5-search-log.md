# D3–D5 检索日志

- 日期：2026-09-27（Europe/Berlin）
- 范围：IFC4/BIM 事实、几何算法正确性、软件接口/行为、外部心理感知实验；不执行 D6。
- 记录规则：每次查询都记录来源、目的、结果和下一步；失败检索也保留。搜索片段、摘要和 README 只用于定位，不能替代原文。
- 使用路径：项目已有 `paper-lookup`、`literature-review`、`citation-management`、`scientific-critical-thinking` 和 Nature academic search/citation 工作流；本次以官方网页、开放全文和本地锁定环境作可复核 fallback。未安装依赖。

## 查询记录

| ID | 查询/入口 | 目标与结果 | 原文状态/处理 |
|---|---|---|---|
| S-001 | `site:ifc43-docs.standards.buildingsmart.org IfcObjectPlacement IFC4` | 找到 IFC placement 线索；转向 IFC4 FINAL 页面核验 | 成功；仅 IFC4 FINAL 页面进入账本 |
| S-002 | `site:ifc43-docs.standards.buildingsmart.org IfcRelAssignsToGroup IFC4` | 找到 IfcGroup 关系线索 | 成功；用 IFC4 FINAL `IfcRelAssignsToGroup` 原文 |
| S-003 | `site:ifc43-docs.standards.buildingsmart.org IfcGrid IfcGridAxis IFC4` | 找到 IfcGrid/Axis 定义 | 成功；用 IFC4 FINAL 原文 |
| S-004 | `site:ifc43-docs.standards.buildingsmart.org IfcSpatialZone IfcCovering IfcSurfaceFeature IfcFurnishingElement IFC4` | 找到区域、覆盖层、表面特征和家具实体线索 | 成功；逐页转到 IFC4 FINAL 原文 |
| S-005 | `site:standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML IfcFurnishingElement` | 核验 FurnishingElement 弃用/泛化范围 | 成功；E-IFC-007 |
| S-006 | `site:standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML IfcSpatialZone` | 核验 SpatialZone 与 Zone 差异 | 成功；E-IFC-005 |
| S-007 | `site:standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML IfcSurfaceFeature` | 核验 surface feature 表达方式 | 成功；E-IFC-006 |
| S-008 | `site:standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML IfcCovering` | 核验 covering/flooring 语义 | 成功；E-IFC-006 |
| S-009 | `site:standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML "Clearance" IfcShapeRepresentation` | 核验 clearance 是否可作为可用区 | 成功；找到 IFC4 ADD2 TC1 概念模板；明确不等同人类 affordance |
| S-010 | `site:standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema "IfcFurniture"` | 核验家具实体和属性 | 成功；E-IFC-007 |
| S-011 | `BIM furniture affordance zone clearance IFC paper full text` | 寻找家具 affordance 的 IFC 原始研究 | 未找到可访问权威原文；结果为商业/泛化空间规划/二手页面；登记 E-GAP-001 |
| S-012 | `IFC BIM furniture space requirements clearance activity zone paper` | 寻找 activity/clearance zone 的 BIM 研究 | 部分命中但没有可核验 IFC 语义原文；失败检索，需负责人提供材料 |
| S-013 | `BIM model furniture usability zone human reach clearance research` | 寻找人体使用区实验 | 未找到同时满足 BIM、家具、原文全文和可复核定位的来源；不升级为证据 |
| S-014 | `IFC usable area zone furniture clearance` | 寻找 IFC usable-area/家具关系 | 仅找到 IfcSpatialZone/IfcZone 官方定义，未找到人类使用区规范；E-IFC-005、E-GAP-001 |
| S-015 | `spatial order regularity symmetry visual complexity operational definition study full text` | D3 术语与可操作化研究 | 命中 Katkov、Gartus & Leder；两篇全文可读但刺激不是家具 |
| S-016 | `visual complexity definition image features regularity symmetry human perception open access` | 复杂度/对称性实验 | 命中 Gartus & Leder PLOS 全文；记录 E-PER-002，禁止心理效度迁移 |
| S-017 | `Gestalt visual continuity operational definition grouping symmetry review full text` | 连续性/分组原文 | 命中 PMC/Frontiers 条目；关键 PMC 页面 reCAPTCHA，未以片段作证据；E-PER-005 |
| S-018 | `layout order regularity spatial arrangement metric paper open access` | 布局秩序指标 | 命中点模式与图像研究，但没有家具布局验证；逐条降级为摘要或工程候选 |
| S-019 | `good continuation visual grouping empirical study Frontiers full text` | 连续性实验全文 | 结果偏视觉刺激/图像导引；没有家具/BIM 场景，未用于切片 |
| S-020 | `visual grouping proximity similarity continuity symmetry open access journal` | Gestalt 术语复核 | 多为综述或观点；关键原文访问受限，登记 E-PER-005 |
| S-021 | `spatial regularity metric point pattern original research open access` | 点模式规则性原始论文 | 找到 van Lieshout & Baddeley DOI；后续 ScanSci 以 OpenAlexOA 下载并人工检查全文，更新 E-PER-004 |
| S-022 | `official SciPy ConvexHull documentation Qhull degeneracy coplanar points` | 算法正确性和退化 | SciPy 官方文档全文可读；E-GEO-001 |
| S-023 | `official scikit-learn PCA documentation SVD principal components` | 主方向定义 | scikit-learn 官方文档全文可读；E-GEO-002 |
| S-024 | `official Shapely buffer distance documentation geometry predicates intersects` | 几何谓词 | Shapely 2.1.2 官方 API 可读；E-GEO-003 |
| S-025 | `official NetworkX shortest path documentation Dijkstra` | 图路径 | NetworkX 官方 API 可读；E-GEO-004 |
| S-026 | `IfcOpenShell official documentation geometry settings version 0.8` | 软件版本/几何设置 | IfcOpenShell 0.8.5 官方文档可读；E-SW-001 |
| S-027 | `IfcOpenShell Python API file by_type official docs` | 实体枚举/接口 | 官方 Python 文档可定位 API；本研究只记录 geometry settings/tree，避免无关接口断言 |
| S-028 | `Bonsai BIM Open IFC Project official documentation` | IFC 项目源与 blend 行为 | Bonsai 0.8.5 官方文档可读；E-SW-003 |
| S-029 | `Blender 5.2 LTS release notes official` | 版本/支持周期 | 官方发布页返回 HTTP 402；未用页面片段作版本证据；改用便携版本地 `--version` 观察，E-SW-004 |
| S-030 | `Protonotarios 2014 absolute interval scale order point patterns full text` | 点模式秩序原文 | DOI/出版商与 Europe PMC 全文请求失败；仅摘要，E-PER-003 |
| S-031 | `Europe PMC fullTextXML 10.1098/rsif.2014.0342` | 直接获取 XML | 返回 500/无 body；失败已记录，不把元数据当原文 |
| S-032 | `PMC visual complexity affect full text` | 视觉复杂度补充实验 | PMC 入口 reCAPTCHA；未纳入证据 |
| S-033 | `PMC4593740 Bayesian hierarchical grouping full text` | 良好延续分组实验 | PMC 入口 reCAPTCHA；未纳入证据 |
| S-034 | `site:arxiv.org 2609.00065 Scientific Agent Skills` | 核验引用管理技能出处 | arXiv v2 页面全文元数据可读；仅作为研究流程出处，不计入领域证据 |

| S-037 | Consensus：`BIM furniture affordance zone clearance space planning` | 寻找家具 affordance/clearance 直接研究 | 找到规则检查、空间规划、动作空间和通用设计候选；均需逐条核验 DOI/全文 |
| S-038 | Consensus：`IfcSpace activities topological requirements closeness accessibility minimum required area BIM nursing home` | 寻找 IfcSpace 活动/拓扑扩展 | 找到 Chaabane et al. 2023，DOI 10.1007/978-3-031-25182-5_47；摘要可读，全文 ScanSci 失败 |
| S-039 | Consensus：`"Simulation of Universal Design by a Functional Design Method"` | 寻找动作空间 IFC 原文 | 找到 Selin & Rossi 2016 DOI 10.15439/2016F306；ScanSci 成功下载并人工阅读 |
| S-040 | Consensus：`"The functional design method for buildings" gamification BIM` | 追踪动作空间/IFC 工程先例 | 找到 Selin & Rossi 2018 DOI 10.15439/2018F162；ScanSci 成功下载并人工阅读 |
| S-041 | buildingSMART IFC4 FINAL：`Pset_SpaceOccupancyRequirements`、`IfcSpace` | 核验原生活动/占用 schema | 官方全文可读；存在 OccupancyType、OccupancyNumber、AreaPerOccupant、MinimumHeadroom；未发现家具 affordance/clearance 实体 |
| S-042 | Consensus：`"Rule-based compliance checking and generative design for building interiors using BIM"` | 规则语言/室内合规 | DOI 10.1016/j.autcon.2020.103368，摘要可读，ScanSci 未找到 PDF |
| S-043 | Consensus：`"Application of Universal Design in the Design of Apartment Kitchens"` | 清空地面/触及/膝部空间 | DOI 10.3130/jaabe.15.403，摘要可读，ScanSci 未找到 PDF |
| S-044 | Consensus：`"Design for maintenance accessibility using BIM tools"` | 维护可达性与规则集 | DOI 10.1108/f-09-2011-0078，摘要可读，ScanSci 未找到 PDF |
| S-045 | 负责人提供本地原文：`C:\Users\tianf\Downloads\protonotarios2014.pdf` | 补齐 Protonotarios 2014 点模式秩序论文全文 | `pdfinfo`：13 页、未加密；SHA256 `0040AC70F9582666F283604A5602F8C60B858AA775EBDCC28C9F0587F870DF84`；`pdftotext -layout` 后逐节核对 §§2.1–2.2、§§3.1–3.2、§4。状态 `full_text_verified`，更新 E-PER-003 |
| S-046 | 负责人提供本地原文：`C:\Users\tianf\Downloads\wagemans2012.pdf` | 补齐 Wagemans 2012 Gestalt 综述全文 | `pdfinfo`：47 页、未加密；SHA256 `B3ACA166C0EDF76C0877FE6D4CD21BA72D081F6AE14F4C78FAD837A0F3B72043`；`pdftotext -layout` 后逐节核对 Abstract、§3、§3.3、§7.3。状态 `full_text_verified`，更新 E-PER-005 |

## 访问失败与补救

- PMC/Europe PMC：reCAPTCHA 或 500；处理为 `inaccessible`/`abstract_only`，不引用搜索片段。
- Protonotarios 出版商/PMC：原先的全文检索失败仍保留在 S-030/S-031；本轮负责人提供 PDF 后完成全文核验，E-PER-003 已从 `abstract_only` 升为 `full_text_verified`。van Lieshout 原文已由 ScanSci OpenAlexOA 下载并检查。
- 负责人提供的 Protonotarios 与 Wagemans PDF 已通过页数、未加密状态、SHA256 和 `pdftotext` 全文核对；本地 PDF 是本轮的原文访问来源，不把早先的搜索片段或失败状态当作当前证据。
- Chaabane 2023 Springer chapter、Sydora 2020、Kang 2016、Liu 2014：均找到 DOI，但本轮 ScanSci legal_only 未取得 PDF；保持 abstract_only。
- Blender 官方发布页：HTTP 402；只保留本机指定便携版版本观察。
- 未找到直接 IFC 家具 affordance zone 原文：不把项目假设升级为 IFC 事实，列入负责人材料清单。

## 可复核入口

- IFC4 官方实体页面：见账本 E-IFC-001 至 E-IFC-008。
- 算法官方文档：见 E-GEO-001 至 E-GEO-004。
- 软件官方文档：见 E-SW-001 至 E-SW-004。
- 全文感知论文：见 E-PER-001 至 E-PER-005（其中 E-PER-003、E-PER-005 为负责人提供 PDF 后核验）。
- 摘要/不可访问论文：见 E-BIM-003、E-BIM-006 至 E-BIM-008，以及 E-GAP-001；PMC4593740 仍不可访问。

| S-035 | ScanSci `legal_only` 下载：`10.1111/j.1467-9574.1996.tb01501.x`、`10.3389/fpsyg.2015.00734`、`10.1371/journal.pone.0185276` | 验证可访问原文 | 3 篇成功；van Lieshout、Katkov、Gartus PDF+Markdown 写入 `C:\Users\tianf\Downloads\d3-d5-evidence-papers`；Protonotarios `10.1098/rsif.2014.0342` 失败（无 PDF/Cloudflare，Unpaywall 邮箱配置缺失） |
| S-036 | ScanSci `legal_only` 下载：`10.1037/a0029333` | Gestalt 综述全文 | 失败：Cloudflare；不安装 CloakBrowser、不配置代理、不启用灰色源 |
