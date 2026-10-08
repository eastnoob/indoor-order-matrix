# D6 空间场设计进度记录

- 日期：2026-10-03
- 性质：追加式进度记录；不替代、不重写或修订输入契约原文
- 契约原文：[space-field-ifc-neutral-scene-input-contract.md](../space-field-ifc-neutral-scene-input-contract.md)
- 停止标记：**STOP FOR D6 SPACE-FIELD DESIGN PROGRESS REVIEW**

本记录只补充截至本日期的设计进度与证据来源。契约原文仍保留其历史表述、状态和停止标记；如后续设计产生新结论，应继续新增带日期和 provenance 的记录，不回写历史结论。

## 证据类型与解释边界

| 类型 | 本记录中的含义 |
|---|---|
| 设计契约 | owner 已接受的设计边界或待议原则；不等于当前代码已经提供相应 API。 |
| 已运行的只读实验 | 记录明确给出 runner、产物或复现结果的有限实验；实验通过只说明其声明的断言和产物检查通过。 |
| 诊断证据 | 合成 fixture、采样结果、静态图，或在 provisional diagnostic frame 下得到的几何观察；不能据此宣称真实房间、通行、生产质量或空间角色。 |
| 真实 IFC 尚未验证能力 | 对真实 IFC 的 native inventory 或复用几何投影记录，不代表重新运行了 live geometry adapter，也不证明合格域、自由空间或拓扑。 |
| 尚未批准的 production 行为 | 尚未获得生产实现批准的 inference、selector、阈值、API 或模型行为；不得从下列实验结果推定其已获批准。 |

## 已确认

1. **家具组是家具分析节点；成员仍是组内观测。墙和柱保留为物理占用、边界或上下文证据，不因其空间位置而改写家具 membership。**
   Provenance：设计记录 [输入契约](../space-field-ifc-neutral-scene-input-contract.md)；实验 **D6 soft-field / empty-space evidence**（[记录](d6-space-field-soft-field-experiment.md)，diagnostic only）和 **D6 pairwise channel / free-space evidence**（[fixture manifest](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/fixture_manifest.json)、[scope audit](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/scope_audit.json)，12 个合成 fixtures，validation `pass`）。限制：家具组节点规则来自既有 authored `furniture_group` 身份；空间场证据未获权力去重新分组或更改成员。

2. **AnalysisDomain 是正式空间分析范围；diagnostic view/frame bounds 不能替代它。没有合格 domain 时，依赖 domain 的自由空间、连通性和路径证据保持 `not_available`。**
   Provenance：设计契约 [输入契约](../space-field-ifc-neutral-scene-input-contract.md) 与 [owner decision](d6-space-field-input-contract-owner-decision.md)，状态为 limited design gate；实验 **IFC input-contract repair v1**（[独立复核](d6-space-field-ifc-input-contract-experiment-repair-v1-independent-review.md)，`ACCEPT LIMITED DIAGNOSTIC EVIDENCE`）和 **pairwise channel** 的 [real IFC audit](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/real_ifc_audit.json)。限制：pairwise 缺域 case 是合成 fixture；真实 IFC audit 标记 `analysis_domain=not_available`，且明确未重跑 adapter，未以 scene bbox 替代 domain。

3. **家具 membership 与空间场推断分开。** 空间场可以记录空域、占用或候选关系，但不将空域加入家具组，也不因 field/candidate 结果改写 authored membership。
   Provenance：实验 **D6 first slice**（[报告](d6-space-field-first-slice-report.md) 和 [最终独立复核](d6-space-field-final-independent-review.md)，`ACCEPT LIMITED DIAGNOSTIC EVIDENCE`）；**soft-field** [报告](d6-space-field-soft-field-experiment.md)；**pairwise channel** [validation](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/validation_report.json) 与 [scope audit](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/scope_audit.json)。限制：这是设计/诊断分层证据，不冻结任何生产空间节点或推断接口。

