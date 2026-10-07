# D6 Native IFC timeout investigation / repair evidence

日期：2026-10-07（Europe/Berlin）；执行会话。当前任务独立复审 pending。

## 调查清单

- [x] 读取 AGENTS、architecture memory、accepted implementation / real-input / independent-review 链和实际 adapter/view 流程。
- [x] 当前 branch `codex/d6-analysis-domain-layout-handoff`，base HEAD `979a756a9859a81a9b700107675cca3025a08975`；index empty、tracked clean；49 个既存 untracked 保留（48 个历史文件及后来新增的 unchanged independent review）。
- [x] IFC 408617800 bytes / SHA-256 `018fca31c0d5b0a952d74baa52cd7da56a4a1a36e6df2e5c5f070a0ca35a1240`；只读，不重写。
- [x] progress 追加 coordinating chat 对 LIMITED live-Blender evidence 的 ACCEPT；原 independent review unchanged。
- [x] 单次 300s baseline，完整阶段/产品/representation JSONL、partial profile、faulthandler、stdout/stderr、exit/timeout。
- [x] 完成小型只读 reproduction；没有已证明的最小 production 修复，不添加 speculative cache/iterator/backend。
- [x] 限定回归、单次 clean 全源 native→view/B2；分开记录两个里程碑和预算。
- [x] 最终 source / artifact fingerprints、scoped diff / staging；local evidence commit 后停止等待复审。

## 测量中的假设与文件范围（production implementation 前记录）

实施前初步测量：解析约 15.721s，materials 0.131s；前 65 次 `create_shape` 累计 124.63s、65 个不同 representation STEP IDs，全部 Body。首个产品的 Python mesh/topology 0.133/0.051s，相比 kernel 1.609s。假设：主要成本是逐产品的原生几何 kernel，而不是反复扫描材料、Python topology、NeutralScene validation 或 B2；随后独立产品原参数调用支持这个假设，不预设 cache/iterator/backend。

当前精确变更范围：新增 `scripts/design/space_field/run_native_ifc_timeout_probe.py`、本报告、manifest（待生成），append-only `docs/project/evidence/d6-space-field-design-progress.md`。`adapters/ifc_bonsai.py`、公共 API/schema、accepted runner / manifest 和所有 deferred policy 保持原样。若无语义保持的小修复证据，不把诊断工具提交称为 production 修复。

完整输出保存在 `outputs/design/d6_native_ifc_timeout_repair/run_001/`；outputs local-only，不 force-add。每次执行保存 runner snapshot，旧失败和旧 profiler version 不覆盖。

## 方法与边界

baseline wrapper 仅记录并调用原函数一次，原参数、return 和 exception 保持。全源产品不筛选，Body/Analysis 的 representation ID 分别记录。cProfile 与 flushed JSONL 存在观察开销；profile 在首次 partial dump 后停止，后续阶段仍由 wrapper 精确记录 elapsed/call boundaries，不能把 partial profile 当作全程 profile。clean run 不替换任何生产函数，只计 outer loader / view 边界。

首轮资源观察是本任务 worker PID 的 Windows CPU / working set 快照；没有终止用户 Blender。解析期间未做另一轮 IFC geometry。baseline 期间曾只读流式查找少量 STEP records，可能产生短暂磁盘/CPU竞争；不能给出完全独占资源的 wall-time 声明。

## Clean 尝试的预先预算决定

300.562s baseline 已完成 176 次 `create_shape`，都是不同的 Body representation；kernel 完成调用累计 270.676s，解析 15.721s，完成 mesh 转换累计 10.602s。未形成 scene。独立四次 subset 提取的 kernel 16.096s / adapter 17.731s；同一 Body 两次 output hash 相等，家具 Body/Analysis 身份不同，world/SI provenance 保留。没有证据支持材料扫描/cache/拓扑小改能解决总成本。

因此仅一次 clean 全源调用的 native 预算在执行前明确扩展到 **600s**（不是 performance fix，不是修复后的速度比较），以判断持续正常前进的全源 native 是否可在允许上限内返回。view/B2 单独 **180s**；如果 loader 未返回，则 view/B2 budget 未使用。没有 production adapter repair，不伪造 failing regression；subset runtime/assertions 是 dependency bottleneck reproduction，不是完整 IFC 成功结果。三组限定测试 fresh 为 112+56+7 passed。

