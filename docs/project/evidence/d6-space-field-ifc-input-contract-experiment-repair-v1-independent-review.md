# D6 空间场 IFC 输入契约实验 repair_v1 独立复核

- 复核日期：2026-10-01
- 复核范围：`outputs/design/space_field_ifc_input_contract_experiment/repair_v1/`
- 复核方式：只读证据核对；未修改 production code、adapter、正式测试、公共 API、依赖、源 IFC 或用户 Blender 文件。

## 总结结论

**ACCEPT LIMITED DIAGNOSTIC EVIDENCE**

`repair_v1/run_002` 的 fixture adapter 结果、真实 IFC 原生盘点、source-fact-only PNG、可回读 `.blend`、provenance、manifest、哈希和临时目录复现相互支持一个有界结论：返修确实运行了五个 disposable IFC4 fixture case，并保留了真实 IFC 的只读实体盘点；它没有证明 live IFC 几何适配，也没有产生自由空间、连通性、路径、通行性或视觉穿透结果。

该结论只适用于设计/诊断证据，不批准 production spatial-field implementation。

## Blockers

无会阻止上述限定诊断结论成立的 blocker。

以下两项 provenance 限定必须保留在证据解释中，不能升级为更强的审计结论：

- `run_ifc_input_contract_repair.py` 的 `_scene_case()` 将每个 case 的 `exit_code` 固定写为 `0`。实际可独立确认的是 runner 进程退出码为 `0`、五个 payload 均存在且断言通过；case-level `exit_code` 不是五个独立子进程退出码。
- `repair_v1/fixture_probe.log` 的初次失败 traceback 含有当时版本的 `tempfile.TemporaryDirectory` 路径，而当前 manifest 只哈希了后续版本的 runner；因此失败尝试被保留，但没有旧 runner 版本的独立哈希绑定。

## Important findings

1. **原交付与返修已清楚区分。** 原 runner 是 `scripts/design/space_field/run_ifc_input_contract_experiment.py`；原 `experiment_results.json` 将 fixture 写成 `not_run_due_to_output_directory_permission_error`，其结构也不同于该 runner 的真实摘要；原 `provenance.json` 没有完整 runner argv、退出码或持久日志。返修使用另一个隔离的 `repair_v1/run_ifc_input_contract_repair.py`，并把成功的 `run_002` 结果与初次权限失败分开保存。
2. **原 Blender 失败是可复核的。** 原 `render_preview.py` 创建文本后直接保存并渲染，没有创建 camera；原 `.blend` 回读得到 `scene.camera=None`、camera object 数为 0。返修产物均有 `RepairPreviewCamera`，本次只读回读也以 Blender 5.2 退出码 0 确认。
3. **失败命令的精确复现性略弱。** `repair_command_log.json` 中 `portable_blender_saved_scene_inspection` 使用 `<saved blend>` 占位符，而不是两条完整 argv；对应的两个 inspection log、保存文件和本次独立回读仍足以支持 camera 结论。
4. **Blender 日志含环境噪声。** thumbnail、扩展缓存和 addon unregister 有权限/网络错误，但目标 PNG 已保存，render 与 blend readback 的目标命令退出码均为 0；这属于环境噪声，不是目标产物失败。

## Minor findings

- PNG 使用黑底浅色文字，原始尺寸为 live `1800x1400`、fixture `1900x1050`；在原始分辨率下文字可读。高分辨率布局留有较大空白，但不影响证据含义。
- 全局 `git diff --check` 的 stderr 被既有 `.tmp-test-preview-final2` 权限问题污染；返修报告已把该结果标为 incomplete。该问题与本次新增复核文档的 whitespace 检查分开记录。

## 逐项证据核对

### 1. 原交付、返修与失败边界

- 原 runner 实际包含 fixture writer、无 domain、显式 domain、缺 geometry 和断 opening relation 的调用位点；原输出 JSON 却写成 fixture 未运行，不能当作该 runner 的实际 payload。
- 原交付的 `experiment_results.json` 将 live geometry 写成 `not_run_timeout_guard`，但原 `provenance.json` 没有完整命令、stdout/stderr 或退出码。因此返修将 live geometry adapter 结论降为 **not verified**，没有重试 408 MB 几何适配。
- 原权限失败 traceback 实际记录了 IfcOpenShell 写 system temporary directory 失败及清理目录的 `PermissionError`；返修把 disposable IFC 固定放在选定的 `repair_v1` 输出目录。