4. **pairwise boundary gap、pairwise free-space profile 和 connectivity 是不同量。** boundary gap 描述家具组边界间隔；free-space profile 依赖支撑几何和占用证据；connectivity 描述给定域内的诊断连通观察。任一量都不能替代另两项，也不自动表示通道、路线宽度或 walkability。
   Provenance：实验 **D6 pairwise channel / free-space evidence**（[experiment record](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/experiment_record.json)、[diagnostic](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/pairwise_diagnostic.json)、[runner](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/run_experiment.py)、[owner review record](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/owner_review_record.md)，状态为 design-only，停在 `STOP FOR PAIRWISE CHANNEL DESIGN REVIEW`）。限制：runner 在合成家具 footprint 间用 `nearest_points` 构造 `fixture_local_diagnostic_segment`，并标记为 `explicit fixture support only`；这不验证一般场景的候选生成规则。

## 已完成证据

| 实验 / 状态 | Provenance 文件 | 证据性质 | 限制 |
|---|---|---|---|
| **D6 space-field first slice** — `ACCEPT LIMITED DIAGNOSTIC EVIDENCE` | [报告](d6-space-field-first-slice-report.md)、[最终独立复核](d6-space-field-final-independent-review.md)、[owner decision](d6-space-field-first-slice-owner-decision.md)、[oracle repair 独立复核](d6-space-field-oracle-repair-independent-review.md) | 合成矩形的独立面积/连通 oracle、uniform sampling 的分辨率/原点敏感性、缺失 domain 的 `not_available`、旋转边界的 `unsupported` 状态。 | 不是 topology convergence；free-run 不是 Euclidean clearance、route width 或真 bottleneck；未使用真实 IFC 几何。历史 oracle 更正以原记录为准。 |
| **IFC input-contract experiment repair v1** — `ACCEPT LIMITED DIAGNOSTIC EVIDENCE` | [原实验记录](d6-space-field-ifc-input-contract-experiment.md)、[repair v1 记录](d6-space-field-ifc-input-contract-experiment-repair-v1.md)、[独立复核](d6-space-field-ifc-input-contract-experiment-repair-v1-independent-review.md)、[manifest](d6-space-field-ifc-input-contract-experiment-repair-v1-manifest.json) | 实际运行五个 disposable IFC4 fixture adapter case：无 domain、显式闭合 domain、有 domain record 但缺 geometry、opening 无 void-host relation、unsupported grid axis uncertainty；并做真实 IFC native inventory 与 source-fact-only preview。 | 未运行完整 live IFC 几何 adapter；没有 free-space、connectivity、opening subtraction、door state 或通行结果。独立复核要求保留 case-level `exit_code` 与旧失败 runner hash 的 provenance 限定。 |
| **Enclosed-room / AnalysisDomain candidate** — `ACCEPT LIMITED DIAGNOSTIC EVIDENCE` | [实验记录](d6-space-field-enclosed-room-domain-candidate-experiment.md)、[comparison](d6-space-field-enclosed-room-domain-candidate-comparison.md)、[verification](d6-space-field-enclosed-room-domain-candidate-verification.md)、[独立复核](d6-space-field-enclosed-room-domain-candidate-independent-review.md)、[owner decision](d6-space-field-input-contract-owner-decision.md) | 九个 fixture case 对显式/自动候选、用户意图优先级和 `missing`、`partial`、`ambiguous`、`invalid`、`not_available` 等诊断状态进行有限比较；自动封闭壳保持未确认，墙厚与 physical field 分开。 | 自动候选只是合成/fixture 设计观察；real IFC 仍是 native inventory，geometry adapter 为 `not_verified`。没有生产 domain selector、门状态推断或 free-space 输出。 |
| **AnalysisDomain boundary construction** — bounded experiment complete，owner review required | [实验记录](d6-space-field-boundary-construction-experiment.md)、[comparison](d6-space-field-boundary-construction-comparison.md)、[verification](d6-space-field-boundary-construction-verification.md) | 在 8 m × 6 m synthetic shell 中比较 inner face、outer face、centerline、authored curve；把 `scope_enclosure_geometry` 与含墙厚的 physical wall field 分开；观察 open/multi-shell/cross-floor 状态传播。 | 不选择生产 boundary construction；real IFC 四种构造均为 `not_verified`；不产生 free-space、路径或空间角色。owner review 尚未完成。 |
| **Pairwise channel / free-space experiment run_001** — validation `pass`；owner review pending | [experiment record](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/experiment_record.json)、[fixture manifest](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/fixture_manifest.json)、[diagnostic JSON](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/pairwise_diagnostic.json)、[real IFC audit](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/real_ifc_audit.json)、[validation report](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/validation_report.json)、[artifact manifest](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/artifact_manifest.json)、[owner review record](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/owner_review_record.md) | 12 个 synthetic fixtures 分别记录 boundary gap、local free-space profile 与 connectivity；含列占用、墙体阻隔、开放列排、断开组件、多候选 channel、缺失/非法几何和缺 domain 情形。临时复现与 JSON/几何/状态/哈希/PNG/Blend/scope 检查记录为通过。 | resolution 为实验采样参数；没有生产选择。runner 在合成家具 footprints 的最近点间构造诊断 support segment，歧义 case 则显式保留候选集合。real IFC audit 复用既有诊断结果、`adapter_rerun=false`，且缺少 qualified AnalysisDomain；不得写成 live IFC space-field 已验证。 |

