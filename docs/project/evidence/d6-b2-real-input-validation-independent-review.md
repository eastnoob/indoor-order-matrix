# D6 B2 检查点与真实输入验证独立审查

- 日期：2026-10-07（Europe/Berlin）。角色：独立 reviewer，未参与本轮实现或原实验执行。
- 建议：**ACCEPT LIMITED LIVE-BLENDER ADAPTER-TO-B2 SOURCE/PROVENANCE/REFUSAL EVIDENCE**。
- 阻断项：**none**。最终接受决定由 coordinating chat 作出。
- 唯一仓库新增文件：本报告；目标路径审查前不存在。

## 1. 审查基线与权限

项目根目录：`D:/PROJECTS/understandOtherPackage/order_analyzer`。
实际分支：`codex/d6-analysis-domain-layout-handoff`；开始及结束 HEAD：
`979a756a9859a81a9b700107675cca3025a08975`。
开始时 tracked modified=0、index=empty、untracked=48；原有文件保留。

已阅读 AGENTS.md、architecture memory、两份 checkpoint/real-input 报告与 manifest、runner、implementation review、coverage-repair review、shadow independent review、implementation-v2 plan（包括 authorization/execution/repair append）及 progress 的相关追加。静态阅读实际 Blender/IFC 入口、NeutralScene 类型、view/B2、MassPatch/projection 与 private serializer。没有重新开启已接受的 implementation design。

实际读取并使用 [superpowers:verification-before-completion](C:/Users/tianf/.codex/plugins/cache/openai-curated-remote/superpowers/6.4.2/skills/verification-before-completion/SKILL.md)。所有本次成功结论来自 fresh checks；历史测试结果明确标为保存证据。

未运行 native IFC extraction、tessellation、pytest、live MCP、Blender 或独立 renderer；未修改 source scene、runner、tests、production、历史报告或 manifest；未安装依赖、切换 branch/worktree、stage、commit、merge、push、reset、clean 或 stash；未创建子任务或向其他会话发送消息。

系统临时审查目录为：
`C:/Users/tianf/AppData/Local/Temp/d6-b2-independent-review-58ba9d0a0d444931abe5e2fb646b26a9`。
其中保存本次 baseline、只读核查脚本/结果和唯一 replay 的完整日志。它们也属于 local-only，不是 Git 交付。

## 2. 两个 Git 检查点及历史保留

实际 ancestry 为：

```text
82d08fe54cf58be519bad6187e1f2f9e499453d5
  -> 8fd6f75d8d4444adac53588f642187d489e14831
  -> 979a756a9859a81a9b700107675cca3025a08975 (HEAD)
```

`git rev-list --parents -n 1` 直接验证两条 parent；两份 commit 对象均可读取。
第一提交有 17 个路径，五个 implementation/test 的完整 diff 已检查：

```text
features/neutral_scene_views.py
test/test_neutral_scene_analysis_regression.py
test/test_svg_scene_adapter.py
test/test_blender_geometry_adapter.py
test/test_group_self_description.py
```

改动限于 private B2、精确 shell identity exclusion、opening uncertainty/provenance 和对应兼容/拒绝回归。没有 adapter、NeutralScene contract 或公共 serializer 改动。其余 12 个直接支持路径是：

```text
docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-independent-review.md
docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-owner-decision.md
docs/project/evidence/d6-b2-geometry-opening-column-loop-closure-implementation-design-review.md
docs/project/evidence/d6-b2-implementation-checkpoint-2026-10-07.md
docs/project/evidence/d6-b2-implementation-checkpoint-manifest-2026-10-07.json
docs/project/evidence/d6-b2-provenance-refusal-implementation-independent-review.md
docs/project/evidence/d6-b2-provenance-refusal-implementation-v2-independent-review.md
docs/project/evidence/d6-b2-provenance-refusal-test-coverage-repair-independent-review.md
docs/project/evidence/d6-b2-real-ifc-shadow-validation-independent-review.md
docs/project/evidence/d6-b2-real-ifc-shadow-validation.md
docs/project/evidence/d6-space-field-design-progress.md
docs/superpowers/plans/2026-10-07-d6-b2-provenance-refusal-implementation-v2.md
```

