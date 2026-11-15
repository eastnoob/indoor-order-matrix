# 参数与模型旁缓存：规划交付及 jj 推进记录

日期：2026-11-15。范围：Spec 与 Plan A/B/C；产品功能尚未实施。
验收与 jj 复审：2026-11-16；修订沿用原规划文件名。

## 唯一交付工作线

- 工作区：`parameter-cache-notes`。
- 绝对路径：`D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-notes`。
- 原始 Spec 检查点：`9456173b`，父提交 `5baf3273`。
- 最初 Plan A 文档检查点：`8449f67c`。后续修订以本记录和最终规划 bookmark 为准。
- 最终 Spec 与 A 修订检查点：`961c84f5`；B 文档检查点：`6d24695f`。这两个提交仍只包含规划文档。
- 本次验收严密性审查之前的规划交付：`b66bf3cfd365f236ea65157b7e6dd1f8b42911de`；保留在祖先链，审查修订另作非空文档提交。
- 最终规划 bookmark：`codex/parameter-cache-planning-20261115`，只指向经过审查的文档交付提交。
- 版本写入者：root。委派者可以写被明确分配的文档；不得修改 jj 历史。
- owner 工作区和其他项目工作线不纳入本轮修改；没有 push、merge 或 owner 集成。

三份计划是后续实现的输入，不能作为“实现验收提交”。不创建虚假的 A/B 实现 handoff 来让下一阶段过闸。

| 文档 | 当前交付 |
| --- | --- |
| [Spec](../specs/2026-11-15-parameter-owned-sidecar-cache-design.md) | 所有权、身份、缓存布局、兼容性与验收条件 |
| [Plan A](../plans/2026-11-15-package-owned-parameters.md) | 参数声明/默认/类型校验、完整快照、计算投影、历史状态传播与 checkpoint 前置保护 |
| [Plan B](../plans/2026-11-15-model-side-cache-store-migration.md) | sidecar、认证、原子发布、锁、迁移、版本管理、全部运行目录接线 |
| [Plan C](../plans/2026-11-15-output-port-and-intermediate-cache.md) | 从实际 A/B 重新 Grill、输出独立性、受限旧结果投影、长期中间产物设计 |
| [讨论笔记](../../project/parameter-and-cache-ownership-note.md) | 用户共识与规划阶段的修订结论 |

## 执行前后如何衔接

1. **A 的起点**：最终规划 bookmark。创建新的 task-owned jj workspace；先固定小型真实旧 receipt、原始 payload hash、实现/backend hash 清单，再改动它们所依赖的代码。不得以本轮未验收草稿代替 A。
2. **A 的验收**：依次执行其可独立验证的任务；不同 agent 运行 focused checks，取得 specification/quality verdict 后由 root 提交。真实的 `plan-a-accepted.md` 记录最终实现提交、候选文件 hash、命令结果、兼容性限制与 B 入口；后续交接提交包含这份记录和原样被测代码。
3. **B 的起点**：A 的已验收交接提交（包含记录中那份实际验收实现），保留 A 参数 API。验证模型移动、所有 UI/CLI run-local 目录、旧 hash 兼容映射、HMAC 多域、锁、索引重建与精确删除。真实的 `plan-b-accepted.md` 记录同等证据。
4. **C 的起点**：B 的已验收交接提交（包含记录中那份实际验收实现）。先 Brainstorm/Grill 实际产物；结果可以是继续 C、先执行小型修补计划，或明确安全拆分尚不可行。没有真实中间产物需求就只交长期设计，不增加运行时框架。
5. **阶段完成**：架构图、讨论笔记和 handoff 与实际代码同步；计划勾选不能替代测试或独立验收。每个任务只记录真实跑过的检查，不声称整个仓库或真实 IFC 重算已经验证。

实现期间由 root 在阶段验收后建立 `codex/parameter-cache-a-accepted`、`codex/parameter-cache-b-accepted` 等 bookmark；存在未通过的检查时不得创建或前移这些验收 bookmark。

## 共同验收协议

本节约束 Spec、A/B/C 的所有 `Expected: PASS` 和提交步骤；局部示例不能降低本协议。只有需求、测试、真实证据和已验收字节能够逐项对应，阶段才可交接。

