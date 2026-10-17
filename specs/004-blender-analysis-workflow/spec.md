# Spec004 — Blender Analysis 工作流

**状态：APPROVED / IMPLEMENTATION IN PROGRESS。** 用户于 2026-10-15 批准计划并授权执行。本文仍是设计与验收边界，不是生产实现或验收通过声明。B3 仍为 OPEN。

## 目标和使用者流程

在指定 portable Blender 的一个可安装 addon 中交付统一 **Analysis workbench**，作为长期分析交付的一站。唯一稳定的 `N → Analysis` 面板包含“分区 / Domain”和“Free-space”两个 section：完整接入已经完成的 B4 分区能力，并新增 free-space 使用链。B4 可以独立刷新、检查、选择和显式确认，不需要先运行 free-space；free-space 使用确认域、analyzer 自有 plane 和既有 AnalysisRequest，异步计算、检查裁剪二维格网、保存新 `.blend` 并重开恢复。

后续 operation 逐步进入同一 UI 与 service boundary，共享 capture、canonical identity、confirmed domain 与只读结果访问。本轮只建立可检验的消费边界，没有现成下游分析 consumer，也不实现未来分析。B4 保留既有 service/reducer；统一入口不要求把其 lifecycle 塞入 free-space AnalysisRequest。

格网是在三维场景中显示的二维 surface grid，不是 voxel 或三维占用。默认 `whole_height_projection`，`spacing=0.25 m`；exact 模式初始 plane `origin.z=1.6 m`，查询高度只由该 plane snapshot 提供。B4 enclosure 推断使用独立 structural scope、datum 0 m、cut 1.5 m；它不是 exact occupancy 的 1.6 m 切面。

## 用户故事与验收情景

### US1：一个入口完成 plane、当前 ROI 和计算（P1）

用户安装并启用 addon，配置 repository root 后，在 linked IFC/Bonsai 场景的 Analysis 面板创建 plane。plane UUID 持久存在，名称只用于显示。面板显示 units、world-XY、默认 whole-height、0.25 m、B4 cut 1.5 m 和 doors/windows closed-scenario 限制。用户刷新当前 B4 候选，检查面积、holes、来源与 refusal，选择并按 Confirm；仅 select/preview 不产生有效 AnalysisDomain。doors/windows 的 closed-scenario 只适用于 exact confirmed boundary members；malformed、failed-target、incomplete 或 ambiguous multi-owner support 仍保持全局 unknown。没有当前选择时，Start 给出明确原因，绝不使用历史 S3 代替。

确认后，Start 冻结 plane/request/domain/source/config tokens，分批捕获完整物理 inventory，用一个 Pixi 子进程执行既有 AnalysisRequest。期间 Blender 仍可交互，显示真实阶段、已捕获对象数和 elapsed。Cancel、失败、场景改变均保留上一个结果，并明确其 freshness。

### US2：显示可信且可解释的离散格网（P1）

只有当前 job/session/plane revision/source/config 匹配的结果可发布为 current。着色 mesh 裁剪至确认域的 exact outline 与 holes；一个 cell 的多个碎片共享稳定 index。点击或输入 row/column 能看到 boolean、六态 FieldStatus、来源、表示限制、query/domain/plane identities 和 reconstructed support/provenance。已知 occupied 不被其他 unknown 擦除；可定位的不确定性只影响其保守 support 涉及的 cells。全局 support_status 与 per-cell status 分开显示。

overlay 使用 frozen snapshot frame，不能 parent 到可编辑 plane/camera 后随之移动旧答案。plane edit 后旧 mesh 留在旧位置并标 stale；display-only Z lift 可单独调整，面板仍显示原始 snapshot 查询高度。

### US3：保存、重开和离线查看（P1）

用户通过 Save Copy 显式选择新的 `.blend` 路径，默认建议 unique run-based 路径；不覆盖当前 `.blend` 或 IFC。plane、tagged overlay、versioned compact JSON Text 随 `.blend` 持久保存，Text 使用 fake user。重开后即使 sidecar 已删除，也能恢复相同 cells、身份和颜色。结果初始为 historical/unverified，不自动重新计算或恢复旧进程；linked IFC 缺失时仍可看保存的 mesh 和证据，并说明重新计算依赖。malformed、digest 错误或更高 schema 的 JSON 被拒绝，并显示诊断。

若原生 `save_as_mainfile(copy=True)` 抛出异常，面板保留 live Text、overlay 与 result，仅清理 addon 自有 partial；本次不记录 saved artifact。只有随后一次原生保存成功后才记录 artifact。

### US4：支持绑定、替身与兼容（P2，但属于完整性）