## 实测瓶颈及最小复现

baseline：300.562s outer，worker PID 62940，kill/reap 后 exit 1、timed_out=true（Pixi outer exit 1；runner timeout 分支意图返回 124，两者分别记录）。176 次 create_shape 完成，175 个 mesh 完成；第 176 个在 topology enter 时被预算截断。176 个不同 product/representation，都是 IfcBuildingElementProxy Body；不代表被卡在某一个产品长达 300s。最后产品 #3155356 / GlobalId `188pSTO81S4h2PjTrmBjlI` / Body #3168685，kernel 2.285s 已完成，13326 triangles 的 topology 尚未 exit。累计 kernel 270.676s（outer 的约 90%），完成 topology 6.073s、mesh 10.602s（包含 topology，不能相加重复计时）。scene construction / validation 和 analysis_scene_view 均未到达。

首轮资源快照 working set 2.298GB，CPU（user+kernel）52.203s；后续快照见 raw JSON。它支持原生进程在实际运算，不证明完全没有用户资源竞争。faulthandler 30s 栈位于 `ifcopenshell_wrapper.create_shape`，最后截断位置以 flushed JSONL 为准。partial profile 的累计成本只覆盖首次 dump 前约 30.7s，不称为完整 300s profile。

独立 subset 是源文件只读 reopen 后的四次原 adapter calls，native budget 120s，实际 33.340s / exit 0；不筛选最终全源 run。所有三种 representation 的 item 是 IfcPolygonalFaceSet；原 settings 为 USE_WORLD_COORDS=True、IfcOpenShell 0.8.5 默认 opencascade，未改 quality/backend。

| subset | triangles | kernel / adapter 秒 | 观察 |
|---|---:|---:|---|
| proxy #1843736 Body #1878363，第一次 | 34124 | 5.878 / 6.476 | provenance/world transform 和 topology 纳入 mesh hash |
| 相同 proxy，相同 Body，第二次 | 34124 | 5.947 / 6.486 | mesh hash 完全一致，kernel 成本仍在 |
| furniture #145072 Body #168180 | 22991 | 4.144 / 4.635 | Body 保留为 source/audit |
| 同一 furniture Analysis #3557582 | 792 | 0.128 / 0.143 | representation ID / mesh ID 不同，analysis source suffix 保留 |

subset cProfile：四个 adapter calls 17.731s，四个 native kernel calls 16.096s；mesh 转换 1.555s、topology 0.572s。源单位 mm、scale 0.001，meshes m/world/transform_applied=True，实际 representation refs 精确匹配。重复 Body hash `9d36702eabd2a55b04ef84218b3b9bfd1181228dbaf643450591aca840660b06`。这支持 unchanged same-input reproducibility，**不是修复前后 complete-scene geometry equivalence**。

第一次 subset 26.087s / exit 1：原 kernel 已完成 5.968s，随后诊断把 immutable mappingproxy 直接交给 JSON 而失败。失败源码、stdout/stderr、profile 和 execution 完整保留；v2 仅将 diagnostic provenance copy 为 dict，使用新 output 目录，原 representation/geometry call 不变。clean runner 同样修正 diagnostic JSON 的 mappingproxy，baseline runner snapshot 保留原 bytes。没有生产异常被吞掉。

没有证明相同 source/representation 的重复 work，也没有在 Python 层找到能移除约 270s kernel work 的局部冗余。复用 settings 的收益不在测得主成本；缓存 unique representation 没有依据。更改 native tessellator/backend 或引入批处理 iterator 需要验证 explicit Body/Analysis、world transforms、opening/unsupported exceptions 与 topology parity，属于本次尚未证明的机制/架构变更。因此不把这些设想写成修复，不改变几何质量、过滤产品或替换 bbox。

## Fresh 限定检查

