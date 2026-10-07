# D6 B2 检查点与真实输入调用执行报告

日期：2026-10-07（Europe/Berlin）。角色：执行者；交付后等待独立复审。

## 执行清单（昂贵操作之前记录）

- [x] A：核对 branch/HEAD/index、五个 accepted diff、输入 bytes/SHA-256；保存 local baseline。
- [x] A：运行下列两组限定回归及 whitespace 检查；显式暂存 implementation、plan、直接 review/owner 链、shadow 小型 manifest/provenance、checkpoint note 和 append-only progress；检查 staged diff 后本地提交。
- [x] B：先用 Blender MCP `get_addon_status`、`get_scene_info` 和只读 identity query 确认 executable、blend/source association、units、IDs、dirty state。
- [x] B：单次 native IFC adapter 实际尝试，300 秒 timeout；没有到达 view/B2，保留完整日志和失败范围。
- [x] B：导出限定 wall/column/door evaluated world-space geometry；使用 `load_blender_neutral_scene(mode="blender_geometry", selected_ids=..., roles=...)`，保留 nullable source ID，实际调用 B2。
- [x] B：断言来源/占用/拒绝契约，保存 raw B2、inventory、uncertainty/provenance、模块路径/hash；同一 fresh geometry 生成 PNG 并查看。
- [x] B：保存快照在新目录重跑小型 adapter-to-B2，显式排除 run metadata 比较诊断；scope/hash/JSON/PNG/diff 检查并准备第二个限定 evidence commit。