1. **先固定基线与必需测试**：每任务 brief 列出需求、关键 pytest node ID（含参数化分支）、fixture、命令、预期行为和证据位置。先在接受的父提交检查既有测试；新增测试必须因目标行为缺失而 RED，不能把导入错误当作数值/缓存行为已被证明。阶段验收前用相同测试路径 `--collect-only -q` 核实必需节点确实收集；检查 pytest 配置、`PYTEST_ADDOPTS` 和实际命令，禁止无记录的 `-k`/`-m` 排除。
2. **通过必须可核验**：独立 verifier 使用计划的完整 focused set，加 `-ra --junitxml=<本任务证据目录中的文件>`，保留终端输出和 XML，记录命令、cwd、Pixi/Python、退出码、collected/passed/failed/error/skipped/xfail/xpass/deselected、耗时及 fixture/候选 SHA256。关键节点必须实际 PASS；skip、xfail、xpass、未收集或缺 fixture 都不能算通过。pytest 退出码 0 或总通过数不能替代逐节点对照。项目 conftest 会切回当前 checkout 根，必须核实导入的模块和 fixture 确实来自该 jj workspace。
3. **基线失败不能洗掉**：记录父提交同一命令的具体失败节点、原因和相关字节。不随便移除失败用例；要修复目标范围内的回归。若无关失败确实只能保留，阶段记录为 `partial / blocked`，列出缺口；不得创建或前移 fully accepted bookmark。可以提交清楚标记的候选供修补，但下一阶段不能把它当 accepted parent。
4. **迁移按家族证明**：A preflight manifest 对 raw、processed、认证 free-space、Blender-wire 逐项固定原 reader、旧 key、输入、实现/backend 与文件 SHA；缺一种即缺该家族的迁移验收。B 必须用真实 pre-A 字节、新进程和独立当前输入证明零计算复用，不能只用新实现生成的缓存或同进程内存登记。缺失证据只能标历史/不支持，不能让 A/B 全范围交接为通过；需要调整承诺时先修订相应 scope/repair gate，并保留未完成需求。
5. **防止空断言**：版本变化须同时验证参数进入真实计算、数值/格点变化与实际调用次数；复用须验证原 key/ref/bytes 和零调用。用空 sidecar 或隔离的冷 miss 证明禁止计算的 sentinel 的确位于真实调用边界。并发从真实 runner 入口验证；删除前必须有真实可用版本、非空依赖和数值，`delete_exact` 返回 True；缺对象不准当删除成功。
6. **冻结后独立验收**：暂停全部写入者，保存允许路径的 diff、实际文件 SHA 和 fixture 清单；不同 agent 在这些字节上执行检查并给出 SPEC/QUALITY verdict。修补后重跑受影响检查并复审。root 提交前再次比对所有被测代码/测试/fixture/config 的 SHA；代码或测试变动使对应证据失效。只追加证据文档时确认不改变被测行为并另做文档检查，避免无限重跑。
7. **交接不自指**：先接受最后的非空实现提交，再在后续文档提交记录它的完整 commit ID、证据文件/hash、结论和下一阶段入口。handoff 的自身提交由外部 bookmark/log 标识，不把未知的自身 hash 写进自身。阶段 accepted bookmark 指向这个已检查的交接提交；B/C 记录它及其中的实现提交，核对祖先关系。C 若只完成安全拆分延期，结论必须是 `split deferred`，不能建立暗示独立输出已实现的 accepted bookmark。

这些证据优先保存在本任务模型旁的 run/evidence 目录；A/B 尚未接线时用明确的临时测试证据目录，并在 handoff 保存可继续访问的绝对路径和 hash。不得为验证更改缓存位置而重算大型模型。

## 检查点与恢复

已核查安装的 `jj commit`、`jj workspace add`、`jj restore` 和 bookmark 命令。`jj commit -m` 会提交当前变更并创建下一空变更；不要先 `jj new` 再把空变更描述成已完成实现。

只读检查用 `jj --ignore-working-copy`，并额外读取真实文件/hash，因为只读历史可能没有尚未 snapshot 的编辑。每个任务开始记录 workspace、父提交、change ID、真实 dirty 文件清单和允许修改的路径。提交前暂停写入者，冻结并复核测试对应的文件 hash。

推荐恢复路径是保留失败候选，再从最后一个已验收 gate 建一个新的 task workspace。既不丢失诊断材料，也不改动其他工作区。只有确认路径完全属于本任务且不存在混合编辑时，才按已核查的 `jj restore --from` 语法恢复明确文件。`jj op log` 用于诊断；不对共享仓库执行全局 undo/op restore，也不删除或清空 owner。