推断 B4 domain 的 source_id 默认 None。把地板 shell 排除为 domain support 时，用户在同一面板显式绑定唯一、当前验证有效的 slab/floor source，或复用完全匹配的现有有效声明；未绑定时显示警告，真实 slab 继续参与 occupancy，原始计算仍可执行。三个旧 hull 的七个 owners 仅作为明确的 scoped declarations 导入，并逐项验证 project/source identity、geometry、coverage 和范围；失败 required proxy 不得退回 raw 原物。旧 `om_b4` operators 在可行时作为同一 service/reducer 的薄兼容入口，不维护第二份 state 或算法。

### US5：独立使用完整 B4 分区工具（P1）

用户只打开 Domain section 即可 Refresh 当前结构候选，编辑有限非负 residual tolerance（mm²），查看 datum 0 m/cut 1.5 m/world-XY 与 doors/windows closed-scenario 假设、source/geometry counts、candidate id/version、面积与 holes、真实 outline/hole curves 和 measured labels。Select 仅预览；explicit Confirm 按当前身份绑定 consent。refusal/error、source/request stale notice、current domain、last attempt、ignored tiny residual count 和 significant aperture residual diagnostics 都保留。统一 service 返回既有 typed/service payload 的这些事实，不从 overlay 重算。不把 reducer 支持但现有 UI 未暴露的 replace/conflict 操作宣称为既有 UI parity；其状态如由 service 返回，应如实显示。

### US6：按明确身份只读消费结果（P1）

无 bpy 的 headless consumer 可列出结果 metadata，按 immutable `ResultRef(kind, result_id, digest)` 精确打开 domain snapshot 或 free-space snapshot；free-space 可按 row/column 重建完整 FieldSample。live 内存文档和重开 embedded 文档走同一读取入口，目录由既有 embedded manifest/文档推导，不另建可变权威 registry。不按时间自动挑 latest，不从 mesh/color 读真值，不 capture、compute 或 mutation。

读取必须校验 schema/algorithm/backend compatibility、project/source、domain、plane/revision、request/query/semantic identity 与 digest；missing、mismatch、ambiguity 明确拒绝。要求 current 时必须有匹配的新鲜来源核验证据，stale/historical/unverified 不得冒充 current；显式 historical read 可保留旧证据。freshness 与 sample.status 独立：current run 仍可能含 unknown/conditional。`physical_occupancy_bool` 的 True=occupied，False 仅在 established/conditional 下表示该 query 的 known-empty；unknown/outside/invalid/not_available 为 None，绝不推断 free、clearance 或 routing。消费端 headless contract tests 是本轮交付，不代表已有真实下游分析。

## 功能需求