输入：`outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc`；期望 408617800 bytes，SHA-256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`。
旧证据只读：`outputs/design/d6_b2_real_ifc_shadow_validation/`。
新产物：`outputs/design/d6_b2_real_input_validation/run_001/` 起，后续使用未占用 run ID。
runner：`scripts/design/space_field/run_b2_real_input_validation.py`，支持 `--output-dir`。

已计划精确命令：

```powershell
pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py -q
pixi run pytest test/test_blender_geometry_adapter.py test/test_group_self_description.py test/test_ifc_bonsai_adapter.py::test_adapter_preserves_native_ifc_opening_and_host_facts -q
git diff --check
git diff --cached --check
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route native --source outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/d6_b2_real_input_validation/run_001/native
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route blender --snapshot outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json --output-dir outputs/design/d6_b2_real_input_validation/run_002
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route blender --snapshot outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json --output-dir outputs/design/d6_b2_real_input_validation/run_003
```

native 命令由 runner 的 stdlib subprocess supervisor 加 300 秒总预算（仅终止该 attempt 子进程）；实际 argv、UTC、日志与结果将在交付前补齐。
无生产代码修复、adapter/schema/test 扩展、domain promotion、partition/contact/loop/free-space/route 算法。B1 多楼层/单位/工作平面及其他 deferred items 不变。

## A：已验证的实现检查点

本地 commit：**`8fd6f75d8d4444adac53588f642187d489e14831`**，parent `82d08fe54cf58be519bad6187e1f2f9e499453d5`；同一 worktree、同一 `codex/d6-analysis-domain-layout-handoff` 分支。
17 个显式路径包含五个 accepted implementation/test 文件和直接 supporting plan/review/owner/shadow/checkpoint/progress 文件；初始 index 为空，没有无关暂存内容。
核对实际 diff，没有发现与 accepted scope 无法归属的重叠改动。详见 [checkpoint note](d6-b2-implementation-checkpoint-2026-10-07.md) 和 [checkpoint manifest](d6-b2-implementation-checkpoint-manifest-2026-10-07.json)。

本轮两组回归为 **112 passed / exit 0**（9.93s）及 **56 passed / exit 0**（0.44s）。没有运行完整 pytest 或整个 IFC test module。
普通 `git diff --check` exit 0；五个实现/测试和本轮新文档的 scoped cached check exit 0。
第一次全 cached check exit 2，仅为两个既存 untracked accepted 文档的末尾空行；原始 bytes保留、具体行号和日志见 checkpoint note。这不是生产测试失败，也没有修改历史 review来消除告警。

旧 shadow 的 report/review 和嵌入 compact manifest 的原 manifest/provenance/validation/inventory 已进入检查点。
旧 shadow runner、geometry、PNG、disposable blend以及源 IFC 仍为 **local-only**；hash证明指纹，不能恢复未提交的内容。accepted outputs逐项 hash未改变。

## B：入口身份与只读 snapshot

MCP 实际顺序：`get_addon_status` → `get_scene_info` → `execute_blender_code` identity query → bounded evaluated-mesh export。
addon返回 protocol 9 / server expected 13；fallback调用实际成功，没有安装或改配置。第一次 scene-info字段请求中的 `placement` 被工具拒绝，随后用返回的具体字段修正；没有因此修改用户场景。

- executable：`D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe`；version **5.2.0 LTS**，符合允许的唯一安装。
- `.blend` path：空字符串，当前 live scene **未保存**；identity discovery及导出前后 `bpy.data.is_dirty=false`。不能据此证明从导入以来从未编辑；**live/IFC geometry parity未验证**。
- Bonsai `IfcStore.path` 与 accepted源 IFC路径相同；IFC4、project STEP #1、GlobalId `2uGd6yom9GZe5$z7LfbGW0` 与accepted inventory匹配。11 walls、16 columns、6 doors各自的完整 STEP/GlobalId集合也逐项匹配；身份不是从 object name猜测。
- 源文件本轮及收尾为 **408617800 bytes**、SHA-256 **`018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`**。
- scene units：METRIC，`scale_length=1.0`，显示 MILLIMETERS。evaluated local vertices乘evaluated `matrix_world`一次，保存世界坐标 metres；**不再施加 IFC mm→m 的0.001**。adapter读取world vertices，不再次应用 source world_transform。
- 使用现有 Blender adapter 的 world XY analysis plane，仅作诊断；没有创建生产 work plane、vertical datum、楼层资格或默认容差选择。

身份 query：`2026-10-07T19:39:14.512321+00:00`；导出 UTC：`19:48:06.899639` 至 `19:48:07.221139`。
快照：**33/33 expected structural objects present**，0 omitted、0 unavailable；56561 vertices、112886 triangles，4,318,044 bytes，SHA-256 **`c5659dcd99d8c4f20b97efd2cc37352d6305436e20e698ccbcf8c89abfe67867`**。
全部结构对象均无 modifier。372 live objects中其余339个明确排除；不提取家具Body，也不绑定/重算家具趋势。完整 object↔STEP↔GlobalId↔adapter record/mesh 映射及每项状态在 tracked manifest的 `source_scope` 和local snapshot里。
普通 Blender adapter按现有契约保留 `SourceObject.source_id=None`、`source_class=None`；B2 没有自动获得 IFC GlobalId。外部证据表通过唯一mesh ref / Neutral record ID解析IFC身份，未在 production record伪造source_id。

## 实际命令、结果与日志

下列是真实执行argv；开头清单中的run编号是操作前计划，首次runner失败后后续都使用新目录。

```powershell
# runner自身预检失败，未进入loader；保留exception/traceback
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route native --source outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/d6_b2_real_input_validation/run_001/native

# 唯一真正进入native adapter的完整提取尝试
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route native --source outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/d6_b2_real_input_validation/run_002/native

# live Blender geometry -> Blender adapter -> NeutralSceneV2 -> B2
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route blender --snapshot outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json --output-dir outputs/design/d6_b2_real_input_validation/run_003

# 同一保存快照的独立进程重跑；不是第二次live capture
pixi run python -B scripts/design/space_field/run_b2_real_input_validation.py --route blender --snapshot outputs/design/d6_b2_real_input_validation/run_001/live_snapshot.json --output-dir outputs/design/d6_b2_real_input_validation/run_004

