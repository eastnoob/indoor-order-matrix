# Quickstart — Spec008 验证指南

日期：2026-10-19。以下是**实施后的验证入口**，本规划轮未执行这些功能测试或 native 操作。当前主树缺工作流依赖；必须先完成 [plan 的 T0](plan.md#实施顺序与交付门槛)，再在恢复完整闭包的 task-owned jj workspace 根目录运行。不可用旧 smoke PASS 代替 [R01–R12](contracts/workflow.md#8-r01r12-覆盖) 的新增断言。

## 1. 前置与环境

保留原工作区 dirty work，使用 jj 隔离工作副本。记录恢复来源 revision、实际文件完整 SHA256、导入/config/fixture/export 闭包和冲突处理依据；workflow007 冲突不能直接传播。不要在验收时混用另一个工作副本的 addon 字节。

在已恢复工作副本的 PowerShell 中运行：

```powershell
$workRoot = (Get-Location).Path
jj --ignore-working-copy workspace list
jj --ignore-working-copy status
pixi run python --version
$blenderExecutable = 'D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe'
if (-not (Test-Path -LiteralPath $blenderExecutable -PathType Leaf)) {
    throw 'Required portable Blender is unavailable.'
}
$requiredFiles = @(
    'blender_addon/order_analyzer_ui/__init__.py'
    'adapters/bonsai_analysis_plane.py'
    'adapters/bonsai_live.py'
    'adapters/blender_analysis_session.py'
    'adapters/blender_analysis_capture.py'
    'adapters/blender_analysis_result_wire.py'
    'features/analysis_requests.py'
    'test/bim/run_analysis_plane_bonsai_smoke.py'
    'test/bim/run_blender_analysis_workflow_smoke.py'
)
foreach ($relativeFile in $requiredFiles) {
    $absoluteFile = Join-Path $workRoot $relativeFile
    if (-not (Test-Path -LiteralPath $absoluteFile -PathType Leaf)) {
        throw "T0 dependency is missing: $absoluteFile"
    }
    Get-FileHash -LiteralPath $absoluteFile -Algorithm SHA256
}
```

预期 Pixi 为 Python 3.12.13；portable 内嵌 Python 是另一套 native 运行时。环境尚未建立时先用 `pixi install` 按 lock 安装，再重复上述检查；不用 pip/venv，也不寻找其他 Blender。

## 2. 定点与回归

先在 T0 恢复基线上重现已记录的 R10 失败；修复后用同一断言转绿，保留前后输出：

```powershell
$eligibilityRegression = (Join-Path $workRoot 'test/test_physical_occupancy_resolution.py') + '::test_furniture_exclusion_vetoes_direct_group_and_affordance_contribution'
pixi run pytest $eligibilityRegression -q
```

历史现象是 view 排除 A、physical_occupancy 保留 A/B 均通过，而 group.support_area 为 4.0、应为 None。不要改断言掩盖该差异。随后运行受影响的既有测试：

```powershell
$focusedTests = @(
    'test/test_analysis_requests.py'
    'test/test_bonsai_analysis_plane.py'
    'test/test_bonsai_live.py'
    'test/test_blender_analysis_capture.py'
    'test/test_blender_analysis_session.py'
    'test/test_blender_analysis_ui.py'
    'test/test_blender_analysis_regions.py'
    'test/test_blender_analysis_runtime.py'
    'test/test_candidate_preview.py'
    'test/test_physical_occupancy_resolution.py'
) | ForEach-Object { Join-Path $workRoot $_ }
pixi run pytest @focusedTests -q
```

`test/test_bonsai_space_authoring.py` 是计划新增文件，实施后再运行，不把缺文件当当前回归失败：

```powershell
pixi run pytest (Join-Path $workRoot 'test/test_bonsai_space_authoring.py') -q
```

预期：上述受影响测试通过，旧调用与持久化兼容；adapter 测试不代替真实 native 几何/历史恢复证明。新增测试按 [data-model](data-model.md) 与 [workflow contract](contracts/workflow.md) 检验，避免只 mock 一次函数调用就宣称闭环完成。

## 3. 必须覆盖的输入矩阵

复用/扩展既有 fixtures；测试期望、线/面积/体积比较阈值及单位在运行前固定并写入证据，不为匹配实际结果事后放宽。B4 gap-closing 容差与 authoring round-trip 精度分别记录。

| 场景 | 预期 |
| --- | --- |
| Storey-only，base=0，明确 manual height=3m | 合法，base=0/top=3m；不要求 slab 或 authored quantity |
| Slab-only，水平上表面=0.2m，manual height=3m | 通过唯一 native 关系解析 storey；base=0.2/top=3.2m；不要求重复填 storey |
| 唯一 GrossHeight=3200mm，项目米/毫米及 quantity Unit override | SI height=3.2m；来源完整，换算一次；零/负/NaN/缺失/歧义量不能自动选用，可走 manual |
| 缺层高但存在相邻 storey elevation | 不自动相减、不用默认值；手动高度可独立继续 |
| Slab 斜面、多级顶面、非唯一高程或关系冲突 | 明确拒绝，不能取 bbox/maxZ 或静默投平；共面三角片允许合成唯一上表面 |
| Native drawing 新建、采用已有、refresh、删除/移动/替换 | 身份与修订准确；改动使旧确认失效；新建取消不残留；unsupported tilt/query 拒绝 |
| 正常层墙与 selected-wall，含内部未选墙、开放边界 | 两模式可用；内部墙继续生效，开放不虚构闭合，normal 清旧 selection scope |
| 凹 shell + 至少一个 hole + 非零 base | native shell/holes/净面积/base/top/volume 与冻结输入一致；scene scale/object transform 不重复换算 |
| 自交、越界/接触 holes、意外 MultiPolygon、stale candidate | 创建前拒绝；不 repair/丢洞/丢片段/seed 重围合；IFC 保持原状 |
| Furniture included/excluded/unknown/unset，direct group/trend/affordance | shared policy 一致；无 eligible members 时不可用值正确，raw refs 与 physical inventory 保留 |
| Whole-height、exact section、finite band，抬高 plane | query 身份与能力明确，whole-height 不暗改；其他实体继续占用；unknown 不冒充 free |
| 既有 IfcSpace 错类型/缺几何/错层/多几何 | 原资格拒绝保持；有效 Space 不要求 B4/新建高度前置 |

## 4. Disposable native 验证与两条保存重开

以下 CLI 参数已按现有 delivery scripts 核对。实施时必须扩展 scripts 的 008 断言；旧脚本成功只说明旧检查成功。所有输出位于当前隔离 workspace 内的独立新目录；仅使用 disposable IFC/Blend，不打开生产文件。

```powershell
$runStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$evidenceRoot = Join-Path $workRoot "outputs/spec008-$runStamp"
$cameraScript = Join-Path $workRoot 'test/bim/run_analysis_plane_bonsai_smoke.py'
$workflowScript = Join-Path $workRoot 'test/bim/run_blender_analysis_workflow_smoke.py'
$cameraEvidence = Join-Path $evidenceRoot 'camera'
& $blenderExecutable --background --factory-startup --python $cameraScript -- --output $cameraEvidence
if ($LASTEXITCODE -ne 0) { throw 'Native camera validation failed.' }
```

camera 脚本须证明 new drawing/adopt/refresh/取消与故障恢复，而非仅 CameraBinding 单独读取。之后分别跑 B4 新建和既有 Space：

```powershell
$newSpaceEvidence = Join-Path $evidenceRoot 'new-space'
& $blenderExecutable --background --factory-startup --python $workflowScript -- --repo-root $workRoot --output-dir $newSpaceEvidence --phase smoke --fixture-mode selected_walls --native-create-space
if ($LASTEXITCODE -ne 0) { throw 'New Space workflow failed.' }
$existingSpaceEvidence = Join-Path $evidenceRoot 'existing-space'
& $blenderExecutable --background --factory-startup --python $workflowScript -- --repo-root $workRoot --output-dir $existingSpaceEvidence --phase smoke --fixture-mode authored_ifcspace
if ($LASTEXITCODE -ne 0) { throw 'Existing Space workflow failed.' }
```

两条均需证明 native camera→正确 Space→free-space，并保存准确 source/plane/domain/query identity、provenance 与历史。新建必须额外校验 shell/holes、base/height 和准确返回 GUID，不接受 seed 操作成功作为 R08 证据。

对两份已保存副本分别用新进程重开。现有脚本要求文件名为 `saved_copy.blend`，且输出必须为该文件同级 `reopen` 目录：

```powershell
foreach ($savedRun in @($newSpaceEvidence, $existingSpaceEvidence)) {
    $savedBlend = Join-Path $savedRun 'saved_copy.blend'
    $reopenEvidence = Join-Path $savedRun 'reopen'
    & $blenderExecutable --background --factory-startup --python $workflowScript -- --repo-root $workRoot --output-dir $reopenEvidence --phase reopen --blend-path $savedBlend
    if ($LASTEXITCODE -ne 0) { throw "Save/reopen failed: $savedRun" }
}
```

预期重开保留 native 身份与必要参数，恢复为 requires_recheck；未经重新 resolve/capture/复核不得自动确认或运行新结果。历史结果按原契约可读取，不能从 display mesh 重建 Field。旧脚本如缺 008 检查应先补断言，不把缺检查的 PASS 算完成。

## 5. Native 故障恢复门槛

在独立 disposable fixtures 中，按 [恢复契约](contracts/workflow.md#5-取消失败与恢复) 对 camera 创建、profile、entity、class/storey、representation assignment、switch 和 round-trip 分别注入故障。具体注入入口由实施测试扩展，当前 CLI 不虚构不存在的 fault 参数。

每次记录操作前后 IFC entity/relationship 集合、owned Blender object/mesh/camera/collection、IFC links、transaction key/history/redo、cursor/selection/container。预期恢复到本操作前边界，既有无关操作保持；再试只创建一份有效结果，成功后的 undo/redo 不破坏绑定。分别覆盖开放事务和已 finalize 失败；明确拒绝无关活动事务。

只删 mesh、返回 CANCELLED、catch 异常、比较 entity 总数或无界 undo 均不足以通过。恢复失败必须报告并阻止成功发布/自动保存，R09 保持未通过。

## 6. 真实 UI / GPU 与性能

在指定 portable 的真实窗口验证两条 camera 入口、已有 Space 视口/列表入口、两种 B4 模式、storey/slab、authored/manual height 和完整 progress/cancel/candidate/eye/area/diagnostics。逐条记录用户动作与对应结果；headless 不能替代选择/hover/overlay/GPU 验收。

记录全场 source capture 和局部结构计算各自的 source 数、耗时、缓存命中与取消行为，确认 selected-wall 没有暗中漏掉内部墙或把全场加载成本写成零。不新承诺未测延迟。

## 7. 交付证据与完成判定

证据至少包含：恢复 revision + 实际完整 SHA256、fixture/输入及单位、运行命令、各需求断言与输出、native geometry 对照、故障矩阵、两条 smoke/reopen 报告、UI/GPU 记录及计时。实际加载进程内记录 addon/adapters 的 `__file__` 与完整 SHA256，并和待交付文件比较；只证明 operator 注册不能证明加载了本轮实现。

只有本 feature 实际通过的 R01–R12 才能勾选 [checklist](checklist.md)。旧失败历史保留；未执行/未通过检查明确列出。B3 OPEN，不因 Spec008 的局部验证关闭；不自动提交、推送、合并或部署生产。
