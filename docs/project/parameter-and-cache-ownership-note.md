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
  sources/
    <source-fingerprint>/
      source.json
      outputs/
        free_space/
          <version-key>.json
        euclidean_distance/
          <version-key>.json
        path_distance/
          <version-key>.json
        axis_potential/
          <version-key>.json
      runs/
        <run-id>/
          logs/
          checkpoints/
          intermediate/
```

`source-fingerprint` 应绑定 IFC、Blender 或 canonical scene capture 的内容，以及被分析的外部依赖文件。文件名和路径主要用于显示；实际复用身份使用内容和依赖指纹，因此模型改名或移动时，只要 sidecar 一起移动，缓存仍可识别。

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
2. 让所有实际运行入口读取同一组包级参数；先补 global source runner 的净空参数。
3. 为 package contract 增加参数暴露级别、单位、来源和影响级别。
4. 将 sidecar 路径解析为默认缓存位置，并保留显式 `cache_directory` 覆盖能力。
5. 明确输出口依赖边界，逐步拆开欧氏与路径结果的缓存 identity。
6. 增加版本列出、精确删除和 `1 → 2 → 1` 命中测试。
7. 为 checkpoint 增加输入、上游 ResultRef、policy 和算法指纹校验。

暂不引入 SQLite，不先做完整参数平台或 GUI，也不先开放 `epsilon`。现有 JSON receipt、原子写入和目录索引足以支持第一阶段的版本管理。
