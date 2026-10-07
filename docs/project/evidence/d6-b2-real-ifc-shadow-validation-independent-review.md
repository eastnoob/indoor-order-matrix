# D6 B2 Real IFC Shadow Validation 独立审查

- 审查日期：2026-10-07（Europe/Berlin）。首次 checkout 记录时间：21:01:53 CEST。
- 建议：**ACCEPT LIMITED REAL-IFC SHADOW DIAGNOSTIC EVIDENCE**。
- 阻断项：**none**。接受范围限于现存 source identity、inventory、继承投影上的诊断观察及 serialized-evidence 可视化。
- 角色：独立证据 reviewer；没有编写、修复或重跑实验。
- 本次唯一新增文件：本报告。目标路径在审查开始时不存在，无需 revision 替代。

## 1. Reviewed snapshot 与方法

实际分支为 `codex/d6-analysis-domain-layout-handoff`；实际 HEAD 为
`82d08fe54cf58be519bad6187e1f2f9e499453d5`。初始 `git status --porcelain=v1`
包含 **5 个 modified、56 个 untracked**，没有 staged 项。5 个既存 modified 文件为：

- `features/neutral_scene_views.py`
- `test/test_blender_geometry_adapter.py`
- `test/test_group_self_description.py`
- `test/test_neutral_scene_analysis_regression.py`
- `test/test_svg_scene_adapter.py`

shadow 原报告、implementation owner decision、implementation plan/review 等已有文档在 untracked
基线中。`outputs/` 由 `.git/info/exclude:13` 本地排除；因此采用当前 local checkout 读取证据。
原报告的「44 个既存 untracked」是原实验的历史自述，不是本次基线，也不能由本次状态重建。

已先读 `AGENTS.md` 与 architecture memory。已实际读取并使用
[`verification-before-completion` SKILL.md](C:/Users/tianf/.codex/plugins/cache/openai-curated-remote/superpowers/6.4.2/skills/verification-before-completion/SKILL.md)，
以 fresh read-only 输出支持结论；没有以历史 `validation_report.status=pass` 替代独立检查。
没有调用 pytest、IfcOpenShell model loader、adapter、tessellation、geometry pipeline、Blender 或 live Blender MCP。

本次实际执行的检查命令/工具如下；inline Python 较长，仅列实际 invocation 及检查内容，不把它冒充保存的审查脚本：

| 实际命令或工具 | 用途与输出 |
|---|---|
| `git branch --show-current`; `git rev-parse HEAD`; `git status --porcelain=v1` | 初始、中途、收尾 checkout/status 对比 |
| `git diff --numstat`; `git diff --cached --numstat` | 5 个既存 dirty 文件；cached 无输出 |
| `git check-ignore -v outputs/design/d6_b2_real_ifc_shadow_validation/artifact_manifest.json` | 确认 `.git/info/exclude:13:outputs/` |
| `Get-Content -LiteralPath ...`; 带行号的 `Get-Content`/`ForEach-Object` | 阅读指定报告、JSON、runner、render/readback helpers 及有关 provenance 源码 |
| `Get-Item -LiteralPath ...`; `Get-FileHash -LiteralPath ... -Algorithm SHA256` | 全部 14 manifest entries、manifest 自身、原报告、source IFC 的 bytes/hash；收尾重复 |
| `rg --files --hidden --no-ignore outputs/design/d6_b2_real_ifc_shadow_validation outputs/design/live_ifc_input_mapping_probe outputs/design/live_ifc_boundary_candidate_comparison` | 有界查找 artifacts/logs；shadow 没有完整运行日志文件 |
| `rg --files docs/project/evidence \| rg 'contract-closure\|live.*input.*mapping\|input-mapping\|shadow'` | 有界查找缺失的 owner decision 等 provenance 路径 |
| `git show 9b50bb1f44c0ae7dc2807c17da084d1ab8163393:docs/project/evidence/d6-contract-closure-owner-decision.md` | 读取缺失 checkout 文档的确切 historical Git equivalent |
| `Get-Content -LiteralPath outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc -TotalCount 12` | 只读 header；确认 `FILE_SCHEMA(('IFC4'))` 和 `.MILLI.,.METRE.` |
| `pixi run python -B -c '...'`（只读 inline 检查） | 9 JSON 解析；saved IDs/roles/support/occupancy/component 字段断言；跨 provenance copy/hash 对照；33 个对象的 GlobalId/STEP/name/ObjectType 对照；XML 解析；PIL `Image.load()` 解码。全部 exit 0 |
| `view_image(...candidate_comparison.png, detail="original")` | 实际查看现存 2200 × 1400 PNG pixels |
| `git diff --check`; `git diff --cached --check` | 均 exit 0；无 whitespace 输出或 permission failure |