| ID | 必须满足的行为 |
|---|---|
| FR01 | 安装型统一 Analysis workbench，唯一稳定 `N → Analysis` 面板，Domain 与 Free-space 两个可独立折叠/展开的 sections；交付完整既有 B4 与新增 free-space；无 server、运行脚本前置步骤或会话级手工 panel 注册依赖。 |
| FR02 | analyzer-owned plane 是唯一几何 author；durable UUID/revision、units/transform/world-XY 验证；display CameraBinding 可选，不能改变 plane。tilt、finite band、3D 明确 unsupported。 |
| FR03 | B4 独立可用并保留 US5 全部 UI/service 能力，refresh/select/explicit confirm、tolerance/assumptions、outline/holes/area、counts/aperture residuals、refusal/attempt/current/stale diagnostics；持久 reducer events 与 candidate/source/frame/domain-request identities；新 canonical identity 不继承旧 STATE consent。 |
| FR04 | 一次完整 capture → canonical NeutralSceneV2 → exact structural subset B4 + full occupancy；canonical id=`ifc-object:{GlobalId}`，source_id=GlobalId，STEP 仅当前 provenance；不改普通 Blender adapter 的 source_id=None 语义。 |
| FR05 | `domain_handoff` additive `domain_geometries` 返回实际 authored refs 或 `_qualified` 的 derived mesh；序列化直接交接，不从 preview 重建或重跑 triangulation。actual holes/membership 随域进入 AnalysisRequest。 |
| FR06 | whole-height 默认、exact 世界 XY 可选；0.25 m 默认；exact 高度唯一来自 plane origin.z；display offset 不进入 query/key。 |
| FR07 | structural source fingerprint 与 full occupancy fingerprint 独立；家具变化令 occupancy stale，不伪造新的 domain consent；analysis Z 改变不自动使合法 XY domain 失效。 |
| FR08 | 显式合法 floor support binding、exact closed-boundary membership；无硬编码 door/slab IDs、无 class-wide slab/window/door 排除。未绑定 support 警告且继续 raw calculation。 |
| FR09 | 既有共享 registry/resolver/原生 MassPatch exact-once；家具 eligibility 不删除 plants/counter/其他物理障碍；missing capture 保持 unresolved；旧 proxy scoped 验证，required refusal 无 raw fallback。 |
| FR10 | FreeSpaceField optional `unresolved_supports`，只有具备可信 identity、query、geometry 与 complete-coverage 证据的支持（含 qualified-empty proof）才能定位 unknown；occupied 优先；point/line/touch support 也保守影响 eligible cell；malformed、missing、failed-target、incomplete 或 ambiguous multi-owner support 全域 unknown；完全域外 support 不污染域内。 |
| FR11 | 全部 bpy 只在主线程；分批 capture/timer，单 callback 目标 50 ms；单对象 to_mesh 不可抢占需测量；无 heavy draw/handler 计算。一个全局 process，多 plane durable results。 |
| FR12 | job/session/source/request/config 冻结；捕获和运行期间含 ABA 的 edits、undo、load、file switch、unregister 均不能把旧结果发布 current；不确定 freshness 显示 unverified。 |
| FR13 | hidden Windows Popen、no shell、validated configured Pixi interpreter；cancel/exit/error 清理自有 job；旧结果保留；不从 imported JSON 执行命令或自动运行 Text。 |
| FR14 | compact versioned JSON：共享 snapshot/query/lattice/source_audit；cell deltas 可精确 reconstruct 每个原始 FieldSample；按值去重，保留同 key 不同值；digest/schema/algorithm 验证、unique sidecar atomic publish。 |
| FR15 | 1 或少量 tagged native mesh overlays、face→cell attrs、actual domain clipping/holes、状态与值明确图例；native mesh/color 只是显示，不是权威结果。 |
| FR16 | row/column、来源、表示限制、support/provenance inspect；六态可用文字辨识；显示 counts，不能 `count*spacing²` 宣称 exact free area。若显示面积，仅明确标记 grid-classified clipped area。 |
| FR17 | `.blend` 内 fake-user compact JSON + tagged plane/mesh 可恢复；sidecar 删除仍恢复；load 不启动 worker；reopen historical/unverified；显式 Save Copy 新路径，不改 IFC。 |
| FR18 | addon/module imports 不 eager import root package/OCTA/evaluator；只使用现有 Pixi dependencies 与授权 portable Blender。 |
| FR19 | 同时完成 0.25 m 两模式真实 operator acceptance、responsive/cancel/error/stale、save new copy/独立 portable process reopen、cells/identities 精确对比、IFC unchanged 证据。fixture smoke 不冒充 live human confirmation。 |
| FR20 | 独立 review、owner evidence、architecture/memory 同步与唯一 version specialist 的 scoped jj；push/merge 单独授权。所有任务保留 checklists、command exits 和输出路径。 |
| FR21 | 复用既有 operation 字符串/descriptor 词汇、B4 service/reducer、AnalysisRequest、Field/result contracts；统一 capture/identity/domain/result access，不新建 framework/DSL/通用 job-result registry；substitute registry 仍只负责 substitute selection。 |
| FR22 | 只读 list metadata→exact immutable ResultRef open→sample read/reconstruct，覆盖 domain/free-space 两类结果与 live/embedded 同入口；验证身份/版本/来源/domain/plane/query/digest/freshness，缺失、冲突、歧义及 stale-as-current 拒绝；unknown/conditional/provenance 原样保留；headless 隔离、无副作用、sidecar-free 恢复测试。 |

## 边界和非目标

本轮交付统一 workbench 的 B4 分区、现有 planar physical occupancy 使用链及只读消费合约；未来 operation 按同一边界增量接入。B3 OPEN；不交付 clearance、routing、3D、complete free-space、新 score/model 层、自动替身、自动 floor detector、新 inference、plugin DSL、queue backend、降低精度或隐式 IFC camera/create_drawing/IFC 写入。旧 outputs、runner artifacts 和历史 source facts 不覆盖。

## 成功判据

1. 初次安装到重开恢复的一条操作链不依赖 experimental panel；两种查询通过相同 AnalysisRequest 核心产生 cell 证据。
2. 已确认真实域/holes/membership 身份完全可追溯；无历史 S3 自动选择，旧 identity migration 不能继承 consent。
3. 纯 display edit 不失效 semantic key；任何不能证明 current 的 source/config/plane 变化只得到 stale/unverified。
4. 完整 FieldSample round-trip、mesh face→cell、source once-counting、localized unknown 和失败保留旧结果有自动化证据。
5. native save/reopen 验收发生后才可记为已实现；本文件不宣称这些步骤已经发生。历史测量 whole-height 约 465 s、exact 约 55 s，性能目标是响应与如实进度，不承诺瞬时完成。
6. B4 独立能力映射逐项通过；只读 headless consumer 在不同 domain/plane/mode/revision 间精确隔离，live 与无 sidecar 重开得到相同权威内容，且不触发 capture/compute/mutation。

## 已批准的设计选择

用户于 2026-10-15 批准 installable addon + existing core/Pixi subprocess、单全局 job、canonical IFC identities、明确支持源绑定、plane 自有/display camera 可选、重开结果 unverified。设计审阅 gate 已通过；若现场没有当前合法 domain 选择，实施验收仍应停在明确选择/确认这一用户动作，不能代替用户编造 consent。
