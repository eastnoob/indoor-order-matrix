# Quickstart 验证流程（计划）

此文件描述实施后的可执行验收步骤；Spec004 已于 2026-10-15 获用户批准，状态为 **APPROVED / IMPLEMENTATION IN PROGRESS**。未安装 addon、未操作 Blender、未完成 live validation；只允许 AGENTS 指定的 portable binary 与 Pixi。

## 前置条件

- **CURRENT TREE ABSENT prerequisite:** T0/version specialist 在隔离 clean environment 恢复并核验 `23d24a3` 的完整 approved dependency/import closure，保留 dirty history；缺失 Spec003 docs 只通过 `git show` 阅读。当前 request/plane/live-capture 缺失，现存 B4/domain handoff 不等于完整 baseline。未经核验不运行以下实施验收。
- 安装仓库锁定环境：`pixi install`。
- `D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe` 可用；禁止检查/启动其他 Blender。
- 一个可读的 Bonsai IFC4 linked scene，live source inventory 可完整捕获。没有现场合法当前 ROI 确认时，可验证 UI/refusal，但不能宣称 occupancy acceptance 完成。
- 实现后将 addon zip 安装/enable，偏好中的 repository root 指向本 repo；runtime 自动验证 `.pixi/envs/default/python.exe`，不能在导入结果中指定 executable。

## 单元和合约验证

```powershell
pixi run python -m pytest test/test_bonsai_live.py test/test_blender_analysis_capture.py test/test_blender_analysis_session.py test/test_blender_analysis_runtime.py test/test_blender_analysis_overlay.py -q
pixi run python -m pytest test/test_analysis_requests.py test/test_free_space_field.py -q
pixi run python -m pytest test/test_b3_live_scene_capture.py test/test_b3_live_analysis_request.py test/test_b3_occupancy_only_handoff.py test/test_bonsai_analysis_plane.py -q
```

预期：canonical GUID/STEP/proxy coverage 一对多或冲突测试拒绝错误映射；localized unknown edge cases、六态和 occupied-wins 通过；完整 `FieldSample` compact serialize/reconstruct equality；altered job/plane/key/digest 不发布；单旧调用未提供 `unresolved_supports` 保持原语义。每条命令的真实 exit/output path 由实现任务写入 `checklist.md`。

统一 workbench 的 headless consumer 验证包含在 `test/test_blender_analysis_session.py`：列出 domain/free-space metadata、按 immutable ResultRef 精确 open、读 cell/reconstruct 全部证据；不同 domain/plane/mode/revision/source 隔离，missing/ambiguity/version/digest/mismatch 与 stale-as-current 拒绝；current 内 unknown/conditional 不改写，历史访问显式允许，未确认 domain=None 仅可作诊断读取而不能供应 confirmed/current-domain consumer。sentinels 证明读取不 capture/compute/spawn/mutate，嵌套修改不能回写权威内容。live 内存文档与删除 sidecar 后恢复的 embedded 文档走同一入口。这是消费合约测试，没有已有真实下游分析 consumer。

## Native addon 真正 operator smoke

实现后先产出 addon zip，在唯一 portable binary 中执行：

```powershell
$blender = 'D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe'
$repoRoot = 'D:\PROJECTS\understandOtherPackage\order_analyzer'
$runName = 'run_' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '_' + [Guid]::NewGuid().ToString('N')
$runDir = Join-Path $repoRoot ('outputs\design\blender_analysis_workflow\' + $runName)
& $blender --background --factory-startup --python-exit-code 1 --python (Join-Path $repoRoot 'test\bim\run_blender_analysis_workflow_smoke.py') -- --phase smoke --repo-root $repoRoot --output-dir $runDir
if ($LASTEXITCODE -ne 0) { throw 'Native smoke failed' }
$reportPath = Join-Path $runDir 'smoke_report.json'
if (-not (Test-Path -LiteralPath $reportPath)) { throw 'Successful report missing' }
$smokeReport = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
if ($smokeReport.status -ne 'success') { throw 'Smoke report did not assert success' }
```

Smoke 必须实际调用 register/install-supported path、N→Analysis class/operator、plane create、B4 refresh/select/explicit test action、Start/cancel/error, inspection, Save Copy/reopen reader；其中明确确认只可用 test fixture 中标注为 synthetic actor 的 disposable domain 并不得当成 live-human acceptance。addon UI 注册在真正 VIEW_3D 测试时还需手工或 UI automation 检查 category=`Analysis`、文字可读、六态不只靠颜色。Smoke 仅证明实现链和 native APIs，不证明 IFC/B3。

Smoke includes an injected native `bpy.ops.wm.save_as_mainfile` exception after creating an addon-owned partial target. Its report must prove live Text bytes/overlay/result identities remain intact, only owned partials are removed, unrelated files remain, and no saved artifact is recorded. A subsequent successful Save Copy records its artifact only after native success. Pure runtime coverage is planned as `test_save_copy_exception_preserves_live_truth_and_cleans_owned_partial`; no such test or smoke has run in this design pass.

