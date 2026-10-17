# Phase 1 Contract — Analyzer UI / native handoff

日期：2026-10-19。状态：设计契约，实施与 native 验收待完成。使用现有 addon、session、B4、request 和 result 入口；下列动作名表达用户交互责任，不要求新增通用 command registry。数据见 [data-model](../data-model.md)，验证见 [quickstart](../quickstart.md)。

## 1. Camera → AnalysisPlane

| 动作 | 输入与前置 | 成功 | 拒绝 / 取消 |
| --- | --- | --- | --- |
| 新建 Bonsai drawing camera | 有效 active IFC/native drawing 环境、原生创建选项；明确用户动作 | 经 native Add Drawing 链路创建；准确返回 entity/object；读取 native pose，绑定 CameraBinding/AnalysisPlane | 不支持姿态或前置缺失明确解释；取消/中途失败恢复本操作创建的 camera/IFC 关系及历史，不留下半成品 |
| 采用已有 drawing camera | 用户选择可验证的 native drawing camera；project/GUID 唯一 | 复用 read_camera_binding/plane_from_camera，展示来源并显式使用 | 普通未绑定 camera、错误 IFC 类型、项目不符、display-only 或 unsupported pose 拒绝；不按名称匹配 |
| 显式刷新 plane | 已有准确 native 绑定 | 重新读取 pose，更新 revision/freshness，失效依赖 Region/result 确认 | 删除/替换/身份不符拒绝；旧 pose 仅作历史，不当 live 当前 |

new drawing 是 IFC authoring；adopt/read/refresh 不写 IFC。新建不得退化为激活旧 camera、当前 viewport 或填写 Z。水平 plane 与 exact section 的能力分别检查；无法支持的旋转/倾斜 query 不静默改成 world XY。

## 2. Space 采用与创建输入

| 动作 / 输入 | 契约 |
| --- | --- |
| 采用选中 IfcSpace | 视口对象或原生源列表明确选择后点击使用；canonical capture → authored_space_domain；唯一 source/type/storey、闭合单一几何/可投影性等原资格检查全部保留 |
| 已有 Space 前置 | 无须先运行 B4，也无须为读取已有 Space 填新建用 height/slab；错误类型、无几何、错层、重复身份或不可支持几何明确拒绝 |
| Storey datum | 明确 storey 和 SI base；零 base 有效；不是由相邻 elevation 计算 height |
| Slab datum | 选定 slab 的真实水平上表面与唯一 native storey；slab-only 可自动解析关系，关系缺失/冲突时拒绝并提示；不强制重复选择同一层 |
| Authored height | 唯一有效 GrossHeight/IfcQuantityLength，记录 quantity 或 project unit 与来源；缺失/无效/歧义不虚构默认值 |
| Manual height | 用户明确有限正长度；与 authored height 是 OR；来源切换使旧候选确认失效 |
| 垂直参数 | camera plane Z、Space base、B4 cut offset/absolute Z、extrusion height 独立；native Space 从选定 base 向 +Z 拉伸该 height |

拒绝通过 bbox/maxZ、自动投平 slab、NetHeight 偷换、相邻标高差或默认 3m/RL3 补齐缺失事实。

## 3. B4 UI 与候选准备

normal 使用目标层相关墙；切回 normal 必须清理旧 selected_wall scope。selected-wall 模式限定选墙包围的候选范围，同时保留相关内部未选墙影响；开放边界不虚构闭合。

复用原 service/reducer、timer-driven preparation、取消、候选缓存与空间索引。保留进度、阶段、计数、容器、单选、面积、eye、容差、closed aperture 规则和完整 current/attempt/refusal/stale/显著 aperture residual diagnostics。失败尝试不得抹掉历史解释，也不得把历史结果显示为当前成功。

hover/list/eye 只读候选缓存或展示；Analyze、选择候选和 preview 不创建 IfcSpace。记录全场 capture 与局部 B4 各自计时和 source 数；局部计算减少不等于全场加载已经跳过。

## 4. 冻结 sketch → native Space

1. 用户选择当前 candidate，冻结 source/session/attempt/candidate/frame/version/digest、完整 shell/holes、datum、height/unit provenance 及 B4 参数；UI 显示将创建的底面/高度和来源。
2. 点击明确创建/确认动作后重新验证身份与 freshness；若场景、plane、基准、高度、轮廓或模式改变，拒绝旧确认。无关 native transaction 活动时拒绝，重复提交不生成第二份对象。
3. 将冻结 Polygon 作为 OA sketch，检查闭合、有限、正面积、内环包含/不相交等；只接纳一个有效 Polygon。禁止 seed 重围合、凸包、丢洞、丢 MultiPolygon 片段或自动 buffer 修补。
4. 进行 structural-local → world SI → product-local → IFC units 交接，长度转换一次。使用 native closed curves + `profile(outer_curve, inner_curves=...)` + extrusion，接 native representation assignment/switch、class/collector/storey placement；禁止调用 exterior-only Spatial polygon helper 丢弃内环。
5. 回读 native representation，验证准确 source、shell/holes 拓扑与边界、净面积、base/top/volume；fixture 在断言前冻结并输出比较容差/单位/来源，不能用 B4 缝隙修补容差事后放宽几何一致性。
6. 成功返回准确 entity/GUID/object refs，canonical recapture，经已有 authored_space_domain 资格流程采用。任何失败先恢复再返回拒绝，不发布半成品。

