# 证据包最小通用规范

状态：**持续维护的开发规范与声明模板，2026-11-17 已对照本地接受的 A/B/C 更新；复用现有类型和显式可选依赖，不新增注册表或调度框架。**

本规范只规定所有证据包必须共有的边界。几何计算、证据语义和包内公式仍由各证据包自己定义。
当前入口见[结构说明](../../project/evidence/evidence-package-structure.md)；验收与未覆盖范围见 [C 交接](../handoffs/2026-11-15-plan-c-complete.md)。原日期章节保留决策历史，不表示后续能力已合入 owner/main。

## 组合与职责边界（2026-11-17 用户确认）

完整证据包由业务入口、参数声明、数值函数、公共发布模板、可选加工与现有存储组合而成。
`EvidencePackage` 是冻结的可配置公共模板，不要求包继承它；不将模型读取、全部算法、缓存或 UI 塞进同一个类，也不因 OOP 名义新增继承树。

| 边界 | 当前职责 |
| --- | --- |
| 包的 entry / builder | 准备并绑定输入、参数与算法；`run_*` 负责复用/计算和存储编排。未来 UI 对接业务入口。 |
| `evaluate(source_envelopes, *, dependencies=(), dependency_graph=None)` | 接收准备好的来源和显式依赖，发布 `EvidencePackageOutput`。 |
| `process_output(raw_output, *, package_freshness=...)` | 读取现有 raw，通过已配置处理器返回独立 `EvidenceProcessedOutput`。 |
| 算法、参数、加工与存储模块 | 各自承担数值计算、参数校验/快照、加工配方和保存复用，复用已有函数与类型。 |

类本体只有上述两个业务方法；包的 facade、builder、存储函数与语义出口不计入此数量。
参数在外围入口或构建时解析/绑定；`parameters=`、`parameter_schema=` 不是 `EvidencePackage.evaluate()` 或 `EvidencePackage` 构造器的现有参数。

## 可选处理出口（2026-11-12 用户确认）

模板保留原输入、算法和原始缓存，提供两个逻辑出口：原始出口默认可用；处理出口默认关闭，只有显式配置本包的处理函数才生效。当前历史 `output_function` / `context_output_function` 是原有计算发布步骤，继续必需；新增 `output_processor` 才是本条所指的可选函数。

- `evaluate(...)` 继续返回原有 `EvidencePackageOutput`；处理函数读取已经生成的原始结果，不重跑计算，也不向旧 `.outputs` 追加渠道。
- `process_output(raw_output, package_freshness=...)` 返回独立的处理结果；未配置时 `error_code="OUTPUT_FUNCTION_NOT_CONFIGURED"`、`outputs=()`，没有可用数值。不能自动 identity 或回退 raw。
- 已配置但执行/输出校验失败时返回 `OUTPUT_PROCESSING_FAILED`；来源未确认 fresh 时返回 `OUTPUT_SOURCE_NOT_FRESH` 并跳过函数。固定错误标记可供 UI 和运行时消费者判断。
- 各包可以配置不同函数；配置显式记录函数 ID、版本和不可变参数。处理身份绑定原始内容和处理配方，原始缓存身份与 JSON v1 不受配置影响。
- 处理渠道沿用已有渠道/尺度/状态类型，并完整引用实际原始渠道。缺失/失效来源不能伪造数值，处理不提升未知状态。
- 原 2026-11-12 可选处理 checkpoint 仅实现运行时处理。后续 lifecycle 已增加独立 processed JSON、缓存与显式跨包处理引用；A/B/C 又增加参数快照、模型侧存储和 opt-in 独立语义出口。原 checkpoint 的限制不再代表当前全部能力。
- 本模板不选择归一化、尺寸、0.6、势或融合公式；原有派生渠道仍属于历史原始发布对象。

执行与验收见[可选处理计划](../plans/2026-11-12-evidence-package-optional-processing.md)。

## 包内内聚与结果保留（2026-11-01 用户确认）

