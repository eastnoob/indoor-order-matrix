# D6 Task 3d：家具组之间 inferred group 的独立设计审查交接

- 日期：2026-09-28。
- 状态：设计笔记，待独立审查与 owner 裁决；不是最终规格或 implementation design。
- 代码事实基线：`07ef271`。本笔记只记录该基线后的用户澄清和设计审查结果。
- 原任务仍由当前设计作者负责。只读独立子代理已完成反向审查；没有创建或转交新的独立用户 session。
- 允许范围：设计文档、设计探针说明、设计证据。禁止改生产代码、adapter、正式测试和依赖，禁止实现 descriptor 或 Bayesian 算法。

## 1. 阅读顺序和优先级

先读 `AGENTS.md`、`docs/indoor_layout_evaluation_matrix_architecture_memory.md`，再读本笔记及以下文件：

- `docs/superpowers/specs/2026-09-27-clean-room-layout-descriptor-contract-design.md`
- `docs/superpowers/plans/2026-09-27-clean-room-layout-descriptor-contract.md`
- `docs/project/d6-group-level-self-description-design.md`
- `docs/project/evidence/d6-group-level-design-probe.json`
- `docs/project/d6-migration-ledger.md`
- `features/scene_inference.py`、`features/neutral_scene_views.py`、`features/position_grammar.py`、`features/column_grid.py`
- `adapters/ifc_bonsai.py`、`adapters/svg_scene.py`
- `test/test_neutral_scene_analysis_regression.py`、`test/test_floorplan_scene_loader.py`、`test/test_column_grid_trend_regression.py`
- `skills/ifc-export/SKILL.md`、`skills/visualarq-source-adapter/SKILL.md`

用户最新澄清优先于旧文档。本笔记明确修正旧设计中的候选入口、推断层级、affordance 来源和 IFC/SVG 验收范围。其余算法、阈值、模型和 schema 建议仍未获 owner 批准。

`docs/superpowers/plans/2026-07-02-entry-door-slot.md` 是现有入口/路径实现的历史参照，不是本次 inferred-group 设计的执行计划。

## 2. 用户已经明确的边界

1. 最小分析节点是家具组。单个家具仅用于构成其所属家具组的几何，不自动成为独立候选节点。
2. 只有 `IfcGroup.ObjectType == "furniture_group"` 进入本 descriptor 的家具组候选集合。其他 `IfcGroup` 只保留 source provenance。
3. `OM.Role=furniture_group` 是现有上游标记，导出为上述 IFC 类型。它定义输入家具组，不能用来替代家具组之间的几何推断。
4. 要设计的 inferred group 发生在这些家具组之间，依据几何关系。旧的泛用 group/region 标签分组方案应弃用；这不等于弃用明确 authored 的家具组候选入口。
5. affordance 是外部传入的带标签属性、几何或替身。不能由家具类型或当前几何自动猜测。它是否进入代表几何和 inferred membership 仍需设计审查。
6. IFC 是主来源，包含 2D、3D 和混合指标。SVG 是部分 2D 算法的测试载体，不承担完整 IFC/3D parity。

前一轮回复中的“先冻结”“第一阶段使用”若超出这六项，应读作作者建议，而非 owner 已批准的规格。

## 3. 原设计、实现事实、修订方向、待决问题

