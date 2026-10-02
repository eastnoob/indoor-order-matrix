# Space Field Oracle Repair: Owner Decision and Handoff

Date: 2026-10-01

## Controller Decision

Based on `docs/project/evidence/d6-space-field-geometry-ifc-independent-review.md`:

- Subcell causal analysis: REVISE. The literal fixture has area 19.2 and three continuous free-space components. The prior one-component claim is contradicted by the independent review. Persistent fine-grid disagreement and a sampler implementation defect are not established.
- Polygon comparison: ACCEPT LIMITED DESIGN EVIDENCE. Source polygon geometry and raster center sampling are different objects; the latter does not guarantee exact topology.
- IFC inventory: ACCEPT LIMITED DESIGN EVIDENCE for the recorded source/hash/schema/units/entities. Source placements and representations alone do not prove extraction correctness. No IfcSpace exists in this source; do not infer the absence of every possible externally supplied domain solely from this count.
- The first diagnostic slice remains closed as a historical bounded delivery, but its accepted one-component/persistent-distortion interpretation is superseded by this correction. Previous evidence must receive an explicit correction note rather than silently retain the contradicted interpretation.
- Production geometry backend, resolution, roles, selector, API and Bayesian/ML remain unapproved.

The controller read the independent report; no tests or source audit were performed by the controller.

## Prompt: Send Back to the Geometry/IFC Experiment Session

请完成一次有界设计证据返修，不是重新启动全套研究或生产开发。
项目：D:\PROJECTS\understandOtherPackage\order_analyzer
先读 AGENTS.md、架构记忆及上述独立复核报告和本裁决。
实际读取并应用 experimental-design、scientific-critical-thinking、scientific-visualization、verification-before-completion；记录路径、动作与结果。技能不可用时报告，不安装依赖。

### Required Changes

1. 保留原 subcell 坐标作为历史 fixture，把该 fixture 的 topology oracle 修正为三个分量；保留独立面积 19.2。
   用实际坐标说明各连通区域，不得只把期望值改成 sampler 输出。
   在原设计/结果解释中加入版本化更正，撤回“细网格持续失真证明实现缺陷”等结论；独立复核文件保持原样。
2. 若要继续测试原来的单连通瓶颈意图，另建明确的一连通 fixture，不覆盖原 fixture。
   给出独立几何图解/oracle；加入闭合与正宽开口的最小对照，明确连接语义。
   只比较预先声明的少量 width/phase；正宽开口不必让精确拓扑改变，栅格是否漏掉连接才是观测。
   不引入 corridor/activity 的生产阈值，也不把几何连接等同可通行性。
3. 把现有 inline polygon probe 保存为独立可复现脚本，记录实际 fixtures、角度、单位、seed（若有）、resolution、origin 和命令。
   标清 source polygon area/components 与 sampled area/components，不再称后者为精确拓扑基线。
   支持 --output-dir 临时复现；优先重用现有逻辑，不搭建通用框架。
4. 更新设计表执行覆盖矩阵：未执行角度/缩放等如实列 partial/deferred，不为补齐表格扩大实验。
   修正 IFC 表述：该样本 IfcSpace=0、无本次可用的显式 IfcSpace domain；外部 domain 未提供。
   区分输入实体存在、adapter 能力与已实测提取；不虚构 opening/affordance，不使用场景包围盒。
5. 只重跑受影响的 resolution/origin 对照和保存脚本的临时复现；无需重跑无关全套测试或再次解析整个 IFC 来证明相同 inventory。
   产出更正前后结果和原因表，以及原三分量/新一分量对照图。
   实际查看图像；优先使用此前可用的 svglib/ReportLab 或其他已装渲染路径，不因 cairosvg 缺失安装依赖。不可用则记录环境限制。
6. 更新 manifest、确定性比较、oracle/status assertions、git diff --check 和范围审计。
   报告有限证据与未决事项，禁止自行宣布算法、分辨率或真实 IFC 空间场通过。

### Scope and Return

只允许 docs/project、scripts/design/space_field、outputs/design 下本任务路径；新增脚本必须放 scripts/design/space_field，保存必要 provenance。
不得修改 features、adapters、正式测试、公共 API、依赖、源 IFC、用户 blend 或既有独立复核报告。
保留用户 dirty/untracked；Git 仅提交明确路径，不 git add .，不破坏性清理。

交回：commit、修复记录、保存的 runner 路径、oracle/结果对照、图片、manifest、验证命令和限制。
下一次独立复核仅针对本次更正与复现缺口，不重复验证已接受的无关输入盘点。

**STOP FOR SPACE FIELD ORACLE REPAIR REVIEW**
