# Group Axis-field Hierarchy Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Delegation requires the existing owner/user route; this document does not independently authorize agents or version writes.

**Goal:** 在现有 axis-potential 包中追加已冻结的圆周方向族，保留全部原叶与完整 scope 支持，并以指定真实 IFC 的 retained 数据交付完整可索引图面。

**Architecture:** 包内普通 helper 从原始 source-axis outputs 计算 exact angular topology 与 max-union family evidence。现有 factory 显式接收 namespace，`evaluate(source_envelopes)` 和 shared core 不变；原 renderer 复用同一份平面几何。

**Tech Stack:** Pixi / locked Python 3.12.13、标准库 `fractions.Fraction` / JSON / hashlib / XML、pytest；不新增依赖。

**Spec:** [Owner-reviewed frozen design](../specs/2026-11-01-group-axis-field-hierarchy-design.md)。**状态：.16.1-.16.4 和总体 .16 已完成；2026-11-01 owner 在最终 independent audit 无 blocker 后接受 frozen axis-only 结果。**当前 replay 为 `outputs/design/group_axis_field_hierarchy_ifc/replay_v2/`，preview 为 `outputs/design/group_axis_field_hierarchy_preview/run_20261101T101331Z/`；v1/旧 preview 与早先失败保留为历史。主状态见[阶段 2B.6a.16](2026-10-26-group-attribution-evidence-field-implementation.md)及[证据记录](../../project/evidence/group-axis-field-hierarchy-v1.md)。这是 owner 接受，不是 user-reviewed、browser/live UI 或现实 cluster validity 接受；本 slice 在文档交接后停止。

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

下列 .16.1-.16.3 helper/factory/runner/renderer 路径均已实现；表中 Create/Modify 保留原计划动作。最终 frozen-contract 和精确整数显示修复由实现工作完成，本次仅同步既有结果，不改代码或测试。

| 文件 | 职责 / 接口 |
| --- | --- |
| Create `features/group_field_hierarchy.py` | 普通函数 `build_axis_field_hierarchy(source_envelopes: tuple[FieldResultEnvelope, ...], source_axis_outputs: tuple[EvidenceOutputChannel, ...], *, scene_namespace: str) -> tuple[EvidenceOutputChannel, ...]`；只依赖标准库和 field_core，消费传入的原叶 records/真实 refs，不反向 import potential 模块 |
| Modify `features/group_axis_potential_field.py` | 现有 `build_group_axis_potential_package(*, scene_namespace: str | None = None) -> EvidencePackage`；None 保持旧模式，非空 namespace 冻结闭包启用追加输出，空值拒绝；原 `_source_axis_field_outputs` 只计算一次 |
| Modify `scripts/design/group_level/run_group_axis_potential_ifc.py` | 现有 `_package_contract(description, envelopes, query, plane, source_sha256, artifact_paths, result, *, scene_namespace=None)` 增可选声明，None 保持旧 contract；扩展模式从实际 result 版本与 namespace/recipe 建 contract |
| Create `scripts/design/group_level/run_group_field_hierarchy_ifc.py` | `run(retained_run: Path, output_root: Path) -> Path`；CLI `--retained-run`、`--output-root`，后者为新结果目录、已存在则拒绝覆盖；不加载 IFC |
| Modify `scripts/design/group_level/render_group_axis_potential_preview.py` | 保持 `load_preview(replay: Path)` / `run(replay: Path, output: Path) -> Path` 与原 CLI；有 hierarchy 文件时追加 family 索引/矩阵/同平面视图，旧输入行为不变 |
| Create `test/test_group_field_hierarchy.py`, `test/test_group_field_hierarchy_ifc.py` | 前者逻辑/retained package 检查，后者新 runner 与 indexed-view 完整性 |
| Modify `test/test_group_axis_potential_field.py`, `test/test_group_axis_potential_preview.py` | 前者使用已有 `_retained_envelopes` 加 legacy preservation/namespace 检查；后者扩展 retained hierarchy 渲染检查 |
| Update 主计划、spec、index、architecture、memory、merge note | 实施进度与最终 owner 接受已同步；证据记录 `docs/project/evidence/group-axis-field-hierarchy-v1.md` 现以 v2 为 current acceptance，保留历史 v1 |

