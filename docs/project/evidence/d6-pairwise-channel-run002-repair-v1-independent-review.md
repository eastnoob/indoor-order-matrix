# D6 pairwise channel run_002 repair_v1 independent review

审阅日期：2026-10-03。审阅分支：`codex/d6-pairwise-channel-run2-repair-v1`。

审阅 HEAD：`f25d3674226fe08ffb56013cb2962267e0de0114`；修补提交的父提交：`de1c53b478e3bb21a7fe2f1e3c24e83ea2ec38a1`。

**裁决：`REVISE`。当前保存的 12 个 synthetic fixture 数值仍可用作 limited design evidence；完整 repair 验收和 implementation design 暂不通过。** 允许下一轮有界设计修补/实验，以澄清下述字段、资格检查和视觉对应关系。本审阅不批准 production selector、固定阈值、route width、walkability、Bayesian/ML、production API 或 production implementation。

本次只读检查 repair bundle，并对照原 run_002、run_001、输入契约和上一份独立审阅。项目内唯一新增文件是本文。所有重跑、图像转换、Blend 回读结果和审查脚本均写入系统临时目录；内存探测没有保存为实验 fixture。没有运行会写回原 bundle 的 `validate.py` main、没有保存 Blend、没有执行任何 `git add`。

## Blockers

### B1 — 墙的资格筛选没有用于实际 occupancy union

[run_experiment.py:458](D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/run_experiment.py:458) 将原始 `fixture["walls"]` 直接交给 `_union_audit`，只有柱来自 `eligible_obstacles`。因此，墙的 excluded reason 和实际几何占据可能矛盾；baseline occupancy 同样传入未经筛选的墙。

只在内存复制 `no_column`，加入 Level 2 墙 `review:level2:wall`，几何为 `(5.8, 0)–(6.2, 8)`：它被记录为 `known_other_floor_exclusion`、`effect=excluded`，但仍出现在 `occupancy_union.source_ids`，把原本的 `computed_same_component` 改成 `computed_disconnected`，组件数从 1 变成 2。它没有造成 partial，却仍错误改变了结果。

现有 12 个 fixture 的墙全部合格，所以保存结果的复算通过；当前 other-floor fixture 只覆盖柱。这是 runner 可复现的资格传播缺口，不能把当前通过结果推广为墙柱统一资格检查已完成。

### B2 — 有 domain 记录但无可用 domain 几何时仍报告 computed

[run_experiment.py:459](D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/run_experiment.py:459) 只把缺记录识别为 `domain is None`。存在记录但没有 geometry parts 时，`_geom` 返回空 Polygon；后续仍计算差集、profile 和 connectivity。

内存复制 `no_column`，仅将 domain 的 `geometry_parts` 清空：candidate validity 为 `invalid`，但 candidate set、profile 和 global empty space 都为 `computed`；connectivity 为 `computed_disconnected`、component_count 为 0。这没有遵守输入契约中 domain record、geometry refs 和 geometry validity 必须分别满足的资格要求。不可用 domain 不应被序列化为已计算的空拓扑。

现有 `missing_analysis_domain` fixture 的三个依赖状态确实都是 `not_available`。本 finding 是缺几何资格的边界行为，不能误写成现有 missing-record fixture 失败。

### B3 — 视觉与已保存几何的对应关系尚未修好

直接查看保存 PNG、离线栅格化保存 SVG，并从保存 Blend 回读和重新渲染后，确认四项限制标签完整，`candidate:01`、`candidate:02`、`selection: none` 的文字彼此没有重叠或裁切。但存在以下实际问题：

- JSON 的 multiple candidate 几何分别位于 `y=2.35` 和 `y=4.85`。[render_visual.py:59](D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/render_visual.py:59) 的 `candidate_01_support` 实际位于 `y=3.6`，`candidate_02_support` 位于 `y=2.55`。Blend 中央面板 offset 为 14，回读对象坐标确认这不是图像缩放误差。候选标签也没有引线或图例把 ID 明确对应到线段。渲染使用独立硬编码，未消费保存的 candidate geometry。
- SVG 的 disconnected 墙范围为 `y=205..505`，面板框范围为 `y=125..555`。若框被读作 domain，图中墙两端都有通路，不能展示标题声称的断连；若框仅是展示卡片，图中又没有单独画出 domain。墙还穿过 `y=495` 的 `profile: computed` 文字。Blend 中对应墙接到 domain 上下边界，两种视觉表达不一致。