### 柱、墙和状态传播证据

- **柱占用和墙体影响：** **D6 column occupancy and channel audit** 的 [报告](d6-space-field-column-channel-audit.md)、[real IFC audit](d6-space-field-column-channel-audit-real-ifc.json)、[validation](d6-space-field-column-channel-audit-validation.json)，以及 **hard partition A/B/C comparison** 的 [报告](d6-space-field-hard-column-comparison.md)、[real IFC comparison](d6-space-field-hard-column-comparison-real-ifc.json)。报告记载在 provisional diagnostic frame 下，复用的占用投影从 furniture-only 的 355.884414 m² / 1 component，经过 wall-aware 的 332.277691 m² / 3 components，到 wall-plus-eligible-columns 的 326.517691 m² / 5 components；`column_effect_on_pairwise_channel=not_available`，virtual wall 未选择。**实验/状态：** bounded diagnostic；限制：这些 real IFC 数值复用先前投影，完整几何 adapter 未重跑，frame 不是 AnalysisDomain；不是生产自由空间或真实通行验证。
- **合成柱/墙状态：** pairwise run_001 的 [fixture manifest](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/fixture_manifest.json) 与 [diagnostic](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/pairwise_diagnostic.json)。`column_between_side_opening`、`column_off_axis_clearance`、`column_row_open_gap` 等说明合格 synthetic fixture 中柱可改变 local profile，而 pairwise boundary gap 保持独立；`disconnected_components` 用贯穿域的 synthetic wall 得到两个 diagnostic components；`multiple_candidate_channels` 保留 `ambiguous`；`missing_invalid_column_geometry` 保留缺失/非法来源并标记 `partial`；`missing_analysis_domain` 的 profile/connectivity 为 `not_available`；不同楼层柱保留来源且不纳入目标层占用。**状态：** runner/validator 的 fixture assertions 通过。**限制：** 均为人工构造 fixture，不是 IFC 原生几何行为证明，也不是 walkability/route 结论。
- **真实 IFC 边界：** [pairwise real IFC audit](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/real_ifc_audit.json)、[IFC repair v1 独立复核](d6-space-field-ifc-input-contract-experiment-repair-v1-independent-review.md)、[column audit](d6-space-field-column-channel-audit.md)。真实 IFC native inventory 记录了 37 个 exact `furniture_group`、95 个家具成员、11 面墙、6 扇门、16 根柱且没有 `IfcSpace` / opening-void relations；已有投影诊断并不等于当前重新提取了 live geometry。**状态：** inventory/复用诊断有限可用；AnalysisDomain `not_available`，live geometry adapter `not_verified`。**限制：** 不推广到其他 IFC，不推断门状态、开口、domain、自由空间、连通或可通行性。

## 当前未冻结