- 包拥有解释其目标关系所需的计算与逻辑，包括适用的几何计算；不以其他证据包必须启用为前置条件。可以复用普通函数和有效缓存，不新增公共测量层或包间调度框架。
- 旧调用继续使用 `evaluate(source_envelopes)`。需要跨包结果的包可额外声明 `dependencies=`，并通过带上下文的输出函数读取已发布渠道；旧输出函数保持兼容。这不表示允许直接传入 scene/polygon。
- 当前纯轴支持保留。现有 opt-in 距离调制及其他距离条件势或联合场只能追加具名结果，不能覆盖原始渠道或擅自改写原结果的含义；场景变化仍按真实依赖检查失效、重算。
- 保留渠道不等于增加独立票数；联合输出已使用的方向、距离不能默认再各计一票。

跨包读取可以建立渠道级依赖，但不自动意味着融合。其引用需完整绑定源包、源输出身份、目标和渠道；不同 target 的同名渠道可同时消费。源包 freshness 与源渠道 status 分开保留，stale/unavailable 的包结果不能作为当前数值输入，也不能发布带 observation 的派生输出。显式传给 `evaluate(..., dependency_graph=...)` 的图必须覆盖全部引用节点、匹配当前包及可用 typed upstream 的实际声明边，并在 callback 前通过无环检查；省略图的旧调用兼容，但不保证完整图或全局间接环检测。共享核心不维护包注册表。距离条件势和跨包融合公式仍需由对应包另行定义。

## 1. 必须定义的内容

每个证据包必须声明：

- `package_id`、`package_schema`、`algorithm_version`；
- `producer`、`output_function_id` 和 `output_function_version`；
- 输入的 source envelope、target、query、scope 和分析平面；
- 稳定且排序后的 target set，以及会影响结果的依赖指纹；
- 包自己的计算函数及其输入渠道；
- 参数名称、类型、单位、默认/必填、合法值、`exposed` 与计算影响，以及有效值和来源；
- 每个输出渠道的名称、含义、单位、状态、来源和 provenance；
- 启用独立语义出口时的 target/channel 地址、参数投影和实际上游依赖；
- 若输出是支持值：极性必须是“非负且越大越支持声明命题”，并声明归一化方法和范围；
- 缓存身份中会影响结果的 source、query、scope、recipe、算法和 schema 指纹；
- 现实 IFC 验证命令、图面和 manifest 位置。

未定义的内容不得由共享核心猜测或补默认值。

## 2. 最小包模板

每个包补齐下面的声明清单；共享模板负责发布和校验，业务入口组合已有算法与存储，不再复制一套 field/cache/result 类型。

```text
PackageDefinition {
  package_id, package_schema, producer,
  output_function_id, output_function_version,
  source_channels, target_rule, query/scope/plane rule,
  parameter_schema, effective_parameter_snapshot, parameter_sources,
  algorithm_or_adapter, run_entry, storage_binding,
  dependency_fingerprints, optional_semantic_output_contracts,
  channel_declarations, recipe, normalization_rule,
  visualization_manifest_rule
}

RawResult = EvidencePackageOutput {
  package_id, output_function, output_function_version, schema,
  source_envelopes, outputs, dependencies, output_identity
}

OptionalProcessedResult = EvidenceProcessedOutput {
  package_id, raw_output_identity, raw_payload_fingerprint,
  processor_id, processor_version, parameters, parameter_snapshot,
  outputs, error_code, processing_identity
}

PackageStatus = {
  freshness, recompute_required, reasons, affected_targets
}
```

`PackageDefinition` 是文档声明清单，不是要求新增的运行时类；参数、运行入口与存储声明也不是 `EvidencePackage` 的新增字段。`EvidencePackage` 是当前已有的可调用执行模板；
`EvidencePackageOutput` 是当前已有的运行时结果承载；`PackageStatus` 复用现有 freshness
协议，visualization manifest 也属于外围发布记录。`output_identity` 与 `processing_identity` 是现有属性，不是另加的构造器参数。
旧 combined runner 返回 `raw_output` / `processed_output` 等映射；C cache runner 返回 `PortRun`，多出口时按语义种类组织。不要混用不同入口的返回形状，也不要求新增统一包装层。

