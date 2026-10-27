# 家具组归属证据场实施计划

> **执行约束：**执行本计划时必须持续维护本文 checklist。每完成一个任务，先补上验证命令或审阅证据，再勾选对应项；失败或阻塞时保持未勾选，写明原因，并停止依赖该项的后续任务。范围或设计需要变化时，先更新 spec 和 checklist，再继续。不得用诊断夹具通过来代替生产实现或现实有效性证据。

**目标：**在不把家具组当作 ground truth、不强制唯一分区的前提下，按已审阅 spec 建立输入契约门、真实证据审阅门，以及门通过后的候选记录和完整作用域归属证据场。允许得到“证据场可用、标量读数仍未决”的结果。

**状态：**阶段 1 已实现并通过指定回归。阶段 1B.0–1B.6 已按当前真实 IFC 的覆盖范围完成交付与自检：37 组、95 成员、666 组对全部有几何关系 envelope 和对应 JSON/SVG，完整 manifest 与图面样本已核查。扩展契约测试在保留的真实 scene/description 上重放通过；未独立重提几何。重叠、共享成员、missing/invalid/partial 等本源未出现的分支仍未覆盖。用户于 2026-10-27 对总览、分离及接触示例的审阅答复“合理”，阶段 1B 用户审阅门已通过；下一步是阶段 2 的证据用途/规则澄清，尚未执行新的读数比较、候选推断、其他证据包或强度实现。

**依据：**[目标对齐与范围边界](../../project/grouping-goal-alignment.md)、[非概率强度 spec](../../project/grouping-strength-spec.md)、[协议执行结果](../../project/evidence/grouping-strength-design-protocol-results.md)、[输入清单切片计划](2026-10-26-group-attribution-field.md)。

## 固定边界

