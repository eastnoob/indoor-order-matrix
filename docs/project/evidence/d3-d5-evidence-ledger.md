# D3–D5 证据账本

- 研究日期：2026-09-27
- 研究范围：D3 术语与候选描述子、D4 IFC4/几何语义、D5 软件行为与外部感知实验。
- 明确排除：D6 实现、生产代码、依赖安装、IFC 修复、Bonsai 导入执行、心理效度验证。
- 证据等级：`full_text_verified`（原文全文可读）、`official_doc_verified`（官方文档可读）、`abstract_only`（仅摘要/元数据）、`inaccessible`（原文无法取得）、`conflicting`（来源互相冲突）。摘要、搜索片段、README、项目记忆不作为原文证据。
- 分类：`IFC_SCHEMA`、`BIM_INTEROP`、`GEOMETRY_ALGORITHM`、`SOFTWARE`、`PERCEPTION_EMPIRICAL`、`ENGINEERING_INFERENCE`。

## 判定规则

1. IFC4 FINAL/ADD2_TC1 是本账本的 IFC 主版本；IFC4X3 页面只用于检索线索，不支撑 IFC4 字段断言。
2. IFC 实体、属性、关系和几何表示是 IFC/BIM 事实；坐标投影、指标公式、阈值、缺失策略和推荐切片是本项目工程推断。
3. 感知论文只说明外部实验如何操作秩序、对称性或复杂度，不证明家具布局的心理效度，也不提供本项目验收阈值。
4. `undefined/not_available` 是几何退化或来源缺失的保真状态；不得把它转成零分。

## D3 术语与描述子边界

| 术语 | 可操作候选 | 所需输入/不变量 | 证据边界 |
|---|---|---|---|
| order（秩序） | 相对位置、方向或重复关系的偏差摘要；需显式轴与容差 | 世界坐标、分析平面、容差 | 本项目工程名称；外部感知研究不能给出家具验收阈值 |
| regularity（规则性） | 最近邻距离/间距或网格偏差的离散度 | 尺度归一化、缺失策略 | 点模式文献仅摘要可得；不直接证明家具规则性 |
| symmetry（对称性） | 对反射/旋转/平移变换的几何残差 | 变换中心、坐标系、容差 | 几何候选；感知实验使用合成图案 |
| repetition（重复） | 形状/属性/间距签名的重复率 | 语义签名、顺序、容差 | 未找到 IFC 家具的直接验证研究 |
| clustering（聚集） | 距离图或点模式交互统计 | 距离尺度、边界校正 | J-function 原论文仅摘要可得 |
| visual complexity（视觉复杂度） | 仅作为外部感知背景 | 图像刺激与观察者实验 | 不用于本项目验收，也不转成家具复杂度分数 |
| continuity（连续性） | 仅作为视觉分组背景 | 轮廓/邻近刺激 | 未获得可支撑家具边界的原文 |
| relative-order | 推荐首个工程描述子：投影序列的单调性/逆序或间距偏差 | 明确分析轴、世界坐标、tolerance | 不是心理构念；需在 D8–D10 验证可重复性 |
| authored-group local trend | 推荐工程描述子：同一 IfcGroup 内质量中心/方向的局部趋势 | IfcRelAssignsToGroup、MassPatch、PCA/方向、缺失策略 | 不代表感知“整体性” |

## 证据记录

### E-IFC-001
- date：2026-09-27
- question：IfcLocalPlacement 如何定义产品坐标与相对放置？
- claim：IfcLocalPlacement 可相对另一个对象放置；省略父放置时为绝对放置；产品几何位于其对象坐标系。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — IfcLocalPlacement
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[IfcLocalPlacement](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifclocalplacement.htm)，实体定义、属性 `PlacementRelTo`、`RelativePlacement`
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：局部放置由相对父放置与相对坐标构成；没有父放置时在工程坐标中解释。
- supports：D4 世界坐标链、相对顺序和方向计算必须先展开放置链。
- does_not_support：不支持任何“家具朝向具有感知意义”的结论。
- confidence：high
- limitations：只定义放置语义；父链循环、无效矩阵和单位异常仍需工程处理。
- follow_up：D6 接口必须保留来源 GlobalId、放置链和单位。

### E-IFC-002
- date：2026-09-27
- question：IfcProductDefinitionShape 表示什么？
- claim：产品可有多个表示上下文；几何表示在对象坐标系中，需由产品放置变换到工程坐标。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — IfcProductDefinitionShape
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[IfcProductDefinitionShape](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcrepresentationresource/lexical/ifcproductdefinitionshape.htm)，实体定义与 `Representations`
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：一个产品定义形状可关联多个形状表示；表示属于产品对象坐标。
- supports：D4 选择 Body/Plan 等表示并记录上下文；几何指标用世界空间计算。
- does_not_support：不支持把任意表示当作人类活动区或心理边界。
- confidence：high
- limitations：不规定应用选择哪个 representation，也不保证表示可网格化。
- follow_up：需在 D6 明确优先 Body/Plan 及无表示时的状态。