### 参数声明与 UI 标签

复用 `features/evidence_package_parameters.py` 的 `ParameterSpec`、`ParameterSchema` 和 `ParameterSnapshot`。声明示例：

```python
from features.evidence_package_parameters import ParameterSchema, ParameterSpec

PARAMETERS = ParameterSchema(
    "example-package", "example-package/1",
    (ParameterSpec("min_total_m", float, 0.55, unit="m", minimum=0.0, exposed=True),),
)
requested = PARAMETERS.resolve({"min_total_m": 0.60})
```

这是声明示例，不代表当前场景规则，也不会自动把参数接进算法。包入口须把有效值交给对应算法，并在 contract/receipt 中保留快照与来源。声明适用的 `minimum` / `maximum` / `choices` / `nullable`；必填参数复用现有 `REQUIRED`。

- `exposed` 只表示未来 UI 调参面板是否提供该项；不另加 `hyperparameter` 字段。
- `resolve()` 对 `exposed=False` 仍允许合法程序传值覆盖；保留类型、范围、选项校验，不增加覆盖禁令或权限含义。该字段不会自动生成 UI。
- `capture_calculated()` 只接受完整历史值与来源，不能用当前默认值补齐历史结果。
- 快照记录有效/计算参数、来源、impact 和计算身份；value contract 当前仅含 type、nullable、unit，不要声称完整复制了默认、上下界、choices 和 exposed。
- 现有无 schema 处理器仍兼容；并非所有已有数字常量均已注册为可调参数。

| `ParameterImpact` | 计算与复用含义 |
| --- | --- |
| `RECOMPUTE_REQUIRED` | 在相关输出选定参数范围内进入计算身份；先找相同版本，未命中才计算。 |
| `REUSE_WITH_WARNING` | 值改变可复用，并保留计算值与请求值差异警告。 |
| `METADATA_ONLY` | 不改变计算身份，也不产生值变化警告。 |

## 3. 统一输入口

当前共享执行模板的计算函数接收不可变的 `FieldResultEnvelope` 序列。query、scope、
分析平面和版本必须从这些 envelope 的 `FieldQuery`/provenance 及包 contract 中取得；
不得读取未声明的全局状态、世界轴、其他包的私有对象或旧缓存。包特有的 target
枚举与依赖声明属于包 contract。现有 `evaluate(source_envelopes)` 调用保持兼容；需要外部渠道的包才显式提供 `dependencies=`，并选择接收上下文的输出函数。

调用者按声明 scope 准备输入；包不被要求读入整个模型，也没有自动抓取模型子集的共享路由。外围 facade 可以接收它自己的 bundle/context，再组织共享模板需要的证据。完整保留来源指本次实际传入的来源。
scope 可以是局部或全房间，但须保留算法必要上下文：局部路径仍需相关障碍和 domain，依赖完整 scope 的加工不得任意删减成员。

输入必须能回答：

```text
对哪个 target，在什么 query、分析平面、scope 和版本下，使用哪些 source channels 计算？
```

包不得偷偷读取未声明的全局状态、世界轴、其他包的私有对象或旧缓存。

target set 必须在包 contract 中先确定并按稳定身份排序；重复 target、隐式 first-wins
和依赖输入顺序造成的随机结果都不允许。没有目标的包结果应显式为 unavailable，不能
用空列表伪装为已计算。

## 4. 统一输出口

输出使用现有 `EvidencePackageOutput`：

- 完整保留所有 source envelopes 和其中的原始 channels；
- 派生结果作为新的 `EvidenceOutputChannel` 追加；
- 每个派生渠道引用实际使用的 source channels；
- 跨包渠道引用进入明确的 dependency 列表，并参与目标包输出身份；
- 派生渠道不能覆盖、删除或把输入状态改成数值零；
- 输出函数和版本必须写入输出身份。

