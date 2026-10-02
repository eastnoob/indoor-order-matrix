# D6 当前 IFC 空间分区候选 Blender 可视化实验

- 日期：2026-10-02
- 状态：STOP FOR OWNER VISUAL REVIEW
- 目的：并列展示不细分基线与几何关系支持的探索性分区候选。
- 当前 Blender：已直接观察并确认 Bonsai IfcStore.path 与本实验 IFC 相同；当前场景未修改、未保存。

## 边界与状态

当前 IFC 没有 IfcSpace，也没有 owner 接受的 AnalysisDomain。所有图使用源几何范围作为 diagnostic_only 视图框，并明确标为 provisional；它不是 room、free-space 或生产边界。

## 实测可用输入

- IFC4；长度单位 mm，换算到米 0.001。
- 原生计数：IfcGroup=37、IfcFurniture=95、IfcWall=11、IfcDoor=6、IfcSpace=0、IfcOpeningElement=0、IfcRelVoidsElement=0。
- 分析节点：37 个 exact group_role == furniture_group，成员保持组内不可拆分；95 个成员几何可用。
- 墙体：11 个可显示的实体墙体几何；墙厚保留在源墙网格的显示层中。
- 组间关系：平面边界间隙、重叠/接触、质心距离和高度兼容性可计算；障碍物穿越关系未用于分区。

## 缺失或未计算输入

- 没有合格 AnalysisDomain；没有 free-space、连通性、route、walkability、visibility 或空间功能结论。
- 没有 IfcRelVoidsElement / IfcRelFillsElement；门几何不被解释为 opening relation，也不推断开闭状态。
- 标签/name 只作为并列诊断字段，不参与分区；没有未经校准的概率或准确率。

## 候选为何不同

- 基线把全部家具组放入一个 provisional diagnostic region，显示“也可能不再细分”。
- 2/3/4 区候选使用同一组间几何关系图：以归一化平面边界间隙构造最小生成树，再分别切除最大、前两条、前三条正间隙边。没有固定米数阈值；切口边和原始数值写入 zone_candidates.json。
- 这些切分是并列诊断视图，不代表最终分区数、最终算法或 owner 认可。

## 视觉阅读提示

- 彩色半透明块：候选区域的显示包络；黑色边框和 Gxx：一个不可拆分的 furniture_group analysis node。
- 灰色实体：墙体或 context/reference；门只作为 context/reference。
- 图例包含 provisional diagnostic candidate — not owner-confirmed、furniture_group analysis node、context/reference only、physical wall geometry 及边界状态。

## Owner 目视问题

- 哪个候选最像你理解的空间分区？
- 有没有图上没分开、但你认为应单独成区的部分？
- 这些颜色更像独立区域，还是一个连续场中的软边界？

STOP FOR OWNER VISUAL REVIEW