`synthetic fixture diagnostic` 和其余三个限制声明明确阻止了真实 IFC、route width、walkability 的推论，但不能修复同一 synthetic fixture 内的几何/状态对应错误。当前图可证明标签存在，不能作为候选几何或断连拓扑的可靠回读证据。修补验收应能对照序列化几何，并消除上述歧义；本次没有修改图像或生成脚本。

## Important findings

1. **候选层的 selection 修补有效，但还不是唯一序列化位置。** 全部 12 个 candidate set 都保存 `selection.selected_candidate_id=null`、`selector="none"`；12 个实际候选均没有 candidate-level `selection`、`selected_candidate_id`、`selector`、`accepted`、`winner` 或 `chosen` 字段。`schema.json` 的 selection contract 也已移到 candidate-set 层。multiple set 保留两个候选并保持 `ambiguous`，没有隐式 winner。不过 [run_experiment.py:422](D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/run_experiment.py:422) 仍将 selection 复制到全部 12 个 free-space profile。当前副本与 set 完全相等，没有现存冲突；若“统一位于 candidate_set.selection”要求唯一位置，则尚未完全满足。进入 consumer 设计前应明确这些副本是只读回显还是需要移除，并校验一致性。

2. **四类 provenance 已拆分，当前 basis 的实际身份可核对。** 所有候选都有 `support_basis_source_ids`、`candidate_geometry_source_refs`、`physical_occupancy_source_ids`、`excluded_source_refs`，并附 role、source kind、level。独立检查确认当前 basis IDs、support refs IDs、geometry refs IDs 一致，且没有与 excluded/context 混放。missing、invalid、Level 2 柱均保留在 excluded refs，未被当作 support。

3. **候选 occupancy context 不是完整的 connectivity 输入清单。** multiple fixture 中，每个候选的 support basis 包含各自的一面墙，但 `physical_occupancy_source_ids=[]`；全局 `occupancy_union.source_ids` 实际包含两面墙和两个家具组。当前计算确实没有漏墙，因为它使用全局 union。审阅可跨文件还原事实，但 consumer 不能把候选的这个字段当作完整 occupancy 输入。support 源可同时在全局具有事实 occupancy 角色；应明确字段表示“额外候选上下文”还是“完整占据集合”，而不能依靠强制 ID 不相交隐去真实双重角色。

4. **结构化 partial 原因修补有效。** `fixture:missing:c1` 和 `fixture:invalid:c1` 可按 source_id 查询，分别有 `missing_geometry`、`invalid_geometry`、`scope=in_scope_obstacle`、`effect=partial`。它们在 source exclusion 清单和依赖 estimand 的 partial 清单同时出现，是两个用途的同一原因记录，没有造成双重占据扣除。Level 2 柱有 `known_other_floor_exclusion`、`effect=excluded`，partial 清单为空，profile/connectivity 不因它变成 partial。

5. **已保存 fixture 的 connectivity 真正独立于 selection。** 独立从 fixture source polygons 重建合格障碍、union 和 domain difference，复算面积、组件及家具边界的组件标签，全部与 evidence 一致。将 `_connectivity` 的 candidate IDs 在内存中换成空列表或无关 ID，只改变追踪元数据，不改变状态、面积或组件。multiple 的 profile/candidate evidence 为 `ambiguous`，connectivity 仍为 `computed_same_component`。disconnected 保持 `computed_disconnected`、2 个组件。0.24 m² 的柱/家具重叠和 0.15 m² 的墙/柱重叠各只扣一次。

6. **membership 与语义边界保持。** 对照原 run_002，domain、furniture group nodes、candidate coordinates、occupancy union、global empty-space 数值、boundary gap 和 connectivity 状态/标签均未改变。家具组仍是两个节点，member_count 分别为 2 和 3；没有创建 virtual wall、改 membership 或选择 partition。墙在 multiple synthetic fixture 中还被用作 wall-band 候选构造参考，这是明确的 synthetic 派生几何，不能升级为真实空间分区。柱行仍为一个连通分量。scene frame 未用作 AnalysisDomain。