`FieldResultEnvelope`、`EvidenceOutputChannel`、`EvidenceChannelReference`、`EvidenceOutputScale`、`EvidencePackageOutput` 均来自现有 `features.field_core`。不引入自定义包输出容器；helper 的内部字典记录仅为包内计算。

## 总 checklist

- [x] Task 1 / .16.1：hierarchy helper 与公式/retained 检查通过。
- [x] Task 2 / .16.2：potential package、namespace、lineage 与独立 freshness 检查通过。
- [x] Task 3 / .16.3：指定 retained replay、完整索引矩阵/平面/manifest 交付通过；证据见下方 Task 3 execution record。
- [x] Task 4 / .16.4：最终文档/覆盖记录同步；owner 已接受 v2、离线图面及无 blocker 的 independent audit，授权完成总体 .16。

## Task 1 / .16.1：Hierarchy logic

**Files:** Create `features/group_field_hierarchy.py`、`test/test_group_field_hierarchy.py`。

**Consumes/produces:** 使用上表 helper 签名。传入同次 `_source_axis_field_outputs` 记录中的 `axis_field_support`、`non_self_profile`、`soft_view_direction` 或 `source_axis_scope_diagnostics`；由原 envelope 取得真实 query、target 和可引用的 overall-axis 渠道。返回 spec §7 的八类具名输出，不返回新容器或改写输入。

- [x] 写 retained-data tests：从真实 trend envelopes 通过 `_load_envelope` 还原，并验证 axis replay manifest 的 IFC SHA-256 与顶层 project ID；未造替代布局 fixture。
- [x] 测 exact `Fraction.from_float` unwrap、方向类/连续窗口族、事件整数对、输入倒序确定性、max-union `J`、full/non-anchor profile 域、support mass/`n_eff`、residual 与只读 Q；真实 retained scope 产生 703 families。
- [x] 纯代数补 exact unwrap 舍入反例；场景覆盖仅使用 retained 数据，未修改真实值补分支。例如：

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

- [x] Implemented the minimal helper with exact topology/events, max-union bounds, profiles, relations, residuals, direction diagnostics, explanations, and existing seven statuses.
- [x] Run GREEN: `PYTHONPATH='.'; pixi run pytest test/test_group_field_hierarchy.py -q` → 6 passed; lineage points to retained `overall_group_axis` channels and source identities remain preserved.

**检查口径：**missing/invalid/全零等新状态逻辑可以用数学/结构不变量验证；不可通过修改真实 envelope 数值生成“新的真实 IFC 覆盖”。精确同角类只保证 support-function redundancy，不合并 self/provenance。已知支持和浮点代数用 pytest.approx；topology/events 用精确相等。

## Task 2 / .16.2：Package / namespace / freshness integration

**Files:** Modify `features/group_axis_potential_field.py`、`scripts/design/group_level/run_group_axis_potential_ifc.py`、`test/test_group_axis_potential_field.py`；追加新逻辑检查至 `test/test_group_field_hierarchy.py`。`features/field_core.py` 不改。

- [x] Retained-data tests cover legacy preservation and the namespace factory using `ifc-project:2uGd6yom9GZe5$z7LfbGW0`:

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

- [x] Existing aggregate remains the legacy path; hierarchy mode reuses the same source-axis tuple once per evaluation, uses `axis-with-hierarchy-v1` / `group-axis-field-hierarchy-output/v1`, and leaves `field_core.py` unchanged.
- [x] `_package_contract(..., scene_namespace=...)` hashes namespace, hierarchy recipe/version, exact numeric policy, source IFC hash, retained result identities, and the stable scope/output target union; `None` preserves the legacy contract.
- [x] Independent subset/full contracts use `evaluate_evidence_package_freshness`; subset→full is stale with union `affected_targets`, and rebuilt full→full is fresh.
- [x] Namespace empty-string rejection, function-version identity, retained source lineage, all 4,112 legacy outputs, and semantic query revision retention are covered; metadata edit counters/live UI remain out of scope.
- [x] Run: `PYTHONPATH='.'; pixi run pytest test/test_group_field_hierarchy.py test/test_group_axis_potential_field.py test/test_group_axis_relation_diagnostic.py test/test_evidence_package_output.py test/test_evidence_package_freshness.py -q` → 52 passed in 39.76s.