上述检查没有计算新的 Shapely validity、union 或 contact；核对的是保存的观察、引用关系和产生这些观察的代码。
新报告写入前，另在工具内存中保存了 61 个既存 dirty/untracked 文件的 hash，以及 25 个相关输入文件的 bytes/hash，供收尾比较；没有写额外脚本、manifest 或 checkpoint。

## 2. Fingerprint 与 manifest 检查

证据根目录为 `outputs/design/d6_b2_real_ifc_shadow_validation/`。
manifest 没有独立 `root` 字段；其 `entries.path` 为相对于 OUT 的路径。
这与 `run_shadow_validation.py:18–19, 862–880` 的 `OUT = runner.parent`、
`path.relative_to(OUT)` 及原报告指定的 artifact folder 一致，故逐项按 manifest 所在目录解析，
没有把 `blend_readback.json` 等错误解析成 repository cwd 下文件。

| 文件 | 现存 bytes | 本次 SHA-256 |
|---|---:|---|
| 原报告 `docs/project/evidence/d6-b2-real-ifc-shadow-validation.md` | 6493 | `f708905a221feaae7d39142a65b6840c582d6bd927a9ca117de9df6de2937ddf` |
| `artifact_manifest.json` | 2490 | `76e39781da78bd66c7f6a5bc60f841b22179f759f9d32c20560e23cb4a980e45` |
| source IFC | 408617800 | `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240` |

source IFC 位于 `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`，
本次可访问；现存 size/hash 与 inventory、shadow provenance、input-mapping provenance、
boundary-candidate provenance 一致。没有 source-inaccessible 限制。

以下 **14/14** entries 的 bytes 与 SHA-256 均 fresh 重算并匹配；missing=0，mismatch=0。

| Artifact | bytes | SHA-256 |
|---|---:|---|
| `blend_readback.json` | 1759 | `604ab9f3c351ef1f0f0c77ba2c950349da3dbde886e15aab55c5ddffef2af583` |
| `boundary_candidate_shadow_results.json` | 19825 | `292a614ab66c1ad3cab5ea2e4b8bf173fa70d95311ecdc1c6a8eb431e8ca5ef2` |
| `candidate_comparison.blend` | 135209 | `015c65634950119a31a06e341b50900750bdd9d970d482ebc8543f524ed67712` |
| `candidate_comparison.json` | 1393309 | `93d06638601088b6ba8751be3f2e7a7a479edefd4fd9c682d5da4f0046b3ad87` |
| `candidate_comparison.png` | 3129543 | `c5bacb7a9997814fe2d352d3a5df4a28118a1a58222bda14b4dfcc35cd2f67f6` |
| `candidate_comparison.svg` | 196358 | `4696e7a8d4535cb48c039c41e79b5bc0a9ee196bdf86f585733995cccf50dd84` |
| `candidate_diagnostics.json` | 47348 | `67222d7c681cca85782af1bbf75b6e6f39459d530fbdeb2ca35539d03cfa702e` |
| `provenance.json` | 2863 | `6712969769df0b611a71dd50a20956672a89ab21f736b5c1829f3dbfa9b08ed4` |
| `readback_blend.py` | 3375 | `9161ae53494b7d9874fc6c33c86dc2a0bcdaed0a9ee7a8a66378eb71a10e873b` |
| `real_ifc_inventory.json` | 14154 | `d0e805c29de992ef1cc79791baddffd2053755adc0d98f702745a02e62e181e5` |
| `render_candidate_comparison.py` | 16322 | `f6d20550e858f3bbd5b0899ccc7e1d6e052a56f1800afb4cf51a94d79ee0f737` |
| `run_shadow_validation.py` | 39401 | `6e8cbccc7e16bb8675d630be82f79b0093a042766823645576355cf7bf7da662` |
| `source_geometry_snapshot.json` | 816923 | `bbe70f83703ae7e961c04367d3c8a0c0414271fad430000d10254ca96cbabed2` |
| `validation_report.json` | 3773 | `b06952c33bcba41cd70b7999824ec417f95bc0d662cf13972bca06a2023f8ae0` |