7. **真实 IFC 边界正确保留。** `real_ifc_audit.json` 为 `adapter_rerun=false`，candidate support、profile、connectivity 全部为 `not_available`，production conclusions 为空。boundary gap 只标为已有几何 gap evidence。没有 live adapter 或 mesh extraction 重跑，没有把 synthetic 数值写成真实 IFC 推论。源 IFC 的实际 SHA-256 与 provenance、audit 和 manifest 一致。

8. **validation 的通过声明超出实际覆盖范围。** [validate.py:297](D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/validate.py:297) 写入 `json_schema_checked=true`，但 main 没有使用 `schema.json` 做完整结构验证。内存负向检查表明，删除候选 geometry、给 basis 添加不存在的 source ID、或把 single fixture 的 candidate_count 改成 999，相关 selection/provenance 检查仍通过。`component_checks=true` 也没有对应的组件复算；global diff pass 和 artifact hash checked 是报告构造中的声明，不能代替实际命令和重算。这些缺口已由本次独立检查补足当前快照的事实验证，但没有使原 validator 成为可冻结的完整契约验证器。

关键状态复核如下；partial 行的组件只是可用几何的诊断观察，不是完整拓扑结论：

| Fixture | Candidate evidence | Profile | Connectivity | Components |
|---|---|---|---|---|
| multiple_candidate_channels | ambiguous / 2 candidates | ambiguous | computed_same_component | 1 |
| disconnected_components | computed | computed | computed_disconnected | 2 |
| missing_analysis_domain | not_available / 0 candidates | not_available | not_available | 未计算 |
| missing_invalid_column_geometry | computed support | partial | partial | 1，诊断观察 |
| different_floor_column | computed | computed | computed_same_component | 1 |
| column_row_open_gap | computed | computed | computed_same_component | 1 |

## Minor findings

- `schema.json` 是 declarative contract 清单，缺少标准 JSON Schema 的结构/type/required 定义，也没有完整声明四类 provenance 和 reason-record 形状。可以作为设计说明，不能把自定义断言的通过叫作标准 JSON Schema 验证通过。
- [inspect_blend.py:24](D:/PROJECTS/understandOtherPackage/order_analyzer/outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/inspect_blend.py:24) 的 `text_positions` 以文字 body 为 key，却查询对象名 `title_multiple`，因此该检查与默认 y=0 比较。本次实际查看证明 warning 位置确实高于标题，但现有布尔检查本身没有证明这一点，也没有检查字形范围或几何遮挡。
- PNG 的警告和候选文字完整、未裁切，但在 1800×760 全图上字号小、对比弱，缩小展示时难读。没有发现文字之间重叠；SVG 中 profile 与墙图形相交已单独列为 B3。
- `independent_scope_audit.json` 由同一 runner 生成，多个 preservation 字段是声明。其名称不意味着已经由独立审阅者产生。本次另做 Git、manifest 和文件快照核验。
- repair manifest 明确自排除，22 个列项覆盖其余全部 repair 文件。原 run_001/run_002 目录还含既存、未列入各自 manifest 的 review/reproduction 文件；本次没有删改它们，保留性核对没有只依赖 manifest。

## 独立验证证据

