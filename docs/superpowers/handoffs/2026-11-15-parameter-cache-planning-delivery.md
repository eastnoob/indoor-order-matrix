# 参数与模型旁缓存：规划交付及 jj 推进记录

日期：2026-11-15。范围：Spec 与 Plan A/B/C；产品功能尚未实施。

## 唯一交付工作线

- 工作区：`parameter-cache-notes`。
- 绝对路径：`D:/PROJECTS/understandOtherPackage/order_analyzer/.worktrees/parameter-cache-notes`。
- 原始 Spec 检查点：`9456173b`，父提交 `5baf3273`。
- 最初 Plan A 文档检查点：`8449f67c`。后续修订以本记录和最终规划 bookmark 为准。
- 最终 Spec 与 A 修订检查点：`961c84f5`；B 文档检查点：`6d24695f`。这两个提交仍只包含规划文档。
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
2. **A 的验收**：依次执行其可独立验证的任务；不同 agent 运行 focused checks，取得 specification/quality verdict 后由 root 提交。真实的 `plan-a-accepted.md` 记录最终实现提交、候选文件 hash、命令结果、兼容性限制与 B 入口。
3. **B 的起点**：A handoff 中的实际验收实现提交，保留 A 参数 API。验证模型移动、所有 UI/CLI run-local 目录、旧 hash 兼容映射、HMAC 多域、锁、索引重建与精确删除。真实的 `plan-b-accepted.md` 记录同等证据。
4. **C 的起点**：B handoff 中的实际验收实现提交。先 Brainstorm/Grill 实际产物；结果可以是继续 C、先执行小型修补计划，或明确安全拆分尚不可行。没有真实中间产物需求就只交长期设计，不增加运行时框架。
5. **阶段完成**：架构图、讨论笔记和 handoff 与实际代码同步；计划勾选不能替代测试或独立验收。每个任务只记录真实跑过的检查，不声称整个仓库或真实 IFC 重算已经验证。

实现期间由 root 在阶段验收后建立 `codex/parameter-cache-a-accepted`、`codex/parameter-cache-b-accepted` 等 bookmark；存在未通过的检查时不得创建或前移这些验收 bookmark。

## 检查点与恢复

已核查安装的 `jj commit`、`jj workspace add`、`jj restore` 和 bookmark 命令。`jj commit -m` 会提交当前变更并创建下一空变更；不要先 `jj new` 再把空变更描述成已完成实现。

只读检查用 `jj --ignore-working-copy`，并额外读取真实文件/hash，因为只读历史可能没有尚未 snapshot 的编辑。每个任务开始记录 workspace、父提交、change ID、真实 dirty 文件清单和允许修改的路径。提交前暂停写入者，冻结并复核测试对应的文件 hash。

推荐恢复路径是保留失败候选，再从最后一个已验收 gate 建一个新的 task workspace。既不丢失诊断材料，也不改动其他工作区。只有确认路径完全属于本任务且不存在混合编辑时，才按已核查的 `jj restore --from` 语法恢复明确文件。`jj op log` 用于诊断；不对共享仓库执行全局 undo/op restore，也不删除或清空 owner。

缓存迁移同样可回退：旧目录始终保留；目标冲突或部分失败不覆盖已有有效项。完成验证前不删除旧目录。暂存失败不能成为命中；不可验证的 checkpoint 只能作为历史，不能直接恢复计算。

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

## 本轮验证边界

最终冻结候选已经由 root 和独立 `planning_coverage` reviewer 复核，规划 **SPEC PASS / QUALITY PASS**，无剩余实质阻断。A 另由 `plan_b_map` 独立交叉核查；B/C 的实际 caller、runtime/UI 与现有 fixture/test 路径也已检查。上述结论是规划验收，不是实现验收。

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