第二提交恰好四个路径：

```text
docs/project/evidence/d6-b2-real-input-validation-manifest.json
docs/project/evidence/d6-b2-real-input-validation.md
docs/project/evidence/d6-space-field-design-progress.md
scripts/design/space_field/run_b2_real_input_validation.py
```

第二提交没有新 production behavior；runner 是诊断工具，progress 仅追加 10 行。第一提交的 progress 仅追加 6 行；两次提交的历史 prefix 都保持。支持文档/runner 的 Git blob 与当前原始 bytes 一致，progress 按各 checkpoint prefix 单独核对。`checkpoint_staged_paths.txt` 的 17 路径集合与实际第一提交一致。

历史 baseline.json 与 checkpoint manifest 的 `initial_dirty_files`（63 项）、`protected_inputs`（22 项）逐字段一致，历史 HEAD 为 `82d08fe…`，index 为 null/empty。五个已采用 implementation/test 的原始 bytes/hash 全部匹配 manifest；其 diff 内容可归属 accepted scope。当前全部 48 个 untracked 都属于历史列表，且逐项 bytes/hash 保持。原 63 项中另外 15 项是明确采用的五个代码/测试及十个 plan/review/report 文件；其中执行者自己的 real-input 报告随后完成，不能要求它保留预执行草稿 hash。protected progress 按历史长度重算 prefix hash，其余 protected files 原始指纹匹配。

因此可以核查“记录过的 unrelated work 没有进入这两个提交，并仍按记录保留”。不能仅凭当前干净的 tracked status 重建更早 dirt，不能证明历史 baseline 未记录的瞬时文件/变化，也不能把保存日志当作本次目击 stage/commit 操作。

原 implementation review 的 REVISE 是 coverage finding，coverage-repair review 为 ACCEPT；plan-v2 的旧 REVISE PLAN 与其后来 disposition 并存。已核对 nullable ID、fixture source identity、authoritative file scope 的处理，没有改写历史判断。两处 accepted 历史末尾空行警告保持原样，不构成本次 blocker。

## 3. 指纹、artifact roots 与模块身份

real-input manifest 没有另一个 artifact root；`artifacts[].path` 是 repository-relative。`source_ifc.path` 是绝对路径；snapshot/runner 可按 repository-relative 的 Windows 路径解析。checkpoint manifest 的 `root` 指向本 repository；嵌入 shadow manifest 的 `entries[].path` 则相对于 `outputs/design/d6_b2_real_ifc_shadow_validation/`。本次按各自 schema 解析，未猜测缺失路径。

| 核查对象 | bytes | fresh SHA-256 |
|---|---:|---|
| accepted IFC：`outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` | 408617800 | `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240` |
| run_001/live_snapshot.json | 4318044 | `c5659dcd99d8c4f20b97efd2cc37352d6305436e20e698ccbcf8c89abfe67867` |
| runner | 15376 | `1cf4b8033c44207b89e63d986cd6023817d0280a133fe80685c6697f69d73d0a` |
| features/neutral_scene_views.py | 49155 | `29421243263b54421fc486cfcd2d72b232c5b5fc3f635ca8d797b67af247a714` |
| run_003/b2_occupancy_refusal.png | 341488 | `63234df8873ba21fb31540e82f4812953ee0b5ed8079a5c7db239fcaaa44258d` |
| real-input manifest（最终提交版本） | 55785 | `afa2a780f4b0140d053caf8d701b64bb749dac44754561793022515dc789f478` |
| implementation checkpoint manifest | 48407 | `64c9c49c9365dbc0373e0b27a5a01f3f33f4281d7ed91a14797a0e9fa3883b8a` |
| real-input execution report | 16679 | `ab23caaa02c18deacec90ae1975eb0201fbb8fe452d0ca722db9cca2c290fb98` |

51/51 real-input artifacts、16/16 declared checkpoint files、22/22 protected inputs（progress 使用历史 prefix）、14/14 shadow artifacts 均匹配；missing=0。real-input 33 个 JSON fresh parse 成功。tracked manifest 的 `actual_b2` 与 run_003 raw B2 相等，`source_scope`/identity/exclusions 与快照一致。

