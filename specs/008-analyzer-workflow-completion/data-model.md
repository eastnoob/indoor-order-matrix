# Phase 1 Data Model — plane / Space composition

日期：2026-10-19。这是目标设计，不表示当前主树已具备以下接线。既有类型、字段命名与 serialization version 以 T0 恢复的接口为准；本设计只扩展现有 session/Region mappings，不建立第三套分析模型，不改变 `room_analysis_model` 或 `FieldStatus`。

## 1. Plane composition

一个薄组合绑定连接原生 drawing camera 与既有 AnalysisPlane。复用 `CameraBinding`；native object/entity 引用只在运行时使用，不序列化 Python 指针或 Blender 名称作为权威身份。

| 数据 | 权威与规则 |
| --- | --- |
| project identity + drawing camera GUID | 原生 IFC 身份；验证 native entity/object 的一一对应及 drawing-camera 资格；名称仅展示 |
| CameraBinding | 既有 native-backed camera pose、单位/来源及 revision；display-only binding 不得用于 author/refresh |
| AnalysisPlane identity/revision | OA 分析身份；原点 SI、正交右手 basis；由 native pose 转换，禁止静默投平 |
| 已观察 source/pose fingerprint | 用于比较相机移动、替换、删除、项目切换及重开；不代替 native truth |
| freshness / review | 沿用现有 session 失效与复核状态；显式采用/refresh 后才可确认；重开为 requires_recheck |

关系：一个当前分析 plane 绑定一个明确 camera；同一 camera 可以被既有历史结果引用，但历史 plane revision 不能冒充当前 revision。任何 pose/source/revision 变化使依赖 Region/result 的确认失效，按既有状态保留历史供查看。

新建 camera 是显式 native authoring；采用已有 camera 和 refresh 只读取事实与更新 OA 状态。新建取消或失败不留下本操作半成品。native 可记录的姿态与具体 query 支持分开判断：完整工作流拒绝 tilt；exact world-XY section 还要求 canonical basis。

## 2. Space composition

另一个薄组合绑定连接原生 IfcSpace 与既有 Region/domain。原生 GUID 和 geometry 始终权威，不新增 IFC class 或由 display mesh 推导的新 Space truth。

| 数据 | 权威与规则 |
| --- | --- |
| project identity + IfcSpace GUID | 指向唯一 native source；canonical source/ref 与 GUID 一致，名称仅展示 |
| storey_ref | 验证所属层；缺失、冲突或与当前目标层不一致时拒绝采用，不按名字猜 |
| Region/domain identity | 复用现有 Region/domain；来自 `authored_space_domain` 的资格校验和 canonical geometry |
| domain geometry / digest | 支持的单一有效几何及 shell/holes；存观察 digest/版本用于 freshness，回读 native 后才能确认当前性 |
| origin/provenance | 区分采用既有 Space 与 created_from_b4；后者保留 candidate/session/frame/outline digest 和 authoring 参数来源 |
| 可选 authoring datum/height/unit provenance | 只记录本次确实使用的参数；既有 Space 直接采用无需先填 B4 基准或人为重建拉伸高度 |
| review / freshness | 沿用 Region confirmation；source/plane/query/domain 改变则失效；保存重开不自动恢复旧确认 |

成功创建只返回准确 IfcSpace entity/GUID 和对应 Blender object，立即 canonical recapture，再走与“采用已有 Space”相同的 `authored_space_domain` 路径。不能用 object 名称差集找新 Space；不能把尚未验证的临时 mesh 当成功结果。

## 3. 既有输入 mapping 中的 datum / height

这些是 authoring 输入与 provenance，不是额外的持久对象类别。

| 输入组 | 值 / 校验 |
| --- | --- |
| datum mode | storey 或 selected slab，二选一；切换使旧候选/确认失效 |
| storey datum | 明确 storey_ref 与已验证变换后的 SI 底面；`0.0 m` 合法，不等于 height |
| slab datum | 选定 slab_ref、唯一 native storey 关系、变换后水平上表面及 SI datum；共面三角片可共享平面，倾斜/多级/歧义拒绝 |
| B4 structural context | 复用 `StructuralContext.datum_z_m/cut_z_m/storey_ref/selected_wall_refs`；记录 cut offset 与 absolute cut 的关系，不以 camera Z 或 extrusion height 覆盖 |
| height mode | authored quantity 或 manual，二选一；显式记录实际使用来源，无隐式合并/叠加 |
| authored quantity | `Qto_BuildingStoreyBaseQuantities.GrossHeight` 的唯一有效 `IfcQuantityLength`；记录 entity/ref/path、原数值、quantity Unit 或 project length unit、SI 值 |
| manual height | 用户明确输入的有限正长度，携带输入单位和 SI 值；authored 缺失/无效/歧义时可直接使用 |
| provenance | native project/storey/slab/quantity refs、转换来源及已观察 revision；无相邻 Elevation 相减、NetHeight 替代或默认高度 |