`raw` / `processed` 是处理层级，不是业务输出种类。C 已提供 opt-in 的 `euclidean_distance` / `path_distance` 与 `axis_potential` / `distance_modulated_axis_support` 独立语义出口，复用 `features/output_port_cache.py` 的 `OutputPortContract` / `OutputPortRef`。契约绑定实际 target/channel、所选参数和上游引用；旧 combined API、raw JSON v1 及原引用的 `port=raw/processed` 含义保持兼容。内部阶段持久缓存与执行运行时仍为 design-only，不要求接入尚未实现的中间层框架。

原始观察、描述性读数、支持读数和状态读数必须分开。角度、距离等原始量不因支持输出规则而被覆盖。

输出渠道的 provenance 至少继承其实际使用的 source envelope 身份、输入 channel
引用、分析平面和 package/function version；跨包输入另保留源 package/output/target/channel 身份及 package freshness。包新增的解释只能追加，不能覆盖来源状态。

渠道算法/输入/输出责任直接使用已有字段：provenance 的 method、algorithm/schema
version 和已声明公式；没有更细声明时使用 package `output_function + version`
加渠道名；`derived_from`、source `cache_identity` 指纹及外部依赖记录实际输入。
geometry/trend 渠道可明确继承顶层 envelope provenance。不要求额外嵌套类型。

## 5. 状态和缺失

包必须区分 `computed`、`partial`、`not_evaluated`、`not_available`、`invalid`、`outside` 和 `ambiguous`。

- 缺失、无效、未知和不适用不填零；
- 不得临时改变分母来掩盖缺失；
- `partial` 可以保留可用的结构化观察；
- `ambiguous` 不得偷偷选择一个赢家；
- 每个非 `computed` 输出必须有原因说明。
- package freshness 与 channel status 是两个维度；freshness 过期不会改写已保存渠道的原始 status。跨包读回遇到 stale/unavailable 包时，有效读取状态为 `not_available`，并同时保留历史渠道状态供审计。
- freshness 为 `fresh` 时，来源渠道原 status 原样交给目标包；目标包按自己的算法解释 `partial`、`outside`、`ambiguous` 等状态，不由共享层猜测语义。

## 6. 支持输出与归一化

只有明确声明支持命题的渠道才可以标为 support。支持值必须满足：

```text
value >= 0
更大的 value = 对声明命题更强的支持
```

包可以自行选择单调转换、组合和归一化，但必须保留原始值、公式、参数、范围和端点含义。`[0,1]` 只统一数值范围，不自动证明跨包语义可比。

同一原始事实的多个派生表达不能因为渠道数量增加而重复投票。包内逻辑应按“充分理由、必要条件、质量调制或描述性诊断”明确区分。

## 7. 缓存和失效

复用现有缓存身份和 freshness 机制。按实际语义输出的契约投影比较，结果只有在其相关内容一致时才可复用：

- target、query、分析平面和 scope；
- source/input fingerprint；
- channel set 和 recipe fingerprint；
- algorithm/schema version；
- 任何会影响公式结果的参数。

历史 combined 接口允许整个包全量失效；C 独立出口按真实依赖分别复用，不能因净空/路线参数改变而作废独立欧氏结果。UI 对接至少得到：

```text
recompute_required: bool
reasons: [reason]
affected_targets: [target]
```

缓存是结果，不是新的证据来源；过期结果可以保留审计，但不得当作当前结果。

freshness 结果是只读的 UI 对接口，不触发计算。其最小字段固定为：

```text
recompute_required: bool
reasons: [{code, dependency, cached, current}, ...]
affected_targets: [stable target id, ...]
```

历史 combined 接口允许整个包失效；`affected_targets` 为空只表示当前结果可复用，不表示没有
目标。算法版本变化单独报告，不能被渲染器版本或文件时间替代。