- 自动 `AnalysisDomain` 推断及候选接受/拒绝生命周期；封闭壳只是 provisional candidate 研究。
- pairwise candidate channel/support geometry 如何从家具组、墙、柱及其他 physical occupancy 生成；当前 runner 只在合成家具最近点间构造 fixture-local segment，并为歧义 case 保留手工指定的候选数，不代表一般候选生成契约。
- resolution、origin、几何 backend 与采样/拓扑稳定性规则；不同设置只是敏感性观察。
- free-space profile 的正式语义、几何定义、通道聚合、与 connectivity 的正式关系。
- space role（包括 corridor/activity-space 等）的证据定义与分类行为。
- selector、固定阈值、winner 选择、route width，以及 deterministic、Bayesian 或 ML 生产模型。
- production API、schema、implementation design 与任何 production integration。

Provenance：输入契约 [deferred fields](../space-field-ifc-neutral-scene-input-contract.md) 和 [owner decision](d6-space-field-input-contract-owner-decision.md)；pairwise [scope audit](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/scope_audit.json) 将生产 backend、resolution、route width、space role、Bayesian/ML、固定阈值和 API 选择均记为 false；boundary construction [实验记录](d6-space-field-boundary-construction-experiment.md) 仍要求 owner review。状态：设计未冻结／production 未批准。限制：此列表表示尚待决定，不是方案推荐或实现承诺。

## 下一阶段

开展独立、有界的设计比较：限定在 qualified `AnalysisDomain` 内，研究如何从家具组节点、墙、柱及其他物理占用生成可审计的 candidate support/channel evidence。每个 candidate 应能回溯来源、几何、坐标/单位与 evidence status；实验需区分输入事实、candidate 几何、profile 与 connectivity 的观察，覆盖缺失/非法/不同楼层、多个候选、局部障碍和断开情形。

保留 `ambiguous`、`partial`、`not_available` 与 `disconnected`，并保留必要的 missing/invalid/unsupported 来源原因；不静默补齐缺失输入，不以 bbox 生成 domain，不选择 winner，不固定阈值，也不设计 production selector。完成该设计证据并复核后，再决定是否另开 implementation design；本记录本身不批准进入实现。

Provenance：当前问题边界来自 pairwise run_001 的 [runner](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/run_experiment.py)、[诊断结果](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/pairwise_diagnostic.json) 与 [owner review record](../../../outputs/design/space_field_pairwise_channel_experiment/run_001/owner_review_record.md)；下一步限制来自 [IFC input contract owner decision](d6-space-field-input-contract-owner-decision.md) 和 [boundary construction experiment](d6-space-field-boundary-construction-experiment.md)。当前状态：pairwise owner review 尚待完成；后续设计 gate 未开启为 production work。

**STOP FOR D6 SPACE-FIELD DESIGN PROGRESS REVIEW**

## 2026-10-06 Git provenance and next handoff gate

本节是追加记录，不改写上方历史契约或进度判断。当前分支为
`codex/d6-analysis-domain-layout-handoff`，HEAD 为
`a149420faf5dfef9d89293a4c415a08df4964581`。生命周期 status-contract repair、amendment
和 conflict-preservation 三个 checkpoint 均为当前 HEAD 的祖先；本次审计将其提交关系、worktree、
分支 tracking 和 untracked 基线记录在
[`d6-space-field-git-provenance-checkpoint-2026-10-06.md`](d6-space-field-git-provenance-checkpoint-2026-10-06.md)
及其
[`manifest`](d6-space-field-git-provenance-manifest-2026-10-06.json) 中。

### 生命周期证据收口

- lifecycle status-contract amendment v1 与 conflict-preservation v1 已获**有限设计证据接受**，可继续进行设计工作；这不是 production implementation、selector、public API 或生产 status enum 的批准。
- authored-domain precedence、unresolved-conflict gate、duplicate-event idempotence、replacement lineage 和 deterministic replay order 是当前设计原则。它们保留来源、事件和版本关系，但不构成生产 API、selector、阈值、后端或自动 domain promotion policy。
- duplicate event 可保留全部 provenance 而只产生一个幂等关系效果；语义冲突必须保留完整记录并阻断下游 promotion；replacement 必须保留旧版本并链接到新版本，且新版本重新进入 provisional/unconfirmed 语义。这些规则仍需在下一阶段 handoff 中作为可审计输入，而不是直接实现。