以下八个模块的路径均在本 repository 对应文件，不存在 foreign import。raw hashes 与原 executed_modules 一致，本次 replay 记录也 byte-identical：

| 模块（路径由 dots 转换为目录并加 .py） | raw bytes | raw SHA-256 |
|---|---:|---|
| adapters.blender_geometry | 17983 | `a0251284925ee3714406ebdca86d904f00b953e70d7affbfa782b36f72542786` |
| adapters.ifc_bonsai | 82655 | `d9c494a0af5a9b5e09c29814de5a8cd2348a7ff5bf31ac48adefec652b041cdd` |
| features.neutral_scene_views | 49155 | `29421243263b54421fc486cfcd2d72b232c5b5fc3f635ca8d797b67af247a714` |
| features.scene_contract | 43313 | `60ca090fb5ba9349b3f817bab53a01ffa1a7310d0c1112debb918a4c1a360db7` |
| features.geometry_views | 29103 | `8feb3852194401485ade4171ecd13140a256c10d1dff1058589100e1e122ba34` |
| features.geometry_substitutes | 6303 | `124852c4a6e1d061e450f3a304e7bc8e847e0f3a6f63e9d483da180ff39f8fa8` |
| features.group_self_description | 45414 | `36de850c98d0e8cb678743c196c29ac74beb5e782a6311e4ac728866816286e6` |
| features.analysis_substitute_discovery | 10373 | `3dd4f6600bee30c6ef2519d79e7c8b71e2469f8c07a31b826d5e95108ab7d4e4` |

独立读取 `git show 8fd6f75:<path>` 并比较完整 bytes：neutral_scene_views raw bytes 与 Git blob 相同；其余七项 raw 不同，但仅执行 `CRLF -> LF` 后与 blob 相同。没有 strip、忽略注释或删字段。raw SHA 与 LF SHA/内容比较分开记录于临时 artifact_audit.json；原 manifest 中 checkpoint_blob_sha256 可追溯。没有实质 drift，replay 测试的是上述检查点内容。

`delivery_checks.json.manifest` 的 53218 bytes / `47126433…` 是明确标注的 initial version，不能证明最终 manifest。`final_scope_audit.log.manifest_bytes/manifest_sha256` 为 55783 / `8471e0d1…`，同样不同于最终提交 bytes；原报告第 93 行说明随后补齐 audit log 等 artifact index。本次不把该历史日志 hash 当作最终版本证明，也没有保存或推断其先前精确 payload。最终版本已经直接与 `979a756:docs/project/evidence/d6-b2-real-input-validation-manifest.json` 的 blob 比较并 fresh hash；不要求循环 self-hash。

## 4. live association 与几何/单位交接

保存的 identity query 代码、raw MCP result、提取后的 live_identity.json 相互一致；export 代码、raw MCP result 与 snapshot 指纹/identity 相互一致。记录的 executable 为唯一允许的 `D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`，版本 5.2.0 LTS。记录时间是原 capture 的时间，不是本次 live observation。

IFC4、IfcStore.path、project STEP #1 / GlobalId `2uGd6yom9GZe5$z7LfbGW0` 与 accepted inventory 匹配。本次另以只读 streaming 文本扫描核对源 IFC 的项目及 33 个指定 STEP record 的 class/GlobalId，34/34 匹配；未通过 native loader 打开 IFC，没有读取/重建几何。

scope 表的 STEP、GlobalId、object_id、object_name、adapter_record_id 各有 33 个唯一值；与 identity query、accepted inventory 的结构集合完全相等。role 由真实 IFC class 映射：IfcWall→wall 11、IfcColumn→column 16、IfcDoor→door 6。所有 status=present、reason=null、modifiers=[]，0 omission/unavailable。372 个 live objects 中另外 339 个明确排除；不把它们算作已验证 furniture/substitute 输入。

转换链经静态代码与本次数值检查支持：

```text
evaluated mesh local vertices
 -> evaluated.matrix_world @ vertex（export helper:55）
 -> snapshot.objects[].vertices，units="m"，transform_applied=true
 -> _mesh_from_snapshot（adapters/blender_geometry.py:106）原样复制
 -> MeshGeometry3D -> mass_patch_from_mesh（geometry_substitutes.py:125）原样复制
 -> plan_projection（geometry_views.py:97）在 world XY 投影 triangle faces
 -> 共用 origin_offset 的 analysis view -> 实际 B2
```