manifest 自身依声明排除；本报告也不纳入原 manifest。现存目录有 9 JSON；均解析通过。
`validation_report.json.json_parse` 只列 7 个前置 JSON，另外两个是 validation 和 manifest 自身，
与原报告「9 JSON」并不冲突。

boundary-candidate provenance 的 `input_evidence.root` 明确为
`outputs/design/live_ifc_input_mapping_probe`：其声明的 5 个 input hashes 全部匹配。
shadow 的 `source_geometry_snapshot.json`、`candidate_comparison.json`、`candidate_diagnostics.json`
与 earlier boundary-candidate 同名文件分别 byte-identical；几何 snapshot 同时与 mapping 的
`source_geometry.json` byte-identical。candidate provenance 中逐 source 的保存 footprint hash
与 mapping `geometry_eligibility.json` 对应值一致；这是 stored hash 引用对照，没有重新生成 WKB。
继承字段 `physical_wall_field_geometry_ref="source_geometry.json"` 保留 earlier mapping 命名，
通过这条 root/copy/hash 链解析；shadow runner 实际使用本地 `source_geometry_snapshot.json`。

## 3. 实际执行链与 provenance 限制

1. **shadow 直接读取 IFC 的部分。** `run_shadow_validation.py:602–628` 调用
   `ifcopenshell.open`，采集 schema、units、contexts、storey、类别计数和对象 identity。
   `build_inventory:189–194,249–263` 的 `OM_AnalysisProxy` 缺失判断来自 earlier mapped inventory，
   不是 shadow 重新扫描 OM property sets；直接读取的 `IfcSpace/IfcSpatialZone` 与该保存记录一致。
2. **继承的几何。** `:630–639` 复制 earlier snapshot/candidate/diagnostics 并核对 mapping geometry
   hash；没有调用生产 IFC adapter，也没有再次从 IFC 提取 footprint 或生成 candidate。
   earlier `generate_live_ifc_probe.py:96–222,606–662` 静态显示：读取 authored
   `IfcPolygonalFaceSet`，应用 product/mapped-item transform 与 0.001 unit scale，投影 world XY；
   不使用 `ifcopenshell.geom` backend。其 `inventory_release_run.json` 保存 exit 0，
   `inventory_release.stdout.log` 保存 8 candidates、11 walls、16 columns 及 matching source hash。
3. **shadow 重新计算的部分。** `:310–515,640–670` 用 Shapely 对保存 geometry 计算 polygon
   validity、source-reference union components、wall-column boundary intersection length，
   并对照 earlier diagnostics。`conditional_loop_support` 的 assignment/contribution 标签继承
   earlier diagnostics；shadow 重新核对 support 是否接触 candidate boundary，并未独立再建立
   新的 closure policy。earlier mapping `boundary_candidates:391–415` 将新 closed hole 的 column
   contact 标记为 conditional role；earlier comparison `run_experiment.py:239–268,313–320`
   对对应 support contact 与 candidate closed ring 形成诊断记录。
4. **Blender 的部分。** `run_shadow_validation.py:582–595,672–718` 静态 command 为指定 portable
   executable，加 `--background --factory-startup --disable-autoexec --python <saved helper>`；
   readback command 另带 disposable `candidate_comparison.blend`。
   renderer `:234–240,288–307,355–358` 仅读 3 个 serialized JSON，以 factory-empty scene
   建立 physical curves/candidate outlines、保存并 render。它没有打开 IFC 或用户 blend。
   readback helper 检查 candidate object property、occupancy tags、labels 与 PNG header，
   没有验证 IFC adapter、实体原始 3D topology 或每条 curve 坐标正确性。

shadow `validation_report.commands` 仅保存 render/readback stdout 的最后一行 `Blender quit`；
deterministic repeat 也只有最后一行及 equality 布尔值，没有完整 stdout/stderr、case-level exit code
或顶层 runner command record。runner 的 `check=True`/`timeout=240` 是代码配置，
不能改写为 independently observed historical exit 0 或 timeout。完整日志缺失仍保持缺失；
JSON/SVG deterministic repeat 是历史保存的 assertion，本次没有重复执行。