### AnalysisDomain/UI handoff design（下一道 gate；只设计不实现）

下一阶段交付一份独立的 design-only handoff，围绕以下边界组织审查：

1. **Candidate 输入与生命周期。** 输入包括 automatic candidate set、显式 authored/user domain、稳定 candidate 与 version 身份、source/geometry refs、evidence state、actor/time/event provenance 和冲突关系。候选默认 retained/provisional；`singleton` 只是集合基数，`unassigned` 只表示尚无显式 assignment，`ambiguous` 保留多个 plausible candidates。确认、拒绝、替换和手绘闭合边界都必须是带 actor、时间、理由和稳定 ID 的显式动作；替换保留 lineage，手绘边界保留原候选与新 authored geometry 的关系。
2. **优先级与拒绝门。** 合格 authored/user domain 在 domain use 上优先于 automatic candidates；automatic candidates 继续作为 provenance 和比较证据保留。冲突不自动选 lexical/event winner，`unresolved conflict` 阻断 domain promotion。没有合格 domain、几何 refs 不可用或冲突未解决时，free-space、connectivity、membership 等 domain-dependent 下游结果必须是 `not_available`；diagnostic scene bounds 只可作为显示 frame。
3. **UI 交互和状态表示。** hover/highlight 只改变显示焦点并显示 candidate/source/status provenance，不改变 lifecycle。自动 singleton、ambiguous 或 unassigned 候选使用中性/琥珀色轮廓，不得仅因几何 plausibility 显示为 active green region；显式确认且资格成立的 active domain 才可使用绿色区域表达，并同时显示 provenance。rejected 候选保留为历史/可展开记录，replaced 旧版本显示灰色历史连线、新版本显示 provisional；partial/missing/invalid/unsupported 使用警告标记；conflict 使用冲突纹理并禁用 promotion；not_available 使用灰显下游操作。具体颜色、组件名和序列化字段仍是 handoff 设计内容，不是已冻结 UI/API。
4. **墙、柱、门窗、opening、家具、context 的 scope/occupancy 角色。** 墙可提供 boundary/enclosure evidence 和 physical occupancy；柱始终是 physical occupancy，只有明确几何接触的诊断 boundary-support 才能作为证据，不能由排列自动变成 virtual wall；门、窗和 `IfcOpeningElement`/host relation 只作为来源事实，不能从存在关系推断 open/closed/permeable 状态；家具保持 authored membership 与 physical occupancy/context 的分离，不因空域或 candidate 改写 membership；其他 context 只作为可视化/来源参考，不能静默升级为 domain。
5. **真实 IFC 边界。** 真实 IFC 在本 handoff 中只用于输入映射、source identity/provenance 对照和可视化探索。不得把 live inventory、场景 bbox、复用投影或 synthetic fixture 写成 qualified AnalysisDomain、free-space、connectivity、membership、route 或 walkability 结果。

下一 gate 的验收应只检查 candidate 输入/生命周期、authored precedence、冲突阻断、UI 状态矩阵、scope/occupancy 角色和无合格 domain 时的下游拒绝行为；不选择 selector、threshold、resolution、geometry backend、Bayesian/ML 方法、production API 或真实 IFC production integration。

### 本次 provenance 限制与停止条件

本次 Git 审计只运行分支/祖先/worktree/status、显式路径 hash/bytes、Markdown/JSON 解析、manifest 自洽、scope、whitespace 和历史契约不变检查。46 条原有 untracked 路径全部保留并在 manifest 中逐条列出；其中 owner-review 中、临时日志/产物或无法证明属于已完成 checkpoint 的文件保持 untracked。未运行完整 pytest、完整 IFC adapter、Blender、Bayesian/ML 或 selector。此记录不把文档收口写成 production implementation 完成。

**STOP FOR D6 PROGRESS AND GIT PROVENANCE CHECKPOINT REVIEW**