METRIC、scale_length=1.0、显示 MILLIMETERS；没有第二次乘 0.001。adapter 消费的是对象级 `units`/vertices/triangles/transform_applied；`source_length_unit` 进入 context。snapshot identity 中的 scale_policy/scene display units 是审计 metadata，不是 adapter 的自动换算参数。SourceObject.world_transform 留作 provenance；MassPatch/view 不再应用该矩阵。

快照含 56561 vertices、112886 triangles；本次逐对象核对有限坐标、triangle index 范围、scope 计数、source record/world_transform 与 mesh refs。32 个矩阵有非零平移，1 个为 identity；所有线性部分为 identity，没有 retained rotation/scale stress case。33 项 referenced world-XY bounds 加唯一 offset `[0.0, 0.009999999776482582]` 后，与 replay view points bounds 的最大差为 **0.0 m**。这独立排除了交接阶段再次平移/缩放的错误。

| 代表 record | world XY bounds（m；minX,minY,maxX,maxY） | world translation（m） |
|---|---|---|
| wall #141159 / 3QAL1kxKLJZxF3Sj5PqTVo | 6.4585819244, 8.75, 6.6085820198, 12.3000001907 | 6.4585819244, 8.75, 0 |
| oblique wall #143733 / 3R_rUQk_TQmBN0VHbYhNx6 | 20.6000003815, 6.5999999046, 25.6000003815, 12.6000003815 | 20.6000003815, 6.5999999046, 0 |
| column #59 / 3GmZVu1k9LTPtswYG5UTt5 | 0, 0, 0.6000000238, 0.6000000238 | 0, 0, 0 |
| column #15584 / 1N82hRNmvUrP89uC6GpdtM | 19.9979991913, 6, 20.5979995728, 6.5999999046 | 19.9979991913, 6, 0 |

未保留 independent local vertex arrays；不能从 retained world arrays 独立证明原 capture 的每次 matrix multiplication，逆变换重建也不是独立 ground truth。这里 local→world 正确性由保存代码/result 支持，world→adapter→view 可本次重放并数值核查。`.blend` 未保存，is_dirty=false 只描述当时状态，**live geometry 与 disk IFC geometry parity 未验证**。

## 5. 唯一有界 replay 与实际 B2 语义

先完整检查 runner 参数/写路径：`main:231-275` 创建新 output-dir（exist_ok=false），worker 只向此目录写 JSON/log/PNG；Blender 分支 `probe:203-209` 只读快照和源 IFC fingerprint，再调用 existing `load_blender_neutral_scene`，不调用 native extraction，也不连接/启动 Blender。`probe:210-211` 调用 canonical `analysis_scene_view(scene)` 并读取真实 private B2。

实际 replay 命令（仅一次）：

```powershell
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route blender --snapshot outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json --output-dir C:/Users/tianf/AppData/Local/Temp/d6-b2-independent-review-58ba9d0a0d444931abe5e2fb646b26a9/replay
```

外部 stdlib supervisor 设置 120 秒 timeout，并保留 outer stdout/stderr/exit；runner 自身 Blender budget 为 180 秒，实际受更短外部上限约束。outer PID 40196、worker PID 67352；outer exit=0、worker exit=0、timed_out=false；外部 elapsed=14.609s、runner elapsed=14.344s。UTC 20:25:48.910420 开始，runner 20:26:03.464058 结束（本地日期仍为 2026-10-07）。worker stderr 为空，Pixi outer stderr 有已有 SSL_CERT_DIR warning，未影响结果。

fresh stdout 顺序明确：loader_start route=blender → loader_returned sources=33 geometries=33 → actual_b2_returned。没有 exception.json。

本次独立脚本按 snapshot object→adapter record→unique mesh ref→raw occupancy row 逐项解析，未仅复用 `validation.assertions=pass`：

