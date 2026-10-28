# Group Axis-field Hierarchy Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Delegation requires the existing owner/user route; this document does not independently authorize agents or version writes.

**Goal:** 在现有 axis-potential 包中追加已冻结的圆周方向族，保留全部原叶与完整 scope 支持，并以指定真实 IFC 的 retained 数据交付完整可索引图面。

**Architecture:** 包内普通 helper 从原始 source-axis outputs 计算 exact angular topology 与 max-union family evidence。现有 factory 显式接收 namespace，`evaluate(source_envelopes)` 和 shared core 不变；原 renderer 复用同一份平面几何。

**Tech Stack:** Pixi / locked Python 3.12.13、标准库 `fractions.Fraction` / JSON / hashlib / XML、pytest；不新增依赖。

**Spec:** [Owner-reviewed frozen design](../specs/2026-11-01-group-axis-field-hierarchy-design.md)。**状态：计划文档已编写并自检；实现与下方四项任务尚未开始。**主状态见[阶段 2B.6a.16](2026-10-26-group-attribution-evidence-field-implementation.md)；下一项 .16.1。

## Global Constraints

- 实施前读 `AGENTS.md`、架构记忆、software architecture 和 spec；所有新增函数有 English-first docstring，关键推导解释 why。
- 只用实际 `overall_group_axis` 与原 `S(g,k)=c_g*cos²(delta)`；scope 行、叶 IDs、原 envelopes/channels/status 完整保留。无硬成员、winner、min3、近似压缩或新 parent anchor。
- 连续圆周窗口 `beta<90°`、exact dyadic topology/events、半开 lifespan、max 支持、P\F residual、scale persistence、full/non-anchor profile 按 spec 执行；未知不填零。
- 不新增 measurement layer、registry、DAG 执行框架、公共 API/room model 字段，不改 shared-core/evaluate 签名。DAG 仅是输出。
- 观察测试只读真实 retained envelopes/geometry 及其子集或排序；不造家具/关系/数值布局 fixture，不修改真实值来声称覆盖。常数只用于纯代数不变量。旧 synthetic tests 仅为既有兼容回归。
- 本轮只验真实 37 组基线；候选 O(n²)、family×group cells O(|G|n²)，不声称 provenance 字节数/运行时也有同一上界。无隐藏截断、无千组承诺。
- 每项开始、推进、完成、阻塞时，同时更新**本计划 task steps 与总 checklist、主计划 .16 对应项和执行记录**，记录当前步骤、命令/结果、产物或 blocker、下一项。未验证不勾选，阻塞保留 `[ ]` 并停止依赖项；范围变化先回 owner。
- 执行开始先 `Get-Command jj`、`jj --help`、`jj --ignore-working-copy status`，遵守 installed help 与 jj-first，保留无关 dirty work。此 slice 不要求也不授权 commit、push、merge、jj snapshot；历史 checkpoint 约定不自动扩张本轮权限。

## 文件与接口边界

下列新增路径**尚未实现**；命令在相应任务创建文件后才可运行。

| 文件 | 职责 / 接口 |
| --- | --- |
| Create `features/group_field_hierarchy.py` | 普通函数 `build_axis_field_hierarchy(source_envelopes: tuple[FieldResultEnvelope, ...], source_axis_outputs: tuple[EvidenceOutputChannel, ...], *, scene_namespace: str) -> tuple[EvidenceOutputChannel, ...]`；只依赖标准库和 field_core，消费传入的原叶 records/真实 refs，不反向 import potential 模块 |
| Modify `features/group_axis_potential_field.py` | 现有 `build_group_axis_potential_package(*, scene_namespace: str | None = None) -> EvidencePackage`；None 保持旧模式，非空 namespace 冻结闭包启用追加输出，空值拒绝；原 `_source_axis_field_outputs` 只计算一次 |
| Modify `scripts/design/group_level/run_group_axis_potential_ifc.py` | 现有 `_package_contract(description, envelopes, query, plane, source_sha256, artifact_paths, result, *, scene_namespace=None)` 增可选声明，None 保持旧 contract；扩展模式从实际 result 版本与 namespace/recipe 建 contract |
| Create `scripts/design/group_level/run_group_field_hierarchy_ifc.py` | `run(retained_run: Path, output_root: Path) -> Path`；CLI `--retained-run`、`--output-root`，后者为新结果目录、已存在则拒绝覆盖；不加载 IFC |
| Modify `scripts/design/group_level/render_group_axis_potential_preview.py` | 保持 `load_preview(replay: Path)` / `run(replay: Path, output: Path) -> Path` 与原 CLI；有 hierarchy 文件时追加 family 索引/矩阵/同平面视图，旧输入行为不变 |
| Create `test/test_group_field_hierarchy.py`, `test/test_group_field_hierarchy_ifc.py` | 前者逻辑/retained package 检查，后者新 runner 与 indexed-view 完整性 |
| Modify `test/test_group_axis_potential_field.py`, `test/test_group_axis_potential_preview.py` | 前者使用已有 `_retained_envelopes` 加 legacy preservation/namespace 检查；后者扩展 retained hierarchy 渲染检查 |
| Update 主计划、spec、index、architecture、memory、merge note | 实施进度与证据同步；新证据记录为 `docs/project/evidence/group-axis-field-hierarchy-v1.md`，仅实施后创建 |