earlier mapping 的 `adapter_live_run.json` **确实**保存 `timed_out=true`、50.328 s、exit 1，
相应 stdout/stderr 文件均为空。这只是 earlier adapter attempt 的保存事实，不能归因于 shadow。
本次只读 hash 与引用检查支持同源链，不是独立复验历史执行。

`provenance.existing_evidence` 引用的 checkout
`docs/project/evidence/d6-contract-closure-owner-decision.md` 不存在。
有界 `rg` 未找到现存等价文件；按 repair 文档明确给出的 commit/path，成功读取
`git show 9b50bb1f44c0ae7dc2807c17da084d1ab8163393:...` 的确切版本作为替代。
其他要求先读的文件均存在，没有内容臆造。
可读取的 owner overlay 允许保存 occupancy/support、缺失 opening 与 validity/connectivity
分离的 bounded design guardrails；本实验没有行使 deferred production 权力。
provenance 没有保存 shadow 原始用户指令全文，因此原任务授权原文未独立验证；
本报告只比较可访问的 dated decision、plan 与实际 runner 范围。

## 4. Inventory、candidate 和拒绝边界

保存的 inventory 与 earlier mapping 逐 GlobalId 对照，**11 walls、16 columns、6 doors**
的 STEP ID、name、ObjectType 均一致；33 个记录均有 representation/placement，并明确 contained
in `Level 1`。IfcOpeningElement、IfcRelVoidsElement、IfcRelFillsElement、IfcSpace、IfcSpatialZone
均为 0。source header、本次 fingerprint 与保存的 inventory/provenance 支持 IFC4 source identity；
本次没有重新运行 native entity inventory。

length unit 为 IfcSIUnit METRE/MILLI，保存 scale=0.001；snapshot/candidates/diagnostics 均为 `m`。
model contexts 为 3D、WCS origin `[0,0,0]`，Body/Analysis 的 true north 为 `[0,1]`；
主 context 的 true north 为 null。唯一 storey 为 STEP #13、
GlobalId `2udSq8mkbQwxg0XrW$uM_r`，elevation=null、placement absent，IfcMapConversion=0。
这些 null **没有**被解释为已建立的 production work plane 或 vertical datum；world XY 仅用于诊断。

mapping 保存的 explicit spaces、zones、OM_AnalysisProxy marker 数均为 0；95 个
OM_AnalysisRepresentation substitute 的 IFC class 全为 IfcFurniture。没有 qualified authored
AnalysisDomain；也没有把 scene bbox、view framing 或候选 polygon 升级为 authored domain。

以下 ID 按 `candidate_comparison.candidate_inventory.candidate_records` 实际顺序对齐；
validity/component/contact 都是保存的诊断观察。本次独立检查了字段一致性和 source 引用。

| Display | Exact candidate ID | valid / polygon components | source-ref components | candidate contact columns | conditional support columns |
|---|---|---|---:|---:|---:|
| C01 | `wall_only:outer_face:outer:04` | true / 1 | 4 | 4 | 0 |
| C02 | `wall_only:inner_face:inner:04:01` | true / 1 | 4 | 0 | 0 |
| C03 | `wall_only:inner_face:inner:04:02` | true / 1 | 4 | 0 | 0 |
| C04 | `wall_plus_column:outer_face:outer:01` | true / 1 | 1 | 13 | 0 |
| C05 | `column_assisted_closure:inner_face:inner:01:01` | true / 1 | 3 | 1 | 1 |
| C06 | `wall_plus_column:inner_face:inner:01:02` | true / 1 | 4 | 0 | 0 |
| C07 | `wall_plus_column:inner_face:inner:01:03` | true / 1 | 4 | 0 | 0 |
| C08 | `column_assisted_closure:inner_face:inner:01:04` | true / 1 | 2 | 10 | 10 |

全部 source references 解析到 27 个唯一 GlobalIds（11 walls + 16 columns），candidate/support
ID 集在 comparison、diagnostics、shadow、saved blend readback 间一致。每个 candidate 保留
`provisional_diagnostic_only`；selection=`none`，candidate set=`ambiguous_diagnostic_only`。
8 个 valid single polygons 并不等于 source 形成一个连通壳。保存的 wall union=13 components、
wall+column union=3 components，与 earlier union diagnostics 一致。11 面墙可以各有多个 polygon
part；object 数与 union component 数不同不是矛盾。C04 source subset 的 1 component 也不使
全部 source union 的 3 components 消失。