## Task 3 / .16.3：Retained IFC replay and complete indexed visualization

**当前接受版本：**`replay_v2` / `run_20261101T101331Z`，最终验证与 owner GO 见下方 `.16.4 final acceptance record`。本节的 v1 命令、旧目录、大小与 4-test 结果保留为历史执行证据，不代表最终修复后重跑了旧组合。

**Files:** Create `scripts/design/group_level/run_group_field_hierarchy_ifc.py`、`test/test_group_field_hierarchy_ifc.py`；Modify `scripts/design/group_level/render_group_axis_potential_preview.py`、`test/test_group_axis_potential_preview.py`。

- [x] runner integration tests consume the **axis replay** `outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z`, verify source/source_after SHA-256, top-level `project_global_id`, plane/frame/scope, retained description/source reuse and source file hashes, and load the original envelopes/matrix/package output. Reuses `_load_envelope` and the existing factory; no IFC extraction or geometry reread. The first package-status attempt exposed a metadata dict incorrectly treated as a path; the runner now checks only string and string-list artifact refs.
- [x] Runner rejects an existing output root, preserves retained `source_manifest.json`, `description.json`, and `envelopes.json` bytes, and writes all 18 specified artifacts. Full counts: 37 leaves, 1,369 leaf cells, 4,112 legacy outputs retained, 34,268 total outputs, 703 families, 26,011 family cells, 1,332 residual edges, and 668 exact event pairs. `package_status.recompute_required=false`.
- [x] Report and manifests include the pinned SHA-256 `1c97e93d5c6f6e2f2430816aca2d2f72bb44fed1ac98afa3aed567ae905cc077`, top-level project ID `2uGd6yom9GZe5$z7LfbGW0`, `ifc-world-plan`, namespace `ifc-project:2uGd6yom9GZe5$z7LfbGW0`, all 51 retained-run file hashes, observed statuses, uncovered scenarios, and an all-output target index. No IFC extraction, synthetic input, real-world cluster validity, or live UI is claimed.
- [x] Renderer preserves the old five-input preview behavior. Hierarchy mode emits `index.html`, the 1,369-cell `matrix.svg`, the 26,011-cell `family_matrix.svg`, and `manifest.json`; all 37 leaves and 703 families have stable indexed links, and the 34,268 package targets map to HTML views. Family plan views reuse the same retained geometry and plane. Unknown values remain `NA`/gray, separate from zero.
- [x] Focused verification: `$env:PYTHONPATH='.'; pixi run pytest test/test_group_field_hierarchy_ifc.py test/test_group_axis_potential_preview.py -q` → 4 passed in 134.59s. Tests cover legacy preservation, overwrite refusal, complete cells/indexes, retained-source immutability, and preview rendering.
- [x] Run the exact retained replay and renderer commands below. Outputs: `outputs/design/group_axis_field_hierarchy_ifc/replay_v1/` (1,495,656,871 bytes) and `outputs/design/group_axis_field_hierarchy_preview/run_20261101T010221Z/` (178,597,195 bytes); no existing root was overwritten.

```powershell
pixi run python -m scripts.design.group_level.run_group_field_hierarchy_ifc --retained-run outputs/design/group_axis_potential_ifc_replay/run_20261031T142448Z --output-root outputs/design/group_axis_field_hierarchy_ifc/replay_v1
pixi run python -m scripts.design.group_level.render_group_axis_potential_preview --replay outputs/design/group_axis_field_hierarchy_ifc/replay_v1 --output-root outputs/design/group_axis_field_hierarchy_preview
```