`FieldResultEnvelope`、`EvidenceOutputChannel`、`EvidenceChannelReference`、`EvidenceOutputScale`、`EvidencePackageOutput` 均来自现有 `features.field_core`。不引入自定义包输出容器；helper 的内部字典记录仅为包内计算。

## 总 checklist

- [ ] Task 1 / .16.1：hierarchy helper 与公式/retained 检查通过。
- [ ] Task 2 / .16.2：potential package、namespace、lineage 与独立 freshness 检查通过。
- [ ] Task 3 / .16.3：指定 retained replay、完整索引矩阵/平面/manifest 交付通过。
- [ ] Task 4 / .16.4：文档/覆盖记录同步并获 owner 结果审阅。

## Task 1 / .16.1：Hierarchy logic

**Files:** Create `features/group_field_hierarchy.py`、`test/test_group_field_hierarchy.py`。

**Consumes/produces:** 使用上表 helper 签名。传入同次 `_source_axis_field_outputs` 记录中的 `axis_field_support`、`non_self_profile`、`soft_view_direction` 或 `source_axis_scope_diagnostics`；由原 envelope 取得真实 query、target 和可引用的 overall-axis 渠道。返回 spec §7 的八类具名输出，不返回新容器或改写输入。

- [ ] 写 failing tests：直接从 `outputs/design/group_trend_alignment_field_ifc/run_20261027T224335Z/envelopes.json` 读取 `envelopes` 数组，用现有 `run_group_axis_potential_ifc_replay._load_envelope` 还原；先验证 manifest IFC SHA-256 和顶层 project ID。把原 package 输出中的上述四类 source-axis channels 传入 helper。没有这些 retained 文件应明确失败，不能 skip 成通过或造替代数据。
- [ ] 测精确角度/alias、全连续窗口 birth/death/active、全部相邻父边/无环、多父/多顶、输入倒序确定性、rational pair JSON 无损往返。逐族用原 retained cell 重算 `J=max(S)`；核对 full/non-anchor 行域/分母、support_mass/n_eff、P\F residual 和只读 Q；0/1/2 个实际源的子集检查只代表这个子 scope，不能改源值。
- [ ] 纯代数补 exact unwrap 舍入反例、max 幂等/单调性、区间界、n_eff 零质量和向量 cancellation；这些常数不建立场景 fixture。例如：

```python
from fractions import Fraction
from math import nextafter

def test_exact_unwrap_keeps_distinct_binary64_angles():
    """Check arithmetic only; these constants do not describe furniture."""
    a, b = 1.0, nextafter(1.0, 2.0)
    assert a != b and a + 180.0 == b + 180.0
    qa, qb = Fraction.from_float(a), Fraction.from_float(b)
    assert qa + 180 < qb + 180
    assert (qb + 180) - (qa + 180) == qb - qa
```

- [ ] Run RED：`pixi run pytest test/test_group_field_hierarchy.py -q`，记录真实失败；再按 spec 实现最小 helper：canonical float→Fraction、精确类/窗口/事件、原叶 max 与 bounds、全部统计/relations/residual/direction/diagnostics。非 computed 输出给 explanation；raw enum 只用 existing 七状态。无轴仅诊断，空 source 继续 caller/core 边界。
- [ ] Run GREEN 同命令；核对每个 derived_from 都来自传入 envelope 的实际 channel，leaf/child refs 仅作 provenance，state 保留。记录本源未观察到的 branch 与仅代数覆盖项，完成本任务/主 .16.1 后才继续。

**检查口径：**missing/invalid/全零等新状态逻辑可以用数学/结构不变量验证；不可通过修改真实 envelope 数值生成“新的真实 IFC 覆盖”。精确同角类只保证 support-function redundancy，不合并 self/provenance。已知支持和浮点代数用 pytest.approx；topology/events 用精确相等。

## Task 2 / .16.2：Package / namespace / freshness integration

**Files:** Modify `features/group_axis_potential_field.py`、`scripts/design/group_level/run_group_axis_potential_ifc.py`、`test/test_group_axis_potential_field.py`；追加新逻辑检查至 `test/test_group_field_hierarchy.py`。`features/field_core.py` 不改。

- [ ] 在既有 test 文件使用现有 `_retained_envelopes()` 写保留检查；新增 factory keyword 的 RED 后再接线。示例中 namespace 是已核验实际 IfcProject ID：

