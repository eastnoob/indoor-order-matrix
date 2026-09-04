# IFC/BIM 转换工作流使用说明

本文是 `ifc-bim-conversion-workflow` skill 的操作入口，适用于 Rhino、Blender 等模型的 BIM 化、IFC 导出、校验和 Bonsai 导入。

## 核心原则

- 源模型默认只读；每阶段独立执行、独立报告，不静默进入下一阶段。
- 几何、图层名和对象名只是证据，不能单独证明 BIM 语义。
- 用户提供的语义、分组、柱网和分析替身优先，缺失时才使用几何推断。
- IFC 是事实来源；区域、路径、trend、边界证据、热图和评分是分析结果，默认不写回事实 IFC。
- 描述层不含感知权重或最终评分。
- 输出目录可选；未指定时使用 `<当前项目>/outputs/<模型名>/`，不覆盖已有结果；输出目录与导入目标相互独立。

## 1. 环境预检

确认 Pixi/Python、IfcOpenShell、源/目标软件、官方 IFC 路径和 MCP 端点。项目使用指定 Blender：

```powershell
pixi run python --version
D:/Blender/BlenderPortableLTS5.2/App/Blender64/blender.exe
```

缺少 IfcOpenShell 时校验为 `not_available`，并阻止导入。不要静默安装依赖或修改用户软件配置。

## 2. 模型预检

检查并记录：单位与比例、Z 高度、坐标和变换、对象可分离性、组/图层/名称/材质、几何有效性、来源，以及用户提供的柱网、可供区域、开口和替身。

最低条件：单位可信、几何基本有效、对象可聚合、具有足够的语义线索。源模型不必预先是完整 IFC。

## 3. 语义归一化

- 一个逻辑家具可以由多个零件组成。
- STL 零件、材质层或 Rhino 组编号不能直接当作家具语义。
- 几何与空间关系推断必须保留源对象 ID、来源组和推断依据。
- 用户指定的语义及替身不得被自动推断覆盖。
- 用户替身优先；动态替身仅用于计算，不替换可见主体，也不默认写入 IFC。
 - 家具整体通常是最小分析单位；椅腿、坐垫、靠背等先视为零件。
 - 优先使用用户分组、Block/Instance 和父子关系；不得仅用全局坐标象限判定归属。
 - 几何证据充分时可以自动聚合，但必须保留来源对象 ID 和置信度。
 - 归属不明确或候选明显残缺时才暂停并询问用户，不因多零件、斜向或跨原点而一律阻止。

嵌套组按“对象—组关系图”处理，而不是按语义树处理：同一对象可能
属于多个组，嵌套组也可能只是组织用途。Block/Instance 是强证据，但不是
绝对的家具边界，仍需判断它是否形成完整功能实体。组名只是标签，不是
身份；稳定依据应是源对象 ID、组 ID，以及可用时的 Block 实例路径。

用户可以显式指定 `logical_object`、`assembly` 或 `component` 覆盖自动判断。
没有显式规则时，系统综合完整几何、空间紧凑性、同级重复结构和功能完整性；
无法确定时进入复核，不静默拆分。

例如，31 个 Rhino 零件可以归一化为 4 把椅子和 1 张桌子，但必须明确这是推断结果，而非源模型自带语义。
建议用户将一件家具的零件放入同一 Group、Block/Instance 或父子层级，并使用 `Chair_01` 等稳定名称；这是帮助识别，不是硬性前置条件。

## 4. IFC 导出

依次选择：已有项目适配器、原生 IFC 导出器、IfcOpenShell 适配器；只有均不可用时才编写最小导出器。

至少保留项目及空间结构、单位、产品实体、类型关系、空间包含、用户定义组和来源信息。家具可使用 `IfcFurniture`/`IfcFurnitureType`，家具组使用 `IfcGroup`，显式柱网优先映射为 `IfcGrid`/`IfcGridAxis`。自定义事实属性使用 `OM_*`，不得冒用保留的 `Pset_*` 名称。