- `pixi run pytest test/test_neutral_scene_analysis_regression.py test/test_svg_scene_adapter.py -q`：112 passed in 5.16s，exit 0。
- `pixi run pytest test/test_blender_geometry_adapter.py test/test_group_self_description.py test/test_ifc_bonsai_adapter.py::test_adapter_preserves_native_ifc_opening_and_host_facts -q`：56 passed in 0.29s，exit 0；opening case 是新建 temporary synthetic IFC，不是源文件空 opening 的失败分支验证。
- `pixi run pytest test/test_ifc_bonsai_adapter.py::test_adapter_tessellates_real_ifc_geometry_in_world_coordinates test/test_ifc_bonsai_adapter.py::test_native_ifc_mesh_uses_analysis_metres_and_actual_representation_id test/test_ifc_bonsai_adapter.py::test_adapter_records_representation_used_for_tessellation_not_first_candidate test/test_ifc_bonsai_adapter.py::test_adapter_preserves_native_ifc_group_and_grid_axis_facts test/test_ifc_bonsai_adapter.py::test_triangle_topology_flags_reject_duplicate_triangles test/test_ifc_bonsai_adapter.py::test_triangle_topology_flags_reject_vertex_touching_shell_components test/test_ifc_bonsai_adapter.py::test_mesh_record_preserves_valid_closed_box_topology -q`：7 passed in 0.29s，exit 0。逐节点读取后确认均为 small synthetic IFC / direct topology cases，名称 real_ifc_geometry 指使用真实 IFC 格式，不读取大型 protected source。

未跑 whole IFC module / full pytest，未改生产或公共 shape，所以没有 broadened shared-helper test scope。没有 real production fix，也没有对应 RED→GREEN speedup 可声称。

## 来源覆盖的已知范围

baseline 原生 parse 返回后的 inventory 有 358 个 IfcProduct：193 IfcBuildingElementProxy、95 IfcFurniture、27 IfcFurnishingElement、16 IfcColumn、11 IfcWall、6 IfcDoor、5 IfcWindow、1 slab、1 grid、3 spatial containers。354 个 Body representations、95 个 Analysis representations；95 个 furniture 全部带 Analysis。STEP ID、GlobalId、class 及 representation STEP/identifier 的完整映射在 manifest / native_inventory.json。

193 个 proxy 是真实 IFC 产品，不把 class 直接当成“物理源”或“分析 helper”的判定；后者依赖 authored OM properties，baseline 尚未执行 source-object classification。typed Analysis 会另增 neutral substitute records，不应增加物理对象计数。baseline 的 176 个 completed shapes 与 175 个 completed meshes 仅覆盖 proxy Body，不能借 inventory 的存在声称 11 墙/16 柱/6 门、95 家具及 Analysis 已进入全源 NeutralScene/B2。小 subset 验证了一个 furniture 的 Body/Analysis 路径，仍不是全部家具覆盖。

inventory 没有 IfcOpeningElement / IfcSpace / IfcSpatialZone 产品；尚未返回的 scene 不能提供真实 opening extraction / empty collection 或 qualification/refusal 的输出证据。synthetic opening test 已通过，但不称为 real opening-failure coverage；不从门推断 opening/host、门状态，不创造 domain，不计算 free-space/route。既存 B2 的拒绝契约由本轮限定回归支持，最终原生调用是否到达 B2 必须单独看 clean run 的实际阶段和 raw JSON。

## 最终结果：已定位主要瓶颈，未修复

唯一 clean 全源调用：**600.704s outer，timed_out=true，worker / Pixi outer exit 1**；UTC 20:57:42.749630 → 21:07:43.439030，worker PID 6636。loader enter 是 20:57:44.153493，实际 loader 约 599s 被截断；600s 是包含 identity/import/fingerprint 的外部预算，不能称为精确 adapter completion time。view/B2 的独立 180s 预算未启动。

没有 loader exit、scene_sources/scene_summary、exception 或 raw B2 JSON；stdout/stderr 均空。当前 native adapter **未返回 NeutralScene**，actual B2 **未到达**。没有 B2 success、几何等价、全部产品成功投影、native opening extraction 成功、qualified-domain refusal 的新真实输出证据。无 PNG，因为没有本轮 native structural view；不借用之前 Blender replay 的图或成功标识。

最后采样 working set 3.106GB、累计 CPU（user+kernel）553.719s，持续原生计算，不能仅从这些值证明 kernel 内部具体 healing/meshing 算法或完全排除系统竞争。主瓶颈由 baseline call boundaries + 栈 + subset profile 支持：逐产品原生 `create_shape` 累计成本超出预算；**compiled kernel 内部更细的根因尚未定位**，不是已修复的 Python bug。没有经过证明可移除该成本的局部语义保持补丁；新的 backend/批处理机制或 kernel 级调查需要单独验证，不在此偷偷实施。