- [x] Checked the returned preview directory and manifest. UTF-8 inspection confirmed the family selector and all 703 family IDs; leaf/family SVGs parse, matrix counts are 1,369 and 26,011, all 34,268 target entries resolve to indexed HTML views, and preview input/artifact hash failures are zero. `view_image` inspection of `representative_2.png` and `matrix.png` confirmed the retained plan rendering, anchor outline and fixed support scale. The first HTML inspection used the Windows GBK default and failed to decode; rerunning with `read_text(encoding='utf-8')` passed. Current retained run observed only computed states; singleton/two-anchor variants, missing/invalid axes, zero clarity, cancellation, exact event ties and other planes remain uncovered. Visual interpretation and owner acceptance remain Task .16.4.

## Task 4 / .16.4：Documentation and owner acceptance

**Files:** 主计划、当前 spec、`docs/project/group-evidence-design-index.md`、`docs/project/group-field-merge-decision-note.md`、`docs/software-architecture.md`、`docs/indoor_layout_evaluation_matrix_architecture_memory.md`；实施后新增 `docs/project/evidence/group-axis-field-hierarchy-v1.md`。

- [x] 复用 Task 1–3 与最终修复/审阅已有证据，更新 [hierarchy 证据记录](../../project/evidence/group-axis-field-hierarchy-v1.md)、主计划、spec、index、merge note、architecture 与 memory；本次只做文档链接/编码/状态检查，不重复数值检查、测试或回放。
- [x] 按 frozen spec §1–10 同步最终 helper/factory/runner 与输入保留证据；canonical admission/status、anchor contribution、profile/residual summary/actual refs 和 browser exact-string 修复完成。保留旧规则/失败记录；current replay/preview 为 v2，owner 已检查最终 report/status/metadata/code/test changes。
- [x] owner 已查看完整索引/矩阵证据和小族、重叠不可比较 top families 三张离线 PNG，接受 `<90°` 方向带、全 37 行而非硬成员、n_eff 非独立样本数与 narrow scale lifespan 非 robustness 的解释；最终 independent audit 无 blocker，owner 于 2026-11-01 明确 GO，授权勾选 .16.4 和总体 .16。browser/live UI 与现实 cluster validity 不在此接受范围。
- [x] 文档明确本轮未验证真实家具旋转/undo、live UI/browser 交互、metadata edit counters、其他分析平面、千组规模、现实归属校准或跨包融合；独立 freshness 比较不代表这些验收通过，Frame/其他包须 owner 另行安排。

## 计划自检与执行记录

**计划编写时历史自检：**spec §2–6 → Task 1；§7–8 → Task 2；§9 → Task 3；§1/10、覆盖限制与状态同步 → Task 4。接口均在本计划明确声明或来自当时源码；新 helper/runner/test 路径在编写时标为未实现。计划编写期未运行 hierarchy 测试/IFC 命令；后续实际实现与命令见 execution records，不含新增依赖。

**2026-11-01 文档交接：**owner 已冻结 .14；.15 计划自检已完成，主计划已记录 .14/.15 完成及其文档证据。

**2026-11-01 .16.1/.16.2 execution record:** Implemented `features/group_field_hierarchy.py`, additive namespace mode in `build_group_axis_potential_package`, and hierarchy-aware `_package_contract`. The retained real source produced 703 families and 30,156 additive hierarchy outputs; legacy mode remains 4,112 outputs. Focused tests passed: `PYTHONPATH='.'; pixi run pytest test/test_group_field_hierarchy.py -q` → 6 passed; the full .16.1/.16.2 regression command → 52 passed. `.16.3` and `.16.4` remain unchecked.