- **physical_occupancy 33 条**，全部 included=true，11 wall、16 column、6 door。每条唯一 mesh ref 均回溯到 snapshot，source_id 保持 null，没有漏柱或按名称推断来源。
- **boundary_support 27 条**，正好对应 11 墙+16 柱的 record/mesh refs；全部 conditional_support=false、diagnostic_only、reason=b2_loop_closure_policy_deferred、candidate_segment_ids=[]。这是未执行 closure policy，不是负的物理接触/支撑观测。
- domain_scope 完整为 availability=not_available、source=none、id=null、geometry_refs=[]、shell_identity=not_applicable、shell_record_ids=[]、blocker=null。display frame 不成为 AnalysisDomain；scene_summary.domain=null。
- candidate_promotion=refused；candidate_polygon_validity、source_components 均 not_available / no_current_source_observation，引用列表为空。没有与旧八个 polygons 进行 validity/components 比较。
- downstream subtraction=refused、free_space/route=not_evaluated；没有 promotion、subtraction、partition、free-space 或 route 结果。
- openings=[]，scene opening_count=0，snapshot 没有 openings/domain；记录的 live IFC OpeningElement/Voids/Fills/Space/SpatialZone counts 均 0。这证明当前默认空 ingress，不验证 native opening extraction 或 real missing/invalid/partial/conflict/unsupported/missing-host 分支。
- 六扇门保持 source physical objects，未变成 void、未推断 observed open/closed、未套用 default-closed scenario。家具 Body、typed substitutes、trend 路径未进入此 probe。

SourceObject.source_id/source_class 在此 mode 均为 None，B2 occupancy 没有原生 IFC GlobalId。完整身份在外部 source_scope 中，通过 record ID/唯一 mesh ref 可审计回溯；这是 **external IFC mapping**，不是 **in-payload IFC provenance**。

private B2 仅位于 `_analysis_view`；`group_self_description.py:923-931` 的既有 `_json_ready` 过滤 underscore keys。probe 的 private-filter assertion 与保存的 public regression 相符，但未重算 real group description，不声称公共 API/schema 改变或全公共生产链验证。

对 replay 与 run_003、run_004 的逐文件 raw bytes 比较全部一致：
`b2_boundary_diagnostics.json`、`view_geometry.json`、`structural_projection_audit.json`、`scene_summary.json`、`validation.json`、`b2_occupancy_refusal.png`，以及额外的 `executed_modules.json`、`input_provenance.json`。
仅排除明确含 run metadata 的 execution.json、runner_identity.json、stdout.log、stderr.log；没有删除失败诊断字段来制造一致。B2 JSON 和来源/几何独立解析才是主要 oracle，pixel equality 是补充。
run_003/run_004 及本次 replay 都消费同一个保存 snapshot，不能称为多次 live acquisition。

## 6. native 失败证据（未重跑）

run_001/native 为 runner precheck：stdout 为空；stderr/exception traceback 在 imported_modules checkpoint equality 的 `AssertionError: adapters.ifc_bonsai`，没有 loader_start。历史 worker PID 90260、exit=1、1.344s、timed_out=false。最初失败 runner 源码没有独立保存；本次只能核查 traceback/command，不重构其精确 bytes。当前七个 CRLF 文件的 raw/LF 差异与描述相容，但不能据此伪造旧 runner 原文。

唯一真正进入 native 的 argv 保存在 run_002/native/execution.json：

```powershell
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route native --source outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/d6_b2_real_input_validation/run_002/native
```

worker argv 使用本项目 `.pixi/envs/default/python.exe`、`-B`、同 runner 和 `--worker`；PID 86956，UTC 19:46:04.103693→19:51:04.266822，elapsed=300.172s、budget=300s、timed_out=true、worker_exit_code=1。outer_command_status 保存 Pixi exit=1；不将该保存值与 runner `return 124` 的静态 timeout 分支混为直接观察。

stdout 只有 `2026-10-07T19:46:05.799235+00:00 loader_start route=native`；stderr 为空。没有 loader_returned、NeutralScene、B2 JSON 或 adapter exception。runner `:201` 实际调用 `load_ifc_neutral_scene(source)`；入口 `adapters/ifc_bonsai.py:1944-1953` 转 `_open_source`/`_scene_from_source`，没有 selection monkeypatch、fake domain argument 或 hybrid shortcut。