pixi run python -B outputs/design/d6_b2_real_input_validation/run_001/verify_delivery.py
```

| route/run | 开始→结束 UTC；耗时 | 实际 exit / 结果 |
|---|---|---|
| run_001/native runner预检 | 19:44:55.641429→19:44:56.996820；1.344s | outer Pixi 1，worker 1；`AssertionError: adapters.ifc_bonsai`，没有loader_start |
| run_002/native完整adapter | 19:46:04.103693→19:51:04.266822；300.172s | outer Pixi 1，worker 1（被supervisor终止）；`timed_out=true`，**native adapter-to-B2 not_verified_timeout** |
| run_003 live snapshot | 19:48:33.536215→19:48:55.130556；21.593s | outer/worker 0；actual B2输出与断言通过 |
| run_004 snapshot repeat | 19:49:54.538564→19:50:17.762176；23.218s | outer/worker 0；actual B2输出与断言通过 |
| delivery audit | 本轮Pixi进程 | 0；30个JSON解析、确定性/保护文件/hash/docstrings检查通过 |

收尾另作fresh scope audit：**33个local JSON**全部解析，全部既存protected文件hash通过、历史progress prefix不变、第二提交的四个显式staged路径匹配。artifact index在收尾补齐late command-status、rerun-cause及audit log；第一次delivery_checks里的manifest hash仅是初次生成版本的指纹，不是收尾manifest自引用。

runner预检失败原因：既存Windows adapter文件为CRLF，Git存储LF，且core.autocrlf=false；最初比较raw bytes，尝试Git path filters后仍有差异。修复只在新runner，明确 **CRLF→LF** 作为content equality的唯一归一化，并同时保存worktree raw SHA-256与checkpoint blob SHA-256。8个production module预检通过后才进行唯一native提取。没有改production文件以使实验通过；旧failed runner源码未单独快照，原exception/traceback与命令已保留。

native worker为Pixi环境 `.../.pixi/envs/default/python.exe`，确实调用现有 `load_ifc_neutral_scene(source)`，没有selection argument、monkeypatch或伪造analysis_domain_source_id。
stdout只有 `2026-10-07T19:46:05.799235+00:00 loader_start route=native`；stderr为空。没有loader_returned、NeutralScene、native B2 JSON或adapter exception。
预算到期只kill此attempt PID **86956**，没有终止用户Blender，也没有重试完整提取。300.172s含kill/reap开销，预算为300s。
native process因timeout没有返回API结果；**不以Blender成功替代native成功**。

live runs实际调用未改的 `load_blender_neutral_scene`（explicit33 selected IDs、显式IFC class→role映射、mode=blender_geometry），随后调用 `features.neutral_scene_views.analysis_scene_view`并保存其真实 `_analysis_view.b2_boundary_diagnostics`。
没有hybrid捷径、旧2D candidate snapshot替换或hand-coded等价diagnostic。

## 实际B2观察与未覆盖分支

**新B2确实被真实live输入调用**，对应checkpoint `8fd6f75…`；实际view module：`D:/PROJECTS/understandOtherPackage/order_analyzer/features/neutral_scene_views.py`，49155 bytes，SHA-256 **`29421243263b54421fc486cfcd2d72b232c5b5fc3f635ca8d797b67af247a714`**，与checkpoint blob raw hash相同。
8个实际imported生产模块路径/raw hashes/归一化hash/commit比对在 `executed_modules.json`及tracked manifest；runner 15376 bytes、SHA-256 **`1cf4b8033c44207b89e63d986cd6023817d0280a133fe80685c6697f69d73d0a`**。

- physical_occupancy：33条，wall11、column16、door6；33/33结构source成功投影，无遗漏。每项mesh ref可解析，identity/geometry provenance可经Neutral record及外部scope表回溯。nullable IFC source_id原样保留。
- boundary_support：27条墙/柱观察，全部 `conditional_support=False`、`diagnostic_only`、reason=`b2_loop_closure_policy_deferred`；没有contact/loop closure计算，candidate_segment_ids因source_id=None而为空，不补写IFC IDs。
- domain_scope：availability=`not_available`、source=`none`、shell_identity=`not_applicable`、shell_record_ids=[]；view_bounds_basis=`scene_geometry_fallback_not_analysis_domain`。显示frame不成为AnalysisDomain。
- candidate_promotion=`refused`；candidate_polygon_validity和source_components均 `not_available`、reason=`no_current_source_observation`。不要求与旧八候选比较一致。
- downstream：subtraction=`refused`，free_space及route=`not_evaluated`。
- live Bonsai IFC的OpeningElement/Voids/Fills/Space/SpatialZone counts均0；snapshot没有manufactured opening/domain字段；当前Blender ingress默认openings=()，实际B2 `openings=[]`。这验证此入口上的空集合，**不证明native opening extraction成功**，也不制造per-opening缺失状态。
- 六扇门仅为source objects/physical occupancy；未作为void，没有observed open/closed状态，未应用default-closed scenario。视图内形状不代表测得门状态。
- conflict/unsupported/invalid/partial/missing-host opening分支在此live输入**没有覆盖**；已有synthetic tests覆盖，其证据与本轮real route分别保留。
- 家具及typed substitutes均未进入结构probe；canonical家具趋势生产链不变，必须继续使用typed substitutes。本轮没有家具趋势计算或Body替代。
- public/private边界不变：focused group regression验证public description；probe另用existing `_json_ready`私有key filter断言，不声称重算完整real group description。未改变production schema或public serializer。

## 可视化、确定性与存储

PNG来自run_003相同fresh view的components及holes，颜色区分wall/column/door physical occupancy，外侧key提供STEP/GlobalId前缀，完整表在JSON。
图片实际解码并通过Codex `view_image`查看：**2400×1500**，341488 bytes，SHA-256 **`63234df8873ba21fb31540e82f4812953ee0b5ed8079a5c7db239fcaaa44258d`**。
明确标注NO QUALIFIED ANALYSIS DOMAIN、NO FREE-SPACE / ROUTE RESULT、source/provenance/refusal validation、no new room partition；个别近邻标签重叠，右侧compact key保留所有33个身份。没有invented candidate outline或旧candidate overlay。
绘图只使用已安装matplotlib/PIL，没有Blender render、disposable .blend或用户scene变更。

run_003与run_004的完整B2 JSON、view_geometry、structural_projection_audit、scene_summary、validation及PNG均byte-identical。
仅execution/runner_identity/stdout/stderr包含run metadata而排除比较；B2内容没有裁剪字段来制造一致。这是保存快照可复现性，不是第二次live capture、native rerun或几何parity验证。
完整本地baseline/probe/MCP/export/exception/stdout/stderr/command/UTC记录均在新output目录，artifact bytes/hash索引在tracked [manifest](d6-b2-real-input-validation-manifest.json)。所有既存dirty/untracked和protected inputs（progress允许append、自己的report除外）hash检查无漂移。

第二个evidence commit仅显式暂存runner、本报告、约56KB compact manifest（含source_scope/raw B2 copy）及progress追加。第二个commit最终hash由执行会话的最终答复与Git log提供，不自引用写入该commit。
源IFC、4.3MB snapshot、PNG、原日志、raw large geometry和export/audit helpers均local-only；checkout外无法仅凭Git重放缺少的snapshot。已把小型identity/B2/command/module/provenance记录实际存入Git；没有force-add outputs。
未merge、push、reset、stash、rebase、git add .、切换branch或导入无关文件。

## 下一次独立复审建议

请独立审查两次commit的explicit scope、accepted chain、真实module/commit身份、source association与unsaved geometry限定、export transform/units、nullable IDs的外部scope解析、实际B2原始输出、timeout日志、empty-opening和未覆盖分支、snapshot复现及PNG解释。
建议待审范围为 **LIMITED LIVE-BLENDER ADAPTER-TO-B2 SOURCE/PROVENANCE/REFUSAL EVIDENCE**；native IFC adapter-to-B2仍not_verified。执行者不代替reviewer或owner接受，不关闭整个B2，不开启下一设计/实现stage。

STOP FOR D6 B2 CHECKPOINT AND REAL-INPUT VALIDATION REVIEW
