# 阶段 0 审计索引

日期：2026-09-27。首轮只完成审计和原始需求归档，未开始功能开发或架构重构。

## 原始来源

- docs/project/raw_requirements/source-01-b044dcf0.txt
- docs/project/raw_requirements/source-02-17de9dce.txt
- docs/project/raw_requirements/README.md
- Spec Kit intake（本机状态）：.specify/assessments/bim-furniture-layout/intake.md

两份副本与用户附件的 SHA-256 已核对相同。现有 docs/indoor_layout_evaluation_matrix_original_prompt.md 是旧记录，哈希不同，不替代本次原话。

## 可复核基线

- pixi 0.69.0 / Python 3.12.13；IfcOpenShell 0.8.5、Shapely 2.1.2、Trimesh 5.1.0、NumPy 2.4.3。
- 指定便携 Blender 5.2.0 LTS 可执行；Bonsai 源码目录存在，但后台 Blender 直接 import bonsai 失败（ModuleNotFoundError）。
- pixi run pytest test/ -q：740 passed in 360.11s。
- test/output/current_blender_four_chairs.ifc：IFC4 inspect/EXPRESS validation passed，但只有 4 个家具和 1 个组，缺少房间/柱网/边界/可供区域。
- .tmp-blender-mcp-terminal-trend/bim_acceptance.ifc：包含丰富对象和派生输入，但 EXPRESS validation failed（IfcGrid 放置和多个产品 ObjectPlacement 缺失）。
- evaluate_scene 的 completion audit 为 completion_ready=false；路由、视觉、柱网仍是 proxy，材料/边界是 metadata handoff，live BIM/Rhino adapter 延后。
- 未发现 Blender/Bonsai 插件 UI、live mode 或完整缓存失效实现；现有输出是中立场景、指标行和预览/JSON/SVG 等证据。

## 技能使用

本轮实际采用：speckit-assess-intake、ifc-bim-conversion-workflow、analysis-substitute-discovery、bim-logical-object-mapping、superpowers:verification-before-completion。学术检索和 Spec Kit 后续阶段技能已发现但未执行；本轮没有新增外部论文/网页证据。

## 门禁

下一阶段仍需用户决定：首个研究问题及感知结果、首条输入源、是否先修复丰富 IFC fixture、Bonsai 目标安装/版本和首版指标范围。
