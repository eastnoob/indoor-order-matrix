# D6 Checkpoint A: controller review

日期：2026-09-30（本地复核完成日期；审阅的 A 提交来自 2026-09-29）。
审阅提交：`0ce1f0478865a29e3ae18cf3f382e232c4d57c49`。
本文件记录总控技术裁决，不冒充用户新增需求或生产授权；不覆写历史 owner decision、Checkpoint A report 或已有 hashed evidence。

## 当前有效裁决

**2026-09-30：APPROVE Checkpoint A，诊断基线提交 `9a38ea89336c521ff6e076982e986ec27f4f9a53`。**

R1/R2/R3 及第二轮空 gap 问题均已复核关闭。以下原始与第二轮 REVISE、停止标记是历史记录，不再表示 A 当前未获批准。批准不等于 production policy/API/selector 冻结，也不授权完整 Checkpoint B 或自动 space 实验。本轮未执行 IFC/Blender。

## 裁决

**A1–A8 执行已完成；Checkpoint A 证据一致性验收：REVISE。**

退回仅针对下列三个已复现的诊断正确性问题，不要求选 winner、冻结生产状态政策、改变 minimum-member-gap 或选择 Bayesian/ML。

| 项目 | 裁决 | 范围与理由 |
|---|---|---|
| 两个 aggregation id 拆分 | APPROVE | `selected_relation_connected` 与 `all_internal_pairs` 描述不同对象；仅批准诊断语义 |
| 五种 aggregation、三种 scale 并列保留 | APPROVE | 不选默认规则、scale、threshold 或 winner |
| selected/eligible、categorical missingness、canonical/reverse provenance | APPROVE as diagnostic evidence | 现有最小断言可重新运行；不是生产契约冻结 |
| maximal/overlap、singleton/unassigned 的诊断方向 | APPROVE with repairs | 保留输出，不升级为 partition 或 formal membership；受连通性和互斥缺陷影响的结果待重跑 |
| H2 可复现产物 | ACCEPT as execution evidence | 880 rows、16 hard gates 和 5 SVG hash 校验通过；不能据此推断所有算法语义正确 |
| 当前 max-span、counter、veto 结果 | REVISE | 三个最小反例证明实现与声明不一致 |
| 最终状态传播、ambiguity/overlap 政策、group-gap 和 ID tie | DEFER production freeze | 限制已明示；不另设为诊断修复完成条件 |
| production selector、implementation design、B1/M1 | DEFER | 本轮不选择或实现 |
| Checkpoint B、真实 IFC/Blender、自动 space | DEFER execution | 本次不执行；三个错误修复并复核后，单独授权最小三组 source-linked smoke check，不要求先冻结 production selector |

## 核实的问题

### R1. Max-span 把孤立节点并入候选

位置：`scripts/design/group_level/run_inferred_group_candidate_field_probe.py`，`_max_span_candidates()` 的连通性检查（当前第 305 行）。

最小输入：节点 A/B/C；全部内部 pair 均 computed、normalized gap 为 1、bound 为 1；selected 仅 `A|B`。

实际：`[['A', 'B', 'C']]`。声明语义要求：`[['A', 'B']]`，C 保留 singleton/unassigned。

根因：`_connected_components()` 故意不输出 singleton；只检查返回分量数等于 1，不能证明该分量覆盖整个候选。一个连通分量加孤立 C 也满足现有检查。

最小修复应验证唯一分量覆盖全部候选节点。不要盲目修改共享 helper 的 singleton 行为；connected recipe 依赖当前排除 singleton 的规则，singleton 由 `_aggregate()` 另行输出。

### R2. Evidence counter 与字段名不一致

位置：同一脚本，`_candidate_record()` 的 `co_membership_evidence`（当前第 380 行）。

- 内部 relation ids 为 AB/AC/BC，而当前 scale 只选 AB：`selected_pair_count` 实际为 3，应为 1。
- AB 为 invalid，但保留 normalized gap `[1.0]`：`evidence_status` 为 invalid，`computed_pair_count` 却为 1，应为 0。

