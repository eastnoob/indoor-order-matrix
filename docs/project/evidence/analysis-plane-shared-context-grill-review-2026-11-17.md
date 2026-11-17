# 多 AnalysisPlane 与证据包共享基础上下文：独立 Grill

日期：2026-11-17。结论：**技术可行，但需要先补本功能 spec，再制定实施计划。** 当前只有口头候选；本报告不是已批准 spec、实施计划或实现验收。审查负责人独立阅读代码，并用三条只读核验支线交叉检查；最终判断由本报告承担。

主要缺口不是平面对象本身，而是原生 singleton、包调用输入门、实际数据配准及缓存来源投影。仅新增场景默认值和选择器不能完成需求。没有发现需要另建祖先证据包、全局属性袋或调度框架的理由。

## 1. 决策树与本次裁决

标记：U＝用户已定；F＝实现事实；C＝owner 候选；R＝本报告建议；O＝仍待裁决。

```text
同一物理场景，多平面 [U]
├─ 平面目录、默认、包覆盖 [C] → 放 scene/UI 设置 [R]
│  ├─ 包显式选择优先；其余继承场景默认 [C/R]
│  └─ native 当前是唯一受管相机 [F] → 必须支持明确身份的新建/选择 [R]
├─ 每次包调用必收平面，即使代码完全不用 [U]
│  ├─ 0 个 → 解析后拒绝；不能暗补 world-XY [U/R]
│  ├─ 1 个 → 默认路径；开跑前固定快照 [U/C/R]
│  └─ ≥2 个 → 显式许可 [U] + 本包实际能力/平面角色 [C/R]
├─ 共享基础输入 [U]
│  ├─ frozen AnalysisPlane/AnalysisContext 与私有请求可复用 [F]
│  └─ 不运行祖先包、不自动准备业务几何 [R]
└─ 实际计算依赖
   ├─ 代码不用、输入也无平面依赖 → 只记调用上下文 [U/R]
   ├─ 直接使用或消费投影数据 → 绑定实际 query/lineage [F/R]
   └─ 不同平面结果 → 继续相容性检查，不自动转换/融合 [C/R]
```

本轮唯一提出的用户语义问题已回答：强制输入也覆盖底层 `EvidencePackage.evaluate()` / `process_output()`；用户澄清“输入一定要输入……里面写代码完全没用过它”。因此不能把新要求悄悄缩为 UI 或新 `run_*` 的限定，也不需要增加“是否使用平面”的用户开关。统一默认解析可替调用者传入；包内算法允许完全忽略该参数。

**O：目前没有必须再问用户的大是大非事项。** 下文是尚待 spec 固定的技术建议，不冒充用户已批准的字段、版本或迁移方案。范围继续服从 `docs/project/grouping-goal-alignment.md:274`：本次不定义新势、归属、候选或融合算法。

## 2. 已核验事实与失败路径

严重性“高”表示会漏掉明确需求、造成错平面数据或破坏既有可信复用；“中”表示必要的生命周期/兼容边界。以下为静态代码与既有测试内容核验；没有重跑测试或完成真实 IFC/UI 验收。

### 高：共享选择不是通用计算请求，也不是祖先包

- `features/scene_contract.py:351` 的 `AnalysisPlane` 已有身份、revision、origin 和右手正交 basis；无宽高。`:424` 的 `AnalysisContext` 只含单个 `analysis_plane`，开放 JSON 在 `:100` 递归冻结。`NeutralSceneV2` 在 `:905` 也只保留一份当前 context。
- `features/analysis_requests.py:104` 的 `AnalysisRequest` 必须有一个 plane 和 grid sampling；`:756` 私有替换 scene/context，并共享原事实。`test/test_analysis_requests.py:249` 已有顺序执行的不同平面/域测试，不能据此宣称 native UI、单次多平面或并发通过。
- `features/field_core.py:523` 的 `EvidencePackageInput` 只有 envelopes/依赖；`:1037` 的 `evaluate()` 不强制 plane，`:148` 的 `FieldQuery.plane=None` 合法。`test/test_evidence_package_output.py:36,139` 明确展示无平面模板调用。