## 2026-10-07 B2 implementation checkpoint（本轮追加）

已接受的 private provenance/refusal implementation 与 coverage repair 正在形成本地检查点，见 [checkpoint note](d6-b2-implementation-checkpoint-2026-10-07.md) 和其 manifest。只包含精确 shell identity、physical occupancy、opening provenance/uncertainty、私有 refusal 及限定兼容回归。
accepted shadow 为 **LIMITED REAL-IFC SHADOW DIAGNOSTIC EVIDENCE**；它检查继承候选/几何证据，不证明本轮新 B2 implementation 真实入口调用。
在检查点阶段，新链 native IFC / live Blender 调用仍 **pending**；随后按本轮已授权的 checkpoint-first probe执行并另记结果。B1 multi-floor/units/work-plane、Bayesian B1 与其他 deferred items 不变，不把全部 B2 标成 complete。

## 2026-10-07 B2 real-input invocation（本轮追加，待独立复审）

implementation checkpoint为 `8fd6f75d8d4444adac53588f642187d489e14831`。唯一完整native IFC adapter attempt在300s预算到期后终止，未返回NeutralScene/B2，保持 **not_verified_timeout**；runner先前一次CRLF identity预检失败发生在loader之前，两者日志分开保留，无完整提取retry。
新链已通过 **live Blender structural geometry → existing Blender adapter → NeutralSceneV2 → actual private B2** 调用。live关联accepted IFC的path/project/33个structural STEP+GlobalId一致；portable Blender5.2符合约束，但blend未保存，IFC/live geometry parity仍未验证。
11墙/16柱/6门全部保留physical occupancy，27条support均conditional=False；domain unavailable、promotion/subtraction refused、validity/components unavailable、free_space/route not_evaluated；真实空opening集合，不覆盖opening conflict/partial等分支。结构subset排除其他339个live对象，不计算家具趋势。
saved snapshot在第二个新进程重跑，raw B2/geometry/audit/validation/PNG byte-identical；报告和compact manifest见 [execution report](d6-b2-real-input-validation.md)。sourceIFC、accepted shadow及无关既有文件hash无漂移。
以上是本轮执行证据，不是独立接受；B1 multi-floor/units/work-plane、typed家具substitute链和所有其他deferred items不变，不新增partition/free-space/route能力。

**STOP FOR D6 B2 CHECKPOINT AND REAL-INPUT VALIDATION REVIEW**

## 2026-10-07 Native IFC timeout investigation（独立下一任务）

Coordinating chat 已 ACCEPT LIMITED LIVE-BLENDER ADAPTER-TO-B2 SOURCE/PROVENANCE/REFUSAL EVIDENCE；原独立报告保持原样。当前另行调查 native 300s timeout，先测量，再做有界最小修复及真实 native→B2 验证；完整几何 B2、B1 policy 与其他 deferred items 不变。

本次 native 调查结果为 **diagnosed dependency bottleneck / no production repair / review-pending**。300.562s instrumented baseline：176 个唯一 Body create_shape 累计 270.676s，解析 15.721s，完成 Python mesh 10.602s；只读 subset 支持原生 kernel 成本且 Body/Analysis 身份、world/SI provenance 不变。唯一 clean 全源尝试预先扩展至 600s（不是性能修复），600.704s outer timeout，未返回 NeutralScene，未到 B2，180s view budget 未使用；worker 已 kill/reap。175 项限定 synthetic/compatibility 检查通过，未改 production adapter/backend/API/policy，source IFC 指纹不变。证据见 [native report](d6-native-ifc-timeout-repair.md) 及 [manifest](d6-native-ifc-timeout-repair-manifest.json)。不把之前 Blender 成功作为本次 native 成功，完整几何 B2 仍 deferred。

STOP FOR D6 NATIVE IFC TIMEOUT REPAIR REVIEW


## 2026-10-08 D6 B2 semantic enclosure private integration (root review pending)