### 2. 真实 IFC 只做原生盘点

对 `outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc` 做了只读 IfcOpenShell 盘点，结果为：

| 项目 | 结果 |
|---|---:|
| schema | `IFC4` |
| `IfcSpace` | 0 |
| `IfcOpeningElement` | 0 |
| `IfcRelVoidsElement` | 0 |
| `IfcRelFillsElement` | 0 |
| `IfcDoor` | 6 |
| `IfcWall` | 11 |
| `IfcFurniture` | 95 |

runner 的 live 分支只调用 `ifcopenshell.open()`、`by_type()` 和身份读取，并写入 `geometry_extraction: "not_run"`；没有 mesh extraction、写回或修改源文件。返修 PNG 也明确写出门实体不替代 IFC opening/void 关系。

### 3. disposable IFC4 fixture 已生成并实际运行

`run_002/fixture_workspace/ifc4_domain_closed_derived_fixture.ifc` 存在且只读盘点为 IFC4、`IfcSpace=1`、`IfcWall=1`、`IfcOpeningElement=1`、`IfcRelVoidsElement=1`、`IfcDoor=0`；临时复现目录有同样的 IFC4 fixture。`fixture_adapter_results.json` 含且仅含以下五个 case，顺序与临时复现一致：

- `no_domain`
- `explicit_domain_with_closed_geometry`
- `explicit_domain_without_geometry`
- `opening_without_voids_host_relation`
- `malformed_authored_grid_axis`

primary 和 `temporary_reproduction_2026-10-01_v2` 的 `cases` JSON 深度相等；两次 runner 进程退出码均为 0。

### 4. 实际 adapter 结果

- `explicit_domain_with_closed_geometry`：`analysis_domain.geometry_refs` 指向 `ifc-mesh:36LMq02kDVsOKNkNtVJHZu`，对应 mesh flags 为 `is_closed=true`、`is_manifold=true`。
- `explicit_domain_without_geometry`：domain record 仍存在，`geometry_refs=[]`，并保留真实 `UncertaintyRecord(code="missing_geometry")`。
- `opening_without_voids_host_relation`：opening record 和 geometry ref 保留，`host_refs=[]`；没有自动补 host，也没有把门实体改写成 opening relation。
- `malformed_authored_grid_axis`：unsupported 来自真实 `UncertaintyRecord(code="unsupported_grid_axis_curve")`，details 为 `failure_type="insufficient_polyline_points"`；payload 没有伪造统一 `unsupported` status enum。
- 五个 adapter payload 均没有 `free_space`、`connectivity` 或 `path/paths` 字段；下游 gate 只保留设计观察 `not_available` 与 `diagnostic_only`，不是 adapter 生成的结果。

### 5. Blender 产物

- `live_ifc_inventory_not_available.png` 只显示 IFC4 直接实体计数与 Door/Wall GlobalId/STEP 身份，包含精确标签 `NOT AVAILABLE — NO QUALIFIED ANALYSIS DOMAIN`，并写明没有显示 free-space、component、connectivity、path、walk 或 visibility result。
- `ifc4_fixture_source_facts.png` 只显示 domain、wall、opening、host relation 与 source IDs，并包含 `SOURCE FACTS ONLY — NO FREE-SPACE, WALKABILITY, OR VISIBILITY RESULT`。图中另有 projection scope 说明，没有把独立 tile 解释成统一分析平面。
- 两张 PNG 均通过 signature、IHDR、IDAT、IEND 和尺寸检查；本次直接查看原始产物，文字和 source-fact 标签可读。
- 本次使用规定的 portable Blender `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` 只读打开两个 `.blend`：两者 `scene.camera` 都是 `RepairPreviewCamera`，camera object 数均为 1；live 对象数为 4，fixture 对象数为 14。

### 6. Provenance、manifest、SHA-256、复现与命令