- 14 个 JSON 严格解析通过：无重复 key，无 JSON NaN/Infinity。逐项检查 candidate 必需字段、计数、ID 唯一性、非空/有效几何、domain containment、source refs 和上述状态。所有已保存候选的这些检查通过。标准 JSON Schema 验证不作已完成声明。
- 只读调用 validator 的 8 组 `_check_*` 函数通过；没有调用其写回 main 或 `_write_manifest`。随后独立重算，而非只引用报告。
- 临时目录 deterministic rerun：11 个核心 JSON、两个 Markdown、一个 SVG，共 14 个文件，bytes/SHA-256 与保存产物一致。未重新生成或覆盖实验 PNG/Blend。
- 独立重算 repair manifest 的 22 个条目、原 run_002 的 21 个条目和 run_001 的 18 个条目，bytes/SHA-256 全部匹配。
- 保存 PNG 实际打开并局部放大查看；保存 SVG 通过本地 `svglib`/`reportlab` 栅格化后实际查看。浏览器因 file URL 安全策略拒绝直接打开 SVG，未绕过该策略。
- 使用指定 portable Blender 回读保存 `.blend`：45 个对象、全部必需文字，独立 readback 的 JSON 内容与保存 readback 一致。另渲染保存 Blend 到系统临时目录后实际查看；全部像素与保存 PNG 相同。PNG 文件字节不相同，差异来自 `Date`、`RenderTime` 元数据，不把这次渲染称作字节确定性通过。
- 核验期间 556 个基线文件的 bytes/SHA-256 保持不变，范围包括三个 run 目录及其既存 reproduction 文件、features、adapters、test/tests、既存 evidence、输入契约、指定源 IFC、入口与 Pixi 文件。既存 untracked evidence 保留；本轮新增范围只有本文。

| 文件 | Bytes | 实际 SHA-256 |
|---|---:|---|
| candidate_evidence.json | 64084 | 2ae3d1141bf9420f3d822ed143e02536ee5b834de18f714da82643802028c55e |
| connectivity_evidence.json | 9886 | d0d4b160fa5ec86d7f041d680bc8a98364b7ed9760fd05cf620b8df7e5f87112 |
| pairwise_diagnostic.json | 80755 | d23a661ea754a1d641d7f575360247f37a4388c5b36f5cdf23811243332231c3 |
| 保存 PNG | 742766 | ad48530d77305e388170ed61d05a81c1fdbbc688162b2ada9cf05e9640bd3ff5 |
| 保存 Blend | 115316 | 90beb12814acf74b90e6d2512acc893fc8faa29558ad9f16170124fa19e3048f |
| 输入契约 | 23822 | b8870bd8f5a1e4be60ac42a7a5a7792ff43b9cc43b5e628aaccd580a40dfca6d |
| 指定源 IFC | 408617800 | 018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240 |

## 未验证事项与裁决边界

没有验证 live IFC 的新 domain、完整 geometry extraction、opening/door 语义、真实 profile/connectivity、通行性或路线宽度。没有批准候选选择算法、阈值、采样分辨率、生产布尔后端、ML/Bayesian 模型或 API。0.5 m 网格和 21 个 profile sample 只是保存的实验设置。

B1/B2 是临时内存探测，不是新增到 repair manifest 的正式 fixture；其他复杂拓扑、洞、多平面、unknown floor、非有限/非法 domain、组合 partial+ambiguity、一般无效墙和生产规模未全面验证。候选集合“完整”只指 runner 枚举的集合完整保留，不证明列尽真实 IFC 的所有候选。

没有定位或访问当前用户打开的 Blender 工程，也无法核实未提供路径的文件或未保存内存状态。实际 Blender 命令仅打开指定 disposable Blend，没有 save 操作；该文件审阅前后 hash 相同。不能据此声称所有用户 Blender 文件都做过独立 hash 审计。

原 run_001、run_002 和源 IFC 被 `.git/info/exclude` 的 `outputs/` 规则忽略；repair 的 23 个文件已经在 HEAD 中跟踪。旧产物当前 manifest 和本次前后 hash 一致，但 Git 不能证明忽略文件在修补提交之前的历史完全未变。本文只报告可核实的当前一致性和本轮保留性。

**是否允许 implementation design：否。** 原数值证据的通过不抵消 B1/B2 的资格缺口和 B3 的视觉对应问题。selection 镜像、occupancy context 语义与验证覆盖也需要在后续有界设计中明确。本轮到独立审阅为止。

## 实际命令和 Git 范围

工作目录均为 `D:\PROJECTS\understandOtherPackage\order_analyzer`。实际读取 `AGENTS.md`、architecture memory、用户列出的重点文件，并补读 repair 的 schema、real_ifc_audit、runner、validator、render/inspect 脚本、blend_readback、experiment/fixture/scope 文件。只发现根目录 AGENTS.md。