| 议题 | 原设计或旧前提 | 当前实现事实 | 修订后的设计方向 | 仍需 owner 决定 |
|---|---|---|---|---|
| 候选入口 | `IfcGroup` 或等价 adapter relation 的表述过宽 | `adapters/ifc_bonsai.py:713` 按 `ObjectType` 区分家具组和普通组；`features/neutral_scene_views.py:706` 仍接受全家具的普通组 | 仅明确的 `furniture_group` 作为 IFC 候选；普通组 fallback 待弃用 | SVG 的等价 2D fixture 如何标注该事实；外部来源的 canonical 映射验收 |
| OM 标签 | 前次讨论尚未确认标签 | `skills/ifc-export/SKILL.md:66` 明写 `OM.Role=furniture_group`；导出无自身产品几何的 `IfcGroup` | OM 是上游来源，IFC `ObjectType` 是当前 adapter 可读入口；组几何来自成员 | 无须重新询问是否使用 OM；只审查不同输入路径是否保留来源 |
| inferred group 层级 | 旧 activity group 位于单家具 extent 与 activity region 之间 | `features/scene_inference.py:71` 仍按 semantic keys 建组；`:2105` 仍有 region fallback；尚无家具组之间的独立几何分组步骤 | 新推断以家具组为节点；不把现有函数误报为已实现的新算法 | 新 inferred group 与旧 activity-group/activity-region 的关系和命名；旧层是否仅 reference |
| 多重 authored membership | 契约允许一个物体属于多个组 | `features/neutral_scene_views.py:726` 的 `setdefault` 只保留首个组 | 所有明确 membership 保留；共享 member 产生组间依赖，不能假设节点独立 | 共享 member 的组间 gap/overlap 是否可用于 membership，还是只作诊断 |
| affordance 与代表几何 | 旧 group extent 混合 physical 和 affordance envelope | `features/scene_inference.py:89` 使用成员 affordance extents 的 union envelope；memory 禁止自动生成 affordance | 外部 affordance 与 physical support 分列；不能静默合并成单一支撑量 | physical-only 或额外 affordance channel；标签、绑定、缺失和高度适用范围 |
| trend estimand | probe 将 doubled-angle 结果称 member frame consensus | `features/column_grid.py:648` 使用 `4θ`；probe 使用 `2θ` | 推荐 deterministic baseline 为 `group_frame`，axis 若保留则独立；0°/90° 在两者中语义不同 | 首个 deterministic trend 是否批准 frame；Bayesian 首模是否同样选择 frame |
| overlap/union | additive support 已有；overlap area 和 union 尚未计算 | probe 有 additive area、center、总 covariance；没有完整 overlap/union 结果 | 推荐首阶段 pairwise overlap diagnostic、union 延后；additive area 不扣 overlap | pairwise 多重重叠的报告语义；normalized gap 分母是否批准及尺寸偏差 |
| invalid/missing | 设计写 any-invalid 导致 group invalid，但下游政策待决 | probe 覆盖部分缺失/退化数值检查，尚无完整 valid/missing/invalid 混合门 | 推荐 invalid group 排除 computed 下游；valid support 仅诊断；invalid 不能变 missing | missing/partial 是否能进入正式 inferred-group 候选图 |
| IFC/SVG 验收 | 旧设计与迁移表笼统写全量 parity | `test/test_neutral_scene_analysis_regression.py:1464` 的等价证据是 planar scope | 2D 相同 canonical facts 做 IFC/SVG 数值验收；3D/混合指标使用 IFC fixtures | fixture、单位、analysis plane、tolerance、验收负责人 |
| probe schema | schema v1 有已运行结果和计划项；不是生产契约 | `scripts/design/group_level/run_group_level_probe.py` 仅做 synthetic 比较和数值断言 | planned fixtures 只能标 planned；不把脚本、默认阈值或结果命名升级为生产规格 | planned fixtures 是否纳入 v2；v2 覆盖哪些已运行和待运行项目 |

## 4. inferred group：交给审查者比较的假设

先回答目标：inferred group 表示几何聚集，还是功能/活动组合？纯几何不能直接证明人类的功能意图。本轮可设计几何聚集证据，但不能称其已获感知或功能效度验证。

建议先固定候选家具组及其状态，再比较独立几何关系。可审查的观测包括 boundary gap、2D 投影 overlap、3D clearance/overlap、尺寸比例、level/Z 兼容性和墙体阻隔。physical 与外部 affordance 的观测保持来源区分。墙体、开口和高度应如何限制关系仍是候选政策。

| 候选假设 | 可检验优点 | 反例和拒绝条件 | 当前裁决 |
|---|---|---|---|
| normalized-gap graph 的 connected components | 简单、易审计；允许连续空间聚集 | A-B 近、B-C 近、A-C 远也会合并；是否允许这种链式结构必须由目标决定 | 比较基线；不能未经审查认定正确或错误 |
| complete-link 或最大组内 pairwise gap 约束 | 可以限制长链和组内跨度 | 可能拆散合理的长排家具组；阈值、平局和划分稳定性尚未定义 | 反链式候选；不是已选算法 |
| 密度或概率分组 | 可研究多尺度或不确定成员关系 | 小场景数据不足、假设和参数更多；不能用 Bayesian 名称替代 estimand 定义 | 后续 reference；本轮不实现、不选 prior |