反例：为了“所有包都收平面”，强迫一个不用空间的算法构造 `AnalysisRequest`，会额外要求域、网格并可能执行抽取/投影。修正：在包调用边界接收小型、不可变的已解析平面上下文；复用 `AnalysisPlane` 和现有冻结/传递机制。单平面数值执行仍用原 `AnalysisRequest`。可增量扩展现有 callback 输入交接点 `field_core.py:1069`，无需继承树或新的包调度器。`EvidencePackage` 是组合模板而非必继承基类，见 `docs/project/evidence/evidence-package-structure.md:15`。

### 高：当前“新建”会复用或移动唯一相机，交替选择还会丢 revision

`adapters/bonsai_analysis_plane.py:584,613` 的 ensure 扫描受管 marker，多于一台就拒绝；UI `blender_addon/order_analyzer_ui/__init__.py:739` 的 New 调这个 ensure。UI `:745` 只保留当前一份 observation，换到别的 GUID 时调用 `plane_from_camera()`；该函数在 adapter `:188` 从 revision=1 开始。

反例：P1 修改到 revision=2 → 采纳 P2 → 再采纳 P1，当前路径不能找回 P1 的旧 observation。简单新增下拉框既没有创建多个受管平面，也没有稳定的逐平面观察历史。

修正：按 `(project_global_id, camera_guid)` 保存每个平面的 observation；默认/覆盖引用身份，标签不当身份。明确区分“创建新的 native drawing”与“按身份 ensure/restore/update”，复用 adapter `:454` 的原生事务和恢复路径。旧无身份 ensure 在只有一个时继续工作，多个时拒绝歧义。不要用 UI `:1927` 的逻辑 UUID 重分配动作掩盖 native 重复链接；adapter `:134` 仍要求实体与对象唯一对应。

### 高：UI 选 P1，数据仍来自 P2，不能靠改标签修复

`features/group_geometry_relation_field.py:48`、`features/group_trend_alignment_field.py:57` 校验 query plane 与 scene plane；实际组几何由 `features/group_self_description.py:124` 经 scene view 准备。`features/group_axis_potential_field.py:1111` 的 contract 继续绑定实际来源 query、plane、值及 support。函数只处理角度，也可能通过输入间接依赖平面。

修正：选择解析只决定本次上下文；具体包入口/adapter 必须核验实际 envelopes、query、frame、scope、单位、原点和几何 lineage。选中 P1 不能把旧 P2 envelope 重新贴成 P1；需要本包原有生产路径或明确拒绝。对完全无平面依赖的算法，无需强行把所收平面塞进计算 query。

多平面开关不等于能力：`AnalysisPlane` 可表示一般正交基底，但 `analysis_requests.py:328` 的 executor 对具体 query 仍有限制，exact section 要 canonical world-XY。单平面包收两个平面必须在算法前拒绝；将来真正多平面包须声明每个平面的角色及对应输入/输出，不能把“任选一个/逐个跑/融合”混成一个默认行为。

### 高：未选 P2 已经会经来源事实污染 P1 的缓存路径

静态复核链：

1. `adapters/blender_analysis_capture.py:482` 枚举所有 `IfcProduct`，`:622` 捕获 native camera binding；`adapters/bonsai_live.py:521` 将其写入 `drawing_camera` 的事实属性。
2. `adapters/blender_analysis_session.py:609` 将全部 source records 放入内容 key，只在 `:619` 删除 context 的 plane；`features/analysis_requests.py:188` 只删除显示键，不按 camera role 投影输入。
3. capture 的 `:505` 指纹仍含相机 pose；session `:678` 用它构造 `SourceBinding` 的内容/来源身份，缺省 canonical identity 也含此 content。
4. capture `:491` 还固定整份 linked IFC SHA，保存相机变化后可能再经 external dependencies 改变来源命名空间。