应用了 [verification-before-completion/SKILL.md](C:/Users/tianf/.codex/plugins/cache/openai-api-curated/superpowers/5fd93af4/skills/verification-before-completion/SKILL.md)，以本次命令和实物回读支撑结论。

以下是实际执行的主要命令。系统临时目录变量对应本次真实路径；Python 脚本通过 `-B` 禁止向项目写入 bytecode：

```powershell
Get-Content AGENTS.md
rg --files -g AGENTS.md -g '!OCTA_toolbox-master/**' -g '!**/.pixi/**'
Get-Content docs/indoor_layout_evaluation_matrix_architecture_memory.md
git branch --show-current
git status --short
git log -6 --format='%h %s'
git show --stat --oneline HEAD
git rev-parse HEAD HEAD^
git diff --name-status HEAD^ HEAD

$reviewTemp = 'C:\Users\tianf\AppData\Local\Temp\d6_repair_independent_review_9le2v6dl'
pixi run python -B "$reviewTemp\read_only_audit.py"
pixi run python -B outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/run_experiment.py --output "$reviewTemp\deterministic_rerun"
# The preceding runner command was invoked by read_only_audit.py as a subprocess.
```

`read_only_audit.py` 实际做 JSON 解析、8 组只读 validator 检查、独立几何重建/union/difference/组件核验、三份 manifest 重算、14 项临时重跑比较、原 run_002 数值对照，以及只修改内存副本的 validator 负向探测。其他实际 `@'... '@ | pixi run python -B -` 片段做严格 JSON 解析、B1/B2 内存探测、SVG 栅格化、PNG 像素比较和 556 文件前后 hash 核对；不向项目目录输出这些探测。审查辅助片段的初次执行曾因 wrapper key/Windows 路径 key 导致 KeyError，纠正后通过；PNG 字节相等断言未通过，随后独立确认像素相等而元数据不同，已如实区分。

```powershell
& 'D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe' --background 'D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\space_field_pairwise_channel_experiment\run_002_repair_v1\pairwise_channel_disposable.blend' --render-output 'C:\Users\tianf\AppData\Local\Temp\d6_pairwise_blend_render_review\blend_render' --render-frame 1

& 'D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe' --factory-startup --background --disable-autoexec --python 'D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\space_field_pairwise_channel_experiment\run_002_repair_v1\inspect_blend.py' -- --blend 'D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\space_field_pairwise_channel_experiment\run_002_repair_v1\pairwise_channel_disposable.blend' --output "$reviewTemp\independent_blend_readback.json"

git diff --no-ext-diff --check HEAD^ HEAD -- outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/
git diff --no-ext-diff --check -- outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/
git diff --cached --no-ext-diff --check -- outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1/

git status --short --untracked-files=no -- features adapters test tests analyzer.py __init__.py docs/project/space-field-ifc-neutral-scene-input-contract.md outputs/design/space_field_pairwise_channel_experiment/run_001 outputs/design/space_field_pairwise_channel_experiment/run_002 outputs/design/space_field_pairwise_channel_experiment/run_002_repair_v1 outputs/full-rhino-ifc-2026-09-23
git diff --name-only HEAD^ HEAD -- features adapters test tests analyzer.py __init__.py docs/project/space-field-ifc-neutral-scene-input-contract.md outputs/design/space_field_pairwise_channel_experiment/run_001 outputs/design/space_field_pairwise_channel_experiment/run_002 outputs/full-rhino-ifc-2026-09-23
git check-ignore -v outputs/design/space_field_pairwise_channel_experiment/run_001/artifact_manifest.json outputs/design/space_field_pairwise_channel_experiment/run_002/artifact_manifest.json outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc
```

三个 repair-only diff-check 均 exit 0、无诊断。受保护 tracked paths 的 status/diff 无输出。父提交到 HEAD 的变化只有 repair 目录内 23 个新增文件；本次工作区没有 tracked 修改、没有 staged 修改，也没有生成 production 实现。本文新增前已有的 untracked evidence 全部保留。

STOP FOR PAIRWISE CHANNEL RUN_002 REPAIR INDEPENDENT REVIEW