纯 `evaluate()` 和现有无持久存储上下文的调用仍可使用；无需为每个包新建存储后端。C cache runner 要求显式 `CacheStore`，地址为 `source / package / semantic-output / raw-or-processed / identity`，数值与 contract 校验仍由包拥有。距离入口见 `features/group_distance_output_ports.py`，轴势/调制入口见 `features/group_axis_output_ports.py`。模型侧 sidecar、显式目录和未保存模型按现有 locator 规则处理，不回退仓库 outputs。

计算身份、内容完整性、文件字节和 freshness 分开核验：`output_identity` 不含
observation/status，空 dependencies 不进入计算 hash 以保留旧发布身份；序列化
`payload_fingerprint` 是除自身外完整规范化输出的 SHA-256，包含观察、状态、
provenance 和输入/配方指纹。单渠道可用 `fingerprint_evidence_dependency(channel)`
计算完整内容指纹。文件 SHA pin 保存字节；保存 contract 必须与新建 current contract
比较，不能信任旧 status receipt。旧计算身份相等不是结果数值相等的证据。

保存读回使用固定 v1 的 `deserialize_field_result_envelope(payload)` 和
`deserialize_evidence_package_output(payload)`，复用已有类型校验；拒绝未知 schema/
结构字段及非 JSON 对象，验证必需的 saved output identity 和存在时的内容指纹。
旧文件无 dependencies/内容指纹仍可读；消费者绑定其文件 SHA 和当前 contract。
放行数值前还必须独立提供 `current_source_envelopes`，按 `target`、`query`、
`channel_set`、`cache_identity`、`raw_status`、`value`、`support`、`source_ids`
核对快照输入签名；来源 reading 和渠道记录随 value 参与。仅 package ID 相同不能
绑定 contract 与 output。当前上下文缺失则 unavailable，输入/query/plane 不匹配
拒绝；顶层 provenance 的 source_freshness/visualization 审计字段不进入签名。

## 8. 来源、图面和验证

每个包必须保留 source IDs、输入身份、分析平面、算法/schema 版本和计算解释。需要空间解释的输出必须由同一 IFC 指纹生成平面图，并由 manifest 将结果 ID 映射到图层或图面。

最低验证清单：

- [ ] 输入身份、query、scope 和分析平面已核验；
- [ ] 输入覆盖声明范围的必要上下文，未随意裁剪周边事实；
- [ ] 参数已交给算法，有效值/来源可追溯；`exposed` 仅按 UI 约定使用；
- [ ] 已区分语义输出种类与 raw/processed 层级，并声明真实参数/上游依赖；
- [ ] 所有原始渠道和状态都被保留；
- [ ] 派生渠道有公式、来源链和版本；
- [ ] 缺失不被改写为零；
- [ ] 输出 JSON 可序列化，缓存身份稳定；
- [ ] 指定 IFC 的平面图、manifest 和 XML/结构解析通过；
- [ ] replay 在相同输入下得到相同结果；
- [ ] 未覆盖状态被明确记录，没有用模拟数据冒充现实覆盖。

## 9. 明确不属于通用模板的内容

通用模板不决定：候选如何生成、成员是否归属、跨包权重、统一融合公式、概率解释、阈值、winner、UI 颜色或某个证据包的几何算法。

这些内容必须在对应证据包或独立融合设计中定义，并继续保留在同一输出契约下。

跨包依赖图负责闭合节点、声明边一致性和拒绝环路，不负责调度执行。没有声明外部依赖的现有包保持独立运行，本规范不要求新增融合渠道。2026-11-10 rollout 独立读回包只忠实追加已有渠道，并分别处理 camera-plane free-space/distance 与 world-plane potential/trend/geometry；该历史 checkpoint 未实现 distance-to-potential 业务整合。当前已有显式 opt-in 距离调制，见结构说明与 C 交接；这不授权混合不兼容分析平面，也不代表通用跨包融合已实现。
