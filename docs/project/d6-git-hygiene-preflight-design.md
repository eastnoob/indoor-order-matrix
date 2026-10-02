# D6 Git Hygiene / Evidence Inventory 前置任务设计

- 日期：2026-10-02
- 状态：设计完成，等待独立 session 执行
- 目的：整理当前大量 dirty/untracked 设计证据，使后续交接和选择性提交可审计
- 主线关系：独立辅助任务，不改变空间场、家具组、trend 或 Bayesian 主线

## 为什么需要这个前置任务

当前分支历史正常，但工作区包含多轮设计文档、probe、渲染物、复核记录和临时文件。部分文件尚未纳入 Git，`.tmp-test-preview-final2` 还存在权限诊断。直接继续使用 `git add .` 会混入不同阶段的证据，阻碍复现和交接。

## 任务边界

允许：只读盘点、分类、重复/孤儿证据识别、hash 和路径清单、提交包建议、权限问题报告。

禁止：删除、移动、覆盖、改名、修改 `.gitignore`、修改 production code、重跑实验、重新渲染、修改源 IFC/Blender、提交当前主线、解决权限问题、合并或重写历史。

## 分类模型

每个未跟踪路径必须归入一个建议类别，并给出理由和 provenance：

- `retain-for-commit`：设计/证据应纳入版本控制；
- `retain-local-artifact`：需要保留但适合由 manifest/外部产物保存；
- `duplicate-or-superseded`：被新证据替代，不能直接删除，只提出处理建议；
- `temporary-or-log`：本地日志或运行残留，提出 ignore/归档建议，不修改；
- `permission-blocked`：无法安全读取或校验；
- `needs-owner-decision`：语义或归属不能由脚本推断。

## 阶段与停止点

1. **Inventory**：记录当前 HEAD、分支、tracked/untracked/staged 状态和权限错误。
2. **Evidence map**：按 D6 子任务、日期、commit、输入、输出、review 状态建立路径映射。
3. **Integrity check**：对可读文件计算 bytes/SHA-256；不运行实验，不把 hash 当作语义验证。
4. **Commit bundles**：提出最小提交包，例如契约文档、独立 review、实验脚本/manifest、渲染产物；每包列出允许路径和排除路径。
5. **Owner gate**：停止并等待 owner 选择保留/提交/本地归档/忽略。未经批准不得改变工作区。

## 交付物

仅新增：

- `docs/project/evidence/d6-git-hygiene-inventory.json`
- `docs/project/evidence/d6-git-hygiene-inventory.md`
- `docs/project/evidence/d6-git-hygiene-artifact-manifest.json`

报告必须包含：命令、当前 HEAD、分支、路径分类、hash 覆盖率、不可读路径、权限问题、建议提交包、主线不受影响的说明、未决 owner 决定。

## 通过标准

- 没有 `git add .`、删除、移动或覆盖；
- 没有 production/API/test/IFC/Blender 修改；
- 所有可读未跟踪路径均有分类或明确列入 `needs-owner-decision`；
- `.tmp-test-preview-final2` 权限问题单独记录，不被当作本任务新错误；
- 报告不把“已盘点”写成“已清理”或“已提交”。

## 主线交接

本任务完成后，空间场主线继续从现有 `repair_v1` 独立复核已接受状态进入封闭房间/analysis-domain 候选设计。Git hygiene 任务只提供路径和提交建议，不改变该设计顺序。

**STOP FOR GIT HYGIENE INVENTORY OWNER REVIEW**
