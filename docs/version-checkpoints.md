# 版本保存点与恢复方法

## 2026-11-07：模拟人外部验证前的完整 v2

- 固定附注标签：`baseline-finite-budget-v2-20261107`。
- 提交：`4b9e7e3f93c2f0e98f1a42c5ab0cd7b363aa5bf3`。
- [查看完整 v2 保存点](https://github.com/Farewellxxxx/X-Program-Beyesian/tree/baseline-finite-budget-v2-20261107)。标签已于本轮正式实验前推送；GitHub API 核对标签对象 `1ec7ea2e883c68678bc44150eeca89382099d125` 指向上述提交，远端 main 与 v2 分支均保持原提交。
- v2 分支 `research/finite-budget-v2` 与本机 `.worktrees/finite-budget-v2` 保持原提交；代码、配置、原结果均保留。
- 本轮工作分支为 `research/observer-validation-v3-study`，可写工作目录为 `E:/study documents/X program/YY Wang/.worktrees/observer-validation-v3`。`main` 保持 v1。

要恢复 v2，请新建副本，不需要重置当前工作。下列目标目录须尚未存在：

```powershell
git -C 'E:/study documents/X program/YY Wang/.publish/X-Program-Beyesian' fetch origin --tags
git -C 'E:/study documents/X program/YY Wang/.publish/X-Program-Beyesian' worktree add --detach 'E:/study documents/X program/YY Wang/.worktrees/restored-v2' baseline-finite-budget-v2-20261107
```

若需继续修改恢复后的版本，可在新目录执行 `git switch -c research/from-preserved-v2`。本轮不移动或覆盖 v1、v2 保存标签。Git 只能恢复已跟踪文件；本地未纳入仓库的个人材料不属于这些保存点。

## 已保存的完整 v1

用户要求在尝试有限预算新方案前保留的版本是：

- **标签：`baseline-decoupled-v1-20261105`**
- **提交：`5556eb4ad95259ee3a8018fd97cd96fd1f9795ca`**
- [直接浏览保存点](https://github.com/Farewellxxxx/X-Program-Beyesian/tree/baseline-decoupled-v1-20261105)
- [对应提交](https://github.com/Farewellxxxx/X-Program-Beyesian/commit/5556eb4ad95259ee3a8018fd97cd96fd1f9795ca)

这是已完成独立模拟乘客、共同估计器下 BO/UCB/staircase 比较的完整发布版本，包含原代码、配置、合成结果、图表和验证记录。其553个清单条目可由`publication_manifest_sha256.csv`验证（清单不对自身求哈希）。本次已推送附注标签，并通过GitHub API核对标签最终指向上述提交。

标签是固定保存点；本项目后续不会移动或覆盖这个标签。即使其他分支继续发展，也能从这里另开副本。Git保存范围限于仓库已跟踪文件；本地未纳入Git的论文、原始数据和个人文件没有被本次操作修改。

## 新旧版本分开放置

| 用途 | 分支或标签 | 本机目录 |
|---|---|---|
| v1原发布目录 | `main`，本轮保持在上述提交 | `E:/study documents/X program/YY Wang/.publish/X-Program-Beyesian` |
| 固定恢复点 | `baseline-decoupled-v1-20261105` | GitHub和本地Git均有 |
| v2有限预算实验 | `research/finite-budget-v2` | `E:/study documents/X program/YY Wang/.worktrees/finite-budget-v2` |

v2使用[独立研究分支](https://github.com/Farewellxxxx/X-Program-Beyesian/tree/research/finite-budget-v2)，本轮不合并main。v2的[中文结果报告](../comfort_boundary_bo_research_package/docs/finite_budget_results_zh.md)与[验证记录](2026-11-05-finite-budget-verification.md)均在新分支中。原工作区中的v1代码与结果保留；使用v2时进入上表的新目录，避免混用两套运行入口。

## 需要恢复时

最稳妥的方式是新建一个v1副本，当前v2工作不受影响。在PowerShell执行（目标目录须尚未存在）：

```powershell
git -C 'E:/study documents/X program/YY Wang/.publish/X-Program-Beyesian' fetch origin --tags
git -C 'E:/study documents/X program/YY Wang/.publish/X-Program-Beyesian' worktree add --detach 'E:/study documents/X program/YY Wang/.worktrees/restored-v1' baseline-decoupled-v1-20261105
```

随后在`E:/study documents/X program/YY Wang/.worktrees/restored-v1`运行原README中的命令。若要从v1开始新的修改，可在该目录执行`git switch -c research/from-preserved-v1`。这些操作不会删除v2，也不需要重置或强制覆盖main。

只想看旧文件时，直接打开上面的GitHub保存点链接即可。