new Space 的写入来自该显式确认；slab/height/eye/preview 本身不触发写入。所有 native 修改属于这一操作的恢复范围，不扩大为通用 authoring 框架。

## 5. 取消、失败与恢复

native wrapper 异常并不保证回滚。操作前必须记录精确 transaction 边界/key/history、相关 IFC/Blender links、本操作拥有的实体/对象/数据块/集合，以及临时 cursor、selection、active container 等状态。

开放事务可走 native discard 路径；已 finalize 的事务要通过已验证的有界历史恢复本操作。禁止无边界 `IfcStore.undo()`、只删 mesh、猜对象名、替换整个 active IFC 或撤销无关用户操作。恢复后检查原状态、资源残留、链接和 history/redo；再试应只生成一份对象。

| 注入点 | 必须证明 |
| --- | --- |
| curve/profile、native entity 创建 | 不残留孤立 IFC/Blender 资源 |
| class/storey/representation assignment | 不残留半绑定实体或关系，原 storey/container 状态完整 |
| representation switch / native 几何回读 | 数据块、显示对象、IFC links 和交易边界恢复 |
| round-trip 校验失败 | 不发布成功；不能接受丢洞/错高度或以 seed 成功替代 |
| camera native 创建中断 | camera/annotation/group/document 等本操作资源被精确恢复 |
| 失败后重试及成功后的 undo/redo | 不重复创建；既有用户操作保持可用；session 不把失效绑定当当前 |

若恢复本身失败，明确报错并标记需复核，阻止后续成功发布/自动保存；该路径不能算作 R09 成功。真实 fixture 证明前不宣称“原子事务已完成”。

## 6. Furniture → free-space

| 边界 | 契约 |
| --- | --- |
| 家具目标 | 只用明确 authored furniture_group/member 声明；名称/图层/邻近不造组；shared participation 在 group/trend/affordance/target 消费前生效 |
| 空 eligible 集 | support_area=None、member_geometry=[]、trend unavailable；raw authored refs 可追溯；unknown 不冒充有效目标，unset 沿用旧行为 |
| 物理占用 | excluded 家具仍按物理事实占用；不通过删除 physical inventory 来“修复”目标分析 |
| SupportBinding | 保留具体 source 关系；选 slab datum 不自动免除所有 slab 占用 |
| Query | 明确选择 whole-height/section/finite-band 并参与 request identity；抬 plane 不自动改 whole-height 语义；能力不支持就拒绝 |
| Field/result | 复用既有 request/field/resolver，unknown/conditional/provenance 和其他实体占用保留，不将 unknown 当 free |

## 7. 保存、重开与已加载实现

沿用既有 session/Region/result 文档、schema/version 与读取入口。保存 plane/Space native identity、观察 revision、source/domain/query identity、必要参数与 provenance；重开还原为 requires_recheck。必须重新 resolve、capture、比对并显式确认后才能运行新的当前分析；旧确认不能自动恢复，历史结果可以按原语义查看。

验证分别覆盖既有 Space 与新建 Space 的完整 closed loop。结果与参数从规范文档恢复，不从 display mesh 反推。部署证据记录实际加载模块 `__file__`、完整 SHA256 和新进程/重新加载证明；operator 已注册不证明加载了本轮字节。UI/GPU、headless native 和 Pixi tests 分别记录，B3 保持 OPEN。

## 8. R01–R12 覆盖

| Requirement | 契约位置 | 实施证明 |
| --- | --- | --- |
| R01 | §1 new drawing，§5 camera recovery | native creation/cancel/fault + UI |
| R02 | §1 adopt/refresh，§7 reopen | GUID/pose/revision/stale/unsupported query |
| R03 | §2 existing Space | selected object/list，拒绝矩阵，无 B4 前置 |
| R04 | §2 datum | storey-only、slab-only、错层/斜面/多级拒绝 |
| R05 | §2 height，§4 units | authored/manual OR、零 base、正 height、unit override |
| R06 | §3 wall modes | normal/selected-wall、内部墙、开放边界、计时 |
| R07 | §3 preserved UI | progress/cancel/eye/area/cache/tolerance/diagnostics 回归 |
| R08 | §4 exact sketch | 凹 shell/holes/非零 base native round-trip |
| R09 | §4 explicit confirm，§5 recovery | 只读前后 IFC 不变、fault matrix、重试/undo/redo |
| R10 | §6 participation/inventory | 已知失败回归转绿且 occupancy 不变 |
| R11 | §6 query/field | 空间/plane/group identity、其他占用、unknown |
| R12 | §7 persistence | 两条 plane→Space→free-space→save/reopen，loaded-byte/UI 证据 |