缓存迁移同样可回退：旧目录始终保留；目标冲突或部分失败不覆盖已有有效项。完成验证前不删除旧目录。暂存失败不能成为命中；不可验证的 checkpoint 只能作为历史，不能直接恢复计算。

### 阶段工作线与命令约束

| 阶段 | 新 jj workspace | 父提交 | 工作 bookmark / 验收 bookmark |
| --- | --- | --- | --- |
| A | `parameter-cache-a-implementation` | 本轮审查后最终规划提交的完整 ID | `codex/parameter-cache-a-work` / `codex/parameter-cache-a-accepted` |
| B | `parameter-cache-b-implementation` | 真实 A accepted handoff 提交的完整 ID | `codex/parameter-cache-b-work` / `codex/parameter-cache-b-accepted` |
| C | `parameter-cache-c-implementation` | 真实 B accepted handoff 提交的完整 ID | `codex/parameter-cache-c-work` / 完成输出拆分才设 `codex/parameter-cache-c-accepted` |

workspace 路径均在本记录的仓库 `.worktrees/` 下。先检查名称/路径不存在；不得复用 `parameter-cache-plan-a` 未验收草稿。bookmarks 是移动定位器，不是验收凭据：每个 brief 固定完整 `planning_commit_id`、`implementation_base_commit_id`、workspace/path、change ID、candidate 文件/hash、accepted implementation/handoff commit ID 和 root writer。已接受提交不 amend/rebase；修补另建子提交。B/C 从真实父提交继承，不能三阶段平行从规划提交各写实现。

以下只由 root 在 canonical planning workspace 执行；此时规划 bookmark 必须已包含本次审查修订。命令展示建 A 的方式，不在本轮文档审查执行：

```powershell
$planningCommit = (jj --ignore-working-copy log -r 'bookmarks(exact:"codex/parameter-cache-planning-20261115")' --no-graph -T 'commit_id').Trim()
if ($LASTEXITCODE -ne 0 -or $planningCommit -notmatch '^[0-9a-f]{40}$') { throw 'Planning commit is not unique' }
jj --ignore-working-copy workspace list
jj workspace add --name parameter-cache-a-implementation --revision $planningCommit 'D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-a-implementation'
```

创建后进入返回的明确路径，核 `jj --ignore-working-copy root`、`status`、`log -r '@ | @-'` 和实际文件/hash。B/C 的 `--revision` 使用已验证 handoff 的完整 ID，禁止默认 revision、猜测 `@-` 或随时变化的 bookmark。后续规划修订若未包含在该 accepted parent 中，只带入相应文档修订并记录来源；如改动已验收运行时契约，先走 repair gate，不能按工作区内过期计划继续。

任务中的 `jj commit -m ...` 是提交意图，必须由 root 增加该 task brief 的明确 filesets 后执行。所有只读 status/diff/log 带 `--ignore-working-copy`；仅 root 在暂停写入者后有意运行一次普通 `jj status` 来 snapshot，随即核对非空差异、允许路径和实测 SHA。裸 commit 会提交全部变更，禁止照抄；混入同文件的无关编辑先分离，不能用选择整个文件来偷偷带入。工作 bookmark 由 root 显式指向非空候选提交，不会因 `jj commit` 自动追踪新空 `@`；未验收候选只标 `candidate/draft`。

提交后从 log 读出完整实现/交接 ID，核 diff 与被测字节，再用带显式 `--revision` 的 `jj bookmark create`（首次）或 `jj bookmark set`（后续）更新验收 bookmark。不能默认指向新空 `@`。无失败或跳过、证据齐全且 SPEC/QUALITY 均通过才执行。

失败先保存 task-owned 文件、diff、SHA、诊断和非空 draft checkpoint（若含无关编辑则保留原工作区），再由 root 用最后 accepted 的完整 ID 创建 `parameter-cache-a-recovery-01` 等新工作区。命名文件恢复只允许 `jj restore --from <已记录的accepted完整ID> <确认独属本任务的明确路径>`，不省略路径。`jj op log` / `jj --at-op ...` 只作只读诊断；禁止共享仓库的 `jj undo`、`jj op restore`，也不依赖本机不存在的 `jj op undo`。

