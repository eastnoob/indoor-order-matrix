# 证据包参数所有权与模型旁缓存设计笔记

日期：2026-11-15  
状态：设计共识记录，尚未实施迁移

## 1. 已确定的原则

每个证据包拥有自己的超参数。超参数应由该证据包的 typed config 声明，带默认值、边界校验和可序列化的参数摘要。用户可以在实例化、命令行或未来 GUI 中修改这些参数。

证据包之间通过不可变的结果引用（`ResultRef`）和结果 receipt 连接。下游证据包可以选择某个上游结果版本，但不能修改上游证据包的参数或已经保存的结果。若需要不同的上游参数，必须请求或生成另一个上游版本。

缓存的种类由语义输出决定，而不是由任意中间变量数量决定。一个输出可以有多个参数版本；版本由该输出真正依赖的输入、参数、算法版本和 schema 决定。

所有缓存、运行中的文件、checkpoint、日志和中间结果默认放在正在编辑的 IFC 或 Blender 模型旁边。缓存位置的选择不改变参数所有权或依赖关系。

## 2. 参数归属

| 参数 | 所属证据包 | 说明 |
| --- | --- | --- |
| 左、右、合计净空 | `group_distance` 的路线距离部分 | 路线可行性和路径距离规则；当前默认 CLI 值为 `0.225 / 0.225 / 0.55 m`。库 API 的 `None` 仍表示保留无净空约束的旧路径。 |
| 网格间距 | `free_space` | 决定自由空间采样分辨率和计算规模。 |
| height band、slab、analysis plane | `free_space` 查询请求 | slab 和平面可能来自场景捕获，但自由空间包保存并校验最终查询绑定。 |
| 几何容差、拓扑容差 | `free_space` | 当前参与自由空间计算，不能被下游距离包改写。 |
| distance modulation 开关 | `group_axis_potential` | 决定是否使用已有距离结果调制轴向势。 |
| `epsilon` | 使用它的 proximity processor | 当前是固定试验参数，暂不作为常用用户旋钮。 |

由完整 scope 计算得到的 `min`、`max`、`median`，以及 source fingerprint、算法版本、package identity 等属于派生或身份数据，不是用户超参数。局部搜索预算可以保留为高级诊断参数，不作为普通业务入口。

## 3. 当前实现状态

当前代码已经有参数进入 cache identity 的基础：

- `free_space`、`group_distance` 和 `group_axis_potential` 都接受 `cache_directory`；
- raw 结果通常保存为 `<cache_key>.json`；
- processed 结果保存为 `processed-<processed_key>.json`；
- 参数从 `1` 改为 `2` 会产生新的 identity，改回 `1` 理论上可以命中原版本。

当前仍有几个结构性缺口：

1. `group_distance` 的欧氏距离和路径距离仍放在同一个 package 中，当前失效范围是 `whole_package`；改变路径净空可能连带使欧氏结果重算。
2. 某些参数仍通过 `Any` 或普通 mapping 传递，没有统一的“暴露参数、默认值、影响级别”描述。
3. global source runner 仍直接写入净空值，未完全复用统一参数入口。
4. owner 工作线的旧 global checkpoint 缺少完整的输入和 policy 指纹保护；不同规则不能安全复用同一个旧 checkpoint 目录。

当前显式运行产物仍主要放在 `outputs/design/...` 的 run 目录中，例如 `input_bundle.json`、`observations.json`、`run_manifest.json` 和 `repair_result.json`。Blender 内容缓存目前有固定路径：

```text
outputs/blender_analysis/content_cache/v1/
```

这些路径属于当前实现或历史证据布局，不是最终的模型旁 sidecar 方案。

## 4. 目标的模型旁缓存布局

对于：

```text
apartment.ifc
```

默认缓存根目录为：

```text
apartment.order_analyzer/
```

Blender 文件同理：

```text
apartment.blend
apartment.order_analyzer/
```

建议的内部结构：

```text
apartment.order_analyzer/
  manifest.json
  index.json
  settings/<package-id>.json
  auth/<key-id>/.free_space_cache_key
  locks/
  quarantine/
  runs/<pending-capture-run-id>/
  sources/
    <source-fingerprint>/
      source.json
      outputs/
        <package-id>/<semantic-port>/<raw-or-processed>/<version-key>/
          receipt.json
          payload.json
      runs/
        <run-id>/
          logs/
          checkpoints/
          scratch/
```

`source-fingerprint` 应绑定 IFC、Blender 或 canonical scene capture 的内容，以及被分析的外部依赖文件。文件名和路径主要用于显示；实际复用身份使用内容和依赖指纹，因此模型改名或移动时，只要 sidecar 一起移动，缓存仍可识别。

