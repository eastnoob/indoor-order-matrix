# Geometry and IFC Input Design: Independent Review Handoff

Date: 2026-10-01

Controller decision: independent review required; no representation, resolution or production implementation is approved. The controller read the delivered design table and result records, but did not run or audit the experimental code.

你是新的独立复核 session，不是上一轮实验执行者。
项目：D:\PROJECTS\understandOtherPackage\order_analyzer
任务：只读核查设计实验和 IFC 输入盘点。发现问题只报告，不修改实验或生产代码。

## 读取与技能

先读 AGENTS.md、架构记忆、总体自描述设计表，以及：
- docs/project/d6-space-field-geometry-ifc-design-handoff.md
- outputs/design/space_field_geometry_ifc_review/experiment_design_table.md
- outputs/design/space_field_geometry_ifc_review/baseline/space_field_probe_results.json
- outputs/design/space_field_geometry_ifc_review/polygon_baseline_results.json
- outputs/design/space_field_geometry_ifc_review/ifc_input_inventory.json

从设计记录和 manifest 定位真实 runner、fixtures、源 IFC 和全部可视化。
若复现脚本、fixture 坐标、运行命令或 provenance 缺失，列为不可复现缺口，不替执行者补写。
读取并实际应用 experimental-design、scientific-critical-thinking、scientific-visualization、verification-before-completion。
同时搜索项目、全局和已声明插件路径；不可用时明确记录等价检查，不虚称使用。

## 必查问题

1. 逐项比较设计表和实际执行：旋转角度、domain/obstacle 旋转对象、孔、窄开口、断开区域、resolution、origin、runtime、缩放和预先声明的验收规则。
   标出 planned、executed、unsupported、missing；名称不是执行证据。
2. 三个 narrow_opening_0.4/0.8/1.5 的输出完全相同。
   查实际 fixture 坐标及生成过程，独立测量开口宽度；验证宽度参数是否进入几何，是否真有控制连通性的瓶颈。
   相同输出不是自动判错，但必须用几何事实解释。若只是改名或宽度未生效，列为 blocker。
3. subcell 敏感 fixture：用独立计算和实际坐标确认面积及连通性，包括正面积连通、边接触和点接触的区别。
   核实连续几何与四邻域栅格的连接语义是否一致。
   不因持续误差就断言程序缺陷；需要定位证据才可区分采样效应、边界处理、代码缺陷和 oracle 假设。
4. 核对所谓 polygon baseline 是向量几何本身，还是仍然基于 polygon 的中心采样。
   明确几何布尔运算结果与采样结果，不能把更换 contains 后的 sampler 称为精确拓扑保证。
   Oracle 不应只是再次调用被测几何流水线；可手算的面积/连通性须独立核对。
5. 只读核查源 IFC 路径/hash、schema、单位和 ObjectType 家具资格。
   区分“存在 placement/representation”与“实际提取并验证 world-space 几何”。
   确认显式 domain 是不存在、未选择还是未解析，不要用一句 not_selected 混淆。
   保留门几何与 opening relation 的区别；家具节点、context、typed substitutes 各有来源。
   盘点不等于真实 IFC 空间场验收，缺失域不能回退到包围盒。
6. 在独立临时输出目录复现可执行实验，不覆盖原交付文件。
   检查确定性 payload、schema、hash、实际图像、资源限制与状态传播。
   可视化裁剪不得掩盖采样统计或修改 oracle；查清源几何与绘图对应关系。
7. 检查修改范围和提交信息；保留既有 dirty/untracked，不将其归因于本任务。
   不运行会覆写源证据的命令，不安装依赖，不启动其他 Blender；如确需渲染，仅使用 AGENTS 指定 portable executable。

## 输出与停止

仅允许新增：
docs/project/evidence/d6-space-field-geometry-ifc-independent-review.md
复现实验输出放临时目录，可在报告引用必要图像和日志，不能覆盖既有产物。

报告包含 Blockers / Important / Minor、真实命令、复现结果、设计表覆盖矩阵、独立 oracle、源文件/hash、未决问题。
裁决按证据分别给：subcell 原因分析、polygon 对照、IFC 输入盘点。
总体为 ACCEPT LIMITED DESIGN EVIDENCE 或 REVISE；明确下一阶段最小缺口。
禁止批准 production backend、resolution、space-role threshold、API、selector 或 Bayesian/ML 生产模型。
完成后停止：

**STOP FOR SPACE FIELD GEOMETRY AND IFC INPUT INDEPENDENT REVIEW**
