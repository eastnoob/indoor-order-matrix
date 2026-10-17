# 原始目标到实现证据清单

日期：2026-10-19。方框仅在本 feature 的实际验收完成后勾选。旧阶段 PASS 不自动迁移。

## 规划

- [x] 读取原始用户意图、当前代码、架构与本地 Spec Kit 模板。
- [x] 独立核查 camera/UI 和 Space/B4 两条链，区分底层接口和用户可用功能。
- [x] 单独建立 008，避免覆盖 006 或重复使用已有有限高度带 007 编号。
- [x] D1 层高来源、D2 slab 基准、D3 OA 包装及 D4 相机交互范围按原会话答复冻结。
- [x] Phase 0 研究、Phase 1 plan/data-model/contracts/quickstart 已生成；原生事务正确性等留作明确实施门槛。
- [x] speckit-tasks 已按 US1–US5 生成任务、依赖和独立验收条件，见 [tasks.md](tasks.md)。
- [ ] Phase 1 设计后续审阅完成。

## 实现与验收

- [ ] R01 Bonsai 同源 Set Camera 交互建立平面并正确取消。
- [ ] R02 已有 camera 转换/刷新/保存/重开；不支持姿态明确拒绝。
- [ ] R03 从实际选中对象及原生列表采用有效 IfcSpace。
- [ ] R04 storey 与 slab 两条基准路径独立成立。
- [ ] R05 自动层高/手动高度 OR，零标高不等于零层高，SI 换算正确。
- [ ] R06 普通与选墙 B4 均可用，局部范围不虚构闭合，性能如实记录。
- [ ] R07 B4 原有进度、候选容器、eye、面积和诊断保留。
- [ ] R08 sketch shell/holes 底面/高度到 native extrude 几何一致性验证。
- [ ] R09 Analyze 不写 IFC；明确确认才写；失败回滚并能再试。
- [ ] R10 excluded/unknown 不贡献家具目标分析，但仍按物理事实占用。
- [ ] R11 空间范围、组目标、其他占用、unknown 与 query 身份完整。
- [ ] R12 新建和既有 Space 均跑通 plane→space→free-space→保存重开。
- [ ] 部署字节与实际已加载模块证明一致；operator 已注册不能代替新代码已加载。
- [ ] 真实交互/GPU 与性能证据独立验收；B3 仍 OPEN。

## 审计中已有失败

2026-10-19 三条定点测试为 2 passed/1 failed；失败为 delivery `test/test_physical_occupancy_resolution.py::test_furniture_exclusion_vetoes_direct_group_and_affordance_contribution`，期望 `group.support_area is None`，实际 `4.0`。对象视图已排除 A、physical_occupancy 保留 A/B 均通过；失败在家具组描述消费者。修复必须保留失败历史，不改断言来掩盖它。