**Superpowers 的 jj 适配**：本机 canonical 的 `jj root` 是该工作区，但 `git rev-parse --show-toplevel` 返回 owner 根，Git HEAD 也不是此工作线。委派 brief 必须覆盖技能中的 Git worktree 检测、Git HEAD/review-package 脚本、implementer 自行 commit 和自动清理：使用 jj 的 base/candidate 完整 ID、`jj --ignore-working-copy diff --from ... --to ... --git` 与真实文件 SHA；只有 root 写历史。不得自动运行 `git clean`、`rm -rf`、workspace 删除、finishing merge/push；保留全部验收证据与草稿。

## 审查发现及修复归属

| 实质漏洞 | 已写入的修复要求 |
| --- | --- |
| 类型提示不执行校验；datum 可为 None 或 dict | A 的 runtime validation、nullable 与历史 value contract；不动态更换同一 schema 的类型 |
| source/GUI 标签或 warning 参数改变数值版本 | A 只 hash recompute-required 投影，完整值留审计 |
| 命中时用 current contract 自比，丢失历史值和 adoption | A 的 lookup 结果携带历史 contract/status；runner 传播 calculated/requested 与来源 |
| 旧 processed key 与 typed key 不同 | A 明确已知旧键/显式路径的采用边界，B 负责受限扫描迁移；禁止补当前默认值伪造历史 |
| 开放 CLI 净空后沿用 source_index-only checkpoint | A 先拒绝错绑定/未完成恢复，B 再迁移完整可恢复状态 |
| IFC 绝对路径和实现文件 hash 改变 key | B 的 verified SourceBinding、预重构 fixture、受限兼容 lookup binding；保留真实算法版本检查 |
| 多密钥目的地覆盖认证材料 | B 的 auth key ID、validator context 和并发 create-once |
| UI 仍写仓库 jobs 或 main 强传旧全局 cache | B 分离固定执行根和运行根，覆盖真实 worker/main/UI seam |
| 索引损坏、并发丢条目或多文件半发布 | B 的可重建索引、完整目录暂存发布、OS 释放锁和明确锁顺序 |
| 删除上游后篡改已认证下游 receipt | B 动态派生依赖状态；不改签名内容、不级联删除 |
| 只把 port 加入 key，processed/reader 仍绑定整个包 | C 同步投影参数、source、raw payload、processor 和读取校验 |
| 将 raw/processed 与语义输出混用 | C 独立 wrapper，旧 reference.port 和 v1 wire bytes 保持兼容 |
| cached snapshot 自证当前 schema 或当前输入 | C 的读取、processing 与 modulation 入口必须由调用方显式提供独立当前 contract 和 owner snapshot；无 typed schema 时显式传 None |
| 为将来需求添加无用户的中间件 | C 默认只做长期设计；实际阶段需重新接受具体用途 |

审查为基于实际代码的规划一致性评估，不等于执行正式 Spec Kit 命令或通过产品测试。可视化省略：本轮结论由代码、接口、路径、文本和版本证据决定。

## 需求到任务的覆盖

| 用户需求 | 验收入口 |
| --- | --- |
| 每包自主决定类型、默认值、暴露项；下游不能改上游 | A Tasks 1、3、5 的 owner schema、运行时校验和不可变性测试 |
| 相同有效计算值同版本；参数改回后复用 | A Tasks 1、4；B Task 4 的旧缓存与两版本迁移测试 |
| 容许 warning 复用并让用户看到差异 | A Tasks 2、4；C Task 4 的 calculated/requested 与 callback 哨兵测试 |
| 默认全部缓存和运行文件在模型旁 | B Tasks 1、3 的 locator、worker、UI、CLI 和临时到已保存路径测试 |
| 改目录优先复制，不重算；能列版本和删除一个 | B Tasks 2、4 的精确地址、call 哨兵、认证域、索引和不级联删除测试 |
| 输出之间没有虚假的依赖耦合 | C Tasks 2–6 同步投影输入、参数、payload、processor、reader 和删除依赖测试 |
| 中间产品容易管理且不提前建平台 | C Tasks 1、7 的真实需求审查与长期 receipt/payload 契约，默认无运行时接入 |
| 可回滚、安全连续推进 | 各计划的 jj gate；本记录的单一版本写入者、失败候选保留和实际 A/B handoff 要求 |

## 隔离的未验收草稿

一次委派误启动了实现，已停止；仅保留诊断，不属于 A/B/C 的交付或验收链。