supervisor 到期 kill 其 worker 的代码与保存结果相符。这是 **timed-out extraction attempt**，不是 adapter 已完成 rejection/success。native adapter-to-B2 仍 **not_verified_timeout**。文件大并不能说明 timeout 根因；本次没有诊断或修复它。native integration 不完整不使已审计的有限 Blender ingress 证据失效。

## 7. 实际 PNG 检查

使用 `view_image` 打开 run_003/b2_occupancy_refusal.png（original requested，工具显示时缩放为 1996×1248；原文件 2400×1500）。蓝墙、橙柱、绿门 physical occupancy 可见，右侧 33 项 label/STEP/GlobalId-prefix key 可读；完整 ID 位于 view_geometry.json。图中实际可见 BLENDER route、structural subset，以及：

```text
NO QUALIFIED ANALYSIS DOMAIN
NO FREE-SPACE / ROUTE RESULT
```

底注说明 conditional=False、27 sources、No contact / loop closure computed、No new room partition、unsaved snapshot / IFC geometry parity unverified。没有 native 成功、计算 support 或新划分结果的表达。

绘图 `plot_geometry:146-153` 消费本次 view 的 geometry_components/holes；独立计数为 41 个 projected components、1 个 hole，不是 B2.source_components 已计算，也不是旧 candidate overlay。部分近邻 W/D/C 标签重叠及左下 legend 覆盖少量源图形；key/JSON 可以定位且范围提示未遮挡，未发现 material visual blocker。不要求 cosmetic rerender。

## 8. Findings 与 coverage

**没有要求修复的 material implementation/evidence finding；阻断项 none。** 下表是证据边界及最低引用要求，不是新开发任务。

| 严重性 | 精确位置/证据 | 影响 | 最小处理 |
|---|---|---|---|
| 非阻断 audit limit | run_001/native/exception.json.traceback；旧失败 runner 未快照 | 无法重现旧 precheck 的精确源码 bytes | 保留 historical reproducibility 限制；本轮不重跑 |
| 非阻断 version limit | delivery_checks.json.manifest；final_scope_audit.log.manifest_sha256；manifest.checks.delivery_checks_manifest_fingerprint；原报告:93 | 历史 audit hashes 不证明最终 manifest bytes | 引用本报告 fresh 最终 fingerprint/Git blob 比较，不要求 self-hash 或改写日志 |
| 非阻断 geometry limit | snapshot.identity.blend_path/ifc_geometry_parity；objects[].vertices | 无独立 retained local vertices 或 disk IFC geometry parity | 保留 saved-live-geometry 限定 |
| 非阻断 coverage/retention limit | native execution.timed_out；B2.openings；manifest.storage.local_only | 不支持 native end-to-end、real opening failure branches 或仅靠 Git 重放 | 按下表引用，不扩大接受范围 |

| 覆盖项 | 本次状态 | 支持与限制 |
|---|---|---|
| source file identity | **independently observed** | streaming bytes/SHA；34 个 project/结构 STEP class+GlobalId 文本核对；不加载 native geometry |
| recorded live-object association | **supported by saved evidence**，表/源文本一致性 independently observed | 原 MCP code/result、project/path/33 identities 相符；未触碰当前 Blender |
| geometry/units handoff | capture **supported by saved evidence**；snapshot→view **reproduced** | matrix once 的保存代码；world data/units 与 33 项 bounds fresh 核查；local vertex reconstruction/parity not verified |
| actual Blender adapter→NeutralSceneV2→B2 | **reproduced** | 一次 bounded replay，exit 0；raw JSON、来源几何与原两进程一致；33 occupancy/27 deferred support independently resolved |
| external vs in-payload IFC identity | **independently observed / reproduced** | external scope table 一对一；production source_id/source_class 与 B2 source_id 为 null；不称 native IFC provenance |
| native adapter→B2 | **not verified**；timeout supported by saved evidence | loader_start 后 300s supervisor timeout，无 scene/B2 返回 |
| opening failure branches | **not verified on real input** | 本次只重放 openings=[]；synthetic coverage 由既存 formal tests/reviews 支持，未重新执行 |
| production domain/free-space/trend readiness | **not verified** | 无 qualified AnalysisDomain；promotion/subtraction refused，下游 not_evaluated；furniture/substitute/trend 未纳入 |