### E-IFC-003
- date：2026-09-27
- question：IfcGrid/IfcGridAxis 的语义是什么？
- claim：IfcGrid 是有 U/V/W 轴集合的 IfcProduct；IfcGridAxis 是 XY 平面的二维曲线轴并可有标签。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — IfcGrid、IfcGridAxis
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[IfcGrid](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcgrid.htm)；[IfcGridAxis](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcgridaxis.htm)，属性 `UAxes/VAxes/WAxes`、`AxisTag/AxisCurve`
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：网格轴是工程对象的一部分，轴曲线位于网格 XY 平面。
- supports：网格作为已作者化参考系；D4 可把轴投影到分析平面。
- does_not_support：不支持从网格轴推断家具规则性或使用路径。
- confidence：high
- limitations：轴曲线是参考几何；未规定家具与轴的关联或容差。
- follow_up：若使用网格趋势，保留轴标签与曲线来源。

### E-IFC-004
- date：2026-09-27
- question：IfcRelAssignsToGroup 是否表达家具群组？
- claim：关系可把对象定义分配到 IfcGroup；对象可以属于零、一个或多个组，分组不是层级树。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — IfcRelAssignsToGroup
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[IfcRelAssignsToGroup](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcrelassignstogroup.htm)，实体定义、`RelatedObjects/RelatingGroup`
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：关系用于任意对象定义的组分配，可递归但不强制层次。
- supports：把作者化组与推断组区分；局部趋势应按显式组计算。
- does_not_support：组成员关系不等于空间相邻、活动区或感知整体性。
- confidence：high
- limitations：组是多对多关系；成员重复、循环和语义用途需项目策略。
- follow_up：记录组来源和多组成员情况，避免重复计数。

### E-IFC-005
- date：2026-09-27
- question：IfcSpatialZone 与 IfcZone 是否可承载空间区域几何？
- claim：IfcSpatialZone 是可重叠、非层级的功能空间对象并可有独立形状；IfcZone 是空间分组且没有自身几何/放置。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — IfcSpatialZone、IfcZone
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[IfcSpatialZone](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcspatialzone.htm)；[IfcZone](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifczone.htm)
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：SpatialZone 可表达热、照明、可用面积等功能区域；Zone 仅用于聚合空间。
- supports：候选区域事实必须指向明确实体和几何来源。
- does_not_support：不能把任意 IfcZone 或未作者化推断区写成 IFC 事实。
- confidence：high
- limitations：实体语义不保证区域几何存在或代表人的活动范围。
- follow_up：D6 需区分 authored zone、derived region 与 missing。

### E-IFC-006
- date：2026-09-27
- question：IfcCovering 与 IfcSurfaceFeature 能否表示地面或表面字段？
- claim：IfcCovering 覆盖其他元素，示例包括地板；IfcSurfaceFeature 修改表面，可有二维框、几何集或表面表示。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — IfcCovering、IfcSurfaceFeature
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[IfcCovering](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcsharedbldgelements/lexical/ifccovering.htm)；[IfcSurfaceFeature](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcstructuralelementsdomain/lexical/ifcsurfacefeature.htm)
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：两者描述建模的覆盖层或表面特征，不定义“视觉边界”或“活动区”。
- supports：地面/表面来源可作为边界候选的原始 IFC 输入。
- does_not_support：不支持从材质或表面特征直接推断人的行为边界。
- confidence：high
- limitations：覆盖层/表面特征不包含行为、视觉或心理边界解释。
- follow_up：把边界证据的实体类型和表示上下文写入 provenance。

### E-IFC-007
- date：2026-09-27
- question：IfcFurniture/IfcFurnishingElement 的范围？
- claim：IfcFurniture 表示桌、椅、柜等完整家具；IfcFurnishingElement 是泛化实体且在 IFC4 后不宜直接实例化。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — IfcFurniture、IfcFurnishingElement
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[IfcFurniture](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcsharedfacilitieselements/lexical/ifcfurniture.htm)；[IfcFurnishingElement](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcfurnishingelement.htm)
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：家具实体继承产品放置和几何表示；内置家具可用连接关系表达。
- supports：家具对象发现、类型标签和几何抽取。
- does_not_support：实体类型不保证真实可用性、用途或活动空间。
- confidence：high
- limitations：类型与几何不保证实际使用方式、尺寸完整性或可移动性。
- follow_up：D6 记录实体类型与 PredefinedType，缺失时保留 unknown。

### E-IFC-008
- date：2026-09-27
- question：IFC Clearance 是否等于人的活动/可用区？
- claim：IFC4 Clearance geometry 是要求围绕元素的空间表示，原因可为通风、维护等；其通用模板不定义人的家具使用区。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 ADD2 TC1 — Clearance Geometry
- version/year：IFC4 ADD2 TC1（访问 2026-09-27）
- locator：[Clearance Geometry](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/schema/templates/clearance-geometry.htm)，概念模板、RepresentationIdentifier `Clearance`
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：Clearance 表示与 Body 不相交的周边空间，可用于维护/通风等约束。
- supports：D4 将 clearance 当作约束几何来源，并标注原因/来源。
- does_not_support：不支持“人类行为可用区”或心理边界的断言。
- confidence：high
- limitations：Clearance 原因可为维护/通风；没有人因尺寸或感知证据。
- follow_up：项目负责人需确认家具 Clearance 是否允许进入 Stage1 合同，或统一使用 OM_ authored affordance schema。