- repair manifest 的 21 个 artifact 条目全部存在，bytes 和 SHA-256 逐项匹配。
- `run_002/verification_report.json` 的 11 个 hash 条目全部重新计算匹配。
- primary 与 temporary reproduction 的五个 `cases` 深度相等；temporary reproduction 使用 `--skip-live-inventory`，因此 live inventory 为 `null` 是预期差异。
- primary fixture、temporary fixture、portable Blender render、saved blend inspection 和 JSON/hash verification 的持久 exit status 文件均为 `exit_code=0`。
- 初次 system-temp fixture 失败为 exit code 1，且 traceback 被保留；它没有被当成成功 fixture 证据。
- `git diff --check` 输出既有 `.tmp-test-preview-final2` 的 Permission denied；该全局检查应视为 incomplete。针对本次新增文档的独立 whitespace 检查单独执行。

### 7. 限制是否诚实

返修和结果文件均保持以下限制：

- live IFC geometry adapter：`not verified` / `not run`；
- 没有 production free-space backend；
- 没有 opening subtraction；
- 没有 door-state 验证；
- 没有 boundary scope、resolution、route width 或空间角色结论；
- 没有 Bayesian/ML 模型选择或结论；
- 没有正式 walkability、visibility、connectivity 或 path 结果；
- proposed status vocabulary 没有被冒充成统一 production enum。

### 8. 范围核对

复核时对 `features/`、`adapters/`、`test/`、`pixi.toml`、`pixi.lock`、`outputs/full-rhino-ifc-2026-09-23`、`analyzer.py`、`__init__.py` 和依赖配置执行 `git status --short`，均无当前状态变化。返修目录中的脚本和输出属于本实验范围；本次只新增本文件。没有运行完整 IFC 几何适配、完整 pytest 或历史实验，也没有改写 source IFC 或用户 Blender 文件。

## 未验证项

- live IFC 的几何提取、mesh 质量、闭合性、manifold 性和平面适配仍未验证。
- 返修没有验证生产 free-space backend、opening subtraction、door-state、boundary scope、resolution、route width、空间角色或 Bayesian/ML 模型。
- 初次失败尝试的旧 runner 没有独立 hash，因此只能证明该失败日志与当时命令路径相符，不能给出旧脚本字节级身份。
- case-level `exit_code` 不能替代独立 adapter subprocess 退出码；后续若需要审计级证据，应在每个调用边界记录真实异常/返回状态并哈希当时 runner。

## 实际读取文件、命令、技能与限制

### 文件

实际读取了 `AGENTS.md`、`docs/project/space-field-ifc-neutral-scene-input-contract.md`、`docs/project/evidence/d6-space-field-input-contract-owner-decision.md`、`docs/project/evidence/d6-space-field-ifc-input-contract-experiment.md`、`docs/project/evidence/d6-space-field-ifc-input-contract-experiment-repair-v1.md`、`docs/project/evidence/d6-space-field-ifc-input-contract-experiment-repair-v1-manifest.json`、`run_002/fixture_adapter_results.json`、`input_output_provenance.json`、`verification_report.json`、`repair_command_log.json`，以及原/返修 runner、renderer、verification、blend inspection、原始 experiment JSON/provenance/manifest、PNG、`.blend` 和持久日志。

### 有界命令

- `.pixi/envs/default/python.exe` + IfcOpenShell：只读盘点 live IFC 和 disposable IFC4 fixture。
- `.pixi/envs/default/python.exe`：解析 case payload、比较 primary/reproduction、重算 manifest 与 verification hash。
- portable Blender 5.2：只读打开两个返修 `.blend` 回读 camera/object；没有保存或重渲染。
- `git status --short`、`git diff --check`：检查范围与既有 whitespace 权限问题。
- `view_image`：查看两张 PNG 可读性与标签；没有编辑图像。

### 技能

本次只应用了 `stop-that-shit` 的 `review` 只读流程（`C:\Users\tianf\.codex\plugins\cache\stop-that-shit\stop-that-shit\0.2.2\skills\stop-that-shit\SKILL.md`）。没有运行完整 pytest、完整 IFC 几何适配、历史实验或生产后端。

STOP FOR SPACE FIELD IFC INPUT EXPERIMENT REPAIR INDEPENDENT REVIEW
