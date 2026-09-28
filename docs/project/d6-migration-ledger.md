# D6 clean-room migration ledger

本表只记录设计候选的迁移裁决。`migrate`、`wrap`、`rewrite`、`discard`、`reference_only` 是设计状态，不是已授权实现。现有代码和测试是 reference evidence；任何迁移都必须通过 canonical contract 和独立测试。

后续用户澄清与独立审查见 [设计交接笔记](d6-inferred-group-design-review-handoff.md)。候选仅为明确的 IFC `furniture_group`；inferred group 发生在家具组之间；IFC/SVG parity 限于等价 canonical 2D facts，3D/混合指标由 IFC fixtures 验收。这些边界优先于下表的宽泛旧表述，尚未批准的算法不因此冻结。

| capability | current location / fact | classification | reason | implementation gate / owner question |
|---|---|---|---|---|
| affordance zones 与 union envelope | `features/scene_inference.py`；architecture memory 定义 furniture affordance extent 为 union envelope | `reference_only` | D6 3d 首 slice 只消费 canonical member support；affordance/use-zone 和 region extent 属后续 region/path scope | 后续 region/path task 决定是否迁移；union topology 仍需 owner 冻结 |
| authored group extraction | `adapters/ifc_bonsai.py::_native_group_records()`；`adapters/svg_scene.py::_authored_groups()` | `wrap` | membership 是 source fact，必须保留 IFC/SVG provenance、multi-membership 和 `authored` kind；不能让 adapter 定义 descriptor | canonical adapter bridge + IFC/SVG parity acceptance gate |
| inferred group | `features/scene_inference.py` 的 region/group inference | `rewrite` | inferred activity/visual group 不能覆盖 authored membership；需要独立 record、status 和 estimand | owner 决定 inferred candidate schema；不得在 Task 3d 实现 |
| position grammar | `features/position_grammar.py` 的 authored/line/pair/grid/cluster/unstructured candidates | `reference_only` | 它描述 assembly grammar，不是 group trend 或 normalized boundary-gap estimand | 后续 position task 单独定义输入、truth 和迁移门 |
| column-grid trend | `features/column_grid.py::_frame_from_angles()` 的四倍角 frame | `wrap` | 现有 0°/90° 等价语义必须可审计地保留为 `group_frame`；不得直接改名为 `group_axis` | wrapper 明确 frame/axis；0/90/180/270 fixture 和 regression parity |
| internal overlap network | `features/scene_inference.py` group internal network | `migrate` | group 内 member overlap 是 relation evidence，和 authored membership 分层后可复用 | canonical support、overlap provenance、multi-membership 和 disconnected tests |
| inter-region gap-path graph | `features/scene_inference.py::build_inferred_region_gap_path_graph()` | `reference_only` | 节点是 activity-region candidates，描述 free space/path width/connectivity；不等于 furniture-group neighbor edge | region/path checkpoint 单独验收；不得由 D6 neighbor 替代 |
| IFC/SVG parity | `adapters/ifc_bonsai.py`、`adapters/svg_scene.py`；现有 parity tests 只是 reference | `wrap` | adapter 只能产出相同 canonical facts；parity 是实现阶段验收门，不是设计 probe 的替代 | 同一 facts 必须匹配 geometry、status、trend estimand、gap/overlap 和 provenance |
| legacy orientation fallback | 历史 record metadata、block axis、authored local orientation、transform history | `discard` | 设计要求最终 world-space Analysis geometry；历史方向不能悄然影响 trend、strength 或 coherence | 缺 geometry 返回 explicit unavailable/uncertain；owner 只可另行批准兼容字段 |
| deterministic strength/coherence | `features/scene_inference.py` group metadata；probe member consensus | `migrate` | 这是可计算 evidence，但必须拆开 `directional_member_support`、`coherence`、`strength`；strength 不是 probability | schema 明确单位、basis、status；synthetic invariance 和 contradiction fixtures |
| Bayesian uncertainty | 当前未实现；旧文档只给候选边界 | `rewrite` | 必须先选 `P(group_axis | …)` 或 `P(group_frame | …)`，并显式建模 missingness、geometry uncertainty、member dependence；neighbor 另有 edge posterior | owner 选 estimand/prior boundary；同 truth 下比较 calibration；Task 3d 不实现 |

## 迁移共识

- `group_frame` 是兼容当前 column-grid trend 的 deterministic baseline；`group_axis` 若保留，作为独立描述量。
- representative 首阶段使用 additive `support_area`、面积加权 `center`、within/between covariance；polygon union 暂缓，overlap 不从 normalized-gap denominator 扣除。
- invalid member 不得静默当 missing；group status 至少保留 `invalid/not_computable`。
- `normalized_boundary_gap` 和 `inter-region gap-path graph` 并存，节点 scope、观测和用途不同。
- IFC/SVG parity 是实现阶段验收门。probe 只做候选比较、数值 oracle、退化/缩放/旋转/缺失/tessellation 检查和可视化诊断。

## 本轮设计裁决（Task 3d）

- 首个 deterministic trend 使用 `group_frame`（`4θ`、modulo 90°）；`group_axis`（`2θ`、modulo 180°）保留为独立描述量。
- Bayesian 首模与 deterministic baseline 使用同一 estimand：`P(group_frame | member geometry, missingness, reliability)`。
- authored furniture-group nodes 先固定，再生成 pairwise relation graph；connected-components 仅 chaining baseline，complete-link/max-span 必须比较。
- 首轮 membership 禁用 trend/frame/coherence/strength；shared authored member 的零 gap/overlap 仅作 diagnostic。
- `partial/missing` 可保留在 relation graph，但不能作为完整 membership evidence；`invalid` 只作 diagnostic，不进入正式 candidate generation。
- representative 使用 additive support、area-weighted center、within/between covariance；union 延后，overlap 不从首阶段 normalized-gap denominator 扣除。
- IFC 是 3D、Z、clearance、barrier 和混合指标的唯一验收来源；SVG 只验等价 2D canonical facts。
- probe schema v2 纳入角度周期、状态混合、overlap/union、尺度、multi-membership、chaining/complete-link、barrier、level、stacking 和 IFC/SVG 2D parity；仍不是 production API 或准确率证据。

## 停止条件

2026-09-28 E8b/E10b 总控收口见 [设计裁决](d6-group-level-design-decision.md)：批准 pairwise observations 分层、已测状态边界、IFC 输入事实和 SVG 分离矩形对照；design probe 已补齐轴对齐 contact/overlap/near 反例。当前未完成同场景双 adapter parity。暂缓 selector 不等于删除 inferred-group 或 Bayesian 目标；迁移分类保持不变。

2026-09-28 objective-design 更新见 [目标语义设计表](d6-group-level-objective-design.md)：建议统一 relation computation，先输出 local-neighborhood，再输出带尺度和规则 provenance 的 candidate views；不把 CC、complete-link、max-span 中任一者静默冻结为唯一 inferred-group 真值。进入 implementation design 前仍需 owner 冻结 canonical descriptor 和 candidate objective。

设计裁决已记录，但最终 candidate selector、输出 partition policy、multi-scale denominator、shared-member 后续证据政策、union topology 及 IFC/SVG fixture acceptance 仍未冻结。完成这些设计门前，不进入 Task 3c、implementation design、descriptor API 或 production algorithm。