参数版本变化不创建新的 source namespace。尚未完成捕获、无法确定内容身份的运行先放在 sidecar 根下的 `runs/`，完成后在运行记录中绑定来源；临时 run ID 不作为正式计算身份。

sidecar 的 `manifest.json` 还应记录缓存格式版本、源文件和外部依赖摘要、创建工具版本及迁移历史。路径、时间和当前选中版本属于展示或工作区状态，不进入计算 identity。

未保存的 Blender 场景没有稳定模型路径，可以先使用会话临时目录；模型保存后再迁移到旁边的 sidecar。模型目录无写权限时，应明确提示用户选择备用目录。

`outputs/design/...` 继续用于显式导出的证据、报告和历史 run，不与内部可复用缓存混用。

## 5. 输出口级缓存行为

目标缓存关系为：

```text
输出口
  └── 参数和输入版本
        └── 不可变 receipt
```

对于当前距离流程：

- `euclidean_distance` 不应依赖净空 policy 或路线 free-space 搜索；
- `path_distance` 应依赖 free-space ResultRef、净空 policy 和路线算法版本；
- `axis_potential` 依赖它实际使用的 distance raw/processed ResultRef 和自己的调制参数。

因此净空从 `1 m` 改为 `2 m` 再改回 `1 m` 时，路径输出应保存两个版本并恢复旧版本；欧氏输出应继续复用。输出之间若存在依赖，删除上游版本后，下游版本显示 `orphaned` 或 `unavailable`，默认不做隐式级联删除。

raw 和 processed 是同一语义输出的不同计算层，不应误认为两个独立业务输出口。processed identity 必须只绑定它真正使用的 raw channel。

## 6. 参数变化提示

每个证据包应为参数标记影响级别：

| 影响级别 | 行为 |
| --- | --- |
| `recompute_required` | 参数进入计算身份，改变版本并需要重新计算。 |
| `reuse_with_warning` | 可以复用旧数值，但界面必须提示当前参数与计算参数不同。 |
| `metadata_only` | 不影响计算身份，只改变展示或报告。 |

当前网格、height band、几何容差、拓扑容差和净空规则都属于 `recompute_required`。将来若需要“改变后不重跑”，应增加只影响报告解释的诊断容差，而不是从计算身份中删除真实计算容差。

## 7. 后续最小实现顺序

1. 为各证据包增加冻结的 typed config，并保留现有默认行为。
2. 让所有实际运行入口读取同一组包级参数；开放 global source runner 的可变净空前，先在 A 中补齐 checkpoint 的输入与 policy 绑定保护。
3. 为 package contract 增加参数暴露级别、单位、来源和影响级别。
4. 将 sidecar 路径解析为默认缓存位置，并保留显式 `cache_directory` 覆盖能力。
5. 明确输出口依赖边界，逐步拆开欧氏与路径结果的缓存 identity。
6. 增加版本列出、精确删除和 `1 → 2 → 1` 命中测试。
7. 在 B 中完善 checkpoint 的可验证迁移与恢复；缺少完整绑定的旧 checkpoint 只保留为历史。

暂不引入 SQLite，不先做完整参数平台或 GUI，也不先开放 `epsilon`。现有 JSON receipt、原子写入和目录索引足以支持第一阶段的版本管理。

## 8. 缓存目录变更时的迁移规则

缓存目录是存储位置，不是计算输入。用户把缓存从旧目录改到新目录时，只要输出身份、参数、上游引用、算法版本和 schema 没有变化，就不应因为路径变化重新计算。

迁移顺序应为：

1. 读取旧目录中的 receipt、索引、运行记录和可验证 checkpoint。
2. 校验 receipt 的 cache key、contract、内容指纹、签名或认证标签，以及它引用的上游结果是否仍可解析。
3. 将通过校验的 receipt 和 payload 复制为目标暂存目录中的完整一代，再原子发布整个结果目录，避免暴露只有部分文件的结果。
4. 在新目录重建或更新 `index.json`，记录原位置、目标位置、复制时间、校验结果和迁移状态。
5. 复制完成后，优先从新目录命中旧版本；只有目标版本不存在或校验失败时，才重新计算受影响的输出。

迁移不得修改计算 identity、版本 key、receipt 内容或上游 `ResultRef`。模型文件改名或移动时，只要模型内容 fingerprint 和 sidecar 一起保留，也不应触发重算。

raw、processed、运行日志和最终报告可以直接复制。checkpoint 只有在其输入、policy、上游结果引用、算法版本和 schema 指纹完全匹配时才可作为可恢复状态；无法验证的 checkpoint 可以保留为历史文件，但不能直接继续计算。