```python
def test_hierarchy_mode_preserves_every_legacy_output():
    """Hierarchy is additive over the exact retained input and legacy leaves."""
    sources = _retained_envelopes()
    legacy = build_group_axis_potential_package().evaluate(sources)
    expanded = build_group_axis_potential_package(
        scene_namespace="ifc-project:2uGd6yom9GZe5$z7LfbGW0"
    ).evaluate(sources)
    original = {(o.target["identity"], o.channel): o for o in legacy.outputs}
    actual = {(o.target["identity"], o.channel): o for o in expanded.outputs}
    assert all(actual[key] == value for key, value in original.items())
    assert expanded.source_envelopes == legacy.source_envelopes
    assert len(actual) > len(original)
```

- [ ] 现有 aggregate 函数仍负责旧模式；将 source-axis outputs 留为同次局部值供 helper 复用。扩展 factory 的 output function 固定 namespace，使用 `axis-with-hierarchy-v1` function version 与 `group-axis-field-hierarchy-output/v1` 包 schema；recipe 为 spec 的 `source-axis-circular-arc-lt90-v1`。不让 helper import potential，不重算/覆盖原叶，不把 Q_F 当 anchor。
- [ ] `_package_contract` 新 keyword 只影响 hierarchy 模式：recipe dependency 显式 hash namespace、hierarchy recipe/version、exact numeric policy 与 schema/function versions；source dependency 同时保留 pinned IFC hash及实际 retained 输入/原 source identities 的规范指纹，不只看文件时间。targets 为 scope IDs 与本次输出 target identities 的稳定去重并集，包含移除/新增 family 的比较地址。None 维持现有契约。
- [ ] 独立读取当前 retained inputs 并重新 evaluate/build 当前 contract，调用实际 `evaluate_evidence_package_freshness(cached_contract=..., current_contract=..., artifacts_available=True)`；不得拿同一 contract 对象当 cached/current 的唯一证明。真实 scope 子集→完整恢复、重排序必须可复算：子集 target set 的丢失/恢复导致 whole-package stale/恢复 fresh，affected_targets 含两边并集。其断言为 `stale["recompute_required"] is True`、`restored["recompute_required"] is False`；query/plane/source/recipe/channel/algorithm 变化按现有 reason codes 分开记录。
- [ ] 测 namespace 的声明缺失/空字符串/冲突、function version 纳入 identity、source refs 非替代性、所有源/原 4,112 输出保留、family logical identity 不依赖 raw leaf ID。current semantic query tag `group-trend-alignment-v1` 保留；非语义 metadata counters 目前没有 live 输入，不能以修改它声称真实 rotate/undo 验收。family semantic-content 恢复不自动证明跨 source/result identities 缓存命中。
- [ ] Run：`pixi run pytest test/test_group_field_hierarchy.py test/test_group_axis_potential_field.py test/test_group_axis_relation_diagnostic.py test/test_evidence_package_output.py test/test_evidence_package_freshness.py -q`。只运行本次相关回归；失败有针对性修复，记录 .16.2 证据后继续。

## Task 3 / .16.3：Retained IFC replay and complete indexed visualization

**Files:** Create `scripts/design/group_level/run_group_field_hierarchy_ifc.py`、`test/test_group_field_hierarchy_ifc.py`；Modify `scripts/design/group_level/render_group_axis_potential_preview.py`、`test/test_group_axis_potential_preview.py`。

