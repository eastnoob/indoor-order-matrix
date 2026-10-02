# Space Field Oracle Repair: Bounded Independent Review

Date: 2026-10-01

Controller status: repair delivered; independent acceptance pending. The controller read the repair record and comparison table, not the experimental implementation, and ran no tests.

你是独立复核 session，不是 oracle 返修执行者。
项目：D:\PROJECTS\understandOtherPackage\order_analyzer
只复核本次 oracle 更正、瓶颈对照和保存脚本的可复现性。
不得重复整个 IFC 盘点、历史图例返修或无关全套 pytest；不得修代码。

## Read

先读 AGENTS.md、架构记忆、docs/project/d6-space-field-oracle-repair-owner-handoff.md。
本次交付目录：outputs/design/space_field_oracle_repair/
读取以下交付：
- oracle_repair_record.md
- rectangle/space_field_probe_results.json
- polygon/polygon_baseline_results.json
- oracle_correction_comparison.md 和 .json
- subcell_corrected_source.svg
- connected_bottleneck_source.svg
- artifact_manifest.json

读取 scripts/design/space_field/run_polygon_baseline.py 及矩形 runner 的相关修改。
按需参考上一轮 docs/project/evidence/d6-space-field-geometry-ifc-independent-review.md，不重跑其已接受的 IFC inventory。
应用 experimental-design、scientific-critical-thinking、scientific-visualization、verification-before-completion；记录实际技能路径、动作与不可用原因。

## Required Checks

1. 原 subcell fixture 坐标确实未改；面积 19.2 和三分量由独立坐标推导支持。
   区分源几何三分量与采样 2/3 分量，不能根据采样输出倒推 oracle。
   确认原一分量和持续失真/程序缺陷论断已在相关报告中明确更正；历史独立 review 不得改写。
2. 新瓶颈 fixture 使用独立 ID，检查源几何面积 36.0、一分量的真实坐标依据和边界连接语义。
   核查 owner handoff 要求的闭合/正宽开口最小对照是否存在及是否有效。
   若只有一张容易通过的一分量图，明确其不足；不因名称包含 bottleneck 就认定测了瓶颈。
   参数是否真正改变几何、source 与 sampled topology 是否分别记录，均需核实。
   不能因这次全为一分量就声称任意窄开口采样稳定或可通行。
3. Polygon runner 是否完整保存了原 inline 流程、fixture 坐标、resolution、origin、单位/单位未指定状态、版本与命令。
   分开 source polygon 布尔几何结果和 center-sampled rows；不得用同一路径的结果作为独立证明。
   新 runner 是可复现实验，不是生产 API。
4. 仅用两个 runner 的 --output-dir 指向新的临时目录复现，不默认运行、不覆盖交付。
   与交付结果比较确定性 payload，runtime/绝对路径单独处理；记录命令、exit、状态和 schema/hash。
   不修改或安装依赖，不执行会覆盖证据的命令。
5. 实际查看两张 source SVG，核对与 fixture 坐标、面积和连接条件一致；清楚标为 source geometry，不伪装为 sampled field。
   可用已装 svglib/ReportLab 转换或可用浏览器查看；不强制 cairosvg，不安装新依赖。
6. 检查 manifest 与实际交付、source runner 的对应；核对 diff 范围和 commit（若有）。
   不误归因已有 dirty/untracked；生产 code/adapter/正式测试/API/依赖/IFC/用户 blend 不得被本返修修改。
   IFC 文案只需检查更正已落实，不再次解析源 IFC。

## Verdict and Stop

只新增一份：
docs/project/evidence/d6-space-field-oracle-repair-independent-review.md
复现/临时 PNG 放临时目录，不改已有产物。

报告包括实际命令和结果、Blockers/Important/Minor、原 fixture 更正、新瓶颈对照和 runner 可复现性的分别裁决。
总体：ACCEPT LIMITED DESIGN EVIDENCE 或 REVISE。
明确阻塞是否影响本轮科学结论；非阻断的文案/视觉小问题可列 Minor，不因美化需要启动无止境返修。
若接受，允许推荐进入空间场表示与输入契约的设计决策，不直接批准生产实现、resolution、corridor/activity 分类或 Bayesian/ML。

**STOP FOR SPACE FIELD ORACLE REPAIR INDEPENDENT REVIEW**