所以“不新增整个平面列表到 hash”仍不够。新增 P2 会增来源条目；移动 P2 会改相机事实；本轮未实跑 cache miss，但依赖链可以逐处复核。

修正必须同时保留完整 capture/freshness/认证证据，并明确**本包实际计算依赖的来源投影及跨 capture 的可信复用准入**。优先复用既有 source namespace、内容 key 与当前发布身份的分离；不要粗删相机、IFC SHA 或认证字段来换命中，也不要借此重写 CacheStore。若现有跨来源准入不能证明物理输入相等，宁可报告需重算；不得宣称已兑现“无关平面切换不作废数值缓存”。这项需在 spec 中给出可证伪的最小方案，才可进入实施计划。

### 中：冻结请求可独立，现有 Blender runtime 仍是单作业

`runtime.py:341`（均指 `blender_addon/order_analyzer_ui/runtime.py`）拒绝第二个 active job，`:355,401` 固定 payload/binding；UI `:732` 禁止运行时相机动作。运行中 depsgraph handler 在 UI `:2162` 早退，真正 freshness 由 runtime `:330,759,806` 的 native guard、会话和前后 observation 负责。

本期保持单作业锁即可满足不同包/请求顺序选不同平面。默认、覆盖在启动前解析；运行期间可禁用这些编辑。冻结后的任务不能再读可变 scene 默认；原生相机仍可能被外部操作改动，必须保留现有 guards，让结果拒绝作为 current，而非因 frozen dataclass 就宣称并发安全。不新增并发调度、多 scene job manager 或锁框架。

### 中：平面不等于域、剖切高度或结构基准

`features/scene_contract.py:496` 的 `AnalysisDomain` 承担有限范围；相机画幅、网格尺寸不能替代它。`analysis_requests.py:131` 将 slab datum 与平面高度换算成有限 band；`:500` 的 exact section 高度是绝对 world Z。`adapters/bonsai_live.py:68` 的 `StructuralContext.from_plane()` 则取 XY，结构 datum/cut 独立；当前 UI `:645` 特别构造固定 world-XY 的 B4 frame，不能随多平面 UI 悄然改语义。

域确认有两层：`analysis_requests.py:348` 会对调用者指定的 exact domain 做内部 confirm；它不是用户同意将 P1 区域用于 P2 的证据。live session `adapters/blender_analysis_session.py:1114` 和 UI `:672` 另查 retained consent/source/structural frame。切换后先按这些相容性条件判断；当前最小 UI 可继续撤销域确认并要求再确认。不能自动挪用旧 plane-local polygon、grid 或 consent，也不应把单纯 occupancy Z 改动误写为 B4 cut 改动。世界坐标事实可复用，不代表旧局部投影可直接复用。

## 3. 修正后的最小设计建议

**选择与传递。** scene/UI 只存平面目录、一个显式默认和各包的“跟随/指定”。启动时按“包显式选择 > 场景默认”解析一次，形成至少一个有效 `AnalysisPlane` 快照及选择来源；后续传入每个包调用，含 `evaluate()`、`process_output()`。这不要求把全部 scene/context 交给算法，也不意味着新增通用环境变量服务。AnalysisPlane 是本次共享基础属性，业务数据仍逐包声明。

**许可与错误。** 默认一个平面；空、重复/歧义身份、失效引用在计算前拒绝。多于一个同时要求显式特殊选项与本包能力声明；本期已有单平面算法维持单平面，不增加新公式。`FieldQuery` 和旧 `AnalysisRequest` 保持表达实际单平面计算的形状；不要把 list 塞进旧 singular 字段。