Smoke 生成 unique addon zip；输出固定在 `D:\PROJECTS\understandOtherPackage\order_analyzer\outputs\design\blender_analysis_workflow\run_<UTC-and-UUID>`。Background 必须用真实 runtime timer/bounded main-thread pump 等待真实 async job，完成并写出 `status=success` 的 `smoke_report.json` 才退出；timeout/error 抛错触发非零 exit，不能 Start 后立即结束。JSON/Text/mesh/capture/polling 均分批并记录 callback/不可分割调用耗时、JSON bytes、mesh counts；超过 50 ms 目标如实记录并缩小后续 batch。Addon import 不加载 Shapely/heavy core；Pixi 预计算 clipped fragments/triangulation。

重开必须使用成功报告中的实际 `saved_copy_path`，禁止填写样例文件名：

```powershell
$savedCopyPath = $smokeReport.saved_copy_path
if (-not (Test-Path -LiteralPath $savedCopyPath)) { throw 'Recorded saved copy missing' }
$reopenDir = Join-Path $runDir 'reopen'
& $blender --background $savedCopyPath --python-exit-code 1 --python (Join-Path $repoRoot 'test\bim\run_blender_analysis_workflow_smoke.py') -- --phase reopen --repo-root $repoRoot --blend-path $savedCopyPath --output-dir $reopenDir
if ($LASTEXITCODE -ne 0) { throw 'Native reopen failed' }
$reopenReportPath = Join-Path $reopenDir 'reopen_report.json'
if (-not (Test-Path -LiteralPath $reopenReportPath)) { throw 'Reopen report missing' }
if ((Get-Content -Raw -LiteralPath $reopenReportPath | ConvertFrom-Json).status -ne 'success') { throw 'Reopen report did not assert success' }
```

## 两模式现场验收

1. 安装并 enable 新包；配置 repo root；检查只有一个 `N → Analysis` 面板，Domain / Free-space 两个 section 可各自折叠/展开。Domain 不依赖 free-space Start 可独立使用。plane UUID/revision 首次创建；全高默认、0.25 m；exact query 的 displayed height = frozen plane origin Z；B4 单独展示 datum0/cut1.5。
2. 先操作 Refresh/Select，不按 Confirm，验证 Start 拒绝且未复用历史 S3。通过 fresh capture 选择 B4 候选，查看 exact boundary source IDs/holes/refusals；只有真实用户点击 Confirm 后 domain 才 active。检查未绑定 floor support 时 warning 且真实 slab remains occupancy。

   Domain-only evidence also covers finite nonnegative tolerance mm² (one conversion to m²), closed doors/windows assumption, source/geometry counts, candidate id/version/area/holes/reason, actual outline/hole curves/labels, error/refusal/current/last-attempt/stale and ignored tiny/significant aperture residual diagnostics. Compare original authoritative B4 service payload; do not claim reducer-only replace/conflict as prior UI parity.
3. 运行 whole-height。记录 `capture / B4 / subprocess / result validation / overlay` 的真实 elapsed、processed/total、单个最长 `to_mesh` callback；期间转动视图和面板仍可响应。观察 plant/counter/furniture 是否按物理实体计入，proxy owners exact-once；记录所有 unresolved sources。
4. 在同一当前 ROI 下运行 exact section，必须显示 query height=plane snapshot `origin.z`，不可通过第二个 Z field 变更。按 row,column 重建完整样本，核对 local unknown / known occupied / six status / support_status。visual overlay clip holes 和 partial domain cells；面积只用 grid-classified clipped area 标签。
5. 启动另一次期间改 source/plane、触发 undo 或 switch scene：结果不得发布 current；旧 mesh 留在原冻结位置并 stale。cancel 和进程错误后旧结果保留。验证 overlay 未 parent 到 plane/camera。
6. 用 Save Copy 存到明确新 `.blend`；确认原 `.blend` 与 IFC byte/stat/history facts 未变。删除 sidecar，开独立第二 portable process 打开 copy；检查 recovered Text schema/digest、mesh、plane/run/source identities/所有 cell samples 与保存前一致，Freshness=historical/unverified 且没有后台自动运行。

   使用同一 list/open/read 接口比较 live 与 restored domain diagnostics 和 free-space samples；exact refs/identities 相同，reopen 仅 contextual freshness 降为 historical/unverified。要求 current 的读取必须拒绝；显式 historical read 保留全部 unknown/conditional/provenance，不运行分析。
7. 将现场唯一确认细节、两 query keys、source fingerprints、IFC unchanged checks、elapsed 和输出 paths 填进 checklist。用户尚未提供有效 current domain 选择时，停在需要用户做何动作的具体提示，不能造出结果。

## Completion boundary

设计、fixture smoke、native API probe 和 live IFC acceptance 是不同证据级别。只有步骤 1–7 的当前 live/重开证据和独立 review 完成后，才能把实现状态从 draft 更新；本 quickstart 本身不表示这些已执行。