迁移应支持“部分成功”：某个输出口复制失败时，其他输出口仍然可以复用；失败的输出标记为 `migration_failed` 或 `unavailable`，不能把整个缓存目录视为无效。原目录在迁移完成并通过抽样读取校验前应保留，不自动删除。

因此，修改缓存目录的用户体验应是“搬运已有结果”，而不是“换目录后全部重跑”。未来 UI 可以显示每个输出版本的 `copied`、`reused`、`migration_failed` 或 `recompute_required` 状态。

## 9. Superpowers 自检查补充

### 9.1 参数信息不能只保存一个值字典

参数需要分成三层：

1. **包代码中的 typed schema**：参数名、类型、默认值、单位、合法范围、是否允许用户暴露、影响级别和 schema 版本。
2. **当前可编辑配置**：sidecar 中保存用户对各包的覆盖值，供下一次运行或 GUI 编辑。它不是历史结果的权威，也不直接决定旧缓存是否存在。
3. **不可变结果 receipt 中的 effective configuration**：保存补齐默认值、完成单位归一和校验后的完整参数快照，以及 `parameter_fingerprint` 和 `config_schema_version`。

receipt 还应记录每个参数的来源，例如 `default`、`user`、`cli` 或 `gui`，用于解释和审计；来源标签不进入计算 identity，同样的有效值不应因为入口不同而重算。计算 identity 只使用 canonical effective parameters 中的 `recompute_required` 投影、实际输入依赖、算法版本和 schema 版本。

归一化过程必须拒绝未知字段、缺失必填值、`bool` 冒充数字、`NaN`、无穷值和无法转换的单位；同一语义的参数只能有一种 canonical JSON 表示。现有 processed receipt 已保存 processor parameters 和 `processing_identity`，但这还不能替代所有证据包共享的参数快照格式。

需要同时区分：

- `calculated_parameters`：该历史结果实际使用的参数；
- `requested_parameters`：当前用户想使用的参数。

两者不同时，系统才能准确显示 `reuse_with_warning` 和 `exact_match=False`，不会声称当前请求参数就是历史计算参数。原有 freshness 映射继续描述计算输入是否有效；warning 和缓存来源单独呈现。默认值必须在 receipt 中具体展开，不能依赖运行时重新读取代码默认值；否则代码默认值改变后会产生无法解释的历史结果。

计算指纹只投影 `recompute_required` 参数；完整 effective snapshot、参数类型/单位/影响声明和来源仍保存在审计记录。`reuse_with_warning`、`metadata_only` 与来源标签不创建新的数值计算版本。

### 9.2 需要很薄的 Cache Store，而不是包语义中间件

当前 persistence 分散在普通 evidence JSON receipt、free-space 自有认证 receipt 和 Blender wire cache 三套实现中。可以引入一个很薄的 `CacheStore` / cache middleware，统一处理：

- sidecar 路径解析；
- receipt 的原子读写和完整性校验入口；
- 每个 identity 的锁，避免 GUI 多开或并发运行重复计算；
- `list`、精确 `delete`、`copy/migrate` 和 index 重建；
- incomplete、损坏或无法验证文件的 quarantine。

这个层不拥有证据包的语义、参数或算法。每个包仍然负责自己的 contract、identity、序列化和验证。middleware 只保存包交给它的 receipt 和 payload。

建议 receipt 的公共外壳至少包含：

```json
{
  "schema": "cache-receipt/v1",
  "package_id": "group_distance",
  "output_port": "path_distance",
  "identity": "...",
  "contract": {
    "effective_parameters": {},
    "parameter_fingerprint": "...",
    "config_schema_version": "...",
    "dependencies": [],
    "algorithm_version": "...",
    "schema_version": "..."
  },
  "upstream_refs": [],
  "payload": {"path": "payload.bin", "format": "...", "fingerprint": "..."},
  "status": "complete"
}
```

`index.json` 只是可重建的目录索引，不是结果真源。索引缺失或损坏时，应通过扫描 receipt 重建。

### 9.3 中间产品、正式输出和 checkpoint 必须分开

不建议一开始做会自动拦截任意函数的“万能可缓存中间件”。它无法可靠判断函数的输入边界、随机状态、外部资源和结果语义。更小且安全的设计是：

- **语义 output**：包对外发布的长期 immutable 结果，进入 `outputs/<package>/<port>/<layer>/` 和版本索引；
- **可复用 intermediate**：包显式声明的阶段产物，拥有自己的 `IntermediateRef`、identity、依赖、参数和 schema，完成后才进入可复用索引；
- **run-local checkpoint/scratch**：可变的运行中状态，只用于精确指纹匹配后的恢复，不作为普通 output 或 intermediate 版本。