**不用就是不读。** 包作者可以不读取必传上下文，不需要通用的“代码是否访问参数”监视器或用户布尔开关。作者负责按实际输入声明依赖，现有 contract/query/上游 refs 校验间接依赖。解析器只处理引用和必要身份核验，不调用 executor、投影、scene view、网格或模型抽取。不能承诺成本为零：`bonsai_analysis_plane.py:145` 的唯一 native link 核验还可能遍历现有 Blender 对象；此为身份管理，不是数值分析。

**四种身份分开。**

| 层次 | 保留什么 | 切换一个真正无关平面的效果 |
| --- | --- | --- |
| 调用记录 | 跟随/覆盖、解析后的完整平面引用/快照、运行身份 | 新记录反映此次选择 |
| 数值内容 | 实际来源、实际投影/query、算法与有效参数、上游内容 | 不变；不得强塞所收但未用的 plane |
| 输出/发布身份 | 实际 target/frame/contract、当前 publication 绑定与内容摘要 | 按既有语义重建；不能统称不变 |
| 原计算来源与当前 freshness | 原计算证据及此次独立核验 | 保留原来源，当前状态重新判断 |

`features/field_core.py:1454` 已把 query plane 纳入数值 key，`:742` 的输出身份依赖来源身份；`features/free_space_evidence_package.py:76` 已分开 plane name/revision 与几何参数，`features/output_port_cache.py:70` 已有实际输入/上游依赖投影。复用这些机制，`ParameterImpact` 不是自动依赖分析器。加工一个旧 P2 raw 时，新传入的 P1 若完全未使用可以仅作调用记录；输出仍保留 P2 的实际来源和坐标。若加工宣称产出 P1 空间结果，必须满足 P1 配准，不能只改标签。

**跨平面结果。** 保留 `group_axis_potential_field.py:117,150`、`group_axis_output_ports.py:88`、`group_distance_output_ports.py:75,120` 对成员、query、原点和几何 registration 的检查。选择了同样的 UUID 不是相容证明；平面不同也没有自动转换承诺。

UI 文字示意即可：`场景默认：P1；势包：跟随场景 → P1；距离包：指定 P2`。另显示“本次已固定 P1/P2”和实际结果坐标来源；不把“输入平面”冒充“算法已经使用”。

## 4. 生命周期与兼容边界

| 场景 | 本期必要行为 | 可复用事实/位置 |
| --- | --- | --- |
| 新建、采纳、切换 | 独立 native drawing；按 project/GUID 精确选择；逐身份保留 observation，切回不重置 | native adapter `:188,454,584`；UI `:745` |
| 修改 pose/高度 | refresh 后形成相符快照；相关数据/域按真实依赖失效；历史结果保留 | adapter `:196`；UI `:712,759` |
| 重命名、画幅变化 | GUID 不变；标签独立；不当作平面几何尺寸或无理由涨 pose revision | adapter `:207,215`；`test/test_bonsai_analysis_plane.py:196` 有相应用例，未重跑 |
| 删除/替换/复制冲突 | 指定引用失效则明确拒绝；不静默改默认、换包覆盖或换 native UUID | adapter `:134,230` |
| 保存/加载 | 保留目录、默认、覆盖和观察记录；重新核验 native；不恢复 reviewed/current/域同意 | UI `:2073,2135`；reviewed 为 SKIP_SAVE；adapter `:648` 可恢复缺失 camera object |
| IFC-only 重开/导入 | 按 IFC marker/GUID 找回原生平面；设置记录若不可恢复，明确要求重新选择；多个时不猜默认 | 持久 native truth 与 scene/UI 设置是两类记录，不承诺任意导出链自动携带默认值 |
| undo/redo | 恢复设置后重验身份/完整 pose，撤销过期 review/域/任务；不能只信 uuid/revision | UI `:2148,2189` 有 undo/load，当前没有 redo_post；redo 需明确覆盖 |
| 运行中设置/原生变化 | 保持现有单作业锁和前后 guard；已冻结任务不随默认漂移 | runtime `:341,759,806` |

