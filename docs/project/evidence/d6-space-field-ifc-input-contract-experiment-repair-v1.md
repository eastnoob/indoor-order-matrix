# D6 空间场 IFC 输入契约设计实验：有界收尾返修

- 日期：2026-10-01
- 范围：只读 IFC4 fixture adapter 对照、真实 IFC 原生盘点、source-fact-only Blender preview。
- 停止标记：**STOP FOR SPACE FIELD IFC INPUT EXPERIMENT REPAIR REVIEW**

## 原交付一致性核对

1. **runner 与实际命令不一致。** 原交付的 `run_ifc_input_contract_experiment.py` 包含 fixture writer 和四类 fixture adapter 调用，但原 `experiment_results.json` 是后续手写 JSON 命令生成的，写入内容为 `fixture_cases=not_run_due_to_output_directory_permission_error`。原 `provenance.json` 只保留了泛化的 `portable python bounded adapter probe`，没有 runner 的完整 argv、退出码或日志。因此原 JSON 不能作为该 runner 的实际输出证据；旧文件全部保留。
2. **fixture 记录与脚本/JSON 矛盾。** 脚本确实声明 `fixture_no_domain`、`fixture_explicit_domain`、缺 geometry、断 opening relation 和状态观察位点；JSON 却明确写成 fixture 未运行。返修用独立 `run_002` 重新执行真实 runner，保存每项 adapter payload、调用形式和退出码。
3. **旧 manifest 没有 PNG。** 原 Blender 脚本在保存 `.blend` 后因没有 camera 抛出 `RuntimeError: Error: Cannot render, no camera`；所以当时没有 PNG 可列入 manifest。旧 manifest 未伪造 PNG，旧 Blender 输出也没有持久化日志。返修加入 camera、正交 framing、PNG 输出和图像检查。
4. **live IFC timeout 不能由旧证据证明。** 旧结果写了 `not_run_timeout_guard`，但没有完整命令、stdout/stderr 日志或退出码；因此本返修把 live geometry adapter 结论定为 **not verified**，只重复 IFC 原生计数和 GlobalId/STEP 身份盘点，未重试完整 408 MB 几何适配。

## 返修 A：IFC4 fixture adapter 对照

使用新目录 `outputs/design/space_field_ifc_input_contract_experiment/repair_v1/run_002/fixture_workspace/` 保存 disposable IFC。正式 fixture、production code、源 IFC 和测试均未改动。runner 为 [run_ifc_input_contract_repair.py](../../../outputs/design/space_field_ifc_input_contract_experiment/repair_v1/run_ifc_input_contract_repair.py)。

实际覆盖五项，均退出码 0：

- `no_domain`：`analysis_domain` 为 `null`，实际 uncertainty 包含 `missing_analysis_domain`。
- `explicit_domain_with_closed_geometry`：显式 `IfcSpace` 被选中；domain geometry ref 可解析，adapter mesh flags 为 `is_closed=true`、`is_manifold=true`。
- `explicit_domain_without_geometry`：domain record 仍存在，但 `geometry_refs=[]`，domain uncertainty 为 `missing_geometry`。
- `opening_without_voids_host_relation`：`IfcOpeningElement` 和 opening geometry 仍存在，实际 `host_refs=[]`；当前 API 没有自动补 host，也没有把门几何改写为 opening relation。
- `malformed_authored_grid_axis`：当前 API 没有统一 `unsupported` status 字段，实际输出的是 `UncertaintyRecord(code="unsupported_grid_axis_curve", failure_type="insufficient_polyline_points")`。这是真实 API 表达，不是伪造的 status 字段。

正向 fixture 的 `AnalysisContext` 实际记录了 IFC4、source unit `mm`、analysis unit `m`、`ifc-world-plan` 和 adapter version。adapter payload 中没有 free-space、connectivity 或 path 结果；这些仍是设计门槛，不是当前 adapter 能力。

临时目录复现使用 `temporary_reproduction_2026-10-01_v2/`，fixture case ids 和 adapter payload 与 primary run 完全一致，复现退出码为 0。两次运行都没有调用真实 IFC 几何适配。

## 返修 B：Blender 只读可视化

使用规定的 portable Blender：

