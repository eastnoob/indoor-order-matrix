# D6 封闭房间 / AnalysisDomain 候选有界实验记录

- 日期：2026-10-02
- 状态：设计实验完成；等待 enclosed-room domain candidate design review
- 范围：只读事实盘点、候选优先级/状态实验、静态交互契约与可视化
- 终止标记：STOP FOR ENCLOSED-ROOM DOMAIN CANDIDATE DESIGN REVIEW

## 目的与 owner direction

本实验比较三类候选：A 显式用户/IFC domain，B 从闭合墙体与 opening 事实推导的 automatic candidate，C 无法形成合格 domain 的诊断结果。owner direction 被记录为待验证假设与设计方向：多数目标场景可能是一个大房间；长期主流 IFC 输入应是用户显式 domain；显式输入优先并可覆盖、修正、拆分或拒绝自动候选；自动候选只有在用户确认后才可成为 authored/accepted domain；UI 本轮只定义契约和静态状态图。

## 已读材料与技能

已读取用户列出的 `AGENTS.md`、架构 memory、D6 input contract、owner decision、repair-v1 independent review、closed/open independent review、指定 features、adapters 和 IFC4 fixture。

实际检查并采用：

- `experimental-design`：把 fixture case 作为固定设计单元，区分 source fact、candidate inference、derived free-space，并保留可复现命令与临时复现。
- `scientific-critical-thinking`：不把 owner hypothesis 或 synthetic topology probe 升格为 production truth；显式记录 partial、ambiguous、invalid、not_available 和 evidence gap。
- `scientific-visualization`：颜色与线型冗余表达，静态图写明缺失/未接受状态，不显示伪造 free-space、walkability、visibility 或 route。
- `speckit-assess-intake/define/research/shape/decide`：检查了适用流程；由于用户限定写入目录，不创建 `.specify/assessments/`，而将 intake/define/research/shape/decide 内容压缩进本 evidence record；这些步骤不能被声称为正式 spec-kit artifact。
- `verification-before-completion`：在报告完成前重新运行 compile、主实验、临时复现、语义比较、SHA-256/manifest 检查。

## 实验设计

实验单元为 9 个 case：现有 IFC4 positive fixture、缺 domain、缺 domain geometry、断 opening-host relation、自动闭合墙壳、单一大房间、多壳冲突、开放边界、跨楼层。真实 live IFC 只做原生 inventory，不运行完整 geometry adapter；结果为 `not_verified`。

不选择 production boundary backend、网格/多边形 backend、resolution、route width、threshold、Bayesian/ML、free-space、connectivity、path 或 space-role algorithm。synthetic endpoint topology 仅用于有界状态探针，不能作为 production tolerance。

## 状态和优先级设计结论

优先级顺序：`user-authored` > `explicit IFC` > `automatic candidate` > `diagnostic-only` > `not_available`。

显式 candidate 即使 `partial` 或 `invalid` 也保留为当前 scope intent，不静默回退到 automatic candidate；如果只有合格 automatic candidate，则它可以作为默认候选，但 `user_confirmed=false`、`accepted=false`、`user_confirmation_required=true`。没有合格 domain 时，diagnostic bounds 只能是 `diagnostic-only`，domain status 为 `not_available`。

建议候选记录至少保存：`candidate_id`、`source_ids`、`geometry_refs`、`source_kind`、`closure_scenario`、`analysis_plane`、`units`、`wall_refs`、`opening_refs`、`domain_geometry_status`、`field_geometry_status`、`provenance`、`uncertainty_status`、`evidence_status`、`user_confirmed`、`accepted`、`diagnostic_only`。

## 几何分层与越界规则

每个 case 分开保存：

1. `scope_enclosure_geometry`：candidate scope 的闭合/开放边界事实；
2. `wall_occupancy_geometry`：含墙厚的 physical wall field geometry；
3. `opening_host_evidence`：opening、host refs 和 closure scenario；
4. `derived_free_space_candidate`：本实验固定为 `not_available`，不计算。

家具或墙体越界时保留完整 source geometry，同时在 candidate/evidence 层标 `partial`；不把裁剪结果写回 source，不跨 domain 建关系。single_large_room fixture 的越界家具就是该规则的 probe。

墙体厚度在 `wall_occupancy_geometry.thickness` 中保留，scope boundary 与 physical field 不合并成 interior-only room。外墙外缘、内墙面、中心线、用户闭合曲线和其他构造仍是待 owner 决策的 boundary construction；本实验不冻结其中任何一种。

## opening 与门状态

`doors_windows_default_closed_scenario_assumption` 只表示场景假设，不表示 IFC 已知状态；门几何不自动转换为 IFC opening relation。positive fixture 验证了 opening 与 host relation；broken relation case 保留 opening geometry 但 `evidence_status=partial`，没有补 host。

## 结果摘要

- 现有 IFC4 explicit IfcSpace：adapter 读到 IfcSpace、wall、opening 和 host relation，但 fixture 的 IfcSpace mesh `is_closed=false`，所以 candidate 为 `explicit IFC / partial / accepted=false`，不能称为合格闭合 domain。
- `single_large_room`：自动墙壳形成一个 `computed` candidate；同时用户闭合曲线优先，选中 `user-authored`，自动 candidate 被 suppress 但保留为 provenance。
- `automatic_closed_wall_shell`：形成一个 `computed` automatic candidate，但必须等待用户确认。
- 多壳：`ambiguous`，不选 domain。
- 开放边界：`partial`，不选 domain。
- 跨楼层：`invalid`，不选 domain。
- 缺 geometry / 缺 domain：`not_available`，不生成 free-space 或 topology 结果。

## UI 交互契约

静态图 [interaction_states.svg](../../../outputs/design/space_field_domain_candidate_experiment/interaction_states.svg) 使用：橙色 automatic candidate、蓝色 authored candidate、绿色 hover/selected、深灰 physical wall field、红色 opening evidence，并显示 `candidate not accepted` 与 `NOT AVAILABLE — NO QUALIFIED ANALYSIS DOMAIN`。

交互契约：hover 高亮并展示 source kind、closure、wall/opening refs、uncertainty/status；accept/reject 写入 user-confirmed/accepted；edit/redraw 替换 scope geometry 但保留 source provenance；split/merge 生成显式 user-authored candidates，同时保留原 automatic candidate 作为 diagnostic。真实 hover UI 未实现，本图是静态交互状态，不声称已实现正式 UI。

## 结论与 gate

本实验支持“单一大房间的闭合墙体可形成一个默认 automatic candidate”的有限结论；它不支持把自动 candidate 称为真实房间，也不支持把现有 IfcSpace fixture 自动称为合格闭合 domain。显式用户 domain 应覆盖自动候选，并可保留自动候选作为可审查 provenance。

下一阶段 boundary/free-space design 仍需 owner review 后才能进入；至少需要决定 boundary construction、partial/ambiguous 聚合语义、用户确认后的 accepted 生命周期、跨楼层/孔洞规则，以及 derived free-space 的后续 gate。

附件：`candidate_results.json`、`fixture_manifest.json`、`source_geometry.json`、`provenance.json`、`interaction_states.svg`、`artifact_manifest.json`、`verification_report.json`。