不需要本期实现自动修复/替换平面、批量删除、自定义改名系统、任意倾斜计算、并发任务、新多平面数值算法或跨平面融合。原生保存/重开已有历史基础，不等于新列表生命周期已经验收。

兼容的最小承诺：

- 既有**单平面**计算、公式、原始数据和返回形状继续可用；旧调用若能从唯一可信上游平面做适配，可以在明确兼容入口解析并传入。真正无平面且无显式默认上下文的旧调用必须迁移；不能因“兼容”放弃用户已确认的必传门。
- `scene_contract.py:157`、`adapters/blender_analysis_result_wire.py:92,372` 和 `field_core.py:1146` 的读取均有严格形状校验。保留旧 singular request、raw/processed v1、ResultRefs 和既有 fixtures 原字节。新选择记录优先放现有外围运行/设置记录；确需新 wire 形状时明确版本及双读，不给历史文件回填今日默认值。
- 新版本代码哈希改变可能使历史缓存需要现有独立 adoption 验证。区分升级造成的一次兼容检查与平面切换造成的无关数值失效；不删除缓存或凭相同 key 直接认 fresh。
- 回退优先保留单平面 UI/执行路径；旧软件面对多个受管平面可能仍会拒绝。不得承诺完整降级可写，也不要为回退删除新增平面或历史结果。

影响面至少包括：`field_core` 输入/发布/加工入口；geometry/trend 的 query 门；axis/distance combined 与 semantic ports；free-space adapter；native plane/capture/live/session/wire；UI 请求、Space sketch/Region 保存（`adapters/bonsai_space_authoring.py:287`）及 lifecycle handlers；对应 `test_*`、真实 runner 和旧 fixtures。现有 root/features `__init__.py` 没有导出这些 request/plane 类型；不因新增入口引入 Blender/数值后端 eager import。没有发现新增依赖、配置框架或公共 room model 形状改动的必要。

## 5. Readiness 与最小推进阶段

**Verdict：需要先补 spec；无已知根本不可行项，无待用户继续裁定的语义阻塞。** 尚不能直接进入实施计划：统一必传门及迁移、原生多身份生命周期、真实输入配准、跨 capture/namespace 的数值依赖投影，均未形成可验收契约。A/B/C 的既有验收不覆盖这些新增义务。

1. **补一份短 spec。** 固定上述入口/兼容边界、选择优先级、冻结时点、逐身份 observation、数量/能力/角色、四种身份与域确认规则；画清 capture → source namespace → 数值 key → publication 的现有链和最小复用准入。同步更新现有架构图/包规范应留给未来获得写入授权的阶段；本审查不改它们。完成门：每个反例均有确定的拒绝、重验或复用结果，不能写“届时自动处理”。
2. **制定最小实施计划。** 按共享输入/兼容与缓存投影、原生目录/UI 生命周期、现有包适配/集成拆成可单独检查的改动；为每步列实际 callers、测试与旧数据边界。原生工作可能影响 capture/namespace，不能排到数值验收之后才发现。此报告不为这些工作授予实施权限。
3. **未来实施与验收。** 先做非空间契约/历史字节与定向缓存验证，再做已批准真实 IFC 的 native/UI 空间验收；继续 Pixi，Blender 仅用 AGENTS 指定 portable 安装。未获授权不启动大测试、IFC 重算或版本写入。

真正多平面算法可等一个具体包需要时再设计；本期仍须有显式许可/能力校验，并证明现有单平面包不会被开关绕过。延后算法不等于删除多平面调用契约。

## 6. 未来验收矩阵与维护清单

以下全部是**待实施验收项**；本轮没有将它们判为通过。契约检查可复用既有真实上下文/非空间哨兵，不制造新布局、IFC 或空间模拟数据。空间检查仅用项目已经批准的指定真实 IFC，并固定来源/代码/结果身份。

