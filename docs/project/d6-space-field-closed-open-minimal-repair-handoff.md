# Closed/Open Contrast: Minimal Repair Decision and Handoff

Date: 2026-10-01

## Controller Decision

Basis: `docs/project/evidence/d6-space-field-oracle-repair-independent-review.md`.
Accepted: historical subcell correction (19.2, three source components) and saved polygon runner reproducibility.
Rejected as evidence for the contrast: current connected_bottleneck_opening source_area=36.0 and its closed/open interpretation. The review found actual source area 33.0 in both cases and an already connected free region. Do not propagate those claims into a backend decision.
Only this contrast requires repair. No further subcell, IFC inventory or historical legend verification is requested.
The controller read the independent report; it did not rerun or audit code.

## Prompt for the Original Repair Executor

请只修复一个闭墙/开口 fixture，完成后交给上一独立复核 session 核对。
项目：D:\PROJECTS\understandOtherPackage\order_analyzer
先读 AGENTS.md 和本次独立复核报告。
使用 experimental-design、scientific-critical-thinking 和 verification-before-completion；图像用 scientific-visualization。记录实际使用，缺失则说明。

### Exact Fixture Specification

坐标为 synthetic unit，明确记录，不代表 IFC 米制或可通行人宽：
- Domain D：矩形 (0, 0, 6, 4)，面积 24。
- 完整障碍墙 B：矩形 (2.5, 0, 3.5, 4)，面积 4；贯穿 domain 高度。
- 闭合 free set：D difference B，面积 20，源几何两个分量。
- 开口 O：矩形 (2.5, 1.5, 3.5, 2.5)，面积 1，位于墙内部。
- 开口后的有效障碍：B difference O，面积 3。
- 开口 free set：D difference (B difference O)，面积 21，源几何一个分量。

此处规定的是实验几何与预期 source oracle，不是语义阈值或生产分辨率。
请先由坐标手算确认这些关系，再核对实际布尔几何。不能只修改期望值使 assertion 通过。

### Required Work

1. 使用独立 fixture IDs 保存 closed/open 两个版本；retire 原错误瓶颈证据并追加明确更正，不静默覆盖历史解释。
2. 真正构造 effective obstacle 与 free polygon，再计算 source area/components；source 值不能硬编码后冒充测量。
   检查 O 与 B 的正面积交集确为 1；source oracle 手算与实际测量分别保存。
3. 采样使用该有效几何，不沿用“扣障碍后直接加入 opening cells”但不验证 domain/有效障碍的 shortcut。
   若保留矩形采样路径，必须与同一 D、B、O 点包含语义一致；只修 design runner，不改生产代码。
4. 只运行这两个 fixture 的有界 sampling 对照：step 0.5/0.25，origin (0,0)/(0.23,0.17)。
   这是四次敏感性观测，不是独立样本。采样失真可以如实报告，不要求每次等于 source oracle。
   结果必须分开 source 与 sampled area/components，不能据此宣称任意窄开口采样稳定或可通行。
5. 保存 closed/open 并排源几何图，显示 domain、有效墙体和真实开口，标签与 JSON 一致。
   只要能清楚审查几何，不扩展 UI/Blender/图例框架；使用已安装图像查看/渲染能力，不安装依赖。
6. 在临时 --output-dir 复现，核对确定性 payload（排除 runtime/path）、oracle 与状态断言、manifest、diff 和范围。
   此次不重跑完整 IFC、无关 fixture 和全套 pytest。

### Scope and Delivery

只允许相关 docs/project、scripts/design/space_field、outputs/design 修改。
不得改生产 features/adapters/API/正式测试/依赖/源 IFC/用户 blend/独立复核文件。
保留用户 dirty/untracked；Git 只提交明确路径。
交回修复记录、commit、保存的 runner/fixtures、source 与 sampled JSON、对照图、manifest 和临时复现命令。
若实际 source 几何不满足手算结果，停止并报告，不调整真值掩盖失败。

**STOP FOR CLOSED-OPEN FIXTURE REVIEW**

## Independent Acceptance Scope