两次 full-source attempts 分别 instrumented 300s baseline 和 uninstrumented 600s clean；预算不同、覆盖均被截断，没有完整运行时间、exact speedup 或生产修复 improvement bound。可陈述的边界只是“176 个唯一原生 shape calls 已用约 270.7s；完整 native load 在 clean 600s outer budget 内仍无返回”。没有不变 heavy timeout 的第三次重跑，也没有遗留 worker。

## 精确执行命令与留存

```powershell
pixi run python -B scripts/design/space_field/run_native_ifc_timeout_probe.py --mode baseline --source outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/d6_native_ifc_timeout_repair/run_001/baseline
pixi run python -B outputs/design/d6_native_ifc_timeout_repair/run_001/subset_supervisor.py
pixi run python -B outputs/design/d6_native_ifc_timeout_repair/run_001/subset_supervisor_v2.py
pixi run python -B scripts/design/space_field/run_native_ifc_timeout_probe.py --mode clean --native-budget 600 --view-budget 180 --source outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc --output-dir outputs/design/d6_native_ifc_timeout_repair/run_001/clean
pixi run python -B outputs/design/d6_native_ifc_timeout_repair/run_001/verify_delivery.py
pixi run python -B outputs/design/d6_native_ifc_timeout_repair/run_001/build_manifest.py
git diff --check
git diff --cached --check
```

exact inner argv、UTC/monotonic start、worker PID/exit、elapsed/budgets 在各 execution.json；source/modules/Python 3.12.13/IfcOpenShell 0.8.5/runner identity 在 identity.json；subset 保存 compiled kernel path/55996416 bytes/SHA-256。baseline 和 clean 的 runner_snapshot 分开保存；第一次 subset serialization failure 的源码、完整 traceback/profile 原样保留，v2 用独立文件和目录。

manifest 嵌入完整 native product/representation inventory、small subset output hash/provenance/units/bounds、实际 module hashes、失败/完成 command records 和 delivery checks，并索引所有 raw local artifact bytes/hash。source IFC、所有 outputs、raw profiles/logs 和 local reproduction/audit helpers **local-only**；Git 存储新 probe、报告/manifest、append-only progress 及原样 independent real-input review。记录 hash 不代表保存 409MB 源 IFC；不 force-add outputs。

开始 baseline 的 status 在新 probe 创建之后记录（49 existing untracked + 新 probe）；existing-file hashes 是稍后补充 checkpoint。48 项与更早保存的 baseline fingerprints 完全一致，新增 independent review 的本轮 checkpoint hash 原样保留。不能假称起始 shell 已测得全部 hashes。progress 历史 Git bytes prefix 保持；production adapter、B2、contract 和 accepted runner/manifest 与 base commit 的内容一致（仅既存 CRLF/LF 归一化比较，raw hashes 单独保留）。首次 whitespace check 找到本轮 append 的空白尾行，已经只修整新尾部，历史 prefix 不变。

最终显式提交路径仅 5 个：新 probe、此报告、新 manifest、progress ledger、原样 `d6-b2-real-input-validation-independent-review.md`。原有其他 48 untracked 不纳入；无切换分支、merge、push、reset、stash、rebase 或递归 cleanup。最终 local evidence commit 的 hash 由 Git / 最终答复提供，避免报告自引用。提交只使诊断证据 reviewable，**本任务 review-pending，未 accepted，native/B2 里程碑仍未完成**。

收尾 fresh source/hash/JSON/identity/prefix/docstring 检查通过，4 个 task worker PID 全部不存在。首次 cached whitespace check 因新 manifest 的 Windows CRLF 被当前 Git whitespace 配置逐行报告；完整失败留在 `staged_whitespace_before_lf.log`。仅将新 tracked manifest 的生成改成显式 LF，再重建 artifact index；raw profiler/runner snapshots/旧 review 的 bytes 不变。最终 scoped staged check 和 exact path check 通过后才提交。

早先 checkpoint `8fd6f75d` 和 LIMITED live-Blender milestone 已被 coordinating chat 接受；本任务不能宣布 accepted 或 complete geometric B2。完整 room closure/opening subtraction/polygon/connectivity/free-space/routes、多楼层/work-plane、selector/public/UI、Bayesian/ML 全部 deferred。

STOP FOR D6 NATIVE IFC TIMEOUT REPAIR REVIEW