中间产物建议采用“JSON receipt + 独立 payload 文件”：小对象可以是 JSON，大型网格、数组或二进制数据放在独立文件中，receipt 记录格式、大小和 fingerprint。未来若引入 SQLite，它更适合作为 metadata、目录和依赖查询索引；payload 文件仍是内容真源，不把 SQLite 作为唯一数据存储。

### 9.4 free-space 迁移必须带上认证密钥

当前 free-space cache 使用目录内的 `_cache_secret(directory)` / `.free_space_cache_key` 进行 receipt 认证。只复制 JSON 而不复制该密钥，会使新目录验证失败并触发重算。因此迁移必须保留对应密钥。新旧目录已有不同密钥时，按 key ID 并存，不能覆盖目的地密钥或重签历史 payload。密钥本身不进入计算 identity，但属于缓存可验证性所需的元数据；其初始化也必须加锁，避免并发覆盖。

### 9.5 生命周期、并发和历史导入规则

缓存状态至少需要区分：`running`、`complete`、`failed`、`stale`、`orphaned`、`quarantined`。只有完整且通过验证的结果能作为 exact cache hit；迁移后的命中应显示为 `migrated_reuse`，历史旧证据应显示为 `historical`，不能自动冒充当前 fresh。

写入时应使用每个 identity 的锁、临时文件和原子发布。崩溃留下的 partial 文件要清理或隔离，不能被当成结果。删除上游版本后，下游保留文件但标记为 `orphaned/unavailable`，不自动篡改下游内容。

旧 `outputs/design/...` 中没有可信 receipt、完整 contract 或可验证 fingerprint 的历史 JSON，不应盲目导入正式缓存。它们继续作为历史证据，若确实需要复用，应通过显式、可审计的 legacy importer 转换为新的 receipt。

### 9.6 自检查后的实施边界

第一阶段只需要实现 typed config 快照、薄 `CacheStore`、sidecar 迁移和正式 output 的版本管理。中间产品先保留长期设计，不为未出现的需求添加运行时类、注册器或目录；SQLite、自动中间件拦截、完整 GUI 管理器和历史批量导入都留到有实际需求时再做。

## 10. 已确认的 Spec 与 A → B → C 计划

用户确认覆盖全部三个范围，并要求连续完成到 Plan C。本轮交付设计与实施计划，尚未实施产品功能、迁移真实缓存或重跑模型。

| 文档 | 责任与交接 |
| --- | --- |
| [总 Spec](../superpowers/specs/2026-11-15-parameter-owned-sidecar-cache-design.md) | 参数所有权、身份、sidecar、兼容性与验收条件 |
| [Plan A](../superpowers/plans/2026-11-15-package-owned-parameters.md) | typed 参数、默认值、快照与 receipt、warning 传播；开放可变净空前先保护 checkpoint |
| [Plan B](../superpowers/plans/2026-11-15-model-side-cache-store-migration.md) | 模型旁所有缓存和运行文件、迁移、认证域、锁、索引、精确删除 |
| [Plan C](../superpowers/plans/2026-11-15-output-port-and-intermediate-cache.md) | 从实际验收的 A/B 重新 Brainstorm/Grill，决定直接拆分或先修补；默认延期中间产物 |
| [jj 推进与交付记录](../superpowers/handoffs/2026-11-15-parameter-cache-planning-delivery.md) | 唯一交付工作线、检查点、恢复方式、审查证据和未验收草稿隔离 |

审查补齐的关键限制：

- 现有 IFC capture 含绝对路径。迁移需验证 `SourceBinding` 并保留原 canonical source ID，不能以“路径不参与 identity”的文字替代实际修复。
- 本轮重构会改变现有 key 所绑定的实现文件 hash。必须使用重构前的真实、小型 receipt 和旧 hash 清单验证受限兼容映射，不能只拿改完代码后生成的 fixture 证明迁移成功。未知算法或数值依赖变化仍然 miss。
- raw/processed loader 必须向 runner 传递历史计算 contract、warning 和 adoption 来源，不能用当前 contract 与自身比较而伪造 exact 命中。
- 模型旁目录还包括 UI worker 的 request/result、stdout/stderr 和 terminal diagnostics；固定 Pixi 解释器、模块路径与工作目录继续使用受信任项目根。
- 删除版本只派生依赖可用性，不修改已认证 receipt，也不隐式级联删除。路径/free-space 版本被删不能使无依赖的 Euclidean modulation 失效。
- B 的起点是实际验收的 A **实现**提交，C 的起点是实际验收的 B **实现**提交。三份计划文档的存在不代表这些功能已经完成。