- 工作区：`D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-plan-a`。
- 父规划提交：`8449f67c`。
- 误启动的首个实现提交：`a0c6f60e`。
- 保留剩余编辑的 WIP 提交：`f9194090`，bookmark `codex/unaccepted-parameter-cache-draft-20261115`。
- WIP 后的空工作副本：`0344f8ed`。没有将这些代码集成进 canonical notes 或 owner。
- 保留文件：`features/evidence_package_parameters.py`、`features/field_core.py`、`features/evidence_package_storage.py`、`test/test_evidence_package_parameters.py`、`test/test_evidence_package_processing.py`。
- 未对该草稿运行独立验收；不得将其名称中的 feature commit 当作已批准结果。

其他早期重复计划工作区 `parameter-owned-plan-a`、`model-side-cache-plan-b`、`output-port-plan-c` 也不是最终交付路径。保留它们的历史，不 cherry-pick 其实现或把其中的计划当成最新版本。

## 原规划交付的验证边界（b66bf3cf）

原规划冻结候选由 root 和独立 `planning_coverage` reviewer 复核，记录为规划 **SPEC PASS / QUALITY PASS**。A 另由 `plan_b_map` 独立交叉核查；B/C 的实际 caller、runtime/UI 与现有 fixture/test 路径也已检查。2026-11-16 的对抗复审发现下面的验收充分性缺口，因此上述历史结论不替代本次修订复核，更不代表实现验收。

检查环境为本记录的 canonical 工作区、Pixi Python。独立命令为 `pixi run python C:/Users/tianf/AppData/Local/Temp/parameter_cache_plan_check_20261115.py`，退出码 `0`：8 份文档、48 段 Python 示例，`errors=[]`。检查范围为 Markdown 本地链接、围栏、占位标记、空白、Python AST 和 JSON 示例语法；未导入或执行示例中的待实现模块。架构大文档的链接与标记审查限本轮新增条目，未声称全面清理历史文档。

冻结文件 SHA256 如下；本记录自身以最终规划提交为准，避免把自身 hash 写入自身。

| 文件 | SHA256 |
| --- | --- |
| Spec | `6ff547d294b5c96baddbc7c12fe561683523fe8bca2e2af85c3f1e313c8b9c33` |
| Plan A | `6c4bc0a0e8da71af0e8a5ce5c764d63e0f5bb09c73717b5ab7d263a519bc8787` |
| Plan B | `22fd109832cb0875db914df8824b39ea49566bfe69d5e9db20820aec89d47409` |
| Plan C | `1a2e847476c476a9a39d4fcd525ecfef8424715f5e31fcfe33ae604f894e5fe6` |
| 讨论笔记 | `c422ad120d802885fc7c92bfd7f1fe62dc24e7cd45c6cc7ab349ce281241d384` |
| software-architecture | `24fc74ad61804599139eeae7de51dae8decf05a2e792a093354e394b52100b2a` |
| architecture memory | `8cceac5a776889f8b825341646f74d24862fc3654f3262d70da0fece4cae8adf` |

最终本地交付检查使用 `jj --ignore-working-copy diff --from 5baf3273 --to <planning-bookmark> --summary`，确认只含这 8 份 Markdown；提交后核对 bookmark 指向、canonical 空工作副本和 owner 原有 revision。无 push、merge 或 owner 集成。

本轮没有实施 sidecar/CacheStore/新参数 API，没有迁移实际用户缓存，没有运行产品测试或重新计算模型；所有实现测试命令属于后续计划的验收步骤。已知不能验证或无法映射的旧缓存会安全 miss，并报告原因，不能保证任意历史 JSON 都无需重算。

## 2026-11-16 验收充分性复审

root 与只读 reviewer `audit_ab_acceptance`、`audit_c_acceptance`、`audit_jj_runbook` 对照实际 fixtures/callers 和安装的 jj 命令复审；问题与修订如下。它们是计划验收漏洞，不是已实现功能的缺陷报告。