`D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe`

最终渲染命令退出码为 0，生成并回读检查：

- [live_ifc_inventory_not_available.png](../../../outputs/design/space_field_ifc_input_contract_experiment/repair_v1/run_002/render_final/live_ifc_inventory_not_available.png)：仅显示真实 IFC 的直接实体盘点、门/墙 GlobalId 与 STEP 身份，明确显示 `NOT AVAILABLE — NO QUALIFIED ANALYSIS DOMAIN`，不显示 source mesh 或 free-space。
- [ifc4_fixture_source_facts.png](../../../outputs/design/space_field_ifc_input_contract_experiment/repair_v1/run_002/render_final/ifc4_fixture_source_facts.png)：显示显式 domain、wall、opening 及 `IfcRelVoidsElement` host ref；明确标记 `SOURCE FACTS ONLY — NO FREE-SPACE, WALKABILITY, OR VISIBILITY RESULT`。
- 对应 disposable blend：[live](../../../outputs/design/space_field_ifc_input_contract_experiment/repair_v1/run_002/render_final/live_ifc_inventory_not_available.blend)、[fixture](../../../outputs/design/space_field_ifc_input_contract_experiment/repair_v1/run_002/render_final/ifc4_fixture_source_facts.blend)。回读检查确认两份文件都有 `RepairPreviewCamera`；live blend 只有文字身份盘点，fixture blend 包含三个 source-fact mesh 对象。

PNG 检查实际确认 PNG signature、IHDR/IDAT/IEND、尺寸：live `1800x1400`，fixture `1900x1050`。Blender 日志中的缩略图缓存 PermissionError 不影响目标 PNG 写入；目标文件已存在并通过 stdlib PNG 检查。

## 事实、当前能力、未验证项

- **事实：** live IFC 原生盘点为 IFC4、`IfcSpace=0`、`IfcOpeningElement=0`、`IfcRelVoidsElement=0`、`IfcRelFillsElement=0`、`IfcDoor=6`、`IfcWall=11`、`IfcFurniture=95`。真实源 IFC 未修改。
- **当前 API 能力：** `NeutralSceneV2.analysis_domain` 可空；显式 domain 无几何时保留 domain record 和 `missing_geometry` uncertainty；`SourceOpening.host_refs` 可为空；unsupported 由具体 uncertainty code 表达；adapter 不执行 opening subtraction 或空间场下游计算。
- **下游边界：** 没有合格 domain 时 free-space、components、connectivity、path 保持 `not_available`；diagnostic bounds 只能是 `diagnostic_only`。这些是契约观察，不是统一现有 status enum。
- **未验证：** live IFC 几何适配、生产 free-space backend、opening subtraction、通行性、视觉穿透、door state、boundary scope、resolution、route width、空间角色和任何 Bayesian/ML 模型。

## 命令、技能和验证

实际命令及退出状态写入 [repair_command_log.json](../../../outputs/design/space_field_ifc_input_contract_experiment/repair_v1/run_002/repair_command_log.json)。本次使用的技能是 `verification-before-completion`，用于要求新鲜 JSON/PNG/hash/Blend 回读证据；`experimental-design`、`scientific-critical-thinking`、`scientific-visualization`、`speckit-assess` 没有在当前可读技能路径中找到，未声称使用。

验证仅包括：fixture runner、临时目录复现、portable Blender render、保存 blend 回读、JSON/PNG/hash 检查和新文本 whitespace 检查。没有运行完整 pytest、完整 IFC 几何适配或无关历史实验。

`git diff --check` 输出了既有 `.tmp-test-preview-final2` Permission denied 诊断；该目录属于既有 dirty/untracked 内容。对本次新增文本文件执行的有界 whitespace 检查无 trailing whitespace。生产目录、adapter、features、正式 fixture/test、公共 API、依赖、源 IFC 和用户 Blender 文件均未修改。

## 停止结论

返修证据已自洽到有界设计实验所需范围：fixture adapter 实测、provenance、重复复现、PNG/blend 和哈希 manifest 均可追溯。实验仍停留在设计验证，不批准 production implementation。

**STOP FOR SPACE FIELD IFC INPUT EXPERIMENT REPAIR REVIEW**