`columns.wall_contact_pairs` 有 20 个唯一 wall/column pairs，涉及 14 个 column GlobalIds，
每个引用均解析，保存 shared boundary length 均大于诊断 epsilon `1e-9 m`。
这与 candidate-specific boundary contact 是不同集合。C01/C04 有 candidate contact 而 support=0，
明确反证「contact 自动变 support」。只有 C05/C08 被保存为 conditional support；合计 11 个
support column IDs，另 5 个无 support reference，全部 16 个仍在 physical occupancy IDs、
每个 candidate 的 all_physical_column_ids 及 source snapshot 的 eligibility 中。
C05/C08 的 source-ref unions 分别为 3/2 components；conditional support 没有被当成全局
连通或生产 enclosure 的证明，更没有把柱变成 wall。epsilon 是既存数值诊断规则，未选为
production geometry tolerance。

6 个 represented IfcDoor 只支持 door presence。保存值 `door_is_opening=false`、
`assumed_closed=false`、`state=not_inferred`；opening host relation=`missing`，opening geometry=
`not_available`，malformed/conflicting/unsupported=`not_verified`。prior default-closed design
scenario 是未应用的 assumption，不是 measured IFC fact。源中没有这些异常关系/几何 case，
故它们仍未在此 real IFC source 上测试，不能被 relabel 为 invalid/computed。

domain promotion=`refused`；free-space、walkability、route/clearance=`not_computed`。
没有生产 route、walkability、clearance、selector、空间角色或 backend readiness 结论。

## 5. 图片与 Blend readback

现存 PNG 已通过 PIL 完整解码且用 image-inspection 工具查看 original pixels。
可辨识蓝色墙体投影、16 个橙色柱方块及青/粉等候选轮廓；layout 与 panel 均完整入框，
范围标签清晰可读，次要说明需原尺寸查看但未截断。以下四条均**实际可见**：

- `REAL IFC SHADOW DIAGNOSTIC`
- `NOT PRODUCTION IMPLEMENTATION`
- `NO DOMAIN PROMOTION`
- `NO FREE-SPACE OR WALKABILITY RESULT`

panel 同时可见 `CANDIDATE SET = 8; status = provisional_diagnostic_only`、
`Conditional loop support: C05=1 column; C08=10`、all 16 columns occupancy 以及缺 domain 说明。
SVG XML fresh parse 通过，包含全部 scope labels、C01–C08 text 与 **35 paths**
（27 physical footprints + 8 candidates），与 renderer 的两个循环对应。

PNG 没有逐 candidate exact ID/color legend，部分轮廓重合，不能从 pixels 单独辨认/计数全部
8 candidates；C05/C08 对应关系由 saved JSON 顺序及 renderer `:299–307,340` 追溯，见上表。
图片足以展示限定诊断、墙柱占用和候选叠加，不足以证明 IFC adapter correctness、source topology
或每条 support contact。不存在遮蔽关键范围标签、错误宣称 production 或使诊断整体不可读的
blocking visual issue；没有以 cosmetic preference 阻止接受。

`blend_readback.json` 保存 51 scene objects、11 physical wall objects、16 physical column objects、
8 matching candidate IDs、missing_required_labels=[]；记录的 Blend/PNG bytes 与现存文件匹配，
其内容与 validation 内嵌 readback 一致。重复的 `NO DOMAIN PROMOTION` label entry 不改变
set-based 检查。本次没有 reopen Blender，所以这是 **supported-by-saved-evidence**，
不是 independently repeated blend test，也不代表用户当前打开的 Blender model。

## 6. Coverage 与历史授权

| Coverage | 本次状态 | 实际支持与限制 |
|---|---|---|
| (a) Direct IFC inventory / source identity | **observed**（当前 bytes/hash/header）；**supported-by-saved-evidence**（inventory） | source 可访问且匹配；runner 直接读取 inventory；保存 identity 与 earlier inventory 对齐。OM marker 缺失继承 earlier mapped inventory。本次不重新加载 IFC model |
| (b) Checks using saved geometry | **supported-by-saved-evidence**；引用/字段一致性本次 observed | 8 validity、13/3 unions、candidate components、20 contacts、conditional refs 自洽；geometry extraction/candidate generation 继承，不独立复算 |
| (c) Serialized-evidence rendering | **observed**（现存 PNG/SVG）；**supported-by-saved-evidence**（执行/Blend readback） | pixels/XML 实查；helpers 的输入边界明确；完整 shadow logs 未保存，未重开 Blend |
| (d) Current live Blender model | **not verified** | 未连接、未查看；不属于 bounded shadow deliverable |
| (e) New B2 implementation end-to-end | **not verified** | runner 未导入/call 新 `_analysis_view.b2_boundary_diagnostics` 链；不是该实现的 IFC acceptance test |
| (f) Production domain / free-space readiness | **not verified** | 没有 qualified domain，promotion refused，下游未计算；本任务不要求实现 deferred 能力 |