| 原验收可能漏过的错误 | 修订后的必需证据 |
| --- | --- |
| 只改 key/snapshot，计算仍忽略新参数 | A processed callback 读取参数并改变结果；微小 free-space 的真实网格、样本数、两次计算和旧值禁算恢复 |
| Store 示例锁正确，真实 runner 在锁外重复计算 | B 普通包、认证 free-space、Blender 入口的 spawn 首 miss 调用计数 |
| importer 只在内存保存兼容 lookup 或认证域 | B P 迁移退出、Q 新进程真实 runner 禁算命中、重建索引后 R 再命中及冷 miss 阳性对照 |
| 缺失几何掩盖新 path 分支、路由 provenance 污染 Euclidean | C 有限真实路径与 combined 对照，禁共享 Euclidean 原语；真实有效 route-only 输入变更不改变 Euclidean bytes/key |
| 手动 projector 预填缓存掩盖 runner 未接入 adoption | C 只有 combined entry 时直接调用 runner，禁两个 producer 且保留历史 bytes/来源 |
| processor/modulation 偷用历史 owner 或忽略当前 recipe | C 各入口独立 current snapshot/schema/recipe 拒绝矩阵与 callback 哨兵；raw selected warning 单独验证 |
| 被删对象/边本来就不存在 | C 四种 fresh-store 删除案例，事前完整数值/边、delete=True、free-space 使真实 path 不可用的阳性对照 |
| pytest 总 PASS 掩盖 skip/缺 node/缺 fixture；提交后 bytes 漂移 | 共同协议的 collect、逐节点 outcome、日志/XML、冻结 SHA、独立验收和阶段交接 |
| Git 脚本读到 owner；全局恢复/裸 commit 伤及其他工作 | jj 专用工作线、root filesets、完整父提交、保留 draft 后新 workspace、禁全局 undo/自动清理 |

原 `b66bf3cf` 和隔离草稿都继续保留；本次仅修订这八份 Markdown。产品实现、真实缓存迁移、Blender/IFC 运行与迁移重启测试仍是后续执行的验收工作。

### 本次复核结论与证据

最终复核候选为 `f25920994bc008e41a0e5f094db4ceda4170eb53`。三位独立 reviewer 对各自 A/B、C、jj 分工均给出 **SPEC PASS / QUALITY PASS**，无剩余阻断；root 核对实际文件、输出与 diff 后，用明确的八份文件路径提交修订为 `4c48b07d3f67a790fd4e7a647fe2888236d705e2`。本小节是后续证据追加，其自身交付提交由最终规划 bookmark/log 标识。

独立 verifier `audit_ab_acceptance` 在 canonical 工作区通过 Pixi 执行原文档 validator，退出码 `0`，8 份文档、48 段 Python 示例、`errors=[]`。保留输出为 `C:/Users/tianf/AppData/Local/Temp/parameter_cache_plan_check_20261116_audit_ab_f2592099.jsonl`，SHA256 为 `d38b46cb2aa0b7f0f34db282ced8eff45dc65cd0975dd2fe1c2087d0a7df5b24`；root 已读取并核验。该检查只验证文档链接/围栏/示例语法等，不导入待实现模块，也不执行未来的产品验收测试。

下表是独立验收时的磁盘字节 SHA256。memory/architecture 在 checkout 为 CRLF、jj 存储为 LF，独立 reviewer 已核对规范化文本相同；其余六份复核文档磁盘与候选字节一致。本记录在候选时的 SHA 为 `ea1c67cde7a702a28a8aea3d0b86e9562850fd998a63d2caad1383b238d89081`，追加此小节后以交付提交为准。

| 文件 | SHA256 |
| --- | --- |
| Spec | `d044911e8dab8a72e593b0388da01a2823050dcb6c062b9ff86b0ef259de3469` |
| Plan A | `3d73d1d542207da48d176e7aa8714d0956a3b834b9e8828758333323bdaa8d70` |
| Plan B | `377b6a9fe5d314bf9ef9bb132e82f38ad28e1343fd4c5400a57814aea8906acb` |
| Plan C | `96bed9c2b17f3a0f8816b1c20be84c9fe140c7e8c2eed14a39034d7ced9cabb3` |
| 讨论笔记 | `9cbe3c92982b0d2c84f930866e3d472c47592b74b3f4aecee5af66665a18ecaf` |
| software-architecture | `8a6d90c63b564b4045ff99bad106b646c341746c09ba0fb00d7165d721de3590` |
| architecture memory | `fc4b71e767b195fd03fdd289edb79d0a05cf11f78395cbced480184e6f597a02` |

已验收内容仍为规划修订。没有产品代码修改、生产缓存复制/删除、大模型重算、Git 操作恢复或 owner 集成。是否满足未来运行时承诺，必须由 A/B/C 的实际执行证据判定。