### E-GEO-001
- date：2026-09-27
- question：凸包算法的退化行为是什么？
- claim：SciPy ConvexHull 在 2D 返回逆时针顶点；共面点可能进入 coplanar 集合；退化输入可抛 QhullError。
- evidence_class：GEOMETRY_ALGORITHM
- source：SciPy API reference — ConvexHull
- version/year：SciPy docs v1.18.0（访问 2026-09-27）
- locator：[ConvexHull](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.ConvexHull.html)，`vertices`、`coplanar`、`QhullError`、`area/volume`
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：输入是点集；维数不足或数值退化可能失败；面积/体积取决于维数。
- supports：质量中心/边界候选可用凸包，但必须显式处理空、单点、共线和退化。
- does_not_support：凸包不能保留凹陷，也不代表家具可用边界。
- confidence：high
- limitations：结果受 Qhull 数值精度与点集质量影响，凸包丢失凹陷。
- follow_up：D6 输出 `geometry_status` 和失败原因，禁止静默变零。

### E-GEO-002
- date：2026-09-27
- question：PCA 可否直接作为主方向？
- claim：PCA 求最大方差的正交分量并在计算前中心化，不做尺度标准化；各向同性或近方形数据的主方向不稳定。
- evidence_class：GEOMETRY_ALGORITHM
- source：scikit-learn decomposition documentation
- version/year：scikit-learn stable docs（访问 2026-09-27）
- locator：[PCA](https://sklearn.org/stable/modules/decomposition.html)，PCA 定义与中心化说明
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：主成分是方差最大的正交方向；输入中心化但不自动缩放。
- supports：可为 MassPatch/家具方向提供候选轴。
- does_not_support：PCA 方向不自动等于 IFC 朝向、设计轴或感知主轴。
- confidence：high
- limitations：PCA 对各向同性、方形和样本不足不稳定，且不处理语义方向。
- follow_up：对圆、正方形、低面积或单点输出 undefined，并保留旋转符号约定。

### E-GEO-003
- date：2026-09-27
- question：距离、交集、清除量等几何谓词的语义？
- claim：Shapely 提供 distance、minimum_clearance、intersects、overlaps、difference、intersection 等几何操作；这些是平面几何谓词。
- evidence_class：GEOMETRY_ALGORITHM
- source：Shapely 2.1.2 API reference
- version/year：Shapely 2.1.2（访问 2026-09-27）
- locator：[Shapely reference](https://shapely.readthedocs.io/en/stable/_reference.html)，对应函数条目
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：谓词按几何对象关系返回布尔量或距离/几何结果。
- supports：D4 清除、重叠和边界计算的实现候选。
- does_not_support：不定义 IFC 语义、单位换算或人的可通过性。
- confidence：high
- limitations：API 不替项目选择平面、容差、单位或无效几何修复方式。
- follow_up：先在世界坐标和统一单位计算，再应用项目阈值。

### E-GEO-004
- date：2026-09-27
- question：NetworkX 最短路径的保证范围？
- claim：shortest_path/Dijkstra 在给定图和边权下求最短路径；默认边权为 1，负权不适用 Dijkstra。
- evidence_class：GEOMETRY_ALGORITHM
- source：NetworkX stable/latest reference
- version/year：NetworkX docs 3.7.1rc0.dev0（访问 2026-09-27）
- locator：[shortest_path](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.generic.shortest_path.html)；[Dijkstra](https://networkx.org/documentation/latest/reference/algorithms/shortest_paths/dijkstra.html)
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：算法只对输入图、权重和方向求路径，不生成空间图。
- supports：若项目先定义可通行图，可用于路径长度/连通性。
- does_not_support：不证明图节点是房间、家具或人的活动点。
- confidence：high
- limitations：路径正确性只针对给定图和权重；图域构造完全由项目负责。
- follow_up：D6 需保存 graph_domain、节点来源和权重定义。

### E-SW-001
- date：2026-09-27
- question：IfcOpenShell 几何设置如何影响提取？
- claim：IfcOpenShell 0.8.5 支持上下文/目标表示、单位转换、开口扣除和网格容差；布尔运算有性能/健壮性权衡。
- evidence_class：SOFTWARE
- source：IfcOpenShell 0.8.5 official docs — geometry settings
- version/year：0.8.5（访问 2026-09-27）
- locator：[geometry settings](https://docs.ifcopenshell.org/ifcopenshell/geometry_settings)，representation、`convert-back-units`、openings、tolerance、kernels 小节
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：几何上下文决定提取目标；内部以米处理，可恢复 IFC 单位；开口扣除可能更慢或失败。
- supports：D5 adapter 需记录设置、单位和失败状态。
- does_not_support：文档不保证每个第三方 IFC 都能成功网格化，也不保证语义分区。
- confidence：high
- limitations：文档描述设置，不保证所有 IFC、布尔运算或第三方几何成功。
- follow_up：首个切片固定版本与 settings，并把失败留在证据账本。

### E-SW-002
- date：2026-09-27
- question：IfcOpenShell geometry tree 能否支持碰撞/清除？
- claim：geometry tree 使用 BVH/UB tree 进行包围盒或精确几何查询；包围盒更快但不精确。
- evidence_class：SOFTWARE
- source：IfcOpenShell Python docs — geometry tree
- version/year：0.8.5（访问 2026-09-27）
- locator：[geometry tree](https://docs.ifcopenshell.org/ifcopenshell-python/geometry_tree.html)，tree construction、intersection、collision、clash/clearance
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：查询可在包围盒层或精确几何层进行，速度与精度有取舍。
- supports：D4 记录检测层级，先粗筛再精算。
- does_not_support：不定义项目阈值或活动区语义。
- confidence：high
- limitations：包围盒查询可能误报/漏报精确相交，精确查询有成本。
- follow_up：报告需注明 bbox-only 与 exact 的差异。

### E-SW-003
- date：2026-09-27
- question：Bonsai 的 IFC 项目打开行为？
- claim：Bonsai 0.8.5 文档说明 `File > Open IFC Project` 以 IFC 为关键源；单独打开 blend 不会加载 IFC 项目。
- evidence_class：SOFTWARE
- source：Bonsai official docs — Starting a new project
- version/year：Bonsai 0.8.5 docs（访问 2026-09-27）
- locator：[Starting a new project](https://docs.bonsaibim.org/guides/authoring/starting_new_project.html)，Open IFC Project 与 IFC/blend 关系小节
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：IFC 文件是项目源，blend 是配套保存；两者保存流程分开。
- supports：D5 记录 UI/项目源假设，并把 live import 作为待验证门槛。
- does_not_support：不证明本机 Bonsai UI 的具体版本行为、导入成功或分析器兼容性。
- confidence：high
- limitations：文档行为不等于本机版本和项目 fixture 的 live UI 验证。
- follow_up：项目负责人决定是否把 live Bonsai gate 推迟到后续阶段。

### E-SW-004
- date：2026-09-27
- question：本机软件版本是否可复现？
- claim：在项目锁定 Pixi 环境中观察到 ifcopenshell 0.8.5、Shapely 2.1.2、NumPy 2.4.3；指定便携 Blender 为 5.2.0 LTS。
- evidence_class：SOFTWARE
- source：本仓库 `pixi.toml` 与受控本机版本命令输出
- version/year：观察日期 2026-09-27；Blender build 2026-07-14
- locator：`D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe --version`；`pixi run python` 版本输出；官方 Blender 页面返回 402
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：版本输出可复现；Blender 官方发布页无法通过当前访问路径读取。
- supports：研究环境和版本记录。
- does_not_support：不支持 Bonsai 导入成功或任何生产性能结论。
- confidence：medium
- limitations：本地观察不是发布页证明，也不覆盖 Bonsai、显卡或性能。
- follow_up：保留本地命令输出；不把 402 页面当成版本原文。

### E-PER-001
- date：2026-09-27
- question：外部实验如何测量视觉秩序/对称性？
- claim：Katkov 等在合成纹理上以 4AFC 和参数化随机场研究秩序/对称性，观察者对局部与全局规律敏感。
- evidence_class：PERCEPTION_EMPIRICAL
- source：Katkov, Harris & Sagi, “Visual perception of order-disorder transition”
- version/year：Frontiers in Psychology 2015, DOI 10.3389/fpsyg.2015.00734
- locator：[全文](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.00734/full)，Abstract、Materials and Methods、Discussion
- access_status：full_text_verified
- short_excerpt_or_paraphrase：实验刺激是 32×32 Gaussian blobs 的合成纹理，任务是 4AFC，不是家具布局。
- supports：秩序/对称性可在外部感知实验中被操作和测量。
- does_not_support：不支持家具布局描述子、阈值或本项目心理效度。
- confidence：high
- limitations：合成纹理、4AFC 与观察者任务和家具布局不同，不能迁移阈值。
- follow_up：仅作为外部背景，不进入 D8–D10 验收。

### E-PER-002
- date：2026-09-27
- question：镜像对称与视觉复杂度的关系是否有实验？
- claim：Gartus & Leder 对抽象黑白图案收集复杂度评分，镜像对称与其他图像指标可预测部分评分；作者明确提出向建筑图像推广仍是未来工作。
- evidence_class：PERCEPTION_EMPIRICAL
- source：Gartus & Leder, “Predicting perceived visual complexity of abstract patterns…”
- version/year：PLOS ONE 2017, 12:e0185276, DOI 10.1371/journal.pone.0185276
- locator：[全文](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0185276)，Study 1/2、Discussion、Limitations
- access_status：full_text_verified
- short_excerpt_or_paraphrase：实验使用 912/252 抽象图案和 29–64 名参与者，模型解释率依刺激集变化。
- supports：感知复杂度与对称性/图像统计可有经验关联。
- does_not_support：不支持家具、BIM、空间可用性或本项目验收效度。
- confidence：high
- limitations：抽象黑白图案和评分任务限制了建筑/家具外推。
- follow_up：不得把视觉复杂度作为 D8–D10 的心理分数。

### E-PER-003
- date：2026-09-27
- question：点模式秩序是否有原始量表？
- claim：Protonotarios 等通过成对排序建立点模式秩序的 Bradley–Terry 间隔量表，以 Poisson 与 Bravais lattice 为锚点；Delaunay 三角形熵（DTE）在该点模式刺激族上最接近观察者量表。
- evidence_class：PERCEPTION_EMPIRICAL
- source：Protonotarios et al., “An absolute interval scale of order for point patterns”
- version/year：Journal of the Royal Society Interface 2014, DOI 10.1098/rsif.2014.0342
- locator：[DOI](https://doi.org/10.1098/rsif.2014.0342)；负责人提供原文 `C:\Users\tianf\Downloads\protonotarios2014.pdf`（13 页，SHA256 `0040AC70F9582666F283604A5602F8C60B858AA775EBDCC28C9F0587F870DF84`）；§§2.1–2.2、§§3.1–3.2、§4，PDF pp. 3–8；文本核对 `protonotarios2014.txt` lines 190–220, 300–350, 403–451, 524–606
- access_status：full_text_verified
- short_excerpt_or_paraphrase：20 名参与者对 20 个点模式进行成对排序；模式来自晶格抖动、仿射拉伸、增删点和非线性变形。观察者量表约 9.86 jnds；DTE 的交叉验证误差约 0.49 jnd，锚点为 Poisson=0、完美晶格=10。
- supports：点模式秩序可在特定合成刺激族中被心理物理量表化；DTE 可作为该刺激族的算法候选。
- does_not_support：不支持家具布局、BIM、清除/可用区、通用算法正确性或本项目心理效度。
- confidence：high（限于论文自身的点模式范围）
- limitations：刺激是二维点模式而非家具/室内场景；观察任务、量表锚点和 DTE 参数都不能直接迁移到本项目；论文中的 Drosophila 应用也不是布局验证。
- follow_up：仅保留为外部感知背景；D8–D10 不采用 DTE 或其 jnd 数值，除非另有家具刺激实验。

### E-PER-004
- date：2026-09-27
- question：空间规则性统计 J-function 是否可直接作为项目指标？
- claim：van Lieshout & Baddeley 定义 J(r)=(1-G(r))/(1-F(r))；Poisson 时 J=1，J<1 表示聚集，J>1 表示规则/抑制，并讨论边界校正估计。
- evidence_class：PERCEPTION_EMPIRICAL
- source：van Lieshout & Baddeley, “A nonparametric measure of spatial interaction in point patterns”
- version/year：Statistica Neerlandica 1996, DOI 10.1111/j.1467-9574.1996.tb01501.x
- locator：[DOI](https://doi.org/10.1111/j.1467-9574.1996.tb01501.x)；ScanSci 下载全文 `C:\Users\tianf\Downloads\d3-d5-evidence-papers\vanLieshout1996_Nonparametric.pdf` / `.md`，§1、Definition 1、§5.1、§6
- access_status：full_text_verified
- short_excerpt_or_paraphrase：全文给出 J 的定义、Poisson/聚集/规则解释、F/G 的边界校正估计，并警告不规则窗口与高维边界效应。
- supports：规则/聚集术语的点模式统计定义、估计方法和边界效应。
- does_not_support：不支持有限房间边界、家具语义、观察者效度或本项目阈值。
- confidence：low
- limitations：研究对象是平稳点过程和点模式；有限室内边界、家具语义、非平稳布局和心理效度仍未验证。
- follow_up：不得在 D8–D10 直接采用 J-function；若未来研究需用，必须先定义有限房间边界校正。

### E-PER-005
- date：2026-09-27
- question：Gestalt 连续性能否证明家具边界？
- claim：Wagemans 等综述系统讨论邻近、相似、共同命运、良好延续、闭合、对称和图形–背景组织，并明确指出线索交互、任务/刺激依赖和跨范式推广仍有限。
- evidence_class：PERCEPTION_EMPIRICAL
- source：Wagemans et al., “A Century of Gestalt Psychology in Visual Perception: I. Perceptual Grouping and Figure-Ground Organization”
- version/year：Psychological Bulletin 2012, 138, 1172–1217, DOI 10.1037/a0029333
- locator：[DOI](https://doi.org/10.1037/a0029333)；负责人提供原文 `C:\Users\tianf\Downloads\wagemans2012.pdf`（47 页，SHA256 `B3ACA166C0EDF76C0877FE6D4CD21BA72D081F6AE14F4C78FAD837A0F3B72043`）；Abstract、§3 “Perceptual Grouping”、§3.3 contour integration、§7.3 limitations/conclusion；文本核对 `wagemans2012.txt` lines 27–45, 560–603, 1083–1169, 2070–2180, 2221–2345
- access_status：full_text_verified
- short_excerpt_or_paraphrase：综述把 proximity、similarity、good continuation、closure、symmetry 等作为视觉分组线索，并指出不同任务/刺激会改变线索作用；轮廓研究常用 Gabor snakes，不能直接等同真实家具边界。
- supports：视觉分组术语、外部实验背景以及“不要把线索或效应跨刺激直接迁移”的批判性边界。
- does_not_support：不支持家具 affordance/clearance、IFC schema、几何算法正确性或本项目心理效度。
- confidence：high（限于综述所覆盖的视觉知觉文献）
- limitations：综述对象是视觉刺激与图形–背景组织，不是建筑布局；PMC4593740 仍未取得全文，不能把该条目与本综述混为已核验证据。
- follow_up：保留为外部感知背景；若后续需要 PMC4593740 的具体实验，负责人仍需提供该原文或作者稿。

### E-GAP-001
- date：2026-09-27
- question：是否存在可直接支撑“BIM 家具 affordance zone”的 IFC 原文？
- claim：多轮检索未找到可访问且权威的 IFC 语义原文；结果多为通用空间规划、商业软件或二手摘要。
- evidence_class：BIM_INTEROP
- source：检索集合（见 search log）
- version/year：截至 2026-09-27
- locator：[search log](./d3-d5-search-log.md)，BIM affordance/clearance 查询组
- access_status：inaccessible
- short_excerpt_or_paraphrase：没有把搜索结果片段升级为证据记录。
- supports：将 affordance zone 暂定为 authored/derived 工程层，等待负责人材料。
- does_not_support：不支持把 affordance zone 写成 IFC 原生事实。
- confidence：high
- limitations：缺少可引用原文，检索空缺不能证明文献不存在。
- follow_up：负责人提供论文 DOI/全文、企业 schema 或确认采用 OM_ 扩展。

### E-INF-001
- date：2026-09-27
- question：D8–D10 应先验证哪一个窄切片？
- claim：推荐“几何/相对顺序 + 作者化组局部趋势”，输入限于 IFC4 放置/Body 几何、IfcRelAssignsToGroup 和世界空间 MassPatch；不含推断组、边界、通道、感知校准或 UI。
- evidence_class：ENGINEERING_INFERENCE
- source：本项目架构记忆、Phase 0 决策与本账本事实的综合推断
- version/year：项目材料版本 2026-09-27
- locator：[架构记忆](../../indoor_layout_evaluation_matrix_architecture_memory.md)、[Phase 0 decisions](phase-0-user-decisions.md)、E-IFC-001/002/004、E-GEO-001/002、E-SW-001
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：上游事实可追溯，指标定义和容差仍是工程选择。
- supports：可形成可重复的最小验证闭环。
- does_not_support：不声称该切片具有心理感知效度。
- confidence：medium
- limitations：这是项目选择而非外部验证；方向、阈值和 fixture 仍待负责人确认。
- follow_up：负责人确认轴、容差、方向退化和真实 fixture 后再进入 D6。

### E-INF-002
- date：2026-09-27
- question：哪些状态必须显式传递到 adapter？
- claim：D6 合同至少需要 GlobalId/entity/type、IfcObjectPlacement 链、representation/context/unit、组关系、分析平面、source/provenance 与 geometry_status。
- evidence_class：ENGINEERING_INFERENCE
- source：D3–D5 综合与项目架构约束
- version/year：2026-09-27
- locator：本账本 E-IFC-001/002/004、E-GEO-001/002、E-SW-001/002；架构记忆的 neutral scene contract 小节
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：把 IFC 事实、几何结果和推断字段分层传递，避免缺失变零。
- supports：D6 未来接口设计的最小字段清单。
- does_not_support：不实现或批准 D6。
- confidence：medium
- limitations：字段清单是接口推断，不代表已经实现或已通过 fixture 测试。
- follow_up：等待负责人决定 OM_ 命名、缺失枚举与报告格式。

## 缺失/退化行为矩阵（工程约束候选）

| 操作 | 旋转 | 尺度/单位 | 缺失 | 退化 |
|---|---|---|---|---|
| 世界坐标投影 | 先展开 IFC 放置链；禁止直接用局部坐标 | 统一单位并记录换算 | 无 placement/representation → not_available | 非有限坐标 → invalid |
| bbox/凸包 | bbox 随方向变化；凸包保留外轮廓 | 面积/距离必须同单位 | 无点 → undefined | 单点/共线/QhullError → undefined + 原因 |
| PCA/方向 | 方向随坐标系变换；记录 sign 约定 | PCA 不自动缩放 | 点数不足 → undefined | 圆/方/各向同性 → unstable/undefined |
| distance/overlap/clearance | 在同一分析平面/坐标系 | 阈值带单位 | 任一几何缺失 → not_available | 无效多边形先报告 invalid，不静默修复 |
| path/graph | 方向只影响节点/边定义 | 权重需单位或无量纲声明 | 无图域 → not_applicable | 不连通 → no_path，不记为零 |


### E-BIM-001
- date：2026-09-27
- question：IFC4 是否有空间活动/占用需求的原生属性集？
- claim：Pset_SpaceOccupancyRequirements 可分配给 IfcSpace、IfcSpatialZone、IfcZone，包含 OccupancyType、OccupancyNumber、OccupancyTimePerDay、AreaPerOccupant 和 MinimumHeadroom 等属性。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — Pset_SpaceOccupancyRequirements
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[Pset_SpaceOccupancyRequirements](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/pset/pset_spaceoccupancyrequirements.htm)，§5.4.5.18，属性表
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：属性集描述空间结构元素中发生/预期发生的工作活动，并给出占用人数、单位面积和最低净空等需求。
- supports：活动/占用需求可以作为 IFC 空间属性事实记录。
- does_not_support：不是家具实例的 affordance 区，也不是通用 clearance 几何。
- confidence：high
- limitations：属性集没有定义家具周边操作多边形、人体姿态轨迹或感知边界。
- follow_up：D6 若需要活动需求，优先引用该属性集并另存派生几何 provenance。

### E-BIM-002
- date：2026-09-27
- question：IfcSpace 是否能承载功能空间和家具包含关系？
- claim：IfcSpace 表示为建筑功能提供面积/体积的空间；家具等产品可通过 IfcRelContainedInSpatialStructure 作为空间容器内容关联；IfcSpace 可使用 Pset_SpaceOccupancyRequirements。
- evidence_class：IFC_SCHEMA
- source：buildingSMART IFC4 FINAL — IfcSpace
- version/year：IFC4 FINAL（访问 2026-09-27）
- locator：[IfcSpace](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcspace.htm)，语义定义、Spatial Container、Property Sets for Objects、FootPrint/Body geometry
- access_status：official_doc_verified
- short_excerpt_or_paraphrase：IfcSpace 是空间结构和空间容器；其几何、放置和边界有独立约束。
- supports：空间级活动/占用事实、家具包含关系和空间几何抽取。
- does_not_support：不自动生成家具 affordance zone、操作空间或行为路径。
- confidence：high
- limitations：空间容器关系不等同家具使用关系；实现协议可能限制空间重叠和边界。
- follow_up：保持 `space_fact` 与 `derived_affordance_region` 两层。

### E-BIM-003
- date：2026-09-27
- question：是否有研究把活动/拓扑要求扩展到 IfcSpace？
- claim：Chaabane 等提出扩展 IfcSpace 以记录活动及 closeness、accessibility、minimum required area 等拓扑/安全要求，并在 Revit/Dynamo 中检查走道宽度、门宽、房间面积和最短距离。
- evidence_class：BIM_INTEROP
- source：Chaabane et al., “Building Information Model and Safety Requirements for Spatial Program Validation”
- version/year：2023，Book chapter，DOI 10.1007/978-3-031-25182-5_47
- locator：[DOI](https://doi.org/10.1007/978-3-031-25182-5_47)；Consensus record [paper](https://consensus.app/papers/details/b7068f1b2766526296b726307102f32b/?utm_source=chatgpt)
- access_status：abstract_only
- short_excerpt_or_paraphrase：摘要明确描述 IfcSpace 扩展、活动、接近性/可达性和最小面积要求；全文未取得。
- supports：直接提供“空间需求扩展层”的研究线索。
- does_not_support：不能证明该扩展属于 IFC4 标准，也不能核验属性名、数据类型或验证结果。
- confidence：medium
- limitations：仅摘要级；Springer PDF 的 ScanSci legal_only 下载失败。
- follow_up：若要采用，需项目负责人提供全文或作者稿。

### E-BIM-004
- date：2026-09-27
- question：人体动作空间能否被建成 IFC/3D 空间对象？
- claim：Selin & Rossi 的 Functional Design Method 从真实动作视频估计三维最大空间需求，生成 IFC 兼容的 3D 空间对象，并将其作为游戏 collider 检验动作是否适合设计空间。
- evidence_class：BIM_INTEROP
- source：Selin & Rossi, “Simulation of Universal Design by a Functional Design Method and by Gamification of Building Information Modeling”
- version/year：2016，FedCSIS，DOI 10.15439/2016F306
- locator：[DOI](https://doi.org/10.15439/2016F306)；[开放全文](https://annals-csis.org/proceedings/2016/pliks/306.pdf)；ScanSci PDF/Markdown：`C:\Users\tianf\Downloads\d3-d5-evidence-papers\Selin2016_Simulation.*`，Markdown §§I–III、§§C–D
- access_status：full_text_verified
- short_excerpt_or_paraphrase：方法用至少两个正交摄像机记录动作，在 x/y/z 中测量空间需求并生成 3D 对象；示例包括轮椅使用者和助手。
- supports：affordance/clearance 可作为项目派生几何，并保存动作、角色和测量 provenance。
- does_not_support：不证明该对象是 IFC 原生家具语义，也不提供普适人体阈值或心理效度。
- confidence：medium
- limitations：原型/试点方法，动作类型和测量精度有限；不是家具专用 schema。
- follow_up：可作为 `derived_action_space` 外部证据，不可命名为 IFC 原生 affordance。

### E-BIM-005
- date：2026-09-27
- question：IFC 几何、转换和动作空间是否在真实建筑试点中联用？
- claim：Selin & Rossi 2018 在超市疏散试点中使用 IFC 子模型、IfcConvert、XML 元数据和 Unity；按 avatar profile 放置描述动作空间的 colliders，并记录疏散结果。
- evidence_class：BIM_INTEROP
- source：Selin & Rossi, “The Functional Design Method for Buildings (FDM) with Gamification of Information Models and AI Help to Design Safer Buildings”
- version/year：2018，FedCSIS，DOI 10.15439/2018F162
- locator：[DOI](https://doi.org/10.15439/2018F162)；ScanSci PDF/Markdown：`C:\Users\tianf\Downloads\d3-d5-evidence-papers\Selin2018_Functional.*`，Markdown §§I–III、§§B–D
- access_status：full_text_verified
- short_excerpt_or_paraphrase：论文明确把 IFC 子模型转换为 OBJ/XML，在 Unity 中用带 profile 的 avatar collider 表示移动空间需求。
- supports：工程上可把动作空间作为与家具/墙体几何分离的派生层，并记录 adapter 转换链。
- does_not_support：不支持 Bonsai/IfcOpenShell 当前版本行为，也不证明碰撞结果符合 IFC 标准。
- confidence：medium
- limitations：应急疏散场景和 Unity 原型与本项目静态家具分析不同；collider 精度由作者称为相对常规级别。
- follow_up：只作为外部工程先例，不能直接导入项目阈值。

### E-BIM-006
- date：2026-09-27
- question：BIM 规则语言能否表达室内空间合规约束？
- claim：Sydora & Stroulia 提出用于室内设计规则的领域语言，并以厨房和客厅布局案例进行规则检查与生成设计。
- evidence_class：BIM_INTEROP
- source：Sydora & Stroulia, “Rule-based compliance checking and generative design for building interiors using BIM”
- version/year：2020，Automation in Construction，DOI 10.1016/j.autcon.2020.103368
- locator：[DOI](https://doi.org/10.1016/j.autcon.2020.103368)；Consensus record [paper](https://consensus.app/papers/details/b09f746b4d8655aca22831ed0d1f1106/?utm_source=chatgpt)
- access_status：abstract_only
- short_excerpt_or_paraphrase：摘要说明同一规则语言用于模型检查和生成布局；全文未取得。
- supports：项目可把规则/阈值作为显式工程配置，而不是感知权重。
- does_not_support：不提供本项目家具 clearance 规则，也不证明 IFC 原生属性映射。
- confidence：low
- limitations：仅摘要级；规则具体内容和几何实现未核验。
- follow_up：若需要规则语言设计，先取得全文并逐条映射。

### E-BIM-007
- date：2026-09-27
- question：通用设计研究如何定义清空地面/触及范围？
- claim：Kang & Lee 用 clear floor space、work flow、reach range、knee clearance 等标准分析公寓厨房布局。
- evidence_class：BIM_INTEROP
- source：Kang & Lee, “Application of Universal Design in the Design of Apartment Kitchens”
- version/year：2016，Journal of Asian Architecture and Building Engineering，DOI 10.3130/jaabe.15.403
- locator：[DOI](https://doi.org/10.3130/jaabe.15.403)；Consensus record [paper](https://consensus.app/papers/details/95bb9441a11b501da16874e97f42e709/?utm_source=chatgpt)
- access_status：abstract_only
- short_excerpt_or_paraphrase：摘要按轮椅用户移动标准分析清空地面、工作三角、触及范围和膝部空间。
- supports：通用设计约束是外部规范/人因背景，可作为未来 authored requirement 的候选来源。
- does_not_support：不支持 IFC schema、家具通用阈值或本项目心理效度。
- confidence：low
- limitations：摘要级且场景限于韩国公寓厨房；ScanSci 未找到 PDF。
- follow_up：负责人若要采用人因约束，需指定规范版本和适用用户群。

### E-BIM-008
- date：2026-09-27
- question：BIM 是否能表达维护可达性而不仅是几何碰撞？
- claim：Liu & Issa 讨论用 BIM 工具和规则集检查维护可达性；普通 clash detection 不一定发现 accessibility 问题。
- evidence_class：BIM_INTEROP
- source：Liu & Issa, “Design for maintenance accessibility using BIM tools”
- version/year：2014，Facilities，DOI 10.1108/f-09-2011-0078
- locator：[DOI](https://doi.org/10.1108/f-09-2011-0078)；Consensus record [paper](https://consensus.app/papers/details/ae5262d2138c5f45a658fd2042e8ab3c/?utm_source=chatgpt)
- access_status：abstract_only
- short_excerpt_or_paraphrase：摘要以排风机维护为案例，指出需有相应规则集才能检查可达性。
- supports：clearance/可达性必须绑定目的和规则集，不应只做几何相交。
- does_not_support：不支持家具使用区或 IFC 原生 affordance schema。
- confidence：low
- limitations：摘要级且场景为设备维护；ScanSci 未找到 PDF。
- follow_up：不要把维护可达性规则直接迁移为家具行为规则。

## 不可访问原文清单

1. Gestalt 相关条目 PMC4593740：当前 PMC 入口 reCAPTCHA/Cloudflare，无法核验全文；Wagemans 2012 综述已由负责人提供 PDF 并完成全文核验。
2. BIM 家具 affordance/clearance 的直接 IFC 原文：检索未找到可访问权威原文，需负责人提供 DOI/PDF/schema。
3. Blender 5.2 官方发布页：当前访问返回 402；仅把本机便携版 `--version` 作为环境观察，不作官方发布证据。

## 研究流程出处（非领域证据）

检索、证据分层和引用核查按项目已有技能执行；技能程序化研究流程的外部说明见 [Kassis et al., Scientific Agent Skills, arXiv:2609.00065v2](https://arxiv.org/abs/2609.00065)。该论文不支持任何 IFC、几何或心理结论。