诊断字段定义：selected count 是本候选 relation ids 与当前 scale selected ids 的交集数量；computed count 是本候选 relation ids 中存在 record、status computed、gap 非空且全部有限的数量。两者独立，不互相代替。不得通过删除原始 invalid 数值来掩盖错误。

### R3. Explicit veto 被缺失的 geometry relation 隐藏

位置：同一脚本，`_candidate_record()` 的 `conflicts` 收集（当前第 354 行）。

最小输入：selected graph AB/BC 连通；A 的成员 a 明确声明 `mutual_exclusion=['C']`；vectors 只含 AB/BC，无 AC geometry record。

实际：候选 ABC 的 `mutual_exclusion_conflicts=[]`、`candidate_status=weak`；单独 `_vetoes(fixture, 'A', 'C')` 可以取得声明。按当前诊断政策应保留 AC veto provenance，并将该候选标为 unassigned/veto diagnostic。

根因：互斥收集仅遍历已存在的内部 vectors。Explicit factual declaration 不应以几何 record 存在为前提。对候选全部内部 group pairs 检查已有 `_vetoes()` 即可；保留 source/target refs，不增加硬性类型分组，也不改变 authored membership。

## 独立验证

本轮实际读取并使用 `receiving-code-review` 核对反馈与调用路径，以及 `verification-before-completion` 运行以下检查。
已读取并评估项目 `speckit-assess-decide`；它是 discovery-to-delivery assessment gate，不是本次局部 checkpoint 验收。本轮未执行其写入流程，也未覆写 `.specify` decision，避免把诊断验收误作 production go。

| 检查 | 本轮实际结果 |
|---|---|
| `pixi run python scripts/design/group_level/run_inferred_group_candidate_field_h2.py verify` | exit 0；880 rows、16 hard gates、source hash、5 SVG/XML hash |
| focused pytest：group self-description、canonical contract、canonical geometry | exit 0；52 passed |
| 直接调用 `design_semantics_assertions(registry)` | exit 0；aggregation/status/canonical-space-key 全部 true |
| `git diff --check 0ce1f04^ 0ce1f04` | exit 0 |
| R1/R2/R3 直接调用现有 helper 的独立反例 | 三项均复现；未改文件或读取 scoring truth |

现有 verify 校验已保存 assertions 的 passed 字段及 hashes，不会发现未覆盖的反例。直接重跑现有断言也通过，说明当前覆盖缺少这些情况，不是产物被篡改。

本轮没有重生成 H2，没有运行 full pytest、IFC、Blender 或自动 space，没有修改 probe、production、API、adapter、测试、依赖或源模型。原有 24 条未跟踪条目未纳入本裁决。

## 发回原实现 session 的 prompt

```text
项目：D:\PROJECTS\understandOtherPackage\order_analyzer
任务：Checkpoint A 最小正确性修复。不是新的算法设计，也不是 Checkpoint B。
基线：0ce1f0478865a29e3ae18cf3f382e232c4d57c49。

先读 AGENTS.md、架构记忆、本 controller-review、A checkpoint report，
以及现有 probe/runner/aggregation 与 status fixtures。先核对 HEAD 和 dirty work。

只解决本 review 的 R1/R2/R3：
1. 先增加能失败的 design regression：selected 只有 AB，AC/BC 均有
   computed finite gap 且在 bound 内；max_span 不得包含孤立 C，
   实际 _aggregate 输出必须保留 C 为 singleton/unassigned。
2. selected counter 只计当前 scale 选中的 candidate relation keys；
   computed counter 按 computed/nonempty/finite geometry evidence 计数。
   覆盖未选内部 pair、invalid 保留数值、非有限值，不删除原始证据。
3. AB/BC 连通而 AC record 缺失，A 明确排斥 C 时，candidate 必须保留
   veto source/target refs 及当前 veto diagnostic 状态。
   遍历候选内部全部 group pairs 检查声明，不依赖 geometry vector 存在。

先确认三项 regression 在旧实现失败，再做最小根因修复并复跑。
检查共享 helper 的所有调用；不要更改 connected helper 的 singleton 约定
来破坏其他 recipe；不要新增框架或重写算法。
保留三个 scale、五个 aggregation，不选 winner，不调参数。
minimum member-gap、ID tie 和最终 status/candidate policy 继续标注
diagnostic limitation，不要求现在冻结 production policy。

允许文件：现有 scripts/design/group_level/ 的相关 probe/runner/fixtures；
对应 H2 evidence/report/record/manifest/SVG 和 checkpoint report。
不得修改本总控裁决或历史 owner decision；不得改 features/、adapters/、
test/、API、NeutralSceneV2、依赖、源 IFC；不得运行 B/Blender/自动 space。

修复后逐项运行现有 H2 runner 的
probe -> score -> visual -> report -> record -> manifest -> verify，
以及当前三组 focused pytest、JSON/XML/hash 与 scope/diff 审计。
如报告模板仍有已拆 id 的过时冲突句，随本次重生成澄清；不扩展实验范围。
明确说明为 exploratory corrective rerun，不是新的独立预注册验证。
记录 scoring/candidate 变化；无变化也如实说明，不从分数选择规则。

使用 explicit-path staging，提交本任务实际修改的允许文件；
不得 git add -A，不接管既有 24 条未跟踪内容，不改写旧提交。
返回 commit、红/绿回归结果、运行结果、范围审计和限制。
停在 STOP FOR CONTRACT REVIEW，等待总控复核；不自行进入 B。
```