交回后由上一独立复核 session 仅核对这个差量：坐标与布尔关系、20/21 source area、2/1 source components、opening/wall 交集、真实 sampling 语义、两幅图和临时复现/hash/范围。
以上通过即可关闭此返修；非阻断美化问题不再开新返修轮次。
随后总控进入表示与输入契约设计裁决，不直接批准生产实现。

## Application Clarification: 2026-10-01

### Owner Original Words

> 门这个东西意义不大其实，一般而言，我们默认其关闭，后面对于boundary的开口，那才是真正的开与闭，所以从元的角度，你当前做的是有意义，只是要注意未来的使用场景

### Controller Interpretation and Decision

- Preserve the closed/open contrast as a foundational effective-boundary geometry experiment. Do not expand it into door-state simulation.
- The intended application prioritizes boundary openings. The scope of `boundary` (domain boundary, internal divider, or another derived boundary) is not yet frozen; this note does not equate all boundaries with the AnalysisDomain perimeter.
- Record generally closed doors as an owner-directed analysis assumption, not an observed IFC door state. Door geometry alone does not establish an opening relation, its geometry, or its permeability.
- Keep physical occupancy, walk permeability, and visual permeability separate. A closed-door assumption does not by itself specify every channel or authorize silently filling all openings.
- This experiment establishes a geometric contrast only. It does not establish route usability, corridor/activity roles, production sampling resolution, or an IFC opening-extraction policy.

### Received Evidence and Review Handoff

The controller read `outputs/design/closed_open_fixture_repair/repair_record.md`. It reports source areas 20/21 and components 2/1, saved rectangle/polygon runners, and separate sampled observations. These are executor-reported results, not controller-verified acceptance.

Send the following bounded task to the previous independent reviewer, not the repair executor:

请独立复核 `outputs/design/closed_open_fixture_repair`，仅检查本次 closed/open 差量。先读 AGENTS.md、本交接笔记、repair_record.md 与保存的两个 runner。实际读取并使用 experimental-design、scientific-critical-thinking、scientific-visualization 和 verification-before-completion；从项目、全局或插件技能路径发现，报告不可用项。

独立核对 D/B/O 坐标、opening 与 wall 交集面积 1、effective obstacle、source free area 20/21 与 components 2/1；确认 source 结果来自实际布尔运算而非硬编码 oracle，采样对应同一有效几何，source 与 sampled 证据分列。只在临时 --output-dir 复现规定的分辨率/原点对照，检查确定性 payload、manifest 和实际源几何图。不得覆盖既有 evidence，不能将图或采样解释为门状态、通行能力或空间角色证明。

不重跑无关 IFC、历史 fixture 或全套测试，不改 production、依赖、源 IFC、用户 blend 或执行者文件。仅新增 `docs/project/evidence/d6-space-field-closed-open-independent-review.md`，保留既有 dirty/untracked。给出 ACCEPT LIMITED DIAGNOSTIC EVIDENCE 或 REVISE；只有正确性、复现性、provenance 问题作为 blocker，非阻断美化记 Minor。

**STOP FOR CLOSED-OPEN FIXTURE INDEPENDENT REVIEW**

## Independent Review Decision: 2026-10-01

The independent review in `docs/project/evidence/d6-space-field-closed-open-independent-review.md` returned:

`ACCEPT LIMITED DIAGNOSTIC EVIDENCE`

The closed/open fixture is now closed as a bounded design experiment. Accepted evidence:

- source geometry changes from area 20 with two components to area 21 with one component;
- the opening has positive-area intersection with the barrier;
- source and sampled results are separated;
- coarse sampling sensitivity is exposed rather than hidden;
- temporary reproduction, deterministic payload, rendering, manifest, and scope checks passed.

This decision does **not** freeze production resolution, boundary semantics, route width, corridor/activity roles, door-state policy, IFC opening extraction, Bayesian/ML behavior, or a public API. It does not establish physical traversability or visual permeability.

Next design gate: define the real IFC/Neutral Scene input contract for analysis-domain geometry, boundary/opening evidence, occupancy blockers, and channel-specific permeability. Keep door geometry as context unless an explicit opening relation or owner analysis assumption supplies its meaning. Do not reopen this fixture unless a later contract requires a directly incompatible semantic change.
