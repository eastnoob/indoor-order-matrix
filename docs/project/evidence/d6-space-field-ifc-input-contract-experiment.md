# D6 空间场 IFC → Neutral Scene 输入契约有界设计实验

日期：2026-10-01。范围：只读输入盘点、当前 adapter 能力边界、provenance 与不可用状态观察；未实现空间场算法。

## 事实

直接读取真实 IFC 得到 IFC4；IfcSpace=0、IfcOpeningElement=0、IfcRelVoidsElement=0、IfcRelFillsElement=0、IfcDoor=6、IfcWall=11、IfcFurniture=95。源文件未修改。项目既有记录的 MILLI METRE 单位未在本次原生计数脚本中重复确认，保留为历史引用而非本次观察。

## 当前代码能力

`adapters/ifc_bonsai.py` 只接受显式 `analysis_domain_source_id` 选择 spatial element；无选择时 `analysis_domain=None` 并写入 `missing_analysis_domain` uncertainty。`SourceOpening` 来自 `IfcOpeningElement.VoidsElements`，当前 schema 允许空 `host_refs`；opening subtraction、通行性和 visibility 不是 adapter 输出。`features/neutral_scene_views.py` 可从源几何生成诊断 view bounds；这不能创建 AnalysisDomain。

## Fixture / probe 观察

本轮输出目录权限导致 IFC4 fixture 文件写入失败，因此未把 fixture adapter 结果冒充已执行结果。已保留可复现脚本 [run_ifc_input_contract_experiment.py](../../scripts/design/space_field/run_ifc_input_contract_experiment.py)；它包含正向、无 domain、缺 geometry、断开 opening relation 以及 partial/conflict/unsupported 观察位点。真实 IFC adapter 几何加载超过有界时间并被终止，记录为 `not_run_timeout_guard`。

## 状态与下游

`available/partial/missing/invalid/ambiguous/conflict/unsupported/not_available/diagnostic_only` 仍是设计候选，不是统一现有 API。无合格 domain 时 free-space、components、connectivity、path 均保持 `not_available`；诊断 bounds 只能为 `diagnostic_only`。门默认关闭仍只是 owner scenario assumption。

## 可视化

使用规定 portable Blender 尝试生成 disposable blend；blend 保存成功，但渲染因无 camera 失败，未生成 PNG。没有伪造 free-space。输出目录中的 blend 与日志状态应视为失败证据。

## 验证与停止结论

已运行 Pixi Python 版本检查、IFC 原生计数、受限 adapter probe、portable Blender 调用、JSON/hash 生成和路径范围状态检查。`git diff --check` 受既有 `.tmp-test-preview-final2` 权限错误影响，未通过；该目录属于既有 dirty 内容。本实验停止在设计验证阶段：未批准 production implementation，未修改 features、adapters、正式 fixture、测试、公共 API、依赖、源 IFC 或用户 blend。