首轮 membership 不建议使用 trend/coherence。先按方向一致性挑成员，再报告方向一致性，会造成循环证据。若以后需要方向参与 grouping，必须声明新的目标、独立评价证据和敏感性比较。

组间 neighbor edge、inferred-group membership 和 activity-region gap path 是三个不同量。neighbor graph 节点为家具组；gap-path graph 节点为 activity-region candidates，描述自由空间、占用率、路径宽度和连通性。两者并存，不能互相替代或自动反写 membership。

## 5. 最小设计 fixtures 和审查依据

既有计划保留：0°/90°/180°/270°、axis/frame 差异、valid/missing/invalid member、overlapping members、additive/union area 对照、unequal-size normalized gap、多重 authored membership、disconnected neighbor components、等价 IFC/SVG canonical 2D facts。

新增 inferred-group 比较计划：

- 三组桥接链、长排、两簇加桥接组：判断 chaining 是目标还是错误，比较两种候选。
- 不等尺寸和统一缩放：比较 normalized gap 分母，检查尺度不变性及大组偏差。
- 同 XY 不同楼层、上下叠置、隔墙近邻：区分投影近邻、3D 关系与阻隔。
- physical contact、physical overlap、affordance-only overlap：不把所有 overlap 当作同一种组证据。
- 几何近但 frame 冲突、几何远但 frame 一致：检查 trend 不回写首轮 membership。
- valid、missing、invalid 家具组节点；共享 authored member：检查排除原因、partial 与依赖。
- IFC 3D 场景及其 SVG 2D 投影：只比较声明的 2D facts；混合指标单独验收。

这些都是 planned，不声称已经运行。审查应比较几何反例、平移/旋转/缩放/tessellation 稳定性、歧义、缺失和可审计性。synthetic truth 只能验证计算性质，不能证明真实场景准确率或人类感知效度。

`support_area` 是几何面积；`directional_member_support` 是方向成员数量或声明权重；`coherence` 是方向一致性；`strength` 是确定性几何证据强度；`uncertainty` 是未来区间或 posterior。deterministic strength 不是概率，不能解释成“方向正确概率”。

未来模型必须分别声明：

```text
P(group_frame | member geometry, missingness, reliability)
P(group_axis | member geometry, missingness, reliability)
P(group_edge | group geometry, gap, overlap, uncertainty)
```

前两项是不同 estimand 的候选，不表示两者均已选择。gap/overlap 是 geometry 计算的观测；edge 是几何关系，不是 authored membership；posterior 不是人的感知概率。missingness、geometry uncertainty 和 member dependence 都不能省略。edge posterior 也不能冒充 inferred partition posterior。

probe 仅用于候选比较、数值 oracle、退化/缩放/旋转/缺失/tessellation 检查和可视化诊断。不得解释成 production API、默认心理阈值、Bayesian prior、真实场景准确率或人类感知效度证据。

## 6. 下一 session 的具体任务

可将以下文本作为独立审查 session 的任务：

> 请按本笔记的阅读顺序审核 D6 Task 3d。先核查实现事实，再质询家具组之间 inferred group 的目标、代表几何和候选算法。只接受 IfcGroup.ObjectType=furniture_group 为 IFC 候选入口；affordance 为外部输入；IFC 主验收，SVG 仅 2D oracle。请逐项输出原设计、当前实现事实、建议修订、反例、待 owner 裁决。比较 connected components 与 complete-link 的适用边界，不直接选默认阈值。明确 hard partition/overlapping membership、未分组节点、partial/invalid、共享 member、阻隔与 3D 关系的政策。最后给出接受、需修订或暂缓的理由。不要进入 Task 3c、implementation design、生产代码或 descriptor API 实现。以 STOP FOR DESIGN REVIEW 结束。

审查输出还需对此前五项给明确建议：Bayesian 首模 frame/axis、pairwise overlap/union、invalid diagnostic 的下游边界、IFC/SVG fixtures/tolerance/负责人、probe schema v2。审查者可以建议，owner 才能批准；待决定项不能静默变成最终规格。

## 7. 本次验证记录

本笔记未改变 probe 算法、fixtures、结果 JSON 或 production code。验证结果在文档 commit 前补录：JSON 解析、现有设计 probe 数值断言、`git diff --check`、修改范围审计。现有 probe 通过不能证明本笔记的新增 fixtures 已完成。

**STOP FOR DESIGN REVIEW**