- AuthoredGroup 是有来源的输入事实，不是真值。只有明确 `furniture_group` 标记或 adapter 明确声明的等价标记才合格；空组只留审计，不进候选节点；重复引用只在身份和证据计数中去重；失效引用留存并带状态；共享对象保留在每个引用它的合格组中，不作 first-wins，也不自动视为互斥。
- 候选是可重叠、嵌套、并存、未覆盖全域的组织假设。候选提议、完整作用域归属场、组 profile 和下游势契合分开处理；明确且可解析的互斥只否决端点共同进入一个候选，不清零端点读数。
- unknown、partial、invalid、conditional、conflict、not_available、not_evaluated 和 incomplete 都保留状态、原因与来源，不换成数值零。范围外于 proposal extent 但仍在冻结作用域内的单元可报告边界张力；scope 外实体不补 field cell。
- 不批准概率语义、标量 `M` 公式、权重、阈值、跨候选归一化、唯一 recipe/winner、UI、公共 API 或 `room_analysis_model` 形状变化。不新增依赖；不恢复 Stage B 合成标签拟合路线。
- legacy dictionary 只使用其逐对象 marker 能表达的信息；不合成空组、悬空引用或共享成员事实。`analysis_scene_view` 的单值 `group` / `region` / `furniture_group` 投影及其旧消费者保持兼容，不从中反推共享关系。canonical contract 继续拒绝重复和悬空引用。
- 本轮增补的首个证据包只使用组间几何关系：成员对的原始/归一化边界间隙、接触、正面积重叠、重叠面积和 witness/source refs。它们是结构化观察，不是支持分数、势强度或正式归属边。
- 证据包通过共享 `FieldResultEnvelope` / `EvidenceChannelRecord` 接入；不新增第二套 field kernel、通用插件框架、DSL、job/result registry 或隐式 selector。后续证据包可以自带几何计算和规则，但必须输出同一类 target/query/channel/status/source/provenance 契约。
- **本阶段唯一现实数据源（依据历史项目记录推断并暂锁定）：**`outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`。任何新运行只读此 IFC；不得换用其他 IFC、SVG、手工拼接 NeutralScene、模拟组/家具/几何或缓存旧观测冒充本轮结果。既有协议夹具只是历史设计审查记录，不是本阶段的数据或现实验证。
- **阶段 1B–4 全程数据边界：**所有新测试运行、读数比较、盲审、recipe/search/profile 诊断与结果只能由上述指定 IFC 的实际记录和从其几何计算出的观测产生。不得新建模拟布局、组、成员、几何、关系或预置读数；不在 IFC 中出现的情形记为“未覆盖”，不得造样例补齐。阶段 0/1 已有夹具与测试仅保留为历史设计或回归证据，不得作为阶段 1B–4 的输入、通过依据或现实有效性证据。
- **源文件身份门：**2026-10-27 在当前工作区观察到该路径文件为 `408618044` bytes、SHA-256 `1C97E93D5C6F6E2F2430816ACA2D2F72BB44FED1AC98AFA3AED567AE905CC077`。历史关系实验使用同一路径但记录的是 `408617800` bytes、SHA-256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`；历史图和计数不得代表当前字节版本。每次运行前核验路径、长度和 SHA-256，并读取/记录当前 IFC schema、project GlobalId、单位和 group/member 身份；指纹与本计划记录不符时停止，不自动改用新输入或旧输出。
- 关系几何只从该 IFC 的明确 `IfcGroup.ObjectType == "furniture_group"` 成员声明、成员 `IfcFurniture` 的 `Body` 几何及其 IFC placement 得出。沿用现有只读 IFC→NeutralScene/`describe_group_relations` 几何路径，应用 source unit/placement 转换恰好一次，再投影到 `scene.context.analysis_plane`；统一线性观测单位并在输出中记录 source unit、转换、frame、容差和算法版本。用户于 2026-10-27 确认当前先采用 world-XY，但不能将其写死在证据包或绘图规则中；未来由相机功能提供新的场景平面，查询、计算和绘图须共同读取该平面。没有合格 `AnalysisDomain` 时，当前结果和平面图明确标作 world-XY 诊断投影，不称为生产分析平面。
- 每个跨组成员对只观察边界距离、面积归一化间隙、接触、正面积重叠/重叠面积，并保留 IFC group/member/source refs、witness、状态和共享成员依赖。当前 `_member_pair_observation` 的计算依据是 Shapely 投影多边形的边界距离与交集面积；接触由间隙容差和非重叠共同定义。组级归并仍 deferred；几何相近、接触或重叠均不生成支持边、候选、成员归属、势或强度。
- **可视化是每次新运行的交付门：**结果必须配套由同一指纹 IFC 生成的平面图；真实家具投影/组身份作为底图，间隙 witness、接触、重叠及不可用/失效状态有清晰区分和图例。不得只画代表性组对而隐藏其余结果：每个 envelope/组对都必须可在完整图层、分幅图或可索引的逐组对平面图中找到，manifest 必须把结果 ID 映射到图面并与 JSON 结果数核对。图及 manifest 显示 IFC 路径/指纹、schema/project identity、坐标 frame、单位、投影说明和 diagnostic-only 边界；缺失几何仍以 ID/status 标出，不补画虚构几何。
- **阶段 2–4 可视化门：**每个新读数、盲审观察、recipe/搜索诊断及可用 profile/field cell 均须能在同一 IFC 指纹生成的平面图中定位；用标注、图层或分幅展示完整结果，并由 manifest 映射结果 ID 与图面。不能合理投影到平面图的内容须标明不可映射并阻断该结果被当作已完成证据，不得仅用汇总表或文字替代空间结果。

## Checklist 维护协议

1. 本文是执行中的唯一状态清单。每个任务完成后，在 checklist 中附上通过的命令、报告路径或审阅记录，再将 `[ ]` 改为 `[x]`；仅开始、部分完成或代码已改但验证未过，都不能勾选。
2. 任务失败、输入资料缺失或前置门未通过时，保留 `[ ]`，在同一项后加 `BLOCKED — 原因 / 所需证据`，并停止所有依赖该项的任务。不要把“未决”记成“通过”。
3. 每次开始新阶段前先检查前置门的 checklist 和证据。若要改变范围、状态语义、recipe 规则或输出形状，先修订 spec/计划并记录审阅，再恢复执行。
4. 每次阶段交接前更新“执行记录”：记录当前门、已完成项、阻塞项和下一项。保留其他工作区改动；jj 优先用于后续版本/工作区管理，不提交、不推送，除非用户另行授权。

### jj 可追溯执行协议（用户确认后启用，2026-10-27）

- 每个实验/实现增量开始前，先记录 `jj status`、`jj diff --stat`、当前
  change id、bookmark 和 `jj op log` 的最新操作；不把未相关 dirty work 静默
  丢弃或重置。
- 用户已授权为本次开发保留本地可回溯历史，但不授权远端 push。对已完成的
  当前基线先建立带说明的本地 checkpoint，再在其子 change 中进行 seed/seed-set
  实验；实验与基线的变更说明必须明确区分“文档/计划”“诊断实现”和“生产实现”。
- 每个增量完成后记录 `jj diff`、验证命令、产物路径和 change id；失败时保留
  失败 change 和日志，不把失败结果改写成通过。需要撤回时优先使用 jj 的
  `jj op log` / `jj op restore` 或恢复到明确的父 change，不直接删除工作目录。
- 本计划不自动执行 `jj git push`、合并或重写远端历史。任何后续 checkpoint
  都只在当前 `codex/group-attribution-evidence-field` 工作线上保留，除非用户
  另行指定 bookmark 或发布动作。

## 计划任务

### 阶段 0：复用已完成的设计审查基线

- [x] 复用协议报告中已重放的 I/C/S/F/D/P 诊断矩阵；其结论只证明夹具表达能力，不证明生产路径或真实量尺。证据：`docs/project/evidence/grouping-strength-design-protocol-results.md`。
- [x] 复用已独立审阅的非概率强度 spec；将标量映射、家族融合和现实校准继续列为未决。证据：`docs/project/grouping-strength-spec.md` 状态与第 5、6、8 节。
- [x] 复用已完成的 AuthoredGroup 输入清单切片，不重做 inventory helper；本计划仅追踪切片审查发现的剩余状态传播和 IFC 空组缺口。证据：`docs/superpowers/plans/2026-10-26-group-attribution-field.md` 与当前实现。

### 阶段 1：对齐输入身份和状态语义

**范围：**只修复中立场景输入事实的传递与审计，不改变旧投影、canonical 拒绝规则或任何候选/强度算法。

- [x] 在 `group_self_description` 的逐组 eligibility 记录中传播 inventory 的 `input_completeness_status`，不要把 partial/invalid 输入报告成 computed；区分输入完整性与几何计算状态。证据：`test_neutral_eligibility_preserves_input_status_separately_from_geometry_status`。
- [x] 调整 IFC group 适配，使显式空 `IfcGroup` 仍能作为 NeutralScene 输入事实到达审计；空家具组标为审计项，不产生候选节点。保留普通 IFC 组的非家具角色，不推断其资格。证据：`test_adapter_retains_empty_ifc_groups_for_authored_group_audit`。
- [x] 增加 partial、全失效引用、显式空 IFC 家具组的回归断言；确认重复引用仍只计一次、共享对象仍映射到所有合格组。证据：`test_neutral_eligibility_preserves_input_status_separately_from_geometry_status`、`test_empty_authored_furniture_group_stays_in_audit_not_eligibility`、`test_neutral_group_description_keeps_inventory_edges_and_deduplicates_geometry`、`test_inventory_preserves_authored_group_edges_without_collapsing_shared_members`。
- [x] 回归确认 canonical contract 仍拒绝重复/悬空引用，`analysis_scene_view` 的兼容投影不变，legacy 路径不补造其无法表达的事实。证据：阶段 1 回归命令覆盖 `test/test_canonical_layout_contract.py`、`test/test_scene_contract.py`、`test/test_group_self_description.py`；221 passed。
- [x] 同步 `docs/software-architecture.md`，只记录实际输入流和审计边界；未声称候选、归属或强度算法已实现。
- [x] 运行 `pixi run pytest test/test_authored_group_inventory.py test/test_group_self_description.py test/test_ifc_bonsai_adapter.py test/test_canonical_layout_contract.py test/test_scene_contract.py -q`；结果：`221 passed in 772.39s (0:12:52)`。focused regressions：`3 passed in 0.28s`。

**阶段 1 执行结论：通过。**输入资格状态、IFC 空组保留、重复/共享/失效引用审计及旧边界的指定回归均通过。架构文档已同步。此门只允许进入阶段 1B 的几何关系场；尚未实现或审阅阶段 1B。

**阶段 1 通过条件：**输入身份规则在 inventory、IFC adapter 与 group description 输出间一致；所有回归测试通过；strict canonical 与旧兼容投影保持原约束。未通过则停在此阶段。

### 阶段 1B（增补）：建立仅组间几何关系的首个证据场

**进入条件：**阶段 1 已通过；若阶段 1 尚未完成，只能先写契约测试和文档，不得把几何观察接入生产场输出。

**本阶段目的：**把现有 `group_self_description` 的组间成员对几何观察包装成可审计、可重放的关系场记录，作为后续证据包的最小接入样板。这里的“场”只表示结构化关系证据；不把“近/接触/重叠”解释成同场支持，也不派生势1相似度、正向支持、候选、强度或 winner。

**现实输入：**本阶段新增实现、测试运行和诊断产物只使用固定的真实 IFC 路径及通过源文件身份门的字节版本。不得创建模拟布局、家具组、成员几何或关系结果；历史实验只作方法背景，不能替代当前输入重跑。每次产生的关系结果都必须能在同一 IFC 的平面图中定位。

**首个证据包输入/输出契约：**

| 项目 | 契约 |
| --- | --- |
| 输入 | 指定 IFC 中阶段 1 合格的 `AuthoredGroup` 对、其 IFC Body 几何来源、冻结作用域、`FieldQuery`（`domain_id` 表示 scope，`frame/plane/height_band/tolerance/revision` 保留查询上下文） |
| 目标 | 每个稳定排序的组对产生一个 `target={kind: "furniture_group_pair", id: canonical_json([group_a, group_b]), identity: ...}`；组 ID 先规范排序，再以无歧义的紧凑 JSON 数组编码，避免合法组 ID 含分隔符时碰撞；不能随输入顺序变化 |
| 几何通道 | `boundary_gap`、`contact`、`positive_area_overlap`；观察中保留 raw/normalized gap、overlap area、member-pair 列表和 witness/source refs |
| 状态 | 保留 computed/partial/invalid/not_available/not_evaluated 等原始状态；shared-member 作为依赖诊断保留，不改写成支持或冲突 |
| 记录边界 | 每个结果是一个 `FieldResultEnvelope`，包含 `FieldQuery`、channel records、source IDs、package provenance、解释和 cache identity；不生成 `field_projection` 或标量值 |
| 可重放性 | 当前指定 IFC 的路径/长度/SHA、来源/查询/证据包算法/模式版本进入 fingerprint；pair、channel、member-pair 和 source refs 稳定排序；相同输入重复运行得到相同结构和 identity |

**证据包适配规则：**未来证据包可以在自己的适配模块中计算几何或读取标签，但不能把规则写进 `field_core.py`；`field_core.py` 只负责共享结果契约、状态冻结、来源审计和 cache identity。几何首包必须复用 `_group_relations` / `_member_pair_observation`，不得复制 Shapely 几何计算；组级 `raw_boundary_gap`、`contact`、`overlap` 仍保持 deferred，首包只包装现有 member-pair observations。所有关系数值必须来自本阶段身份门通过的 IFC 运行；没有出现在 IFC 中的几何情形不得用合成对象补造，记为未覆盖。

- [x] **1B.0 锁定并资格化唯一 IFC 输入。**只读核验固定路径、文件长度、SHA-256、IFC schema/project GlobalId、长度单位、精确家具组身份及成员引用；确认当前版本与上方观察到的指纹一致。核验 IFC 文件前后 hash 相同；输出本阶段 source manifest。资格检查确认 37 组均为精确家具组标记、95 条成员引用均指向有 Body 表示的 IfcFurniture，且没有重复 GlobalId 引用；Body 表示的几何有效性留待真实关系提取阶段核验。证据：`docs/project/evidence/group-attribution-ifc-source-manifest.json`；`pixi run python` + IfcOpenShell 0.8.5 只读清单检查；文件前后 SHA-256 相同。任一身份/单位/几何资格与预期不符则停止，不复用旧 hash 下的历史 PNG/JSON。
- [x] **1B.1 先写 IFC 驱动的契约测试。**`test/test_group_geometry_relation_field.py` 只读取通过身份门的 IFC，经现有 adapter 和关系描述路径取得真实组对，断言 envelope 的 target/query/channel/provenance、`field_projection is None`、描述性通道和无 support/strength 语义；由 manifest 的 37 个真实组推导并核验 666 个无序组对。验证命令：`pixi run pytest test/test_group_geometry_relation_field.py -q`；结果：`1 passed in 1441.70s`（2026-10-27），第二次运行修正适配器规范 `ifc-group:<GlobalId>` 后通过。不得用模拟场景或历史产物替代。
- [x] **1B.2 实现最小几何包适配器。**`features/group_geometry_relation_field.py` 提供 `build_group_geometry_relation_envelopes`，复用 `describe_group_relations(scene)` 的 member-pair observations、状态、shared-member 依赖和来源 witness，按稳定 pair ID 输出 `FieldResultEnvelope`；未修改公共 API、canonical validation 或 `room_analysis_model`。证据：上述 IFC 驱动契约测试通过。
- [x] **1B.3 接入共享 field 契约。**三个几何通道均为 `EvidenceChannelRecord`，保留 descriptive polarity、状态、source refs、单位和 provenance；缺失/失效不填零；使用 `build_field_result_cache_identity`。证据：上述 IFC 驱动契约测试断言 channel set、descriptive polarity、无 support、source/input fingerprint 和非空 identity。
- [x] **1B.3a 临时复用投影。**组关系路径复用本次 `analysis_scene_view` 已计算的未平移几何投影，避免重复投影；不建立跨调用缓存或新的缓存机制。验证：`pixi run pytest test/test_group_self_description.py -q`，42 passed（2026-10-27，仅为既有逻辑回归，不计作指定 IFC 的 1B 现实证据）。
- [x] **1B.4 基于指定 IFC 做回归验证。**核查 666 组对/4386 成员对均为 computed、source refs 和共享依赖元数据与本源一致、组对排序稳定；每组对选一个真实 computed 成员对复算正反方向，共 666 样本；同一真实 description 重建 envelope 的值与 identity 一致。证据：本阶段结项记录及 `outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96/artifact_validation.json`，修正测试在保留的真实 IFC 现场重放 `1 passed in 5.88s`，exit code 0。未独立重提几何；正面积重叠、共享成员、missing/invalid/partial/unavailable 分支本源没有，保持未覆盖，不代表状态传播已验证。不得构造模拟几何补覆盖。
- [x] **1B.5 同步场与证据包文档。**新增 `docs/project/evidence/geometry-relation-field-package-v1.md`，描述场基础模块、首包输入输出、状态和未决边界；同步 `docs/project/grouping-goal-alignment.md`、`docs/software-architecture.md` 和 `docs/indoor_layout_evaluation_matrix_architecture_memory.md`，只记录已实现的共享 Field core 接入和首包边界，不提前声称完整归属场或 free-space/live promotion 已完成。证据：上述四份文档已更新。
- [x] **1B.6 生成并审查 IFC 平面图结果。**本轮产物目录 `outputs/design/group_geometry_relation_field_ifc/run_20261027T165920Z_fb0d96` 含完整 envelopes、plane-local geometry、666 对 JSON/SVG、overview 及 view manifest；全部 667 SVG 解析通过，每个 envelope 与 pair JSON/图面一一对应。总览、最近/最远分离组对、接触组对 PNG 已目视审阅；逐对完整性为结构/manifest 检查，不声称逐张目视。运行前后源 hash 一致，图面包含源身份、平面、单位和 diagnostic-only 标记。证据：`artifact_validation.json`、下方结项记录及首包文档；独立只读产物复审认可当前源覆盖范围内交付。
- [x] **交接门：用户审阅几何关系场。**2026-10-27，向用户说明审阅范围为总览中的投影布局、分离示例中的来源组及最近边界、接触示例中的投影接触；用户答复“合理”。这是展示结果的样本审阅认可，不扩大为全部状态/其他平面或归属强度的认可。下一步先讨论阶段 2 所需的证据用途和规则；新证据包仍须逐个讨论输入/规则/状态/输出。

**阶段 1B 通过条件：**唯一 IFC 源身份经核验且运行前后未变；每个合格组对都能得到可审计的几何关系 envelope；状态、共享成员依赖、source refs、query 和 fingerprint 可追且重放稳定；所有结果均可在本轮 IFC 平面图中定位；没有 selector、formal membership edge、positive support、strength、winner 或概率语义。通过后先停下来审阅几何场，再讨论下一个证据包。

**执行记录（2026-10-27 续）：**1B.1–1B.3 的真实 IFC 契约测试首次运行发现测试期望使用裸 GlobalId，而适配器规范身份为 `ifc-group:<GlobalId>`；修正测试身份编码后重新运行通过。两次运行均读取同一 manifest 指纹 IFC；首次失败不计为通过证据，第二次 `1 passed in 1441.70s` 作为当前证据。由于全 IFC Body 三角化成本约 24 分钟，后续验证不得未经审阅擅自改用抽样、旧 hash 产物或模拟场景。

**执行记录（2026-10-27，投影复用）：**`_neutral_scene_view` 将本次未平移的投影组件留在私有 view 元数据中，`_neutral_inputs` 和已接受的 trend 替身几何复用这些组件；没有改投影算法或几何/状态语义。`pixi run pytest test/test_group_self_description.py -q` 通过（42 passed），其中既有合成回归仅用于代码兼容检查，不作为 1B 现实证据。完整 IFC 状态审计及全结果平面图仍未完成。

**执行记录（2026-10-27，分析平面与合并验证）：**当前使用场景提供的 world-XY；证据包新增 query plane 与 scene plane 一致性校验，绘图复用同次关系描述的平面局部多边形。1B.4/1B.6 的 IFC 契约测试与全量报告合并在一次加载中进行，不引入持久投影缓存。早先仅打印平面名称的遗留加载已结束；首次报告运行因检阅发现名称字段和审计变量错误而中止，不计作通过证据。两项 checklist 保持未勾选，待修正后的真实运行与图面审查。

**合并验证失败记录：**`pixi run pytest test/test_group_geometry_relation_field.py -q -s` 在 `1193.51s` 后失败于 shared-member provenance 的比较：Field core 冻结后的 `member_ids=()` 与原描述的 `member_ids=[]` 内容相同，测试直接比较嵌套容器却把冻结类型差异当成事实差异。修正为逐字段比较状态及成员 ID 列表，未修改生产数据或几何规则；失败不计通过。下一轮加 `--pdb` 保留意外失败时的真实计算现场，避免丢失数据后反复加载 IFC。

**扩展验证与重放记录（2026-10-27）：**下一轮 `pixi run pytest test/test_group_geometry_relation_field.py -q -s --pdb` 发现测试引用被公开 description 过滤掉的私有 `_tolerances`；修正为读取 `scene.context.geometry_tolerance`。该外层运行最终仍为 `1 failed in 1356.70s`，不计通过。调试器保留本轮真实 IFC scene 和 description；重载修正后的测试，仅将 loader/descriptor 返回值指向这两份真实对象，再执行同一测试的 nested pytest，得到 `1 passed in 5.88s`、exit code 0、对称性样本 666/666。通过证据是保留真实计算现场的重放，不是新一轮独立完整 IFC 几何提取；identity 检查也是同一 description 的 envelope 重建，不声称独立提取可重复性。

**阶段 1B 结项记录（2026-10-27，交付待用户审阅）：**源文件长度 `408618044`、SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`，运行前后及独立只读产物复审一致。37 组/95 成员产生 666 computed 组对、4386 computed 成员对，其中 4370 gap、16 contact、0 正面积 overlap；16 组对含 contact，666 组对也均有正 gap，组对类型不互斥。共享成员依赖为 0；666/666 组对有可追 source refs。全部结果已映射到本轮 `run_20261027T165920Z_fb0d96` 的 pair JSON/SVG 和 manifest；667 SVG 均可解析，总览、近距、远距、实际接触 PNG 样本可读。后续 SVG 文案/来源元数据刷新只使用本轮保存的 polygons/pair JSON，未修改几何观测、envelope 或 IFC。报告 helper 为 `scripts/design/group_level/render_group_geometry_relation_field_ifc.py:write_report`，由测试传入本次计算结果，不负责加载 IFC。详见[首包验证记录](../../project/evidence/geometry-relation-field-package-v1.md#current-verification-and-limits)及产物 `artifact_validation.json`。据此勾选 1B.4/1B.6；本源没有的重叠、共享成员、missing/invalid/partial/unavailable 分支及其传播保持未覆盖。world-XY 从 scene context 读取，其他平面/相机接入尚未验证。下一项仅为用户审阅几何场；阶段 2–4 不推进。

### 阶段 2：完成读数与现实解释性决策门

**进入条件增补：**阶段 1 与阶段 1B 均已通过，或其未决影响已记录并得到审阅；阶段 1B 的结构化几何观察不得被当作强度或现实解释性证据。

**当前交接（2026-10-27）：**阶段 1B 样本审阅已获用户“合理”的答复。用户随后确认距离的软关联方向，并澄清上层组没有硬边界、不作“是否同组”的二值判定，但需可描述的组织功能以计算总体朝向。用户对“候选组织方式（这里简称组织视图）→完整 scope 软参与→总体方向/离散度”结构表示暂时同意；“组织视图”不是新增对象，只是对计划/spec 中 candidate `k` 的解释性称呼。该结构作为讨论基线，尚未批准候选 recipe、参与公式、阈值或成员对到组对的聚合；`seed/seed-set` 也只是待审提出方案，不是原计划既有机制，也不隐式加入方向相似性证据包。下一项讨论候选如何提出，以及距离怎样转成软参与程度；涉及输出/汇总边界时先增补 spec/checklist，再实施。需要用户回答时停止。下方真实比较、盲审及 recipe 等未执行项保持未勾选。

**试验增补（2026-10-27）：**用户同意先试 seed 思路。先做只读诊断：以现有真实 IFC 运行产物中的每个 AuthoredGroup 作为 seed，输出其对完整 scope 的组对距离剖面和可定位平面图；只保留原始/汇总几何观察与相对排序，不生成 participation、membership、support、strength、candidate closure 或 winner。该试验用于检查表示是否足以承载“总体方向”的后续输入，不改变阶段 2 的正式 recipe/读数决策。

**证据结构渐进原则（2026-10-27，用户确认）：**证据包、证据通道、Envelope 与最小证据分辨率先作为可演进的工作契约，不在首个几何包之后提前锁死最终组合方式。每新增一个证据包，先记录其输入数据、几何/标签规则、原子观察、通道、Envelope 目标、状态与来源要求；实现后检查现有结构是否能无损承载这些事实。若不能，先扩展契约并记录审阅，再继续实现；不得为了适配旧结构而丢弃原始观察、共享依赖、状态或来源。只有在多个真实证据包都完成结构审阅后，才裁定最小证据分辨率、跨通道派生规则和是否允许显式的有向证据组合。任何组合都必须保留输入通道和来源链，不能自动压成总分。

- [x] 将协议夹具已覆盖的完整 candidate×scope 表示、scope 外事实、状态分层、依赖引用、profile 覆盖和 singleton 缺证据视为设计诊断基线；如阶段 1 暴露新的契约缺口，只补那个缺口，不复制既有矩阵。证据：协议结果报告及 `scripts/design/group_level/run_group_attribution_field_slice.py`、`run_group_attribution_protocol_followup.py`。
- [x] **阶段 2A：seed 关系剖面诊断（仅表示试验）。**从现有指定 IFC 的完整几何关系产物生成每个 AuthoredGroup 作为 seed 的完整 scope 关系剖面和逐 seed 平面图；只输出 raw/normalized gap、contact/overlap 状态、source refs 与相对排序，不输出 participation 或任何归属/强度读数。验证命令：`pixi run python -m scripts.design.group_level.run_seed_candidate_profile_experiment`；外部审计确认 37 个真实 seed、666 个组对、每 seed 36 个关系、每 seed 37 个 scope 成员、37/37 SVG XML 可解析、source fingerprint/query plane 对齐，且 `participation_formula=null`、`strength_formula=null`、`candidate_closure=not_evaluated`。证据：[`group-seed-relation-profile-experiment-v1.md`](../../project/evidence/group-seed-relation-profile-experiment-v1.md) 与 [`run_20261027T_seed_profile_v1`](../../../outputs/design/group_seed_candidate_experiment/run_20261027T_seed_profile_v1)。该项只证明表示试验完成，不批准 seed recipe、参与度或强度；下一步为用户审阅少量 seed 平面图。
- [ ] **阶段 2B：证据结构适配审阅。**对每个后续证据包逐项记录输入、原子观察、通道、Envelope 目标、状态/来源和可视化定位；检查现有契约能否无损承载。若出现结构缺口，先更新 spec、架构文档和 checklist，再实现该包。阶段 2B 不提前裁定最终最小证据分辨率、跨通道组合或包套包规则；这些决定留到多个真实证据包完成结构审阅后。
- [x] **阶段 2B.1：势/趋势现有实现审计。**审计 `furniture_frame.py`、`group_self_description.py`、`scene_inference.py` 及既有 trend 证据记录；确认已有组级 `overall_group_axis`、`member_frame`、`member_axis`、`layout_axis`，以及 typed Analysis 来源/状态传播；确认它们尚未接入几何关系 Envelope。历史趋势产物因 IFC hash 过期不可复用；旧测试 monkeypatch 漂移已修复，当前焦点回归 `13 passed`；当前 IFC 样本重放选出 3 个完整组，typed Analysis 均 accepted，四类 estimand 均 computed。证据：[`group-trend-alignment-audit-v1.md`](../../project/evidence/group-trend-alignment-audit-v1.md)。该项只完成现状审计，不批准第二包的最终通道或组合规则。
- [x] **阶段 2B.2：冻结势/趋势对齐包 v1 工作契约。**用户于 2026-10-27 同意以 `furniture_group` 为 target，保留 `overall_group_axis`、`member_frame`、`member_axis`、`layout_axis` 四个并行通道，并分别保留 typed Analysis bindings、source/provenance、状态和诊断证据。该项只冻结结构承载方式；组合、总体势/strength、权重、阈值、candidate/winner 与包套包仍未决定。证据：[`group-trend-alignment-audit-v1.md`](../../project/evidence/group-trend-alignment-audit-v1.md#approved-second-package-working-contract)。
- [x] **阶段 2B.3：当前 IFC 全量势/趋势对齐诊断。**只读运行固定 IFC，覆盖全部合格 AuthoredGroup；为每组输出四通道 Envelope/JSON、source/status audit、同一分析平面的组级可视化和 manifest。不得把诊断结果接入几何关系包的组合、candidate、membership 或 strength；不得用合成布局补足 IFC 未覆盖状态。验证：`pixi run python -m scripts.design.group_level.run_group_trend_alignment_field_ifc` 返回 `status=pass`；当前指纹前后均为 408618044 bytes / SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`；37 envelopes、每个 4 channels、37 computed / 0 partial / 0 invalid / 0 not_available；148 SVG 与 manifest 条目，独立 XML 解析 `148/148` 通过。证据：[`group-trend-alignment-field-package-v1.md`](../../project/evidence/group-trend-alignment-field-package-v1.md) 与 `outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/`。
- [x] **阶段 2B.4：静音单体家具层并审计早期 2D 组间关系。**趋势包公开通道收缩为 `overall_group_axis` 与 `layout_axis`；`member_frame`、`member_axis`、成员绑定和成员明细保留在底层描述/provenance 作为 suppressed audit，不再进入 active `channel_set` 或新图层。组间几何包继续以家具组对为 target，member-pair gap/contact/overlap 只标为 `audit_only`，组级聚合仍为 `deferred`。对照早期 `group_self_description`、`position_grammar`、`column_grid`、region-shape 与 network 设计，只有前者的 semantic/neighborhood 关系登记到当前 envelope provenance；位置模式和柱网关系保持独立证据域。证据：[`group-relation-history-audit-v1.md`](../../project/evidence/group-relation-history-audit-v1.md)、聚焦契约测试 `test/test_group_evidence_unit_boundary.py`（2 passed）。真实 IFC v2 runner 尚未重新执行；旧 v1 产物保留，不可当作 v2 验证。
- [ ] 对指定 IFC 中可观测的同源、移除提议证据、独立/留出 attribution 三臂做读数比较；所有比较输入、输出及其差异都映射到该 IFC 平面图。只有存在可解释且可辩护的读数映射时才比较数值；若缺少映射或真正独立证据，记录为未决并停止标量 `M` 决策。不得使用合成预置读数估计膨胀效应。
- [ ] 仅用指定 IFC 选择未参与规则设计、来源可追且可遮蔽 authored-group 名称的真实场景进行盲审；审阅材料及记录都由该 IFC 的平面图呈现，并记录证据链是否可理解、异议、缺失和冲突。场景不合适或无法盲化时，记录原因并保持现实解释性未决，不换用或构造其他场景。
- [ ] 形成基于指定 IFC 的 recipe 决策记录，附可定位全部相关读数的平面图；仅在审阅证据支持时固定 recipe 语义，否则保留并行 recipe 或未决，不选唯一候选。不得把构造 fixture 的成功写成现实有效性。
- [ ] recipe 语义稳定后，才新增搜索规模/时间/内存诊断，并复用 Stage A 的 37-node 基线；只测新增搜索行为，诊断结果映射回指定 IFC 平面图，预算截断明确标 `incomplete`。recipe 未稳定时保持此项未执行，不测成本。
- [ ] 若上述结果改变 spec 的边界或读数定义，先更新并重新审阅 spec；若没有改变，记录“spec 继续作为基线”的审阅结论。

**阶段 2 通过条件：**输入门通过；同源依赖结论有证据或明确保留未决；真实场景已经盲审，或已说明没有合适场景并将现实解释性明确记为未决；recipe 与搜索成本只在其前置条件满足时裁定。未决门必须记录对后续 E、M 和 profile 分别有什么影响；不得因未决而强行推进数值强度。

### 阶段 3：通过审阅门后实现证据场

**进入条件：**阶段 1 与阶段 1B 完成；阶段 2 的每项审阅门均已完成，或已将资料不足及未决结论、原因和影响记录清楚；计划/spec 如有变更已复审。无合适真实场景时，将现实解释性明确保留为未决；缺少可辩护的数值映射时，只阻止标量 `M` 和数值 profile 的冻结。两种情况本身都不阻止按已审阅结构实现非数值证据场 `E`，但不得把其结果描述成现实验证通过或可解释强度。

- [ ] 按已审阅的 recipe 记录 `P=(recipe, scope, proposal_extent, closure_status, proposal_evidence)`；候选发现与 attribution 分开，闭包只在对应 recipe 的搜索完整时声明。无已批准 recipe 时不得暗选单一方案。
- [ ] 为每个候选和尺度/查询建立冻结作用域内全部合格 AuthoredGroup 的 `E(g,k,s)` 记录，含 proposal extent 内外的区分、逐家族观察/极性、状态与原因、source refs、依赖及 proposal exposure；scope 外实体另记原因，不造零值 cell。
- [ ] 将已核验的互斥只作为候选联合参与约束；无效、歧义、越界端点保留未决诊断。让 `search_status` 独立于 field cell 状态，截断搜索不可标为 closed。
- [ ] 仅基于指定 IFC 提供可复放的来源驱动验证，检查该源实际呈现的完整作用域覆盖、重叠候选、共享来源去依赖、状态传播、互斥端点、proposal 外读数和 incomplete 搜索；不得创建新 fixture、模拟场景或预置读数。不在 IFC 中出现的情形逐项记录为未覆盖。每个实际 field cell 和验证发现都须映射到 IFC 平面图及 manifest；不得把历史夹具通过作为现实校准结论。
- [ ] 将场作为内部设计/实现结果，不接 UI，不增加公共 API 或 `room_analysis_model` 字段；若消费者需要新输出形状，先更新 spec 并重新审阅。

### 阶段 4：可选强度投影与成员 profile

- [ ] 仅当阶段 2 提供可辩护的证据映射时，为有依据的证据家族派生非概率 `M_k(g,s)`；没有共同量尺时保留分家族向量，不生成合成标量。
- [ ] 只汇总可用的 proposal-extent 成员读数；保留均值、中位数、弱尾等并列 profile 视图及成员数、有效读数数、expected/observed family coverage、状态计数和缺失原因。具体生产统计量须经审阅，不得由本计划默认选定。
- [ ] 未知、缺失、invalid、冲突或 not_available 不填零；singleton 无内部关系证据时不得自动得满分；候选间不归一化，不生成 winner。
- [ ] 将每个可用 profile 读数、状态及成员覆盖投影到指定 IFC 平面图；完整结果通过图层/分幅和 manifest 逐项可查。无法由该 IFC 定位的 profile 结果不计为完成证据。
- [ ] 只有当 profile 读法通过独立审阅且平面图交付门通过后，才将这一阶段标为完成；否则将 M/profile 限制保持为 spec 中的未决事项。

## 停止条件与执行记录

- 以下任一情况均停止依赖任务：输入资格仍有消费者分歧；互斥端点不能唯一解析；证据来源/依赖不可追；同源比较没有可辩护读数；真实场景不适合盲审；recipe 闭包未定义；搜索预算导致 incomplete；profile 需要未经审阅的权重或阈值。
- 停止时保留已计算的证据及其状态，不回退成硬分区，不删掉未知，不以“继续实现”为理由补默认值。
- **执行记录（2026-10-27）：**阶段 1 已完成：`eligibility` 透传 authored input completeness，IFC adapter 保留空 `IfcGroup`，完整阶段 1 回归 `221 passed`，architecture map 同步；详见阶段 1 checklist 的逐项证据。历史 IFC 关系实验在指定路径的旧字节版本上记录 37 组/666 组对、650 gap/10 contact/6 overlap，且全部 diagnostic-only；当前同路径文件的长度和 SHA-256 已变化，旧计数及图不能作为当前结果。此前 1B.1 RED 测试使用 `_neutral_scene()` 合成矩形几何，违反本阶段 IFC-only 数据边界，已撤下该测试。
- **执行记录（续，2026-10-27）：**按历史记录推断并暂锁定 IFC 源；1B.0 已通过：当前文件为 408618044 bytes、SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`，IFC4，Project GlobalId `2uGd6yom9GZe5$z7LfbGW0`，长度单位 mm（0.001 m），37 个精确标记家具组、95 条唯一 IfcFurniture 成员引用均有 Body representation；核验前后 hash 一致。Source manifest：`docs/project/evidence/group-attribution-ifc-source-manifest.json`。Body 几何有效性、关系包、契约测试和平面图结果尚未完成；当前下一项为 1B.1，仅用此 IFC 编写契约测试。不得直接实现 trend、语义、自由空间、墙体或强度包。
- **执行记录（续，2026-10-27，阶段 2A）：**在不重新加载 IFC 的前提下，使用同一指纹运行产物生成 seed 关系剖面。`pixi run python -m scripts.design.group_level.run_seed_candidate_profile_experiment` 成功；脚本自检并外部审计确认 37 seed、666 组对、每 seed 36 条关系、完整 37 组 scope、37 张平面 SVG，全部 XML 可解析，source fingerprint 与 query plane 对齐。输出只保留 gap/contact/overlap 观察和相对排序；参与度、membership、support、strength、closure、winner 均未生成。阶段 2A 可勾选，但用户仍需审阅少量 seed SVG；正式 recipe、参与公式与强度决策保持未决。
- **jj 记录（2026-10-27，阶段 2A checkpoint）：**实验与证据文档已提交到本地 change `uovrnnxq`（bookmark `codex/group-attribution-seed-experiment`，message `experiment: complete seed relation profile diagnostic`）；当前工作区保留空的后续 change，未执行 push/merge。`jj status` 反复报告一个既有的未跟踪文件 `docs/project/evidence/d6-space-field-soft-field-boundary-repair-v1-empty-space.json`（约 1.3 MiB）超过默认新文件快照上限；本次未删除、未修改、未纳入该文件，也未让它阻断本实验 checkpoint。
- **用户审阅记录（2026-10-27，阶段 2A 距离表达）：**用户确认 seed 图作为“距离”表达是正确且有用的。该确认只通过几何距离的可视化表达门；尚未批准距离到软参与、候选闭包、势/强度或其他证据的映射。下一步先讨论距离在场中的保留与使用规则。
- **逐层可视化记录（2026-10-27，阶段 2A）：**按用户要求，对一个真实且含接触关系的 seed 生成距离、接触、正面积重叠、来源/状态四张同源平面图。选定 seed 覆盖 36 个组对，其中 1 个接触成员对、0 个正面积重叠成员对，36/36 关系有 source IDs；四个 SVG 均由同一指纹 IFC 的已保存投影几何生成并通过 XML 解析。证据：[`group-seed-evidence-layer-visualization-v1.md`](../../project/evidence/group-seed-evidence-layer-visualization-v1.md)。该图层交付只验证通道可分别呈现，不改变参与度、组合或强度未决状态。
- **用户计划补充（2026-10-27，证据结构渐进）：**用户确认将“先让证据包暴露结构需求，再逐步调整证据结构，最后裁定最小分辨率与组合规则”纳入当前计划。该原则已写入阶段 2 的固定工作规则；不得把当前几何包的结构试验提前宣称为最终 spec。
- **阶段 2B.1 执行记录（2026-10-27，势/趋势审计）：**现有代码已能产生组级四类趋势描述，但它们仍属于 `group_self_description` 的组几何描述，不属于当前组间几何关系证据包。历史 IFC 趋势结果绑定旧指纹，当前源不能直接复用；旧测试 monkeypatch 漂移已修复，焦点回归 `13 passed`。当前 IFC 样本重放确认 3 个完整组的 typed Analysis bindings 均 accepted、四类 estimand 均 computed；由于现有 runner 在前三个完整组后停止，这不是 37 组全量证据。下一项是讨论并冻结第二包的 target、通道和状态/来源承载，再决定是否写全量当前 IFC 诊断 runner。
- **阶段 2B.2–2B.3 执行记录（2026-10-27）：**用户同意第二包工作契约后，新增 `features/group_trend_alignment_field.py` 与只读 runner `scripts/design/group_level/run_group_trend_alignment_field_ifc.py`。runner 只从固定 IFC 提取 37 个精确家具组和 95 个成员的 Body/Analysis 表示，单次构造 NeutralScene 与描述，生成 37 个 group-target Envelope、四个并行通道及 148 个同一 `ifc-world-plan` 的 SVG；源文件前后指纹一致，所有 SVG XML 可解析。当前 IFC 全部四通道为 computed，但这只表示现有 descriptor 已计算，不代表势、强度、候选或归属已决定；partial/invalid/not_available 状态在本源未出现，仍未覆盖。证据：[`group-trend-alignment-field-package-v1.md`](../../project/evidence/group-trend-alignment-field-package-v1.md)。下一步仍是阶段 2 的真实读数比较、盲审和 recipe 决策门，不是合成趋势或强度。
- **阶段 2B.4 执行记录（2026-10-28）：**按用户“组作为最小公开单位、单体家具层暂时沉默”的决定，趋势包 active channel 已收缩为 `overall_group_axis` 与 `layout_axis`；`member_frame`、`member_axis` 及成员绑定改为 suppressed/audit。几何关系包仍保留组对 envelope，但把 member-pair 观察显式标为 `audit_only`，并写入组级聚合 `deferred` 以及历史 semantic/neighborhood/position/column-grid 对照 provenance。新增 `test/test_group_evidence_unit_boundary.py`，聚焦测试 `2 passed`。没有重新运行耗时的全 IFC v2 runner；旧 v1 产物保留，不能当作 v2 的现实验证。详见 [`group-relation-history-audit-v1.md`](../../project/evidence/group-relation-history-audit-v1.md)。

## 计划自检

| 自检项 | 结果 | 计划依据 |
| --- | --- | --- |
| 遵守目标对齐文档：模糊、可重叠的归属场；AuthoredGroup 不是 ground truth | 通过 | 固定边界；阶段 3 |
| 不引入概率、默认 `M`、权重、阈值、winner 或跨候选归一化 | 通过 | 固定边界；阶段 2、4 的条件门 |
| 保留空/重复/失效/共享输入与 legacy/canonical 的能力边界 | 通过 | 阶段 1 与固定边界 |
| 区分 proposal、完整作用域 field、profile、下游消费者 | 通过 | 固定边界；阶段 3、4 |
| 无真实场景或量尺映射时分别保留解释性/M 未决，并允许按已审阅结构继续 E | 通过 | 阶段 2、3 的通过与进入条件 |
| 将诊断夹具与生产/现实证据分开，不重复已通过矩阵 | 通过 | 阶段 0、2 |
| 真实盲审、同源泄漏与 Stage A 37-node 成本都有前置条件和停止规则 | 通过 | 阶段 2 |
| checklist 有执行期维护、证据记录、失败阻断和范围变更规则 | 通过 | 文首“执行约束”与 checklist 维护协议 |
| 首个证据包只使用组间几何关系，且不生成强度/归属答案 | 通过 | 固定边界；阶段 1B |
| 证据包通过共享 FieldResultEnvelope 接入，不引入第二套 field kernel 或插件框架 | 通过 | 固定边界；阶段 1B.2—1B.3 |
| 公开证据以家具组为最小单位；单体成员通道仅保留为 audit/suppressed，不参与 active channel 或强度 | 通过（阶段 2B.4） | 本次代码边界、`group-relation-history-audit-v1.md`、聚焦契约测试 |
| 后续证据包逐个讨论后再接入，不能由首包隐式带入 trend/语义/free-space | 通过 | 阶段 1B 通过条件；执行记录 |
| 阶段 1 严守输入身份与状态语义范围；阶段 1B 只交付几何观察，没有提前实现后续证据或强度 | 通过 | 阶段 1 checklist、221 项回归；阶段 1B 当前源结项记录；用户审阅门及阶段 2–4 待执行项保持未勾选 |
| 阶段 1B–4 新运行只读取推断锁定的真实 IFC，源文件身份在运行前后可核验 | 通过（1B.0 当前源身份已核验；旧历史指纹下产物仍不可复用） | 固定边界；1B.0 manifest；执行记录 |
| 阶段 1B–4 不新建模拟家具/布局/关系/预置读数；现实覆盖缺项如实标未覆盖 | 通过（已提升为全阶段门） | 固定边界；阶段 1B.1、1B.4 与阶段 2–4 来源驱动条目 |
| 阶段 1B–4 每项新空间结果均能定位到同一 IFC 平面图，manifest 覆盖完整结果集 | 通过（已提升为全阶段门） | 固定边界；可视化门；阶段 1B.6 与阶段 2–4 |