**2026-11-01 .16.3 execution record:** Added the retained replay runner and hierarchy preview mode. Focused command `$env:PYTHONPATH='.'; pixi run pytest test/test_group_field_hierarchy_ifc.py test/test_group_axis_potential_preview.py -q` → 4 passed in 134.59s. The exact replay CLI wrote `outputs/design/group_axis_field_hierarchy_ifc/replay_v1/`; the exact renderer CLI wrote `outputs/design/group_axis_field_hierarchy_preview/run_20261101T010221Z/`. Verified 37 leaves/1,369 leaf cells, 4,112 legacy outputs preserved, 34,268 total indexed outputs, 703 families/26,011 family cells, 1,332 residual edges, 668 exact event pairs, pinned source SHA-256, top-level project GlobalId, `ifc-world-plan`, 51 retained input hashes, `package_status.recompute_required=false`, valid SVGs, and zero preview input/artifact hash mismatches. UTF-8 HTML check found all 703 family IDs and the complete selector; inspected representative plan and leaf matrix PNGs. Outputs occupy 1,495,656,871 bytes and 178,597,195 bytes respectively. First runner status check failed because hierarchy metadata was treated as a file path; fixed by filtering to string/list-of-string references. One HTML inspection initially used Windows GBK and failed; explicit UTF-8 rerun passed. Only computed states occurred in this retained run; singleton/two-anchor shapes, missing/invalid axes, zero clarity, cancellation, exact event ties, and other planes remain uncovered. `.16.4` remains unchecked for owner review and visual interpretation.

**2026-11-01 .16.4 initial delegated documentation record (historical):** 已新增 hierarchy evidence 并同步 index、历史 merge note、architecture、memory、frozen spec 与两个计划；当时只复用 52 passed/4 passed 和 v1，未重跑测试/回放。acceptance review 发现 `JSON.parse` 显示大 rational numerators 舍入，后续又发现 frozen-contract direction/status/audit 输出遗漏；当时 `.16.4` 和总体 `.16` 保持未勾选。该 pending 状态及 v1/旧 preview 保留为历史，由下述最终接受记录 supersede。

**2026-11-01 .16.4 final acceptance record:** owner 最终 GO 已收到；独立 replay audit 无剩余 blocker。当前 replay `outputs/design/group_axis_field_hierarchy_ifc/replay_v2/`，preview `outputs/design/group_axis_field_hierarchy_preview/run_20261101T101331Z/`。固定 IFC SHA-256/project/plane 未变；37 leaves/1,369 leaf cells/4,112 legacy outputs/703 families/26,011 family cells/1,332 residual edges/668 exact events/34,268 targets 不变，package `fresh`、`recompute_required=false`；无新 IFC extraction 或 synthetic input。107 retained files 未变、17 artifact hashes 与 14 input hashes 匹配、完整索引通过；browser rational pairs 为 exact decimal strings，原 machine integer pairs 保留。

最终修复覆盖 no-axis/zero-mass unavailable、canonical modulo endpoint、valid descriptor admission、anchor contribution mass/fraction/positive-contributor `anchor_only`、profile leaf-cell coverage/status counts、residual known mass/mean 和 actual original cell target refs。helper check 8 passed/42.33s；summary/ref 最后修改后的 targeted invariant test 1 passed、7 deselected/22.40s，覆盖完整实际 DAG/lifespans、J/max、parent monotonicity、P\F residual、mass/n_eff/refs；renderer tests 3 passed/35.72s，含 exact strings、hierarchy README、optional sample absence。compilation/exact replay/renderer CLI exit 0。独立 audit 检查 314,167 actual source refs 和 1,332 residual summaries，retained S/J/topology 等于 v1；旧 52/4 命令只作历史范围证据，未由本次文档更新重跑。

owner 亲自检查最终 report/status/metadata/code/test changes 及 `family_representative_small.png`、`family_representative_overlap_top_a.png`、`family_representative_overlap_top_b.png`：H204 两个 G10/G12 anchors 仍有 37 support rows；H159/H174 为不可比较的重叠 top families，共享 27 refs，G06 为 0.227040/0.592176；H174 仅在 `[89.9999974008°,90°)` 存在，不称 robustness。三图同一 37-group geometry/0..1 color scale/orange anchors 已接受。实际 singleton subset 已测，但原 37-group 全场未观察到 singleton、missing/invalid、zero、cancellation、ties 或其他 planes。browser file-URL policy 阻止 local HTML，未绕过，browser/live UI 未接受。最终 `.16.4`、Task 4 全部子项与总体 `.16` 完成，仅为 owner frozen axis-only 接受；不扩大为用户审阅/现实 cluster validity，不启动 Frame/geometry/fusion。本次仅更新原 8 docs，复用证据，不运行新 code/tests/replay/review/version operations。