输出目录不作为强制输入。未指定时，将 IFC、inspection、validation、映射和日志统一写入 `<当前项目>/outputs/<模型名>/`；若结果已存在，应创建独立运行目录或先询问是否覆盖。导出完成不等于自动导入。

## 5. 独立检查与校验

```powershell
pixi run python skills/ifc-bim-conversion-workflow/scripts/inspect_ifc.py <file.ifc> --json
pixi run python skills/ifc-bim-conversion-workflow/scripts/validate_ifc.py <file.ifc> --express-rules
```

检查 schema、单位、实体数量、GlobalId 重复、空间包含、类型/组关系及几何表示。`failed` 或 `not_available` 均阻止导入；能被解析不等于 IFC 合法，错误与警告必须分开记录。

## 6. 导入决策

先展示校验结果，再明确选择：

- 模式：`manual` 或 `automatic`。
- 目标：Rhino、Blender+Bonsai 或其他软件。

自动导入会修改目标场景，必须在执行前获得明确确认；清空场景和保存文件需要分别说明，不能沿用模糊授权。

## 7. Bonsai 导入

必须按 IFC 项目加载，而非几何导入：

```python
import bpy

bpy.ops.bim.load_project(
    filepath="<file.ifc>",
    should_start_fresh_session=False,
    import_without_ifc_data=False,
    is_advanced=False,
)
```

注意：

- `import_without_ifc_data=True` 会丢失 BIM 元数据，不能证明 BIM 导入成功。
- `should_start_fresh_session=True` 可能清空会话，只有用户明确批准才使用。
- 不默认保存 `.blend`，避免覆盖用户文件；Rhino 源文件继续保持只读。

## 8. 导入后核验

```powershell
pixi run python skills/ifc-bim-conversion-workflow/scripts/verify_bonsai_mapping.py
```

必须确认活动 `IfcStore`、schema、要求的实体数量、类型/组/空间关系和几何对象。每个 Blender BIM 对象必须具有正的非零整数 `BIMObjectProperties.ifc_definition_id`，且该 ID 能反查对应 IFC 实体。

对象名类似 `IfcFurniture/chair_01` 只是标签，不是映射证据。核验步骤只读，不得导入、删除、清空或保存。

## 常见误判

- 31 个零件不等于 31 件家具。
 - 全局坐标的四个象限不能作为家具零件归属的唯一依据。
- 图层叫 `furniture` 不等于对象已经是 `IfcFurniture`。
- Blender 中看见网格不等于 Bonsai 已导入 BIM。
- IFC 能解析不等于通过规则校验。
- 有 `IfcGroup` 不等于成员关系正确。
- 有 IFC 文件不等于当前 `IfcStore` 已激活。
- 离线测试成功不等于用户当前 Blender 场景已通过实时核验。

## 每次应保留的记录

- 源模型路径与只读预检摘要。
- 逻辑对象、来源 ID 和推断依据。
 - 逻辑家具与源零件的映射、置信度和待确认项。
- IFC 输出路径、inspection 和 validation 报告。
- 导入模式、目标及确认记录。
- Bonsai 实体、关系与对象映射核验结果。
- 失败、未执行和工具不可用的具体原因。

## 现有入口

- [Skill 入口](../skills/ifc-bim-conversion-workflow/SKILL.md)
- [IFC 检查器](../skills/ifc-bim-conversion-workflow/scripts/inspect_ifc.py)
- [IFC 校验器](../skills/ifc-bim-conversion-workflow/scripts/validate_ifc.py)
- [Bonsai 映射核验器](../skills/ifc-bim-conversion-workflow/scripts/verify_bonsai_mapping.py)

## 完成标准

只有“源对象语义可追溯、IFC 合法、Bonsai 活动 `IfcStore` 存在、对象到 IFC 的正数映射可反查”同时满足，才可以称为 BIM 化导入完成。