## 有限收口条件

R1/R2/R3 回归通过、原有诊断约定不退化、重生成证据及 hashes 一致、范围审计通过，即可接受 A 为 diagnostic baseline。最终生产政策未冻结不再单独阻止 A 诊断收口。

随后由总控单独派发最小真实 IFC 三组 smoke check：核实 unit/placement/geometry/provenance，并交付可见源模型对照。自动 space 继续作为独立设计实验，不要求用户手工定义走廊或空间，不把 bbox/canvas 静默冒充真实 domain。

**STOP FOR CONTRACT REVIEW**

## 第二轮复核：caed1af

日期：2026-09-30。提交：`caed1afc0f8940df969e6115e03e92ff6454a41c`。

**本轮结论：R1/R3 已关闭；R2 已覆盖变体通过，但空 gap 变体仍须最小修订。A 验收仍为 REVISE，仅剩这一项。**

本轮实际重新运行：

- `design_semantics_assertions(registry)`：aggregation、diagnostic regressions、status matrix、canonical space key 全部通过。
- R1 输出 `[['A', 'B']]`，C 保留 singleton/unassigned。
- R2 有限值变体 selected/computed 为 1/2；non-finite 变体 computed 为 1。
- R3 缺少 AC geometry record 时保留 `a -> C` veto，candidate 为 unassigned。
- H2 `verify`：exit 0；880 rows、16 hard gates、5 SVG/XML hashes。
- focused pytest：exit 0；52 passed。
- `git diff --check caed1af^ caed1af`：exit 0；提交仅 7 个 design/evidence 文件，无生产修改。

### 剩余问题：空 gap 计数会崩溃

位置：`run_inferred_group_candidate_field_probe.py`，`_candidate_record()` 第 390–394 行。

当前表达式：

```python
vector.get("status") == "computed"
and vector.get("normalized_gaps")
and all(math.isfinite(value) for value in vector["normalized_gaps"])
```

当 status computed、normalized_gaps 为 `[]` 时，这个表达式返回列表 `[]`，不是布尔值；传入 `sum()` 后报 `TypeError: unsupported operand type(s) for +: 'int' and 'list'`。本轮已直接调用现有 `_candidate_record()` 复现，exit 1。

这不改变状态政策：computed count 已明确要求 gap 非空且有限，因此该 pair 应计为 0。没有 normalized gap 不应让诊断生成崩溃，也不得填入 0 gap。现有 finite/invalid/NaN 回归没有覆盖空列表。

最小修正：将计数条件中的 `vector.get("normalized_gaps")` 改为 `bool(vector.get("normalized_gaps"))`；在同一 diagnostic regression 增加 computed + empty-list，断言 computed_pair_count 为 0。无需新 API、新模型或改生产代码。

### 发回原实现 session 的追加 prompt