已读取 implementation design owner decision、implementation-v2 plan 的 disposition/execution/repair
记录、test-coverage repair independent review，以及 design-progress 记录，仅用于分清覆盖与授权。
2026-10-03 progress 与 2026-10-07 historical closure/repair 的 `production implementation not approved`
保留其当时 scope；同为 2026-10-07 的后续 plan append 明确记录 owner 授权了 bounded private
provenance/refusal plumbing，coverage repair review 为 ACCEPT。没有精确执行时间时不强造时序，
按文档明确标明的 later append/disposition 解释。

因此不能把 shadow 原报告首部 `Production implementation: not approved` 读成否认后续所有
B2 implementation 授权；它限定本次 diagnostic 不批准 production geometry/integration。
后续 private implementation 授权/fixture tests 也不能倒推 shadow 已调用新链，或把此 report
升级成真实 IFC integration 验证。两类工作可以分别有限接受，无需重新开启 deferred design cycle。

## 7. Findings 与最小处理

没有 blocking correctness、missing-material-artifact 或 overclaim finding；不要求修复或重跑才能接受。
以下为可追溯的非阻断限制：

| 严重性 | 精确位置/证据 | 对 limited claim 的影响 | 最小处理 |
|---|---|---|---|
| P3 / 非阻断 audit limit | `validation_report.json.commands`、`deterministic_rerun`；runner `:849,851–854` 仅保存最后一行 stdout；目录无完整 shadow logs | 不能独立核实历史 exit code/时长或 repeat 的执行历史；不使现存 artifact identity、saved record 自洽和 visible scope 失效 | 引用结果时保留「saved execution evidence、未独立复跑」限定。若未来要证明历史退出码，再附可取得的原始记录；本次不要求新实验 |
| P3 / 非阻断 presentation limit | `candidate_comparison.png`，renderer `:299–307,338–343`；图中只写 C05/C08 shorthand，无逐 ID legend，轮廓重合 | PNG 不能独立完成逐候选识别；exact IDs 可由 JSON/helper 顺序追溯，四条 scope 标签及墙柱/候选图仍可读 | 与 ID 对照表一起引用图片即可；若以后单独展示 PNG，可附已有 ID key。没有要求本次重渲染 |

原始 shadow 授权全文和完整 historical Git-scope logs 未包含在可读 provenance 中；本报告不宣称
验证了它们，也不把这类历史审计限制伪造成 adapter failure 或当前证据缺失。

## 8. 收尾 Git scope 与建议

收尾核对：branch/HEAD 未变，初始 5 modified 与 56 untracked status 全部保留；唯一新增
status entry 是本报告。写入前保存的 61 个既存 dirty/untracked 文件 hash 与 25 个相关输入
bytes/hash 均未改变。14 manifest artifacts、manifest、原报告、source IFC 的收尾复核仍匹配。
未发现影响本次结论的 reviewed-input drift；没有把不同 snapshot 混作一次稳定复验。
`git diff --check` 与 `git diff --cached --check` 均 exit 0，本报告独立 trailing-whitespace 检查通过。
没有 pre-existing permission failure；没有 stage、commit、branch switch、worktree、clean 或 stash。

建议 **ACCEPT LIMITED REAL-IFC SHADOW DIAGNOSTIC EVIDENCE**：现存证据可追溯、内部一致，
claim boundaries 与实际 runner/图片一致。阻断项 **none**；上述 audit/presentation 限制按表保留。
本接受不关闭 B2 整体，不批准 production integration，不验证新 B2 chain 对真实 IFC 的行为，
不授权下一步；最终决定由 coordinating chat 在用户带回本报告后作出。

STOP FOR D6 REAL IFC B2 SHADOW INDEPENDENT REVIEW
