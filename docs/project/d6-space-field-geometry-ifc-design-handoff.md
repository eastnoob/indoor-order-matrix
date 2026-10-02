# D6 Space Field Geometry and IFC Input Design Handoff

Date: 2026-10-01

你是新的外部设计实验执行 session。
项目：D:\PROJECTS\understandOtherPackage\order_analyzer

## 授权与目标

空间场第一切片已接受为有限诊断证据，不需重做此前图例返修。
当前授权：先写本实验的设计表，再执行有界设计探针，最后交回审查。
允许研究脚本，不允许 production implementation design 或生产实现。
目标：查清拓扑失真，比较适用的几何表示，并盘点真实 IFC 的空间场输入。
不要把输入盘点、算法实验和真实 IFC 空间场验收混成一次通过。

## 先读

- AGENTS.md 与 docs/indoor_layout_evaluation_matrix_architecture_memory.md
- docs/project/d6-overall-self-description-design-table.md
- docs/project/evidence/d6-space-field-first-slice-owner-decision.md
- docs/project/evidence/d6-space-field-first-slice-report.md
- docs/project/evidence/d6-space-field-final-independent-review.md
- scripts/design/space_field/run_space_field_probe.py 及对应 JSON/manifest
- docs/project/evidence/d6-ifc-trend-checkpoint-1b-report.md

查阅相关 geometry、domain、sampling、substitute 工具与 IFC adapter 的真实调用路径。
旧实现是可评估的参考，不是必须沿用的架构；合适才复用，拒绝复用须说明理由。

## 技能使用

发现全局、插件和项目 .agents/skills；若 .agent 存在也检查。
读取并实际应用 experimental-design、scientific-critical-thinking、scientific-visualization。
评估 Spec Kit assess-define/shape/decide 是否适合这个局部设计门槛，复用已有证据。
不要为套流程重新启动整个项目；不使用或前置条件不满足时说明理由。
完成检查使用 verification-before-completion；找不到时执行并记录等价检查。
记录实际技能路径、动作、产出和不可用原因；不要只列技能名称。

## 顺序与实验边界

1. 先形成精简设计表：问题、候选表示、fixture、独立 oracle、变量、验收标准、预算和失败状态。
   写明每个实验能支持和不能支持的结论，再运行探针；不必为每个小脚本请求新审批。
2. 追查 subcell_gap_origin_sensitive 的持续拓扑失真。
   独立重算真实域/障碍的连通性，先排除 fixture/oracle 错误；再区分采样效应和程序缺陷。
   不假定问题必然来自分辨率，不得改真值以迁就算法；修订假设须留前后记录。
3. 对照当前 center sampler 与一个可用的 polygon-capable 几何基线。
   优先已有 helper 或已安装依赖；若能力缺失，报告并停止该分支，不安装新依赖。
   最小 fixtures：原敏感场景、旋转/斜边界、带孔域、窄开口、断开区域。
   开口合成 fixture 不代表真实 IFC opening 已获得。
4. 在预先限定的多个分辨率、相对原点偏移和旋转下比较面积/拓扑。
   检查单位缩放一致性、运行成本及非收敛；最细网格不是真值，多分辨率不是独立样本。
   独立 oracle 不得直接调用被测流程或复制其输出。
   数值公差和资源预算可以声明；禁止以硬宽度阈值决定 corridor/activity 标签。
5. 只读盘点一个已有真实 IFC 样本：记录路径/hash、schema、单位、placement、显式域、几何来源、context、Z 和 opening capability。
   IFC 家具节点严格来自 ObjectType == furniture_group；普通 group/名称/图层不创造节点。
   无显式 domain 则 not_available，不能拿包围盒/场景范围替代。
   区分当前缺失输入与需要未来设计的 domain 提取机制；不要永久排除自动派生域的研究。
   Trend 只用 typed Analysis 替身；占用/阻隔的功能几何来源另行说明，不能机械套用 trend 规则。
   门几何不是 IFC opening relation；affordance 不由类型自动生成；context 不变成家具节点。
6. 生成源几何与采样/拓扑对照图，标明真实、近似、unsupported 和失真结果。
   可视化裁剪不能修改或掩盖底层采样统计；连续边界与中心采样单元需区别呈现。
   IFC 若输入不齐，只呈现输入盘点，不伪造场计算或走廊分类。
   若生成 Blender 预览，仅用 D:\Blender\BlenderPortableLTS5.2\App\Blender64\blender.exe；
   保存独立输出文件，不修改源 IFC 或用户 blend。无需为本任务强行建立新的 UI。

## 范围、验证与交回

只允许修改 docs/project、scripts/design/space_field、outputs/design/space_field。
不得修改 features、adapters、正式测试、公共 API、依赖、源 IFC 或用户 blend。
若发现生产缺陷，只报告；禁止顺便修复或实现 selector、空间角色分类、Bayesian/ML。
保留既有 dirty/untracked 内容；仅提交明确路径，禁止 git add . 或破坏性 Git 操作。

交付设计表与逐项决策记录、探针/fixtures/oracles、JSON、可视化、manifest、复现命令与限制表。
保留 --output-dir 的临时复现能力；隔离 runtime/path 后比较确定性结果。
执行 oracle/status 检查、实际图像查看、hash、diff 与范围审计；报告失败同样是有效产出。
结论只能推荐下一步和适用范围，不得自行冻结生产分辨率或批准生产实现。
交回 commit、产物路径、技能使用记录、阻塞项及待裁决问题。
执行者不承担最终独立验收；总控将另外派发只读复核任务。

**STOP FOR SPACE FIELD GEOMETRY AND IFC INPUT DESIGN REVIEW**