## 9. 实际检查命令、留存与收尾

| 实际命令/工具 | 本次结果 |
|---|---|
| `git branch --show-current`; `git rev-parse HEAD`; `git status --porcelain=v1`; `git diff --cached --name-status` | 开始/结束 branch/HEAD 不变；index empty；48→49 untracked，仅本报告新增 |
| `git show --format=fuller --stat <commit>`; `git rev-list --parents -n 1 <commit>`; `git diff --name-status 8fd6f75 979a756`; `git diff-tree --no-commit-id --name-only -r <commit>` | 17/4 精确路径；实际 ancestry 已固定 |
| `git show 8fd6f75 -- <五个 implementation/test 路径>`; 两次 progress diff；`git show <commit>:<path>` | 完整代码/测试 diff 与限定 scope 相符；文档 bytes、progress prefixes 匹配 |
| `Get-Content` / `Select-Object`; `rg -n` / `rg --files` | 指定 docs/code/保存 logs/actual filenames 有界阅读 |
| `pixi run python -B <temp>/inspect.py <temp>` | 保存 current 48 项 baseline，解析两个 manifest 实际 schema |
| `pixi run python -B <temp>/audit.py <temp>` | streaming source hash、51 artifact、16 checkpoint、22 protected、14 shadow 核对；8 modules raw/LF 比较；33 JSON parse，exit 0 |
| `pixi run python -B <temp>/replay_supervisor.py <temp>` | 执行第 5 节唯一命令，120s 外部上限；14.609s、exit 0，无 retry |
| `pixi run python -B <temp>/independent_semantics.py <temp>` | 逐 source/mesh/role/occupancy/support、triangles、bounds、status 和 8 文件跨三进程比较，exit 0 |
| `pixi run python -B <temp>/git_source_audit.py <temp>` | 34 IFC identity 文本、historical baseline、48 preserved files、17 staged paths、committed doc identity、outputs untracked 检查，exit 0 |
| `view_image(run_003/b2_occupancy_refusal.png)` | 实际查看 pixels；限定语义与 source key 可见 |
| `git diff --check`; `git diff --cached --check` | 本次 exit 0；没有改写历史 whitespace warning |
| `pixi run python -B <temp>/final_scope.py <temp>` | 收尾 baseline/hash/artifacts/Git scope 与本报告检查，exit 0 |

`<temp>` 指第 1 节绝对目录。这些临时脚本/结果未进入仓库。原 regression_a/b.log 的末行分别是 **112 passed in 9.93s / 56 passed in 0.44s**，保存 outer exit 0；属于 historical saved evidence，本次未运行或重新宣称这些回归通过。

`git ls-files` 对本轮 outputs 与 source IFC 无输出：snapshot、PNG、detailed logs、export helpers、IFC 和 shadow 大文件 **local-only**。Git 实际存储小 manifest/identity/source_scope/B2 copies、runner、报告及进度；记录 hash 不储存被引用文件内容。在没有这些本地文件的 checkout 中，仅凭 Git 无法 replay；当前 checkout 全部必要 prerequisites 可访问。

收尾与开始相比：branch/HEAD 不变，tracked diff=empty、cached diff=empty；48 个既有 untracked 的状态和逐文件 bytes/hash 未变；唯一新 status entry 为 `?? docs/project/evidence/d6-b2-real-input-validation-independent-review.md`。51 个 real-input artifact 和受保护 source/checkpoint/document 指纹仍匹配。只读 scope delta 没有 production、runner、tests、源输入或既有证据修改。

建议接受范围严格限定于 **LIMITED LIVE-BLENDER ADAPTER-TO-B2 SOURCE/PROVENANCE/REFUSAL EVIDENCE**。它证明关联的保存 live structural geometry 经现有 adapter 进入实际 private B2，并保留占用、外部来源解析与拒绝语义；不接受整个 B2，不批准 native production IFC integration、房间划分、自由空间/路线、家具趋势 readiness 或 downstream stage，不做 merge。

STOP FOR D6 B2 REAL-INPUT INDEPENDENT REVIEW