The newly authorized private production integration is consolidated in [executed report](d6-b2-semantic-enclosure-private-integration.md), [independent implementation review](d6-b2-semantic-enclosure-private-integration-independent-review.md) and the pre-edit plan. One explicit private view entry and one focused helper recompute semantic carriers from immutable Neutral Scene geometry using caller-supplied plane/metres/datum/cut/contact/area/scenario authority; public/default view functions and exported model remain unchanged. Frozen 38-source production run_007 gives all six doors/five windows as 11 default-closed scenario carriers, five contours and one provisional compound scope; strict contact separately gives eight carriers/three contours/one scope. Original physical/source/participation facts and ordinary B2 diagnostics are preserved; structural union and all 11 mappings match prior evidence, all five windows support contours, and two diagonal residuals stay unsealed. A independently ACCEPTS bounded private provisional integration on final helper d0a5e2c2... after genuine F01-F05 repairs, linked/unlinked missing-host positive inference and actual invalid/contradictory/unfilled/ambiguous negative checks. The earlier overstrict unlinked zero-carrier assertion is explicitly withdrawn under the existing accepted rule, with failed audits/unaccepted intermediate snapshots/runs preserved; it was a review-expectation correction, not a new owner policy or source defect. Final B delivery_003/run_007 and A verification pin the same source hashes. One configured full Pixi suite exited 0: 874 passed / 13 skipped in 965.37 s, within root's 20-minute bound; all 887 collected node identities reconcile to actual progress, no interrupted native result/continuation/second full suite. Skips are retained as skips from the unavailable optional IFC-workflow fixture. Source/test/harness hashes remain unchanged before/after; protected evidence/dependencies/input/IFC bytes and prior ledger prefix are verified, branch/HEAD/index preserved, no staging/commits. Unknown authored floor datum, disk/live mesh parity, self-intersection/topology certification, local residuals and shared-wall allocation remain limitations; no active AnalysisDomain, certified rooms/free-space/routes, global tolerance/default, public schema/model/UI/adapter/native conversion or general production/merge approval is claimed. Root/human retains phase acceptance.

STOP FOR D6 B2 SEMANTIC ENCLOSURE PRIVATE INTEGRATION REVIEW
Root phase decision, 2026-10-08 (Europe/Berlin): **ACCEPT the bounded private B2 semantic-enclosure integration at final delivery_003 / run_007** after A's independent ACCEPT and the configured full suite (874 passed / 13 skipped, exit 0). The preceding pending-review header remains historical. Acceptance covers explicit private provisional computation, source/physical occupancy preservation, the authorized default-closed scenario, qualified missing-only host inference and explicit conflict/unfilled refusals. It does not authorize certified room count, active AnalysisDomain, global tolerance/defaults, public API/UI/free-space, disk/live mesh parity or commit/merge. No code/test/harness/plan/independent-review/old-run changes follow this decision; root acceptance is appended within this existing phase entry and the original ledger prefix remains intact.

STOP FOR D6 B2 SEMANTIC ENCLOSURE PRIVATE INTEGRATION REVIEW

## 2026-10-08 D6 B2 private semantic-enclosure Git checkpoint

The separately authorized single local checkpoint retains the accepted delivery_003 / run_007 code, regressions, frozen plan and acceptance/review reports. [Checkpoint scope and retention record](d6-b2-semantic-enclosure-git-checkpoint.md) and [fingerprint manifest](d6-b2-semantic-enclosure-git-checkpoint-manifest.json) identify parent HEAD ab55da50dfb278b639e2327008ad23a50e86973d, exact reviewed bytes and the reused 90-focused / 874-passed / 13-skipped full-suite evidence; no computation or tests are rerun here. Only the accepted private-integration phase plus this entry are staged from the ledger; its older uncommitted history and original 30,449-byte prefix remain in the working file. Local-only outputs/input/PNG/harness stay outside Git; recorded hashes do not preserve them. The post-commit receipt records the actual commit and remaining dirty state separately. Acceptance remains private, provisional and scenario-specific; AnalysisDomain handoff is the next separately scoped stage, with no implementation or promotion here.

STOP FOR D6 B2 GIT CHECKPOINT REVIEW