| 验收组 | 必须观察到的结果 |
| --- | --- |
| 必传门 | evaluate/process_output/combined/semantic/run 入口均收到非空上下文；默认代传有效；空/无来源/歧义在算法前拒绝；算法可以完全不读参数 |
| 数量/能力 | 默认一个；两平面未许可拒绝；已许可但单平面包仍拒绝；不把两次单平面执行称为一个多平面算法 |
| 零额外计算 | 真正无平面依赖的算法在改默认/覆盖后，投影、网格、模型抽取 producer 调用数仍为零；只发生必要引用解析/身份管理 |
| 选择与隔离 | 默认 P1、包 A 跟随、包 B 指定 P2；改默认只影响随后解析的跟随调用；冻结任务及显式覆盖不漂移；P1→P2→P1 observation 不重置 |
| 防错平面 | 包声明输入角色或空间输出属于 P1 时，拒绝 P2 投影及不相容 frame/原点/成员；未参与加工的 P1 只记调用上下文，结果继续标明实际 P2 来源/坐标，不能重贴 query |
| 缓存 | 可独立证明只改变未使用分析相机/默认/覆盖时，P1 数值内容可按可信准入复用，含该类修改后的保存；物理事实或真实外部依赖变化不承诺复用；使用 P2 的输入变化必须失效；恢复旧有效输入可找回历史；原来源与新调用审计并存 |
| 域与高度 | 精确 shell/holes、world→local 只转换一次；域 consent 不跨不相容 frame 挪用；slab band/exact Z/B4 datum-cut 独立；不支持 tilt 明确拒绝 |
| 原生生命周期 | 创建两平面、明确采纳/选择、改名/改 pose、删除/重复链接、保存加载、同 GUID 恢复、undo/redo；失效不静默换平面，历史结果仍能精确读回 |
| 作业一致性 | 第二 native job 仍拒绝；运行期原生修改触发现有 freshness 门；不能以旧 frozen 结果发布 current |
| 兼容/回退 | 旧单平面 API 适配、raw/processed v1/ResultRefs/保留 fixtures 字节不变；未知新字段/版本不误读；旧单平面回退限制明示 |

持续维护 checklist（未来使用，均未勾选）：

- [ ] 新增包同时说明必传上下文、实际 plane/query/上游依赖与支持数量；不靠 `uses_plane=False` 抹掉投影 lineage。
- [ ] 变更 native/capture/source binding 时复核未选相机是否进入数值 key、namespace 或 adoption 门。
- [ ] 默认/包覆盖/域/高度规则改动时核对实际 callers、UI 表示、历史读取与架构图；不把新语义写成已有事实。
- [ ] 生命周期或 wire 改动覆盖 load/undo/redo、失效引用、旧结果与 strict decoder；保留来源认证和已有事务恢复。
- [ ] 以实际执行记录区分契约通过、数值通过、native/UI 通过；不复用超出来源/平面/代码范围的旧验收结论。

## 7. 报告自检与边界

已核验要求的八类问题：共享机制、原生生命周期、输入/能力门、真实依赖与缓存、请求独立/作业锁、域/高度/配准、兼容与回退、readiness/推进路线。用户追加澄清已纳入；不保留已回答问题为阻塞。

本轮只新增本文件。只读使用安装的 jj（`--ignore-working-copy`）和代码/文档读取；忽略 working copy 的 status 可能陈旧，不据此声称 owner 磁盘无未提交修改。未执行 jj/Git 历史写入、其他 chat 消息、实现、测试套件、Blender、IFC 重算、联网研究或依赖安装。Pixi 自检核对 26 个完整路径/行号引用、未勾选的未来清单及 220 份既有代码/文档哈希不变；两个只读复审另核对包/缓存与 UI/native 事实，发现的验收表述歧义已修正。这些检查不构成功能验收。

已省略 UI 原型、通用注册/调度/访问追踪框架及新算法。主要剩余风险是来源认证与计算依赖的分离尚未定 spec，真实 native 生命周期和缓存独立性尚未实测；本次审查结束后不自动进入实施。