- [ ] runner 测试先失败：`run(retained_run, tmp_path / "hierarchy_run")` 消费 **axis replay** `outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z`，核验 source_manifest 的 source/source_after SHA-256、顶层 `project_global_id`、完整 plane/frame/scope、description/source_reuse 及实际文件哈希，读取原 envelopes/matrix/output。通过既有 `_load_envelope`/factory 计算新输出，不 import IFC extraction 路线或重新提几何。project ID 不在 `source` 子字段。
- [ ] 实现 `run` 与两个 CLI 参数，结果目录已存在则拒绝覆盖；保留旧输入 bytes/legacy IDs，不复制整个 IFC。输出文件固定为：`axis_potential_output.json`、`envelopes.json`、`description.json`、`source_manifest.json`、`source_reuse.json`、`field_matrix.json`、`field_profiles.json`、`field_directions.json`、`field_view_manifest.json`、`view_manifest.json`、`hierarchy.json`、`family_matrix.json`、`family_profiles.json`、`family_directions.json`、`family_view_manifest.json`、`package_contract.json`、`package_status.json`、`report.json`。前三种 family 数据与 hierarchy 均从本次 package outputs 序列化，不第二次推断。
- [ ] report 记录 37 scope / 37 原叶 / 1,369 原 cell / 4,112 原输出保留、新 class/family/edge/cell 实数、覆盖与未覆盖状态、exact event pair、源/输入指纹和版本、namespace。不预设 family 数；把 machine-readable all-target manifest 映射到每个 leaf/family/cell 的 indexed plan。manifest 与 report 都说明未重提 IFC、不声称现实 cluster 或 live UI。
- [ ] renderer 保留旧 preview 输入行为，hierarchy 模式读取同一个 description geometry dataset 和 family 向量，生成 `index.html`（完整叶/族选择）、`matrix.svg`（原叶矩阵）、`family_matrix.svg`（完整 family 矩阵）和 `manifest.json`。每个族有稳定 hash anchor 与对应 matrix/plan 索引，全部 37 行可查；manifest 把每个 cell 指到 family 索引及 group ID。支持/unknown 样式区分，显示 source axes、lifespan/coverage/residual，无硬边界。representative 图片是附加浏览材料，不能替代全量索引。
- [ ] 测所有输出 JSON 可解析、所有声明 SVG/XML 可解析、所有矩阵单元与 package 数值/状态一一相等、所有 family/leaf plan 索引都存在、每个视图保留全部 scope 几何（含孔洞/原 plane-local 坐标）、输入前后哈希不变，None 与零显示不同；rational pairs 不经 JavaScript 浮点还原拓扑。测试 renderer 在生成的临时真实 replay 上工作，不依赖尚未手动生成的固定新目录。
- [ ] Run：`pixi run pytest test/test_group_field_hierarchy_ifc.py test/test_group_axis_potential_preview.py -q`。通过后执行下面真实 retained replay 与现有 renderer 命令（新 runner 创建前不能执行）：

```powershell
pixi run python -m scripts.design.group_level.run_group_field_hierarchy_ifc --retained-run outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z --output-root outputs/design/group_axis_field_hierarchy_ifc/replay_v1
pixi run python -m scripts.design.group_level.render_group_axis_potential_preview --replay outputs/design/group_axis_field_hierarchy_ifc/replay_v1 --output-root outputs/design/group_axis_field_hierarchy_preview
```

- [ ] 核对本次返回的 preview 目录/manifest，抽看总览、小族、重叠族与 top 的同源 plan；程序完整性检查覆盖全部索引。记录首次失败与修复、耗时/输出规模、实际 uncovered cases；不可用输出不伪装 fresh。重复 replay 用新且明确命名的 output-root，绝不覆盖旧证据。提交 .16.3 证据给 owner，图面解释性由 Task 4 裁定。

## Task 4 / .16.4：Documentation and owner acceptance

**Files:** 主计划、当前 spec、`docs/project/group-evidence-design-index.md`、`docs/project/group-field-merge-decision-note.md`、`docs/software-architecture.md`、`docs/indoor_layout_evaluation_matrix_architecture_memory.md`；实施后新增 `docs/project/evidence/group-axis-field-hierarchy-v1.md`。

- [ ] 记录 Task 1–3 实际命令/结果、run/manifest 路径、输入指纹、全量计数和状态覆盖，更新本计划步骤与主 .16 checklist；测试失败或 namespace/数据缺失时保持依赖任务未勾选并记录 blocker。
- [ ] 对照 frozen spec §1–10 核对实现、输入保留与全部可视化；架构 map 只写实际新增普通 helper、factory seam 和 runner，不宣称 live UI/新执行框架。保留旧决策笔记与历史失败记录，现行规则指向 frozen spec。
- [ ] 向 owner 提供完整矩阵/索引与代表 plan，说明 `<90°` 只表达方向带、空间分离平行组织不能区分、n_eff 非独立样本数、未发生的真实状态仍 uncovered。owner 审阅通过才勾选 .16.4 和总体 .16；否则记录具体异议并只修对应范围。
- [ ] 最终执行范围不含真实家具旋转/undo、live UI/browser 交互、metadata edit counters、其他分析平面、千组规模或现实归属校准；不得由独立 freshness 合约比较推导这些验收已通过。Frame/其他包的下一步须 owner 另行安排。

## 计划自检与执行记录

文档自检覆盖：spec §2–6 → Task 1；§7–8 → Task 2；§9 → Task 3；§1/10、覆盖限制与状态同步 → Task 4。接口均在本计划明确声明或来自现有源码；新 helper/runner/test 路径已标未实现，现有命令使用 Pixi/pytest，不含版本写入或新增依赖。无实际 hierarchy 测试/IFC 命令在计划编写期运行。

**2026-11-01 文档交接：**owner 已冻结 .14；.15 计划自检已完成，主计划已记录 .14/.15 完成及其文档证据。所有 Task 1–4 与主 .16 执行项仍未勾选，下一项 .16.1。执行者在每次开始、推进、完成或阻塞时追加实际证据，不能把本段计划自检当作实现验证。