所有几何交接均以 SI 为分析边界；native authoring 处按已有单位转换约定进入 IFC 单位一次。scene scale、object matrix、project units 与 quantity override 要分别验证，不能把显示单位当作已经换算的数值。

## 4. 冻结 B4 sketch 的值

沿用 B4 candidate cache/document，不新增 sketch registry。明确创建前冻结以下现有值：source/capture/session/attempt identity、candidate identity、B4 两种模式及 selected-wall scope、structural frame、一个 Polygon 的 exterior 与全部 interior rings、datum、高度来源与 SI 值、effective B4 参数、geometry/algorithm version 和 outline digest。

校验规则：

- shell/holes 坐标有限、闭合、有效，面积为正；内环在 shell 内且互不相交/接触，不接触 shell。
- 一个 candidate 对应一个 Polygon；意外 MultiPolygon 或损坏环明确拒绝，不做 hull/buffer/丢片段修复。
- digest 保留环的几何与拓扑；按 native API 约定整理闭合点重复和环方向时，不得改变轮廓语义或重新围合。
- source、plane、storey/slab、height、query 或 B4 参数改变后，旧 sketch/confirmation stale，必须重新准备/复核。
- 内部 label/seed 仅供 UI 选择，不能替代 shell/holes。临时 sketch/preview 对象标记为展示产物，不进入 physical inventory。

round-trip 验证复用现有 geometry/test 比较工具，在运行前固定并记录 fixture 的线/面积/体积容差、单位和来源；B4 gap-closing 容差不自动成为 extrusion 几何误差许可。验证 topology、逐环边界、净面积、base/top 与 volume，失败不发布 Space。

## 5. 状态与写入边界

下表是既有 session/Region 状态行为的设计约束，不要求新建一个平行状态机或增加 FieldStatus。

| 事件 | 状态变化 | IFC / Blender 影响 |
| --- | --- | --- |
| 选择/读取已有 camera 或 Space | 取得可复核绑定，验证后显式使用 | 不写 IFC |
| 新建 drawing camera | 预检 → native 创建 → 准确绑定 | 仅显式动作写入；取消/失败恢复本操作资源与历史 |
| B4 Analyze / 选择 / eye / preview | 更新 attempt/cache/current/stale 等既有状态 | 只读分析；展示对象不成为 IFC truth |
| 确认 B4 Space 创建 | 重新验证冻结输入 → 暂时 creating | 拒绝重复提交与无关活动事务；临时资源仅属本操作 |
| 创建及 round-trip 成功 | native recapture → Space composition → 待/已按既有 UI 规则确认 domain | 返回准确 native 身份；不从成功创建推导所有后续分析已确认 |
| 任一步失败或取消 | 不发布当前成功；精确恢复操作前边界 | 开放/已 finalize 事务分别处理；恢复失败明确拒绝继续成功流程 |
| source/pose/query/domain 修改 | 依赖确认失效，保留既有历史诊断 | 不自动改写 IFC 或伪装旧结果为 current |
| 保存/重开 | 还原身份、参数、历史结果与 provenance；requires_recheck | 重新 resolve native、capture、验证后才能再次确认和运行 |

authoring 的 transaction key、owned entity/object/mesh/collection refs、临时 cursor/selection/container 状态是短生命周期恢复数据，不添加到分析公共导出。不得持久化运行时指针；不得以取消标志或错误报告代替恢复证明。

## 6. Furniture / physical inventory / query

家具 eligibility 沿用已有 included/excluded/unknown/unset 策略。excluded/unknown 在家具目标分析中执行 shared veto；unset 保留既有行为。authored group/member refs 保留，消费者从 eligible members 求 support/trend/affordance；无 eligible members 时 support_area=None、member_geometry=[]、trend unavailable。

physical inventory 仍保留对象及其实际占用事实，不能因家具目标排除而删除。SupportBinding 只作用于明确的 source 与关系；slab datum 选择不把所有 slabs 排除。whole-height/section/finite-band 沿用既有 request 身份，camera Z 改变不隐式切换 query；unknown 继续携带 diagnostics/provenance，不能当 free。

持久化继续使用现有 session/Region/result schema/version 机制；扩展必要 OA mapping 时同步测试迁移/缺省行为。不得从展示 mesh 重建权威 Field/result，也不改变 `room_analysis_model` 公共形状。