```text
继续 Checkpoint A，不执行 B。先读 controller-review 的“第二轮复核”。
基线 caed1af。R1/R3 与 R2 已有 finite/non-finite 结果已获技术确认，
不要重做这些修复或扩展生产政策。

唯一剩余修复：_candidate_record 的 computed_pair_count 条件中，
把裸 vector.get("normalized_gaps") 转为 bool(...)，避免 computed + []
向 sum() 传入列表。先增加空 gap 反例确认旧代码 TypeError；
修复后断言不崩溃、computed count=0、原始空列表保留，不填零。
沿用现有 diagnostic_regression_assertion；不新增框架或 API。

按已有授权范围重跑 H2 probe -> score -> visual -> report -> record
-> manifest -> verify、focused 52 tests、hash/schema/diff/scope 审计。
明确路径提交实际变更文件；既有 25 条未跟踪内容保持原样。
更新 checkpoint report，返回 commit 与红/绿结果；
停在 STOP FOR CONTRACT REVIEW。不要执行 B/IFC/Blender/自动 space，
不要选 winner、threshold 或冻结 production policy。
```

原有并列诊断方向仍批准。该空 gap 回归修复并通过原有验证后，不再追加生产政策冻结作为 A 收口条件；下一项仍是另行授权的最小真实 IFC 三组可视化 smoke check。

**STOP FOR CONTRACT REVIEW**

## 第三轮复核与 A 收口：9a38ea8

日期：2026-09-30。审阅提交：`9a38ea89336c521ff6e076982e986ec27f4f9a53`。

### 独立验证结果

| 检查 | 结果 |
|---|---|
| 直接运行 `design_semantics_assertions(registry)` | aggregation、diagnostic regressions、status matrix、canonical space key 全部通过 |
| R1 | max-span 为 AB；C 保留 singleton/unassigned |
| R2 | finite selected/computed 为 1/2；non-finite computed 为 1；empty gap computed 为 0，原始 `[]` 保留 |
| R3 | AC geometry record 缺失时仍保留 `a -> C` veto provenance，candidate 为 unassigned |
| H2 `verify` | exit 0；880 scoring rows、16 hard gates、5 SVG/XML hashes、source hashes |
| focused pytest | exit 0；52 passed |
| `git diff --check 9a38ea8^ 9a38ea8` | exit 0 |
| 提交范围 | 7 个既有 design/evidence 文件；无生产代码、正式测试、adapter/API 或依赖修改 |

本轮直接运行断言并核验产物，没有重生成 H2，没有运行 full pytest、IFC、Blender 或自动 space。当前复核使用 receiving-code-review 的核实流程和 verification-before-completion 的实际命令检查，未开启新的 assessment/specify/implementation 流程。

### 裁决

**APPROVE：Checkpoint A 收口为可复现的 diagnostic baseline。未发现本次允许范围内新的阻断问题。**

- 批准并列三种 scale、五种 aggregation，以及已验证的诊断状态、计数、provenance 和反例行为；不选 winner。
- H2 分数仅表示该 synthetic fixture 的计算对照，不证明真实场景分组准确率或心理效度。
- minimum-member-gap、ID tie、最终 candidate/uncertainty/space policy 继续属于生产设计未决项，不阻止本次诊断基线收口。
- 旧 owner decision 和 A report 是历史/执行记录；本总控裁决是 A 当前批准依据，不能把历史 REVISE 误读为 A 仍未获准。

### 下一步边界

推荐下一独立 checkpoint 是最小真实 IFC 三组 source-linked smoke check：检查家具组资格、单位、placement、实际 geometry 和来源映射，展示真实 source meshes 与描述 overlay 的对应关系。该任务用于发现接入问题，不验证最终 inferred membership，不立即扩大到全模型候选枚举。

执行前单独派发有明确范围的 prompt。当前不自动执行、不授权完整 B、生产集成或自动 space。自动 space 的设计目标仍保留：系统推导几何和角色，不要求用户预定义走廊；研究时区分范围、剩余空区、空区结构和角色，不把 bbox/canvas 静默当真实 domain。

**CHECKPOINT A APPROVED — STOP BEFORE REAL IFC SMOKE CHECK**
